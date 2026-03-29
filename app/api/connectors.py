"""Connector management endpoints."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.connector import ConnectorRead, ConnectorSyncResponse
from app.services.connector_service import (
    ConfigurationError,
    ConnectorNotFoundError,
    ConnectorService,
    InvalidStateError,
    OAuthError,
    WorkspaceNotFoundError,
)


router = APIRouter()


def _service(session: AsyncSession = Depends(get_db_session)) -> ConnectorService:
    return ConnectorService(session)


@router.get("/connectors", response_model=list[ConnectorRead])
async def list_connectors(
    workspace_id: UUID,
    svc: ConnectorService = Depends(_service),
) -> list[ConnectorRead]:
    try:
        connectors = await svc.list_connectors(workspace_id)
    except WorkspaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    return [ConnectorRead.model_validate(c) for c in connectors]


@router.get("/connectors/slack/install")
async def slack_install(
    workspace_id: UUID,
    svc: ConnectorService = Depends(_service),
):
    try:
        await svc._require_workspace(workspace_id)
    except WorkspaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )

    try:
        url = await svc.build_slack_install_url(workspace_id)
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        )

    return RedirectResponse(url=url, status_code=status.HTTP_302_FOUND)


@router.get("/connectors/slack/callback", response_model=ConnectorRead)
async def slack_callback(
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    svc: ConnectorService = Depends(_service),
) -> ConnectorRead:
    try:
        connector = await svc.handle_slack_callback(
            code=code, state=state, error=error
        )
    except InvalidStateError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        )
    except OAuthError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        )
    except WorkspaceNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Workspace not found",
        )
    except ConfigurationError as exc:
        raise HTTPException(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            detail=str(exc),
        )

    return ConnectorRead.model_validate(connector)


@router.post(
    "/connectors/{connector_id}/sync",
    response_model=ConnectorSyncResponse,
)
async def sync_connector(
    connector_id: UUID,
    svc: ConnectorService = Depends(_service),
) -> ConnectorSyncResponse:
    try:
        connector = await svc.queue_sync(connector_id)
    except ConnectorNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found",
        )
    return ConnectorSyncResponse(
        id=connector.id,
        status="queued",
        message="Sync queued (placeholder — real Celery dispatch in a later phase)",
        last_sync_at=connector.last_sync_at,
    )


@router.delete(
    "/connectors/{connector_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
async def disconnect_connector(
    connector_id: UUID,
    svc: ConnectorService = Depends(_service),
) -> None:
    try:
        await svc.disconnect(connector_id)
    except ConnectorNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Connector not found",
        )
