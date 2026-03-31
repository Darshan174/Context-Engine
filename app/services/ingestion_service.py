"""Ingestion pipeline — processes raw SourceDocuments into knowledge graph facts.

Phase 1 uses a rule-based stub extractor.  A future phase will swap in
an LLM-backed extractor without changing the service interface.
"""

from __future__ import annotations

import re
from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.knowledge import (
    Component,
    ComponentSource,
    KnowledgeModel,
    Relationship,
    RelationshipType,
)
from app.models.review import ReviewItem
from app.models.source import ConnectorType, SourceDocument


class IngestionServiceError(Exception):
    """Base ingestion error."""


class IngestionService:
    """Reads unprocessed SourceDocuments and creates knowledge graph entries."""

    _LOW_CONFIDENCE_THRESHOLD = 0.60
    _HIGH_RISK_CONFIDENCE_THRESHOLD = 0.45
    _AUTO_MODEL_NAMES: dict[ConnectorType, tuple[str, str]] = {
        ConnectorType.SLACK: ("Slack Insights", "Auto-generated from Slack connector sync"),
        ConnectorType.NOTION: ("Notion Insights", "Auto-generated from Notion connector sync"),
    }
    _FALLBACK_MODEL = ("Connector Insights", "Auto-generated from connector sync")

    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def process_single_document(
        self,
        workspace_id: UUID,
        document: SourceDocument,
        connector_type: ConnectorType | None = None,
    ) -> int:
        """Process a single SourceDocument (used by reprocess endpoint).

        Returns 1 if the document was processed, 0 if already processed.
        """
        if document.processed_at is not None:
            return 0

        model_name, model_desc = self._AUTO_MODEL_NAMES.get(
            connector_type, self._FALLBACK_MODEL
        )
        model = await self._get_or_create_model(workspace_id, model_name, model_desc)

        await self._ingest_document(model, document)

        document.processed_at = datetime.now(timezone.utc)
        await self.session.flush()
        return 1

    async def process_connector_documents(
        self,
        workspace_id: UUID,
        connector_id: UUID,
        connector_type: ConnectorType | None = None,
    ) -> int:
        """Process all unprocessed SourceDocuments for a specific connector.

        Returns the number of documents processed.
        """
        docs = await self._select_unprocessed(connector_id)
        if not docs:
            return 0

        model_name, model_desc = self._AUTO_MODEL_NAMES.get(
            connector_type, self._FALLBACK_MODEL
        )
        model = await self._get_or_create_model(workspace_id, model_name, model_desc)

        processed = 0
        for doc in docs:
            await self._ingest_document(model, doc)
            doc.processed_at = datetime.now(timezone.utc)
            processed += 1

        await self.session.flush()
        return processed

    # ── Private helpers ───────────────────────────────────────────

    async def _select_unprocessed(
        self, connector_id: UUID
    ) -> list[SourceDocument]:
        """Return SourceDocuments for this connector that have not been processed yet.

        Uses populate_existing so that ORM objects are refreshed from the
        DB — necessary because _persist_documents uses Core-level SQL
        that bypasses the ORM identity map when resetting processed_at.
        """
        result = await self.session.scalars(
            select(SourceDocument)
            .where(
                SourceDocument.connector_id == connector_id,
                SourceDocument.processed_at.is_(None),
            )
            .order_by(SourceDocument.ingested_at)
            .execution_options(populate_existing=True)
        )
        return list(result)

    async def _get_or_create_model(
        self, workspace_id: UUID, model_name: str, model_desc: str,
    ) -> KnowledgeModel:
        """Return the auto-generated KnowledgeModel, creating it if needed."""
        model = await self.session.scalar(
            select(KnowledgeModel).where(
                KnowledgeModel.workspace_id == workspace_id,
                KnowledgeModel.name == model_name,
            )
        )
        if model is None:
            model = KnowledgeModel(
                workspace_id=workspace_id,
                name=model_name,
                description=model_desc,
                auto_generated=True,
            )
            self.session.add(model)
            await self.session.flush()
        return model

    async def _create_component(
        self,
        model: KnowledgeModel,
        name: str,
        value: str,
        confidence: float,
        doc: SourceDocument,
    ) -> Component:
        """Create a new component version for a fact."""
        component = Component(
            model_id=model.id,
            name=name,
            value=value,
            confidence=confidence,
            authority_source=doc.source_url,
            valid_from=datetime.now(timezone.utc),
        )
        self.session.add(component)
        await self.session.flush()
        return component

    async def _ensure_source_link(
        self, component: Component, doc: SourceDocument
    ) -> None:
        """Create a ComponentSource link if it doesn't already exist."""
        exists = await self.session.scalar(
            select(ComponentSource.component_id).where(
                ComponentSource.component_id == component.id,
                ComponentSource.source_document_id == doc.id,
            )
        )
        if exists is not None:
            return

        link = ComponentSource(
            component_id=component.id,
            source_document_id=doc.id,
            extraction_context=f"Extracted from {doc.connector_type.value} "
            f"document {doc.external_id}",
        )
        self.session.add(link)
        await self.session.flush()

    async def _ingest_document(
        self,
        model: KnowledgeModel,
        doc: SourceDocument,
    ) -> None:
        now = datetime.now(timezone.utc)
        facts = self._collapse_facts(self._extract_facts(doc))
        existing_links = await self._load_document_links(doc.id)
        retained_component_ids: set[UUID] = set()

        for name, value, confidence in facts:
            component = await self._resolve_component_for_fact(
                model=model,
                name=name,
                value=value,
                confidence=confidence,
                doc=doc,
                observed_at=now,
            )
            await self._ensure_source_link(component, doc)
            retained_component_ids.add(component.id)

        for link, component in existing_links:
            if component.id in retained_component_ids:
                continue
            await self.session.delete(link)
            await self.session.flush()
            await self._retire_if_orphaned(
                component,
                reason=(
                    f"Source document {doc.external_id} no longer supports "
                    f"{component.name}."
                ),
                retired_at=now,
            )

    async def _resolve_component_for_fact(
        self,
        *,
        model: KnowledgeModel,
        name: str,
        value: str,
        confidence: float,
        doc: SourceDocument,
        observed_at: datetime,
    ) -> Component:
        active_components = await self._select_active_components(model.id, name)
        same_value = next(
            (component for component in active_components if component.value == value),
            None,
        )
        if same_value is not None:
            same_value.confidence = max(same_value.confidence, confidence)
            same_value.last_verified_at = observed_at
            same_value.is_stale = False
            same_value.authority_source = doc.source_url
            await self._sync_active_review_item(
                same_value,
                confidence=confidence,
                conflicting_with=[],
            )
            await self.session.flush()
            return same_value

        component = await self._create_component(model, name, value, confidence, doc)
        for previous in active_components:
            await self._supersede_component(
                previous,
                successor=component,
                reason=(
                    f"{name} changed from {previous.value!r} to {value!r} "
                    f"based on source document {doc.external_id}."
                ),
                superseded_at=observed_at,
            )

        await self._sync_active_review_item(
            component,
            confidence=confidence,
            conflicting_with=active_components,
        )
        await self.session.flush()
        return component

    async def _sync_active_review_item(
        self,
        component: Component,
        *,
        confidence: float,
        conflicting_with: list[Component],
    ) -> None:
        if conflicting_with:
            title = f"{component.name} changed across sources"
            summary = (
                f'The latest extracted value is "{component.value}", but a prior active fact '
                f"was superseded during ingestion and still needs human confirmation."
            )
            await self._upsert_review_item(
                component,
                status="needs_review",
                severity="high",
                kind="conflict",
                title=title,
                summary=summary,
                confidence=confidence,
                rationale=(
                    f"{component.name} replaced an earlier active fact during ingestion. "
                    "A human should confirm that the newest value is canonical."
                ),
                suggested_action=(
                    "Confirm whether the latest value should remain active or mark it superseded."
                ),
            )
            return

        if confidence < self._LOW_CONFIDENCE_THRESHOLD:
            severity = (
                "high" if confidence < self._HIGH_RISK_CONFIDENCE_THRESHOLD else "medium"
            )
            await self._upsert_review_item(
                component,
                status="needs_review",
                severity=severity,
                kind="low_confidence",
                title=f"{component.name} extracted with low confidence",
                summary=(
                    f'The extracted value "{component.value}" still needs human review '
                    "before it should be treated as reliable truth."
                ),
                confidence=confidence,
                rationale=(
                    f"Extractor confidence {confidence:.2f} is below the "
                    f"{self._LOW_CONFIDENCE_THRESHOLD:.2f} review threshold."
                ),
                suggested_action="Confirm the canonical value or supersede this fact.",
            )
            return

        await self._resolve_pending_review_item(component)

    async def _resolve_pending_review_item(self, component: Component) -> None:
        item = await self._get_review_item(component.id)
        if item is None or item.status != "needs_review":
            return
        if item.kind not in {"conflict", "low_confidence"}:
            return

        item.status = "approved"
        item.summary = f"{component.name} no longer requires review."
        item.rationale = (
            "A later ingestion pass resolved the previously flagged trust issue."
        )
        item.suggested_action = "No action needed."
        await self.session.flush()

    async def _supersede_component(
        self,
        component: Component,
        *,
        successor: Component | None,
        reason: str,
        superseded_at: datetime,
    ) -> None:
        if component.valid_to is None:
            component.valid_to = superseded_at
        component.is_stale = True
        if successor is not None:
            component.superseded_by_id = successor.id
            await self._upsert_supersedes_relationship(
                successor,
                component,
                description=reason,
            )
        await self._retire_component_relationships(
            component,
            retired_at=superseded_at,
        )

        await self._upsert_review_item(
            component,
            status="superseded",
            severity="low",
            kind="superseded_fact",
            title=f"{component.name} is now historical",
            summary=(
                f'The fact "{component.value}" has been superseded by a newer extraction.'
                if successor is not None
                else f'The fact "{component.value}" is no longer supported by the source.'
            ),
            confidence=component.confidence,
            rationale=reason,
            suggested_action=(
                "No action needed unless the historical fact is still being cited."
            ),
        )

    async def _retire_if_orphaned(
        self,
        component: Component,
        *,
        reason: str,
        retired_at: datetime,
    ) -> None:
        has_sources = await self.session.scalar(
            select(ComponentSource.component_id)
            .where(ComponentSource.component_id == component.id)
            .limit(1)
        )
        if has_sources is not None:
            return
        await self._supersede_component(
            component,
            successor=None,
            reason=reason,
            superseded_at=retired_at,
        )

    async def _retire_component_relationships(
        self,
        component: Component,
        *,
        retired_at: datetime,
    ) -> None:
        relationships = await self.session.scalars(
            select(Relationship).where(
                Relationship.valid_to.is_(None),
                Relationship.relationship_type != RelationshipType.SUPERSEDES,
                or_(
                    Relationship.source_component_id == component.id,
                    Relationship.target_component_id == component.id,
                ),
            )
        )
        for relationship in relationships:
            relationship.valid_to = retired_at
        await self.session.flush()

    async def _upsert_supersedes_relationship(
        self,
        successor: Component,
        predecessor: Component,
        *,
        description: str,
    ) -> None:
        relationship = await self.session.scalar(
            select(Relationship).where(
                Relationship.source_component_id == successor.id,
                Relationship.target_component_id == predecessor.id,
                Relationship.relationship_type == RelationshipType.SUPERSEDES,
            )
        )
        if relationship is None:
            relationship = Relationship(
                source_component_id=successor.id,
                target_component_id=predecessor.id,
                relationship_type=RelationshipType.SUPERSEDES,
                confidence=1.0,
                description=description,
            )
            self.session.add(relationship)
        else:
            relationship.confidence = 1.0
            relationship.description = description
        await self.session.flush()

    async def _upsert_review_item(
        self,
        component: Component,
        *,
        status: str,
        severity: str,
        kind: str,
        title: str,
        summary: str,
        confidence: float | None,
        rationale: str | None,
        suggested_action: str | None,
    ) -> None:
        item = await self._get_review_item(component.id)
        if item is None:
            item = ReviewItem(
                component_id=component.id,
                status=status,
                severity=severity,
                kind=kind,
                title=title,
                summary=summary,
                confidence=confidence,
                rationale=rationale,
                suggested_action=suggested_action,
            )
            self.session.add(item)
            await self.session.flush()
            return

        if item.status not in {"needs_review", "superseded"} and status == "needs_review":
            return

        item.status = status
        item.severity = severity
        item.kind = kind
        item.title = title
        item.summary = summary
        item.confidence = confidence
        item.rationale = rationale
        item.suggested_action = suggested_action
        await self.session.flush()

    async def _get_review_item(self, component_id: UUID) -> ReviewItem | None:
        return await self.session.scalar(
            select(ReviewItem).where(ReviewItem.component_id == component_id)
        )

    async def _select_active_components(
        self,
        model_id: UUID,
        name: str,
    ) -> list[Component]:
        result = await self.session.scalars(
            select(Component)
            .where(
                Component.model_id == model_id,
                Component.name == name,
                Component.valid_to.is_(None),
            )
            .order_by(Component.valid_from.desc(), Component.id.desc())
        )
        return list(result)

    async def _load_document_links(
        self,
        document_id: UUID,
    ) -> list[tuple[ComponentSource, Component]]:
        rows = await self.session.execute(
            select(ComponentSource, Component)
            .join(Component, ComponentSource.component_id == Component.id)
            .where(ComponentSource.source_document_id == document_id)
        )
        return list(rows.all())

    @staticmethod
    def _collapse_facts(
        facts: list[tuple[str, str, float]],
    ) -> list[tuple[str, str, float]]:
        latest_by_name: dict[str, tuple[str, str, float]] = {}
        for name, value, confidence in facts:
            latest_by_name[name] = (name, value, confidence)
        return list(latest_by_name.values())

    # ── Stub extractor ────────────────────────────────────────────

    @staticmethod
    def _extract_facts(
        doc: SourceDocument,
    ) -> list[tuple[str, str, float]]:
        """Rule-based fact extraction from a SourceDocument.

        Returns a list of (name, value, confidence) tuples.  This is a
        placeholder that extracts obvious patterns; the LLM extractor
        will replace it in a later phase.
        """
        facts: list[tuple[str, str, float]] = []
        content = doc.content
        meta = doc.metadata_json or {}
        channel = meta.get("channel_name", "unknown")

        # Pattern: "decision: <text>" or "decided: <text>"
        for m in re.finditer(
            r"(?:decision|decided)\s*:\s*(.+?)(?:\n|$)", content, re.IGNORECASE
        ):
            facts.append((
                f"Decision in #{channel}",
                m.group(1).strip(),
                0.75,
            ))

        # Pattern: "action item: <text>" or "todo: <text>" or "AI: <text>"
        for m in re.finditer(
            r"(?:action item|todo|AI)\s*:\s*(.+?)(?:\n|$)", content, re.IGNORECASE
        ):
            facts.append((
                f"Action Item in #{channel}",
                m.group(1).strip(),
                0.70,
            ))

        # Pattern: "blocker: <text>" or "blocked by: <text>"
        for m in re.finditer(
            r"(?:blocker|blocked by)\s*:\s*(.+?)(?:\n|$)", content, re.IGNORECASE
        ):
            facts.append((
                f"Blocker in #{channel}",
                m.group(1).strip(),
                0.80,
            ))

        # Fallback: if no structured facts found, create a channel summary
        # entry from messages with thread replies (likely important discussions)
        if not facts and meta.get("reply_count"):
            author = doc.author or "Unknown"
            preview = content[:200].replace("\n", " ")
            facts.append((
                f"Discussion in #{channel}",
                f"{author}: {preview}",
                0.55,
            ))

        return facts
