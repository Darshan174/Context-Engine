from __future__ import annotations

import secrets
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db_session
from app.schemas.eval import EvalCasesRead, EvalRunRequest, EvalSummaryRead
from app.services.eval_service import (
    EvalRequestError,
    EvalService,
    EvalWorkspaceNotFoundError,
)


router = APIRouter()


def get_eval_service(session: AsyncSession = Depends(get_db_session)) -> EvalService:
    return EvalService(session)


def _is_local_request(request: Request) -> bool:
    forwarded_for = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
    if forwarded_for:
        host = forwarded_for
    else:
        host = request.client.host if request.client is not None else ""
    return host in {"127.0.0.1", "::1", "localhost", "testclient"}


def require_eval_admin(
    request: Request,
    admin_token: str | None = Header(default=None, alias="X-Eval-Admin-Token"),
) -> None:
    if settings.environment == "test":
        return
    if settings.eval_allow_local_requests and _is_local_request(request):
        return
    if (
        settings.eval_admin_token
        and admin_token
        and secrets.compare_digest(admin_token, settings.eval_admin_token)
    ):
        return
    raise HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Eval runs are restricted to local/admin access",
    )


@router.get("/evals/summary", response_model=EvalSummaryRead)
async def get_eval_summary(
    workspace_id: UUID,
    service: EvalService = Depends(get_eval_service),
) -> EvalSummaryRead:
    try:
        return await service.get_summary_payload(workspace_id)
    except EvalWorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.get("/evals/cases", response_model=EvalCasesRead)
async def get_eval_cases(
    workspace_id: UUID,
    domain: str | None = Query(default=None),
    service: EvalService = Depends(get_eval_service),
) -> EvalCasesRead:
    try:
        return await service.get_cases_payload(workspace_id, domain=domain)
    except EvalWorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc


@router.post(
    "/evals/run",
    response_model=EvalCasesRead,
    dependencies=[Depends(require_eval_admin)],
)
async def run_evals(
    payload: EvalRunRequest,
    service: EvalService = Depends(get_eval_service),
) -> EvalCasesRead:
    try:
        await service.run_latest(
            workspace_id=payload.workspace_id,
            domains=payload.domains,
            case_ids=payload.case_ids,
            pass_threshold=payload.pass_threshold,
        )
        return await service.get_cases_payload(payload.workspace_id)
    except EvalWorkspaceNotFoundError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc)) from exc
    except EvalRequestError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
