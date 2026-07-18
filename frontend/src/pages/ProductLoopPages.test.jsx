import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, useLocation } from "react-router-dom";
import { beforeEach, describe, expect, it, vi } from "vitest";

import NowPage from "./NowPage";
import PreparePage from "./PreparePage";
import RunsPage from "./RunsPage";
import WorkItemsPage from "./WorkItemsPage";

const mocks = vi.hoisted(() => ({
  workspace: {
    activeWorkspaceId: "workspace-1",
    activeWorkspace: { id: "workspace-1", name: "Context Engine" },
    workspacesQuery: { isLoading: false },
    workspaces: [{ id: "workspace-1", name: "Context Engine" }],
    selectedId: "workspace-1",
    setSelectedId: vi.fn(),
  },
  digest: { data: null, isLoading: false, isError: false },
  prepare: { data: null, isPending: false, isError: false, mutateAsync: vi.fn(), reset: vi.fn() },
  packs: { data: { items: [] }, isLoading: false },
  pack: { data: null, isLoading: false, isError: false },
  comparison: { data: null, isLoading: false, isError: false },
  outcomes: { data: null, isLoading: false, isError: false },
  adapters: {
    data: {
      items: [{
        id: "codex",
        label: "Codex CLI",
        installed: true,
        version: "codex-cli 0.142.5",
        launch_support: "ready",
      }],
    },
    isLoading: false,
    isError: false,
  },
  startWork: { isPending: false, error: null, mutateAsync: vi.fn() },
  setGoal: { isPending: false, error: null, mutateAsync: vi.fn() },
  clearGoal: { isPending: false, error: null, mutateAsync: vi.fn() },
  completeGoal: { isPending: false, isError: false, error: null, mutate: vi.fn() },
}));

vi.mock("./useProductWorkspace", () => ({
  useProductWorkspace: () => mocks.workspace,
}));

vi.mock("../context-map/api", () => ({
  useContextDigest: () => mocks.digest,
  useSetCurrentGoal: () => mocks.setGoal,
  useClearCurrentGoal: () => mocks.clearGoal,
  useCompleteCurrentGoal: () => mocks.completeGoal,
  useAgentAdapters: () => mocks.adapters,
  useStartWorkSession: () => mocks.startWork,
  usePrepareContext: () => mocks.prepare,
  useContextPacks: () => mocks.packs,
  useContextPack: () => mocks.pack,
  useContextPackComparison: () => mocks.comparison,
  useRunOutcomes: () => mocks.outcomes,
}));

beforeEach(() => {
  mocks.digest.data = null;
  mocks.digest.isLoading = false;
  mocks.digest.isError = false;
  mocks.prepare.data = null;
  mocks.prepare.isPending = false;
  mocks.prepare.isError = false;
  mocks.prepare.mutateAsync.mockReset().mockResolvedValue({});
  mocks.prepare.reset.mockReset();
  mocks.packs.data = { items: [] };
  mocks.packs.isLoading = false;
  mocks.pack.data = null;
  mocks.pack.isLoading = false;
  mocks.pack.isError = false;
  mocks.comparison.data = null;
  mocks.comparison.isLoading = false;
  mocks.comparison.isError = false;
  mocks.outcomes.data = null;
  mocks.outcomes.isLoading = false;
  mocks.outcomes.isError = false;
  mocks.adapters.data = { items: [{ id: "codex", label: "Codex CLI", installed: true, version: "codex-cli 0.142.5", launch_support: "ready" }] };
  mocks.adapters.isLoading = false;
  mocks.adapters.isError = false;
  mocks.startWork.isPending = false;
  mocks.startWork.error = null;
  mocks.startWork.mutateAsync.mockReset().mockResolvedValue({ pack: { context_pack_id: "pack-new" } });
  mocks.setGoal.isPending = false;
  mocks.setGoal.error = null;
  mocks.setGoal.mutateAsync.mockReset().mockResolvedValue({});
  mocks.clearGoal.isPending = false;
  mocks.clearGoal.error = null;
  mocks.clearGoal.mutateAsync.mockReset().mockResolvedValue(null);
  mocks.completeGoal.isPending = false;
  mocks.completeGoal.isError = false;
  mocks.completeGoal.error = null;
  mocks.completeGoal.mutate.mockReset();
});

