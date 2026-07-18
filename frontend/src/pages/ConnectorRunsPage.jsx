import { AlertTriangle, ArrowLeft, CheckCircle2, Clock3, Loader2, XCircle } from "lucide-react";
import { Link, useParams } from "react-router-dom";

import { useConnectorSyncJobs, useConnectors } from "../api/hooks";

export default function ConnectorRunsPage() {
  const { connectorType } = useParams();
  const connectorsQuery = useConnectors();
  const connector = (connectorsQuery.data || []).find((item) => item.type === connectorType) || null;
  const jobsQuery = useConnectorSyncJobs(connector?.id, { enabled: Boolean(connector?.id) });
  const jobs = jobsQuery.data || [];

  return (
    <div className="relative mx-auto w-full max-w-4xl space-y-6">
      <header>
        <Link to="/app/connectors" className="inline-flex items-center gap-1.5 text-xs font-black text-[#68685f] hover:text-[#171713] dark:text-[#aaa9a0] dark:hover:text-white">
          <ArrowLeft className="h-3.5 w-3.5" /> Connectors
        </Link>
        <p className="mt-6 text-xs font-black uppercase tracking-[0.18em] text-[#85857c]">Connector evidence</p>
        <h1 className="mt-2 text-3xl font-black tracking-tight">{connector?.name || connectorType || "Connector"} runs</h1>
        <p className="mt-2 max-w-2xl text-sm leading-6 text-[#68685f] dark:text-[#aaa9a0]">Complete sync history for this connector, including failures and recorded processing results.</p>
      </header>

      {connectorsQuery.isLoading || jobsQuery.isLoading ? <State icon={Loader2} title="Loading connector runs…" spin /> : null}
      {connectorsQuery.isError || jobsQuery.isError ? <State icon={AlertTriangle} title="Could not load connector runs" detail={connectorsQuery.error?.message || jobsQuery.error?.message} /> : null}
      {!connectorsQuery.isLoading && !connectorsQuery.isError && !connector ? <State icon={AlertTriangle} title="Connector not found" detail="Return to Connectors and choose an available connector." /> : null}
      {connector && !jobsQuery.isLoading && !jobsQuery.isError ? (
        jobs.length ? (
          <div className="space-y-3">
            {jobs.map((job) => <ConnectorRun key={job.jobId || `${job.status}-${job.createdAt}`} job={job} />)}
          </div>
        ) : <State icon={Clock3} title="No sync runs recorded" detail="Run this connector once and its durable sync evidence will appear here." />
      ) : null}
    </div>
  );
}

function ConnectorRun({ job }) {
  const failed = job.status === "failed";
  const completed = job.status === "completed";
  const Icon = failed ? XCircle : completed ? CheckCircle2 : Clock3;
  const metadata = job.resultMetadata || {};
  return (
    <article className="rounded-2xl border border-[#d8d8cf] bg-[#fbfbf6] p-5 dark:border-[#292925] dark:bg-[#141411]">
      <div className="flex flex-col justify-between gap-3 sm:flex-row sm:items-start">
        <div>
          <p className={`flex items-center gap-2 text-[10px] font-black uppercase tracking-[0.14em] ${failed ? "text-red-600" : completed ? "text-emerald-700 dark:text-emerald-300" : "text-amber-700 dark:text-amber-300"}`}><Icon className="h-3.5 w-3.5" />{job.status || "unknown"}</p>
          <h2 className="mt-2 text-sm font-black">{failed ? job.errorMessage || "Connector sync failed" : completed ? summarizeResult(metadata) : `Sync ${job.status}`}</h2>
        </div>
        <time className="text-[10px] font-semibold text-[#85857c]">{formatDate(job.createdAt)}</time>
      </div>
      {job.errorType ? <p className="mt-3 text-xs font-semibold text-red-600 dark:text-red-300">{job.errorType}</p> : null}
      {Object.keys(metadata).length ? <pre className="mt-4 max-h-48 overflow-auto whitespace-pre-wrap rounded-lg bg-[#efefe7] p-3 text-[10px] leading-5 text-[#4f4f48] dark:bg-[#0f0f0c] dark:text-[#d8d8cf]">{JSON.stringify(metadata, null, 2)}</pre> : null}
    </article>
  );
}

function State({ icon: Icon, title, detail, spin = false }) {
  return <div className="rounded-2xl border border-dashed border-[#d8d8cf] bg-[#fbfbf6] p-10 text-center dark:border-[#292925] dark:bg-[#141411]"><Icon className={`mx-auto h-6 w-6 text-[#85857c] ${spin ? "animate-spin" : ""}`} /><h2 className="mt-3 text-sm font-black">{title}</h2>{detail ? <p className="mx-auto mt-2 max-w-xl text-xs leading-5 text-[#68685f] dark:text-[#aaa9a0]">{detail}</p> : null}</div>;
}

function summarizeResult(metadata) {
  const count = metadata.items_synced ?? metadata.documents_created ?? metadata.processed_count;
  return Number.isFinite(Number(count)) ? `${Number(count).toLocaleString()} item${Number(count) === 1 ? "" : "s"} recorded` : "Connector sync completed";
}

function formatDate(value) {
  if (!value) return "Time unavailable";
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? "Time unavailable" : date.toLocaleString();
}
