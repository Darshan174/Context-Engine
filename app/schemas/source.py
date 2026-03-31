"""Pydantic schemas for source document endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class SourceDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    connector_id: UUID
    connector_type: str
    external_id: str
    content: str
    author: str | None
    source_url: str | None
    created_at_source: datetime | None
    ingested_at: datetime
    processed_at: datetime | None
    metadata: dict[str, Any]


class SourceDocumentList(BaseModel):
    items: list[SourceDocumentRead]
    total: int
    has_more: bool
    next_cursor: str | None = None
