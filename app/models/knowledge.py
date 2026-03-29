from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from app.models.source import enum_values

if TYPE_CHECKING:
    from app.models.source import SourceDocument
    from app.models.user import Workspace


class KnowledgeModelStatus(str, enum.Enum):
    ACTIVE = "active"
    ARCHIVED = "archived"


class RelationshipType(str, enum.Enum):
    DEPENDS_ON = "depends_on"
    BLOCKED_BY = "blocked_by"
    ENABLES = "enables"
    CONTRADICTS = "contradicts"
    SUPERSEDES = "supersedes"
    RELATED_TO = "related_to"


class RelationshipSentiment(str, enum.Enum):
    POSITIVE = "positive"
    NEGATIVE = "negative"
    NEUTRAL = "neutral"


class KnowledgeModel(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "knowledge_models"
    __table_args__ = (UniqueConstraint("workspace_id", "name"),)

    workspace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[KnowledgeModelStatus] = mapped_column(
        Enum(
            KnowledgeModelStatus,
            name="knowledge_model_status_enum",
            values_callable=enum_values,
        ),
        nullable=False,
        default=KnowledgeModelStatus.ACTIVE,
        server_default=text("'active'"),
    )
    auto_generated: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )

    workspace: Mapped["Workspace"] = orm_relationship(back_populates="knowledge_models")
    components: Mapped[list["Component"]] = orm_relationship(
        back_populates="model",
        cascade="all, delete-orphan",
    )


class Component(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "components"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="components_confidence_range"),
    )

    model_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("knowledge_models.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    authority_source: Mapped[str | None] = mapped_column(String(255), nullable=True)
    last_verified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    is_stale: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        server_default=text("false"),
    )
    embedding: Mapped[list[float] | None] = mapped_column(Vector(1024), nullable=True)

    model: Mapped["KnowledgeModel"] = orm_relationship(back_populates="components")
    outgoing_relationships: Mapped[list["Relationship"]] = orm_relationship(
        back_populates="source_component",
        foreign_keys="Relationship.source_component_id",
        cascade="all, delete-orphan",
    )
    incoming_relationships: Mapped[list["Relationship"]] = orm_relationship(
        back_populates="target_component",
        foreign_keys="Relationship.target_component_id",
        cascade="all, delete-orphan",
    )
    source_links: Mapped[list["ComponentSource"]] = orm_relationship(
        back_populates="component",
        cascade="all, delete-orphan",
    )
    source_documents: Mapped[list["SourceDocument"]] = orm_relationship(
        secondary="component_sources",
        back_populates="components",
        viewonly=True,
    )


class Relationship(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "relationships"
    __table_args__ = (
        CheckConstraint("confidence >= 0 AND confidence <= 1", name="relationships_confidence_range"),
        CheckConstraint(
            "source_component_id <> target_component_id",
            name="relationships_distinct_components",
        ),
    )

    source_component_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("components.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    target_component_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("components.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    relationship_type: Mapped[RelationshipType] = mapped_column(
        Enum(
            RelationshipType,
            name="relationship_type_enum",
            values_callable=enum_values,
        ),
        nullable=False,
    )
    sentiment: Mapped[RelationshipSentiment] = mapped_column(
        Enum(
            RelationshipSentiment,
            name="relationship_sentiment_enum",
            values_callable=enum_values,
        ),
        nullable=False,
        default=RelationshipSentiment.NEUTRAL,
        server_default=text("'neutral'"),
    )
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )

    source_component: Mapped["Component"] = orm_relationship(
        back_populates="outgoing_relationships",
        foreign_keys=[source_component_id],
    )
    target_component: Mapped["Component"] = orm_relationship(
        back_populates="incoming_relationships",
        foreign_keys=[target_component_id],
    )

    @property
    def source_component_name(self) -> str | None:
        if self.source_component is None:
            return None
        return self.source_component.name

    @property
    def target_component_name(self) -> str | None:
        if self.target_component is None:
            return None
        return self.target_component.name


class ComponentSource(Base):
    __tablename__ = "component_sources"

    component_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("components.id", ondelete="CASCADE"),
        primary_key=True,
    )
    source_document_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("source_documents.id", ondelete="CASCADE"),
        primary_key=True,
    )
    extraction_context: Mapped[str | None] = mapped_column(Text, nullable=True)

    component: Mapped["Component"] = orm_relationship(back_populates="source_links")
    source_document: Mapped["SourceDocument"] = orm_relationship(back_populates="component_links")
