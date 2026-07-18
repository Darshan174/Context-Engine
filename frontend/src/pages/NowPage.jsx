import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
  ArrowRight,
  Bot,
  CheckCircle2,
  Clock3,
  GitBranch,
  ListTodo,
  ShieldAlert,
} from "lucide-react";

import WorkspaceTopicGate from "../components/WorkspaceTopicGate";
import {
  useAgentAdapters,
  useClearCurrentGoal,
  useCompleteCurrentGoal,
  useContextDigest,
  useStartWorkSession,
} from "../context-map/api";
import { cleanDisplayText, formatTimeAgo } from "../context-map/digest";
import { useProductWorkspace } from "./useProductWorkspace";
import StartWorkPanel from "./work-session/StartWorkPanel";
import WorkContractCard from "./work-session/WorkContractCard";

export default function NowPage() {
  const workspace = useProductWorkspace();
  const navigate = useNavigate();
  const [searchParams, setSearchParams] = useSearchParams();
  const digestQuery = useContextDigest(workspace.activeWorkspaceId);
  const adaptersQuery = useAgentAdapters(workspace.activeWorkspaceId);
  const startWorkSession = useStartWorkSession(workspace.activeWorkspaceId);
  const clearCurrentGoal = useClearCurrentGoal(workspace.activeWorkspaceId);
  const completeCurrentGoal = useCompleteCurrentGoal(workspace.activeWorkspaceId);
  const [editingWork, setEditingWork] = useState(false);
  const [initialWork, setInitialWork] = useState(null);
  const digest = digestQuery.data || {};
  const cards = digest.cards || [];

  useEffect(() => {
    setEditingWork(false);
    setInitialWork(null);
  }, [workspace.activeWorkspaceId]);

  useEffect(() => {
    const requestedCardId = searchParams.get("work");
    if (!requestedCardId || !cards.length) return;
    const card = cards.find((item) => item.id === requestedCardId);
    if (!card) return;
    setInitialWork({
      title: cleanDisplayText(card.title),
      componentId: card.id.replace(/^component:/, ""),
      sourceId: card.source_snapshot?.source_document_id || undefined,
    });
    setEditingWork(true);
    const next = new URLSearchParams(searchParams);
    next.delete("work");
    setSearchParams(next, { replace: true });
  }, [cards, searchParams, setSearchParams]);

  if (!workspace.workspacesQuery.isLoading && !workspace.activeWorkspaceId) {
    return (
      <WorkspaceTopicGate
        workspaces={workspace.workspaces}
        selectedId={workspace.selectedId}
        onSelect={workspace.setSelectedId}
      />
    );
  }
  if (workspace.workspacesQuery.isLoading || digestQuery.isLoading) {
    return <PageState title="Loading the current project state…" />;
  }
  if (digestQuery.isError) {
    return <PageState title="Could not load the project state" detail={digestQuery.error?.message} error />;
  }

  const goal = digest.current_goal || null;
  const currentGoal = cleanDisplayText(goal?.title);
  const allAttentionCards = cards
    .filter((card) => card.attention_required)
    .sort((left, right) => (right.attention_score || 0) - (left.attention_score || 0));
  const attentionCards = allAttentionCards.slice(0, 3);
  const backlogCards = cards
    .filter((card) => ["issue", "task"].includes(card.category))
    .filter((card) => card.focus_eligible)
    .filter((card) => !["resolved", "closed", "superseded", "stale"].includes(card.status))
    .filter((card) => card.id !== `component:${goal?.component_id}`)
    .sort((left, right) => (right.attention_score || 0) - (left.attention_score || 0));
  const suggestedCard = backlogCards[0] || null;
  const recommendedAction = cleanDisplayText(
    suggestedCard?.title
    || allAttentionCards[0]?.next_action,
  );
  const latestOutcome = digest.oversight?.latest_outcome;
  const repoPath = digest.scope?.project_paths?.[0];
  const sourceCount = Number(digest.scope?.included_source_count || 0);
  const unassignedSessionCount = Number(digest.scope?.unknown_relevance_source_count || 0);

  function startFromCard(card) {
    setInitialWork({
      title: cleanDisplayText(card.title),
      componentId: card.id.replace(/^component:/, ""),
      sourceId: card.source_snapshot?.source_document_id || undefined,
    });
    setEditingWork(true);
    window.requestAnimationFrame(() => document.querySelector('[aria-label="Start AI work"]')?.scrollIntoView?.({ behavior: "smooth", block: "start" }));
  }

  async function beginWork(contract) {
    const result = await startWorkSession.mutateAsync(contract);
    navigate(`/app/runs?pack=${encodeURIComponent(result.pack.context_pack_id)}`);
  }

  async function clearGoal() {
    await clearCurrentGoal.mutateAsync();
    setInitialWork(null);
    setEditingWork(true);
  }

  return (
    <div className="relative mx-auto w-full max-w-6xl space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-[#85857c]">{workspace.activeWorkspace?.name || "Project"}</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight text-[#171713] dark:text-white">Now</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#68685f] dark:text-[#aaa9a0]">
            Current project truth, recent agent evidence, and the next useful action.
          </p>
        </div>
        <div className="flex items-center gap-2">
          <Link to="/app/explain" className="inline-flex h-10 items-center gap-2 rounded-lg border border-[#d8d8cf] bg-white px-4 text-xs font-black text-[#4f4f48] dark:border-[#33332e] dark:bg-[#171713] dark:text-[#d8d8cf]">
            Explain project
          </Link>
          {goal ? <Link to="/app/prepare" className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#171713] px-4 text-xs font-black text-white dark:bg-[#d9ff68] dark:text-[#171713]">Inspect context <ArrowRight className="h-3.5 w-3.5" /></Link> : <button type="button" onClick={() => setEditingWork(true)} className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#171713] px-4 text-xs font-black text-white dark:bg-[#d9ff68] dark:text-[#171713]">Start AI work <ArrowRight className="h-3.5 w-3.5" /></button>}
        </div>
      </header>

      {unassignedSessionCount > 0 ? (
        <div className="flex flex-col justify-between gap-3 rounded-xl border border-amber-200 bg-amber-50 px-4 py-3 text-amber-950 dark:border-amber-900/60 dark:bg-amber-950/25 dark:text-amber-100 sm:flex-row sm:items-center">
          <div>
            <p className="text-xs font-black">{unassignedSessionCount} AI session{unassignedSessionCount === 1 ? " is" : "s are"} not assigned to this project</p>
            <p className="mt-0.5 text-[11px] leading-5 opacity-75">Visible for review, but excluded from project health, goal suggestions, and compiled project truth until relevance is proven.</p>
          </div>
          <Link to="/app/explain" className="shrink-0 text-xs font-black underline underline-offset-4">Review evidence</Link>
        </div>
      ) : null}

      <section className="grid gap-4 lg:grid-cols-[1.55fr_.95fr]">
        <div className="space-y-3">
          {goal && !editingWork ? <WorkContractCard goal={goal} onReplace={() => { setInitialWork({ title: currentGoal, definitionOfDone: goal.work_contract?.definition_of_done || [], targetModel: goal.work_contract?.agent?.target_model || "" }); setEditingWork(true); }} onStop={clearGoal} stopping={clearCurrentGoal.isPending} /> : <StartWorkPanel adapters={adaptersQuery.data?.items || []} error={startWorkSession.error?.message} initialWork={initialWork} isPending={startWorkSession.isPending} onStart={beginWork} />}
          <div className="flex flex-wrap gap-2 text-[10px] font-bold text-[#68685f] dark:text-[#aaa9a0]">
            <Metric icon={GitBranch} label={repoPath ? repoPath.split("/").filter(Boolean).pop() : "Repository not indexed"} />
            <Metric icon={Bot} label={`${sourceCount} captured source${sourceCount === 1 ? "" : "s"}`} />
            <Metric icon={Clock3} label={digest.generated_at ? `Updated ${formatTimeAgo(digest.generated_at)}` : "Update time unavailable"} />
          </div>
        </div>

        <article className="rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-6 shadow-sm dark:border-[#292925] dark:bg-[#141411]">
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.16em] text-[#85857c]">
            <CheckCircle2 className="h-3.5 w-3.5" /> Latest observed result
          </div>
          {latestOutcome ? (
            <>
              <p className="mt-5 text-base font-black leading-6 text-[#171713] dark:text-white">{cleanDisplayText(latestOutcome.summary)}</p>
              <div className="mt-4 grid grid-cols-2 gap-2">
                <OutcomeMetric label="Recorded model" value={latestOutcome.model || "Unreported"} />
                <OutcomeMetric label="Verification" value={`${latestOutcome.verification?.passed || 0}/${latestOutcome.verification?.observed || 0} passed`} />
                <OutcomeMetric label="Files changed" value={latestOutcome.changed_files?.length || 0} />
                <OutcomeMetric label="Status" value={cleanDisplayText(latestOutcome.status || "Observed")} />
              </div>
              <p className="mt-3 text-[10px] font-semibold text-[#85857c]">{latestOutcome.tool ? `${latestOutcome.tool} · ` : ""}Observed {formatTimeAgo(latestOutcome.observed_at)}{latestOutcome.head_commit ? ` · ${String(latestOutcome.head_commit).slice(0, 7)}` : ""}</p>
              <Link to={`/app/runs${latestOutcome.run_id ? `?run=${encodeURIComponent(latestOutcome.run_id)}` : ""}`} className="mt-5 inline-flex items-center gap-1.5 text-xs font-black text-[#171713] underline underline-offset-4 dark:text-[#d9ff68]">
                Inspect this run <ArrowRight className="h-3 w-3" />
              </Link>
              {latestOutcome.verified_success && goal?.source_kind !== "active_agent_run" ? <button type="button" onClick={() => completeCurrentGoal.mutate({ runId: latestOutcome.run_id })} disabled={completeCurrentGoal.isPending} className="mt-4 block w-full rounded-lg bg-emerald-700 px-3 py-2.5 text-xs font-black text-white disabled:opacity-50 dark:bg-emerald-300 dark:text-emerald-950">{completeCurrentGoal.isPending ? "Completing work…" : "Accept result and complete work"}</button> : <Link to="/app/runs" className="mt-4 block rounded-lg border border-[#d8d8cf] px-3 py-2.5 text-center text-xs font-black dark:border-[#33332e]">Continue or retry</Link>}
              {completeCurrentGoal.isError ? <p role="alert" className="mt-2 text-[10px] font-bold text-red-600 dark:text-red-400">{completeCurrentGoal.error?.message || "The goal could not be completed."}</p> : null}
            </>
          ) : (
            <><p className="mt-5 text-sm leading-6 text-[#68685f] dark:text-[#aaa9a0]">No observed result is attached to this work yet. After the harness runs, this card shows changed files, checks, blockers, and the recorded model.</p>{goal ? <Link to="/app/runs" className="mt-5 inline-flex items-center gap-1.5 text-xs font-black underline underline-offset-4">Run or inspect the agent <ArrowRight className="h-3 w-3" /></Link> : null}</>
          )}
        </article>
      </section>

      <section className="grid gap-4 lg:grid-cols-[1.2fr_.8fr]">
        <article className="rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-6 dark:border-[#292925] dark:bg-[#141411]">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.16em] text-[#85857c]">
              <ShieldAlert className="h-3.5 w-3.5" /> Needs attention
            </div>
            <Link to="/app/work?view=attention" className="rounded-full bg-amber-100 px-2 py-1 text-[9px] font-black text-amber-800 underline underline-offset-2 dark:bg-amber-950/50 dark:text-amber-200">View all {allAttentionCards.length}</Link>
          </div>
          {attentionCards.length ? (
            <div className="mt-4 divide-y divide-[#e6e6de] dark:divide-[#292925]">
              {attentionCards.map((card) => (
                <div key={card.id} className="flex items-start justify-between gap-3 py-4 first:pt-0 last:pb-0">
                  <div>
                  <p className="text-sm font-black text-[#171713] dark:text-white">{cleanDisplayText(card.title)}</p>
                  <p className="mt-1.5 line-clamp-2 text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">{distinctCardDetail(card, "Open the evidence record for the latest observed detail.")}</p>
                  </div>
                  <Link aria-label={`Inspect ${cleanDisplayText(card.title)}`} to={`/app/explain?card=${encodeURIComponent(card.id)}`} className="shrink-0 rounded-lg border border-[#d8d8cf] p-2 text-[#68685f] dark:border-[#33332e] dark:text-[#d8d8cf]"><ArrowRight className="h-3.5 w-3.5" /></Link>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-4 text-sm leading-6 text-[#68685f] dark:text-[#aaa9a0]">No blocker, conflict, stale evidence, or high-risk review is currently visible.</p>
          )}
        </article>

        <article className="rounded-2xl border border-[#171713] bg-[#171713] p-6 text-white dark:border-[#d9ff68] dark:bg-[#d9ff68] dark:text-[#171713]">
          <p className="text-[10px] font-black uppercase tracking-[0.16em] opacity-60">Suggested next · not selected</p>
          <p className="mt-4 text-lg font-black leading-7">{recommendedAction || "No actionable backlog item is strong enough to suggest yet."}</p>
          <p className="mt-3 text-xs leading-5 opacity-70">Suggestions come from visible source-backed work. Starting one still requires completion criteria and an agent choice.</p>
          {suggestedCard ? (
            <button type="button" onClick={() => startFromCard(suggestedCard)} className="mt-6 inline-flex items-center gap-2 rounded-lg bg-white px-3.5 py-2.5 text-xs font-black text-[#171713] dark:bg-[#171713] dark:text-white">
              Set up this work <ArrowRight className="h-3.5 w-3.5" />
            </button>
          ) : null}
        </article>
      </section>

      <section className="rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-6 dark:border-[#292925] dark:bg-[#141411]">
        <div className="flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.16em] text-[#85857c]"><ListTodo className="h-3.5 w-3.5" /> Backlog</div>
          <Link to="/app/work?view=backlog" className="text-[10px] font-black text-[#85857c] underline underline-offset-4">View all {backlogCards.length}</Link>
        </div>
        {backlogCards.length ? (
          <div className="mt-4 grid gap-2 md:grid-cols-2">
            {backlogCards.slice(0, 4).map((card) => (
              <button key={card.id} type="button" onClick={() => startFromCard(card)} className="rounded-lg border border-[#e1e1d9] p-3 text-left transition hover:border-[#aaa99f] dark:border-[#2d2d28] dark:hover:border-[#57574f]">
                <span className="block text-xs font-black text-[#171713] dark:text-white">{cleanDisplayText(card.title)}</span>
                <span className="mt-1 block text-[10px] font-semibold text-[#85857c]">Define done and choose an agent</span>
              </button>
            ))}
          </div>
        ) : <p className="mt-4 text-sm text-[#68685f] dark:text-[#aaa9a0]">No actionable issues or tasks are currently captured.</p>}
      </section>
    </div>
  );
}

function Metric({ icon: Icon, label }) {
  return <span className="inline-flex items-center gap-1.5 rounded-full bg-[#efefe7] px-2.5 py-1.5 dark:bg-[#252521]"><Icon className="h-3 w-3" />{label}</span>;
}

function OutcomeMetric({ label, value }) {
  return <div className="rounded-lg bg-[#efefe7] p-2.5 dark:bg-[#252521]"><p className="truncate text-xs font-black">{value}</p><p className="mt-1 text-[8px] font-black uppercase tracking-wide text-[#85857c]">{label}</p></div>;
}

function distinctCardDetail(card, fallback) {
  if (!card) return fallback;
  const title = cleanDisplayText(card.title);
  for (const candidate of [card.summary, card.next_action, card.why_it_matters]) {
    let detail = cleanDisplayText(candidate);
    if (!detail) continue;
    if (title && detail.toLowerCase().startsWith(title.toLowerCase())) {
      detail = detail.slice(title.length).trim();
    }
    detail = detail
      .replace(/^State:\s*\S+\s*/i, "")
      .replace(/^Labels:\s*none\s*/i, "")
      .trim();
    if (detail && detail.toLowerCase() !== title.toLowerCase()) return detail;
  }
  return fallback;
}

function PageState({ title, detail, error = false }) {
  return (
    <div className={`mx-auto max-w-xl rounded-2xl border p-8 text-center ${error ? "border-red-200 bg-red-50 dark:border-red-900/60 dark:bg-red-950/30" : "border-[#d8d8cf] bg-[#fbfbf6] dark:border-[#292925] dark:bg-[#141411]"}`}>
      <h1 className="text-lg font-black">{title}</h1>
      {detail ? <p className="mt-2 text-sm text-[#68685f] dark:text-[#aaa9a0]">{detail}</p> : null}
    </div>
  );
}
