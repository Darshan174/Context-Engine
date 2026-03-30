import { useState } from "react";
import { useContextQuery } from "../api/hooks";
import MockBadge from "../components/MockBadge";

const FRESHNESS_STYLE = {
  current: "bg-emerald-50 text-emerald-700 border-emerald-200",
  possibly_stale: "bg-amber-50 text-amber-700 border-amber-200",
  stale: "bg-red-50 text-red-700 border-red-200",
};

const FRESHNESS_LABEL = {
  current: "Current",
  possibly_stale: "Possibly stale",
  stale: "Stale",
};

export default function Query() {
  const [input, setInput] = useState("");
  const mutation = useContextQuery();
  const result = mutation.data;
  const isMock = result?._isMock ?? false;
  const isNoMatch =
    result &&
    result.confidence === 0 &&
    (!result.components || result.components.length === 0) &&
    (!result.sources || result.sources.length === 0);

  const handleSubmit = (e) => {
    e.preventDefault();
    const q = input.trim();
    if (!q) return;
    mutation.mutate(q);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <div className="flex items-center gap-3">
        <h2 className="text-lg font-semibold text-gray-800">Context Query</h2>
        {isMock && result && <MockBadge />}
        {!isMock && result && (
          <span className="px-2 py-0.5 text-[11px] rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700">
            Live backend
          </span>
        )}
      </div>
      <p className="text-xs text-gray-400">
        Query your workspace context. Live backend answers are preferred; demo answers only appear when the backend is unreachable.
      </p>

      {/* ── Input ───────────────────────────────── */}
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your company data..."
          aria-label="Query input"
          className="flex-1 px-4 py-2.5 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/40"
        />
        <button
          type="submit"
          disabled={mutation.isPending || !input.trim()}
          className="px-5 py-2.5 text-sm font-medium rounded-lg bg-brand-600 text-white hover:bg-brand-700 disabled:opacity-50 transition-colors shrink-0"
        >
          {mutation.isPending ? "Thinking..." : "Ask"}
        </button>
      </form>

      {/* ── Loading ─────────────────────────────── */}
      {mutation.isPending && (
        <div role="status" aria-live="polite" className="flex items-center gap-3 py-8 justify-center text-gray-400">
          <svg className="animate-spin h-5 w-5 text-brand-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Querying knowledge graph...</span>
        </div>
      )}

      {/* ── Error ───────────────────────────────── */}
      {mutation.isError && (
        <div role="alert" className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
          <p className="text-sm text-red-600">
            {mutation.error?.message || "Failed to get an answer."}
          </p>
          <button
            onClick={() => mutation.mutate(input.trim())}
            disabled={!input.trim()}
            className="mt-3 px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 transition-colors"
          >
            Retry
          </button>
        </div>
      )}

      {/* ── No-match ─────────────────────────────── */}
      {result && !mutation.isPending && isNoMatch && (
        <div className="space-y-4">
          <div className="bg-gray-100 rounded-xl px-5 py-3">
            <p className="text-sm text-gray-600 font-medium">{result.question}</p>
          </div>
          <div className="bg-amber-50 border border-amber-200 rounded-xl p-5 text-center space-y-2">
            <p className="text-sm font-medium text-amber-700">No grounded answer found</p>
            <p className="text-xs text-amber-600">
              {result.answer || "The knowledge graph does not contain enough structured context to answer this question."}
            </p>
            {!isMock && (
              <p className="text-xs text-amber-700">
                If you recently connected Slack, run a sync from{" "}
                <a href="/connectors" className="underline underline-offset-2">
                  Connectors
                </a>{" "}
                and try again.
              </p>
            )}
          </div>
        </div>
      )}

      {/* ── Answer ──────────────────────────────── */}
      {result && !mutation.isPending && !isNoMatch && (
        <div className="space-y-4">
          {/* Question echo */}
          <div className="bg-gray-100 rounded-xl px-5 py-3">
            <p className="text-sm text-gray-600 font-medium">{result.question}</p>
          </div>

          {/* Answer body */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
            {!isMock && (
              <div className="flex flex-wrap items-center gap-2 text-[11px] text-gray-500">
                <span className="px-2 py-0.5 rounded-full bg-gray-100 text-gray-600">
                  Live workspace context
                </span>
                <span>
                  Grounded in {result.components?.length ?? 0} component{result.components?.length === 1 ? "" : "s"}
                  {" "}from {result.sources?.length ?? 0} source{result.sources?.length === 1 ? "" : "s"}.
                </span>
              </div>
            )}
            {result.answer ? (
              <div className="text-sm text-gray-800 leading-relaxed space-y-2">
                {result.answer.split("\n").filter(Boolean).map((line, i) => (
                  <p key={i}>{line}</p>
                ))}
              </div>
            ) : (
              <p className="text-sm text-gray-400 italic">No answer could be determined for this query.</p>
            )}

            {/* Confidence */}
            {result.confidence != null && (
              <div className="flex items-center gap-3">
                <span className="text-xs text-gray-400">Confidence</span>
                <div className="flex-1 h-1.5 bg-gray-100 rounded-full overflow-hidden max-w-[200px]">
                  <div
                    className={`h-full rounded-full ${
                      result.confidence >= 0.9
                        ? "bg-emerald-500"
                        : result.confidence >= 0.75
                          ? "bg-amber-400"
                          : "bg-red-400"
                    }`}
                    style={{ width: `${Math.round(result.confidence * 100)}%` }}
                  />
                </div>
                <span className="text-xs text-gray-500">{Math.round(result.confidence * 100)}%</span>
              </div>
            )}

            {/* Freshness + timestamp */}
            <div className="flex items-center gap-2">
              {result.freshness && (
                <span
                  className={`px-2 py-0.5 text-[11px] rounded-full border ${
                    FRESHNESS_STYLE[result.freshness] || "bg-blue-50 text-blue-700 border-blue-200"
                  }`}
                >
                  {FRESHNESS_LABEL[result.freshness] || result.freshness}
                </span>
              )}
              {result.answeredAt && (
                <p className="text-[11px] text-gray-300">{result.answeredAt}</p>
              )}
            </div>
          </div>

          {/* Cited components */}
          {result.components?.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Cited Components
              </h3>
              <div className="divide-y divide-gray-100">
                {result.components.map((c) => (
                  <div key={c.id} className="py-2.5">
                    <div className="flex items-center justify-between">
                      <div>
                        <span className="text-sm font-medium text-gray-700">{c.name}</span>
                        {c.model && (
                          <span className="ml-2 text-xs text-gray-400">{c.model}</span>
                        )}
                      </div>
                      <span className="text-sm font-semibold text-gray-900">{c.value}</span>
                    </div>
                    {(c.confidence != null || c.authority_source || c.last_verified_at) && (
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1 mt-1.5 text-[11px] text-gray-400">
                        {c.confidence != null && (
                          <span>{Math.round(c.confidence * 100)}% confidence</span>
                        )}
                        {c.authority_source && (
                          <span>via {c.authority_source}</span>
                        )}
                        {c.last_verified_at && (
                          <span>verified {formatDate(c.last_verified_at)}</span>
                        )}
                      </div>
                    )}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Sources */}
          {result.sources?.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Sources
              </h3>
              <div className="flex flex-wrap gap-2">
                {result.sources.map((s, i) => (
                  <SourceChip key={typeof s === "string" ? s : i} source={s} />
                ))}
              </div>
            </div>
          )}
        </div>
      )}

      {/* ── Empty / hint ────────────────────────── */}
      {!result && !mutation.isPending && !mutation.isError && (
        <div className="text-center py-12 text-gray-400 space-y-2">
          <SearchIcon />
          <p className="text-sm">Ask a question to query your knowledge graph.</p>
          <div className="flex flex-wrap justify-center gap-2 pt-2">
            {["What is our current MRR?", "How healthy are our customers?"].map((q) => (
              <button
                key={q}
                onClick={() => { setInput(q); mutation.mutate(q); }}
                className="px-3 py-1.5 text-xs rounded-lg border border-gray-200 text-gray-500 hover:bg-gray-50 transition-colors"
              >
                {q}
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SourceChip({ source }) {
  if (!source) return null;
  if (typeof source !== "object") {
    return (
      <span className="px-2.5 py-1 text-xs rounded-full bg-gray-100 text-gray-600">
        {String(source)}
      </span>
    );
  }
  const label = source.type || source.url || "Source";
  const meta = [source.author, source.date].filter(Boolean).join(" · ");
  return (
    <span
      className="inline-flex items-center gap-1.5 px-2.5 py-1 text-xs rounded-full bg-gray-100 text-gray-600"
      title={meta || undefined}
    >
      {source.url ? (
        <a href={source.url} target="_blank" rel="noopener noreferrer" className="underline">
          {label}
        </a>
      ) : (
        label
      )}
      {meta && <span className="text-gray-400">{meta}</span>}
    </span>
  );
}

function formatDate(iso) {
  if (!iso) return null;
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function SearchIcon() {
  return (
    <svg className="w-10 h-10 mx-auto text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
    </svg>
  );
}
