import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import Query from "../Query";

vi.mock("../../api/hooks", () => ({
  useContextQuery: vi.fn(),
}));

import { useContextQuery } from "../../api/hooks";

const noopMut = {
  mutate: vi.fn(),
  data: undefined,
  isPending: false,
  isError: false,
  error: null,
};

beforeEach(() => {
  vi.clearAllMocks();
  useContextQuery.mockReturnValue(noopMut);
});

describe("Query — empty state", () => {
  it("renders hint text and suggested question chips", () => {
    render(<Query />);

    expect(screen.getByText("Ask a question to query your knowledge graph.")).toBeInTheDocument();
    expect(screen.getByText("What is our current MRR?")).toBeInTheDocument();
    expect(screen.getByText("How healthy are our customers?")).toBeInTheDocument();
  });

  it("has Ask button disabled when input is blank", () => {
    render(<Query />);

    expect(screen.getByText("Ask")).toBeDisabled();
  });
});

describe("Query — submit flow", () => {
  it("calls mutate on form submit", async () => {
    const mutate = vi.fn();
    useContextQuery.mockReturnValue({ ...noopMut, mutate });

    render(<Query />);

    await userEvent.type(
      screen.getByPlaceholderText("Ask a question about your company data..."),
      "What is our MRR?",
    );
    await userEvent.click(screen.getByText("Ask"));

    expect(mutate).toHaveBeenCalledWith("What is our MRR?");
  });

  it("calls mutate when clicking a suggested question chip", async () => {
    const mutate = vi.fn();
    useContextQuery.mockReturnValue({ ...noopMut, mutate });

    render(<Query />);

    await userEvent.click(screen.getByText("What is our current MRR?"));

    expect(mutate).toHaveBeenCalledWith("What is our current MRR?");
  });

  it("shows pending state", () => {
    useContextQuery.mockReturnValue({ ...noopMut, isPending: true });

    render(<Query />);

    expect(screen.getByText("Querying knowledge graph...")).toBeInTheDocument();
    expect(screen.getByText("Thinking...")).toBeInTheDocument();
  });
});

describe("Query — mock response", () => {
  const mockResult = {
    question: "What is our MRR?",
    answer: "Current MRR is $2.4M.",
    confidence: 0.92,
    answeredAt: "just now",
    components: [
      { id: "c1", name: "MRR", value: "$2.4M", model: "Revenue Model" },
    ],
    sources: ["Stripe", "Internal DB"],
    _isMock: true,
  };

  it("shows answer and MockBadge for mock response", () => {
    useContextQuery.mockReturnValue({ ...noopMut, data: mockResult });

    render(<Query />);

    expect(screen.getByText("Current MRR is $2.4M.")).toBeInTheDocument();
    expect(screen.getByText(/Demo data/)).toBeInTheDocument();
  });

  it("renders cited components", () => {
    useContextQuery.mockReturnValue({ ...noopMut, data: mockResult });

    render(<Query />);

    expect(screen.getByText("Cited Components")).toBeInTheDocument();
    expect(screen.getByText("MRR")).toBeInTheDocument();
    expect(screen.getByText("$2.4M")).toBeInTheDocument();
    expect(screen.getByText("Revenue Model")).toBeInTheDocument();
  });

  it("renders source chips", () => {
    useContextQuery.mockReturnValue({ ...noopMut, data: mockResult });

    render(<Query />);

    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.getByText("Stripe")).toBeInTheDocument();
    expect(screen.getByText("Internal DB")).toBeInTheDocument();
  });
});

describe("Query — real response", () => {
  it("shows answer without MockBadge for real response", () => {
    const realResult = {
      question: "What is our MRR?",
      answer: "MRR is $3.1M as of this month.",
      confidence: 0.95,
      answeredAt: "2s ago",
      components: [],
      sources: [],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: realResult });

    render(<Query />);

    expect(screen.getByText("MRR is $3.1M as of this month.")).toBeInTheDocument();
    expect(screen.queryByText(/Demo data/)).not.toBeInTheDocument();
  });
});