describe("product loop pages", () => {
  it("turns the digest into a concise current-state and next-action surface", () => {
    mocks.digest.data = {
      generated_at: "2026-07-17T10:00:00Z",
      scope: { included_source_count: 7, project_paths: ["/workspace/context-engine"] },
      current_goal: {
        id: "goal-1",
        component_id: "task-1",
        title: "Harden the model adapter",
        source_kind: "user_selected",
        selected_by: "local",
        selected_at: "2026-07-17T09:00:00Z",
        can_clear: true,
        work_contract: {
          definition_of_done: ["The adapter reports a deterministic capability profile"],
          agent: { adapter_id: "codex", target_model: "older-coder", model_identity_source: "configured_by_user" },
          context: { token_budget: 4000 },
        },
      },
      oversight: {
        current_focus: { component_id: "task-1", title: "Harden the model adapter" },
        latest_outcome: { summary: "Compiler tests passed.", observed_at: "2026-07-17T09:30:00Z" },
      },
      cards: [
        { id: "component:task-1", category: "task", title: "Harden the model adapter", summary: "Implement capability-aware rendering.", next_action: "Add provider capability probing.", focus_eligible: true, attention_required: false },
        { id: "risk-1", category: "risk", status: "active", title: "Model identity is self-reported", summary: "Provider identity is not independently verified.", attention_score: 95, attention_required: true },
        { id: "component:issue-2", category: "issue", status: "needs_review", title: "Issue #2: Add hybrid retrieval", summary: "Backlog work.", attention_score: 60, focus_eligible: true, attention_required: false },
      ],
    };

    render(<MemoryRouter><NowPage /></MemoryRouter>);

    expect(screen.getByRole("heading", { name: "Harden the model adapter" })).toBeInTheDocument();
    expect(screen.getByText(/Model identity is self\s*-\s*reported/)).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "View all 1" })[0]).toHaveAttribute("href", "/app/work?view=attention");
    expect(screen.getAllByText(/Issue 2: Add hybrid retrieval/).length).toBeGreaterThan(0);
    expect(screen.getAllByRole("link", { name: /Inspect context/ })[0]).toHaveAttribute("href", "/app/prepare");
    expect(screen.getByRole("link", { name: "Explain project" })).toHaveAttribute("href", "/app/explain");
  });

  it("turns a backlog suggestion into a work contract and exact pack", async () => {
    mocks.digest.data = {
      generated_at: "2026-07-17T10:00:00Z",
      scope: { included_source_count: 2, project_paths: ["/workspace/context-engine"] },
      current_goal: null,
      oversight: {},
      cards: [{
        id: "component:issue-2",
        category: "issue",
        status: "needs_review",
        title: "Issue #2: Add hybrid retrieval",
        summary: "Backlog work.",
        attention_score: 60,
        focus_eligible: true,
        attention_required: false,
        source_snapshot: { source_document_id: "source-2" },
      }],
    };

    render(<MemoryRouter><NowPage /><LocationProbe /></MemoryRouter>);

    expect(screen.getByRole("heading", { name: "Give the agent a job, not a label." })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "View all 0" })).toHaveAttribute("href", "/app/work?view=attention");
    fireEvent.click(screen.getByRole("button", { name: "Set up this work" }));
    expect(screen.getByLabelText("Work objective")).toHaveValue("Issue 2: Add hybrid retrieval");
    fireEvent.change(screen.getByLabelText("Definition of done"), { target: { value: "Hybrid retrieval returns the expected source\nFocused tests pass" } });
    fireEvent.click(screen.getByRole("button", { name: /Prepare and continue/ }));
    await waitFor(() => expect(mocks.startWork.mutateAsync).toHaveBeenCalledWith({
      objective: "Issue 2: Add hybrid retrieval",
      definition_of_done: ["Hybrid retrieval returns the expected source", "Focused tests pass"],
      component_id: "issue-2",
      source_kind: "suggested_card",
      source_id: "source-2",
      adapter_id: "codex",
      target_model: undefined,
      token_budget: 4000,
    }));
    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("/app/runs?pack=pack-new"));
  });

  it("closes a current goal only when the user accepts a verified attached result", () => {
    mocks.digest.data = {
      current_goal: { id: "goal-1", title: "Fix the redirect", source_kind: "user_selected", can_clear: true },
      scope: { project_paths: ["/workspace/context-engine"] },
      cards: [],
      oversight: {
        latest_outcome: {
          run_id: "run-1",
          summary: "Completed: 2 files changed; 2/2 verification checks passed.",
          status: "completed",
          model: "older-coder",
          tool: "local-harness",
          changed_files: ["app.py", "test_app.py"],
          verification: { passed: 2, observed: 2 },
          verified_success: true,
          observed_at: "2026-07-18T09:00:00Z",
        },
      },
    };

    render(<MemoryRouter><NowPage /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: "Accept result and complete work" }));

    expect(mocks.completeGoal.mutate).toHaveBeenCalledWith({ runId: "run-1" });
    expect(screen.getByRole("link", { name: "Inspect this run" })).toHaveAttribute("href", "/app/runs?run=run-1");
  });

  it("shows compiler selection, exclusions, model profile, and the exact brief", async () => {
    mocks.digest.data = {
      scope: { project_paths: ["/workspace/context-engine"] },
      cards: [],
      current_goal: {
        id: "goal-1",
        title: "Fix the redirect",
        component_id: "task-1",
        work_contract: {
          definition_of_done: ["The redirect lands on the intended workspace"],
          agent: { adapter_id: "codex", target_model: "older-coder" },
          context: { token_budget: 4000 },
        },
      },
    };
    mocks.prepare.data = {
      markdown: "# Agent brief\n\nUse source-backed evidence.",
      health_score: 92,
      manifest: {
        objective: "Fix the redirect",
        target_model: { name: "older-coder", profile: "small_coder_model" },
        rendering: { estimated_tokens: 740 },
        token_accounting: { selected_item_tokens: 700 },
      },
      selected_context: [{ id: "selected-1", title: "Authentication decision", item_type: "decision", inclusion_reason: "direct_objective_match", token_cost: 180 }],
      excluded_context: [{ id: "excluded-1", reason: "lower_ranked" }],
    };
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(globalThis.navigator, "clipboard", { configurable: true, value: { writeText } });

    render(<MemoryRouter initialEntries={["/app/prepare"]}><PreparePage /></MemoryRouter>);

    expect(screen.queryByLabelText("Task")).not.toBeInTheDocument();
    expect(screen.getAllByRole("heading", { name: "Fix the redirect" })).toHaveLength(2);
    expect(screen.getByText("The redirect lands on the intended workspace")).toBeInTheDocument();
    expect(screen.getByText("Concise small-model profile inferred for older-coder · 740 estimated tokens")).toBeInTheDocument();
    expect(screen.getByText("Authentication decision")).toBeInTheDocument();
    expect(screen.getByText(/Excluded evidence · 1/)).toBeInTheDocument();
    expect(screen.getByText("Brief compiled")).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: "Copy brief" }));
    await waitFor(() => expect(writeText).toHaveBeenCalledWith("# Agent brief\n\nUse source-backed evidence."));

    fireEvent.click(screen.getByRole("button", { name: "Rebuild context pack" }));
    await waitFor(() => expect(mocks.prepare.mutateAsync).toHaveBeenCalledWith(expect.objectContaining({
      objective: "Fix the redirect",
      workspace_goal_id: "goal-1",
      target_model: "older-coder",
      token_budget: 4000,
      mode: "task",
    })));
  });

  it("compares exact selected context across two persisted packs", async () => {
    mocks.digest.data = { scope: { project_paths: ["/workspace/context-engine"] }, cards: [] };
    mocks.packs.data = { items: [
      { context_pack_id: "pack-new", objective: "Fix redirect", created_at: "2026-07-18T09:00:00Z", selected_count: 2, run_count: 1 },
      { context_pack_id: "pack-old", objective: "Fix redirect", created_at: "2026-07-18T08:00:00Z", selected_count: 2, run_count: 0 },
    ] };
    mocks.comparison.data = {
      left: { estimated_tokens: 900, health_score: 60 },
      right: { estimated_tokens: 760, health_score: 82 },
      selected_context: {
        retained: [{ id: "task:b", title: "Link observed runs" }],
        added: [{ id: "verification:c", title: "Run focused checks" }],
        removed: [{ id: "decision:a", title: "Keep explicit goals" }],
        changed: [],
      },
    };

    render(<MemoryRouter><PreparePage /></MemoryRouter>);
    const compareBoxes = screen.getAllByRole("checkbox");
    fireEvent.click(compareBoxes[0]);
    fireEvent.click(compareBoxes[1]);

    expect(screen.getByRole("heading", { name: "Exact pack comparison" })).toBeInTheDocument();
    expect(screen.getByText("+22")).toBeInTheDocument();
    expect(screen.getByText(/Token delta -140/)).toBeInTheDocument();
  });

  it("opens saved packs through a stable pack URL", async () => {
    mocks.digest.data = { scope: { project_paths: ["/workspace/context-engine"] }, cards: [] };
    mocks.packs.data = { items: [{
      context_pack_id: "pack-new",
      objective: "Fix redirect",
      created_at: "2026-07-18T09:00:00Z",
      selected_count: 2,
      run_count: 1,
    }] };

    render(<MemoryRouter initialEntries={["/app/prepare"]}><PreparePage /><LocationProbe /></MemoryRouter>);
    fireEvent.click(screen.getByRole("button", { name: /Fix redirect.*2 selected.*1 runs/ }));

    await waitFor(() => expect(screen.getByTestId("location")).toHaveTextContent("?pack=pack-new"));
  });

  it("keeps observed runs separate from an honest, non-causal comparison", () => {
    mocks.digest.data = {
      current_goal: {
        id: "goal-1",
        title: "Fix the redirect",
        work_contract: {
          definition_of_done: ["The redirect works", "Focused checks pass"],
          agent: { adapter_id: "codex", target_model: "older-coder", model_identity_source: "configured_by_user" },
        },
      },
      scope: { project_paths: ["/workspace/context-engine"] },
    };
    mocks.packs.data = { items: [{
      context_pack_id: "pack-1",
      workspace_goal_id: "goal-1",
      objective: "Fix the redirect",
      target_model: "older-coder",
      selected_count: 4,
      health_score: 88,
    }] };
    mocks.outcomes.data = {
      measurement_note: "Model names are recorded labels, not independently verified provider identities.",
      runs: [{
        run_id: "run-1",
        context_pack_id: "pack-1",
        workspace_goal_id: "goal-1",
        model: "older-coder",
        model_profile: "small_coder_model",
        objective: "Fix the redirect",
        tool: "codex",
        status: "complete",
        completed: true,
        verified_success: true,
        failed_verification: false,
        unresolved_blocker: false,
        duration_seconds: 83,
        started_at: "2026-07-17T10:00:00Z",
        changed_files: ["frontend/src/App.jsx"],
        verification: { observed: 2, passed: 2, failed: 0 },
      }],
      groups: [{
        model: "older-coder",
        model_profile: "small_coder_model",
        observed_runs: 1,
        verified_successful_runs: 1,
        verified_success_rate: 1,
        failed_verification_runs: 0,
        unresolved_blocker_runs: 0,
      }],
    };

    render(<MemoryRouter><RunsPage /></MemoryRouter>);

    expect(screen.getByRole("heading", { name: "Fix the redirect" })).toBeInTheDocument();
    expect(screen.getByText("2/2")).toBeInTheDocument();
    expect(screen.getByText("4 Result", { exact: false })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Compare/ }));
    expect(screen.getByRole("heading", { name: "A paired baseline is still missing" })).toBeInTheDocument();
    expect(screen.getByText("100%")).toBeInTheDocument();
    expect(screen.getByText(/not independently verified provider identities/)).toBeInTheDocument();
  });

  it("generates a guided harness command for the exact persisted pack", async () => {
    mocks.digest.data = {
      current_goal: {
        id: "goal-1",
        title: "Fix the redirect",
        work_contract: {
          definition_of_done: ["The redirect works"],
          agent: { adapter_id: "codex", target_model: "older-coder", model_identity_source: "configured_by_user" },
        },
      },
      scope: { project_paths: ["/workspace/context-engine"] },
    };
    mocks.packs.data = { items: [{
      context_pack_id: "pack-1",
      workspace_goal_id: "goal-1",
      objective: "Fix the redirect",
      target_model: "older-coder",
      selected_count: 4,
      health_score: 88,
    }] };
    mocks.outcomes.data = { runs: [], groups: [] };
    const writeText = vi.fn().mockResolvedValue(undefined);
    Object.defineProperty(globalThis.navigator, "clipboard", { configurable: true, value: { writeText } });

    render(<MemoryRouter><RunsPage /></MemoryRouter>);

    const copy = await screen.findByRole("button", { name: "Copy command" });
    fireEvent.click(copy);
    await waitFor(() => expect(writeText).toHaveBeenCalledWith(expect.stringContaining("--context-pack-id pack-1")));
    expect(writeText.mock.calls[0][0]).toContain("--adapter codex --target-model older-coder --verify");
    expect(screen.queryByLabelText("Worker command")).not.toBeInTheDocument();
  });

  it("does not run a same-title pack that was never attached to the current goal", () => {
    mocks.digest.data = {
      current_goal: {
        id: "goal-1",
        title: "Fix the redirect",
        work_contract: {
          definition_of_done: ["The redirect works"],
          agent: { adapter_id: "codex", target_model: "older-coder", model_identity_source: "configured_by_user" },
        },
      },
      scope: { project_paths: ["/workspace/context-engine"] },
    };
    mocks.packs.data = { items: [{
      context_pack_id: "legacy-pack",
      workspace_goal_id: null,
      objective: "Fix the redirect",
      target_model: "older-coder",
      selected_count: 4,
      health_score: 88,
    }] };
    mocks.outcomes.data = { runs: [], groups: [] };

    render(<MemoryRouter><RunsPage /></MemoryRouter>);

    expect(screen.getByText("No pack is attached to this work contract")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Rebuild pack" })).toHaveAttribute("href", "/app/prepare");
    expect(screen.queryByRole("button", { name: "Copy command" })).not.toBeInTheDocument();
  });

  it("shows the full inspectable work queue without silently selecting work", async () => {
    mocks.digest.data = {
      current_goal: null,
      cards: [
        { id: "component:risk-1", category: "risk", status: "active", title: "Provider model identity is unverified", summary: "The provider label is self-reported.", attention_score: 91, attention_required: true, focus_eligible: false, source_snapshot: { source_document_id: "source-1", freshness: "observed" }, provenance: [{ id: "p1" }] },
        { id: "component:task-2", category: "task", status: "active", title: "Add capability probing", summary: "Probe the selected model adapter.", next_action: "Implement the adapter probe.", attention_score: 60, attention_required: false, focus_eligible: true, source_snapshot: { source_document_id: "source-2", freshness: "observed" }, provenance: [{ id: "p2" }] },
        { id: "component:issue-closed", category: "issue", status: "needs_review", title: "Closed provider issue", summary: "This issue is already closed upstream.", attention_score: 70, attention_required: false, focus_eligible: false, focus_ineligible_reason: "This issue is closed at its provider and is no longer actionable.", source_snapshot: { source_document_id: "source-3", freshness: "unknown", provider_state: "closed" }, provenance: [{ id: "p3" }] },
      ],
    };

    render(<MemoryRouter initialEntries={["/app/work?view=backlog"]}><WorkItemsPage /></MemoryRouter>);

    expect(screen.getByRole("heading", { name: "Add capability probing" })).toBeInTheDocument();
    expect(screen.queryByRole("heading", { name: "Closed provider issue" })).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Inspect evidence" })).toHaveAttribute("href", "/app/explain?card=component%3Atask-2");
    expect(screen.getByRole("link", { name: "Source" })).toHaveAttribute("href", "/app/sources?source=source-2");
    expect(screen.getByRole("link", { name: "Start this work" })).toHaveAttribute("href", "/app?work=component%3Atask-2");
  });
});

function LocationProbe() {
  const location = useLocation();
  return <output data-testid="location">{location.pathname}{location.search}</output>;
}
