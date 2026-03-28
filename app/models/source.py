from __future__ import annotations

import enum
from datetime import datetime
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, String, Text, UniqueConstraint, func, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship as orm_relationship

from app.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from app.models.knowledge import Component, ComponentSource


class ConnectorType(str, enum.Enum):
    SLACK = "slack"
    NOTION = "notion"
    GDRIVE = "gdrive"
    GONG = "gong"


def enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    return [member.value for member in enum_cls]


class SourceDocument(UUIDPrimaryKeyMixin, Base):
    __tablename__ = "source_documents"
    __table_args__ = (UniqueConstraint("connector_type", "external_id"),)

    connector_type: Mapped[ConnectorType] = mapped_column(
        Enum(
            ConnectorType,
            name="connector_type_enum",
            values_callable=enum_values,
        ),
        nullable=False,
        index=True,
    )
    external_id: Mapped[str] = mapped_column(String(255), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    author: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str | None] = mapped_column(String(2048), nullable=True)
    created_at_source: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
    )
    metadata_json: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
        server_default=text("'{}'::jsonb"),
    )

    component_links: Mapped[list["ComponentSource"]] = orm_relationship(
        back_populates="source_document",
        cascade="all, delete-orphan",
    )
    components: Mapped[list["Component"]] = orm_relationship(
        secondary="component_sources",
        back_populates="source_documents",
        viewonly=True,
    )
