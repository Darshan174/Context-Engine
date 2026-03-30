import { render, screen } from "@testing-library/react";
import { act } from "react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Connectors from "../Connectors";

vi.mock("../../api/hooks", () => ({
  useConnectors: vi.fn(),
  useSyncConnector: vi.fn(),
  useDisconnectConnector: vi.fn(),
  useWorkspaces: vi.fn(),
}));

vi.mock("../../context/WorkspaceContext", () => ({
  useWorkspaceSelection: vi.fn(),
  resolveWorkspaceId: vi.fn(),
}));

import {
  useConnectors,
  useDisconnectConnector,
  useSyncConnector,
  useWorkspaces,
} from "../../api/hooks";
import { resolveWorkspaceId, useWorkspaceSelection } from "../../context/WorkspaceContext";

const syncMut = {
  mutate: vi.fn(),
  isPending: false,
  variables: undefined,
};

const disconnectMut = {
  mutate: vi.fn(),
  isPending: false,
  variables: undefined,
};

function mockConnectorsQuery(overrides = {}) {
  const value = {
    data: [],
    isMock: false,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
    ...overrides,
  };
  useConnectors.mockReturnValue(value);
  return value;
}

function renderConnectors() {
  return render(
    <MemoryRouter>
      <Connectors />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  syncMut.mutate.mockReset();
  disconnectMut.mutate.mockReset();
  useSyncConnector.mockReturnValue(syncMut);
  useDisconnectConnector.mockReturnValue(disconnectMut);
  useWorkspaces.mockReturnValue({ data: [{ id: "ws_1", name: "Workspace" }] });
  useWorkspaceSelection.mockReturnValue({ selectedId: "ws_1" });
  resolveWorkspaceId.mockReturnValue("ws_1");
});

afterEach(() => {
  vi.useRealTimers();
});

