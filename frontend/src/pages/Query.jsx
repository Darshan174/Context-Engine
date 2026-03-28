import { useState } from "react";
import { useContextQuery } from "../api/hooks";
import MockBadge from "../components/MockBadge";

export default function Query() {
  const [input, setInput] = useState("");
  const mutation = useContextQuery();
  const result = mutation.data;
  const isMock = result?._isMock ?? true;

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
      </div>

      {/* ── Input ───────────────────────────────── */}
      <form onSubmit={handleSubmit} className="flex gap-3">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a question about your company data..."
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
        <div className="flex items-center gap-3 py-8 justify-center text-gray-400">
          <svg className="animate-spin h-5 w-5 text-brand-600" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          <span className="text-sm">Querying knowledge graph...</span>
        </div>
      )}

      {/* ── Error ───────────────────────────────── */}
      {mutation.isError && (
        <div className="bg-red-50 border border-red-200 rounded-xl p-4 text-center">
          <p className="text-sm text-red-600">
            {mutation.error?.message || "Failed to get an answer."}
          </p>
        </div>
      )}

      {/* ── Answer ──────────────────────────────── */}
      {result && !mutation.isPending && (
        <div className="space-y-4">
          {/* Question echo */}
          <div className="bg-gray-100 rounded-xl px-5 py-3">
            <p className="text-sm text-gray-600 font-medium">{result.question}</p>
          </div>

          {/* Answer body */}
          <div className="bg-white border border-gray-200 rounded-xl p-5 space-y-4">
            <p className="text-sm text-gray-800 leading-relaxed">{result.answer}</p>

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

            <p className="text-[11px] text-gray-300">{result.answeredAt}</p>
          </div>

          {/* Cited components */}
          {result.components?.length > 0 && (
            <div className="bg-white border border-gray-200 rounded-xl p-5">
              <h3 className="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-3">
                Cited Components
              </h3>
              <div className="divide-y divide-gray-100">
                {result.components.map((c) => (
                  <div key={c.id} className="flex items-center justify-between py-2">
                    <div>
                      <span className="text-sm font-medium text-gray-700">{c.name}</span>
                      {c.model && (
                        <span className="ml-2 text-xs text-gray-400">{c.model}</span>
                      )}
                    </div>
                    <span className="text-sm font-semibold text-gray-900">{c.value}</span>
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
                {result.sources.map((s) => (
                  <span
                    key={s}
                    className="px-2.5 py-1 text-xs rounded-full bg-gray-100 text-gray-600"
                  >
                    {s}
                  </span>
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

function SearchIcon() {
  return (
    <svg className="w-10 h-10 mx-auto text-gray-300" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={1.5}>
      <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-5.197-5.197m0 0A7.5 7.5 0 105.196 5.196a7.5 7.5 0 0010.607 10.607z" />
    </svg>
  );
}
