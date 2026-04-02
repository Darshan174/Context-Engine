from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.decision import DecisionHistoryRead, DecisionRead
from app.services.decision_service import (
    DecisionNotFoundError,
    DecisionService,
    DecisionWorkspaceNotFoundError,
)


router = APIRouter()


def get_decision_service(session: AsyncSession = Depends(get_db_session)) -> DecisionService:
    return DecisionService(session)


@router.get("/decisions", response_model=list[DecisionRead])
async def list_decisions(
    workspace_id: UUID,
    include_historical: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    service: DecisionService = Depends(get_decision_service),
) -> list[DecisionRead]:
    try:
        return await service.list_decisions(
            workspace_id=workspace_id,
            include_historical=include_historical,
            limit=limit,
        )
    except DecisionWorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/decisions/{component_id}/history", response_model=DecisionHistoryRead)
async def get_decision_history(
    component_id: UUID,
    workspace_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    service: DecisionService = Depends(get_decision_service),
) -> DecisionHistoryRead:
    try:
        return await service.get_decision_history(
            workspace_id=workspace_id,
            component_id=component_id,
            limit=limit,
            cursor=cursor,
        )
    except DecisionWorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except DecisionNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
