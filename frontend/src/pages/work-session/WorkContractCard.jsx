import { ArrowRight, CheckCircle2, Cpu, PackageCheck } from "lucide-react";
import { Link } from "react-router-dom";

import { cleanDisplayText } from "../../context-map/digest";

export default function WorkContractCard({ goal, onReplace, onStop, stopping = false }) {
  const contract = goal?.work_contract || {};
  const agent = contract.agent || {};
  const context = contract.context || {};
  const criteria = contract.definition_of_done || [];
  return (
    <article className="rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-6 shadow-sm dark:border-[#292925] dark:bg-[#141411]">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div>
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.16em] text-emerald-700 dark:text-emerald-300"><PackageCheck className="h-3.5 w-3.5" />Active AI work</div>
          <h2 className="mt-3 max-w-3xl text-2xl font-black leading-tight">{cleanDisplayText(goal?.title)}</h2>
        </div>
        {goal?.source_kind !== "active_agent_run" ? <div className="flex gap-2"><button type="button" onClick={onReplace} className="rounded-lg border border-[#d8d8cf] px-3 py-2 text-[10px] font-black dark:border-[#33332e]">Replace task</button>{goal?.can_clear ? <button type="button" onClick={onStop} disabled={stopping} className="px-2 py-2 text-[10px] font-black text-[#85857c] underline underline-offset-4 disabled:opacity-50">{stopping ? "Stopping…" : "Stop"}</button> : null}</div> : <span className="rounded-full bg-emerald-100 px-2.5 py-1 text-[9px] font-black uppercase text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">Agent running</span>}
      </div>

      <div className="mt-5 grid gap-4 md:grid-cols-[1.35fr_.65fr]">
        <div className="rounded-xl bg-[#efefe7] p-4 dark:bg-[#252521]">
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.12em] text-[#85857c]"><CheckCircle2 className="h-3.5 w-3.5" />Done when</div>
          {criteria.length ? <ul className="mt-3 space-y-2 text-xs font-semibold leading-5">{criteria.map((item) => <li key={item} className="flex gap-2"><span aria-hidden="true">✓</span><span>{item}</span></li>)}</ul> : <p className="mt-3 text-xs leading-5 text-amber-800 dark:text-amber-200">This is a legacy goal with no completion criteria. Replace it before running an agent.</p>}
        </div>
        <div className="rounded-xl bg-[#efefe7] p-4 dark:bg-[#252521]">
          <div className="flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.12em] text-[#85857c]"><Cpu className="h-3.5 w-3.5" />Execution</div>
          <dl className="mt-3 space-y-3 text-xs"><Fact label="Agent" value={agent.adapter_id || "Not configured"} /><Fact label="Model" value={agent.target_model || "Provider default · unverified"} /><Fact label="Context" value={context.token_budget ? `${context.token_budget} token budget` : "Conservative default"} /></dl>
        </div>
      </div>
      {criteria.length && agent.adapter_id ? <div className="mt-5 flex flex-wrap gap-3"><Link to="/app/runs" className="inline-flex h-10 items-center gap-2 rounded-lg bg-[#171713] px-4 text-xs font-black text-white dark:bg-[#d9ff68] dark:text-[#171713]">Continue to agent <ArrowRight className="h-3.5 w-3.5" /></Link><Link to="/app/prepare" className="inline-flex h-10 items-center rounded-lg border border-[#d8d8cf] px-4 text-xs font-black dark:border-[#33332e]">Inspect context</Link></div> : null}
    </article>
  );
}

function Fact({ label, value }) {
  return <div><dt className="text-[9px] font-black uppercase tracking-wide text-[#85857c]">{label}</dt><dd className="mt-1 break-words font-black">{value}</dd></div>;
}
