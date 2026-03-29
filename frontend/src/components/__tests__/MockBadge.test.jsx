import { render, screen } from "@testing-library/react";
import MockBadge from "../MockBadge";

describe("MockBadge", () => {
  it("renders demo data label", () => {
    render(<MockBadge />);

    expect(screen.getByText(/Demo data/)).toBeInTheDocument();
  });
});
