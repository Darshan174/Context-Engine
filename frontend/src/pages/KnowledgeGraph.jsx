import { useState } from "react";
import GraphVisualizer from "../components/GraphVisualizer";
import RelationshipEdge from "../components/RelationshipEdge";
import StatusView from "../components/StatusView";
import MockBadge from "../components/MockBadge";
import { useKnowledgeGraph } from "../api/hooks";
import { graphNodes as mockNodes, graphEdges as mockEdges } from "../fixtures/mockData";

const NODE_TYPES = ["all", "model", "source", "component"];

export default function KnowledgeGraph() {
  const [search, setSearch] = useState("");
  const [typeFilter, setTypeFilter] = useState("all");
  const { data, isMock, ...query } = useKnowledgeGraph();

  const status = <StatusView query={{ data, ...query }} empty="No graph data yet." />;
  if (query.isLoading || query.isError) return <div className="max-w-6xl mx-auto">{status}</div>;

  const graphNodes = data?.nodes ?? mockNodes;
  const graphEdges = data?.edges ?? mockEdges;

  const filteredNodes = graphNodes.filter((n) => {
    const matchesSearch =
      !search || n.label.toLowerCase().includes(search.toLowerCase());
    const matchesType = typeFilter === "all" || n.type === typeFilter;
    return matchesSearch && matchesType;
  });

  const filteredNodeIds = new Set(filteredNodes.map((n) => n.id));

  const filteredEdges = graphEdges.filter(
    (e) => filteredNodeIds.has(e.source) && filteredNodeIds.has(e.target),
  );

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold text-gray-800">Knowledge Graph</h2>
        {isMock && <MockBadge />}
      </div>

      {/* ── Controls ────────────────────────────── */}
      <div className="flex flex-wrap items-center gap-3">
        <input
          type="text"
          placeholder="Search nodes..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="px-3 py-2 text-sm border border-gray-200 rounded-lg w-64 focus:outline-none focus:ring-2 focus:ring-brand-500/40"
        />
        <div className="flex gap-1">
          {NODE_TYPES.map((t) => (
            <button
              key={t}
              onClick={() => setTypeFilter(t)}
              className={`px-3 py-1.5 text-xs rounded-lg border transition-colors ${
                typeFilter === t
                  ? "bg-brand-600 text-white border-brand-600"
                  : "bg-white text-gray-600 border-gray-200 hover:bg-gray-50"
              }`}
            >
              {t === "all" ? "All types" : t}
            </button>
          ))}
        </div>
        <span className="ml-auto text-xs text-gray-400">
          {filteredNodes.length}/{graphNodes.length} nodes &middot; {filteredEdges.length}/{graphEdges.length} edges
        </span>
      </div>

      {/* ── Graph area ──────────────────────────── */}
      <div className="h-[460px]">
        <GraphVisualizer nodes={filteredNodes} edges={filteredEdges} />
      </div>

      {/* ── Edge list ───────────────────────────── */}
      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <h3 className="text-sm font-semibold text-gray-700 mb-3">Relationships</h3>
        {filteredEdges.length === 0 ? (
          <p className="text-sm text-gray-400">No relationships match your filters.</p>
        ) : (
          <div className="divide-y divide-gray-100">
            {filteredEdges.map((e) => {
              const src = graphNodes.find((n) => n.id === e.source);
              const tgt = graphNodes.find((n) => n.id === e.target);
              return (
                <RelationshipEdge
                  key={`${e.source}-${e.target}`}
                  sourceLabel={src?.label}
                  targetLabel={tgt?.label}
                  label={e.label}
                />
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}
