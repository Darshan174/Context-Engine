import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
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

describe("Connectors", () => {
  it("shows loading state", () => {
    useConnectors.mockReturnValue({
      data: undefined,
      isMock: false,
      isLoading: true,
      isError: false,
    });

    render(<Connectors />);
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows empty state when connector list is empty", () => {
    useConnectors.mockReturnValue({
      data: [],
      isMock: false,
      isLoading: false,
      isError: false,
    });

    render(<Connectors />);
    expect(screen.getByText("No connectors configured.")).toBeInTheDocument();
  });

  it("renders demo note and disables actions when mock-backed", () => {
    useConnectors.mockReturnValue({
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
      isLoading: false,
      isError: false,
    });

    render(<Connectors />);

    expect(screen.getByText(/Demo data/)).toBeInTheDocument();
    expect(screen.getByText(/OAuth and sync actions unlock once the backend endpoints are live/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Demo mode" })).toBeDisabled();
    expect(screen.getByRole("button", { name: "Coming soon" })).toBeDisabled();
  });

  it("renders Slack connect link for a real disconnected connector", () => {
    useConnectors.mockReturnValue({
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
      isMock: false,
      isLoading: false,
      isError: false,
    });

    render(<Connectors />);

    const link = screen.getByRole("link", { name: "Connect Slack" });
    expect(link).toHaveAttribute("href", "/api/connectors/slack/install?workspace_id=ws_1");
    expect(screen.getByText("Not connected")).toBeInTheDocument();
  });

  it("shows coming-soon connector as disabled", () => {
    useConnectors.mockReturnValue({
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
      isMock: false,
      isLoading: false,
      isError: false,
    });

    render(<Connectors />);

    expect(screen.getByRole("button", { name: "Coming soon" })).toBeDisabled();
    expect(screen.getByText(/deferred until the Slack path is stable/)).toBeInTheDocument();
  });

  it("queues sync for a connected connector", async () => {
    useConnectors.mockReturnValue({
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
      isMock: false,
      isLoading: false,
      isError: false,
    });

    render(<Connectors />);

    await userEvent.click(screen.getByRole("button", { name: "Sync now" }));
    expect(syncMut.mutate).toHaveBeenCalledWith("conn_1", expect.any(Object));
  });

  it("disconnects a connected connector", async () => {
    useConnectors.mockReturnValue({
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
      isMock: false,
      isLoading: false,
      isError: false,
    });

    render(<Connectors />);

    await userEvent.click(screen.getByRole("button", { name: "Disconnect" }));
    expect(disconnectMut.mutate).toHaveBeenCalledWith("conn_1", expect.any(Object));
  });

  it("renders backend connector metadata from config", () => {
    useConnectors.mockReturnValue({
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
        },
      ],
      isMock: false,
      isLoading: false,
      isError: false,
    });

    render(<Connectors />);

    expect(screen.getByText("Acme Workspace")).toBeInTheDocument();
    expect(screen.getByText(/Sync queued Mar 29, 2026, 9:35 AM/)).toBeInTheDocument();
    expect(screen.getByText(/Slack scopes: channels:history,channels:read/)).toBeInTheDocument();
  });

  it("shows success notice after sync callback succeeds", async () => {
    syncMut.mutate.mockImplementation((_id, opts) => opts.onSuccess());
    useConnectors.mockReturnValue({
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
      isMock: false,
      isLoading: false,
      isError: false,
    });

    render(<Connectors />);

    await userEvent.click(screen.getByRole("button", { name: "Sync now" }));
    expect(screen.getByText("Slack sync queued. Refreshing connector state.")).toBeInTheDocument();
  });
});
