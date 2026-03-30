import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useSourceDocuments } from "../api/hooks";
import MockBadge from "../components/MockBadge";
import StatusView from "../components/StatusView";

const CONNECTOR_OPTIONS = [
  { value: "all", label: "All connectors" },
  { value: "slack", label: "Slack" },
  { value: "notion", label: "Notion" },
  { value: "gdrive", label: "Google Drive" },
  { value: "gong", label: "Gong" },
];

const PROCESSED_OPTIONS = [
  { value: "all", label: "All states" },
  { value: "processed", label: "Processed" },
  { value: "unprocessed", label: "Pending" },
];

const CONNECTOR_PILL = {
  slack: "bg-violet-100 text-violet-700",
  notion: "bg-gray-100 text-gray-700",
  gdrive: "bg-emerald-100 text-emerald-700",
  gong: "bg-indigo-100 text-indigo-700",
  unknown: "bg-slate-100 text-slate-600",
};

export default function Sources() {
  const [connector, setConnector] = useState("all");
  const [processed, setProcessed] = useState("all");
  const [search, setSearch] = useState("");
  const { data, isMock, ...query } = useSourceDocuments({ connector, processed, search });
  const documents = data ?? [];
  const [selectedId, setSelectedId] = useState(null);

  useEffect(() => {
    if (documents.length === 0) {
      setSelectedId(null);
      return;
    }
    if (!selectedId || !documents.some((doc) => doc.id === selectedId)) {
      setSelectedId(documents[0].id);
    }
  }, [documents, selectedId]);

  const selectedDocument = useMemo(
    () => documents.find((doc) => doc.id === selectedId) ?? null,
    [documents, selectedId],
  );

  if (query.isLoading || query.isError) {
    return (
      <div className="max-w-6xl mx-auto">
        <StatusView query={query} empty="No source documents yet." />
      </div>
    );
  }

  const processedCount = documents.filter((doc) => doc.processed).length;
  const pendingCount = documents.length - processedCount;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-800">Sources</h2>
            {isMock && <MockBadge />}
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Inspect the raw documents that feed the knowledge graph before and after extraction.
          </p>
          {isMock && (
            <p className="text-xs text-amber-600 mt-2">
              Showing demo source documents until the backend source-documents API is available.
            </p>
          )}
        </div>
        <div className="rounded-xl border border-gray-200 bg-white px-4 py-3 text-right">
          <p className="text-[11px] uppercase tracking-wide text-gray-400">Pipeline</p>
          <p className="text-sm font-medium text-gray-700">
            {documents.length} stored · {processedCount} processed · {pendingCount} pending
          </p>
        </div>
      </div>

      <div className="grid gap-3 md:grid-cols-[minmax(0,1fr)_220px_220px]">
        <label className="block">
          <span className="block text-xs font-medium text-gray-600 mb-1">Search</span>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search content, author, channel, page..."
            aria-label="Search source documents"
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg focus:outline-none focus:ring-2 focus:ring-brand-500/40"
          />
        </label>

        <label className="block">
          <span className="block text-xs font-medium text-gray-600 mb-1">Connector</span>
          <select
            value={connector}
            onChange={(e) => setConnector(e.target.value)}
            aria-label="Filter source documents by connector"
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/40"
          >
            {CONNECTOR_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="block text-xs font-medium text-gray-600 mb-1">Processing</span>
          <select
            value={processed}
            onChange={(e) => setProcessed(e.target.value)}
            aria-label="Filter source documents by processing state"
            className="w-full px-3 py-2 text-sm border border-gray-200 rounded-lg bg-white focus:outline-none focus:ring-2 focus:ring-brand-500/40"
          >
            {PROCESSED_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </label>
      </div>

      {documents.length === 0 ? (
        <StatusView
          query={{ isLoading: false, isError: false, data: [] }}
          empty="No source documents match the current filters."
        />
      ) : (
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1.2fr)_minmax(320px,0.8fr)]">
          <section
            aria-label="Stored documents"
            className="bg-white rounded-xl border border-gray-200 overflow-hidden"
          >
            <div className="px-4 py-3 border-b border-gray-100 flex items-center justify-between">
              <div>
                <p className="text-sm font-semibold text-gray-700">Stored documents</p>
                <p className="text-xs text-gray-400">
                  Select a document to inspect its raw content and lineage.
                </p>
              </div>
              <Link to="/connectors" className="text-xs font-medium text-brand-700 hover:text-brand-800">
                Back to connectors
              </Link>
            </div>

            <div className="divide-y divide-gray-100">
              {documents.map((doc) => (
                <button
                  key={doc.id}
                  type="button"
                  onClick={() => setSelectedId(doc.id)}
                  aria-pressed={selectedId === doc.id}
                  className={`w-full text-left px-4 py-4 transition-colors ${
                    selectedId === doc.id ? "bg-brand-50" : "hover:bg-gray-50"
                  }`}
                >
                  <div className="flex items-start justify-between gap-3">
                    <div className="min-w-0">
                      <div className="flex flex-wrap items-center gap-2">
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                            CONNECTOR_PILL[doc.connectorType] ?? CONNECTOR_PILL.unknown
                          }`}
                        >
                          {doc.connectorType}
                        </span>
                        <span
                          className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                            doc.processed
                              ? "bg-emerald-100 text-emerald-700"
                              : "bg-amber-100 text-amber-700"
                          }`}
                        >
                          {doc.processed ? "Processed" : "Pending"}
                        </span>
                        {doc.location && (
                          <span className="text-[11px] text-gray-400 truncate">{doc.location}</span>
                        )}
                      </div>
                      <p className="mt-2 text-sm font-medium text-gray-800 truncate">
                        {doc.author || "Unknown author"}
                      </p>
                      <p className="mt-1 text-xs text-gray-500 line-clamp-2">{doc.preview}</p>
                    </div>
                    <div className="text-right shrink-0">
                      <p className="text-[11px] text-gray-400">{formatDate(doc.createdAtSource)}</p>
                      <p className="text-[11px] text-gray-400 mt-1">Ingested {formatDate(doc.ingestedAt)}</p>
                    </div>
                  </div>
                </button>
              ))}
            </div>
          </section>

          <section
            aria-label="Document detail"
            className="bg-white rounded-xl border border-gray-200 p-5 space-y-4"
          >
            {selectedDocument ? (
              <>
                <div className="flex items-center justify-between gap-3">
                  <h3 className="text-sm font-semibold text-gray-700">Document detail</h3>
                  <span
                    className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${
                      selectedDocument.processed
                        ? "bg-emerald-100 text-emerald-700"
                        : "bg-amber-100 text-amber-700"
                    }`}
                  >
                    {selectedDocument.processed ? "Processed" : "Pending extraction"}
                  </span>
                </div>

                <dl className="grid grid-cols-[110px_minmax(0,1fr)] gap-y-2 text-xs">
                  <dt className="text-gray-400">Connector</dt>
                  <dd className="text-gray-700">{selectedDocument.connectorType}</dd>
                  <dt className="text-gray-400">Author</dt>
                  <dd className="text-gray-700">{selectedDocument.author || "Unknown"}</dd>
                  <dt className="text-gray-400">Location</dt>
                  <dd className="text-gray-700">{selectedDocument.location || "—"}</dd>
                  <dt className="text-gray-400">Created</dt>
                  <dd className="text-gray-700">{formatDate(selectedDocument.createdAtSource)}</dd>
                  <dt className="text-gray-400">Ingested</dt>
                  <dd className="text-gray-700">{formatDate(selectedDocument.ingestedAt)}</dd>
                  <dt className="text-gray-400">Processed</dt>
                  <dd className="text-gray-700">{formatDate(selectedDocument.processedAt)}</dd>
                  <dt className="text-gray-400">External ID</dt>
                  <dd className="text-gray-700 break-all">{selectedDocument.externalId}</dd>
                </dl>

                {selectedDocument.sourceUrl && (
                  <a
                    href={selectedDocument.sourceUrl}
                    target="_blank"
                    rel="noreferrer"
                    className="inline-flex text-xs font-medium text-brand-700 hover:text-brand-800"
                  >
                    Open original source
                  </a>
                )}

                <div>
                  <p className="text-xs font-medium text-gray-600 mb-2">Raw content</p>
                  <pre className="rounded-xl bg-gray-50 border border-gray-100 p-4 text-xs text-gray-700 whitespace-pre-wrap break-words font-sans max-h-[420px] overflow-y-auto">
                    {selectedDocument.content}
                  </pre>
                </div>
              </>
            ) : (
              <div className="flex flex-col items-center justify-center py-16 text-gray-400">
                <p className="text-sm">Select a document to inspect it.</p>
              </div>
            )}
          </section>
        </div>
      )}
    </div>
  );
}

function formatDate(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}
