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
  useContextPackComparison,
  useContextPacks,
  usePrepareContext,
} from "../context-map/api";
import { cleanDisplayText, formatTimeAgo } from "../context-map/digest";
import { useProductWorkspace } from "./useProductWorkspace";

export default function PreparePage() {
  const workspace = useProductWorkspace();
  const digestQuery = useContextDigest(workspace.activeWorkspaceId);
  const prepareContext = usePrepareContext();
  const packsQuery = useContextPacks(workspace.activeWorkspaceId);
  const [searchParams, setSearchParams] = useSearchParams();
  const requestedPackId = searchParams.get("pack");
  const [selectedPackId, setSelectedPackId] = useState(requestedPackId);
  const [comparisonPackIds, setComparisonPackIds] = useState([]);
  const [copied, setCopied] = useState(false);
  const selectedPackQuery = useContextPack(workspace.activeWorkspaceId, selectedPackId);
  const comparisonQuery = useContextPackComparison(workspace.activeWorkspaceId, comparisonPackIds);

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
  const workContract = currentGoal?.work_contract || {};
  const contractAgent = workContract.agent || {};
  const contractContext = workContract.context || {};

  useEffect(() => {
    setSelectedPackId(requestedPackId || null);
    setCopied(false);
    setComparisonPackIds([]);
    prepareContext.reset?.();
  }, [requestedPackId, workspace.activeWorkspaceId]);

  if (!workspace.workspacesQuery.isLoading && !workspace.activeWorkspaceId) {
    return <WorkspaceTopicGate workspaces={workspace.workspaces} selectedId={workspace.selectedId} onSelect={workspace.setSelectedId} />;
  }

  const rebuild = async () => {
    if (!currentGoal) return;
    setCopied(false);
    setSelectedPackId(null);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete("pack");
    setSearchParams(nextParams, { replace: true });
    await prepareContext.mutateAsync({
      objective: currentGoal.title,
      objective_origin: "trusted_human",
      workspace_id: workspace.activeWorkspaceId,
      workspace_goal_id: currentGoal.id,
      focus_component_id: currentGoal.component_id || undefined,
      repo_path: digestQuery.data?.scope?.project_paths?.[0] || undefined,
      target_model: contractAgent.target_model || undefined,
      token_budget: Number(contractContext.token_budget || 4000),
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

  const openSavedPack = (id) => {
    prepareContext.reset?.();
    setSelectedPackId(id);
    setCopied(false);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.set("pack", id);
    setSearchParams(nextParams, { replace: true });
  };

  const prepareNewPack = () => {
    setSelectedPackId(null);
    setCopied(false);
    const nextParams = new URLSearchParams(searchParams);
    nextParams.delete("pack");
    setSearchParams(nextParams, { replace: true });
  };

  const toggleComparisonPack = (id) => {
    setComparisonPackIds((current) => (
      current.includes(id)
        ? current.filter((value) => value !== id)
        : [...current.slice(-1), id]
    ));
  };

  return (
    <div className="relative mx-auto w-full max-w-7xl space-y-6">
      <header className="flex flex-col justify-between gap-4 sm:flex-row sm:items-end">
        <div>
          <p className="text-xs font-black uppercase tracking-[0.18em] text-[#85857c]">{workspace.activeWorkspace?.name || "Project"}</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight">Context pack</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#68685f] dark:text-[#aaa9a0]">Review what the agent will receive, why each item was included, and what was left out.</p>
        </div>
        {selectedPackId ? <button type="button" onClick={prepareNewPack} className="text-xs font-black underline underline-offset-4">Back to active work</button> : null}
      </header>

      <div className="grid items-start gap-5 xl:grid-cols-[.72fr_1.28fr]">
        <div className="space-y-5">
          <section className="space-y-5 rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-6 dark:border-[#292925] dark:bg-[#141411]" aria-label="Active work contract">
            {currentGoal ? <>
              <div><p className="text-[10px] font-black uppercase tracking-[0.14em] text-[#85857c]">Prepared for active work</p><h2 className="mt-2 text-lg font-black leading-7">{cleanDisplayText(currentGoal.title)}</h2></div>
              <div><p className="text-[10px] font-black uppercase tracking-[0.12em] text-[#85857c]">Done when</p>{workContract.definition_of_done?.length ? <ul className="mt-2 space-y-2 text-xs font-semibold leading-5">{workContract.definition_of_done.map((item) => <li key={item} className="flex gap-2"><Check className="mt-0.5 h-3.5 w-3.5 shrink-0 text-emerald-600" />{item}</li>)}</ul> : <p className="mt-2 text-xs font-semibold text-amber-700 dark:text-amber-300">No completion criteria were saved. Replace this legacy goal before running it.</p>}</div>
              <dl className="grid grid-cols-2 gap-2"><ContractFact label="Agent" value={contractAgent.adapter_id || "Not configured"} /><ContractFact label="Model" value={contractAgent.target_model || "Provider default · unverified"} /><ContractFact label="Context budget" value={`${contractContext.token_budget || 4000} tokens`} /><ContractFact label="Capability profile" value="Inferred · not provider-probed" /></dl>
              {prepareContext.isError ? <p role="alert" className="text-xs font-bold leading-5 text-red-600">{prepareContext.error?.message || "The context pack could not be rebuilt."}</p> : null}
              <button type="button" onClick={rebuild} disabled={prepareContext.isPending} className="inline-flex h-11 w-full items-center justify-center gap-2 rounded-xl bg-[#171713] px-4 text-xs font-black text-white disabled:opacity-50 dark:bg-[#d9ff68] dark:text-[#171713]">{prepareContext.isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <PackageCheck className="h-4 w-4" />}{prepareContext.isPending ? "Rebuilding exact pack…" : "Rebuild context pack"}</button>
              <Link to="/app" className="block text-center text-[10px] font-black text-[#85857c] underline underline-offset-4">Change objective, done criteria, agent, or model in Now</Link>
            </> : <div className="py-4 text-center"><PackageCheck className="mx-auto h-8 w-8 text-[#aaa99f]" /><h2 className="mt-3 text-base font-black">No active work contract</h2><p className="mx-auto mt-2 max-w-sm text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">Start AI work first. Context Engine will compile the pack as part of that action—there is no second task box here.</p><Link to="/app" className="mt-5 inline-flex h-10 items-center rounded-lg bg-[#171713] px-4 text-xs font-black text-white dark:bg-[#d9ff68] dark:text-[#171713]">Start AI work</Link></div>}
          </section>

          <PackHistory packs={packsQuery.data?.items || []} loading={packsQuery.isLoading} selectedPackId={selectedPackId} comparisonPackIds={comparisonPackIds} onOpen={openSavedPack} onToggleComparison={toggleComparisonPack} />
          <PackComparison data={comparisonQuery.data} loading={comparisonQuery.isLoading} error={comparisonQuery.isError ? comparisonQuery.error : null} selectedCount={comparisonPackIds.length} />
        </div>

        <section aria-label="Compiled context result" className="min-h-[520px] rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-6 dark:border-[#292925] dark:bg-[#141411]">
          {selectedPackQuery.isLoading ? <ResultState icon={Loader2} title="Reopening saved context pack…" spin /> : null}
          {selectedPackQuery.isError ? <ResultState icon={XCircle} title="Could not reopen context pack" detail={selectedPackQuery.error?.message} /> : null}
          {!result && !selectedPackQuery.isLoading ? <ResultState icon={FileText} title="No context pack open" detail="Start work in Now, rebuild the active pack, or reopen an exact saved artifact from history." /> : null}
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
              <div className="flex flex-col gap-2 border-t border-[#e2e2da] pt-4 dark:border-[#292925] sm:flex-row sm:items-center sm:justify-between"><p className="text-[10px] font-semibold text-[#85857c]">This exact artifact is saved and will be passed to the configured harness.</p><Link to={`/app/runs?pack=${encodeURIComponent(result.context_pack_id)}`} className="text-xs font-black underline underline-offset-4">Continue to agent</Link></div>
            </div>
          ) : null}
        </section>
      </div>
    </div>
  );
}

function PackHistory({ packs, loading, selectedPackId, comparisonPackIds, onOpen, onToggleComparison }) {
  return (
    <section className="rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-5 dark:border-[#292925] dark:bg-[#141411]">
      <div className="flex items-center justify-between gap-3"><h2 className="flex items-center gap-2 text-xs font-black uppercase tracking-[0.14em]"><History className="h-4 w-4" />Pack history</h2><span className="text-[10px] font-bold text-[#85857c]">{packs.length} saved</span></div>
      {loading ? <p className="mt-4 text-xs text-[#85857c]">Loading saved packs…</p> : null}
      {!loading && !packs.length ? <p className="mt-4 text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">No packs have been compiled for this workspace yet.</p> : null}
      {packs.length ? <div className="mt-3 max-h-80 space-y-2 overflow-auto">{packs.map((pack) => (
        <div key={pack.context_pack_id} className={`flex items-stretch rounded-lg border ${selectedPackId === pack.context_pack_id ? "border-[#171713] bg-[#efefe7] dark:border-[#d9ff68] dark:bg-[#252521]" : "border-[#e2e2da] hover:border-[#aaa99f] dark:border-[#292925]"}`}>
          <button type="button" onClick={() => onOpen(pack.context_pack_id)} className="min-w-0 flex-1 p-3 text-left">
            <span className="block truncate text-xs font-black">{cleanDisplayText(pack.objective)}</span>
            <span className="mt-1 block text-[10px] font-semibold text-[#85857c]">{formatTimeAgo(pack.created_at)} · {pack.selected_count} selected · {pack.run_count} runs</span>
          </button>
          <label className="flex shrink-0 cursor-pointer items-center gap-1.5 border-l border-[#e2e2da] px-3 text-[9px] font-black uppercase tracking-wide text-[#85857c] dark:border-[#292925]"><input aria-label={`Compare ${cleanDisplayText(pack.objective)} from ${formatTimeAgo(pack.created_at)}`} type="checkbox" checked={comparisonPackIds.includes(pack.context_pack_id)} onChange={() => onToggleComparison(pack.context_pack_id)} />Compare</label>
        </div>
      ))}</div> : null}
    </section>
  );
}

function PackComparison({ data, loading, error, selectedCount }) {
  if (selectedCount === 0) return null;
  if (selectedCount === 1) return <section className="rounded-2xl border border-dashed border-[#d8d8cf] p-5 text-xs font-semibold text-[#68685f] dark:border-[#292925] dark:text-[#aaa9a0]">Choose one more saved pack to compare exact context selection.</section>;
  if (loading) return <section className="rounded-2xl border border-[#d8d8cf] p-5 text-xs font-semibold dark:border-[#292925]">Comparing saved packs…</section>;
  if (error) return <section role="alert" className="rounded-2xl border border-red-200 bg-red-50 p-5 text-xs font-bold text-red-700 dark:border-red-900/60 dark:bg-red-950/25 dark:text-red-300">{error.message || "The saved packs could not be compared."}</section>;
  if (!data) return null;
  const context = data.selected_context || {};
  const tokenDelta = Number(data.right?.estimated_tokens || 0) - Number(data.left?.estimated_tokens || 0);
  const healthDelta = Math.round(Number(data.right?.health_score || 0) - Number(data.left?.health_score || 0));
  return (
    <section className="rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-5 dark:border-[#292925] dark:bg-[#141411]" aria-label="Context pack comparison">
      <div className="flex items-center justify-between gap-3"><h2 className="text-xs font-black uppercase tracking-[0.14em]">Exact pack comparison</h2><span className="text-[9px] font-black uppercase text-[#85857c]">Older → newer</span></div>
      <div className="mt-4 grid grid-cols-2 gap-2 sm:grid-cols-4"><ComparisonMetric label="Retained" value={context.retained?.length || 0} /><ComparisonMetric label="Added" value={context.added?.length || 0} /><ComparisonMetric label="Removed" value={context.removed?.length || 0} /><ComparisonMetric label="Health delta" value={`${healthDelta >= 0 ? "+" : ""}${healthDelta}`} /></div>
      <p className="mt-3 text-[10px] font-semibold text-[#85857c]">Token delta {tokenDelta >= 0 ? "+" : ""}{tokenDelta}. This compares persisted item identities and fields; it does not guess semantic equivalence.</p>
      <ComparisonItems title="Added context" items={context.added || []} tone="text-emerald-700 dark:text-emerald-300" />
      <ComparisonItems title="Removed context" items={context.removed || []} tone="text-red-700 dark:text-red-300" />
      {context.changed?.length ? <ComparisonItems title="Retained but changed" items={context.changed.map((item) => item.right)} tone="text-amber-700 dark:text-amber-300" /> : null}
    </section>
  );
}

function ComparisonMetric({ label, value }) {
  return <div className="rounded-xl bg-[#efefe7] p-3 text-center dark:bg-[#252521]"><p className="text-lg font-black">{value}</p><p className="text-[9px] font-black uppercase tracking-wide text-[#85857c]">{label}</p></div>;
}

function ComparisonItems({ title, items, tone }) {
  if (!items.length) return null;
  return <details className="mt-3 rounded-lg border border-[#e2e2da] dark:border-[#292925]"><summary className={`cursor-pointer p-3 text-[10px] font-black uppercase tracking-wide ${tone}`}>{title} · {items.length}</summary><div className="space-y-2 border-t border-[#e2e2da] p-3 dark:border-[#292925]">{items.map((item, index) => <p key={item.id || item.component_id || index} className="text-xs font-semibold">{cleanDisplayText(item.title || item.name || item.summary || item.id || "Context item")}</p>)}</div></details>;
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

function ContractFact({ label, value }) {
  return <div className="rounded-xl bg-[#efefe7] p-3 dark:bg-[#252521]"><dt className="text-[9px] font-black uppercase tracking-wide text-[#85857c]">{label}</dt><dd className="mt-1 break-words text-[10px] font-black">{value}</dd></div>;
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
