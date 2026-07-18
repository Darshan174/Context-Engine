import { useEffect, useMemo, useState } from "react";
import {
  AlertTriangle,
  ArrowRight,
  CheckCircle2,
  Clipboard,
  Clock3,
  FileCode2,
  FlaskConical,
  PlayCircle,
  RefreshCw,
  Terminal,
  XCircle,
} from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import WorkspaceTopicGate from "../components/WorkspaceTopicGate";
import { useAgentAdapters, useContextDigest, useContextPacks, useRunOutcomes } from "../context-map/api";
import { cleanDisplayText, formatTimeAgo } from "../context-map/digest";
import { useProductWorkspace } from "./useProductWorkspace";

export default function RunsPage() {
  const workspace = useProductWorkspace();
  const digestQuery = useContextDigest(workspace.activeWorkspaceId);
  const adaptersQuery = useAgentAdapters(workspace.activeWorkspaceId);
  const packsQuery = useContextPacks(workspace.activeWorkspaceId);
  const outcomesQuery = useRunOutcomes(workspace.activeWorkspaceId, { refetchInterval: 5000 });
  const [searchParams, setSearchParams] = useSearchParams();
  const [view, setView] = useState("recent");
  const [verify, setVerify] = useState(true);
  const [copied, setCopied] = useState(false);

  const report = outcomesQuery.data;
  const runs = report?.runs || [];
  const groups = report?.groups || [];
  const digest = digestQuery.data || {};
  const goal = digest.current_goal || null;
  const workContract = goal?.work_contract || {};
  const agentContract = workContract.agent || {};
  const adapterId = agentContract.adapter_id || "";
  const adapter = (adaptersQuery.data?.items || []).find((item) => item.id === adapterId) || null;
  const repoPath = digest.scope?.project_paths?.[0] || "";
  const packs = packsQuery.data?.items || [];
  const matchingPacks = goal?.id
    ? packs.filter((pack) => pack.workspace_goal_id === goal.id)
    : [];
  const requestedPackId = searchParams.get("pack");
  const latestPack = matchingPacks.find((pack) => pack.context_pack_id === requestedPackId)
    || matchingPacks[0]
    || null;
  const selectedRunId = searchParams.get("run");
  const hasGoalResult = Boolean(goal?.id && runs.some((run) => run.workspace_goal_id === goal.id));
  const generatedCommand = useMemo(() => buildHarnessCommand({
    objective: goal?.title,
    repoPath,
    workspaceId: workspace.activeWorkspaceId,
    contextPackId: latestPack?.context_pack_id,
    adapterId,
    targetModel: agentContract.target_model,
    verify,
    adapterInstalled: adapter?.installed,
  }), [adapter?.installed, adapterId, agentContract.target_model, goal?.title, latestPack?.context_pack_id, repoPath, verify, workspace.activeWorkspaceId]);

  useEffect(() => {
    setCopied(false);
  }, [workspace.activeWorkspaceId]);

  if (!workspace.workspacesQuery.isLoading && !workspace.activeWorkspaceId) {
    return <WorkspaceTopicGate workspaces={workspace.workspaces} selectedId={workspace.selectedId} onSelect={workspace.setSelectedId} />;
  }

  const selectRun = (runId) => {
    const next = new URLSearchParams(searchParams);
    next.set("run", runId);
    setSearchParams(next, { replace: true });
  };

  const copyCommand = async () => {
    await navigator.clipboard.writeText(generatedCommand);
    setCopied(true);
  };

  return (
    <div className="relative mx-auto w-full max-w-6xl space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-[#85857c]">{workspace.activeWorkspace?.name || "Project"}</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight">Runs</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#68685f] dark:text-[#aaa9a0]">Run the prepared goal locally, then inspect recorded changes and deterministic verification.</p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <button type="button" onClick={() => outcomesQuery.refetch()} disabled={outcomesQuery.isFetching} className="inline-flex h-10 items-center gap-2 rounded-lg border border-[#d8d8cf] bg-white px-3 text-[10px] font-black disabled:opacity-50 dark:border-[#33332e] dark:bg-[#171713]"><RefreshCw className={`h-3.5 w-3.5 ${outcomesQuery.isFetching ? "animate-spin" : ""}`} />Refresh observations</button>
          <div className="inline-flex rounded-xl border border-[#d8d8cf] bg-[#fbfbf6] p-1 dark:border-[#292925] dark:bg-[#141411]">
            <ViewButton active={view === "recent"} onClick={() => setView("recent")} icon={PlayCircle}>Recent</ViewButton>
            <ViewButton active={view === "compare"} onClick={() => setView("compare")} icon={FlaskConical}>Compare</ViewButton>
          </div>
        </div>
      </header>

      <RunSetup
        goal={goal}
        repoPath={repoPath}
        latestPack={latestPack}
        adapter={adapter}
        adapterId={adapterId}
        targetModel={agentContract.target_model}
        modelIdentitySource={agentContract.model_identity_source}
        verify={verify}
        generatedCommand={generatedCommand}
        copied={copied}
        hasGoalResult={hasGoalResult}
        onVerifyChange={setVerify}
        onCopy={copyCommand}
      />

      {outcomesQuery.isLoading ? <EmptyState title="Loading observed runs…" /> : null}
      {outcomesQuery.isError ? <EmptyState title="Could not load run evidence" detail={outcomesQuery.error?.message} error /> : null}

      {!outcomesQuery.isLoading && !outcomesQuery.isError && view === "recent" ? (
        runs.length ? (
          <section className="space-y-3" aria-label="Observed runs">
            {runs.map((run) => <RunCard key={run.run_id} run={run} selected={run.run_id === selectedRunId} onSelect={() => selectRun(run.run_id)} />)}
          </section>
        ) : (
          <EmptyState title="No observed harness runs yet" detail="Complete the guided setup above, paste the explicit command into a terminal on the machine that owns this repository, and this page will pick up the recorded result." />
        )
      ) : null}

      {!outcomesQuery.isLoading && !outcomesQuery.isError && view === "compare" ? (
        <div className="space-y-5">
          <section className={`rounded-2xl border p-5 ${groups.length >= 2 ? "border-amber-200 bg-amber-50 dark:border-amber-900/60 dark:bg-amber-950/25" : "border-[#d8d8cf] bg-[#fbfbf6] dark:border-[#292925] dark:bg-[#141411]"}`}>
            <div className="flex items-start gap-3">
              <AlertTriangle className={`mt-0.5 h-4 w-4 shrink-0 ${groups.length >= 2 ? "text-amber-600" : "text-[#85857c]"}`} />
              <div>
                <h2 className="text-sm font-black">{groups.length >= 2 ? "Multiple models observed; paired proof is still missing" : "A paired baseline is still missing"}</h2>
                <p className="mt-1.5 text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">These are Context Engine-linked runs grouped by their recorded model. To claim model lift, run the same task from the same commit as old alone, old with Context Engine, and new alone.</p>
              </div>
            </div>
          </section>

          {groups.length ? (
            <section className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {groups.map((group) => <ModelGroup key={`${group.model}:${group.model_profile}`} group={group} />)}
            </section>
          ) : <EmptyState title="No model outcomes to compare" detail="The comparison will appear after locally observed harness runs have deterministic outcomes and verification evidence." />}

          {report?.measurement_note ? <p className="text-[10px] font-semibold leading-5 text-[#85857c]">{report.measurement_note}</p> : null}
        </div>
      ) : null}
    </div>
  );
}

