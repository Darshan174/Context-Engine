import json
from datetime import datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from app.models import (
    AgentRun,
    Component,
    ContextPack,
    Model,
    RunObservation,
    SourceDocument,
    Workspace,
    WorkspaceGoal,
)


async def _project(db_session):
    workspace = Workspace(id=uuid4(), name="Goal project", slug=f"goal-{uuid4().hex}")
    model = Model(id=uuid4(), name=f"Tasks {uuid4().hex}")
    source = SourceDocument(
        id=uuid4(),
        workspace_id=workspace.id,
        source_type="github_issue",
        external_id="issue-12",
        source_url="https://github.example/acme/project/issues/12",
        content="Issue #12: Fix workspace onboarding.",
        metadata_json=json.dumps({
            "item_type": "issue",
            "repo_full_name": "acme/project",
            "number": 12,
            "state": "open",
        }),
    )
    task = Component(
        id=uuid4(),
        workspace_id=workspace.id,
        model_id=model.id,
        source_document_id=source.id,
        name="Issue #12: Fix workspace onboarding",
        value="Make project selection explicit.",
        fact_type="issue",
        status="active",
        confidence=0.9,
    )
    db_session.add_all([workspace, model, source, task])
    await db_session.flush()
    return workspace, task


async def test_select_replace_and_clear_current_goal(client, db_session):
    workspace, task = await _project(db_session)

    selected = await client.put(
        f"/api/workspaces/{workspace.id}/current-goal",
        json={
            "title": task.name,
            "component_id": str(task.id),
            "source_kind": "suggested_card",
            "source_id": str(task.source_document_id),
        },
    )
    assert selected.status_code == 200
    assert selected.json()["component_id"] == str(task.id)
    assert selected.json()["selected_by"] == "local"
    assert selected.json()["work_contract"]["objective"] == task.name
    assert selected.json()["work_contract"]["agent"]["adapter_id"] is None

    digest = await client.get("/api/context/digest", params={"workspace_id": str(workspace.id)})
    assert digest.status_code == 200
    assert digest.json()["current_goal"]["title"] == task.name
    assert digest.json()["oversight"]["current_focus"]["component_id"] == str(task.id)

    replacement = await client.put(
        f"/api/workspaces/{workspace.id}/current-goal",
        json={"title": "Ship the repo-first onboarding"},
    )
    assert replacement.status_code == 200
    assert replacement.json()["component_id"] is None

    goals = list(await db_session.scalars(
        select(WorkspaceGoal)
        .where(WorkspaceGoal.workspace_id == workspace.id)
        .order_by(WorkspaceGoal.selected_at, WorkspaceGoal.id)
    ))
    assert [goal.status for goal in goals] == ["replaced", "active"]

    cleared = await client.delete(f"/api/workspaces/{workspace.id}/current-goal")
    assert cleared.status_code == 204
    digest = await client.get("/api/context/digest", params={"workspace_id": str(workspace.id)})
    assert digest.json()["current_goal"] is None
    assert digest.json()["oversight"]["current_focus"] is None


async def test_start_work_session_persists_contract_and_exact_pack(client, db_session):
    workspace, task = await _project(db_session)

    response = await client.post(
        f"/api/workspaces/{workspace.id}/work-session",
        json={
            "objective": task.name,
            "definition_of_done": [
                "The project picker survives a reload",
                "The focused regression test passes",
            ],
            "component_id": str(task.id),
            "source_kind": "suggested_card",
            "source_id": str(task.source_document_id),
            "adapter_id": "codex",
            "target_model": "older-coder",
            "token_budget": 4000,
        },
    )

    assert response.status_code == 200, response.text
    data = response.json()
    assert data["goal"]["work_contract"] == {
        "schema_version": "work_session.v1",
        "objective": task.name,
        "definition_of_done": [
            "The project picker survives a reload",
            "The focused regression test passes",
        ],
        "agent": {
            "adapter_id": "codex",
            "target_model": "older-coder",
            "model_identity_source": "configured_by_user",
            "provider_attested": False,
        },
        "context": {
            "token_budget": 4000,
            "capability_profile_source": "inferred_from_model_label",
            "provider_probed": False,
        },
    }
    pack = data["pack"]
    assert pack["workspace_goal_id"] == data["goal"]["id"]
    assert pack["manifest"]["workspace_goal_id"] == data["goal"]["id"]
    assert pack["manifest"]["work_contract"] == data["goal"]["work_contract"]
    assert "## Definition Of Done" in pack["markdown"]
    assert "The project picker survives a reload" in pack["markdown"]
    assert "## Agent Target" in pack["markdown"]
    assert "Runtime model provider-attested: `false`" in pack["markdown"]

    persisted_goal = await db_session.get(WorkspaceGoal, UUID(data["goal"]["id"]))
    persisted_pack = await db_session.get(ContextPack, UUID(pack["context_pack_id"]))
    assert json.loads(persisted_goal.contract_json)["agent"]["adapter_id"] == "codex"
    assert persisted_pack.workspace_goal_id == persisted_goal.id


