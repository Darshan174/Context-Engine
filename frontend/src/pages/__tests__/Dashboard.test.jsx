import { render, screen } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import Dashboard from "../Dashboard";

vi.mock("../../api/hooks", () => ({
  useDashboard: vi.fn(),
}));

import { useDashboard } from "../../api/hooks";

function renderDashboard() {
  return render(
    <MemoryRouter>
      <Dashboard />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
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
          { label: "Sources", value: 3, delta: "+1" },
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
    expect(screen.queryByText("Your workspace is empty")).not.toBeInTheDocument();
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
    expect(screen.getByRole("link", { name: "Models" })).toHaveAttribute("href", "/models");
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