describe("Query — object sources", () => {
  it("renders structured source objects with type and author", () => {
    const result = {
      question: "Test?",
      answer: "Answer.",
      confidence: 0.9,
      sources: [
        { type: "Slack", author: "alice", date: "2024-03-01" },
        { type: "Notion", url: "https://notion.so/page" },
      ],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    expect(screen.getByText("Slack")).toBeInTheDocument();
    expect(screen.getByText(/alice/)).toBeInTheDocument();
    expect(screen.getByText("Notion")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Notion" })).toHaveAttribute(
      "href",
      "https://notion.so/page",
    );
  });

  it("renders mixed string and object sources", () => {
    const result = {
      question: "Test?",
      answer: "Answer.",
      confidence: 0.9,
      sources: ["CSV export", { type: "Gong", author: "bob" }],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    expect(screen.getByText("CSV export")).toBeInTheDocument();
    expect(screen.getByText("Gong")).toBeInTheDocument();
    expect(screen.getByText(/bob/)).toBeInTheDocument();
  });
});

describe("Query — freshness badge", () => {
  it("shows freshness badge when present on result", () => {
    const result = {
      question: "Test?",
      answer: "Answer.",
      confidence: 0.9,
      freshness: "2 min ago",
      answeredAt: "just now",
      sources: [],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    expect(screen.getByText("2 min ago")).toBeInTheDocument();
  });

  it("does not show freshness badge when absent", () => {
    const result = {
      question: "Test?",
      answer: "Answer.",
      confidence: 0.9,
      answeredAt: "just now",
      sources: [],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    expect(screen.getByText("just now")).toBeInTheDocument();
    // No freshness badge rendered
    expect(screen.queryByText(/min ago/)).not.toBeInTheDocument();
  });
});

describe("Query — semantic freshness", () => {
  it("shows 'Current' with green styling for freshness=current", () => {
    const result = {
      question: "Test?",
      answer: "Answer.",
      confidence: 0.9,
      freshness: "current",
      sources: [],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    const badge = screen.getByText("Current");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/emerald/);
  });

  it("shows 'Possibly stale' with amber styling", () => {
    const result = {
      question: "Test?",
      answer: "Answer.",
      confidence: 0.9,
      freshness: "possibly_stale",
      sources: [],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    const badge = screen.getByText("Possibly stale");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/amber/);
  });

  it("shows 'Stale' with red styling", () => {
    const result = {
      question: "Test?",
      answer: "Answer.",
      confidence: 0.9,
      freshness: "stale",
      sources: [],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    const badge = screen.getByText("Stale");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/red/);
  });
});

describe("Query — empty answer (non-zero confidence)", () => {
  it("shows fallback message when answer is empty string", () => {
    const result = {
      question: "Unknown?",
      answer: "",
      confidence: 0.5,
      sources: ["some source"],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    expect(screen.getByText("No answer could be determined for this query.")).toBeInTheDocument();
  });

  it("shows fallback message when answer is null", () => {
    const result = {
      question: "Unknown?",
      answer: null,
      confidence: 0.5,
      sources: ["some source"],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    expect(screen.getByText("No answer could be determined for this query.")).toBeInTheDocument();
  });
});

describe("Query — no-match response", () => {
  it("shows dedicated no-match state for confidence=0 with no components/sources", () => {
    const result = {
      question: "What is our churn rate?",
      answer: "I could not find matching structured context for this question.",
      confidence: 0,
      components: [],
      sources: [],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    expect(screen.getByText("No grounded answer found")).toBeInTheDocument();
    expect(screen.getByText(/could not find matching/)).toBeInTheDocument();
    // Should NOT render like a normal answer card
    expect(screen.queryByText("Confidence")).not.toBeInTheDocument();
    expect(screen.queryByText("Cited Components")).not.toBeInTheDocument();
  });

  it("shows default no-match text when answer is empty", () => {
    const result = {
      question: "Unknown thing?",
      answer: "",
      confidence: 0,
      components: [],
      sources: [],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    expect(screen.getByText("No grounded answer found")).toBeInTheDocument();
    expect(screen.getByText(/does not contain enough structured context/)).toBeInTheDocument();
  });
});

describe("Query — real backend success response", () => {
  it("renders answer with confidence bar, freshness, components, and sources", () => {
    const result = {
      question: "What is our MRR?",
      answer: "Current MRR is $3.1M based on Stripe data.",
      confidence: 0.92,
      freshness: "current",
      answeredAt: "2s ago",
      components: [
        { id: "c1", name: "MRR", value: "$3.1M", model: "Revenue Model", confidence: 0.95, authority_source: "stripe", last_verified_at: "2026-03-29" },
      ],
      sources: [
        { type: "Stripe", url: "https://dashboard.stripe.com" },
        { type: "Internal DB", author: "system" },
      ],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    // Answer text
    expect(screen.getByText("Current MRR is $3.1M based on Stripe data.")).toBeInTheDocument();
    // Confidence
    expect(screen.getByText("92%")).toBeInTheDocument();
    // Freshness badge
    const badge = screen.getByText("Current");
    expect(badge).toBeInTheDocument();
    expect(badge.className).toMatch(/emerald/);
    // Components
    expect(screen.getByText("Cited Components")).toBeInTheDocument();
    expect(screen.getByText("MRR")).toBeInTheDocument();
    expect(screen.getByText("$3.1M")).toBeInTheDocument();
    // Component metadata
    expect(screen.getByText("95% confidence")).toBeInTheDocument();
    expect(screen.getByText("via stripe")).toBeInTheDocument();
    expect(screen.getByText(/verified/)).toBeInTheDocument();
    // Sources
    expect(screen.getByText("Sources")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Stripe" })).toHaveAttribute("href", "https://dashboard.stripe.com");
    expect(screen.getByText("Internal DB")).toBeInTheDocument();
    // No mock badge
    expect(screen.queryByText(/Demo data/)).not.toBeInTheDocument();
  });

  it("renders multiline causal answers as separate paragraphs", () => {
    const result = {
      question: "Why is MRR growing?",
      answer: "MRR is growing at 12% MoM.\nThis is driven by expansion revenue from existing customers.\nChurn remains low at 2%.",
      confidence: 0.88,
      freshness: "current",
      components: [],
      sources: [],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    expect(screen.getByText("MRR is growing at 12% MoM.")).toBeInTheDocument();
    expect(screen.getByText(/driven by expansion revenue/)).toBeInTheDocument();
    expect(screen.getByText(/Churn remains low/)).toBeInTheDocument();
  });

  it("omits component metadata line when fields are absent", () => {
    const result = {
      question: "Test?",
      answer: "Answer.",
      confidence: 0.9,
      components: [
        { id: "c1", name: "Metric", value: "100", model: "M1" },
      ],
      sources: [],
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: result });

    render(<Query />);

    expect(screen.getByText("Metric")).toBeInTheDocument();
    expect(screen.queryByText(/confidence$/)).not.toBeInTheDocument();
    expect(screen.queryByText(/^via /)).not.toBeInTheDocument();
    expect(screen.queryByText(/^verified /)).not.toBeInTheDocument();
  });
});

describe("Query — network failure mock fallback", () => {
  it("shows mock badge when response has _isMock flag", () => {
    const mockResult = {
      question: "What is our MRR?",
      answer: "Current MRR is $2.4M.",
      confidence: 0.92,
      answeredAt: "just now",
      components: [
        { id: "c1", name: "MRR", value: "$2.4M", model: "Revenue Model" },
      ],
      sources: ["Stripe"],
      _isMock: true,
    };
    useContextQuery.mockReturnValue({ ...noopMut, data: mockResult });

    render(<Query />);

    expect(screen.getByText("Current MRR is $2.4M.")).toBeInTheDocument();
    expect(screen.getByText(/Demo data/)).toBeInTheDocument();
  });
});

describe("Query — error state", () => {
  it("shows error message and retry button", () => {
    useContextQuery.mockReturnValue({
      ...noopMut,
      isError: true,
      error: { message: "Server returned 500" },
    });

    render(<Query />);

    expect(screen.getByText("Server returned 500")).toBeInTheDocument();
    expect(screen.getByText("Retry")).toBeInTheDocument();
  });

  it("retry button calls mutate with current input", async () => {
    const mutate = vi.fn();
    useContextQuery.mockReturnValue({
      ...noopMut,
      mutate,
      isError: true,
      error: { message: "Server error" },
    });

    render(<Query />);

    await userEvent.type(
      screen.getByPlaceholderText("Ask a question about your company data..."),
      "What is our MRR?",
    );
    await userEvent.click(screen.getByText("Retry"));

    expect(mutate).toHaveBeenCalledWith("What is our MRR?");
  });

  it("hides empty state when error is shown", () => {
    useContextQuery.mockReturnValue({
      ...noopMut,
      isError: true,
      error: { message: "fail" },
    });

    render(<Query />);

    expect(screen.queryByText("Ask a question to query your knowledge graph.")).not.toBeInTheDocument();
  });

  it("shows real 4xx/5xx errors without mock fallback", () => {
    useContextQuery.mockReturnValue({
      ...noopMut,
      isError: true,
      error: { message: "422 Unprocessable Entity", status: 422 },
    });

    render(<Query />);

    expect(screen.getByText("422 Unprocessable Entity")).toBeInTheDocument();
    expect(screen.queryByText(/Demo data/)).not.toBeInTheDocument();
  });
});
