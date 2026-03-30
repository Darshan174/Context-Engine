import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Sources from "../Sources";

vi.mock("../../api/hooks", () => ({
  useSourceDocuments: vi.fn(),
}));

import { useSourceDocuments } from "../../api/hooks";

const baseDocuments = [
  {
    id: "sd1",
    connectorType: "slack",
    externalId: "C-price:1",
    author: "Alice",
    content: "decision: enterprise pricing moves to $600/seat",
    preview: "decision: enterprise pricing moves to $600/seat",
    sourceUrl: "https://slack.com/doc/1",
    createdAtSource: "2026-03-29T09:20:00Z",
    ingestedAt: "2026-03-29T09:22:00Z",
    processedAt: "2026-03-29T09:23:00Z",
    processed: true,
    location: "#pricing",
  },
  {
    id: "sd2",
    connectorType: "slack",
    externalId: "C-prod:2",
    author: "Rahul",
    content: "blocker: SSO rollout is blocked by audit review",
    preview: "blocker: SSO rollout is blocked by audit review",
    sourceUrl: "https://slack.com/doc/2",
    createdAtSource: "2026-03-29T10:20:00Z",
    ingestedAt: "2026-03-29T10:21:00Z",
    processedAt: null,
    processed: false,
    location: "#product",
  },
  {
    id: "sd3",
    connectorType: "notion",
    externalId: "notion:page-1",
    author: "alice@example.com",
    content: "Engineering Roadmap\n\nWe are targeting Q3 for the SSO launch.",
    preview: "Engineering Roadmap",
    sourceUrl: "https://notion.so/page-1",
    createdAtSource: "2026-03-28T10:00:00Z",
    ingestedAt: "2026-03-29T14:05:00Z",
    processedAt: "2026-03-29T14:06:00Z",
    processed: true,
    location: "Engineering Roadmap",
  },
];

function renderSources() {
  return render(
    <MemoryRouter>
      <Sources />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
});

describe("Sources", () => {
  it("shows loading state", () => {
    useSourceDocuments.mockReturnValue({
      data: undefined,
      isMock: false,
      isLoading: true,
      isError: false,
      refetch: vi.fn(),
    });

    renderSources();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders mock badge, summary, and selected document detail", () => {
    useSourceDocuments.mockReturnValue({
      data: baseDocuments,
      isMock: true,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderSources();

    const detail = screen.getByRole("region", { name: "Document detail" });

    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.getByText(/Demo data/)).toBeInTheDocument();
    expect(screen.getByText(/3 stored · 2 processed · 1 pending/)).toBeInTheDocument();
    expect(within(detail).getByText("Alice")).toBeInTheDocument();
    expect(within(detail).getByText("Raw content")).toBeInTheDocument();
    expect(
      within(detail).getByText(/enterprise pricing moves to \$600\/seat/),
    ).toBeInTheDocument();
  });

  it("filters by connector and processing state", async () => {
    useSourceDocuments.mockImplementation(({ connector = "all", processed = "all" }) => {
      const filtered = baseDocuments.filter((doc) => {
        const matchesConnector = connector === "all" || doc.connectorType === connector;
        const matchesProcessed =
          processed === "all" ||
          (processed === "processed" && doc.processed) ||
          (processed === "unprocessed" && !doc.processed);
        return matchesConnector && matchesProcessed;
      });
      return {
        data: filtered,
        isMock: false,
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      };
    });

    renderSources();

    await userEvent.selectOptions(
      screen.getByLabelText("Filter source documents by connector"),
      "notion",
    );
    expect(
      within(screen.getByRole("region", { name: "Document detail" })).getByText("alice@example.com"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Rahul")).not.toBeInTheDocument();

    await userEvent.selectOptions(
      screen.getByLabelText("Filter source documents by processing state"),
      "unprocessed",
    );
    expect(screen.getByText("No source documents match the current filters.")).toBeInTheDocument();
  });

  it("filters by search text", async () => {
    useSourceDocuments.mockImplementation(({ search = "" }) => {
      const q = search.trim().toLowerCase();
      const filtered = !q
        ? baseDocuments
        : baseDocuments.filter((doc) =>
            [doc.author, doc.content, doc.location].join(" ").toLowerCase().includes(q),
          );
      return {
        data: filtered,
        isMock: false,
        isLoading: false,
        isError: false,
        refetch: vi.fn(),
      };
    });

    renderSources();

    await userEvent.type(screen.getByLabelText("Search source documents"), "roadmap");

    expect(
      within(screen.getByRole("region", { name: "Document detail" })).getByText("alice@example.com"),
    ).toBeInTheDocument();
    expect(screen.queryByText("Rahul")).not.toBeInTheDocument();
  });

  it("switches selected document when a row is clicked", async () => {
    useSourceDocuments.mockReturnValue({
      data: baseDocuments,
      isMock: false,
      isLoading: false,
      isError: false,
      refetch: vi.fn(),
    });

    renderSources();

    await userEvent.click(screen.getByRole("button", { name: /Rahul/i }));

    const detail = screen.getByRole("region", { name: "Document detail" });

    expect(within(detail).getByText("Pending extraction")).toBeInTheDocument();
    expect(
      within(detail).getByText(/SSO rollout is blocked by audit review/),
    ).toBeInTheDocument();
  });
});
