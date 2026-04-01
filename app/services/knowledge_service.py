from __future__ import annotations

from uuid import UUID

from sqlalchemy import Select, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.knowledge import Component, ComponentSource, KnowledgeModel, Relationship
from app.models.review import ReviewItem
from app.models.user import Workspace
from app.processing.embedder import BaseEmbedder, build_default_embedder


class KnowledgeServiceError(Exception):
    """Base knowledge service error."""


class ResourceNotFoundError(KnowledgeServiceError):
    """Raised when a requested record is not present."""


class ResourceConflictError(KnowledgeServiceError):
    """Raised when a write violates a uniqueness or integrity rule."""


class InvalidRequestError(KnowledgeServiceError):
    """Raised when a request is semantically invalid."""


class KnowledgeService:
    def __init__(
        self,
        session: AsyncSession,
        *,
        embedder: BaseEmbedder | None = None,
    ) -> None:
        self.session = session
        self._embedder = embedder or build_default_embedder()

    async def create_model(self, **payload: object) -> KnowledgeModel:
        workspace_id = payload["workspace_id"]
        if not await self._workspace_exists(workspace_id):
            raise ResourceNotFoundError("Workspace not found")

        knowledge_model = KnowledgeModel(**payload)
        self.session.add(knowledge_model)
        await self._commit_or_raise(
            "A knowledge model with this name already exists in the workspace"
        )
        await self.session.refresh(knowledge_model)
        return knowledge_model

    async def list_models_for_workspace(self, workspace_id: UUID) -> list[KnowledgeModel]:
        if not await self._workspace_exists(workspace_id):
            raise ResourceNotFoundError("Workspace not found")

        result = await self.session.scalars(
            select(KnowledgeModel)
            .where(KnowledgeModel.workspace_id == workspace_id)
            .order_by(KnowledgeModel.name.asc())
        )
        return list(result)

    async def get_model(self, model_id: UUID) -> KnowledgeModel:
        result = await self.session.scalar(self._model_select(model_id))
        if result is None:
            raise ResourceNotFoundError("Knowledge model not found")
        return result

    async def get_component(self, component_id: UUID) -> Component:
        component = await self.session.scalar(
            select(Component)
            .options(
                selectinload(Component.source_documents),
                selectinload(Component.review_item).selectinload(ReviewItem.decision_history),
                selectinload(Component.model),
            )
            .where(Component.id == component_id)
        )
        if component is None:
            raise ResourceNotFoundError("Component not found")
        return component

    async def add_component(self, model_id: UUID, **payload: object) -> Component:
        model = await self.get_model(model_id)
        payload.setdefault(
            "embedding",
            await self._embedder.embed_text(
                f"{payload['name']}\n{payload['value']}"
            ),
        )
        component = Component(model_id=model.id, **payload)
        self.session.add(component)
        await self._commit_or_raise("Unable to create component with the provided data")
        return await self.get_component(component.id)

    async def update_component(self, component_id: UUID, **payload: object) -> Component:
        component = await self._get_component(component_id)
        should_refresh_embedding = "name" in payload or "value" in payload
        for field, value in payload.items():
            setattr(component, field, value)
        if should_refresh_embedding:
            component.embedding = await self._embedder.embed_text(
                f"{component.name}\n{component.value}"
            )

        await self._commit_or_raise("Unable to update component with the provided data")
        return await self.get_component(component.id)

    async def delete_component(self, component_id: UUID) -> None:
        component = await self._get_component(component_id)
        await self.session.delete(component)
        await self.session.commit()

    async def create_relationship(self, **payload: object) -> Relationship:
        source_component_id = payload["source_component_id"]
        target_component_id = payload["target_component_id"]
        if source_component_id == target_component_id:
            raise InvalidRequestError("A relationship must connect two different components")

        await self._get_component(source_component_id)
        await self._get_component(target_component_id)

        relationship = Relationship(**payload)
        self.session.add(relationship)
        await self._commit_or_raise("Unable to create relationship with the provided data")
        return await self._get_relationship(relationship.id)

    async def get_model_relationships(self, model_id: UUID) -> list[Relationship]:
        await self.get_model(model_id)
        component_ids = select(Component.id).where(Component.model_id == model_id)

        result = await self.session.scalars(
            select(Relationship)
            .options(
                selectinload(Relationship.source_component),
                selectinload(Relationship.target_component),
            )
            .where(
                or_(
                    Relationship.source_component_id.in_(component_ids),
                    Relationship.target_component_id.in_(component_ids),
                )
            )
            .order_by(Relationship.created_at.desc())
        )
        return list(result)

    async def get_component_sources(self, component_id: UUID) -> list[ComponentSource]:
        """Return ComponentSource rows (with source_document loaded) for a component."""
        await self._get_component(component_id)  # raises if missing
        result = await self.session.scalars(
            select(ComponentSource)
            .options(selectinload(ComponentSource.source_document))
            .where(ComponentSource.component_id == component_id)
        )
        return list(result)

    async def get_component_relationships(self, component_id: UUID) -> list[Relationship]:
        await self._get_component(component_id)
        result = await self.session.scalars(
            select(Relationship)
            .options(
                selectinload(Relationship.source_component),
                selectinload(Relationship.target_component),
            )
            .where(
                or_(
                    Relationship.source_component_id == component_id,
                    Relationship.target_component_id == component_id,
                )
            )
            .order_by(Relationship.created_at.desc())
        )
        return list(result)

    async def _get_relationship(self, relationship_id: UUID) -> Relationship:
        relationship = await self.session.scalar(
            select(Relationship)
            .options(
                selectinload(Relationship.source_component),
                selectinload(Relationship.target_component),
            )
            .where(Relationship.id == relationship_id)
        )
        if relationship is None:
            raise ResourceNotFoundError("Relationship not found")
        return relationship

    def _model_select(self, model_id: UUID) -> Select[tuple[KnowledgeModel]]:
        return (
            select(KnowledgeModel)
            .options(
                selectinload(KnowledgeModel.components).selectinload(Component.source_documents),
                selectinload(KnowledgeModel.components)
                .selectinload(Component.review_item)
                .selectinload(ReviewItem.decision_history),
            )
            .where(KnowledgeModel.id == model_id)
        )

    async def _workspace_exists(self, workspace_id: UUID) -> bool:
        return (
            await self.session.scalar(
                select(Workspace.id).where(Workspace.id == workspace_id).limit(1)
            )
            is not None
        )

    async def _get_component(self, component_id: UUID) -> Component:
        component = await self.session.scalar(
            select(Component).where(Component.id == component_id)
        )
        if component is None:
            raise ResourceNotFoundError("Component not found")
        return component

    async def _commit_or_raise(self, message: str) -> None:
        try:
            await self.session.commit()
        except IntegrityError as exc:
            await self.session.rollback()
            raise ResourceConflictError(message) from exc
