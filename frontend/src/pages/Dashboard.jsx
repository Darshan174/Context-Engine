import { Link } from "react-router-dom";
import {
  useConnectorProcessingSummary,
  useConnectors,
  useDashboard,
  useEvalSummary,
  useReviewQueue,
} from "../api/hooks";
import MockBadge from "../components/MockBadge";
import StatusView from "../components/StatusView";

const DESTINATIONS = {
  Sources: "/app/sources",
  Models: "/app/models",
  Relationships: "/app/graph",
};

export default function Dashboard() {
  const query = useDashboard();
  const reviewQuery = useReviewQueue();
  const evalQuery = useEvalSummary();
  const connectorsQuery = useConnectors();
  const processingQuery = useConnectorProcessingSummary();

  if (query.isLoading || query.isError) {
    return (
      <div className="max-w-6xl mx-auto">
        <StatusView query={query} empty="No data yet. Create a workspace and add some models." />
      </div>
    );
  }

  const { stats = [], activity = [], alerts = [] } = query.data;
  const reviewItems = reviewQuery.data ?? [];
  const isEmpty = stats.length > 0 && stats.every((s) => s.value === 0);
  const needsReviewCount = reviewItems.filter((item) => item.status === "needs_review").length;
  const conflictCount = reviewItems.filter((item) => item.kind === "conflict").length;
  const historicalCount = reviewItems.filter((item) => item.status === "superseded").length;
  const connectors = (connectorsQuery.data ?? []).filter((connector) => connector.availability === "available");
  const processingByType = new Map(
    (processingQuery.data?.items ?? []).map((item) => [item.connectorType, item]),
  );
  const connectorErrors = connectors.filter((connector) => connector.status === "error").length;
  const queuedConnectors = connectors.filter((connector) => connector.syncQueuedAt).length;
  const pendingExtraction = Array.from(processingByType.values()).reduce(
    (total, item) => total + Number(item.unprocessedDocuments ?? 0),
    0,
  );
  const accuracySummary = evalQuery.data;
  const accuracyThreshold = accuracySummary?.threshold ?? null;
  const accuracyPassRate = accuracySummary?.passRate ?? null;
  const atRiskDomains = (accuracySummary?.domains ?? []).filter(
    (domain) =>
      accuracyThreshold != null &&
      domain.passRate != null &&
      domain.passRate < accuracyThreshold,
  ).length;
  const accuracyBlockers = accuracySummary?.blockers?.length ?? 0;
  const accuracyHealthy =
    accuracyPassRate != null &&
    accuracyThreshold != null &&
    accuracyPassRate >= accuracyThreshold;

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      <div>
        <h2 className="text-lg font-semibold text-gray-800">Overview</h2>
        <p className="text-xs text-gray-400 mt-1">
          Your workspace at a glance — source documents, models, components, and data health.
        </p>
      </div>

      {/* ── Stat cards ──────────────────────────── */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {stats.map((s) => (
          <Link
            key={s.label}
            to={DESTINATIONS[s.label] ?? "/app/query"}
            className="bg-white rounded-xl border border-gray-200 p-5 hover:shadow-sm transition-shadow block"
          >
            <p className="text-xs font-medium text-gray-500 uppercase tracking-wide">{s.label}</p>
            <p className="mt-1 text-2xl font-bold text-gray-900">{s.value.toLocaleString()}</p>
            <p className="mt-1 text-xs text-gray-400">{s.delta}</p>
          </Link>
        ))}
      </div>

      {isEmpty && (
        <div className="bg-brand-50 border border-brand-200 rounded-xl p-5 text-center">
          <p className="text-sm font-medium text-brand-800">Your workspace is empty</p>
          <p className="text-xs text-brand-600 mt-1">
            Head to{" "}
            <Link to="/app/models" className="underline font-medium">
              Models
            </Link>{" "}
            to create your first model and start adding components.
          </p>
        </div>
      )}
      {!isEmpty && stats.some((s) => s.label === "Sources" && s.value > 0) && (
        <div className="bg-emerald-50 border border-emerald-200 rounded-xl p-4">
          <p className="text-sm font-medium text-emerald-800">Live source data is available</p>
          <p className="text-xs text-emerald-700 mt-1">
            Synced connector documents are stored and ready for extraction and query.
          </p>
          <Link to="/app/sources" className="inline-flex mt-3 text-xs font-medium text-emerald-800 underline">
            Inspect source documents
          </Link>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-700">Trust Status</h3>
            <p className="text-xs text-gray-400 mt-1">
              Review pressure, contradictions, and historical context that may affect downstream answers.
            </p>
          </div>
          <Link to="/app/review" className="text-xs font-medium text-brand-700 hover:text-brand-800">
            Open review queue
          </Link>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <TrustCard
            label="Needs review"
            value={needsReviewCount}
            tone="amber"
            to="/app/review?status=needs_review"
          />
          <TrustCard
            label="Conflicts"
            value={conflictCount}
            tone="red"
            to="/app/review?kind=conflict"
          />
          <TrustCard
            label="Historical facts"
            value={historicalCount}
            tone="slate"
            to="/app/review?status=superseded"
          />
        </div>
        {needsReviewCount > 0 && (
          <p className="mt-4 text-xs text-amber-700">
            Review attention is needed before low-confidence or conflicting facts become default operating context.
          </p>
        )}
      </div>

      {accuracySummary && (
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="flex items-center gap-2">
                <h3 className="text-sm font-semibold text-gray-700">Accuracy Status</h3>
                {evalQuery.isMock && <MockBadge />}
              </div>
              <p className="text-xs text-gray-400 mt-1">
                Eval pass rate, domain risk, and remaining blockers before trust claims get stronger.
              </p>
            </div>
            <Link to="/app/accuracy" className="text-xs font-medium text-brand-700 hover:text-brand-800">
              Open accuracy dashboard
            </Link>
          </div>
          <div className="mt-4 grid gap-3 sm:grid-cols-3">
            <TrustCard
              label="Pass rate"
              value={formatPercent(accuracyPassRate)}
              tone={accuracyHealthy ? "emerald" : "amber"}
              to="/app/accuracy"
            />
            <TrustCard
              label="At-risk domains"
              value={atRiskDomains}
              tone={atRiskDomains > 0 ? "amber" : "slate"}
              to="/app/accuracy"
            />
            <TrustCard
              label="Open blockers"
              value={accuracyBlockers}
              tone={accuracyBlockers > 0 ? "red" : "slate"}
              to="/app/accuracy"
            />
          </div>
          <p className={`mt-4 text-xs ${accuracyHealthy ? "text-emerald-700" : "text-amber-700"}`}>
            Latest eval run {formatDateTime(accuracySummary.latestRunAt)}.
            {accuracyThreshold != null ? ` Current gate ${formatPercent(accuracyThreshold)}.` : ""}
          </p>
        </div>
      )}

      <div className="bg-white rounded-xl border border-gray-200 p-5">
        <div className="flex items-start justify-between gap-4">
          <div>
            <h3 className="text-sm font-semibold text-gray-700">Pipeline Status</h3>
            <p className="text-xs text-gray-400 mt-1">
              Connector health, queued syncs, and extraction pressure across the workspace.
            </p>
          </div>
          <Link to="/app/connectors" className="text-xs font-medium text-brand-700 hover:text-brand-800">
            Open connectors
          </Link>
        </div>
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <TrustCard
            label="Queued syncs"
            value={queuedConnectors}
            tone="slate"
            to="/app/connectors"
          />
          <TrustCard
            label="Connector errors"
            value={connectorErrors}
            tone={connectorErrors > 0 ? "red" : "slate"}
            to="/app/connectors"
          />
          <TrustCard
            label="Pending extraction"
            value={pendingExtraction}
            tone={pendingExtraction > 0 ? "amber" : "slate"}
            to="/app/sources?processed=unprocessed"
          />
        </div>
        {connectors.length > 0 ? (
          <div className="mt-4 grid gap-3 lg:grid-cols-2">
            {connectors.map((connector) => (
              <PipelineCard
                key={connector.type}
                connector={connector}
                processing={processingByType.get(connector.type) ?? null}
              />
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-gray-400">
            No live connectors are configured yet.
          </p>
        )}
      </div>

      <div className="grid lg:grid-cols-3 gap-6">
        {/* ── Recent activity ────────────────────── */}
        <div className="lg:col-span-2 bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Recent Activity</h3>
          {activity.length === 0 ? (
            <p className="text-sm text-gray-400">No recent activity.</p>
          ) : (
            <ul className="divide-y divide-gray-100">
              {activity.map((a) => (
                <li key={a.id} className="py-3 flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3">
                    <ActivityDot type={a.type} />
                    <span className="text-sm text-gray-700">{a.text}</span>
                  </div>
                  <span className="text-xs text-gray-400 whitespace-nowrap">{a.ts}</span>
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* ── Stale alerts ───────────────────────── */}
        <div className="bg-white rounded-xl border border-gray-200 p-5">
          <h3 className="text-sm font-semibold text-gray-700 mb-4">Stale Alerts</h3>
          {alerts.length === 0 ? (
            <p className="text-sm text-gray-400">No alerts.</p>
          ) : (
            <ul className="space-y-3">
              {alerts.map((a) => (
                <li
                  key={a.id}
                  className={`rounded-lg p-3 text-sm border ${
                    a.severity === "error"
                      ? "bg-red-50 border-red-200 text-red-800"
                      : "bg-amber-50 border-amber-200 text-amber-800"
                  }`}
                >
                  <p className="font-medium">{a.source}</p>
                  <p className="text-xs mt-0.5 opacity-80">{a.message}</p>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}

function TrustCard({ label, value, tone, to }) {
  const toneClasses = {
    amber: "bg-amber-50 border-amber-200 text-amber-800",
    emerald: "bg-emerald-50 border-emerald-200 text-emerald-800",
    red: "bg-red-50 border-red-200 text-red-800",
    slate: "bg-slate-50 border-slate-200 text-slate-700",
  };

  return (
    <Link
      to={to ?? "/app/review"}
      className={`rounded-xl border px-4 py-3 block hover:shadow-sm transition-shadow ${toneClasses[tone] ?? toneClasses.slate}`}
    >
      <p className="text-[11px] uppercase tracking-wide opacity-80">{label}</p>
      <p className="mt-2 text-2xl font-semibold">{value}</p>
    </Link>
  );
}

function formatPercent(value) {
  if (value == null) return "—";
  return `${Math.round(value * 100)}%`;
}

function formatDateTime(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function PipelineCard({ connector, processing }) {
  const pending = Number(processing?.unprocessedDocuments ?? 0);
  const processed = Number(processing?.processedDocuments ?? connector.totalProcessedCount ?? 0);
  const total = Number(processing?.totalDocuments ?? connector.itemsSynced ?? 0);

  return (
    <div className="rounded-xl border border-gray-200 bg-gray-50 p-4">
      <div className="flex items-start justify-between gap-3">
        <div>
          <div className="flex items-center gap-2">
            <p className="text-sm font-semibold text-gray-800">{connector.name}</p>
            {connector.providerLabel && (
              <span className="rounded-full bg-white px-2 py-0.5 text-[10px] font-medium text-gray-600 border border-gray-200">
                {connector.providerLabel}
              </span>
            )}
          </div>
          <p className="mt-1 text-xs text-gray-500">{connector.description}</p>
        </div>
        <span
          className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
            connector.status === "connected"
              ? "bg-emerald-100 text-emerald-700"
              : connector.status === "error"
                ? "bg-red-100 text-red-700"
                : "bg-gray-100 text-gray-600"
          }`}
        >
          {connector.status}
        </span>
      </div>

      <div className="mt-3 grid grid-cols-2 gap-y-2 text-xs">
        <span className="text-gray-400">Last sync</span>
        <span className="text-right text-gray-700">{connector.lastSync}</span>
        <span className="text-gray-400">Stored docs</span>
        <span className="text-right text-gray-700">{total.toLocaleString()}</span>
        <span className="text-gray-400">Processed</span>
        <span className="text-right text-gray-700">{processed.toLocaleString()}</span>
        <span className="text-gray-400">Pending</span>
        <span className="text-right text-gray-700">{pending.toLocaleString()}</span>
      </div>

      {connector.syncQueuedAt && (
        <p className="mt-3 text-[11px] text-blue-700">
          Sync queued {connector.syncQueuedAt}.
        </p>
      )}
      {!connector.syncQueuedAt && connector.status === "connected" && pending > 0 && (
        <p className="mt-3 text-[11px] text-amber-700">
          Extraction is still pending for {pending.toLocaleString()} source document{pending === 1 ? "" : "s"}.
        </p>
      )}
      {connector.status === "error" && (
        <p className="mt-3 text-[11px] text-red-700">
          This connector needs attention before new source data can be trusted.
        </p>
      )}
      {connector.status === "disconnected" && (
        <p className="mt-3 text-[11px] text-gray-500">
          Connect this source to start ingesting raw context into the workspace.
        </p>
      )}

      <div className="mt-4 flex flex-wrap gap-3 text-xs">
        <Link to="/app/connectors" className="font-medium text-brand-700 hover:text-brand-800">
          Open connector
        </Link>
        {connector.connectorId && (
          <Link
            to={`/app/connectors/${connector.type}/runs`}
            className="font-medium text-brand-700 hover:text-brand-800"
          >
            Run history
          </Link>
        )}
        {total > 0 && (
          <Link to="/app/sources" className="font-medium text-brand-700 hover:text-brand-800">
            Sources
          </Link>
        )}
      </div>
    </div>
  );
}

const DOT_COLORS = {
  sync: "bg-blue-400",
  create: "bg-emerald-400",
  merge: "bg-brand-500",
  alert: "bg-amber-400",
  model: "bg-purple-400",
};

function ActivityDot({ type }) {
  return (
    <span className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${DOT_COLORS[type] || "bg-gray-300"}`} />
  );
}