function RunSetup({ goal, repoPath, latestPack, adapter, adapterId, targetModel, modelIdentitySource, verify, generatedCommand, copied, hasGoalResult, onVerifyChange, onCopy }) {
  const ready = Boolean(goal && repoPath && latestPack && adapterId && adapter?.installed && generatedCommand);
  const criteria = goal?.work_contract?.definition_of_done || [];
  return (
    <section className="rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-5 dark:border-[#292925] dark:bg-[#141411]" aria-label="Guided harness setup">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.14em] text-[#85857c]"><Terminal className="h-3.5 w-3.5" />Launch configured agent</div>
          <h2 className="mt-2 text-lg font-black">Exact pack in. Observable result out.</h2>
          <p className="mt-1 max-w-2xl text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">The harness passes the saved pack to the configured agent, records the repository delta, runs authorized checks, and attaches the result to this work contract.</p>
        </div>
        <div className="flex flex-wrap gap-1.5 text-[9px] font-black uppercase tracking-wide">
          <Step ready={Boolean(goal && criteria.length)}>1 Work contract</Step>
          <Step ready={Boolean(latestPack)}>2 Pack</Step>
          <Step ready={Boolean(adapter?.installed)}>3 Agent</Step>
          <Step ready={hasGoalResult}>4 Result</Step>
        </div>
      </div>

      <div className="mt-5 grid gap-5 lg:grid-cols-[.9fr_1.1fr]">
        <div className="space-y-3">
          <SetupFact label="Active work" value={cleanDisplayText(goal?.title) || "No work contract"} action={!goal ? <Link to="/app" className="font-black underline underline-offset-4">Start in Now</Link> : null} />
          <SetupFact label="Done when" value={criteria.length ? `${criteria.length} explicit completion check${criteria.length === 1 ? "" : "s"}` : "Missing completion criteria"} action={goal && !criteria.length ? <Link to="/app" className="font-black underline underline-offset-4">Replace legacy goal</Link> : null} />
          <SetupFact label="Repository" value={repoPath || "No indexed repository"} />
          <SetupFact
            label="Persisted context pack"
            value={latestPack
              ? `${shortId(latestPack.context_pack_id)} · ${latestPack.selected_count} selected · ${Math.round(latestPack.health_score || 0)}% readiness`
              : goal?.source_kind === "active_agent_run"
                ? "An attached harness run is already active"
                : "No pack is attached to this work contract"}
            action={!latestPack && goal && goal.source_kind !== "active_agent_run"
              ? <Link to="/app/prepare" className="font-black underline underline-offset-4">Rebuild pack</Link>
              : latestPack
                ? <Link to={`/app/prepare?pack=${encodeURIComponent(latestPack.context_pack_id)}`} className="font-black underline underline-offset-4">Inspect pack</Link>
                : null}
          />
        </div>

        <div className="space-y-4">
          <div className="grid gap-3 sm:grid-cols-2"><SetupFact label="Agent adapter" value={adapter ? `${adapter.label} · ${adapter.version || "version unknown"}` : adapterId ? `${adapterId} · not detected` : "Not configured"} /><SetupFact label="Requested model" value={targetModel || "Provider default · unverified"} /></div>
          <div className="rounded-xl border border-[#e2e2da] p-3 text-[10px] font-semibold leading-5 text-[#68685f] dark:border-[#292925] dark:text-[#aaa9a0]"><strong className="text-[#171713] dark:text-white">Model identity:</strong> {modelIdentitySource === "configured_by_user" ? "configured by the user" : "provider default not reported to Context Engine"}. The runtime provider has not attested the model identity.</div>
          {goal && !adapterId ? <p role="status" className="rounded-lg bg-amber-50 p-3 text-[10px] font-bold text-amber-900 dark:bg-amber-950/25 dark:text-amber-100">This is a legacy goal without an agent adapter. Replace it in Now to create a runnable work contract.</p> : null}
          {adapterId && !adapter?.installed ? <p role="status" className="rounded-lg bg-amber-50 p-3 text-[10px] font-bold text-amber-900 dark:bg-amber-950/25 dark:text-amber-100">{adapter?.label || adapterId} is not detected on the Context Engine machine, so the launch command is withheld.</p> : null}
          <label className="flex items-start gap-2 rounded-lg bg-[#efefe7] p-3 text-[10px] font-semibold leading-4 dark:bg-[#252521]"><input type="checkbox" checked={verify} onChange={(event) => onVerifyChange(event.target.checked)} className="mt-0.5" /><span><strong>Run required verification after the worker.</strong> Commands come from the inspected context pack and execute only because you authorize them here.</span></label>
        </div>
      </div>

      {ready ? (
        <div className="mt-5 rounded-xl bg-[#171713] p-4 text-white dark:bg-[#0b0b09]">
          <div className="flex items-center justify-between gap-3"><p className="text-[10px] font-black uppercase tracking-[0.12em] text-[#aaa9a0]">Paste in a terminal on the repository machine</p><button type="button" onClick={onCopy} className="inline-flex items-center gap-1.5 rounded-md bg-white px-2.5 py-1.5 text-[10px] font-black text-[#171713]"><Clipboard className="h-3 w-3" />{copied ? "Copied" : "Copy command"}</button></div>
          <code className="mt-3 block overflow-x-auto whitespace-pre-wrap break-all text-[10px] leading-5 text-[#e8e8e0]">{generatedCommand}</code>
          <p className="mt-3 text-[9px] leading-4 text-[#aaa9a0]">This is a generated first-class adapter command—no raw worker command or shell pipeline. The local CLI uses direct argv execution and this page polls for its observed result.</p>
        </div>
      ) : null}
    </section>
  );
}

