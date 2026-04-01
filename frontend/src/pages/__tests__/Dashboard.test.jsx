import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "../Dashboard";

vi.mock("../../api/hooks", () => ({
  useConnectorProcessingSummary: vi.fn(),
  useConnectors: vi.fn(),
  useDashboard: vi.fn(),
  useEvalSummary: vi.fn(),
  useReviewQueue: vi.fn(),
}));

import {
  useConnectorProcessingSummary,
  useConnectors,
  useDashboard,
  useEvalSummary,
  useReviewQueue,
} from "../../api/hooks";

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useConnectors.mockReturnValue({
    isLoading: false,
    isError: false,
    isMock: false,
    data: [],
    refetch: vi.fn(),
  });
  useConnectorProcessingSummary.mockReturnValue({
    data: { items: [] },
    refetch: vi.fn(),
  });
  useReviewQueue.mockReturnValue({
    isLoading: false,
    isError: false,
    data: [],
    refetch: vi.fn(),
  });
  useEvalSummary.mockReturnValue({
    isLoading: false,
    isError: false,
    isMock: false,
    data: {
      passRate: 0.72,
      passedCases: 18,
      totalCases: 25,
      threshold: 0.7,
      latestRunAt: "2026-04-01T09:30:00Z",
      domains: [
        { domain: "pricing", passRate: 0.8, passed: 4, total: 5 },
        { domain: "meeting", passRate: 0.6, passed: 3, total: 5 },
      ],
      blockers: ["Meeting domain still depends on a small gold set."],
      metrics: [],
    },
    refetch: vi.fn(),
  });
});

