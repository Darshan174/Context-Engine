import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter, Routes, Route } from "react-router-dom";
import ModelDetail from "../ModelDetail";

vi.mock("../../api/hooks", () => ({
  useComponentSources: vi.fn(),
  useModel: vi.fn(),
  useCreateComponent: vi.fn(),
  useUpdateComponent: vi.fn(),
  useDeleteComponent: vi.fn(),
}));

vi.mock("../../components/RelationshipsPanel", () => ({
  default: () => <div data-testid="relationships-panel" />,
}));

import {
  useComponentSources,
  useModel,
  useCreateComponent,
  useUpdateComponent,
  useDeleteComponent,
} from "../../api/hooks";

const noopMut = { mutate: vi.fn(), isPending: false, isError: false, error: null };

const backendModel = {
  id: "model-1",
  name: "Revenue Model",
  description: "Tracks revenue",
  workspace_id: "ws-1",
  updated_at: "2024-01-01T00:00:00Z",
  components: [
    {
      id: "comp-1",
      name: "MRR",
      value: "$2.4M",
      confidence: 0.95,
      last_verified_at: "2024-01-01T00:00:00Z",
      authority_source: "Stripe",
      authority_weight: 0.92,
      reviewStatus: "needs_review",
      reviewItemId: "rq1",
      reviewSummary: "Finance still needs to confirm the month-end adjustment.",
      decisionHistory: [
        {
          id: "rqd1",
          previousStatus: null,
          newStatus: "needs_review",
          actorType: "system",
          note: "Conflict generated automatically during ingestion.",
          createdAt: "2024-01-01T01:00:00Z",
        },
      ],
      sourceDocuments: [
        {
          id: "sd5",
          label: "#finance revenue decision",
          connectorType: "slack",
          author: "Alice",
          extractionContext: "Extracted from finance thread",
          extractorName: "Structured extractor",
          extractorSchemaVersion: "3",
        },
      ],
    },
    {
      id: "comp-2",
      name: "Churn Rate",
      value: "3.2%",
      confidence: 0.8,
      last_verified_at: null,
      authority_source: null,
      reviewStatus: "superseded",
      reviewItemId: "rq4",
      temporalState: "historical",
    },
  ],
};

const mockModel = {
  name: "Mock Model",
  description: "Mock description",
  lastUpdated: "Jan 1, 2024",
  components: [
    { id: "mock-1", name: "Mock Metric", value: "100", confidence: 0.9, freshness: "2d ago", sources: ["CSV"] },
  ],
};

function renderDetail(modelId = "model-1") {
  return render(
    <MemoryRouter initialEntries={[`/model/${modelId}`]}>
      <Routes>
        <Route path="/model/:modelId" element={<ModelDetail />} />
      </Routes>
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useComponentSources.mockReturnValue({ data: [], isLoading: false, isError: false });
  useCreateComponent.mockReturnValue(noopMut);
  useUpdateComponent.mockReturnValue(noopMut);
  useDeleteComponent.mockReturnValue(noopMut);
});

