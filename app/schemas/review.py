"""Schemas for trust/review/provenance endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict


ReviewStatus = Literal["needs_review", "approved", "rejected", "superseded"]
ReviewSeverity = Literal["high", "medium", "low"]
ReviewKind = Literal[
    "review_item",
    "conflict",
    "low_confidence",
    "fact_update",
    "superseded_fact",
]


class ReviewItemSourceDocumentRead(BaseModel):
    id: UUID
    label: str
    connector_type: str


class ReviewDecisionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    previous_status: str | None
    new_status: str
    actor_type: str
    note: str | None
    created_at: datetime


class ReviewItemRead(BaseModel):
    id: UUID
    status: str
    severity: str
    kind: str
    title: str
    summary: str
    confidence: float | None
    last_seen_at: datetime
    model_id: UUID | None
    model_name: str | None
    sources: list[str]
    source_documents: list[ReviewItemSourceDocumentRead]
    rationale: str | None
    suggested_action: str | None
    decision_history: list[ReviewDecisionRead] = []


class ComponentSourceRead(BaseModel):
    id: UUID
    connector_type: str
    external_id: str
    label: str
    author: str | None
    source_url: str | None
    created_at_source: datetime | None
    ingested_at: datetime
    processed_at: datetime | None
    deleted_at: datetime | None
    extraction_context: str | None
    extractor_name: str | None = None
    extractor_kind: str | None = None
    extractor_schema_version: str | None = None


class SourceDocumentComponentRead(BaseModel):
    id: UUID
    model_id: UUID
    model_name: str
    name: str
    value: str
    confidence: float
    valid_from: datetime | None = None
    valid_to: datetime | None = None
    superseded_by: UUID | None = None
    review_status: str | None
    review_item_id: UUID | None
    review_summary: str | None = None
    decision_history: list[ReviewDecisionRead] = []
    temporal_state: str | None
