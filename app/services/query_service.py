from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from itertools import chain
from typing import Iterable
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge import Component, KnowledgeModel, Relationship, RelationshipType
from app.models.source import SourceDocument
from app.models.user import Workspace
from app.schemas.query import (
    FreshnessStatus,
    QueryComponentRead,
    QueryFilters,
    QueryResult,
    QuerySourceRead,
)

STOPWORDS = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "do",
    "for",
    "from",
    "how",
    "in",
    "is",
    "it",
    "of",
    "on",
    "our",
    "the",
    "to",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "with",
}
RELATIONSHIP_HINT_TOKENS = {
    "affect",
    "because",
    "blocked",
    "blocker",
    "delay",
    "delayed",
    "depends",
    "dependency",
    "impact",
    "impacts",
    "related",
    "relationship",
    "why",
}
RELATIONSHIP_TYPE_WEIGHT = {
    RelationshipType.BLOCKED_BY: 2.5,
    RelationshipType.DEPENDS_ON: 2.0,
    RelationshipType.CONTRADICTS: 1.75,
    RelationshipType.ENABLES: 1.25,
    RelationshipType.SUPERSEDES: 1.0,
    RelationshipType.RELATED_TO: 0.75,
}


class QueryServiceError(Exception):
    """Base query service error."""


class QueryResourceNotFoundError(QueryServiceError):
    """Raised when a query references a missing workspace."""


@dataclass(slots=True)
class ScoredComponent:
    model: KnowledgeModel
    component: Component
    score: float
    blended_confidence: float


