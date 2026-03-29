/**
 * React Query hooks for Context Engine API.
 *
 * Each hook tries the real backend first. If the fetch fails (backend
 * down, network error), it falls back to mock fixtures so the UI stays
 * usable during frontend-only development.
 */

import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import {
  dashboardStats,
  recentActivity,
  staleAlerts,
  connectors as mockConnectors,
  graphNodes as mockGraphNodes,
  graphEdges as mockGraphEdges,
  modelFixtures,
  queryExamples as mockQueryExamples,
} from "../fixtures/mockData";

// ── Helpers ────────────────────────────────────────────────────

/**
 * Wrap an API call so it falls back to mock data on network failure.
 *
 * `fallbackStatuses` is for endpoints that are intentionally stubbed out
 * in the backend for the current phase (for example 404/501 during Phase 1).
 */
function withFallback(apiFn, mockData, { fallbackStatuses = [] } = {}) {
  return async () => {
    try {
      return await apiFn();
    } catch (err) {
      if (err.status && !fallbackStatuses.includes(err.status)) {
        throw err; // real API error (4xx/5xx) — propagate
      }
      if (err.status) {
        console.warn(`[api] endpoint unavailable (${err.status}), using mock data`);
        return mockData;
      }
      console.warn("[api] backend unreachable, using mock data");
      return mockData;
    }
  };
}

const LS_KEY = "ce:selectedWorkspaceId";
const CONNECTOR_CATALOG = {
  slack: {
    type: "slack",
    name: "Slack",
    description: "Channels, DMs, and thread history",
    color: "#4A154B",
    availability: "available",
  },
  notion: {
    type: "notion",
    name: "Notion",
    description: "Wikis, docs, and linked databases",
    color: "#111111",
    availability: "coming_soon",
  },
  gdrive: {
    type: "gdrive",
    name: "Google Drive",
    description: "Docs, Sheets, Slides, and folder content",
    color: "#0F9D58",
    availability: "coming_soon",
  },
  gong: {
    type: "gong",
    name: "Gong",
    description: "Calls, transcripts, and customer conversations",
    color: "#7C3AED",
    availability: "coming_soon",
  },
};

/**
 * Resolve the workspace ID to use for API calls.
 *
 * Priority:
 * 1. localStorage selection (set by workspace switcher)
 * 2. First workspace from the backend
 *
 * Returns null if no workspaces exist.
 */
async function getWorkspaceId() {
  const workspaces = await api.get("/workspaces");
  if (workspaces.length === 0) return null;

  const stored = localStorage.getItem(LS_KEY);
  if (stored && workspaces.some((w) => w.id === stored)) return stored;

  return workspaces[0].id;
}

// ── Workspaces ────────────────────────────────────────────────

export function useWorkspaces() {
  return useQuery({
    queryKey: ["workspaces"],
    queryFn: () => api.get("/workspaces"),
    retry: 1,
  });
}

export function useCreateWorkspace() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => api.post("/workspaces", body),
    onSuccess: (newWorkspace) => {
      // Auto-select the newly created workspace
      if (newWorkspace?.id) {
        localStorage.setItem(LS_KEY, newWorkspace.id);
      }
      qc.invalidateQueries({ queryKey: ["workspaces"] });
    },
  });
}

// ── Dashboard ──────────────────────────────────────────────────

const MOCK_DASHBOARD = {
  stats: dashboardStats,
  activity: recentActivity,
  alerts: staleAlerts,
};

export function useDashboard() {
  return useQuery({
    queryKey: ["dashboard"],
    queryFn: withFallback(async () => {
      const wsId = await getWorkspaceId();
      if (!wsId) throw new Error("no workspace");

      const models = await api.get(`/models?workspace_id=${wsId}`);

      // Fetch each model's detail to get actual component counts
      const details = await Promise.all(
        models.map((m) => api.get(`/models/${m.id}`)),
      );
      const totalComponents = details.reduce(
        (n, d) => n + (d.components?.length ?? 0),
        0,
      );

      return {
        stats: [
          { label: "Sources", value: 0, icon: "database", delta: "—" },
          { label: "Models", value: models.length, icon: "cube", delta: "—" },
          { label: "Components", value: totalComponents, icon: "puzzle", delta: "—" },
          { label: "Relationships", value: 0, icon: "link", delta: "—" },
        ],
        activity: recentActivity, // no backend endpoint yet
        alerts: staleAlerts, // no backend endpoint yet
      };
    }, MOCK_DASHBOARD),
  });
}

// ── Models (list) ──────────────────────────────────────────────

export function useModels() {
  return useQuery({
    queryKey: ["models"],
    queryFn: withFallback(async () => {
      const wsId = await getWorkspaceId();
      if (!wsId) return [];
      return api.get(`/models?workspace_id=${wsId}`);
    }, []),
  });
}

// ── Model detail ───────────────────────────────────────────────

export function useModel(modelId) {
  return useQuery({
    queryKey: ["model", modelId],
    queryFn: withFallback(
      () => api.get(`/models/${modelId}`),
      modelFixtures[modelId] ?? {
        name: `Model: ${modelId}`,
        description: "No mock data available for this model ID.",
        lastUpdated: "—",
        components: [],
      },
    ),
    enabled: !!modelId,
  });
}

// ── Connectors ─────────────────────────────────────────────────

