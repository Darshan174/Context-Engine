import { render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import ConnectorRuns from "../ConnectorRuns";

vi.mock("../../api/hooks", () => ({
  useConnectors: vi.fn(),
  useConnectorSyncJobs: vi.fn(),
  useConnectorSyncStatus: vi.fn(),
}));

import {
  useConnectors,
  useConnectorSyncJobs,
  useConnectorSyncStatus,
} from "../../api/hooks";

function renderRuns(initialEntry = "/app/connectors/slack/runs") {
  return render(
    <MemoryRouter initialEntries={[initialEntry]}>
      <Routes>
        <Route path="/app/connectors/:connectorType/runs" element={<ConnectorRuns />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useConnectorSyncJobs.mockReturnValue({
    data: [],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });
  useConnectorSyncStatus.mockReturnValue({
    data: null,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });
});

describe("ConnectorRuns", () => {
  it("renders loading state", () => {
    useConnectors.mockReturnValue({
      data: undefined,
      isMock: false,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });

    renderRuns();

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders recent jobs and latest job details for a live connector", () => {
    useConnectors.mockReturnValue({
      data: [
        {
          type: "slack",
          connectorId: "conn_1",
          name: "Slack",
          description: "Channels",
          status: "connected",
          lastSync: "Mar 31, 2026, 9:05 AM",
          itemsSynced: 18,
          processedCount: 11,
        },
      ],
      isMock: false,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    useConnectorSyncStatus.mockReturnValue({
      data: {
        jobId: "job_latest",
        jobType: "sync",
        status: "completed",
        createdAt: "2026-03-31T09:00:00Z",
        startedAt: "2026-03-31T09:00:05Z",
        completedAt: "2026-03-31T09:01:00Z",
        resultMetadata: {
          documents_fetched: 18,
          documents_persisted: 12,
          documents_processed: 11,
          sync_mode: "incremental",
        },
      },
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });
    useConnectorSyncJobs.mockReturnValue({
      data: [
        {
          jobId: "job_latest",
          jobType: "sync",
          status: "completed",
          createdAt: "2026-03-31T09:00:00Z",
          completedAt: "2026-03-31T09:01:00Z",
          resultMetadata: {
            documents_fetched: 18,
            documents_persisted: 12,
            documents_processed: 11,
          },
        },
        {
          jobId: "job_prev",
          jobType: "reprocess",
          status: "failed",
          createdAt: "2026-03-31T08:00:00Z",
          errorMessage: "Extraction worker timed out",
          resultMetadata: {},
        },
      ],
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderRuns();

    expect(screen.getByText("Slack Run History")).toBeInTheDocument();
    expect(screen.getByText("Latest job")).toBeInTheDocument();
    expect(
      screen.getByText("Slack sync completed: fetched 18, stored 12, processed 11 (incremental)."),
    ).toBeInTheDocument();
    expect(screen.getByText("Recent runs")).toBeInTheDocument();
    expect(screen.getByText("Fetched 18, stored 12, processed 11")).toBeInTheDocument();
    expect(screen.getByText("Extraction worker timed out")).toBeInTheDocument();
    expect(screen.getByText("reprocess")).toBeInTheDocument();
  });

  it("shows mock-mode notice when live run history is unavailable", () => {
    useConnectors.mockReturnValue({
      data: [
        {
          type: "slack",
          connectorId: null,
          name: "Slack",
          description: "Channels",
          status: "connected",
          lastSync: "Never",
          itemsSynced: 0,
        },
      ],
      isMock: true,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderRuns();

    expect(screen.getByText(/Demo data/)).toBeInTheDocument();
    expect(screen.getByText(/Live run history is unavailable in demo mode/)).toBeInTheDocument();
  });
});
