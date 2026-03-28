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
      () => api.get("/connectors"),
      mockConnectors,
      { fallbackStatuses: [404, 501] },
    ),
  });
  return { ...query, isMock: query.data === mockConnectors };
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
      } catch {
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
