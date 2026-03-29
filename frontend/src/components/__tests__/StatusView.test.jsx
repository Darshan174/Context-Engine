import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import StatusView from "../StatusView";

describe("StatusView", () => {
  it("shows loading spinner", () => {
    render(<StatusView query={{ isLoading: true, isError: false }} />);

    expect(screen.getByText("Loading...")).toBeInTheDocument();
    expect(screen.getByRole("status")).toBeInTheDocument();
  });

  it("shows error with message and retry button", async () => {
    const refetch = vi.fn();
    render(
      <StatusView
        query={{
          isLoading: false,
          isError: true,
          error: { message: "Connection refused" },
          refetch,
        }}
      />,
    );

    expect(screen.getByRole("alert")).toBeInTheDocument();
    expect(screen.getByText("Failed to load")).toBeInTheDocument();
    expect(screen.getByText("Connection refused")).toBeInTheDocument();

    await userEvent.click(screen.getByText("Retry"));
    expect(refetch).toHaveBeenCalled();
  });

  it("shows default error message when error.message is absent", () => {
    render(
      <StatusView
        query={{ isLoading: false, isError: true, error: {}, refetch: vi.fn() }}
      />,
    );

    expect(screen.getByText("Something went wrong.")).toBeInTheDocument();
  });

  it("shows empty state for null data", () => {
    render(
      <StatusView
        query={{ isLoading: false, isError: false, data: null }}
        empty="Nothing here."
      />,
    );

    expect(screen.getByText("Nothing here.")).toBeInTheDocument();
  });

  it("shows empty state for empty array", () => {
    render(
      <StatusView
        query={{ isLoading: false, isError: false, data: [] }}
        empty="No items."
      />,
    );

    expect(screen.getByText("No items.")).toBeInTheDocument();
  });

  it("shows empty state for empty object", () => {
    render(
      <StatusView
        query={{ isLoading: false, isError: false, data: {} }}
      />,
    );

    expect(screen.getByText("Nothing here yet.")).toBeInTheDocument();
  });

  it("returns null when data is present", () => {
    const { container } = render(
      <StatusView
        query={{ isLoading: false, isError: false, data: [{ id: 1 }] }}
      />,
    );

    expect(container.innerHTML).toBe("");
  });
});
