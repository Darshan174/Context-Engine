import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import Models from "../Models";

vi.mock("../../api/hooks", () => ({
  useModels: vi.fn(),
  useCreateModel: vi.fn(),
}));

import { useModels, useCreateModel } from "../../api/hooks";

const defaultCreateMut = {
  mutate: vi.fn(),
  isPending: false,
  isError: false,
  error: null,
};

function renderModels() {
  return render(
    <MemoryRouter>
      <Models />
    </MemoryRouter>,
  );
}

beforeEach(() => {
  vi.clearAllMocks();
  useCreateModel.mockReturnValue(defaultCreateMut);
});

describe("Models — create flow", () => {
  it("shows loading state", () => {
    useModels.mockReturnValue({
      isLoading: true,
      isError: false,
      data: undefined,
      refetch: vi.fn(),
    });

    renderModels();
    expect(screen.getByText("Loading...")).toBeInTheDocument();
  });

  it("shows empty state when no models exist", () => {
    useModels.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
      refetch: vi.fn(),
    });

    renderModels();
    expect(screen.getByText("No models yet. Create one to get started.")).toBeInTheDocument();
    expect(screen.getByText("Self-host modeling flow")).toBeInTheDocument();
    expect(screen.getByText(/usually become useful after you sync sources/i)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Open sources" })).toHaveAttribute("href", "/app/sources");
  });

  it("shows model cards when models exist", () => {
    useModels.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [
        { id: "m1", name: "Revenue", description: "Revenue model", status: "active", updated_at: "2024-01-01" },
        { id: "m2", name: "Costs", description: "Cost model", status: "draft", updated_at: "2024-01-02" },
      ],
      refetch: vi.fn(),
    });

    renderModels();
    expect(screen.getByText("Revenue")).toBeInTheDocument();
    expect(screen.getByText("Costs")).toBeInTheDocument();
  });

  it("opens create form on + New Model click", async () => {
    useModels.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
      refetch: vi.fn(),
    });

    renderModels();

    await userEvent.click(screen.getByText("+ New Model"));

    expect(screen.getByText("Create a new model")).toBeInTheDocument();
    expect(screen.getByPlaceholderText("e.g. Q1 Revenue Model")).toBeInTheDocument();
  });

  it("submits create model form", async () => {
    const mutate = vi.fn();
    useCreateModel.mockReturnValue({ ...defaultCreateMut, mutate });
    useModels.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
      refetch: vi.fn(),
    });

    renderModels();

    await userEvent.click(screen.getByText("+ New Model"));
    await userEvent.type(screen.getByPlaceholderText("e.g. Q1 Revenue Model"), "Revenue Model");
    await userEvent.type(screen.getByPlaceholderText("What does this model track?"), "Tracks revenue");
    await userEvent.click(screen.getByText("Create"));

    expect(mutate).toHaveBeenCalledWith(
      { name: "Revenue Model", description: "Tracks revenue" },
      expect.objectContaining({ onSuccess: expect.any(Function) }),
    );
  });

  it("disables Create button when name is empty", async () => {
    useModels.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
      refetch: vi.fn(),
    });

    renderModels();

    await userEvent.click(screen.getByText("+ New Model"));

    expect(screen.getByText("Create")).toBeDisabled();
  });

  it("closes form on Cancel", async () => {
    useModels.mockReturnValue({
      isLoading: false,
      isError: false,
      data: [],
      refetch: vi.fn(),
    });

    renderModels();

    await userEvent.click(screen.getByText("+ New Model"));
    expect(screen.getByText("Create a new model")).toBeInTheDocument();

    await userEvent.click(screen.getByText("Cancel"));
    expect(screen.queryByText("Create a new model")).not.toBeInTheDocument();
  });
});
