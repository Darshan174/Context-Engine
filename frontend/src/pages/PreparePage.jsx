import { useEffect, useMemo, useState } from "react";
import {
  Check,
  Clipboard,
  Download,
  ExternalLink,
  FileText,
  History,
  Loader2,
  PackageCheck,
  ShieldCheck,
  XCircle,
} from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import WorkspaceTopicGate from "../components/WorkspaceTopicGate";
import {
  useContextDigest,
  useContextPack,
  useContextPacks,
  usePrepareContext,
} from "../context-map/api";
import { cleanDisplayText, formatTimeAgo } from "../context-map/digest";
import { readWorkspacePreferences, writeWorkspacePreferences } from "../context/workspacePreferences";
import { useProductWorkspace } from "./useProductWorkspace";

export default function PreparePage() {
  const workspace = useProductWorkspace();
  const digestQuery = useContextDigest(workspace.activeWorkspaceId);
  const prepareContext = usePrepareContext();
  const packsQuery = useContextPacks(workspace.activeWorkspaceId);
  const [searchParams] = useSearchParams();
  const initialPreferences = readWorkspacePreferences(
    workspace.activeWorkspaceId,
    "prepare",
    { targetModel: "", tokenBudget: "4000" },
  );
  const [objective, setObjective] = useState(searchParams.get("objective") || "");
  const [targetModel, setTargetModel] = useState(initialPreferences.targetModel);
  const [tokenBudget, setTokenBudget] = useState(initialPreferences.tokenBudget);
  const [selectedPackId, setSelectedPackId] = useState(null);
  const [copied, setCopied] = useState(false);
  const selectedPackQuery = useContextPack(workspace.activeWorkspaceId, selectedPackId);

  const result = selectedPackId ? selectedPackQuery.data : prepareContext.data;
  const rendering = result?.manifest?.rendering || {};
  const profile = result?.manifest?.target_model?.profile;
  const resultModel = result?.manifest?.target_model?.name;
  const readiness = Math.round(result?.health_score ?? 0);
  const health = result?.manifest?.context_health || {};
  const readinessStatus = contextReadiness(readiness);
  const selectedTokens = result?.manifest?.token_accounting?.selected_item_tokens;
  const selectedItems = result?.selected_context || [];
  const excludedItems = result?.excluded_context || [];
  const exclusionSummary = useMemo(() => countBy(excludedItems, "reason"), [excludedItems]);
  const currentGoal = digestQuery.data?.current_goal || null;
  const objectiveMatchesGoal = normalized(objective) === normalized(currentGoal?.title);

  useEffect(() => {
    writeWorkspacePreferences(workspace.activeWorkspaceId, "prepare", {
      targetModel,
      tokenBudget,
    });
  }, [workspace.activeWorkspaceId, targetModel, tokenBudget]);

  useEffect(() => {
    if (objective || !digestQuery.data) return;
    const focus = digestQuery.data.oversight?.current_focus?.title;
    const task = (digestQuery.data.cards || []).find((card) => card.category === "task");
    setObjective(cleanDisplayText(focus || task?.title || ""));
  }, [digestQuery.data, objective]);

  useEffect(() => {
    setSelectedPackId(null);
    setCopied(false);
    prepareContext.reset?.();
  }, [workspace.activeWorkspaceId]);

  if (!workspace.workspacesQuery.isLoading && !workspace.activeWorkspaceId) {
    return <WorkspaceTopicGate workspaces={workspace.workspaces} selectedId={workspace.selectedId} onSelect={workspace.setSelectedId} />;
  }

  const submit = async (event) => {
    event.preventDefault();
    setCopied(false);
    setSelectedPackId(null);
    await prepareContext.mutateAsync({
      objective: objective.trim(),
      objective_origin: "trusted_human",
      workspace_id: workspace.activeWorkspaceId,
      workspace_goal_id: objectiveMatchesGoal ? currentGoal?.id : undefined,
      focus_component_id: objectiveMatchesGoal ? currentGoal?.component_id || undefined : undefined,
      repo_path: digestQuery.data?.scope?.project_paths?.[0] || undefined,
      target_model: targetModel.trim() || undefined,
      token_budget: Number(tokenBudget),
      mode: "task",
    });
  };

  const copyBrief = async () => {
    await navigator.clipboard.writeText(result.markdown);
    setCopied(true);
  };

  const downloadBrief = () => {
    const blob = new Blob([result.markdown], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement("a");
    anchor.href = url;
    anchor.download = `context-pack-${result.context_pack_id}.md`;
    anchor.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="relative mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-[#85857c]">{workspace.activeWorkspace?.name || "Project"}</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight">Prepare</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#68685f] dark:text-[#aaa9a0]">Compile and recover source-backed agent briefs as durable project artifacts.</p>
        </div>
        {selectedPackId ? <button type="button" onClick={() => { setSelectedPackId(null); setCopied(false); }} className="text-xs font-black underline underline-offset-4">Prepare a new pack</button> : null}
      </header>

      <div className="grid items-start gap-5 xl:grid-cols-[.72fr_1.28fr]">
        <div className="space-y-5">
          <form onSubmit={submit} className="space-y-5 rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-6 dark:border-[#292925] dark:bg-[#141411]">
            <label className="block">
              <span className="text-xs font-black">Task</span>
              <textarea aria-label="Task" required value={objective} onChange={(event) => setObjective(event.target.value)} rows={5} placeholder="Fix the authentication redirect loop and add focused tests" className="mt-2 w-full resize-none rounded-xl border border-[#d8d8cf] bg-white px-3.5 py-3 text-sm font-semibold leading-6 outline-none focus:border-[#77776e] dark:border-[#33332e] dark:bg-[#0f0f0c]" />
            </label>
            {currentGoal ? <p className={`rounded-lg px-3 py-2 text-[10px] font-bold ${objectiveMatchesGoal ? "bg-emerald-50 text-emerald-800 dark:bg-emerald-950/30 dark:text-emerald-200" : "bg-amber-50 text-amber-900 dark:bg-amber-950/30 dark:text-amber-200"}`}>{objectiveMatchesGoal ? "This pack will remain attached to the current goal." : "This task differs from the current goal, so the pack will remain an independent artifact."}</p> : null}
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="block">
                <span className="text-xs font-black">Target model label <span className="font-semibold text-[#85857c]">(optional)</span></span>
                <input aria-label="Target model" value={targetModel} onChange={(event) => setTargetModel(event.target.value)} placeholder="e.g. qwen2.5-coder-7b" className="mt-2 h-10 w-full rounded-lg border border-[#d8d8cf] bg-white px-3 text-xs font-semibold outline-none focus:border-[#77776e] dark:border-[#33332e] dark:bg-[#0f0f0c]" />
                <span className="mt-1.5 block text-[10px] font-semibold leading-4 text-[#85857c]">Capabilities are inferred conservatively; provider probing is not connected yet.</span>
              </label>
              <label className="block">
                <span className="text-xs font-black">Context budget</span>
                <input aria-label="Context budget" type="number" min="300" step="100" required value={tokenBudget} onChange={(event) => setTokenBudget(event.target.value)} className="mt-2 h-10 w-full rounded-lg border border-[#d8d8cf] bg-white px-3 text-xs font-semibold outline-none focus:border-[#77776e] dark:border-[#33332e] dark:bg-[#0f0f0c]" />
              </label>
            </div>
            {prepareContext.isError ? <p role="alert" className="text-xs font-bold leading-5 text-red-600">{prepareContext.error?.message || "The context pack could not be prepared."}</p> : null}
            <button type="submit" disabled={prepareContext.isPending || !objective.trim()} className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#171713] px-4 text-xs font-black text-white disabled:opacity-50 dark:bg-[#d9ff68] dark:text-[#171713]">
              {prepareContext.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <PackageCheck className="h-4 w-4" />}
              {prepareContext.isPending ? "Compiling evidence…" : "Compile context"}
            </button>
          </form>

          <PackHistory packs={packsQuery.data?.items || []} loading={packsQuery.isLoading} selectedPackId={selectedPackId} onOpen={(id) => { prepareContext.reset?.(); setSelectedPackId(id); setCopied(false); }} />
        </div>

        <section aria-label="Compiled context result" className="min-h-[520px] rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-6 dark:border-[#292925] dark:bg-[#141411]">
          {selectedPackQuery.isLoading ? <ResultState icon={Loader2} title="Reopening saved context pack…" spin /> : null}
          {selectedPackQuery.isError ? <ResultState icon={XCircle} title="Could not reopen context pack" detail={selectedPackQuery.error?.message} /> : null}
          {!result && !selectedPackQuery.isLoading ? <ResultState icon={FileText} title="No context pack open" detail="Compile one task or reopen a saved pack. Every result remains available in this workspace." /> : null}
          {result ? (
            <div className="space-y-6">
              <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
                <div>
                  <div className={`flex items-center gap-2 ${readinessStatus.tone}`}><ShieldCheck className="h-4 w-4" /><span className="text-[10px] font-black uppercase tracking-[0.14em]">{readinessStatus.label}</span></div>
                  <h2 className="mt-2 text-lg font-black">{cleanDisplayText(result.objective || result.manifest?.objective) || resultModel || "Saved context pack"}</h2>
                  <p className="mt-1 text-xs font-semibold text-[#68685f] dark:text-[#aaa9a0]">{profileDescription(profile, resultModel)} · {rendering.estimated_tokens ?? selectedTokens ?? "Unknown"} estimated tokens</p>
                  <p className="mt-1 font-mono text-[10px] text-[#85857c]">Pack {result.context_pack_id}</p>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button type="button" onClick={copyBrief} className="inline-flex h-9 items-center gap-2 rounded-lg bg-[#171713] px-3 text-[10px] font-black text-white dark:bg-[#d9ff68] dark:text-[#171713]"><Clipboard className="h-3.5 w-3.5" />{copied ? "Copied" : "Copy brief"}</button>
                  <button type="button" onClick={downloadBrief} className="inline-flex h-9 items-center gap-2 rounded-lg border border-[#d8d8cf] px-3 text-[10px] font-black dark:border-[#33332e]"><Download className="h-3.5 w-3.5" />Download</button>
                </div>
              </div>

              <div className="grid grid-cols-3 gap-2">
                <ResultMetric value={selectedItems.length} label="Selected" />
                <ResultMetric value={excludedItems.length} label="Excluded" />
                <ResultMetric value={`${readiness}%`} label="Readiness" />
              </div>

              {readiness < 70 ? <div role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-semibold leading-5 text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/30 dark:text-amber-100"><strong>Review before handoff.</strong> {healthSummary(health)}</div> : null}

              <EvidenceList title="Included evidence" items={selectedItems} selected />
              <EvidenceList title={`Excluded evidence · ${excludedItems.length}`} items={excludedItems} exclusionSummary={exclusionSummary} />

              <details className="rounded-lg border border-[#e2e2da] dark:border-[#292925]">
                <summary className="cursor-pointer p-3 text-xs font-black uppercase tracking-[0.12em]">Preview compiled brief</summary>
                <pre className="max-h-96 overflow-auto whitespace-pre-wrap border-t border-[#e2e2da] bg-[#0f0f0c] p-4 text-xs leading-5 text-[#e8e8e0] dark:border-[#292925]">{result.markdown}</pre>
              </details>
              <p className="text-[10px] font-semibold text-[#85857c]">This artifact is saved. Nothing is sent to an agent automatically.</p>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function PackHistory({ packs, loading, selectedPackId, onOpen }) {
  return (
    <section className="rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-5 dark:border-[#292925] dark:bg-[#141411]">
      <div className="flex items-center justify-between gap-3"><h2 className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em]"><History className="h-4 w-4" />Pack history</h2><span className="text-[10px] font-bold text-[#85857c]">{packs.length} saved</span></div>
      {loading ? <p className="mt-4 text-xs text-[#85857c]">Loading saved packs…</p> : null}
      {!loading && !packs.length ? <p className="mt-4 text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">No packs have been compiled for this workspace yet.</p> : null}
      {packs.length ? <div className="mt-3 max-h-80 space-y-2 overflow-auto">{packs.map((pack) => (
        <button key={pack.context_pack_id} type="button" onClick={() => onOpen(pack.context_pack_id)} className={`block w-full rounded-lg border p-3 text-left ${selectedPackId === pack.context_pack_id ? "border-[#171713] bg-[#efefe7] dark:border-[#d9ff68] dark:bg-[#252521]" : "border-[#e2e2da] hover:border-[#aaa99f] dark:border-[#292925]"}`}>
          <span className="block truncate text-xs font-black">{cleanDisplayText(pack.objective)}</span>
          <span className="mt-1 block text-[10px] font-semibold text-[#85857c]">{formatTimeAgo(pack.created_at)} · {pack.selected_count} selected · {pack.run_count} runs</span>
        </button>
      ))}</div> : null}
    </section>
  );
}

function EvidenceList({ title, items, selected = false, exclusionSummary = {} }) {
  return (
    <section>
      <div className="flex flex-wrap items-center justify-between gap-2"><h3 className="text-xs font-black uppercase tracking-[0.14em] text-[#68685f] dark:text-[#c6c6bd]">{title}</h3>{!selected && items.length ? <span className="text-[10px] font-semibold text-[#85857c]">{Object.entries(exclusionSummary).map(([reason, count]) => `${humanReason(reason)} ${count}`).join(" · ")}</span> : null}</div>
      {items.length ? <div className="mt-3 space-y-2">{items.map((item) => <EvidenceItem key={item.id} item={item} selected={selected} />)}</div> : <p className="mt-3 text-xs text-[#85857c]">None.</p>}
    </section>
  );
}

function EvidenceItem({ item, selected }) {
  const citations = item.citations || (item.citation ? [item.citation] : []);
  const sourceId = item.source_document_id || citations.find((citation) => citation?.source_document_id)?.source_document_id;
  return (
    <details className="rounded-lg border border-[#e2e2da] bg-white dark:border-[#292925] dark:bg-[#0f0f0c]">
      <summary className="cursor-pointer list-none p-3">
        <span className="flex items-start justify-between gap-3"><span><span className="block text-xs font-black">{cleanDisplayText(item.title) || item.item_type || "Evidence item"}</span><span className="mt-1 block text-[10px] font-semibold text-[#85857c]">{selected ? humanReason(item.inclusion_reason) : humanReason(item.reason)} · score {Number(item.score || 0).toFixed(2)} · {item.token_cost || 0} tokens</span></span><span className={`rounded-full px-2 py-1 text-[9px] font-black uppercase ${selected ? "bg-emerald-100 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200" : "bg-slate-100 text-slate-600 dark:bg-neutral-900 dark:text-neutral-300"}`}>{selected ? "Included" : "Excluded"}</span></span>
      </summary>
      <div className="space-y-3 border-t border-[#e2e2da] px-3 py-3 text-xs leading-5 text-[#68685f] dark:border-[#292925] dark:text-[#aaa9a0]">
        {item.summary ? <p>{cleanDisplayText(item.summary)}</p> : null}
        {item.reason_detail ? <p>{cleanDisplayText(item.reason_detail)}</p> : null}
        <dl className="grid gap-2 sm:grid-cols-2"><EvidenceField label="Trust" value={humanReason(item.trust_zone)} /><EvidenceField label="Truth state" value={humanReason(item.truth_state)} /><EvidenceField label="Revision" value={item.source_revision_number ? `Source revision ${item.source_revision_number}` : "Not supplied"} /><EvidenceField label="Provenance" value={item.provenance_verified === true ? "Verified" : item.provenance_verified === false ? "Not verified" : "Not available"} /></dl>
        {citations.map((citation, index) => <blockquote key={`${citation?.citation_id || "citation"}-${index}`} className="rounded-lg bg-[#efefe7] p-3 text-xs dark:bg-[#252521]">{citation?.quote || citation?.excerpt || "Citation metadata recorded without an excerpt."}</blockquote>)}
        {sourceId ? <Link to={`/app/sources?source=${encodeURIComponent(sourceId)}`} className="inline-flex items-center gap-1.5 text-xs font-black text-[#171713] underline underline-offset-4 dark:text-[#d9ff68]">Inspect source and revision <ExternalLink className="h-3 w-3" /></Link> : <p className="text-[10px] font-semibold text-[#85857c]">No external source document applies to this compiler-generated item.</p>}
      </div>
    </details>
  );
}

function EvidenceField({ label, value }) {
  return <div><dt className="text-[9px] font-black uppercase tracking-wide text-[#85857c]">{label}</dt><dd className="mt-0.5 font-semibold">{value || "Not available"}</dd></div>;
}

function ResultState({ icon: Icon, title, detail, spin = false }) {
  return <div className="flex min-h-[450px] flex-col items-center justify-center text-center"><Icon className={`h-9 w-9 text-[#aaa9a0] ${spin ? "animate-spin" : ""}`} /><h2 className="mt-4 text-base font-black">{title}</h2>{detail ? <p className="mt-2 max-w-sm text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">{detail}</p> : null}</div>;
}

function ResultMetric({ value, label }) {
  return <div className="rounded-xl bg-[#efefe7] p-3 text-center dark:bg-[#252521]"><p className="text-lg font-black">{value}</p><p className="mt-0.5 text-[10px] font-bold uppercase tracking-wide text-[#85857c]">{label}</p></div>;
}

function countBy(items, key) {
  return items.reduce((counts, item) => ({ ...counts, [item[key] || "not_selected"]: (counts[item[key] || "not_selected"] || 0) + 1 }), {});
}

function profileLabel(profile) {
  return ({ small_coder_model: "Concise small-model profile", general_coder_model: "Structured general-model profile", frontier_coder_model: "Frontier-model profile" })[profile] || "Adaptive model profile";
}

function profileDescription(profile, model) {
  return model && model !== "default" ? `${profileLabel(profile)} inferred for ${model}` : `Conservative default (${profileLabel(profile).toLowerCase()})`;
}

function contextReadiness(score) {
  if (score >= 70) return { label: "Brief compiled", tone: "text-emerald-700 dark:text-emerald-300" };
  if (score >= 40) return { label: "Brief compiled — review recommended", tone: "text-amber-700 dark:text-amber-300" };
  return { label: "Brief compiled — evidence weak", tone: "text-red-700 dark:text-red-300" };
}

function healthSummary(health) {
  const reasons = (health.reasons || []).slice(0, 3).map((reason) => humanReason(reason).replaceAll(":", ": "));
  if (reasons.length) return `Readiness is reduced by ${reasons.join(", ").toLowerCase()}.`;
  return "Readiness is below the safe handoff threshold; inspect selected evidence and exclusions first.";
}

function humanReason(value) {
  return String(value || "not supplied").replaceAll("_", " ").replace(/^./, (letter) => letter.toUpperCase());
}

function normalized(value) {
  return cleanDisplayText(value).replace(/\s+/g, " ").trim();
}
