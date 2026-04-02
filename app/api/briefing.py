from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.briefing import (
    FounderBriefRead,
    LaunchGuardRead,
    LaunchGuardRequest,
    TimelineRead,
)
from app.services.briefing_service import BriefingService, BriefingWorkspaceNotFoundError


router = APIRouter()


def get_briefing_service(session: AsyncSession = Depends(get_db_session)) -> BriefingService:
    return BriefingService(session)


@router.get("/founder-brief", response_model=FounderBriefRead)
async def get_founder_brief(
    workspace_id: UUID,
    lookback_days: int = Query(default=7, ge=1, le=90),
    service: BriefingService = Depends(get_briefing_service),
) -> FounderBriefRead:
    try:
        return await service.build_founder_brief(
            workspace_id=workspace_id,
            lookback_days=lookback_days,
        )
    except BriefingWorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/timeline", response_model=TimelineRead)
async def get_timeline(
    workspace_id: UUID,
    limit: int = Query(default=50, ge=1, le=200),
    cursor: str | None = Query(default=None),
    service: BriefingService = Depends(get_briefing_service),
) -> TimelineRead:
    try:
        return await service.build_timeline(
            workspace_id=workspace_id,
            limit=limit,
            cursor=cursor,
        )
    except BriefingWorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/launch-guard/check", response_model=LaunchGuardRead)
async def run_launch_guard(
    payload: LaunchGuardRequest,
    service: BriefingService = Depends(get_briefing_service),
) -> LaunchGuardRead:
    try:
        return await service.run_launch_guard(
            workspace_id=payload.workspace_id,
            draft=payload.draft,
        )
    except BriefingWorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
