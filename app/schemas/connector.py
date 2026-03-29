"""Pydantic schemas for connector endpoints."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class ConnectorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    workspace_id: UUID
    connector_type: str
    status: str
    last_sync_at: datetime | None
    config: dict[str, Any]


class ConnectorSyncResponse(BaseModel):
    id: UUID
    status: str
    message: str
    last_sync_at: datetime | None


class SlackInstallResponse(BaseModel):
    redirect_url: str
