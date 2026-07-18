import { useEffect, useMemo, useState } from "react";
import { ArrowRight, Bot, Loader2, PackageCheck } from "lucide-react";

import { cleanDisplayText } from "../../context-map/digest";

export default function StartWorkPanel({
  adapters = [],
  error,
  initialWork = null,
  isPending = false,
  onStart,
}) {
  const installedAdapters = useMemo(
    () => adapters.filter((adapter) => adapter.installed),
    [adapters],
  );
  const preferredAdapter = installedAdapters.find((adapter) => adapter.id === "codex")
    || installedAdapters[0]
    || adapters[0]
    || null;
  const [objective, setObjective] = useState("");
  const [doneWhen, setDoneWhen] = useState("");
  const [adapterId, setAdapterId] = useState("");
  const [targetModel, setTargetModel] = useState("");
  const [tokenBudget, setTokenBudget] = useState("4000");

  useEffect(() => {
    setObjective(cleanDisplayText(initialWork?.title || initialWork?.objective || ""));
    setDoneWhen((initialWork?.definitionOfDone || []).join("\n"));
    setTargetModel(initialWork?.targetModel || "");
  }, [initialWork]);

  useEffect(() => {
    if (!adapterId && preferredAdapter?.id) setAdapterId(preferredAdapter.id);
  }, [adapterId, preferredAdapter?.id]);

  const selectedAdapter = adapters.find((adapter) => adapter.id === adapterId) || null;
  const criteria = doneWhen
    .split("\n")
    .map((item) => cleanDisplayText(item))
    .filter(Boolean);
  const canStart = objective.trim().length >= 3
    && criteria.length > 0
    && selectedAdapter?.installed;

  const submit = (event) => {
    event.preventDefault();
    if (!canStart) return;
    onStart({
      objective: cleanDisplayText(objective),
      definition_of_done: criteria,
      component_id: initialWork?.componentId || undefined,
      source_kind: initialWork?.componentId ? "suggested_card" : "user_selected",
      source_id: initialWork?.sourceId || undefined,
      adapter_id: adapterId,
      target_model: cleanDisplayText(targetModel) || undefined,
      token_budget: Number(tokenBudget),
    });
  };

  return (
    <form onSubmit={submit} className="space-y-5 rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-6 shadow-sm dark:border-[#292925] dark:bg-[#141411]" aria-label="Start AI work">
      <div>
        <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.16em] text-[#85857c]"><Bot className="h-3.5 w-3.5" />Start AI work</div>
        <h2 className="mt-3 text-xl font-black">Give the agent a job, not a label.</h2>
        <p className="mt-2 max-w-2xl text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">Context Engine will save this work contract, compile the exact evidence pack, and generate a runnable command for the installed agent you choose.</p>
      </div>

      <label className="block">
        <span className="text-xs font-black">What should the agent finish?</span>
        <textarea aria-label="Work objective" required rows={3} value={objective} onChange={(event) => setObjective(event.target.value)} placeholder="Fix the authentication redirect loop and add focused regression tests" className="mt-2 w-full resize-none rounded-xl border border-[#d8d8cf] bg-white px-3.5 py-3 text-sm font-semibold leading-6 outline-none focus:border-[#77776e] dark:border-[#33332e] dark:bg-[#0f0f0c]" />
      </label>

      <label className="block">
        <span className="text-xs font-black">Done when <span className="font-semibold text-[#85857c]">— one check per line</span></span>
        <textarea aria-label="Definition of done" required rows={3} value={doneWhen} onChange={(event) => setDoneWhen(event.target.value)} placeholder={"The redirect lands on the intended workspace\nThe regression test fails before the fix and passes after it"} className="mt-2 w-full resize-none rounded-xl border border-[#d8d8cf] bg-white px-3.5 py-3 text-sm font-semibold leading-6 outline-none focus:border-[#77776e] dark:border-[#33332e] dark:bg-[#0f0f0c]" />
        {!criteria.length ? <span className="mt-1.5 block text-[10px] font-semibold text-[#85857c]">This is what lets Context Engine judge the result instead of merely recording activity.</span> : null}
      </label>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-xs font-black">Run with</span>
          <select aria-label="Agent adapter" value={adapterId} onChange={(event) => setAdapterId(event.target.value)} className="mt-2 h-11 w-full rounded-lg border border-[#d8d8cf] bg-white px-3 text-xs font-black outline-none dark:border-[#33332e] dark:bg-[#0f0f0c]">
            {adapters.map((adapter) => <option key={adapter.id} value={adapter.id} disabled={!adapter.installed}>{adapter.label}{adapter.installed ? ` · ${adapter.version || "detected"}` : " · not detected"}</option>)}
          </select>
          <span className="mt-1.5 block text-[10px] font-semibold text-[#85857c]">{selectedAdapter?.installed ? `${selectedAdapter.label} was detected on this machine${selectedAdapter.launch_support === "experimental" ? "; this adapter is experimental" : ""}.` : "No supported agent CLI was detected on the Context Engine machine."}</span>
        </label>
        <label className="block">
          <span className="text-xs font-black">Model <span className="font-semibold text-[#85857c]">(optional)</span></span>
          <input aria-label="Target model" value={targetModel} onChange={(event) => setTargetModel(event.target.value)} placeholder="Blank uses the agent's default" className="mt-2 h-11 w-full rounded-lg border border-[#d8d8cf] bg-white px-3 text-xs font-semibold outline-none dark:border-[#33332e] dark:bg-[#0f0f0c]" />
          <span className="mt-1.5 block text-[10px] font-semibold text-[#85857c]">A typed model is recorded as user-configured, not provider-attested.</span>
        </label>
      </div>

      <details className="rounded-xl border border-[#e2e2da] p-3 dark:border-[#292925]">
        <summary className="cursor-pointer text-[10px] font-black uppercase tracking-[0.12em] text-[#68685f] dark:text-[#c6c6bd]">Context budget</summary>
        <label className="mt-3 block"><span className="text-[10px] font-bold text-[#85857c]">Maximum estimated tokens</span><input aria-label="Context budget" type="number" min="300" max="200000" step="100" value={tokenBudget} onChange={(event) => setTokenBudget(event.target.value)} className="mt-1.5 h-10 w-full rounded-lg border border-[#d8d8cf] bg-white px-3 text-xs font-semibold dark:border-[#33332e] dark:bg-[#0f0f0c]" /></label>
      </details>

      {error ? <p role="alert" className="text-xs font-bold leading-5 text-red-600 dark:text-red-400">{error}</p> : null}
      {!installedAdapters.length ? <p role="status" className="rounded-xl border border-amber-200 bg-amber-50 p-3 text-xs font-bold text-amber-900 dark:border-amber-900/60 dark:bg-amber-950/25 dark:text-amber-100">Install or expose Codex CLI, Claude Code, or OpenCode on the machine running Context Engine before starting a work session.</p> : null}
      <button type="submit" disabled={!canStart || isPending} className="inline-flex h-12 w-full items-center justify-center gap-2 rounded-xl bg-[#171713] px-4 text-xs font-black text-white disabled:opacity-40 dark:bg-[#d9ff68] dark:text-[#171713]">
        {isPending ? <Loader2 className="h-4 w-4 animate-spin" /> : <PackageCheck className="h-4 w-4" />}
        {isPending ? "Building the work session…" : "Prepare and continue"}
        {!isPending ? <ArrowRight className="h-4 w-4" /> : null}
      </button>
    </form>
  );
}
