from __future__ import annotations

from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge import (
    Component,
    ComponentSource,
    KnowledgeModel,
    Relationship,
    RelationshipType,
)
from app.models.review import ReviewItem
from app.models.user import Workspace
from app.schemas.decision import (
    DecisionHistoryRead,
    DecisionRationaleSourceRead,
    DecisionRead,
)


class DecisionServiceError(Exception):
    """Base decision-register service error."""


class DecisionWorkspaceNotFoundError(DecisionServiceError):
    """Raised when the workspace does not exist."""


class DecisionNotFoundError(DecisionServiceError):
    """Raised when a decision component is missing or out of scope."""


class DecisionService:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_decisions(
        self,
        *,
        workspace_id: UUID,
        include_historical: bool = False,
        limit: int = 50,
    ) -> list[DecisionRead]:
        await self._require_workspace(workspace_id)

        stmt = self._decision_stmt(workspace_id)
        if not include_historical:
            stmt = stmt.where(Component.valid_to.is_(None))

        rows = await self.session.scalars(
            stmt.order_by(
                Component.valid_to.is_not(None).asc(),
                Component.valid_from.desc(),
                Component.id.desc(),
            ).limit(limit)
        )
        return [self._serialize_decision(component) for component in rows]

    async def get_decision_history(
        self,
        *,
        workspace_id: UUID,
        component_id: UUID,
        limit: int = 50,
        cursor: str | None = None,
    ) -> DecisionHistoryRead:
        await self._require_workspace(workspace_id)
        target = await self.session.scalar(
            self._decision_stmt(workspace_id).where(Component.id == component_id)
        )
        if target is None:
            raise DecisionNotFoundError("Decision not found")

        lineage_stmt = self._decision_stmt(workspace_id).where(
            Component.model_id == target.model_id,
            func.lower(Component.name) == target.name.lower(),
        )
        total_versions = int(
            await self.session.scalar(
                select(func.count())
                .select_from(Component)
                .join(KnowledgeModel, Component.model_id == KnowledgeModel.id)
                .where(
                    KnowledgeModel.workspace_id == workspace_id,
                    Component.model_id == target.model_id,
                    func.lower(Component.name) == target.name.lower(),
                    func.lower(Component.name).like("%decision%"),
                )
            )
            or 0
        )
        current = await self.session.scalar(
            self._decision_stmt(workspace_id)
            .where(
                Component.model_id == target.model_id,
                func.lower(Component.name) == target.name.lower(),
                Component.valid_to.is_(None),
            )
            .order_by(Component.valid_from.desc(), Component.id.desc())
        )

        if cursor:
            try:
                cursor_id = UUID(cursor)
                cursor_row = (
                    await self.session.execute(
                        select(Component.valid_from, Component.id).where(
                            Component.id == cursor_id,
                            Component.model_id == target.model_id,
                            func.lower(Component.name) == target.name.lower(),
                        )
                    )
                ).one_or_none()
                if cursor_row is not None:
                    cursor_ts, cursor_uid = cursor_row
                    from sqlalchemy import tuple_

                    lineage_stmt = lineage_stmt.where(
                        tuple_(Component.valid_from, Component.id)
                        < tuple_(cursor_ts, cursor_uid)
                    )
            except ValueError:
                pass

        entries = list(
            await self.session.scalars(
                lineage_stmt.order_by(
                    Component.valid_from.desc(),
                    Component.id.desc(),
                ).limit(limit + 1)
            )
        )
        has_more = len(entries) > limit
        paged_entries = entries[:limit]
        next_cursor = str(paged_entries[-1].id) if has_more and paged_entries else None
        return DecisionHistoryRead(
            workspace_id=workspace_id,
            decision_name=target.name,
            current_decision_id=current.id if current is not None else None,
            total_versions=total_versions,
            has_more=has_more,
            next_cursor=next_cursor,
            entries=[self._serialize_decision(component) for component in paged_entries],
        )

    def _decision_stmt(self, workspace_id: UUID):
        return (
            select(Component)
            .join(KnowledgeModel, Component.model_id == KnowledgeModel.id)
            .options(
                selectinload(Component.model),
                selectinload(Component.review_item).selectinload(ReviewItem.decision_history),
                selectinload(Component.source_links).selectinload(ComponentSource.source_document),
                selectinload(Component.incoming_relationships).selectinload(
                    Relationship.source_component
                ),
            )
            .where(
                KnowledgeModel.workspace_id == workspace_id,
                func.lower(Component.name).like("%decision%"),
            )
        )

    async def _require_workspace(self, workspace_id: UUID) -> None:
        workspace = await self.session.scalar(
            select(Workspace.id).where(Workspace.id == workspace_id).limit(1)
        )
        if workspace is None:
            raise DecisionWorkspaceNotFoundError("Workspace not found")

    @staticmethod
    def _serialize_decision(component: Component) -> DecisionRead:
        model = component.model
        review_item = component.review_item
        rationale_sources = [
            DecisionRationaleSourceRead(
                source_document_id=link.source_document.id,
                label=link.source_document.label,
                connector_type=link.source_document.connector_type.value,
                source_url=link.source_document.source_url,
                author=link.source_document.author,
                created_at_source=link.source_document.created_at_source,
                extraction_context=link.extraction_context,
                extracted_value=link.extracted_value,
                extractor_name=link.extractor_name,
                extractor_kind=link.extractor_kind,
                extractor_schema_version=link.extractor_schema_version,
            )
            for link in sorted(
                component.source_links,
                key=lambda item: (
                    item.source_document.created_at_source or item.source_document.ingested_at
                ),
                reverse=True,
            )
            if link.source_document.deleted_at is None
        ]
        primary_source = rationale_sources[0] if rationale_sources else None
        return DecisionRead(
            id=component.id,
            model_id=component.model_id,
            model_name=model.name if model is not None else "",
            name=component.name,
            value=component.value,
            summary=review_item.summary if review_item is not None else component.value,
            confidence=component.confidence,
            authority_weight=component.authority_weight,
            authority_source=component.authority_source,
            source_document_id=primary_source.source_document_id if primary_source else None,
            source_label=primary_source.label if primary_source else None,
            connector_type=primary_source.connector_type if primary_source else None,
            related_blocker=DecisionService._related_blocker(component),
            review_status=component.review_status,
            review_summary=component.review_summary,
            review_item_id=component.review_item_id,
            valid_from=component.valid_from,
            valid_to=component.valid_to,
            superseded_by=component.superseded_by,
            is_current=component.valid_to is None,
            temporal_state=component.temporal_state,
            decision_history=list(review_item.decision_history) if review_item is not None else [],
            rationale_sources=rationale_sources,
        )

    @staticmethod
    def _related_blocker(component: Component) -> str | None:
        blockers: list[str] = []
        for relationship in component.incoming_relationships:
            if relationship.valid_to is not None:
                continue
            if relationship.relationship_type != RelationshipType.BLOCKED_BY:
                continue
            source_component = relationship.source_component
            if source_component is None or source_component.valid_to is not None:
                continue
            if not source_component.name.lower().startswith("blocker"):
                continue
            blockers.append(source_component.value)
        return blockers[0] if blockers else None