async def test_agent_adapter_catalog_is_detected_and_honest(client, db_session):
    workspace, _ = await _project(db_session)

    response = await client.get(f"/api/workspaces/{workspace.id}/agent-adapters")

    assert response.status_code == 200
    items = {item["id"]: item for item in response.json()["items"]}
    assert {"codex", "claude_code", "opencode"}.issubset(items)
    assert items["codex"]["detection_source"] == "server_path"
    assert items["codex"]["model_identity"]["provider_attested"] is False
    assert items["codex"]["capability_profile"]["provider_probed"] is False


async def test_old_context_pack_is_not_inferred_as_current_goal(client, db_session):
    workspace, task = await _project(db_session)
    db_session.add(ContextPack(
        id=uuid4(),
        workspace_id=workspace.id,
        objective=task.name,
        focus_component_id=task.id,
        objective_origin="source_component",
        markdown="# Old brief",
        manifest="{}",
    ))
    await db_session.flush()

    digest = await client.get("/api/context/digest", params={"workspace_id": str(workspace.id)})
    assert digest.status_code == 200
    assert digest.json()["objective"]["status"] == "supplied"
    assert digest.json()["current_goal"] is None
    assert digest.json()["oversight"]["current_focus"] is None


async def test_new_workspace_starts_without_another_workspaces_goal(client):
    first = await client.post("/api/workspaces", json={"name": "Configured Project"})
    first_id = first.json()["id"]
    selected = await client.put(
        f"/api/workspaces/{first_id}/current-goal",
        json={"title": "Keep this project's goal"},
    )
    assert selected.status_code == 200

    fresh = await client.post("/api/workspaces", json={"name": "Fresh Project"})
    fresh_id = fresh.json()["id"]
    fresh_digest = await client.get(
        "/api/context/digest", params={"workspace_id": fresh_id}
    )
    configured_digest = await client.get(
        "/api/context/digest", params={"workspace_id": first_id}
    )

    assert fresh_digest.status_code == 200
    assert fresh_digest.json()["current_goal"] is None
    assert configured_digest.json()["current_goal"]["title"] == (
        "Keep this project's goal"
    )


async def test_active_run_temporarily_overrides_selected_goal(client, db_session):
    workspace, task = await _project(db_session)
    response = await client.put(
        f"/api/workspaces/{workspace.id}/current-goal",
        json={"title": "Review the backlog"},
    )
    assert response.status_code == 200
    selected_goal_id = UUID(response.json()["id"])
    pack = ContextPack(
        id=uuid4(),
        workspace_id=workspace.id,
        objective=task.name,
        focus_component_id=task.id,
        objective_origin="trusted_human",
        markdown="# Active brief",
        manifest="{}",
        workspace_goal_id=selected_goal_id,
    )
    run = AgentRun(
        id=uuid4(),
        workspace_id=workspace.id,
        context_pack_id=pack.id,
        objective="Implement the active task",
        tool="codex",
        status="running",
    )
    db_session.add_all([pack, run])
    await db_session.flush()

    digest = await client.get("/api/context/digest", params={"workspace_id": str(workspace.id)})
    goal = digest.json()["current_goal"]
    assert goal["id"] == str(selected_goal_id)
    assert goal["title"] == "Implement the active task"
    assert goal["source_kind"] == "active_agent_run"
    assert goal["can_clear"] is False
    assert goal["work_contract"]["objective"] == "Review the backlog"


async def test_rejects_ineligible_goal_component(client, db_session):
    workspace, task = await _project(db_session)
    task.fact_type = "github_pr"
    await db_session.flush()

    response = await client.put(
        f"/api/workspaces/{workspace.id}/current-goal",
        json={"title": task.name, "component_id": str(task.id)},
    )
    assert response.status_code == 422
    assert "delivery evidence" in response.json()["detail"]


