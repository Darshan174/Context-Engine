import { useMemo, useState } from "react";
import {
  useConnectors,
  useDisconnectConnector,
  useSyncConnector,
  useWorkspaces,
} from "../api/hooks";
import MockBadge from "../components/MockBadge";
import StatusView from "../components/StatusView";
import { resolveWorkspaceId, useWorkspaceSelection } from "../context/WorkspaceContext";

const STATUS_PILL = {
  connected: "bg-emerald-100 text-emerald-700",
  disconnected: "bg-gray-100 text-gray-600",
  warning: "bg-amber-100 text-amber-700",
  error: "bg-red-100 text-red-700",
  coming_soon: "bg-slate-100 text-slate-600",
};

const STATUS_LABEL = {
  connected: "Connected",
  disconnected: "Not connected",
  warning: "Warning",
  error: "Error",
  coming_soon: "Coming soon",
};

export default function Connectors() {
  const { data, isMock, ...query } = useConnectors();
  const workspaces = useWorkspaces();
  const { selectedId } = useWorkspaceSelection();
  const syncMut = useSyncConnector();
  const disconnectMut = useDisconnectConnector();
  const [actionError, setActionError] = useState(null);
  const [actionNotice, setActionNotice] = useState(null);

  const workspaceId = useMemo(
    () => resolveWorkspaceId(workspaces.data, selectedId),
    [workspaces.data, selectedId],
  );

  if (query.isLoading || query.isError) {
    return (
      <div className="max-w-5xl mx-auto">
        <StatusView query={{ data, ...query }} empty="No connectors configured." />
      </div>
    );
  }

  const list = data ?? [];

  return (
    <div className="max-w-5xl mx-auto space-y-6">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-3">
            <h2 className="text-lg font-semibold text-gray-800">Connectors</h2>
            {isMock && <MockBadge />}
          </div>
          <p className="text-xs text-gray-400 mt-1">
            Slack is the Phase 2 reference connector. Notion, Drive, and Gong stay visible here so the
            admin surface is stable while the backend expands.
          </p>
          {isMock && (
            <p className="text-xs text-amber-600 mt-2">
              Connector cards are in demo mode right now. OAuth and sync actions unlock once the backend
              endpoints are live.
            </p>
          )}
        </div>
        <div className="px-3 py-2 rounded-lg border border-gray-200 bg-white text-right">
          <p className="text-[11px] uppercase tracking-wide text-gray-400">Phase</p>
          <p className="text-sm font-medium text-gray-700">Slack first</p>
        </div>
      </div>

      {actionError && (
        <div className="rounded-xl border border-red-200 bg-red-50 p-4">
          <p className="text-sm text-red-700">{actionError}</p>
        </div>
      )}
      {actionNotice && (
        <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4">
          <p className="text-sm text-emerald-700">{actionNotice}</p>
        </div>
      )}

      {list.length === 0 ? (
        <StatusView query={{ data: list, isLoading: false, isError: false }} empty="No connectors configured." />
      ) : (
        <div className="grid sm:grid-cols-2 gap-5">
          {list.map((connector) => (
            <ConnectorCard
              key={connector.type}
              connector={connector}
              disabled={isMock}
              workspaceId={workspaceId}
              syncMut={syncMut}
              disconnectMut={disconnectMut}
              onActionError={setActionError}
              onActionNotice={setActionNotice}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ConnectorCard({
  connector,
  disabled,
  workspaceId,
  syncMut,
  disconnectMut,
  onActionError,
  onActionNotice,
}) {
  const {
    connectorId,
    type,
    name,
    description,
    status,
    lastSync,
    itemsSynced,
    color,
    availability,
    message,
    teamName,
    scope,
    syncQueuedAt,
  } = connector;

  const canConnect = !disabled && availability === "available" && status === "disconnected" && !!workspaceId;
  const canSync = !disabled && !!connectorId && (status === "connected" || status === "error");
  const canDisconnect = !disabled && !!connectorId && (status === "connected" || status === "error");
  const installHref = workspaceId
    ? `/api/connectors/${type}/install?workspace_id=${workspaceId}`
    : null;

  const handleSync = () => {
    onActionError(null);
    onActionNotice(null);
    syncMut.mutate(connectorId, {
      onError: (err) => onActionError(err?.message || `Failed to queue sync for ${name}.`),
      onSuccess: () => onActionNotice(`${name} sync queued. Refreshing connector state.`),
    });
  };

  const handleDisconnect = () => {
    onActionError(null);
    onActionNotice(null);
    disconnectMut.mutate(connectorId, {
      onError: (err) => onActionError(err?.message || `Failed to disconnect ${name}.`),
      onSuccess: () => onActionNotice(`${name} disconnected.`),
    });
  };

  return (
    <div className="bg-white rounded-xl border border-gray-200 p-5 flex flex-col gap-4 hover:shadow-sm transition-shadow">
      <div className="flex items-center gap-3">
        <span
          className="w-10 h-10 rounded-lg flex items-center justify-center text-white text-sm font-bold shrink-0"
          style={{ backgroundColor: color }}
        >
          {name[0]}
        </span>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-gray-800">{name}</h3>
          <p className="text-xs text-gray-500">{description}</p>
        </div>
        <span
          className={`px-2.5 py-0.5 rounded-full text-[11px] font-medium ${STATUS_PILL[status]}`}
        >
          {STATUS_LABEL[status]}
        </span>
      </div>

      <div className="rounded-lg bg-gray-50 border border-gray-100 p-3">
        <div className="grid grid-cols-2 text-xs text-gray-500 gap-y-1">
          <span>Last sync</span>
          <span className="text-right text-gray-700">{lastSync}</span>
          <span>Items synced</span>
          <span className="text-right text-gray-700">{Number(itemsSynced || 0).toLocaleString()}</span>
          {teamName && (
            <>
              <span>Workspace</span>
              <span className="text-right text-gray-700">{teamName}</span>
            </>
          )}
        </div>
        {syncQueuedAt && (
          <div className="mt-2 inline-flex items-center gap-2 rounded-full bg-blue-50 px-2.5 py-1 text-[11px] text-blue-700">
            <span className="inline-block h-1.5 w-1.5 rounded-full bg-blue-500" />
            Sync queued {syncQueuedAt}
          </div>
        )}
        {message && (
          <p className="text-[11px] text-gray-500 mt-2">{message}</p>
        )}
        {scope && (
          <p className="text-[11px] text-gray-400 mt-2">
            Slack scopes: {scope}
          </p>
        )}
        {status === "disconnected" && availability === "available" && (
          <p className="text-[11px] text-gray-500 mt-2">
            Connect Slack to start ingesting messages, threads, and source-backed pricing or roadmap facts.
          </p>
        )}
        {status === "coming_soon" && (
          <p className="text-[11px] text-gray-500 mt-2">
            Backend support for this connector is intentionally deferred until the Slack path is stable.
          </p>
        )}
      </div>

      <div className="flex flex-wrap gap-2 mt-auto">
        {status === "coming_soon" ? (
          <button
            type="button"
            disabled
            className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-400 cursor-not-allowed"
          >
            Coming soon
          </button>
        ) : canConnect ? (
          <a
            href={installHref}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-brand-600 text-white hover:bg-brand-700 transition-colors"
          >
            Connect Slack
          </a>
        ) : (
          <button
            type="button"
            disabled
            className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-400 cursor-not-allowed"
          >
            {disabled ? "Demo mode" : workspaceId ? "Already connected" : "Select workspace"}
          </button>
        )}

        <button
          type="button"
          disabled={!canSync || syncMut.isPending}
          onClick={handleSync}
          className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-600 hover:bg-gray-50 disabled:text-gray-400 disabled:cursor-not-allowed transition-colors"
        >
          {syncMut.isPending && syncMut.variables === connectorId ? "Syncing..." : "Sync now"}
        </button>

        <button
          type="button"
          disabled={!canDisconnect || disconnectMut.isPending}
          onClick={handleDisconnect}
          className="px-3 py-1.5 text-xs font-medium rounded-lg border border-red-200 text-red-600 hover:bg-red-50 disabled:text-gray-400 disabled:border-gray-200 disabled:cursor-not-allowed transition-colors"
        >
          {disconnectMut.isPending && disconnectMut.variables === connectorId
            ? "Disconnecting..."
            : "Disconnect"}
        </button>
      </div>
    </div>
  );
}