export function useConnectors() {
  const query = useQuery({
    queryKey: ["connectors"],
    queryFn: withFallback(
      async () => {
        const wsId = await getWorkspaceId();
        if (!wsId) return [];
        return api.get(`/connectors?workspace_id=${wsId}`);
      },
      mockConnectors,
      { fallbackStatuses: [404, 501] },
    ),
  });
  return {
    ...query,
    data: normalizeConnectors(query.data),
    isMock: query.data === mockConnectors,
  };
}

// ── Knowledge Graph ────────────────────────────────────────────

const MOCK_GRAPH = { nodes: mockGraphNodes, edges: mockGraphEdges };

export function useKnowledgeGraph() {
  const query = useQuery({
    queryKey: ["knowledge-graph"],
    queryFn: withFallback(
      () => api.get("/graph"),
      MOCK_GRAPH,
      { fallbackStatuses: [404, 501] },
    ),
  });
  return { ...query, isMock: query.data === MOCK_GRAPH };
}

// ── Context Query ─────────────────────────────────────────────

const MOCK_QUERY_RESPONSE = mockQueryExamples;

/**
 * Submit a natural-language question to the Context API.
 *
 * Fully mock-backed for now — the backend query endpoint does not exist yet.
 * When the backend is ready, replace the mock with:
 *   api.post("/query", { question, workspace_id })
 */
export function useContextQuery() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (question) => {
      try {
        const wsId = await getWorkspaceId();
        return await api.post("/query", { question, workspace_id: wsId });
      } catch (err) {
        // Only fall back to mock on network errors (backend unreachable).
        // Real server errors (4xx/5xx) have a status — let them propagate.
        if (err.status) throw err;

        // Simulate latency then return a mock answer that best matches the question
        await new Promise((r) => setTimeout(r, 800));
        const q = question.toLowerCase();
        const match = MOCK_QUERY_RESPONSE.find((m) =>
          m.question.toLowerCase().split(" ").some((w) => w.length > 3 && q.includes(w)),
        );
        return {
          ...(match ?? MOCK_QUERY_RESPONSE[0]),
          question,
          answeredAt: "just now",
          _isMock: true,
        };
      }
    },
  });
}

// ── Relationships (per model) ──────────────────────────────────

export function useModelRelationships(modelId) {
  return useQuery({
    queryKey: ["model-relationships", modelId],
    queryFn: withFallback(
      () => api.get(`/models/${modelId}/relationships`),
      [],
    ),
    enabled: !!modelId,
  });
}

// ── Mutations ──────────────────────────────────────────────────

export function useCreateModel() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (body) => {
      const wsId = await getWorkspaceId();
      return api.post("/models", { workspace_id: wsId, ...body });
    },
    onSuccess: () => qc.invalidateQueries({ queryKey: ["models"] }),
  });
}

export function useCreateComponent(modelId) {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => api.post(`/models/${modelId}/components`, body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["model", modelId] }),
  });
}

export function useUpdateComponent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ componentId, ...body }) => api.patch(`/components/${componentId}`, body),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["model"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useDeleteComponent() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (componentId) => api.delete(`/components/${componentId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["model"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useCreateRelationship() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (body) => api.post("/relationships", body),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["model-relationships"] }),
  });
}

export function useSyncConnector() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectorId) => api.post(`/connectors/${connectorId}/sync`, {}),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connectors"] }),
  });
}

export function useDisconnectConnector() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectorId) => api.delete(`/connectors/${connectorId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connectors"] }),
  });
}

function normalizeConnectors(data) {
  if (!Array.isArray(data)) return [];

  const isMockShape = data.every((item) => item && "lastSync" in item);
  if (isMockShape) {
    return data.map((item) => ({
      ...item,
      type: item.id,
      connectorId: null,
      availability: item.id === "slack" ? "available" : "coming_soon",
      isInstalled: item.status === "connected" || item.status === "warning" || item.status === "error",
      status: item.id === "slack" ? item.status : "coming_soon",
    }));
  }

  const recordsByType = new Map(
    data
      .filter((item) => item?.connector_type)
      .map((item) => [item.connector_type, item]),
  );

  return Object.values(CONNECTOR_CATALOG).map((catalogItem) => {
    const record = recordsByType.get(catalogItem.type);
    if (!record) {
      return {
        ...catalogItem,
        id: catalogItem.type,
        connectorId: null,
        status:
          catalogItem.availability === "available" ? "disconnected" : "coming_soon",
        isInstalled: false,
        lastSync: "Never",
        itemsSynced: 0,
        message:
          catalogItem.availability === "available"
            ? "Not connected yet."
            : "Planned after the Slack reference connector ships.",
      };
    }

    return {
      ...catalogItem,
      id: record.id,
      connectorId: record.id,
      status: record.status,
      isInstalled: record.status !== "disconnected",
      lastSync: formatConnectorDate(record.last_sync_at),
      itemsSynced: extractConnectorCount(record.config),
      message: record.config?.message ?? null,
      teamName: record.config?.team_name ?? null,
      teamId: record.config?.team_id ?? null,
      scope: record.config?.scope ?? null,
      syncQueuedAt: formatConnectorDate(record.config?.sync_queued_at, { fallback: null }),
    };
  });
}

function formatConnectorDate(value, { fallback = "Never" } = {}) {
  if (!value) return fallback;
  try {
    return new Date(value).toLocaleString();
  } catch {
    return value;
  }
}

function extractConnectorCount(config) {
  if (!config || typeof config !== "object") return 0;
  return (
    config.document_count ??
    config.items_synced ??
    config.item_count ??
    0
  );
}
