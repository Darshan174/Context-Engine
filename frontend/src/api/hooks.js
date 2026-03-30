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
  sourceDocuments as mockSourceDocuments,
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
    provider: "native",
    providerLabel: "Built in",
    providerNote: "Slack stays native because OAuth, thread expansion, and real-time events are product-critical.",
  },
  notion: {
    type: "notion",
    name: "Notion",
    description: "Wikis, docs, and linked databases",
    color: "#111111",
    availability: "coming_soon",
    provider: "dlt",
    providerLabel: "dlt",
    providerNote: "Planned to use a dlt verified source instead of hand-building the full Notion sync stack.",
  },
  gdrive: {
    type: "gdrive",
    name: "Google Drive",
    description: "Docs, Sheets, Slides, and folder content",
    color: "#0F9D58",
    availability: "coming_soon",
    provider: "unstructured",
    providerLabel: "Unstructured",
    providerNote: "Planned to use Unstructured for Drive ingestion and document extraction.",
  },
  gong: {
    type: "gong",
    name: "Gong",
    description: "Calls, transcripts, and customer conversations",
    color: "#7C3AED",
    availability: "coming_soon",
    provider: "official_api",
    providerLabel: "Official API",
    providerNote: "Likely to stay on the Gong API directly because transcript semantics matter more than generic ETL.",
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

      const [models, connectors] = await Promise.all([
        api.get(`/models?workspace_id=${wsId}`),
        api.get(`/connectors?workspace_id=${wsId}`),
      ]);

      // Fetch each model's detail to get actual component counts
      const details = await Promise.all(
        models.map((m) => api.get(`/models/${m.id}`)),
      );
      const relationshipsPerModel = await Promise.all(
        models.map((m) => api.get(`/models/${m.id}/relationships`)),
      );
      const totalComponents = details.reduce(
        (n, d) => n + (d.components?.length ?? 0),
        0,
      );
      const relationshipCount = new Set(
        relationshipsPerModel.flatMap((rels) => (rels ?? []).map((rel) => rel.id)),
      ).size;
      const sourceDocumentCount = connectors.reduce(
        (n, connector) => n + extractConnectorCount(connector.config),
        0,
      );
      const activeConnectorCount = connectors.filter(
        (connector) => connector.status === "connected" || connector.status === "error",
      ).length;
      const sourceDelta =
        activeConnectorCount > 0
          ? `${activeConnectorCount} connector${activeConnectorCount === 1 ? "" : "s"} active`
          : "No connectors active";

      return {
        stats: [
          { label: "Sources", value: sourceDocumentCount, icon: "database", delta: sourceDelta },
          { label: "Models", value: models.length, icon: "cube", delta: "—" },
          { label: "Components", value: totalComponents, icon: "puzzle", delta: "—" },
          { label: "Relationships", value: relationshipCount, icon: "link", delta: "—" },
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
  const refetch = async () => {
    const result = await query.refetch();
    return {
      ...result,
      data: normalizeConnectors(result.data),
      isMock: result.data === mockConnectors,
    };
  };
  return {
    ...query,
    data: normalizeConnectors(query.data),
    isMock: query.data === mockConnectors,
    refetch,
  };
}

// ── Source Documents ────────────────────────────────────────────

export function useSourceDocuments(filters = {}) {
  const { connector = "all", processed = "all", search = "" } = filters;
  const query = useQuery({
    queryKey: ["source-documents", connector, processed, search],
    queryFn: async () => {
      const wsId = await getWorkspaceId();
      if (!wsId) {
        return { items: [], isMock: false };
      }

      const params = new URLSearchParams({ workspace_id: wsId });
      if (connector !== "all") params.set("connector_type", connector);
      if (processed !== "all") params.set("processed", processed);
      if (search.trim()) params.set("q", search.trim());

      try {
        const data = await api.get(`/source-documents?${params.toString()}`);
        return {
          items: normalizeSourceDocuments(data),
          isMock: false,
        };
      } catch (err) {
        if (err.status && ![404, 501].includes(err.status)) {
          throw err;
        }
        if (err.status) {
          console.warn(`[api] source-documents unavailable (${err.status}), using mock data`);
        } else {
          console.warn("[api] backend unreachable for source-documents, using mock data");
        }
        return {
          items: filterMockSourceDocuments(mockSourceDocuments, { connector, processed, search }),
          isMock: true,
        };
      }
    },
  });

  return {
    ...query,
    data: query.data?.items ?? [],
    isMock: query.data?.isMock ?? false,
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
    return data.map((item) => {
      const type = item.type ?? item.id;
      const catalogItem = CONNECTOR_CATALOG[type] ?? {};
      return {
        ...catalogItem,
        ...item,
        type,
        connectorId: null,
        availability: type === "slack" ? "available" : "coming_soon",
        isInstalled: item.status === "connected" || item.status === "warning" || item.status === "error",
        status: type === "slack" ? item.status : "coming_soon",
        provider: item.provider ?? catalogItem.provider,
        providerLabel: item.providerLabel ?? catalogItem.providerLabel,
        providerNote: item.providerNote ?? catalogItem.providerNote,
      };
    });
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
      provider: record.provider ?? catalogItem.provider,
      providerLabel: record.provider_label ?? catalogItem.providerLabel,
      providerNote: record.provider_note ?? catalogItem.providerNote,
    };
  });
}

function normalizeSourceDocuments(data) {
  if (!Array.isArray(data)) return [];

  return data.map((item) => {
    const connectorType = item.connectorType ?? item.connector_type ?? "unknown";
    const metadata = item.metadata ?? item.metadata_json ?? {};
    return {
      id: item.id,
      connectorType,
      externalId: item.externalId ?? item.external_id,
      author: item.author ?? "Unknown",
      content: item.content ?? "",
      preview: item.content ?? "",
      sourceUrl: item.sourceUrl ?? item.source_url ?? null,
      createdAtSource: item.createdAtSource ?? item.created_at_source ?? null,
      ingestedAt: item.ingestedAt ?? item.ingested_at ?? null,
      processedAt: item.processedAt ?? item.processed_at ?? null,
      processed: Boolean(item.processedAt ?? item.processed_at),
      location:
        metadata.location ??
        metadata.channel_name ??
        metadata.page_id ??
        item.location ??
        null,
      metadata,
    };
  });
}

function filterMockSourceDocuments(data, filters) {
  const items = normalizeSourceDocuments(data);
  const connector = filters.connector ?? "all";
  const processed = filters.processed ?? "all";
  const search = (filters.search ?? "").trim().toLowerCase();

  return items.filter((item) => {
    const matchesConnector = connector === "all" || item.connectorType === connector;
    const matchesProcessed =
      processed === "all" ||
      (processed === "processed" && item.processed) ||
      (processed === "unprocessed" && !item.processed);
    const haystack = [
      item.author,
      item.content,
      item.location,
      item.externalId,
      item.connectorType,
    ]
      .filter(Boolean)
      .join(" ")
      .toLowerCase();
    const matchesSearch = !search || haystack.includes(search);
    return matchesConnector && matchesProcessed && matchesSearch;
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