function RunCard({ run, selected, onSelect }) {
  const changedFiles = run.changed_files || [];
  const verification = run.verification || { passed: 0, observed: 0 };
  const state = run.verified_success
    ? { label: "Verified", icon: CheckCircle2, tone: "text-emerald-700 dark:text-emerald-300", chip: "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200" }
    : run.failed_verification
      ? { label: "Checks failed", icon: XCircle, tone: "text-red-700 dark:text-red-300", chip: "bg-red-100 text-red-800 dark:bg-red-950/50 dark:text-red-200" }
      : { label: "Unverified", icon: AlertTriangle, tone: "text-amber-700 dark:text-amber-300", chip: "bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-200" };
  const StateIcon = state.icon;
  return (
    <article id={`run-${run.run_id}`} className={`rounded-2xl border bg-[#fbfbf6] p-5 dark:bg-[#141411] ${selected ? "border-[#171713] ring-2 ring-[#171713]/10 dark:border-[#d9ff68] dark:ring-[#d9ff68]/10" : "border-[#d8d8cf] dark:border-[#292925]"}`}>
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className={`flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.13em] ${state.tone}`}><StateIcon className="h-3.5 w-3.5" />{state.label}{selected ? " · linked from Now" : ""}</div>
          <h2 className="mt-2 text-base font-black leading-6">{cleanDisplayText(run.objective) || "Recorded agent run"}</h2>
          <p className="mt-1 text-xs font-semibold text-[#68685f] dark:text-[#aaa9a0]">{run.model} · {profileLabel(run.model_profile)}{run.tool ? ` · ${run.tool}` : ""}</p>
        </div>
        <button type="button" onClick={onSelect} aria-pressed={selected} className={`w-fit rounded-full px-2.5 py-1 text-[9px] font-black ${state.chip}`}>{selected ? "Evidence open" : "Inspect evidence"}</button>
      </div>
      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4">
        <RunMetric icon={Clock3} value={durationLabel(run.duration_seconds)} label="Duration" />
        <RunMetric icon={FileCode2} value={changedFiles.length} label="Files changed" />
        <RunMetric icon={CheckCircle2} value={`${verification.passed}/${verification.observed}`} label="Checks passed" />
        <RunMetric icon={PlayCircle} value={run.completed ? "Complete" : run.status} label="Outcome" />
      </div>
      {run.outcome_summary ? <p className="mt-4 text-xs font-semibold leading-5 text-[#4f4f48] dark:text-[#d8d8cf]">{cleanDisplayText(run.outcome_summary)}</p> : null}
      {selected ? (
        <div className="mt-4 space-y-3 rounded-xl border border-[#e1e1d9] p-4 text-xs dark:border-[#2d2d28]">
          <div className="grid gap-3 sm:grid-cols-2"><EvidenceField label="Run ID" value={run.run_id} /><EvidenceField label="Context pack" value={run.context_pack_id || "Not linked"} /></div>
          {changedFiles.length ? <div><p className="text-[9px] font-black uppercase tracking-wide text-[#85857c]">Observed changed files</p><p className="mt-1 break-words font-mono text-[10px] leading-5 text-[#68685f] dark:text-[#aaa9a0]">{changedFiles.join(" · ")}</p></div> : null}
          {run.context_pack_id ? <Link to={`/app/prepare?pack=${encodeURIComponent(run.context_pack_id)}`} className="inline-flex items-center gap-1.5 text-xs font-black underline underline-offset-4">Inspect exact context pack <ArrowRight className="h-3 w-3" /></Link> : null}
        </div>
      ) : changedFiles.length ? <p className="mt-4 break-words font-mono text-[10px] leading-5 text-[#68685f] dark:text-[#aaa9a0]">{changedFiles.slice(0, 5).join(" · ")}</p> : null}
      <p className="mt-3 text-[10px] font-semibold text-[#85857c]">{run.started_at ? `Started ${formatTimeAgo(run.started_at)}` : "Start time unavailable"}{run.unresolved_blocker ? " · unresolved blocker recorded" : ""}</p>
    </article>
  );
}

