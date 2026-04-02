import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Meetings from "../Meetings";

vi.mock("../../api/hooks", () => ({
  useSourceDocument: vi.fn(),
  useSourceDocumentComponents: vi.fn(),
  useSourceDocumentReviewItems: vi.fn(),
  useSourceDocuments: vi.fn(),
}));

import {
  useSourceDocument,
  useSourceDocumentComponents,
  useSourceDocumentReviewItems,
  useSourceDocuments,
} from "../../api/hooks";

function renderMeetings({ initialEntries = ["/app/meetings/sd10"] } = {}) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/app/meetings" element={<Meetings />} />
        <Route path="/app/meetings/:documentId" element={<Meetings />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useSourceDocuments.mockReturnValue({
    data: [
      {
        id: "sd10",
        connectorType: "zoom",
        meetingTopic: "Weekly Product Review",
        location: "Weekly Product Review",
        host: "founder@example.com",
        participants: ["Founder", "Ops"],
        recordingDate: "2026-03-31",
        createdAtSource: "2026-03-31T10:00:05Z",
        ingestedAt: "2026-03-31T10:16:00Z",
        processed: true,
        content:
          "Founder: decision: Launch the pricing page next Tuesday.\nOps: blocker: waiting on legal approval.",
      },
    ],
    isLoading: false,
    isError: false,
    isMock: false,
    hasMore: false,
    fetchNextPage: vi.fn(),
    isFetchingNextPage: false,
    refetch: vi.fn(),
  });
  useSourceDocument.mockReturnValue({
    data: null,
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });
  useSourceDocumentComponents.mockReturnValue({
    data: [
      {
        id: "c1",
        name: "Decision: Pricing page launch",
        value: "Launch the pricing page next Tuesday",
        modelId: "pricing",
        modelName: "Pricing Strategy",
        reviewStatus: "approved",
        authorityWeight: 0.95,
        validFrom: "2026-03-31T10:00:00Z",
      },
      {
        id: "c2",
        name: "Launch blocker",
        value: "Waiting on legal approval",
        modelId: "roadmap",
        modelName: "Engineering Roadmap",
        reviewStatus: "needs_review",
        reviewItemId: "rq1",
        authorityWeight: 0.6,
        validFrom: "2026-03-31T10:05:00Z",
      },
      {
        id: "c3",
        name: "Decision: Old pricing page date",
        value: "Ship the pricing page this Friday",
        modelId: "pricing",
        modelName: "Pricing Strategy",
        reviewStatus: "historical",
        temporalState: "historical",
        validFrom: "2026-03-25T10:00:00Z",
        validTo: "2026-03-31T10:00:00Z",
      },
    ],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });
  useSourceDocumentReviewItems.mockReturnValue({
    data: [
      {
        id: "rq1",
        title: "Pricing page blocker needs review",
        summary: "Legal approval is still unresolved.",
      },
    ],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });
});

describe("Meetings", () => {
  it("shows loading state", () => {
    useSourceDocuments.mockReturnValue({
      data: undefined,
      isLoading: true,
      isError: false,
      isMock: false,
      hasMore: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
      refetch: vi.fn(),
    });

    renderMeetings({ initialEntries: ["/app/meetings"] });

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows empty state when there are no transcripts", () => {
    useSourceDocuments.mockReturnValue({
      data: [],
      isLoading: false,
      isError: false,
      isMock: false,
      hasMore: false,
      fetchNextPage: vi.fn(),
      isFetchingNextPage: false,
      refetch: vi.fn(),
    });

    renderMeetings({ initialEntries: ["/app/meetings"] });

    expect(screen.getByText("No Zoom meeting transcripts yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Connect Zoom" })).toHaveAttribute(
      "href",
      "/app/connectors",
    );
  });

  it("renders meeting transcript detail with decisions, blockers, outcomes, and review items", () => {
    renderMeetings();

    expect(screen.getByText("Meetings")).toBeInTheDocument();
    expect(screen.getAllByText("Weekly Product Review")).toHaveLength(2);
    expect(screen.getByText("Meeting outcome snapshot")).toBeInTheDocument();
    expect(screen.getAllByText("Current decisions")).toHaveLength(2);
    expect(screen.getAllByText("Open loops")).toHaveLength(2);
    expect(screen.getByText("Historical context")).toBeInTheDocument();
    expect(screen.getByText("Launch the pricing page next Tuesday.")).toBeInTheDocument();
    expect(screen.getByText("waiting on legal approval.")).toBeInTheDocument();
    expect(screen.getByText("Decision: Pricing page launch")).toBeInTheDocument();
    expect(screen.getByText("Launch blocker")).toBeInTheDocument();
    expect(screen.getByText("Decision: Old pricing page date")).toBeInTheDocument();
    expect(screen.getByText("Pricing page blocker needs review")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open timeline" })).toHaveAttribute(
      "href",
      "/app/changes",
    );
    expect(screen.getByRole("link", { name: "Open launch guard" })).toHaveAttribute(
      "href",
      "/app/launch-guard",
    );
  });

  it("shows transcript stats in the meeting list", () => {
    renderMeetings();

    const listItem = screen.getByRole("button", { name: /weekly product review/i });
    expect(within(listItem).getByText("1 decisions · 1 blockers")).toBeInTheDocument();
    expect(within(listItem).getByText("Zoom transcript")).toBeInTheDocument();
  });

  it("shows outcome snapshot counts for the selected meeting", () => {
    renderMeetings();

    expect(screen.getAllByText("Current decisions")[0].closest("div")).toHaveTextContent("1");
    expect(screen.getAllByText("Open loops")[0].closest("div")).toHaveTextContent("1");
    expect(screen.getByText("Review threads").closest("div")).toHaveTextContent("1");
    expect(screen.getByText("Historical facts").closest("div")).toHaveTextContent("1");
    expect(screen.getAllByText("Authority:")[0].parentElement).toHaveTextContent(
      "Authority: 0.95",
    );
    expect(screen.getByRole("link", { name: "Open review" })).toHaveAttribute(
      "href",
      "/app/review/rq1",
    );
  });
});
