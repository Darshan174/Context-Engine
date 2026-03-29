import { render, screen } from "@testing-library/react";
import RelationshipsPanel from "../RelationshipsPanel";

vi.mock("../../api/hooks", () => ({
  useModelRelationships: vi.fn(),
  useCreateRelationship: vi.fn(),
}));

import { useModelRelationships, useCreateRelationship } from "../../api/hooks";

const localComponents = [
  { id: "comp-a", name: "MRR" },
  { id: "comp-b", name: "Churn Rate" },
];

const defaultRelQuery = {
  data: [],
  isLoading: false,
  isError: false,
  refetch: vi.fn(),
};

beforeEach(() => {
  vi.clearAllMocks();
  useCreateRelationship.mockReturnValue({
    mutate: vi.fn(),
    isPending: false,
    isError: false,
  });
});

describe("RelationshipsPanel — name resolution", () => {
  it("uses inline names from the relationship response", () => {
    useModelRelationships.mockReturnValue({
      ...defaultRelQuery,
      data: [
        {
          id: "rel-1",
          source_component_id: "comp-a",
          target_component_id: "cross-1",
          source_component_name: "MRR",
          target_component_name: "External Revenue",
          relationship_type: "enables",
          sentiment: "positive",
          confidence: 0.9,
        },
      ],
    });

    render(
      <RelationshipsPanel modelId="m1" components={localComponents} isBackendData />,
    );

    expect(screen.getByText("MRR")).toBeInTheDocument();
    expect(screen.getByText("External Revenue")).toBeInTheDocument();
  });

  it("falls back to componentMap when response names are missing", () => {
    useModelRelationships.mockReturnValue({
      ...defaultRelQuery,
      data: [
        {
          id: "rel-2",
          source_component_id: "comp-a",
          target_component_id: "comp-b",
          relationship_type: "depends_on",
          sentiment: "neutral",
          confidence: 0.85,
        },
      ],
    });

    render(
      <RelationshipsPanel modelId="m1" components={localComponents} isBackendData />,
    );

    expect(screen.getByText("MRR")).toBeInTheDocument();
    expect(screen.getByText("Churn Rate")).toBeInTheDocument();
  });

  it("falls back to shortId when both response names and componentMap miss", () => {
    const crossId = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee";

    useModelRelationships.mockReturnValue({
      ...defaultRelQuery,
      data: [
        {
          id: "rel-3",
          source_component_id: "comp-a",
          target_component_id: crossId,
          relationship_type: "related_to",
          sentiment: "neutral",
          confidence: 0.7,
        },
      ],
    });

    render(
      <RelationshipsPanel modelId="m1" components={localComponents} isBackendData />,
    );

    expect(screen.getByText("MRR")).toBeInTheDocument();
    expect(screen.getByText("aaaaaaaa...")).toBeInTheDocument();
  });

  it("prefers response names over componentMap", () => {
    useModelRelationships.mockReturnValue({
      ...defaultRelQuery,
      data: [
        {
          id: "rel-4",
          source_component_id: "comp-a",
          target_component_id: "comp-b",
          source_component_name: "Monthly Recurring Revenue",
          target_component_name: "Customer Churn",
          relationship_type: "blocked_by",
          sentiment: "negative",
          confidence: 0.6,
        },
      ],
    });

    render(
      <RelationshipsPanel modelId="m1" components={localComponents} isBackendData />,
    );

    // Response names win even though both IDs are in the local component list
    expect(screen.getByText("Monthly Recurring Revenue")).toBeInTheDocument();
    expect(screen.getByText("Customer Churn")).toBeInTheDocument();
    expect(screen.queryByText("MRR")).not.toBeInTheDocument();
  });
});