async def test_closed_remote_issue_is_not_actionable_or_compilable(client, db_session):
    workspace, task = await _project(db_session)
    source = await db_session.get(SourceDocument, task.source_document_id)
    source.metadata_json = json.dumps({
        "item_type": "issue",
        "repo_full_name": "acme/project",
        "number": 12,
        "state": "closed",
    })
    await db_session.flush()

    digest = await client.get(
        "/api/context/digest", params={"workspace_id": str(workspace.id)}
    )
    card = next(
        item for item in digest.json()["cards"]
        if item["id"] == f"component:{task.id}"
    )
    assert card["source_snapshot"]["provider_state"] == "closed"
    assert card["focus_eligible"] is False
    assert "closed" in card["focus_ineligible_reason"]

    selected = await client.put(
        f"/api/workspaces/{workspace.id}/current-goal",
        json={"title": task.name, "component_id": str(task.id)},
    )
    assert selected.status_code == 422
    assert "closed" in selected.json()["detail"]

    prepared = await client.post(
        "/api/context/prepare",
        json={
            "workspace_id": str(workspace.id),
            "focus_component_id": str(task.id),
            "objective_origin": "source_component",
        },
    )
    assert prepared.status_code == 422
    assert "closed" in prepared.json()["detail"]["message"]


async def test_open_issue_is_backlog_not_attention(client, db_session):
    workspace, task = await _project(db_session)

    response = await client.get(
        "/api/context/digest", params={"workspace_id": str(workspace.id)}
    )
    assert response.status_code == 200
    data = response.json()
    card = next(item for item in data["cards"] if item["id"] == f"component:{task.id}")
    assert card["category"] == "issue"
    assert card["attention_required"] is False
    clusters = {cluster["id"]: cluster for cluster in data["clusters"]}
    assert card["id"] in clusters["backlog"]["card_ids"]
    assert card["id"] not in clusters["needs_attention"]["card_ids"]


async def test_verified_attached_run_can_explicitly_complete_current_goal(
    client, db_session
):
    workspace, task = await _project(db_session)
    selected = await client.put(
        f"/api/workspaces/{workspace.id}/current-goal",
        json={
            "title": task.name,
            "component_id": str(task.id),
            "source_kind": "suggested_card",
            "source_id": str(task.source_document_id),
        },
    )
    goal_id = selected.json()["id"]
    observed_at = datetime(2026, 7, 18, 9, 0, 0)
    pack = ContextPack(
        id=uuid4(),
        workspace_id=workspace.id,
        workspace_goal_id=UUID(goal_id),
        objective=task.name,
        focus_component_id=task.id,
        markdown="# Verified goal pack",
        manifest=json.dumps({"schema_version": "context_pack.v2"}),
    )
    run = AgentRun(
        id=uuid4(),
        workspace_id=workspace.id,
        context_pack_id=pack.id,
        run_key=f"goal-completion-{uuid4()}",
        model="older-coder",
        tool="local-harness",
        objective=task.name,
        status="completed",
        started_at=observed_at,
        ended_at=observed_at + timedelta(minutes=4),
    )
    verification_source = SourceDocument(
        id=uuid4(),
        workspace_id=workspace.id,
        source_type="agent_run_observation",
        external_id=f"verification-{uuid4()}",
        content="Focused verification passed.",
        metadata_json=json.dumps({"observed_by": "local_harness"}),
    )
    outcome_source = SourceDocument(
        id=uuid4(),
        workspace_id=workspace.id,
        source_type="agent_run_observation",
        external_id=f"outcome-{uuid4()}",
        content="Goal completed with verification.",
        metadata_json=json.dumps({"observed_by": "local_harness"}),
    )
    verification = RunObservation(
        id=uuid4(),
        agent_run_id=run.id,
        source_document_id=verification_source.id,
        event_type="verification",
        event_key="goal:verification",
        payload_json=json.dumps({"command": "pytest -q", "exit_code": 0}),
        observed_at=observed_at + timedelta(minutes=3),
        command="pytest -q",
        exit_code=0,
    )
    outcome = RunObservation(
        id=uuid4(),
        agent_run_id=run.id,
        source_document_id=outcome_source.id,
        event_type="outcome",
        event_key="goal:outcome",
        payload_json=json.dumps({"status": "completed"}),
        observed_at=observed_at + timedelta(minutes=4),
        content="Goal completed with verification.",
        files_json=json.dumps(["app/workspaces.py"]),
    )
    db_session.add_all([
        pack,
        run,
        verification_source,
        outcome_source,
        verification,
        outcome,
    ])
    await db_session.commit()

    digest = await client.get(
        "/api/context/digest", params={"workspace_id": str(workspace.id)}
    )
    assert digest.status_code == 200
    assert digest.json()["oversight"]["latest_outcome"]["verified_success"] is True

    completed = await client.post(
        f"/api/workspaces/{workspace.id}/current-goal/complete",
        json={"run_id": str(run.id)},
    )

    assert completed.status_code == 200
    assert completed.json()["status"] == "completed"
    refreshed = await client.get(
        "/api/context/digest", params={"workspace_id": str(workspace.id)}
    )
    assert refreshed.json()["current_goal"] is None