function ModelGroup({ group }) {
  const successRate = group.verified_success_rate === null ? null : Math.round(group.verified_success_rate * 100);
  return (
    <article className="rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-5 dark:border-[#292925] dark:bg-[#141411]">
      <p className="text-[10px] font-black uppercase tracking-[0.14em] text-[#85857c]">Recorded model</p>
      <h2 className="mt-2 break-words text-base font-black">{group.model}</h2>
      <p className="mt-1 text-[10px] font-semibold text-[#85857c]">{profileLabel(group.model_profile)}</p>
      <div className="mt-5 flex items-end justify-between gap-3">
        <div><p className="text-3xl font-black">{successRate === null ? "—" : `${successRate}%`}</p><p className="mt-1 text-[9px] font-black uppercase tracking-wide text-[#85857c]">Verified success</p></div>
        <p className="text-right text-xs font-bold text-[#68685f] dark:text-[#aaa9a0]">{group.verified_successful_runs}/{group.observed_runs} runs</p>
      </div>
      <div className="mt-4 h-2 overflow-hidden rounded-full bg-[#e6e6de] dark:bg-[#292925]"><div className="h-full rounded-full bg-emerald-500" style={{ width: `${successRate || 0}%` }} /></div>
      <div className="mt-4 flex flex-wrap gap-2 text-[9px] font-bold text-[#68685f] dark:text-[#aaa9a0]"><span>{group.failed_verification_runs} failed checks</span><span>·</span><span>{group.unresolved_blocker_runs} blocked</span></div>
    </article>
  );
}

