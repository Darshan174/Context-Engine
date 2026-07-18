from __future__ import annotations

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field, field_validator
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.api.dependencies import get_access_scope
from app.database import get_db_session
from app.models import CodeFile, Component, SourceDocument, Workspace
from app.services.access import AccessScope, source_access_predicate
from app.services.focus_policy import focus_eligibility
from app.services.agent_adapters import adapter_spec, detect_agent_adapters
from app.services.context_compiler import (
    ContextBudgetExceededError,
    ContextCompiler,
    ContextPersistenceError,
    FocusValidationError,
    InvalidGoalError,
    InvalidRepoPathError,
)
from app.services.workspace_scope import metadata_dict
from app.services.workspace_goals import (
    build_work_contract,
    clear_workspace_goal,
    complete_workspace_goal,
    goal_to_dict,
    select_workspace_goal,
    WorkspaceGoalCompletionError,
)


router = APIRouter()


class WorkspaceGoalSelect(BaseModel):
    title: str = Field(min_length=3, max_length=2000)
    component_id: UUID | None = None
    source_kind: Literal["user_selected", "suggested_card"] = "user_selected"
    source_id: str | None = Field(default=None, max_length=255)

    @field_validator("title")
    @classmethod
    def normalize_title(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 3:
            raise ValueError("title must contain at least 3 visible characters")
        return normalized


class WorkspaceGoalComplete(BaseModel):
    run_id: UUID


class WorkSessionStart(BaseModel):
    objective: str = Field(min_length=3, max_length=2000)
    definition_of_done: list[str] = Field(default_factory=list, max_length=8)
    component_id: UUID | None = None
    source_kind: Literal["user_selected", "suggested_card"] = "user_selected"
    source_id: str | None = Field(default=None, max_length=255)
    adapter_id: Literal["codex", "claude_code", "opencode"]
    target_model: str | None = Field(default=None, max_length=255)
    token_budget: int = Field(default=4000, ge=300, le=200000)

    @field_validator("objective")
    @classmethod
    def normalize_objective(cls, value: str) -> str:
        normalized = " ".join(value.split())
        if len(normalized) < 3:
            raise ValueError("objective must contain at least 3 visible characters")
        return normalized

    @field_validator("definition_of_done")
    @classmethod
    def normalize_definition_of_done(cls, values: list[str]) -> list[str]:
        normalized = []
        for raw in values:
            value = " ".join(str(raw or "").split())
            if not value:
                continue
            if len(value) > 500:
                raise ValueError("each definition-of-done item must be 500 characters or less")
            if value not in normalized:
                normalized.append(value)
        return normalized


async def _require_workspace(
    session: AsyncSession,
    workspace_id: UUID,
    access_scope: AccessScope,
) -> Workspace:
    if not access_scope.allows_workspace(workspace_id):
        raise HTTPException(status_code=404, detail="Workspace not found")
    workspace = await session.get(Workspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return workspace


async def _require_goal_component(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    component_id: UUID | None,
    access_scope: AccessScope,
) -> Component | None:
    if component_id is None:
        return None
    component = await session.scalar(
        select(Component)
        .options(selectinload(Component.source_document))
        .join(SourceDocument, Component.source_document_id == SourceDocument.id)
        .where(
            Component.id == component_id,
            Component.workspace_id == workspace_id,
            source_access_predicate(access_scope, workspace_id=workspace_id),
        )
    )
    if component is None:
        raise HTTPException(status_code=404, detail="Goal component not found")
    eligible, reason = focus_eligibility(
        component.fact_type,
        component.status,
        provider_state=(
            str(metadata_dict(component.source_document).get("state") or "")
            if component.source_document is not None
            else None
        ),
    )
    if not eligible:
        raise HTTPException(status_code=422, detail=reason)
    return component


async def _workspace_repo_path(
    session: AsyncSession,
    *,
    workspace_id: UUID,
) -> str | None:
    return await session.scalar(
        select(CodeFile.repo_root)
        .where(
            CodeFile.workspace_id == workspace_id,
            CodeFile.repo_root.is_not(None),
        )
        .order_by(CodeFile.updated_at.desc(), CodeFile.id.desc())
        .limit(1)
    )


@router.put("/workspaces/{workspace_id}/current-goal")
async def set_current_goal(
    workspace_id: UUID,
    payload: WorkspaceGoalSelect,
    session: AsyncSession = Depends(get_db_session),
    access_scope: AccessScope = Depends(get_access_scope),
) -> dict:
    await _require_workspace(session, workspace_id, access_scope)
    await _require_goal_component(
        session,
        workspace_id=workspace_id,
        component_id=payload.component_id,
        access_scope=access_scope,
    )
    goal = await select_workspace_goal(
        session,
        workspace_id=workspace_id,
        title=payload.title,
        component_id=payload.component_id,
        source_kind=payload.source_kind,
        source_id=payload.source_id,
        selected_by=access_scope.principal_id,
    )
    await session.commit()
    return goal_to_dict(goal)


@router.get("/workspaces/{workspace_id}/agent-adapters")
async def get_agent_adapters(
    workspace_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    access_scope: AccessScope = Depends(get_access_scope),
) -> dict:
    await _require_workspace(session, workspace_id, access_scope)
    return {
        "workspace_id": str(workspace_id),
        "items": await detect_agent_adapters(),
    }


@router.post("/workspaces/{workspace_id}/work-session")
async def start_work_session(
    workspace_id: UUID,
    payload: WorkSessionStart,
    session: AsyncSession = Depends(get_db_session),
    access_scope: AccessScope = Depends(get_access_scope),
) -> dict:
    await _require_workspace(session, workspace_id, access_scope)
    await _require_goal_component(
        session,
        workspace_id=workspace_id,
        component_id=payload.component_id,
        access_scope=access_scope,
    )
    adapter_spec(payload.adapter_id)
    contract = build_work_contract(
        objective=payload.objective,
        definition_of_done=payload.definition_of_done,
        adapter_id=payload.adapter_id,
        target_model=payload.target_model,
        token_budget=payload.token_budget,
    )
    try:
        goal = await select_workspace_goal(
            session,
            workspace_id=workspace_id,
            title=payload.objective,
            component_id=payload.component_id,
            source_kind=payload.source_kind,
            source_id=payload.source_id,
            selected_by=access_scope.principal_id,
            work_contract=contract,
        )
        result = await ContextCompiler(session).compile_context_pack(
            payload.objective,
            workspace_id=workspace_id,
            repo_path=await _workspace_repo_path(
                session,
                workspace_id=workspace_id,
            ),
            target_model=payload.target_model,
            token_budget=payload.token_budget,
            persist=True,
            focus_component_id=payload.component_id,
            workspace_goal_id=goal.id,
            objective_origin="trusted_human",
            work_contract=contract,
            access_scope=access_scope,
        )
        await session.commit()
    except ContextBudgetExceededError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=422,
            detail={
                "code": "context_budget_too_small",
                "message": str(exc),
                "minimum_required_tokens": exc.minimum_required_tokens,
            },
        ) from exc
    except FocusValidationError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=exc.status_code,
            detail={"code": exc.code, "message": str(exc)},
        ) from exc
    except (InvalidGoalError, InvalidRepoPathError, ValueError) as exc:
        await session.rollback()
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ContextPersistenceError as exc:
        await session.rollback()
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not result.context_pack_id:
        raise HTTPException(status_code=500, detail="Context pack was not persisted")
    return {
        "goal": goal_to_dict(goal),
        "pack": {
            "context_pack_id": result.context_pack_id,
            "schema_version": result.schema_version,
            "workspace_id": str(workspace_id),
            "workspace_goal_id": str(goal.id),
            "objective": payload.objective,
            "markdown": result.markdown,
            "manifest": result.manifest,
            "health_score": result.health_score,
            "selected_context": result.selected_items,
            "excluded_context": result.excluded_items,
            "focus": dict(result.manifest.get("focus") or {}),
        },
    }


@router.delete("/workspaces/{workspace_id}/current-goal", status_code=204)
async def delete_current_goal(
    workspace_id: UUID,
    session: AsyncSession = Depends(get_db_session),
    access_scope: AccessScope = Depends(get_access_scope),
) -> Response:
    await _require_workspace(session, workspace_id, access_scope)
    await clear_workspace_goal(session, workspace_id=workspace_id)
    await session.commit()
    return Response(status_code=204)


@router.post("/workspaces/{workspace_id}/current-goal/complete")
async def complete_current_goal(
    workspace_id: UUID,
    payload: WorkspaceGoalComplete,
    session: AsyncSession = Depends(get_db_session),
    access_scope: AccessScope = Depends(get_access_scope),
) -> dict:
    await _require_workspace(session, workspace_id, access_scope)
    try:
        goal = await complete_workspace_goal(
            session,
            workspace_id=workspace_id,
            run_id=payload.run_id,
        )
        await session.commit()
    except WorkspaceGoalCompletionError as exc:
        await session.rollback()
        raise HTTPException(status_code=409, detail=str(exc)) from exc
    return goal_to_dict(goal)
