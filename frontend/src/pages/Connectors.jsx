import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
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

const PROVIDER_PILL = {
  native: "bg-gray-100 text-gray-700",
  dlt: "bg-sky-100 text-sky-700",
  unstructured: "bg-orange-100 text-orange-700",
  official_api: "bg-indigo-100 text-indigo-700",
};

const OAUTH_POLL_INTERVAL_MS = 1500;

function formatDocumentCount(count) {
  const total = Number(count || 0);
  return `${total.toLocaleString()} source document${total === 1 ? "" : "s"}`;
}

export default function Connectors() {
  const { data, isMock, ...query } = useConnectors();
  const workspaces = useWorkspaces();
  const { selectedId } = useWorkspaceSelection();
  const syncMut = useSyncConnector();
  const disconnectMut = useDisconnectConnector();
  const [actionError, setActionError] = useState(null);
  const [actionNotice, setActionNotice] = useState(null);
  const [oauthFlow, setOauthFlow] = useState(null);

  const workspaceId = useMemo(
    () => resolveWorkspaceId(workspaces.data, selectedId),
    [workspaces.data, selectedId],
  );

  const list = data ?? [];
  const slackConnector = list.find((item) => item.type === "slack") ?? null;

  useEffect(() => {
    if (!oauthFlow || isMock) return undefined;

    let cancelled = false;

    const finishOAuthFlow = (slack, startedStatus) => {
      setOauthFlow(null);

      if (slack?.status === "connected") {
        const teamSuffix = slack.teamName ? ` to ${slack.teamName}` : "";
        setActionError(null);
        setActionNotice(
          startedStatus === "disconnected"
            ? `Slack connected${teamSuffix}.`
            : `Slack OAuth finished${teamSuffix}. Connector state refreshed.`,
        );
        return;
      }

      if (slack?.status === "error") {
        setActionNotice(null);
        setActionError(
          "Slack OAuth finished, but the connector is still in an error state. Refresh OAuth or check the backend logs.",
        );
        return;
      }

      setActionNotice(null);
      setActionError("Slack OAuth window closed before the connector status updated.");
    };

    const tick = async () => {
      const result = await query.refetch();
      if (cancelled) return;

      if (result.isError) {
        if (oauthFlow.popup?.closed) {
          setOauthFlow(null);
          setActionNotice(null);
          setActionError("Failed to refresh connector state after Slack OAuth.");
        }
        return;
      }

      const nextList = result.data ?? [];
      const nextSlack = nextList.find((item) => item.type === "slack") ?? null;
      const popupClosed = oauthFlow.popup?.closed ?? true;

      if (!popupClosed && nextSlack?.status === "connected" && oauthFlow.startedStatus === "disconnected") {
        oauthFlow.popup.close?.();
        finishOAuthFlow(nextSlack, oauthFlow.startedStatus);
        return;
      }

      if (popupClosed) {
        finishOAuthFlow(nextSlack, oauthFlow.startedStatus);
      }
    };

    const timer = window.setInterval(() => {
      void tick();
    }, OAUTH_POLL_INTERVAL_MS);

    return () => {
      cancelled = true;
      window.clearInterval(timer);
    };
  }, [isMock, oauthFlow, query.refetch]);

  const startSlackOAuth = (installHref, currentStatus) => {
    setActionError(null);
    setActionNotice(null);

    const popup = window.open(
      installHref,
      "ce-slack-oauth",
      "popup=yes,width=640,height=820",
    );

    if (!popup) {
      window.location.assign(installHref);
      return;
    }

    popup.focus?.();
    setOauthFlow({
      popup,
      startedStatus: currentStatus,
    });
    setActionNotice(
      currentStatus === "disconnected"
        ? "Slack OAuth opened in a new window. Finish there to connect the workspace."
        : "Slack reconnect opened in a new window. Finish there to refresh credentials.",
    );
  };

  if (query.isLoading || query.isError) {
    return (
      <div className="max-w-5xl mx-auto">
        <StatusView query={{ data, ...query }} empty="No connectors configured." />
      </div>
    );
  }

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
      {slackConnector && (
        <SlackSummaryBanner
          connector={slackConnector}
          isDemo={isMock}
          oauthPending={!!oauthFlow}
          workspaceId={workspaceId}
          onStartOAuth={startSlackOAuth}
        />
      )}

      {list.length === 0 ? (
        <StatusView query={{ data: list, isLoading: false, isError: false }} empty="No connectors configured." />
      ) : (
        <div className="grid sm:grid-cols-2 gap-5">
          {list.map((connector) => (
            <ConnectorCard
              key={connector.type}
              connector={connector}
              isDemo={isMock}
              oauthPending={!!oauthFlow}
              workspaceId={workspaceId}
              syncMut={syncMut}
              disconnectMut={disconnectMut}
              onActionError={setActionError}
              onActionNotice={setActionNotice}
              onStartOAuth={startSlackOAuth}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function ConnectorCard({
  connector,
  isDemo,
  oauthPending,
  workspaceId,
  syncMut,
  disconnectMut,
  onActionError,
  onActionNotice,
  onStartOAuth,
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
    provider,
    providerLabel,
    providerNote,
  } = connector;

  const canConnect = !isDemo && !oauthPending && availability === "available" && status === "disconnected" && !!workspaceId;
  const canReconnect =
    !isDemo &&
    !oauthPending &&
    availability === "available" &&
    !!workspaceId &&
    (status === "connected" || status === "error");
  const canSync = !isDemo && !oauthPending && !!connectorId && (status === "connected" || status === "error");
  const canDisconnect = !isDemo && !oauthPending && !!connectorId && (status === "connected" || status === "error");
  const installHref = workspaceId
    ? `/api/connectors/${type}/install?workspace_id=${workspaceId}`
    : null;

  const handleSync = () => {
    onActionError(null);
    onActionNotice(null);
    syncMut.mutate(connectorId, {
      onError: (err) => onActionError(err?.message || `Failed to sync ${name}.`),
      onSuccess: (result) => onActionNotice(result?.message || `${name} sync completed.`),
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
          <div className="flex items-center gap-2">
            <h3 className="text-sm font-semibold text-gray-800">{name}</h3>
            {providerLabel && (
              <span
                className={`px-2 py-0.5 rounded-full text-[10px] font-medium ${PROVIDER_PILL[provider] ?? PROVIDER_PILL.native}`}
              >
                {providerLabel}
              </span>
            )}
          </div>
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
        {providerNote && (
          <p className="text-[11px] text-gray-400 mt-2">
            Connector path: {providerNote}
          </p>
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
        {status === "error" && (
          <p className="text-[11px] text-red-600 mt-2">
            Slack needs attention. Reconnect the workspace or retry sync after checking OAuth and connector health.
          </p>
        )}
        {status === "connected" && teamName && (
          <p className="text-[11px] text-emerald-700 mt-2">
            Connected and ready for ingestion.
          </p>
        )}
        {status === "connected" && itemsSynced > 0 && (
          <div className="mt-2">
            <p className="text-[11px] text-emerald-700">
              {formatDocumentCount(itemsSynced)} available for extraction and query.
            </p>
            <Link to="/sources" className="inline-flex mt-1 text-[11px] font-medium text-emerald-700 underline">
              Inspect stored documents
            </Link>
          </div>
        )}
        {status === "connected" && itemsSynced === 0 && !syncQueuedAt && (
          <p className="text-[11px] text-gray-500 mt-2">
            OAuth is complete. Run a sync to start storing Slack history in the database.
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
            onClick={(event) => {
              event.preventDefault();
              onStartOAuth(installHref, status);
            }}
            className="px-3 py-1.5 text-xs font-medium rounded-lg bg-brand-600 text-white hover:bg-brand-700 transition-colors"
          >
            Connect Slack
          </a>
        ) : canReconnect ? (
          <a
            href={installHref}
            onClick={(event) => {
              event.preventDefault();
              onStartOAuth(installHref, status);
            }}
            className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-700 hover:bg-gray-50 transition-colors"
          >
            Reconnect Slack
          </a>
        ) : (
          <button
            type="button"
            disabled
            className="px-3 py-1.5 text-xs font-medium rounded-lg border border-gray-200 text-gray-400 cursor-not-allowed"
          >
            {isDemo
              ? "Demo mode"
              : oauthPending
                ? "Waiting for Slack..."
                : workspaceId
                  ? "Already connected"
                  : "Select workspace"}
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

function SlackSummaryBanner({ connector, isDemo, oauthPending, workspaceId, onStartOAuth }) {
  const reconnectHref = workspaceId
    ? `/api/connectors/slack/install?workspace_id=${workspaceId}`
    : null;

  if (connector.status === "connected") {
    return (
      <div className="rounded-xl border border-emerald-200 bg-emerald-50 p-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-emerald-800">
            Slack is connected{connector.teamName ? ` to ${connector.teamName}` : ""}.
          </p>
          <p className="text-xs text-emerald-700 mt-1">
            {connector.syncQueuedAt
              ? `A sync is queued for ${connector.syncQueuedAt}.`
              : connector.itemsSynced > 0
                ? `${formatDocumentCount(connector.itemsSynced)} available for extraction and query.`
                : `Last completed sync: ${connector.lastSync}. Run a sync to store Slack history.`}
          </p>
          {connector.itemsSynced > 0 && (
            <Link to="/sources" className="inline-flex mt-3 text-xs font-medium text-emerald-800 underline">
              Inspect stored documents
            </Link>
          )}
        </div>
        {!isDemo && !oauthPending && reconnectHref && (
          <a
            href={reconnectHref}
            onClick={(event) => {
              event.preventDefault();
              onStartOAuth(reconnectHref, connector.status);
            }}
            className="shrink-0 px-3 py-1.5 text-xs font-medium rounded-lg border border-emerald-200 text-emerald-800 hover:bg-white/70 transition-colors"
          >
            Refresh OAuth
          </a>
        )}
      </div>
    );
  }

  if (connector.status === "error") {
    return (
      <div className="rounded-xl border border-red-200 bg-red-50 p-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-red-800">Slack needs attention.</p>
          <p className="text-xs text-red-700 mt-1">
            Reconnect the workspace to refresh credentials, then run another sync.
          </p>
        </div>
        {!isDemo && !oauthPending && reconnectHref && (
          <a
            href={reconnectHref}
            onClick={(event) => {
              event.preventDefault();
              onStartOAuth(reconnectHref, connector.status);
            }}
            className="shrink-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
          >
            Refresh OAuth
          </a>
        )}
      </div>
    );
  }

  if (connector.status === "disconnected") {
    return (
      <div className="rounded-xl border border-amber-200 bg-amber-50 p-4 flex items-start justify-between gap-4">
        <div>
          <p className="text-sm font-medium text-amber-800">Slack is not connected yet.</p>
          <p className="text-xs text-amber-700 mt-1">
            Phase 2 starts with Slack so you can ingest channel history before adding other sources.
          </p>
        </div>
        {!isDemo && !oauthPending && reconnectHref && (
          <a
            href={reconnectHref}
            onClick={(event) => {
              event.preventDefault();
              onStartOAuth(reconnectHref, connector.status);
            }}
            className="shrink-0 px-3 py-1.5 text-xs font-medium rounded-lg bg-brand-600 text-white hover:bg-brand-700 transition-colors"
          >
            Start Slack OAuth
          </a>
        )}
      </div>
    );
  }

  return null;
}