describe("Connectors", () => {
  it("shows loading state", () => {
    mockConnectorsQuery({
      data: undefined,
      isLoading: true,
    });

    renderConnectors();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows empty state when connector list is empty", () => {
    mockConnectorsQuery({
      data: [],
    });

    renderConnectors();
    expect(screen.getByText("No connectors configured.")).toBeInTheDocument();
  });

  it("renders demo note and disables actions when mock-backed", () => {
    mockConnectorsQuery({
      data: [
        {
          type: "slack",
          connectorId: null,
          name: "Slack",
          description: "Channels",
          status: "connected",
          lastSync: "3 min ago",
          itemsSynced: 14820,
          color: "#4A154B",
          availability: "available",
        },
        {
          type: "notion",
          connectorId: null,
          name: "Notion",
          description: "Docs",
          status: "coming_soon",
          lastSync: "Never",
          itemsSynced: 0,
          color: "#111111",
          availability: "coming_soon",
        },
      ],
      isMock: true,
    });

    renderConnectors();

    expect(screen.getByText(/Demo data/)).toBeInTheDocument();
    expect(screen.getByText(/OAuth and sync actions unlock once the backend endpoints are live/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Demo mode" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Coming soon" })).toBeDisabled();
  });

  it("renders Slack connect link for a real disconnected connector", () => {
    mockConnectorsQuery({
      data: [
        {
          type: "slack",
          connectorId: null,
          name: "Slack",
          description: "Channels",
          status: "disconnected",
          lastSync: "Never",
          itemsSynced: 0,
          color: "#4A154B",
          availability: "available",
        },
      ],
    });

    renderConnectors();

    const link = screen.getByRole("link", { name: "Start Slack OAuth" });
    expect(link).toHaveAttribute("href", "/api/connectors/slack/install?workspace_id=ws_1");
    expect(screen.getByText("Not connected")).toBeInTheDocument();
    expect(screen.getByText("Slack is not connected yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Connect Slack" })).toHaveAttribute(
      "href",
      "/api/connectors/slack/install?workspace_id=ws_1",
    );
  });

  it("shows coming-soon connector as disabled", () => {
    mockConnectorsQuery({
      data: [
        {
          type: "gong",
          connectorId: null,
          name: "Gong",
          description: "Calls",
          status: "coming_soon",
          lastSync: "Never",
          itemsSynced: 0,
          color: "#7C3AED",
          availability: "coming_soon",
        },
      ],
    });

    renderConnectors();

    expect(screen.getByRole("button", { name: "Coming soon" })).toBeDisabled();
    expect(screen.getByText(/deferred until the Slack path is stable/)).toBeInTheDocument();
  });

  it("queues sync for a connected connector", async () => {
    mockConnectorsQuery({
      data: [
        {
          type: "slack",
          connectorId: "conn_1",
          name: "Slack",
          description: "Channels",
          status: "connected",
          lastSync: "just now",
          itemsSynced: 12,
          color: "#4A154B",
          availability: "available",
        },
      ],
    });

    renderConnectors();

    await userEvent.click(screen.getByRole("button", { name: "Sync now" }));
    expect(syncMut.mutate).toHaveBeenCalledWith("conn_1", expect.any(Object));
  });

  it("disconnects a connected connector", async () => {
    mockConnectorsQuery({
      data: [
        {
          type: "slack",
          connectorId: "conn_1",
          name: "Slack",
          description: "Channels",
          status: "connected",
          lastSync: "just now",
          itemsSynced: 12,
          color: "#4A154B",
          availability: "available",
        },
      ],
    });

    renderConnectors();

    await userEvent.click(screen.getByRole("button", { name: "Disconnect" }));
    expect(disconnectMut.mutate).toHaveBeenCalledWith("conn_1", expect.any(Object));
  });

  it("renders backend connector metadata from config", () => {
    mockConnectorsQuery({
      data: [
        {
          type: "slack",
          connectorId: "conn_1",
          name: "Slack",
          description: "Channels",
          status: "connected",
          lastSync: "Mar 29, 2026, 9:30 AM",
          itemsSynced: 42,
          color: "#4A154B",
          availability: "available",
          teamName: "Acme Workspace",
          scope: "channels:history,channels:read",
          syncQueuedAt: "Mar 29, 2026, 9:35 AM",
          message: "Sync queued (placeholder)",
          provider: "native",
          providerLabel: "Built in",
          providerNote:
            "Slack stays native because OAuth, thread expansion, and real-time events are product-critical.",
        },
      ],
    });

    renderConnectors();

    expect(screen.getByText("Acme Workspace")).toBeInTheDocument();
    expect(screen.getByText("Built in")).toBeInTheDocument();
    expect(screen.getByText(/Sync queued Mar 29, 2026, 9:35 AM/)).toBeInTheDocument();
    expect(screen.getByText(/Slack scopes: channels:history,channels:read/)).toBeInTheDocument();
    expect(screen.getByText(/Connector path: Slack stays native/)).toBeInTheDocument();
    expect(screen.getByText("Slack is connected to Acme Workspace.")).toBeInTheDocument();
    expect(screen.getByText("42 source documents available for extraction and query.")).toBeInTheDocument();
    expect(screen.getAllByRole("link", { name: "Inspect stored documents" })[0]).toHaveAttribute(
      "href",
      "/sources",
    );
    expect(screen.getByRole("link", { name: "Refresh OAuth" })).toHaveAttribute(
      "href",
      "/api/connectors/slack/install?workspace_id=ws_1",
    );
  });

  it("shows success notice after sync callback succeeds", async () => {
    syncMut.mutate.mockImplementation((_id, opts) =>
      opts.onSuccess({ message: "Synced 12 documents" }),
    );
    mockConnectorsQuery({
      data: [
        {
          type: "slack",
          connectorId: "conn_1",
          name: "Slack",
          description: "Channels",
          status: "connected",
          lastSync: "just now",
          itemsSynced: 12,
          color: "#4A154B",
          availability: "available",
        },
      ],
    });

    renderConnectors();

    await userEvent.click(screen.getByRole("button", { name: "Sync now" }));
    expect(screen.getByText("Synced 12 documents")).toBeInTheDocument();
  });

  it("shows reconnect guidance for error state", () => {
    mockConnectorsQuery({
      data: [
        {
          type: "slack",
          connectorId: "conn_1",
          name: "Slack",
          description: "Channels",
          status: "error",
          lastSync: "Never",
          itemsSynced: 12,
          color: "#4A154B",
          availability: "available",
        },
      ],
    });

    renderConnectors();

    expect(screen.getByText("Slack needs attention.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Refresh OAuth" })).toHaveAttribute(
      "href",
      "/api/connectors/slack/install?workspace_id=ws_1",
    );
    expect(screen.getByRole("link", { name: "Reconnect Slack" })).toHaveAttribute(
      "href",
      "/api/connectors/slack/install?workspace_id=ws_1",
    );
  });

  it("shows planned OSS providers for coming-soon connectors", () => {
    mockConnectorsQuery({
      data: [
        {
          type: "notion",
          connectorId: null,
          name: "Notion",
          description: "Docs",
          status: "coming_soon",
          lastSync: "Never",
          itemsSynced: 0,
          color: "#111111",
          availability: "coming_soon",
          provider: "dlt",
          providerLabel: "dlt",
          providerNote:
            "Planned to use a dlt verified source instead of hand-building the full Notion sync stack.",
        },
        {
          type: "gdrive",
          connectorId: null,
          name: "Google Drive",
          description: "Files",
          status: "coming_soon",
          lastSync: "Never",
          itemsSynced: 0,
          color: "#0F9D58",
          availability: "coming_soon",
          provider: "unstructured",
          providerLabel: "Unstructured",
          providerNote:
            "Planned to use Unstructured for Drive ingestion and document extraction.",
        },
      ],
    });

    renderConnectors();

    expect(screen.getByText("dlt")).toBeInTheDocument();
    expect(screen.getByText("Unstructured")).toBeInTheDocument();
    expect(screen.getByText(/dlt verified source/)).toBeInTheDocument();
    expect(screen.getByText(/Unstructured for Drive ingestion/)).toBeInTheDocument();
  });

  it("opens Slack OAuth in a popup and shows pending guidance", async () => {
    const popup = { closed: false, close: vi.fn(), focus: vi.fn() };
    vi.spyOn(window, "open").mockReturnValue(popup);
    mockConnectorsQuery({
      data: [
        {
          type: "slack",
          connectorId: null,
          name: "Slack",
          description: "Channels",
          status: "disconnected",
          lastSync: "Never",
          itemsSynced: 0,
          color: "#4A154B",
          availability: "available",
        },
      ],
    });

    renderConnectors();

    await userEvent.click(screen.getByRole("link", { name: "Connect Slack" }));

    expect(window.open).toHaveBeenCalledWith(
      "/api/connectors/slack/install?workspace_id=ws_1",
      "ce-slack-oauth",
      expect.stringContaining("width=640"),
    );
    expect(screen.getByText(/Slack OAuth opened in a new window/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Waiting for Slack..." })).toBeDisabled();
  });

  it("refreshes connector state after popup closes and shows success notice", async () => {
    const user = userEvent.setup();
    const popup = { closed: false, close: vi.fn(), focus: vi.fn() };
    vi.spyOn(window, "open").mockReturnValue(popup);
    let pollCallback;
    vi.spyOn(window, "setInterval").mockImplementation((fn) => {
      pollCallback = fn;
      return 1;
    });
    vi.spyOn(window, "clearInterval").mockImplementation(() => {});
    const refetch = vi.fn().mockResolvedValue({
      isError: false,
      data: [
        {
          type: "slack",
          connectorId: "conn_1",
          name: "Slack",
          description: "Channels",
          status: "connected",
          lastSync: "just now",
          itemsSynced: 12,
          color: "#4A154B",
          availability: "available",
          teamName: "Acme Workspace",
        },
      ],
    });
    mockConnectorsQuery({
      data: [
        {
          type: "slack",
          connectorId: null,
          name: "Slack",
          description: "Channels",
          status: "disconnected",
          lastSync: "Never",
          itemsSynced: 0,
          color: "#4A154B",
          availability: "available",
        },
      ],
      refetch,
    });

    renderConnectors();

    await user.click(screen.getByRole("link", { name: "Connect Slack" }));
    popup.closed = true;

    await act(async () => {
      pollCallback();
      await Promise.resolve();
      await Promise.resolve();
    });

    expect(refetch).toHaveBeenCalled();
    expect(screen.getByText("Slack connected to Acme Workspace.")).toBeInTheDocument();
  });
});
