from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query as FastAPIQuery, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_session
from app.schemas.query import QueryFilters, QueryRequest, QueryResult
from app.services.query_service import QueryResourceNotFoundError, QueryService


router = APIRouter()


def get_query_service(session: AsyncSession = Depends(get_db_session)) -> QueryService:
    return QueryService(session)


@router.get("/query", response_model=QueryResult)
async def query_context(
    q: str = FastAPIQuery(..., min_length=1),
    workspace_id: UUID = FastAPIQuery(...),
    models: list[str] | None = FastAPIQuery(default=None),
    min_confidence: float = FastAPIQuery(default=0.5, ge=0.0, le=1.0),
    max_age_days: int | None = FastAPIQuery(default=None, ge=0),
    as_of: datetime | None = FastAPIQuery(default=None),
    service: QueryService = Depends(get_query_service),
) -> QueryResult:
    try:
        return await service.query(
            question=q,
            workspace_id=workspace_id,
            filters=QueryFilters(
                model_names=models,
                min_confidence=min_confidence,
                max_age_days=max_age_days,
                as_of=as_of,
            ),
        )
    except QueryResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post("/query", response_model=QueryResult)
async def query_context_post(
    payload: QueryRequest,
    service: QueryService = Depends(get_query_service),
) -> QueryResult:
    try:
        return await service.query(
            question=payload.question,
            workspace_id=payload.workspace_id,
            filters=payload.to_filters(),
        )
    except QueryResourceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