describe("Dashboard", () => {
  it("shows loading state", () => {
    useDashboard.mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
      refetch: vi.fn(),
    });

    renderDashboard();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows stat cards with data", () => {
    useDashboard.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        stats: [
          { label: "Sources", value: 42, delta: "1 connector active" },
          { label: "Models", value: 2, delta: "stable" },
          { label: "Components", value: 15, delta: "+5" },
          { label: "Relationships", value: 8, delta: "+2" },
        ],
        activity: [],
        alerts: [],
      },
      refetch: vi.fn(),
    });

    renderDashboard();
    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.getByText("15")).toBeInTheDocument();
    expect(screen.getByText("Live source data is available")).toBeInTheDocument();
    expect(screen.getByText(/stored and ready for extraction and query/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Inspect source documents" })).toHaveAttribute("href", "/app/sources");
    expect(screen.getByRole("link", { name: /Sources/ })).toHaveAttribute("href", "/app/sources");
    expect(screen.queryByText("Your workspace is empty")).not.toBeInTheDocument();
  });

  it("renders trust status counts and review queue link", () => {
    useDashboard.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        stats: [{ label: "Models", value: 1, delta: "—" }],
        activity: [],
        alerts: [],
      },
      refetch: vi.fn(),
    });
    useReviewQueue.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [
        { id: "r1", status: "needs_review", kind: "conflict" },
        { id: "r2", status: "needs_review", kind: "low_confidence" },
        { id: "r3", status: "superseded", kind: "superseded_fact" },
      ],
      refetch: vi.fn(),
    });

    renderDashboard();

    expect(screen.getByText("Trust Status")).toBeInTheDocument();
    expect(screen.getByText("Needs review")).toBeInTheDocument();
    expect(screen.getByText("Conflicts")).toBeInTheDocument();
    expect(screen.getByText("Historical facts")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open review queue" })).toHaveAttribute("href", "/app/review");
    expect(screen.getByRole("link", { name: /Needs review/ })).toHaveAttribute("href", "/app/review?status=needs_review");
    expect(screen.getByRole("link", { name: /Conflicts/ })).toHaveAttribute("href", "/app/review?kind=conflict");
    expect(screen.getByRole("link", { name: /Historical facts/ })).toHaveAttribute("href", "/app/review?status=superseded");
    expect(screen.getByText(/Review attention is needed/)).toBeInTheDocument();
  });

  it("renders accuracy status summary and accuracy dashboard link", () => {
    useDashboard.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        stats: [{ label: "Models", value: 1, delta: "—" }],
        activity: [],
        alerts: [],
      },
      refetch: vi.fn(),
    });

    renderDashboard();

    expect(screen.getByText("Accuracy Status")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open accuracy dashboard" })).toHaveAttribute(
      "href",
      "/app/accuracy",
    );
    expect(screen.getByRole("link", { name: /Pass rate/ })).toHaveAttribute(
      "href",
      "/app/accuracy",
    );
    expect(screen.getByRole("link", { name: /At-risk domains/ })).toHaveAttribute(
      "href",
      "/app/accuracy",
    );
    expect(screen.getByRole("link", { name: /Open blockers/ })).toHaveAttribute(
      "href",
      "/app/accuracy",
    );
    expect(screen.getByText(/Latest eval run/)).toBeInTheDocument();
  });

  it("renders pipeline status cards and run-history links", () => {
    useDashboard.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        stats: [{ label: "Sources", value: 12, delta: "2 connectors active" }],
        activity: [],
        alerts: [],
      },
      refetch: vi.fn(),
    });
    useConnectors.mockReturnValue({
      isLoading: false,
      isError: false,
      isMock: false,
      data: [
        {
          type: "slack",
          connectorId: "conn_slack",
          name: "Slack",
          description: "Channels",
          status: "connected",
          lastSync: "Mar 31, 2026, 9:05 AM",
          itemsSynced: 10,
          providerLabel: "Built in",
          availability: "available",
        },
        {
          type: "notion",
          connectorId: "conn_notion",
          name: "Notion",
          description: "Docs",
          status: "error",
          lastSync: "Never",
          itemsSynced: 2,
          providerLabel: "dlt",
          syncQueuedAt: "Mar 31, 2026, 10:00 AM",
          availability: "available",
        },
      ],
      refetch: vi.fn(),
    });
    useConnectorProcessingSummary.mockReturnValue({
      data: {
        items: [
          {
            connectorType: "slack",
            processedDocuments: 8,
            unprocessedDocuments: 2,
            totalDocuments: 10,
          },
          {
            connectorType: "notion",
            processedDocuments: 1,
            unprocessedDocuments: 1,
            totalDocuments: 2,
          },
        ],
      },
      refetch: vi.fn(),
    });

    renderDashboard();

    expect(screen.getByText("Pipeline Status")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open connectors" })).toHaveAttribute("href", "/app/connectors");
    expect(screen.getByRole("link", { name: /Queued syncs/ })).toHaveAttribute("href", "/app/connectors");
    expect(screen.getByRole("link", { name: /Connector errors/ })).toHaveAttribute("href", "/app/connectors");
    expect(screen.getByRole("link", { name: /Pending extraction/ })).toHaveAttribute("href", "/app/sources?processed=unprocessed");
    expect(screen.getByText("Slack")).toBeInTheDocument();
    expect(screen.getByText("Notion")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Run history" })[0]).toHaveAttribute(
      "href",
      "/app/connectors/slack/runs",
    );
    expect(screen.getByText(/Extraction is still pending for 2 source documents/i)).toBeInTheDocument();
    expect(screen.getByText(/Sync queued Mar 31, 2026, 10:00 AM/i)).toBeInTheDocument();
    expect(screen.getByText(/needs attention before new source data can be trusted/i)).toBeInTheDocument();
  });

  it("shows onboarding hint when all stats are zero", () => {
    useDashboard.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        stats: [
          { label: "Sources", value: 0, delta: "—" },
          { label: "Models", value: 0, delta: "—" },
          { label: "Components", value: 0, delta: "—" },
          { label: "Relationships", value: 0, delta: "—" },
        ],
        activity: [],
        alerts: [],
      },
      refetch: vi.fn(),
    });

    renderDashboard();
    expect(screen.getByText("Your workspace is empty")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Models" })).toHaveAttribute("href", "/app/models");
  });

  it("degrades gracefully when activity and alerts are missing", () => {
    useDashboard.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        stats: [{ label: "Models", value: 1, delta: "—" }],
      },
      refetch: vi.fn(),
    });

    renderDashboard();
    expect(screen.getByText("No recent activity.")).toBeInTheDocument();
    expect(screen.getByText("No alerts.")).toBeInTheDocument();
  });

  it("renders activity items and alert items", () => {
    useDashboard.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        stats: [{ label: "Models", value: 1, delta: "—" }],
        activity: [
          { id: 1, text: "Slack synced 10 messages", ts: "5 min ago", type: "sync" },
        ],
        alerts: [
          { id: 1, source: "Gong", message: "No data in 7 days", severity: "error" },
        ],
      },
      refetch: vi.fn(),
    });

    renderDashboard();
    expect(screen.getByText("Slack synced 10 messages")).toBeInTheDocument();
    expect(screen.getByText("Gong")).toBeInTheDocument();
    expect(screen.getByText("No data in 7 days")).toBeInTheDocument();
  });
});
