from __future__ import annotations

from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.connector import Connector
    from app.models.knowledge import KnowledgeModel


class Workspace(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "workspaces"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    knowledge_models: Mapped[list["KnowledgeModel"]] = orm_relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    connectors: Mapped[list["Connector"]] = orm_relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )
    users: Mapped[list["User"]] = orm_relationship(
        back_populates="workspace",
        cascade="all, delete-orphan",
    )


class User(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    __tablename__ = "users"
    __table_args__ = (UniqueConstraint("workspace_id", "email"),)

    workspace_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("workspaces.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    full_name: Mapped[str | None] = mapped_column(String(255), nullable=True)

    workspace: Mapped["Workspace"] = orm_relationship(back_populates="users")
