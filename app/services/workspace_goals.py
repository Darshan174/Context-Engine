from __future__ import annotations

import json
from datetime import datetime
from typing import Any, Mapping, Sequence
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import AgentRun, ContextPack, WorkspaceGoal
from app.services.harness_outcomes import HarnessOutcomeService
from app.time import utc_now


ACTIVE_RUN_STATUSES = frozenset({"queued", "running", "in_progress"})


class WorkspaceGoalCompletionError(ValueError):
    pass


WORK_SESSION_SCHEMA_VERSION = "work_session.v1"


def goal_to_dict(goal: WorkspaceGoal) -> dict:
    contract = workspace_goal_contract(goal)
    return {
        "id": str(goal.id),
        "workspace_id": str(goal.workspace_id),
        "title": goal.title,
        "component_id": str(goal.component_id) if goal.component_id else None,
        "source_kind": goal.source_kind,
        "source_id": goal.source_id,
        "work_contract": contract,
        "selected_by": goal.selected_by,
        "selected_at": goal.selected_at,
        "status": goal.status,
        "ended_at": goal.ended_at,
        "can_clear": goal.status == "active",
    }


def build_work_contract(
    *,
    objective: str,
    definition_of_done: Sequence[str] | None = None,
    adapter_id: str | None = None,
    target_model: str | None = None,
    token_budget: int | None = None,
) -> dict[str, Any]:
    normalized_objective = " ".join(str(objective or "").split())
    criteria = []
    for raw in definition_of_done or []:
        value = " ".join(str(raw or "").split())
        if value and value not in criteria:
            criteria.append(value)
    model = " ".join(str(target_model or "").split()) or None
    return {
        "schema_version": WORK_SESSION_SCHEMA_VERSION,
        "objective": normalized_objective,
        "definition_of_done": criteria,
        "agent": {
            "adapter_id": adapter_id,
            "target_model": model,
            "model_identity_source": (
                "configured_by_user" if model else "provider_default_unverified"
            ),
            "provider_attested": False,
        },
        "context": {
            "token_budget": int(token_budget) if token_budget is not None else None,
            "capability_profile_source": "inferred_from_model_label",
            "provider_probed": False,
        },
    }


def workspace_goal_contract(goal: WorkspaceGoal) -> dict[str, Any]:
    try:
        value = json.loads(goal.contract_json or "{}")
    except (TypeError, json.JSONDecodeError):
        value = {}
    if isinstance(value, dict) and value.get("schema_version") == WORK_SESSION_SCHEMA_VERSION:
        return value
    return build_work_contract(objective=goal.title)


async def resolve_current_goal(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    allowed_component_ids: set[UUID] | None = None,
) -> dict | None:
    """Return active work, never an objective inferred from an old context pack."""
    run = await session.scalar(
        select(AgentRun)
        .where(
            AgentRun.workspace_id == workspace_id,
            AgentRun.status.in_(ACTIVE_RUN_STATUSES),
            AgentRun.objective.is_not(None),
        )
        .order_by(AgentRun.started_at.desc(), AgentRun.id.desc())
        .limit(1)
    )
    if run is not None and str(run.objective or "").strip():
        component_id = None
        attached_goal = None
        if run.context_pack_id:
            pack = await session.get(ContextPack, run.context_pack_id)
            candidate = pack.focus_component_id if pack is not None else None
            if pack is not None and pack.workspace_goal_id is not None:
                attached_goal = await session.get(WorkspaceGoal, pack.workspace_goal_id)
            if candidate and (
                allowed_component_ids is None or candidate in allowed_component_ids
            ):
                component_id = candidate
        return {
            "id": str(attached_goal.id) if attached_goal is not None else f"run:{run.id}",
            "workspace_id": str(workspace_id),
            "title": str(run.objective).strip(),
            "component_id": str(component_id) if component_id else None,
            "source_kind": "active_agent_run",
            "source_id": str(run.id),
            "work_contract": (
                workspace_goal_contract(attached_goal)
                if attached_goal is not None
                else build_work_contract(objective=str(run.objective).strip())
            ),
            "selected_by": run.tool or "agent_harness",
            "selected_at": run.started_at,
            "can_clear": False,
        }

    goal = await session.scalar(
        select(WorkspaceGoal)
        .where(
            WorkspaceGoal.workspace_id == workspace_id,
            WorkspaceGoal.status == "active",
        )
        .order_by(WorkspaceGoal.selected_at.desc(), WorkspaceGoal.id.desc())
        .limit(1)
    )
    return goal_to_dict(goal) if goal is not None else None


async def select_workspace_goal(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    title: str,
    component_id: UUID | None,
    source_kind: str,
    source_id: str | None,
    selected_by: str,
    selected_at: datetime | None = None,
    work_contract: Mapping[str, Any] | None = None,
) -> WorkspaceGoal:
    now = selected_at or utc_now()
    active = list(await session.scalars(
        select(WorkspaceGoal).where(
            WorkspaceGoal.workspace_id == workspace_id,
            WorkspaceGoal.status == "active",
        )
    ))
    for previous in active:
        previous.status = "replaced"
        previous.ended_at = now
    goal = WorkspaceGoal(
        workspace_id=workspace_id,
        title=" ".join(title.split()),
        component_id=component_id,
        status="active",
        source_kind=source_kind,
        source_id=source_id,
        contract_json=json.dumps(
            dict(work_contract or build_work_contract(objective=title)),
            sort_keys=True,
            separators=(",", ":"),
        ),
        selected_by=selected_by,
        selected_at=now,
    )
    session.add(goal)
    await session.flush()
    return goal


async def clear_workspace_goal(
    session: AsyncSession,
    *,
    workspace_id: UUID,
) -> WorkspaceGoal | None:
    goal = await session.scalar(
        select(WorkspaceGoal).where(
            WorkspaceGoal.workspace_id == workspace_id,
            WorkspaceGoal.status == "active",
        )
    )
    if goal is None:
        return None
    goal.status = "cleared"
    goal.ended_at = utc_now()
    await session.flush()
    return goal


async def complete_workspace_goal(
    session: AsyncSession,
    *,
    workspace_id: UUID,
    run_id: UUID,
) -> WorkspaceGoal:
    goal = await session.scalar(
        select(WorkspaceGoal).where(
            WorkspaceGoal.workspace_id == workspace_id,
            WorkspaceGoal.status == "active",
        )
    )
    if goal is None:
        raise WorkspaceGoalCompletionError("No active workspace goal exists")
    run = await session.get(AgentRun, run_id)
    if run is None or run.workspace_id != workspace_id or run.context_pack_id is None:
        raise WorkspaceGoalCompletionError("The observed run was not found in this workspace")
    pack = await session.get(ContextPack, run.context_pack_id)
    if pack is None or pack.workspace_goal_id != goal.id:
        raise WorkspaceGoalCompletionError(
            "The observed run is not attached to the active workspace goal"
        )
    report = await HarnessOutcomeService(session).summarize(workspace_id=workspace_id)
    outcome = next((item for item in report.runs if item.run_id == str(run_id)), None)
    if outcome is None or not outcome.verified_success:
        raise WorkspaceGoalCompletionError(
            "The goal can be completed only from a verified harness result"
        )
    goal.status = "completed"
    goal.ended_at = utc_now()
    await session.flush()
    return goal
