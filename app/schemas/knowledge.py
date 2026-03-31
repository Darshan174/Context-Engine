from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.knowledge import (
    KnowledgeModelStatus,
    RelationshipSentiment,
    RelationshipType,
)


class KnowledgeModelCreate(BaseModel):
    workspace_id: UUID
    name: str = Field(min_length=1, max_length=255)
    description: str | None = None
    status: KnowledgeModelStatus = KnowledgeModelStatus.ACTIVE
    auto_generated: bool = False


class ComponentCreate(BaseModel):
    name: str = Field(min_length=1, max_length=255)
    value: str = Field(min_length=1)
    confidence: float = Field(ge=0.0, le=1.0)
    authority_source: str | None = Field(default=None, max_length=255)
    last_verified_at: datetime | None = None
    is_stale: bool = False


class ComponentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=255)
    value: str | None = Field(default=None, min_length=1)
    confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    authority_source: str | None = Field(default=None, max_length=255)
    last_verified_at: datetime | None = None
    is_stale: bool | None = None


class RelationshipCreate(BaseModel):
    source_component_id: UUID
    target_component_id: UUID
    relationship_type: RelationshipType
    sentiment: RelationshipSentiment = RelationshipSentiment.NEUTRAL
    description: str | None = None
    confidence: float = Field(ge=0.0, le=1.0)


class ComponentSourceDocumentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    label: str
    connector_type: str


class ComponentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    model_id: UUID
    name: str
    value: str
    confidence: float
    authority_source: str | None
    valid_from: datetime
    valid_to: datetime | None
    superseded_by: UUID | None = None
    last_verified_at: datetime
    is_stale: bool
    review_status: str | None = None
    review_summary: str | None = None
    review_item_id: UUID | None = None
    temporal_state: str | None = None
    source_documents: list[ComponentSourceDocumentRead] = []
    created_at: datetime
    updated_at: datetime


class KnowledgeModelRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    name: str
    description: str | None
    status: KnowledgeModelStatus
    auto_generated: bool
    created_at: datetime
    updated_at: datetime


class KnowledgeModelDetail(KnowledgeModelRead):
    components: list[ComponentRead]


class RelationshipRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    source_component_id: UUID
    source_component_name: str | None = None
    target_component_id: UUID
    target_component_name: str | None = None
    relationship_type: RelationshipType
    sentiment: RelationshipSentiment
    description: str | None
    confidence: float
    valid_from: datetime
    valid_to: datetime | None = None
    superseded_by: UUID | None = None
    temporal_state: str | None = None
    created_at: datetime
