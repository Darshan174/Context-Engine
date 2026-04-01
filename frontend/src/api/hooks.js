/**
 * React Query hooks for Context Engine API.
 *
 * Each hook tries the real backend first. If the fetch fails (backend
 * down, network error), it falls back to mock fixtures so the UI stays
 * usable during frontend-only development.
 */

import { useInfiniteQuery, useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { api } from "./client";
import {
  dashboardStats,
  evalCasesByDomain as mockEvalCasesByDomain,
  evalSummary as mockEvalSummary,
  recentActivity,
  staleAlerts,
  connectors as mockConnectors,
  reviewQueue as mockReviewQueue,
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
    availability: "available",
    provider: "dlt",
    providerLabel: "dlt",
    providerNote: "Powered by a dlt-backed connector path so we can reuse the substrate but keep our own storage and extraction pipeline.",
  },
  zoom: {
    type: "zoom",
    name: "Zoom",
    description: "Meeting transcripts and recording metadata",
    color: "#0B5CFF",
    availability: "available",
    provider: "official_api",
    providerLabel: "Official API",
    providerNote: "Transcript-first Zoom ingestion keeps the connector focused on high-signal meeting context instead of media processing.",
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

export function useConnectorSyncStatus(connectorId, { enabled = true } = {}) {
  return useQuery({
    queryKey: ["connector-sync-status", connectorId],
    enabled: enabled && !!connectorId,
    retry: false,
    refetchInterval: (query) => {
      const status = query.state.data?.status;
      return status === "pending" || status === "running" ? 2000 : false;
    },
    queryFn: async () => {
      try {
        const data = await api.get(`/connectors/${connectorId}/sync-status`);
        return normalizeSyncJob(data);
      } catch (err) {
        if (err.status && ![404, 501].includes(err.status)) {
          throw err;
        }
        return null;
      }
    },
  });
}

export function useConnectorSyncJobs(connectorId, { enabled = true } = {}) {
  return useQuery({
    queryKey: ["connector-sync-jobs", connectorId],
    enabled: enabled && !!connectorId,
    retry: false,
    refetchInterval: (query) => {
      const jobs = query.state.data ?? [];
      const hasActive = jobs.some((job) => job.status === "pending" || job.status === "running");
      return hasActive ? 2000 : false;
    },
    queryFn: async () => {
      try {
        const data = await api.get(`/connectors/${connectorId}/sync-jobs`);
        return Array.isArray(data) ? data.map(normalizeSyncJob) : [];
      } catch (err) {
        if (err.status && ![404, 501].includes(err.status)) {
          throw err;
        }
        return [];
      }
    },
  });
}

// ── Source Documents ────────────────────────────────────────────

export function useSourceDocuments(filters = {}) {
  const { connector = "all", processed = "all", search = "" } = filters;
  const query = useInfiniteQuery({
    queryKey: ["source-documents", connector, processed, search],
    initialPageParam: null,
    queryFn: async ({ pageParam }) => {
      const wsId = await getWorkspaceId();
      if (!wsId) {
        return {
          items: [],
          total: 0,
          hasMore: false,
          nextCursor: null,
          isMock: false,
        };
      }

      const params = new URLSearchParams({ workspace_id: wsId });
      if (connector !== "all") params.set("connector_type", connector);
      if (processed !== "all") params.set("processed", String(processed === "processed"));
      if (pageParam) params.set("cursor", pageParam);
      params.set("limit", "25");

      try {
        const data = await api.get(`/source-documents?${params.toString()}`);
        const items = applySourceSearchFilter(normalizeSourceDocuments(data.items ?? []), search);
        return {
          items,
          total: data.total ?? items.length,
          hasMore: Boolean(data.has_more),
          nextCursor: data.next_cursor ?? null,
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
        if (pageParam) {
          return {
            items: [],
            total: 0,
            hasMore: false,
            nextCursor: null,
            isMock: true,
          };
        }
        const items = filterMockSourceDocuments(mockSourceDocuments, { connector, processed, search });
        return {
          items,
          total: items.length,
          hasMore: false,
          nextCursor: null,
          isMock: true,
        };
      }
    },
    getNextPageParam: (lastPage) => (lastPage.hasMore ? lastPage.nextCursor : undefined),
  });

  const pages = query.data?.pages ?? [];
  const data = pages.flatMap((page) => page.items);
  const firstPage = pages[0];

  return {
    ...query,
    data,
    total: search.trim() ? data.length : (firstPage?.total ?? data.length),
    hasMore: query.hasNextPage ?? false,
    isMock: firstPage?.isMock ?? false,
  };
}

export function useSourceDocument(documentId) {
  return useQuery({
    queryKey: ["source-document", documentId],
    enabled: !!documentId,
    queryFn: async () => {
      const wsId = await getWorkspaceId();
      if (!wsId || !documentId) return null;

      try {
        const data = await api.get(`/source-documents/${documentId}?workspace_id=${wsId}`);
        return normalizeSourceDocuments([data])[0] ?? null;
      } catch (err) {
        if (err.status && err.status !== 501) {
          throw err;
        }
        const fallback = normalizeSourceDocuments(mockSourceDocuments).find((doc) => doc.id === documentId);
        return fallback ?? null;
      }
    },
  });
}

export function useSourceDocumentComponents(documentId) {
  return useQuery({
    queryKey: ["source-document-components", documentId],
    enabled: !!documentId,
    queryFn: async () => {
      const wsId = await getWorkspaceId();
      if (!wsId || !documentId) return [];

      try {
        const data = await api.get(`/source-documents/${documentId}/components?workspace_id=${wsId}`);
        return normalizeSourceComponentRefs(data);
      } catch (err) {
        if (err.status && ![404, 501].includes(err.status)) {
          throw err;
        }
        return buildMockSourceComponentRefs(documentId);
      }
    },
  });
}

export function useComponentSources(componentId, { enabled = true } = {}) {
  return useQuery({
    queryKey: ["component-sources", componentId],
    enabled: enabled && !!componentId,
    queryFn: async () => {
      if (!componentId) return [];

      try {
        const data = await api.get(`/components/${componentId}/sources`);
        return normalizeComponentSourceRefs(data);
      } catch (err) {
        if (err.status && ![404, 501].includes(err.status)) {
          throw err;
        }
        return buildMockComponentSources(componentId);
      }
    },
  });
}

export function useSourceDocumentReviewItems(documentId) {
  return useQuery({
    queryKey: ["source-document-review-items", documentId],
    enabled: !!documentId,
    queryFn: async () => {
      const wsId = await getWorkspaceId();
      if (!wsId || !documentId) return [];

      try {
        const params = new URLSearchParams({
          workspace_id: wsId,
          source_document_id: documentId,
        });
        const data = await api.get(`/review-items?${params.toString()}`);
        return normalizeReviewItems(data);
      } catch (err) {
        if (err.status && ![404, 501].includes(err.status)) {
          throw err;
        }
        return buildMockSourceReviewItems(documentId);
      }
    },
  });
}

export function useConnectorProcessingSummary() {
  return useQuery({
    queryKey: ["connector-processing-summary"],
    queryFn: async () => {
      const wsId = await getWorkspaceId();
      if (!wsId) return { items: [], isMock: false };

      try {
        const data = await api.get(`/connectors/processing-summary?workspace_id=${wsId}`);
        return {
          items: normalizeProcessingSummary(data),
          isMock: false,
        };
      } catch (err) {
        if (err.status && ![404, 501].includes(err.status)) {
          throw err;
        }
        return {
          items: buildMockProcessingSummary(mockSourceDocuments),
          isMock: true,
        };
      }
    },
  });
}

export function useReviewQueue(filters = {}) {
  const { status = "all", severity = "all", kind = "all" } = filters;
  const query = useQuery({
    queryKey: ["review-queue", status, severity, kind],
    queryFn: async () => {
      const wsId = await getWorkspaceId();
      if (!wsId) return { items: [], isMock: false };

      const params = new URLSearchParams({ workspace_id: wsId });
      if (status !== "all") params.set("status", status);
      if (severity !== "all") params.set("severity", severity);
      if (kind !== "all") params.set("kind", kind);

      try {
        const data = await api.get(`/review-items?${params.toString()}`);
        return { items: normalizeReviewItems(data), isMock: false };
      } catch (err) {
        if (err.status && ![404, 501].includes(err.status)) {
          throw err;
        }
        return {
          items: filterReviewItems(normalizeReviewItems(mockReviewQueue), { status, severity, kind }),
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

// ── Accuracy / eval summary ──────────────────────────────────

export function useEvalSummary() {
  const query = useQuery({
    queryKey: ["eval-summary"],
    queryFn: async () => {
      const wsId = await getWorkspaceId();
      if (!wsId) return { summary: null, isMock: false };

      try {
        const data = await api.get(`/evals/summary?workspace_id=${wsId}`);
        return { summary: normalizeEvalSummary(data), isMock: false };
      } catch (err) {
        if (err.status && ![400, 404, 422, 501].includes(err.status)) {
          throw err;
        }
        return { summary: normalizeEvalSummary(mockEvalSummary), isMock: true };
      }
    },
  });

  return {
    ...query,
    data: query.data?.summary ?? null,
    isMock: query.data?.isMock ?? false,
  };
}

export function useEvalCases(domain, { enabled = true } = {}) {
  const query = useQuery({
    queryKey: ["eval-cases", domain],
    enabled: enabled && !!domain,
    queryFn: async () => {
      const wsId = await getWorkspaceId();
      if (!wsId || !domain) return { payload: null, isMock: false };

      const params = new URLSearchParams({ workspace_id: wsId, domain });
      try {
        const data = await api.get(`/evals/cases?${params.toString()}`);
        return { payload: normalizeEvalCases(data), isMock: false };
      } catch (err) {
        if (err.status && ![400, 404, 422, 501].includes(err.status)) {
          throw err;
        }
        return {
          payload: normalizeEvalCases(mockEvalCasesByDomain[domain] ?? { selectedDomain: domain, cases: [] }),
          isMock: true,
        };
      }
    },
  });

  return {
    ...query,
    data: query.data?.payload ?? null,
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
  return useMutation({
    mutationFn: async (input) => {
      const request =
        typeof input === "string"
          ? { question: input, maxAgeDays: null, asOf: null }
          : {
              question: input?.question ?? "",
              maxAgeDays: input?.maxAgeDays ?? null,
              asOf: input?.asOf ?? null,
            };
      try {
        const wsId = await getWorkspaceId();
        return await api.post("/query", {
          question: request.question,
          workspace_id: wsId,
          ...(request.maxAgeDays != null ? { max_age_days: request.maxAgeDays } : {}),
          ...(request.asOf ? { as_of: request.asOf } : {}),
        });
      } catch (err) {
        // Only fall back to mock on network errors (backend unreachable).
        // Real server errors (4xx/5xx) have a status — let them propagate.
        if (err.status) throw err;

        // Simulate latency then return a mock answer that best matches the question
        await new Promise((r) => setTimeout(r, 800));
        const q = request.question.toLowerCase();
        const match = MOCK_QUERY_RESPONSE.find((m) =>
          m.question.toLowerCase().split(" ").some((w) => w.length > 3 && q.includes(w)),
        );
        return {
          ...(match ?? MOCK_QUERY_RESPONSE[0]),
          question: request.question,
          answeredAt: "just now",
          ...(request.asOf ? { asOf: request.asOf } : {}),
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
    onSuccess: (_data, connectorId) => {
      qc.invalidateQueries({ queryKey: ["connectors"] });
      qc.invalidateQueries({ queryKey: ["connector-sync-status", connectorId] });
      qc.invalidateQueries({ queryKey: ["connector-sync-jobs", connectorId] });
      qc.invalidateQueries({ queryKey: ["connector-processing-summary"] });
    },
  });
}

export function useDisconnectConnector() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (connectorId) => api.delete(`/connectors/${connectorId}`),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["connectors"] }),
  });
}

export function useApproveReviewItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reviewItemId) => api.post(`/review-items/${reviewItemId}/approve`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["source-document-review-items"] });
      qc.invalidateQueries({ queryKey: ["source-document-components"] });
      qc.invalidateQueries({ queryKey: ["model"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useRejectReviewItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reviewItemId) => api.post(`/review-items/${reviewItemId}/reject`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["source-document-review-items"] });
      qc.invalidateQueries({ queryKey: ["source-document-components"] });
      qc.invalidateQueries({ queryKey: ["model"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useSupersedeReviewItem() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (reviewItemId) => api.post(`/review-items/${reviewItemId}/supersede`, {}),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["review-queue"] });
      qc.invalidateQueries({ queryKey: ["source-document-review-items"] });
      qc.invalidateQueries({ queryKey: ["source-document-components"] });
      qc.invalidateQueries({ queryKey: ["model"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useReprocessSourceDocument() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async (documentId) => {
      const wsId = await getWorkspaceId();
      const job = await api.post(`/source-documents/${documentId}/reprocess?workspace_id=${wsId}`, {});
      return normalizeSyncJob(job);
    },
    onSuccess: (job, documentId) => {
      qc.invalidateQueries({ queryKey: ["source-documents"] });
      qc.invalidateQueries({ queryKey: ["source-document", documentId] });
      qc.invalidateQueries({ queryKey: ["source-document-components", documentId] });
      qc.invalidateQueries({ queryKey: ["source-document-review-items", documentId] });
      qc.invalidateQueries({ queryKey: ["connector-processing-summary"] });
      qc.invalidateQueries({ queryKey: ["connectors"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
      if (job?.connectorId) {
        qc.invalidateQueries({ queryKey: ["connector-sync-status", job.connectorId] });
        qc.invalidateQueries({ queryKey: ["connector-sync-jobs", job.connectorId] });
      }
    },
  });
}

export function useConnectNotion() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ token }) => {
      const wsId = await getWorkspaceId();
      return api.post("/connectors/notion/connect", { workspace_id: wsId, token });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["connectors"] });
      qc.invalidateQueries({ queryKey: ["connector-processing-summary"] });
      qc.invalidateQueries({ queryKey: ["source-documents"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });
}

export function useConnectZoom() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: async ({ token }) => {
      const wsId = await getWorkspaceId();
      return api.post("/connectors/zoom/connect", { workspace_id: wsId, token });
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["connectors"] });
      qc.invalidateQueries({ queryKey: ["connector-processing-summary"] });
      qc.invalidateQueries({ queryKey: ["source-documents"] });
      qc.invalidateQueries({ queryKey: ["dashboard"] });
    },
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
        availability: catalogItem.availability ?? "coming_soon",
        isInstalled: item.status === "connected" || item.status === "warning" || item.status === "error",
        status:
          catalogItem.availability === "available"
            ? item.status
            : "coming_soon",
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
      syncMode: record.config?.sync_mode ?? null,
      syncModeNote: record.config?.sync_mode_note ?? null,
      processedCount: Number(record.config?.processed_count ?? 0),
      totalProcessedCount: Number(record.config?.total_processed_count ?? 0),
      authMode: record.config?.auth_mode ?? null,
      accountId: record.config?.account_id ?? null,
      ingestionMode: record.config?.ingestion_mode ?? null,
      sourceFocus: record.config?.source_focus ?? null,
      lastWebhookEvent: record.config?.last_zoom_webhook_event ?? null,
      lastWebhookReceivedAt: formatConnectorDate(record.config?.last_zoom_webhook_received_at, {
        fallback: null,
      }),
      provider: record.provider ?? catalogItem.provider,
      providerLabel: record.provider_label ?? catalogItem.providerLabel,
      providerNote: record.provider_note ?? catalogItem.providerNote,
    };
  });
}

function normalizeSyncJob(data) {
  if (!data) return null;

  return {
    jobId: data.jobId ?? data.job_id ?? data.id ?? null,
    jobType: data.jobType ?? data.job_type ?? "sync",
    connectorId: data.connectorId ?? data.connector_id ?? null,
    status: data.status ?? "pending",
    startedAt: data.startedAt ?? data.started_at ?? null,
    completedAt: data.completedAt ?? data.completed_at ?? null,
    errorType: data.errorType ?? data.error_type ?? null,
    errorMessage: data.errorMessage ?? data.error_message ?? null,
    createdAt: data.createdAt ?? data.created_at ?? null,
    resultMetadata: data.resultMetadata ?? data.result_metadata ?? {},
  };
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
        metadata.meeting_topic ??
        metadata.team_name ??
        metadata.page_title ??
        metadata.page_id ??
        item.location ??
        null,
      meetingTopic: metadata.meeting_topic ?? item.meetingTopic ?? item.meeting_topic ?? null,
      host: metadata.host ?? item.host ?? null,
      participants: Array.isArray(metadata.participants)
        ? metadata.participants
        : Array.isArray(item.participants)
          ? item.participants
          : [],
      recordingDate: metadata.recording_date ?? item.recordingDate ?? item.recording_date ?? null,
      transcriptTimestamp:
        metadata.transcript_timestamp ??
        item.transcriptTimestamp ??
        item.transcript_timestamp ??
        null,
      sourceType: metadata.source_type ?? item.sourceType ?? item.source_type ?? null,
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

function normalizeProcessingSummary(data) {
  if (!Array.isArray(data)) return [];
  return data.map((item) => ({
    connectorId: item.connector_id,
    connectorType: item.connector_type,
    status: item.status,
    totalDocuments: Number(item.total_documents ?? 0),
    processedDocuments: Number(item.processed_documents ?? 0),
    unprocessedDocuments: Number(item.unprocessed_documents ?? 0),
    lastSyncAt: formatConnectorDate(item.last_sync_at),
  }));
}

function buildMockProcessingSummary(data) {
  const docs = normalizeSourceDocuments(data);
  const groups = new Map();
  for (const doc of docs) {
    const current = groups.get(doc.connectorType) ?? {
      connectorId: doc.connectorType,
      connectorType: doc.connectorType,
      status: "connected",
      totalDocuments: 0,
      processedDocuments: 0,
      unprocessedDocuments: 0,
      lastSyncAt: formatConnectorDate(doc.ingestedAt),
    };
    current.totalDocuments += 1;
    if (doc.processed) current.processedDocuments += 1;
    else current.unprocessedDocuments += 1;
    groups.set(doc.connectorType, current);
  }
  return Array.from(groups.values());
}

function normalizeReviewItems(data) {
  if (!Array.isArray(data)) return [];
  return data.map((item) => ({
    id: item.id,
    status: item.status ?? "needs_review",
    severity: item.severity ?? "medium",
    kind: item.kind ?? "review_item",
    title: item.title ?? "Untitled review item",
    summary: item.summary ?? "",
    confidence: typeof item.confidence === "number" ? item.confidence : null,
    freshness: item.freshness ?? formatConnectorDate(item.last_seen_at, { fallback: "—" }),
    model: item.model ?? item.model_name ?? null,
    modelId: item.modelId ?? item.model_id ?? null,
    sources: item.sources ?? [],
    sourceDocuments: item.sourceDocuments ?? item.source_documents ?? [],
    rationale: item.rationale ?? item.detail ?? "",
    suggestedAction: item.suggestedAction ?? item.suggested_action ?? null,
    lastSeenAt: item.lastSeenAt ?? item.last_seen_at ?? null,
    decisionHistory: normalizeReviewDecisionHistory(
      item.decisionHistory ?? item.decision_history ?? [],
    ),
  }));
}

function normalizeReviewDecisionHistory(data) {
  if (!Array.isArray(data)) return [];
  return data.map((item) => ({
    id: item.id,
    previousStatus: item.previousStatus ?? item.previous_status ?? null,
    newStatus: item.newStatus ?? item.new_status ?? null,
    actorType: item.actorType ?? item.actor_type ?? null,
    note: item.note ?? null,
    createdAt: item.createdAt ?? item.created_at ?? null,
  }));
}

function normalizeEvalSummary(data) {
  if (!data || typeof data !== "object") return null;

  const source = data.summary ?? data;
  const domains = Array.isArray(source.domains)
    ? source.domains
    : Array.isArray(source.domain_summaries)
      ? source.domain_summaries
      : [];

  return {
    passRate: toNumber(
      source.passRate ??
        source.pass_rate ??
        source.overall_pass_rate ??
        source.passRateOverall,
    ),
    passedCases: toNumber(
      source.passedCases ?? source.passed_cases ?? source.passed_count ?? source.total_passed ?? 0,
    ),
    totalCases: toNumber(
      source.totalCases ?? source.total_cases ?? source.total ?? source.case_count ?? 0,
    ),
    threshold: toNumber(source.threshold ?? source.pass_threshold ?? null),
    latestRunAt:
      source.latestRunAt ??
      source.latest_run_at ??
      source.latest_run_timestamp ??
      source.generated_at ??
      null,
    domains: domains.map((item) => ({
      domain: item.domain ?? item.name ?? "unknown",
      passRate: toNumber(item.passRate ?? item.pass_rate ?? 0),
      passed: toNumber(item.passed ?? item.passed_cases ?? item.case_count ?? 0),
      total: toNumber(item.total ?? item.total_cases ?? item.case_count ?? 0),
    })),
    metrics: normalizeEvalMetrics(
      source.metrics ??
        source.metric_summary ??
        buildEvalMetricSummary(source),
    ),
    blockers: normalizeEvalBlockers(source.blockers ?? []),
  };
}

function normalizeEvalMetrics(data) {
  if (Array.isArray(data)) {
    return data.map((item, index) => ({
      key: item.key ?? item.metric ?? `metric_${index + 1}`,
      label: item.label ?? item.metric ?? `Metric ${index + 1}`,
      value: toNumber(item.value ?? 0),
      target: toNumber(item.target ?? null),
      direction: item.direction === "down" ? "down" : "up",
    }));
  }

  if (!data || typeof data !== "object") return [];

  return Object.entries(data).map(([key, value]) => ({
    key,
    label: key.replaceAll("_", " "),
    value: toNumber(value ?? 0),
    target: null,
    direction: key.includes("error") ? "down" : "up",
  }));
}

function buildEvalMetricSummary(source) {
  const metrics = [];

  if (source.average_retrieval_hit_quality != null) {
    metrics.push({
      key: "average_retrieval_hit_quality",
      label: "Retrieval hit quality",
      value: source.average_retrieval_hit_quality,
      direction: "up",
    });
  }
  if (source.average_extracted_fact_correctness != null) {
    metrics.push({
      key: "average_extracted_fact_correctness",
      label: "Extracted fact correctness",
      value: source.average_extracted_fact_correctness,
      direction: "up",
    });
  }
  if (source.average_final_answer_correctness != null) {
    metrics.push({
      key: "average_final_answer_correctness",
      label: "Final answer correctness",
      value: source.average_final_answer_correctness,
      direction: "up",
    });
  }
  if (source.confidence_calibration_error != null) {
    metrics.push({
      key: "confidence_calibration_error",
      label: "Confidence calibration error",
      value: source.confidence_calibration_error,
      direction: "down",
    });
  }

  return metrics;
}

function normalizeEvalCases(data) {
  if (!data || typeof data !== "object") return null;

  const source = data;
  return {
    selectedDomain: source.selectedDomain ?? source.selected_domain ?? null,
    cases: normalizeEvalCaseItems(source.cases ?? []),
  };
}

function normalizeEvalCaseItems(data) {
  if (!Array.isArray(data)) return [];
  return data.map((item) => ({
    caseId: item.caseId ?? item.case_id ?? null,
    domain: item.domain ?? "unknown",
    question: item.question ?? "Untitled eval case",
    predictedConfidence: toNumber(item.predictedConfidence ?? item.predicted_confidence ?? null),
    retrievalHitQuality: toNumber(item.retrievalHitQuality ?? item.retrieval_hit_quality ?? null),
    extractedFactCorrectness: toNumber(
      item.extractedFactCorrectness ?? item.extracted_fact_correctness ?? null,
    ),
    finalAnswerCorrectness: toNumber(
      item.finalAnswerCorrectness ?? item.final_answer_correctness ?? null,
    ),
    passed: Boolean(item.passed),
    detail: item.detail ?? "",
  }));
}

function normalizeEvalBlockers(data) {
  if (!Array.isArray(data)) return [];
  return data.map((item) =>
    typeof item === "string"
      ? item
      : item?.detail ?? item?.question ?? item?.case_id ?? "Unknown blocker",
  );
}

function toNumber(value) {
  if (value == null || value === "") return null;
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : null;
}

function normalizeSourceComponentRefs(data) {
  if (!Array.isArray(data)) return [];
  return data.map((item) => ({
    id: item.id,
    name: item.name ?? "Unnamed component",
    value: item.value ?? "",
    confidence: typeof item.confidence === "number" ? item.confidence : null,
    modelId: item.modelId ?? item.model_id ?? null,
    modelName: item.modelName ?? item.model_name ?? item.model ?? "Unknown model",
    reviewStatus: item.reviewStatus ?? item.review_status ?? null,
    reviewItemId: item.reviewItemId ?? item.review_item_id ?? null,
    reviewSummary: item.reviewSummary ?? item.review_summary ?? null,
    temporalState: item.temporalState ?? item.temporal_state ?? null,
    validFrom: item.validFrom ?? item.valid_from ?? null,
    validTo: item.validTo ?? item.valid_to ?? null,
    supersededBy: item.supersededBy ?? item.superseded_by ?? null,
  }));
}

function normalizeComponentSourceRefs(data) {
  if (!Array.isArray(data)) return [];
  return data.map((item, index) => ({
    id: item.id ?? `${item.external_id ?? "source"}-${index}`,
    label:
      item.label ??
      item.location ??
      item.author ??
      item.externalId ??
      item.external_id ??
      `Source ${index + 1}`,
    connectorType: item.connectorType ?? item.connector_type ?? null,
    author: item.author ?? null,
    sourceUrl: item.sourceUrl ?? item.source_url ?? null,
    createdAtSource: item.createdAtSource ?? item.created_at_source ?? null,
    ingestedAt: item.ingestedAt ?? item.ingested_at ?? null,
    processedAt: item.processedAt ?? item.processed_at ?? null,
    extractionContext: item.extractionContext ?? item.extraction_context ?? null,
    extractorName: item.extractorName ?? item.extractor_name ?? null,
    extractorKind: item.extractorKind ?? item.extractor_kind ?? null,
    extractorSchemaVersion:
      item.extractorSchemaVersion ?? item.extractor_schema_version ?? null,
  }));
}

function filterReviewItems(items, filters) {
  const { status = "all", severity = "all", kind = "all" } = filters;
  return items.filter((item) => {
    const matchesStatus = status === "all" || item.status === status;
    const matchesSeverity = severity === "all" || item.severity === severity;
    const matchesKind = kind === "all" || item.kind === kind;
    return matchesStatus && matchesSeverity && matchesKind;
  });
}

function buildMockSourceComponentRefs(documentId) {
  return Object.entries(modelFixtures).flatMap(([modelId, model]) =>
    (model.components ?? [])
      .filter((component) =>
        (component.sourceDocuments ?? component.source_documents ?? []).some((doc) => doc?.id === documentId),
      )
      .map((component) => ({
        id: component.id,
        name: component.name,
        value: component.value,
        confidence: typeof component.confidence === "number" ? component.confidence : null,
        modelId,
        modelName: model.name,
        reviewStatus: component.reviewStatus ?? component.review_status ?? null,
        reviewItemId: component.reviewItemId ?? component.review_item_id ?? null,
        reviewSummary: component.reviewSummary ?? component.review_summary ?? null,
        temporalState: component.temporalState ?? component.temporal_state ?? null,
        validFrom: component.validFrom ?? component.valid_from ?? null,
        validTo: component.validTo ?? component.valid_to ?? null,
        supersededBy: component.supersededBy ?? component.superseded_by ?? null,
      })),
  );
}

function buildMockComponentSources(componentId) {
  for (const model of Object.values(modelFixtures)) {
    const component = (model.components ?? []).find((item) => item.id === componentId);
    if (component) {
      return normalizeComponentSourceRefs(component.sourceDocuments ?? component.source_documents ?? []);
    }
  }
  return [];
}

function buildMockSourceReviewItems(documentId) {
  return normalizeReviewItems(mockReviewQueue).filter((item) =>
    (item.sourceDocuments ?? []).some((doc) => doc?.id === documentId),
  );
}

function applySourceSearchFilter(items, search) {
  const q = search.trim().toLowerCase();
  if (!q) return items;
  return items.filter((item) => {
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
    return haystack.includes(q);
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
