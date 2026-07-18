import { useState } from "react";
import { ArrowLeft, ArrowRight, ExternalLink, Search, ShieldAlert, ListTodo } from "lucide-react";
import { Link, useSearchParams } from "react-router-dom";

import WorkspaceTopicGate from "../components/WorkspaceTopicGate";
import { useContextDigest } from "../context-map/api";
import { cleanDisplayText } from "../context-map/digest";
import { useProductWorkspace } from "./useProductWorkspace";

export default function WorkItemsPage() {
  const workspace = useProductWorkspace();
  const digestQuery = useContextDigest(workspace.activeWorkspaceId);
  const [searchParams, setSearchParams] = useSearchParams();
  const [query, setQuery] = useState("");
  const tab = ["attention", "backlog", "all"].includes(searchParams.get("view"))
    ? searchParams.get("view")
    : "attention";

  if (!workspace.workspacesQuery.isLoading && !workspace.activeWorkspaceId) {
    return <WorkspaceTopicGate workspaces={workspace.workspaces} selectedId={workspace.selectedId} onSelect={workspace.setSelectedId} />;
  }
  if (workspace.workspacesQuery.isLoading || digestQuery.isLoading) {
    return <PageState title="Loading project work…" />;
  }
  if (digestQuery.isError) {
    return <PageState title="Could not load project work" detail={digestQuery.error?.message} error />;
  }

  const digest = digestQuery.data || {};
  const cards = digest.cards || [];
  const currentComponentId = digest.current_goal?.component_id;
  const attention = cards
    .filter((card) => card.attention_required)
    .sort(byAttention);
  const backlog = cards
    .filter(isBacklogCard)
    .filter((card) => card.id !== `component:${currentComponentId}`)
    .sort(byAttention);
  const visibleCards = tab === "attention"
    ? attention
    : tab === "backlog"
      ? backlog
      : uniqueCards([...attention, ...backlog]);
  const normalizedQuery = query.trim().toLowerCase();
  const filteredCards = visibleCards.filter((card) => !normalizedQuery || [card.title, card.summary, card.next_action, card.why_it_matters, card.status, card.category]
    .some((value) => cleanDisplayText(value).toLowerCase().includes(normalizedQuery)));

  const selectTab = (nextTab) => {
    const next = new URLSearchParams(searchParams);
    next.set("view", nextTab);
    setSearchParams(next, { replace: true });
  };

  return (
    <div className="relative mx-auto w-full max-w-6xl space-y-6">
      <header className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <Link to="/app" className="inline-flex items-center gap-1.5 text-xs font-black text-[#68685f] underline underline-offset-4 dark:text-[#aaa9a0]"><ArrowLeft className="h-3.5 w-3.5" />Back to Now</Link>
          <p className="mt-5 text-xs font-black uppercase tracking-[0.18em] text-[#85857c]">{workspace.activeWorkspace?.name || "Project"}</p>
          <h1 className="mt-2 text-3xl font-black tracking-tight">Project work</h1>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-[#68685f] dark:text-[#aaa9a0]">The complete work queue. Inspect evidence first; make something current only when you intend to work on it.</p>
        </div>
        <div className="grid grid-cols-3 rounded-xl border border-[#d8d8cf] bg-[#fbfbf6] p-1 dark:border-[#292925] dark:bg-[#141411]">
          <TabButton active={tab === "attention"} onClick={() => selectTab("attention")}>Attention · {attention.length}</TabButton>
          <TabButton active={tab === "backlog"} onClick={() => selectTab("backlog")}>Backlog · {backlog.length}</TabButton>
          <TabButton active={tab === "all"} onClick={() => selectTab("all")}>All</TabButton>
        </div>
      </header>

      <label className="relative block">
        <Search className="pointer-events-none absolute left-3.5 top-1/2 h-4 w-4 -translate-y-1/2 text-[#85857c]" />
        <input aria-label="Search project work" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search titles, evidence summaries, status, or next action" className="h-11 w-full rounded-xl border border-[#d8d8cf] bg-white pl-10 pr-4 text-sm font-semibold outline-none focus:border-[#77776e] dark:border-[#33332e] dark:bg-[#141411]" />
      </label>

      {filteredCards.length ? (
        <section className="space-y-3" aria-label="Project work items">
          {filteredCards.map((card) => (
            <WorkItemCard
              key={card.id}
              card={card}
              isCurrent={card.id === `component:${currentComponentId}`}
            />
          ))}
        </section>
      ) : (
        <PageState title={normalizedQuery ? "No work matches this search" : `No ${tab === "all" ? "project work" : tab} is currently visible`} detail={normalizedQuery ? "Clear the search or choose a different work view." : "Context Engine only lists work supported by captured project evidence."} />
      )}
    </div>
  );
}

function WorkItemCard({ card, isCurrent }) {
  const sourceId = card.source_snapshot?.source_document_id;
  const eligibleComponentId = componentId(card);
  const isAttention = Boolean(card.attention_required);
  const detail = cleanDisplayText(card.summary || card.why_it_matters || card.next_action) || "No additional source-backed summary is available.";
  return (
    <article className="rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-5 dark:border-[#292925] dark:bg-[#141411]">
      <div className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2 text-[9px] font-black uppercase tracking-[0.13em] text-[#85857c]">
            <span className={`inline-flex items-center gap-1 rounded-full px-2 py-1 ${isAttention ? "bg-amber-100 text-amber-800 dark:bg-amber-950/50 dark:text-amber-200" : "bg-[#efefe7] text-[#68685f] dark:bg-[#252521] dark:text-[#c6c6bd]"}`}>{isAttention ? <ShieldAlert className="h-3 w-3" /> : <ListTodo className="h-3 w-3" />}{isAttention ? "Needs attention" : "Backlog"}</span>
            <span>{cleanDisplayText(card.category)}</span>
            <span>·</span>
            <span>{cleanDisplayText(card.status || "observed")}</span>
            {isCurrent ? <span className="rounded-full bg-emerald-100 px-2 py-1 text-emerald-800 dark:bg-emerald-950/50 dark:text-emerald-200">Current goal</span> : null}
          </div>
          <h2 className="mt-3 text-base font-black leading-6">{cleanDisplayText(card.title)}</h2>
          <p className="mt-2 max-w-3xl text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">{detail}</p>
          {card.next_action ? <p className="mt-3 text-xs font-semibold text-[#4f4f48] dark:text-[#d8d8cf]"><strong>Next:</strong> {cleanDisplayText(card.next_action)}</p> : null}
        </div>
        <div className="flex shrink-0 flex-wrap gap-2">
          <Link to={`/app/explain?card=${encodeURIComponent(card.id)}`} className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-[#d8d8cf] px-3 text-[10px] font-black dark:border-[#33332e]">Inspect evidence <ArrowRight className="h-3 w-3" /></Link>
          {sourceId ? <Link to={`/app/sources?source=${encodeURIComponent(sourceId)}`} className="inline-flex h-9 items-center gap-1.5 rounded-lg border border-[#d8d8cf] px-3 text-[10px] font-black dark:border-[#33332e]">Source <ExternalLink className="h-3 w-3" /></Link> : null}
          {!isCurrent && card.focus_eligible && eligibleComponentId ? <Link to={`/app?work=${encodeURIComponent(card.id)}`} className="inline-flex h-9 items-center rounded-lg bg-[#171713] px-3 text-[10px] font-black text-white dark:bg-[#d9ff68] dark:text-[#171713]">Start this work</Link> : null}
        </div>
      </div>
      <div className="mt-4 flex flex-wrap gap-2 border-t border-[#e6e6de] pt-4 text-[9px] font-bold text-[#85857c] dark:border-[#292925]">
        <span>{card.provenance?.length || 0} provenance record{card.provenance?.length === 1 ? "" : "s"}</span>
        {card.source_snapshot?.freshness ? <><span>·</span><span>Source {cleanDisplayText(card.source_snapshot.freshness)}</span></> : null}
        {Number.isFinite(Number(card.attention_score)) ? <><span>·</span><span>Priority {Math.round(Number(card.attention_score))}</span></> : null}
      </div>
    </article>
  );
}

function isBacklogCard(card) {
  return ["issue", "task"].includes(card.category)
    && card.focus_eligible
    && !["resolved", "closed", "superseded", "stale"].includes(card.status);
}

function byAttention(left, right) {
  return (right.attention_score || 0) - (left.attention_score || 0);
}

function uniqueCards(cards) {
  return [...new Map(cards.map((card) => [card.id, card])).values()];
}

function componentId(card) {
  const value = String(card?.id || "");
  return value.startsWith("component:") ? value.slice("component:".length) : null;
}

function TabButton({ active, onClick, children }) {
  return <button type="button" onClick={onClick} aria-pressed={active} className={`h-8 rounded-lg px-3 text-[10px] font-black ${active ? "bg-[#171713] text-white dark:bg-[#d9ff68] dark:text-[#171713]" : "text-[#68685f] dark:text-[#aaa9a0]"}`}>{children}</button>;
}

function PageState({ title, detail, error = false }) {
  return <div className={`rounded-2xl border p-8 text-center ${error ? "border-red-200 bg-red-50 dark:border-red-900/60 dark:bg-red-950/25" : "border-dashed border-[#d8d8cf] bg-[#fbfbf6] dark:border-[#292925] dark:bg-[#141411]"}`}><h1 className="text-base font-black">{title}</h1>{detail ? <p className="mx-auto mt-2 max-w-xl text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">{detail}</p> : null}</div>;
}
