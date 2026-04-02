from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field

from app.schemas.review import ReviewDecisionRead


class DecisionRationaleSourceRead(BaseModel):
    source_document_id: UUID
    label: str
    connector_type: str
    source_url: str | None = None
    author: str | None = None
    created_at_source: datetime | None = None
    extraction_context: str | None = None
    extracted_value: str | None = None
    extractor_name: str | None = None
    extractor_kind: str | None = None
    extractor_schema_version: str | None = None


class DecisionRead(BaseModel):
    id: UUID
    model_id: UUID
    model_name: str
    name: str
    value: str
    summary: str
    confidence: float
    authority_weight: float
    authority_source: str | None = None
    source_document_id: UUID | None = None
    source_label: str | None = None
    connector_type: str | None = None
    related_blocker: str | None = None
    review_status: str | None = None
    review_summary: str | None = None
    review_item_id: UUID | None = None
    valid_from: datetime
    valid_to: datetime | None = None
    superseded_by: UUID | None = None
    is_current: bool
    temporal_state: str | None = None
    decision_history: list[ReviewDecisionRead] = []
    rationale_sources: list[DecisionRationaleSourceRead] = []


class DecisionHistoryRead(BaseModel):
    workspace_id: UUID
    decision_name: str
    current_decision_id: UUID | None = None
    total_versions: int = 0
    has_more: bool = False
    next_cursor: str | None = None
    entries: list[DecisionRead] = Field(default_factory=list)
