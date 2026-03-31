import { Link, useParams } from "react-router-dom";
import {
  useConnectors,
  useConnectorSyncJobs,
  useConnectorSyncStatus,
} from "../api/hooks";
import MockBadge from "../components/MockBadge";
import StatusView from "../components/StatusView";

const STATUS_PILL = {
  completed: "bg-emerald-100 text-emerald-700",
  failed: "bg-red-100 text-red-700",
  pending: "bg-blue-100 text-blue-700",
  running: "bg-blue-100 text-blue-700",
};

export default function ConnectorRuns() {
  const { connectorType } = useParams();
  const connectorsQuery = useConnectors();
  const connectors = connectorsQuery.data ?? [];
  const connector = connectors.find((item) => item.type === connectorType) ?? null;
  const jobsQuery = useConnectorSyncJobs(connector?.connectorId, {
    enabled: !connectorsQuery.isMock && !!connector?.connectorId,
  });
  const latestJobQuery = useConnectorSyncStatus(connector?.connectorId, {
    enabled: !connectorsQuery.isMock && !!connector?.connectorId,
  });

  if (connectorsQuery.isLoading || connectorsQuery.isError) {
    return (
      <div className="max-w-5xl mx-auto">
        <StatusView query={connectorsQuery} empty="Connector runs are not available." />
      </div>
    );
  }

  if (!connector) {
    return (
      <div className="max-w-5xl mx-auto">
        <StatusView query={{ isLoading: false, isError: false, data: [] }} empty="Connector not found." />
      </div>
    );
  }

  const isMock = connectorsQuery.isMock || !connector.connectorId;
  const jobs = jobsQuery.data ?? [];
  const latestJob = latestJobQuery.data ?? null;

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-800">{connector.name} Run History</h2>
            {isMock && <MockBadge />}
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Inspect background sync and reprocess jobs for this connector.
          </p>
          {isMock && (
            <p className="text-xs text-amber-600 mt-2">
              Job history is only available when the backend sync-job endpoints are live for this connector.
            </p>
          )}
        </div>
        <Link
          to="/app/connectors"
          className="rounded-lg border border-gray-200 bg-white px-3 py-2 text-xs font-medium text-gray-700 hover:bg-gray-50"
        >
          Back to connectors
        </Link>
      </div>

      <div className="grid gap-4 md:grid-cols-[minmax(0,1.1fr)_minmax(280px,0.9fr)]">
        <section className="rounded-xl border border-gray-200 bg-white p-5 space-y-4">
          <div>
            <p className="text-xs uppercase tracking-wide text-gray-400">Connector</p>
            <p className="mt-1 text-sm font-semibold text-gray-800">{connector.name}</p>
            <p className="mt-1 text-xs text-gray-500">{connector.description}</p>
          </div>

          <div className="grid grid-cols-2 gap-y-2 text-xs">
            <span className="text-gray-400">Status</span>
            <span className="text-right text-gray-700">{connector.status}</span>
            <span className="text-gray-400">Last sync</span>
            <span className="text-right text-gray-700">{connector.lastSync}</span>
            <span className="text-gray-400">Stored docs</span>
            <span className="text-right text-gray-700">
              {Number(connector.itemsSynced || 0).toLocaleString()}
            </span>
            {connector.processedCount != null && (
              <>
                <span className="text-gray-400">Processed docs</span>
                <span className="text-right text-gray-700">
                  {Number(connector.processedCount || 0).toLocaleString()}
                </span>
              </>
            )}
          </div>
        </section>

        <section className="rounded-xl border border-gray-200 bg-white p-5 space-y-3">
          <div className="flex items-center justify-between gap-3">
            <p className="text-xs uppercase tracking-wide text-gray-400">Latest job</p>
            {latestJob ? <StatusBadge status={latestJob.status} /> : null}
          </div>
          {latestJob ? (
            <div className="space-y-2 text-xs text-gray-600">
              <p>
                <span className="text-gray-400">Type:</span>{" "}
                <span className="text-gray-700 capitalize">{latestJob.jobType ?? "sync"}</span>
              </p>
              <p>
                <span className="text-gray-400">Created:</span> {formatDateTime(latestJob.createdAt)}
              </p>
              {latestJob.startedAt && (
                <p>
                  <span className="text-gray-400">Started:</span> {formatDateTime(latestJob.startedAt)}
                </p>
              )}
              {latestJob.completedAt && (
                <p>
                  <span className="text-gray-400">Finished:</span> {formatDateTime(latestJob.completedAt)}
                </p>
              )}
              {latestJob.status === "completed" && (
                <p className="rounded-lg bg-emerald-50 px-3 py-2 text-emerald-700">
                  {formatCompletedSyncNotice(connector.name, latestJob.resultMetadata)}
                </p>
              )}
              {latestJob.status === "failed" && (
                <p className="rounded-lg bg-red-50 px-3 py-2 text-red-700">
                  {latestJob.errorType ? `${latestJob.errorType}: ` : ""}
                  {latestJob.errorMessage || "Job failed."}
                </p>
              )}
              {(latestJob.status === "pending" || latestJob.status === "running") && (
                <p className="rounded-lg bg-blue-50 px-3 py-2 text-blue-700">
                  Worker is {latestJob.status === "running" ? "running" : "queued"} for this job.
                </p>
              )}
            </div>
          ) : (
            <p className="text-xs text-gray-500">No run has been recorded for this connector yet.</p>
          )}
        </section>
      </div>

      <section className="rounded-xl border border-gray-200 bg-white overflow-hidden">
        <div className="border-b border-gray-100 px-5 py-4">
          <p className="text-sm font-semibold text-gray-700">Recent runs</p>
          <p className="mt-1 text-xs text-gray-400">
            Completed, failed, queued, and reprocess jobs are listed here in reverse chronological order.
          </p>
        </div>
        {isMock ? (
          <div className="px-5 py-8 text-sm text-gray-500">
            Live run history is unavailable in demo mode.
          </div>
        ) : jobs.length === 0 ? (
          <div className="px-5 py-8 text-sm text-gray-500">
            No sync or reprocess jobs have been recorded for this connector yet.
          </div>
        ) : (
          <div className="divide-y divide-gray-100">
            {jobs.map((job) => (
              <div key={job.jobId ?? `${job.status}-${job.createdAt}`} className="px-5 py-4">
                <div className="flex items-start justify-between gap-4">
                  <div className="min-w-0">
                    <div className="flex flex-wrap items-center gap-2">
                      <StatusBadge status={job.status} />
                      <span className="rounded-full bg-gray-100 px-2 py-0.5 text-[10px] font-medium text-gray-600 capitalize">
                        {job.jobType ?? "sync"}
                      </span>
                    </div>
                    <p className="mt-2 text-sm text-gray-800">
                      {job.status === "completed"
                        ? summarizeSyncJob(job.resultMetadata)
                        : job.status === "failed"
                          ? job.errorMessage || "Sync failed."
                          : `Job ${job.status}`}
                    </p>
                    <div className="mt-1 flex flex-wrap items-center gap-x-3 gap-y-1 text-[11px] text-gray-400">
                      <span>Created {formatDateTime(job.createdAt)}</span>
                      {job.startedAt && <span>Started {formatDateTime(job.startedAt)}</span>}
                      {job.completedAt && <span>Finished {formatDateTime(job.completedAt)}</span>}
                    </div>
                  </div>
                  <span className="text-[11px] text-gray-400">{job.jobId}</span>
                </div>
              </div>
            ))}
          </div>
        )}
      </section>
    </div>
  );
}

