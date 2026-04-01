"""Pydantic schemas for connector endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, field_validator


class ConnectorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    connector_type: str
    status: str
    last_sync_at: datetime | None
    config: dict[str, Any]
    provider: str | None = None
    provider_label: str | None = None
    provider_note: str | None = None


class ConnectorSyncResponse(BaseModel):
    id: UUID
    status: str
    message: str
    last_sync_at: datetime | None


class SyncJobResponse(BaseModel):
    """Returned immediately when a sync is dispatched (202 Accepted)."""

    job_id: UUID
    job_type: str
    connector_id: UUID
    status: str
    created_at: datetime


class SyncJobDetail(BaseModel):
    """Full job state returned by the sync-status and sync-jobs endpoints."""

    model_config = ConfigDict(from_attributes=True)

    job_id: UUID
    job_type: str
    connector_id: UUID
    status: str
    started_at: datetime | None
    completed_at: datetime | None
    error_type: str | None
    error_message: str | None
    result_metadata: dict[Any, Any]
    created_at: datetime


class SlackInstallResponse(BaseModel):
    redirect_url: str


class NotionConnectRequest(BaseModel):
    workspace_id: UUID
    token: str

    @field_validator("token")
    @classmethod
    def token_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Notion integration token must not be blank")
        return v


class ZoomConnectRequest(BaseModel):
    workspace_id: UUID
    token: str

    @field_validator("token")
    @classmethod
    def token_not_blank(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Zoom access token must not be blank")
        return v


class ConnectorProcessingSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    connector_id: UUID
    connector_type: str
    status: str
    total_documents: int
    processed_documents: int
    unprocessed_documents: int
    last_sync_at: datetime | None
