import { render, screen, within } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import Engineering from "../Engineering";

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

function renderEngineering({ initialEntries = ["/app/engineering/sd12"] } = {}) {
  return render(
    <MemoryRouter initialEntries={initialEntries}>
      <Routes>
        <Route path="/app/engineering" element={<Engineering />} />
        <Route path="/app/engineering/:documentId" element={<Engineering />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useSourceDocuments.mockReturnValue({
    data: [
      {
        id: "sd11",
        connectorType: "github",
        repository: "acme/context-engine",
        documentTitle: "Issue #42: Tighten accuracy gating",
        githubItemType: "issue",
        author: "octocat",
        createdAtSource: "2026-04-01T10:00:00Z",
        ingestedAt: "2026-04-01T10:08:00Z",
        processed: true,
        content:
          "Track the regression command and make the eval bar visible before launch.",
        pullRequestReferences: [],
        commitReferences: [],
      },
      {
        id: "sd12",
        connectorType: "github",
        repository: "acme/context-engine",
        documentTitle: "Review Comment on Pull Request #77: Add eval CLI",
        githubItemType: "pull_request_review_comment",
        author: "maintainer",
        createdAtSource: "2026-04-01T12:45:00Z",
        ingestedAt: "2026-04-01T12:50:00Z",
        processed: true,
        content:
          "decision: ship after PR #13 and commit abc1234.\nblocker: waiting on CI stability.",
        parentExternalId: "github:acme/context-engine:pull_request:77",
        pullRequestReferences: ["acme/context-engine#13"],
        commitReferences: ["abc1234"],
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
        id: "e1",
        name: "Decision: Ship eval CLI after PR #13",
        value: "Ship after PR #13 and commit abc1234",
        modelId: "engineering",
        modelName: "Engineering Execution",
        reviewStatus: "approved",
        authorityWeight: 0.93,
        validFrom: "2026-04-01T12:45:00Z",
      },
      {
        id: "e2",
        name: "CI stability blocker",
        value: "Waiting on CI stability before merge",
        modelId: "engineering",
        modelName: "Engineering Execution",
        reviewStatus: "needs_review",
        reviewItemId: "rq5",
        authorityWeight: 0.66,
        validFrom: "2026-04-01T12:46:00Z",
      },
      {
        id: "e3",
        name: "Decision: Old eval rollout sequence",
        value: "Ship before PR #13 lands",
        modelId: "engineering",
        modelName: "Engineering Execution",
        reviewStatus: "historical",
        temporalState: "historical",
        validFrom: "2026-03-28T12:00:00Z",
        validTo: "2026-04-01T12:45:00Z",
      },
    ],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });
  useSourceDocumentReviewItems.mockReturnValue({
    data: [
      {
        id: "rq5",
        title: "CI stability still needs confirmation",
        summary: "The review comment points at CI instability but the owner is still unclear.",
      },
    ],
    isLoading: false,
    isError: false,
    refetch: vi.fn(),
  });
});

describe("Engineering", () => {
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

    renderEngineering({ initialEntries: ["/app/engineering"] });

    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows empty state when there is no GitHub activity", () => {
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

    renderEngineering({ initialEntries: ["/app/engineering"] });

    expect(screen.getByText("No GitHub activity yet.")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Connect GitHub" })).toHaveAttribute(
      "href",
      "/app/connectors",
    );
  });

  it("renders engineering detail with refs, linked facts, and review pressure", () => {
    renderEngineering();

    expect(screen.getByText("Engineering")).toBeInTheDocument();
    expect(screen.getByText("Engineering signal snapshot")).toBeInTheDocument();
    expect(screen.getByText("Repository").closest("div")).toHaveTextContent("acme/context-engine");
    expect(screen.getAllByText("Review Comment on Pull Request #77: Add eval CLI")).toHaveLength(2);
    expect(screen.getAllByText("Linked decisions")).toHaveLength(2);
    expect(screen.getByText("Blocked or pending work")).toBeInTheDocument();
    expect(screen.getByText("Decision: Ship eval CLI after PR #13")).toBeInTheDocument();
    expect(screen.getByText("CI stability blocker")).toBeInTheDocument();
    expect(screen.getByText("Decision: Old eval rollout sequence")).toBeInTheDocument();
    expect(screen.getByText("CI stability still needs confirmation")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open timeline" })).toHaveAttribute(
      "href",
      "/app/changes",
    );
  });

  it("shows list stats and repository metadata in the engineering list", () => {
    renderEngineering();

    const listItem = screen.getByRole("button", {
      name: /review comment on pull request #77: add eval cli/i,
    });
    expect(within(listItem).getByText("2 refs · 1 decisions")).toBeInTheDocument();
    expect(within(listItem).getByText("pull request review comment")).toBeInTheDocument();
  });

  it("shows snapshot counts and refs for the selected engineering item", () => {
    renderEngineering();

    expect(screen.getByText("PR / commit refs").closest("div")).toHaveTextContent("2");
    expect(screen.getAllByText("Linked decisions")[0].closest("div")).toHaveTextContent("1");
    expect(screen.getAllByText("Open blockers")[0].closest("div")).toHaveTextContent("1");
    expect(screen.getByText("Review threads").closest("div")).toHaveTextContent("1");
    expect(screen.getByText("acme/context-engine#13")).toBeInTheDocument();
    expect(screen.getByText("abc1234")).toBeInTheDocument();
    expect(screen.getAllByText("Authority:")[0].parentElement).toHaveTextContent("Authority: 0.93");
  });
});