class QueryService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def query(
        self,
        question: str,
        workspace_id: UUID,
        filters: QueryFilters | None = None,
    ) -> QueryResult:
        filters = filters or QueryFilters()
        workspace = await self.session.scalar(
            select(Workspace).where(Workspace.id == workspace_id).limit(1)
        )
        if workspace is None:
            raise QueryResourceNotFoundError("Workspace not found")

        models = await self._load_models(workspace_id, filters)
        scored = self._score_components(question, models, filters)

        if not scored:
            return QueryResult(
                question=question,
                answer=(
                    f'I could not find matching structured context for "{question}" '
                    "in this workspace."
                ),
                confidence=0.0,
                freshness=FreshnessStatus.CURRENT,
                components=[],
                sources=[],
                answered_at=self._answered_at(),
            )

        selected = self._select_components(scored)
        components = [self._serialize_component(item) for item in selected]
        sources = self._serialize_sources(selected)
        answer = self._build_answer(question, selected)
        confidence = round(sum(item.blended_confidence for item in selected) / len(selected), 2)
        freshness = self._calculate_freshness(item.component for item in selected)

        return QueryResult(
            question=question,
            answer=answer,
            confidence=confidence,
            freshness=freshness,
            components=components,
            sources=sources,
            answered_at=self._answered_at(),
        )

    async def _load_models(
        self,
        workspace_id: UUID,
        filters: QueryFilters,
    ) -> list[KnowledgeModel]:
        stmt = (
            select(KnowledgeModel)
            .options(
                selectinload(KnowledgeModel.components).selectinload(Component.source_documents),
                selectinload(KnowledgeModel.components)
                .selectinload(Component.outgoing_relationships)
                .selectinload(Relationship.target_component),
                selectinload(KnowledgeModel.components)
                .selectinload(Component.incoming_relationships)
                .selectinload(Relationship.source_component),
            )
            .where(KnowledgeModel.workspace_id == workspace_id)
            .order_by(KnowledgeModel.name.asc())
        )

        if filters.model_names:
            lowered = {name.lower() for name in filters.model_names}
            result = await self.session.scalars(stmt)
            return [model for model in result if model.name.lower() in lowered]

        result = await self.session.scalars(stmt)
        return list(result)

    def _score_components(
        self,
        question: str,
        models: Iterable[KnowledgeModel],
        filters: QueryFilters,
    ) -> list[ScoredComponent]:
        question_text = question.lower()
        question_tokens = self._tokenize(question)
        scored: list[ScoredComponent] = []

        for model in models:
            model_tokens = self._tokenize(model.name)
            model_score = 0.0
            if model.name.lower() in question_text:
                model_score += 2.5
            model_score += 1.25 * len(model_tokens & question_tokens)

            for component in model.components:
                if component.confidence < filters.min_confidence:
                    continue
                if not self._within_age_limit(component, filters.max_age_days):
                    continue

                component_tokens = self._tokenize(component.name)
                value_tokens = self._tokenize(component.value)
                authority_tokens = self._tokenize(component.authority_source or "")

                score = model_score
                if component.name.lower() in question_text:
                    score += 5.0
                score += 2.5 * len(component_tokens & question_tokens)
                score += 1.0 * min(3, len(value_tokens & question_tokens))
                score += 0.5 * min(2, len(authority_tokens & question_tokens))

                if score <= 0:
                    continue

                query_match_confidence = min(score / 10.0, 1.0)
                blended_confidence = round(
                    (0.6 * component.confidence) + (0.4 * query_match_confidence), 2
                )
                scored.append(
                    ScoredComponent(
                        model=model,
                        component=component,
                        score=score,
                        blended_confidence=min(blended_confidence, 1.0),
                    )
                )

        scored.sort(
            key=lambda item: (
                item.score,
                item.blended_confidence,
                item.component.last_verified_at,
            ),
            reverse=True,
        )
        return scored

    def _select_components(self, scored: list[ScoredComponent]) -> list[ScoredComponent]:
        best = scored[0]
        selected = [best]
        seen_signatures = {self._component_signature(best.component)}
        minimum_score = max(best.score * 0.72, best.score - 1.5)

        for candidate in scored[1:]:
            if len(selected) >= 3:
                break
            if candidate.score < minimum_score:
                continue
            signature = self._component_signature(candidate.component)
            if signature in seen_signatures:
                continue
            selected.append(candidate)
            seen_signatures.add(signature)

        return selected

    def _serialize_component(self, scored: ScoredComponent) -> QueryComponentRead:
        return QueryComponentRead(
            id=scored.component.id,
            model=scored.model.name,
            name=scored.component.name,
            value=scored.component.value,
            confidence=scored.component.confidence,
            authority_source=scored.component.authority_source,
            last_verified_at=scored.component.last_verified_at,
        )

    def _serialize_sources(self, scored: Iterable[ScoredComponent]) -> list[QuerySourceRead]:
        seen: set[UUID] = set()
        serialized: list[QuerySourceRead] = []
        documents: list[SourceDocument] = []

        for item in scored:
            documents.extend(item.component.source_documents)

        documents.sort(
            key=lambda doc: doc.created_at_source or doc.ingested_at,
            reverse=True,
        )

        for doc in documents:
            if doc.id in seen:
                continue
            seen.add(doc.id)
            serialized.append(
                QuerySourceRead(
                    type=doc.connector_type.value,
                    author=doc.author,
                    date=doc.created_at_source.date().isoformat()
                    if doc.created_at_source is not None
                    else None,
                    url=doc.source_url,
                )
            )
            if len(serialized) >= 5:
                break

        return serialized

    def _build_answer(self, question: str, scored: list[ScoredComponent]) -> str:
        relationship_context = self._build_relationship_context(question, scored[0])

        if len(scored) == 1:
            item = scored[0]
            answer = f"{item.component.name} ({item.model.name}): {item.component.value}."
            if relationship_context:
                return f"{answer} {relationship_context}"
            return answer

        models = {item.model.name for item in scored}
        summary = "; ".join(
            f"{item.component.name}: {item.component.value}" for item in scored[:3]
        )
        if len(models) == 1:
            model_name = next(iter(models))
            answer = f"I found {len(scored)} relevant components in {model_name}: {summary}."
        else:
            answer = f"I found {len(scored)} relevant components across the workspace: {summary}."
        if relationship_context:
            return f"{answer} {relationship_context}"
        return answer

    def _build_relationship_context(
        self,
        question: str,
        scored: ScoredComponent,
    ) -> str | None:
        question_tokens = self._tokenize(question)
        if not (question_tokens & RELATIONSHIP_HINT_TOKENS):
            return None

        relation_match = self._select_relationship(scored.component, question)
        if relation_match is None:
            return None

        relation, other_component = relation_match
        sentence = self._relationship_sentence(scored.component, relation, other_component)
        if relation.description:
            description = relation.description.strip()
            if description:
                description = description.rstrip(".") + "."
                return f"{sentence} {description}"
        return sentence

    def _select_relationship(
        self,
        component: Component,
        question: str,
    ) -> tuple[Relationship, Component] | None:
        question_text = question.lower()
        question_tokens = self._tokenize(question)
        candidates: list[tuple[float, Relationship, Component]] = []

        for relation in chain(component.outgoing_relationships, component.incoming_relationships):
            other_component = self._other_component(component, relation)
            if other_component is None:
                continue

            relation_tokens = self._tokenize(relation.relationship_type.value.replace("_", " "))
            other_tokens = self._tokenize(other_component.name)
            score = RELATIONSHIP_TYPE_WEIGHT.get(relation.relationship_type, 1.0) + relation.confidence
            score += 0.75 * len(relation_tokens & question_tokens)
            score += 0.5 * min(2, len(other_tokens & question_tokens))

            if relation.relationship_type in {
                RelationshipType.BLOCKED_BY,
                RelationshipType.DEPENDS_ON,
            } and question_tokens & {"because", "blocked", "blocker", "delay", "delayed", "depends", "dependency", "why"}:
                score += 1.0

            if other_component.name.lower() in question_text:
                score += 1.0

            candidates.append((score, relation, other_component))

        if not candidates:
            return None

        candidates.sort(key=lambda item: item[0], reverse=True)
        _, relation, other_component = candidates[0]
        return relation, other_component

    def _other_component(
        self,
        component: Component,
        relation: Relationship,
    ) -> Component | None:
        if relation.source_component_id == component.id:
            return relation.target_component
        if relation.target_component_id == component.id:
            return relation.source_component
        return None

    def _relationship_sentence(
        self,
        component: Component,
        relation: Relationship,
        other_component: Component,
    ) -> str:
        if relation.source_component_id == component.id:
            if relation.relationship_type == RelationshipType.BLOCKED_BY:
                return f"It is blocked by {other_component.name}."
            if relation.relationship_type == RelationshipType.DEPENDS_ON:
                return f"It depends on {other_component.name}."
            if relation.relationship_type == RelationshipType.ENABLES:
                return f"It enables {other_component.name}."
            if relation.relationship_type == RelationshipType.CONTRADICTS:
                return f"It conflicts with {other_component.name}."
            if relation.relationship_type == RelationshipType.SUPERSEDES:
                return f"It supersedes {other_component.name}."
            return f"It is related to {other_component.name}."

        if relation.relationship_type == RelationshipType.BLOCKED_BY:
            return f"{other_component.name} is blocked by it."
        if relation.relationship_type == RelationshipType.DEPENDS_ON:
            return f"{other_component.name} depends on it."
        if relation.relationship_type == RelationshipType.ENABLES:
            return f"{other_component.name} is enabled by it."
        if relation.relationship_type == RelationshipType.CONTRADICTS:
            return f"{other_component.name} conflicts with it."
        if relation.relationship_type == RelationshipType.SUPERSEDES:
            return f"{other_component.name} is superseded by it."
        return f"{other_component.name} is related to it."

    def _calculate_freshness(self, components: Iterable[Component]) -> FreshnessStatus:
        now = datetime.now(UTC)
        stale_threshold = now - timedelta(days=30)
        warning_threshold = now - timedelta(days=7)

        freshness = FreshnessStatus.CURRENT
        for component in components:
            last_verified = self._normalize_dt(component.last_verified_at)
            if last_verified <= stale_threshold:
                return FreshnessStatus.STALE
            if last_verified <= warning_threshold:
                freshness = FreshnessStatus.POSSIBLY_STALE
        return freshness

    def _within_age_limit(self, component: Component, max_age_days: int | None) -> bool:
        if max_age_days is None:
            return True
        cutoff = datetime.now(UTC) - timedelta(days=max_age_days)
        return self._normalize_dt(component.last_verified_at) >= cutoff

    def _normalize_dt(self, value: datetime) -> datetime:
        if value.tzinfo is None:
            return value.replace(tzinfo=UTC)
        return value.astimezone(UTC)

    def _tokenize(self, text: str) -> set[str]:
        return {
            token
            for token in re.findall(r"[a-z0-9]+", text.lower())
            if len(token) > 1 and token not in STOPWORDS
        }

    def _component_signature(self, component: Component) -> tuple[str, str]:
        return (
            component.name.strip().lower(),
            component.value.strip().lower(),
        )

    def _answered_at(self) -> str:
        return datetime.now(UTC).strftime("%Y-%m-%d %H:%M UTC")
