import { render, screen } from "@testing-library/react";
import FundamentalsCard from "./fundamentals-card";

describe("FundamentalsCard", () => {
  it("renders placeholders when dataset is missing", () => {
    render(<FundamentalsCard fundamentals={null} quote={null} />);

    expect(screen.getByTestId("fundamentals-card-empty")).toBeInTheDocument();
  });

  it("displays all metrics with their units", () => {
    render(
      <FundamentalsCard
        fundamentals={{
          symbol: "NVDA",
          marketCap: 1_000_000_000_000,
          peRatio: 45.2,
          dividendYield: 0.006,
          week52High: 500,
          week52Low: 200,
        }}
        quote={{ price: 450, changePct: 0.0125, currency: "USD" }}
      />,
    );

    expect(screen.getByRole("heading", { name: /nvda/i })).toBeInTheDocument();
    const capLabel = screen.getByText(/capitalisation/i);
    expect((capLabel.nextElementSibling as HTMLElement).textContent).toContain("$");
    const yieldLabel = screen.getByText(/rendement dividende/i);
    expect((yieldLabel.nextElementSibling as HTMLElement).textContent).toContain("%");
  });

  it("handles partial fundamentals gracefully", () => {
    render(
      <FundamentalsCard
        fundamentals={{ symbol: "AAPL", marketCap: null }}
        quote={{ price: null, changePct: null }}
      />,
    );

    expect(screen.getByText(/cours : —/i)).toBeInTheDocument();
    const fallbackLabel = screen.getByText(/capitalisation/i);
    expect((fallbackLabel.nextElementSibling as HTMLElement).textContent).toContain("—");
  });
});