function Step({ ready, children }) {
  return <span className={`rounded-full px-2 py-1 ${ready ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200" : "bg-[#efefe7] text-[#85857c] dark:bg-[#252521]"}`}>{ready ? "✓ " : ""}{children}</span>;
}

function SetupFact({ label, value, action = null }) {
  return <div className="rounded-xl bg-[#efefe7] p-3 dark:bg-[#252521]"><p className="text-[9px] font-black uppercase tracking-wide text-[#85857c]">{label}</p><div className="mt-1 flex items-start justify-between gap-3"><p className="min-w-0 break-words text-xs font-black">{value}</p>{action ? <div className="shrink-0 text-[10px]">{action}</div> : null}</div></div>;
}

function EvidenceField({ label, value }) {
  return <div><p className="text-[9px] font-black uppercase tracking-wide text-[#85857c]">{label}</p><p className="mt-1 break-all font-mono text-[10px]">{value}</p></div>;
}

function RunMetric({ icon: Icon, value, label }) {
  return <div className="rounded-xl bg-[#efefe7] p-3 dark:bg-[#252521]"><div className="flex items-center gap-1.5"><Icon className="h-3 w-3 text-[#85857c]" /><span className="text-sm font-black">{value}</span></div><p className="mt-1 text-[9px] font-bold uppercase tracking-wide text-[#85857c]">{label}</p></div>;
}

function ViewButton({ active, onClick, icon: Icon, children }) {
  return <button type="button" onClick={onClick} aria-pressed={active} className={`inline-flex h-8 items-center gap-1.5 rounded-lg px-3 text-[10px] font-black ${active ? "bg-[#171713] text-white dark:bg-[#d9ff68] dark:text-[#171713]" : "text-[#68685f] dark:text-[#aaa9a0]"}`}><Icon className="h-3.5 w-3.5" />{children}</button>;
}

function EmptyState({ title, detail, error = false }) {
  return <div className={`rounded-2xl border p-10 text-center ${error ? "border-red-200 bg-red-50 dark:border-red-900/60 dark:bg-red-950/25" : "border-dashed border-[#d8d8cf] bg-[#fbfbf6] dark:border-[#292925] dark:bg-[#141411]"}`}><h2 className="text-base font-black">{title}</h2>{detail ? <p className="mx-auto mt-2 max-w-xl text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">{detail}</p> : null}</div>;
}

function buildHarnessCommand({ objective, repoPath, workspaceId, contextPackId, adapterId, targetModel, verify, adapterInstalled }) {
  if (!objective || !repoPath || !workspaceId || !contextPackId || !adapterId || !adapterInstalled) return "";
  const args = [
    "ctxe", "harness", "run", shellQuote(objective),
    "--repo", shellQuote(repoPath),
    "--workspace-id", shellQuote(workspaceId),
    "--context-pack-id", shellQuote(contextPackId),
    "--adapter", shellQuote(adapterId),
    ...(targetModel ? ["--target-model", shellQuote(targetModel)] : []),
    ...(verify ? ["--verify"] : []),
  ];
  return args.join(" ");
}

function shellQuote(value) {
  const text = String(value || "");
  if (/^[a-zA-Z0-9_./:{}@+-]+$/.test(text)) return text;
  return `'${text.replaceAll("'", `'"'"'`)}'`;
}

function durationLabel(seconds) {
  if (!Number.isFinite(Number(seconds))) return "—";
  const value = Number(seconds);
  if (value < 60) return `${Math.round(value)}s`;
  return `${Math.floor(value / 60)}m ${Math.round(value % 60)}s`;
}

function profileLabel(value) {
  return String(value || "unreported").replace("_coder_model", "").replaceAll("_", " ");
}

function shortId(value) {
  const text = String(value || "");
  return text.length > 12 ? `…${text.slice(-10)}` : text;
}
