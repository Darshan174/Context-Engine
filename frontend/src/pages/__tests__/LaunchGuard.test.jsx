import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import LaunchGuard from "../LaunchGuard";

vi.mock("../../api/hooks", () => ({
  useLaunchGuardContext: vi.fn(),
  useLaunchGuardCheck: vi.fn(),
}));

import { useLaunchGuardCheck, useLaunchGuardContext } from "../../api/hooks";

function renderLaunchGuard() {
  return render(
    <MemoryRouter>
      <LaunchGuard />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useLaunchGuardContext.mockReturnValue({
    isLoading: false,
    isError: false,
    isMock: false,
    data: {
      decisions: [
        {
          id: "sd1",
          title: "Enterprise pricing moves to $600 per seat",
          summary: "Slack confirmed the pricing change for next quarter.",
          status: "needs_review",
          sourceDocumentId: "sd1",
          sourceLabel: "#pricing",
          reviewItemIds: ["rq1"],
        },
      ],
      components: [
        {
          id: "p1",
          name: "Enterprise Seat Price",
          value: "$600/seat",
          modelId: "pricing",
          modelName: "Pricing Strategy",
          reviewStatus: "needs_review",
          reviewSummary: "Slack and Notion disagree on the active enterprise price.",
          reviewItemId: "rq1",
          temporalState: null,
          confidence: 0.86,
        },
      ],
      reviewItems: [
        {
          id: "rq1",
          title: "Pricing conflict",
          summary: "Slack and Notion disagree on the active enterprise price.",
          status: "needs_review",
          model: "Pricing Strategy",
        },
      ],
      evalSummary: {
        threshold: 0.7,
        domains: [
          { domain: "pricing", passRate: 0.6, passed: 3, total: 5 },
        ],
      },
    },
    refetch: vi.fn(),
  });
  useLaunchGuardCheck.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({
      claims: [
        {
          claim: "We are launching enterprise pricing at $500 per seat next week once the pricing page is published.",
          status: "contradicted",
          reason: "Current trusted pricing differs from the claim.",
          matched_component_id: "p1",
          matched_component_name: "Enterprise Seat Price",
          matched_component_value: "$600/seat",
          evidence: [
            {
              source_document_id: "sd1",
              label: "#pricing",
              connector_type: "slack",
            },
          ],
        },
      ],
    }),
    isPending: false,
  });
});

describe("LaunchGuard", () => {
  it("shows loading state", () => {
    useLaunchGuardContext.mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
      refetch: vi.fn(),
    });

    renderLaunchGuard();

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows empty state when launch-guard context is missing", () => {
    useLaunchGuardContext.mockReturnValue({
      isLoading: false,
      isError: false,
      isMock: false,
      data: {
        decisions: [],
        components: [],
        reviewItems: [],
        evalSummary: null,
      },
      refetch: vi.fn(),
    });

    renderLaunchGuard();

    expect(screen.getByText("Launch Guard does not have enough context yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Connect sources" })).toHaveAttribute(
      "href",
      "/app/connectors",
    );
  });

  it("analyzes a risky draft against current trust state", async () => {
    renderLaunchGuard();

    await userEvent.click(screen.getByRole("button", { name: "Pricing announcement" }));

    expect(screen.getByText("High risk")).toBeInTheDocument();
    expect(screen.getByText(/Contradicted claim/i)).toBeInTheDocument();
    expect(screen.getByText(/Current trusted pricing differs from the claim/i)).toBeInTheDocument();
    expect(screen.getByText("Grounding evidence")).toBeInTheDocument();
    expect(screen.getByText("Enterprise Seat Price")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open timeline" })).toHaveAttribute(
      "href",
      "/app/changes",
    );
  });
});