describe("ModelDetail", () => {
  it("shows loading state", () => {
    useModel.mockReturnValue({ isLoading: true, isError: false, data: undefined, refetch: vi.fn() });
    renderDetail();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("renders model header and components", () => {
    useModel.mockReturnValue({ isLoading: false, isError: false, data: backendModel, refetch: vi.fn() });
    renderDetail();
    expect(screen.getByText("Revenue Model")).toBeInTheDocument();
    expect(screen.getByText("MRR")).toBeInTheDocument();
    expect(screen.getByText("$2.4M")).toBeInTheDocument();
    expect(screen.getByText("Churn Rate")).toBeInTheDocument();
  });

  it("renders source-backed evidence links when component provenance exists", () => {
    useModel.mockReturnValue({ isLoading: false, isError: false, data: backendModel, refetch: vi.fn() });
    renderDetail();

    expect(screen.getByText("Current components")).toBeInTheDocument();
    expect(screen.getAllByText("Historical context").length).toBeGreaterThan(0);
    expect(screen.getByText(/superseded facts are separated below/i)).toBeInTheDocument();
    expect(screen.getByText("Evidence")).toBeInTheDocument();
    expect(screen.getByText("Needs review")).toBeInTheDocument();
    const reviewLinks = screen.getAllByRole("link", { name: "Open review item" });
    expect(reviewLinks.some((link) => link.getAttribute("href") === "/app/review/rq1")).toBe(true);
    expect(screen.getByRole("link", { name: /finance revenue decision/i })).toHaveAttribute(
      "href",
      "/app/sources/sd5",
    );
    expect(screen.getByText("Author: Alice")).toBeInTheDocument();
    expect(screen.getByText("Extracted from finance thread")).toBeInTheDocument();
    expect(screen.getByText("Extracted by Structured extractor · schema v3")).toBeInTheDocument();
    expect(screen.getByText("Authority weight 92%")).toBeInTheDocument();
    expect(screen.getByText("Review history")).toBeInTheDocument();
    expect(screen.getByText("Marked needs review")).toBeInTheDocument();
    expect(screen.getByText("Conflict generated automatically during ingestion.")).toBeInTheDocument();
  });

  it("loads evidence from the component sources endpoint when inline provenance is absent", () => {
    useComponentSources.mockImplementation((componentId) => ({
      data:
        componentId === "comp-1"
          ? [
              {
                id: "sd6",
                label: "Finance signoff note",
                connectorType: "notion",
                author: "CFO",
                extractionContext: "Extracted from approval note",
                extractorKind: "llm",
                extractorSchemaVersion: "2",
              },
            ]
          : [],
      isLoading: false,
      isError: false,
    }));
    useModel.mockReturnValue({
      isLoading: false,
      isError: false,
      data: {
        ...backendModel,
        components: backendModel.components.map((component) =>
          component.id === "comp-1" ? { ...component, sourceDocuments: [] } : component,
        ),
      },
      refetch: vi.fn(),
    });

    renderDetail();

    expect(screen.getByRole("link", { name: /Finance signoff note/i })).toHaveAttribute(
      "href",
      "/app/sources/sd6",
    );
    expect(screen.getByText("Author: CFO")).toBeInTheDocument();
    expect(screen.getByText("Extracted from approval note")).toBeInTheDocument();
    expect(screen.getByText("Extracted by llm · schema v2")).toBeInTheDocument();
  });

  it("shows Edit/Delete buttons for backend data", () => {
    useModel.mockReturnValue({ isLoading: false, isError: false, data: backendModel, refetch: vi.fn() });
    renderDetail();
    expect(screen.getAllByText("Edit")).toHaveLength(2);
    expect(screen.getAllByText("Delete")).toHaveLength(2);
  });

  it("hides Edit/Delete and Add Component for mock data", () => {
    useModel.mockReturnValue({ isLoading: false, isError: false, data: mockModel, refetch: vi.fn() });
    renderDetail();
    expect(screen.queryByText("Edit")).not.toBeInTheDocument();
    expect(screen.queryByText("Delete")).not.toBeInTheDocument();
    expect(screen.queryByText("+ Add Component")).not.toBeInTheDocument();
  });

  it("shows + Add Component button for backend data", () => {
    useModel.mockReturnValue({ isLoading: false, isError: false, data: backendModel, refetch: vi.fn() });
    renderDetail();
    expect(screen.getByText("+ Add Component")).toBeInTheDocument();
  });
});

describe("ModelDetail — edit flow", () => {
  beforeEach(() => {
    useModel.mockReturnValue({ isLoading: false, isError: false, data: backendModel, refetch: vi.fn() });
  });

  it("enters edit mode with pre-filled values", async () => {
    renderDetail();

    const editButtons = screen.getAllByText("Edit");
    await userEvent.click(editButtons[0]);

    expect(screen.getByDisplayValue("MRR")).toBeInTheDocument();
    expect(screen.getByDisplayValue("$2.4M")).toBeInTheDocument();
    expect(screen.getByDisplayValue("0.95")).toBeInTheDocument();
    expect(screen.getByDisplayValue("Stripe")).toBeInTheDocument();
  });

  it("calls update mutation on Save", async () => {
    const mutate = vi.fn();
    useUpdateComponent.mockReturnValue({ ...noopMut, mutate });
    renderDetail();

    await userEvent.click(screen.getAllByText("Edit")[0]);

    const valueInput = screen.getByDisplayValue("$2.4M");
    await userEvent.clear(valueInput);
    await userEvent.type(valueInput, "$3.0M");

    await userEvent.click(screen.getByText("Save"));

    expect(mutate).toHaveBeenCalledWith(
      expect.objectContaining({ componentId: "comp-1", name: "MRR", value: "$3.0M" }),
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it("cancels edit mode without saving", async () => {
    renderDetail();

    await userEvent.click(screen.getAllByText("Edit")[0]);
    expect(screen.getByDisplayValue("MRR")).toBeInTheDocument();

    await userEvent.click(screen.getByText("Cancel"));

    expect(screen.queryByDisplayValue("MRR")).not.toBeInTheDocument();
    expect(screen.getByText("MRR")).toBeInTheDocument();
  });
});

describe("ModelDetail — delete flow", () => {
  beforeEach(() => {
    useModel.mockReturnValue({ isLoading: false, isError: false, data: backendModel, refetch: vi.fn() });
  });

  it("shows delete confirmation", async () => {
    renderDetail();

    await userEvent.click(screen.getAllByText("Delete")[0]);

    expect(screen.getByText(/Delete.*MRR/)).toBeInTheDocument();
    expect(screen.getByText("This action cannot be undone.")).toBeInTheDocument();
    expect(screen.getByText("Yes, delete")).toBeInTheDocument();
  });

  it("calls delete mutation on confirm", async () => {
    const mutate = vi.fn();
    useDeleteComponent.mockReturnValue({ ...noopMut, mutate });
    renderDetail();

    await userEvent.click(screen.getAllByText("Delete")[0]);
    await userEvent.click(screen.getByText("Yes, delete"));

    expect(mutate).toHaveBeenCalledWith("comp-1", expect.objectContaining({ onSuccess: expect.any(Function) }));
  });

  it("cancels delete confirmation", async () => {
    renderDetail();

    await userEvent.click(screen.getAllByText("Delete")[0]);
    expect(screen.getByText(/Delete.*MRR/)).toBeInTheDocument();

    await userEvent.click(screen.getByText("Cancel"));

    expect(screen.queryByText(/Delete.*MRR/)).not.toBeInTheDocument();
    expect(screen.getByText("MRR")).toBeInTheDocument();
  });
});