function StatusBadge({ status }) {
  return (
    <span
      className={`rounded-full px-2 py-0.5 text-[10px] font-medium ${
        STATUS_PILL[status] ?? "bg-slate-100 text-slate-600"
      }`}
    >
      {status}
    </span>
  );
}

function summarizeSyncJob(metadata) {
  if (!metadata || typeof metadata !== "object") {
    return "Sync completed.";
  }
  const fetched = Number(metadata.documents_fetched ?? 0);
  const persisted = Number(metadata.documents_persisted ?? 0);
  const processed = Number(metadata.documents_processed ?? 0);
  return `Fetched ${fetched}, stored ${persisted}, processed ${processed}`;
}

function formatCompletedSyncNotice(connectorName, metadata) {
  if (!metadata || typeof metadata !== "object") {
    return `${connectorName} sync completed.`;
  }

  const fetched = Number(metadata.documents_fetched ?? 0);
  const persisted = Number(metadata.documents_persisted ?? 0);
  const processed = Number(metadata.documents_processed ?? 0);
  const syncMode = metadata.sync_mode ? ` (${metadata.sync_mode})` : "";

  return `${connectorName} sync completed: fetched ${fetched}, stored ${persisted}, processed ${processed}${syncMode}.`;
}

function formatDateTime(value) {
  if (!value) return "—";
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}
