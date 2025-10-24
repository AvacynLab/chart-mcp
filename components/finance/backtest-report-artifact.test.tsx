import { render, screen, waitFor, within } from "@testing-library/react";
import { act } from "react";
import userEvent from "@testing-library/user-event";
import BacktestReportArtifact, {
  type BacktestReportArtifactData,
  type BacktestRetestParams,
} from "./backtest-report-artifact";

function buildArtifact(partial: Partial<BacktestReportArtifactData> = {}): BacktestReportArtifactData {
  return {
    symbol: "BTCUSD",
    timeframe: "1D",
    metrics: {
      totalReturn: 0.42,
      cagr: 0.21,
      maxDrawdown: -0.12,
      winRate: 0.55,
      sharpe: 1.8,
      profitFactor: 1.6,
    },
    equityCurve: [
      { ts: 1_700_000_000, equity: 100_000 },
      { ts: 1_700_086_400, equity: 112_000 },
    ],
    trades: [
      {
        entryTs: 1_700_000_000,
        exitTs: 1_700_086_400,
        entryPrice: 20_000,
        exitPrice: 22_400,
        returnPct: 0.12,
      },
    ],
    ...partial,
  };
}

describe("BacktestReportArtifact", () => {
  it("renders accessible metric table", () => {
    render(<BacktestReportArtifact artifact={buildArtifact()} />);

    const table = screen.getByRole("table", { name: /métriques principales/i });
    expect(table).toBeInTheDocument();

    const columnHeaders = within(table).getAllByRole("columnheader");
    expect(columnHeaders).toHaveLength(2);
    expect(columnHeaders[0]).toHaveTextContent(/indicateur/i);
    expect(columnHeaders[1]).toHaveTextContent(/valeur/i);
  });

  it("validates retest parameters before invoking callback", async () => {
    const onRetest = vi.fn();
    render(<BacktestReportArtifact artifact={buildArtifact()} onRetest={onRetest} />);

    await act(async () => {
      await userEvent.clear(screen.getByLabelText(/fenêtre rapide/i));
      await userEvent.type(screen.getByLabelText(/fenêtre rapide/i), "200");
      await userEvent.clear(screen.getByLabelText(/fenêtre lente/i));
      await userEvent.type(screen.getByLabelText(/fenêtre lente/i), "200");
      await userEvent.click(screen.getByTestId("retest-button"));
    });

    expect(onRetest).not.toHaveBeenCalled();
    const errorMessage = await screen.findByTestId("retest-error");
    expect(errorMessage).toHaveTextContent(
      /strictement inférieure/i,
    );
  });

  it("passes coerced parameters to the retest handler", async () => {
    const onRetest = vi.fn<(params: BacktestRetestParams) => void>();
    render(
      <BacktestReportArtifact
        artifact={buildArtifact({ trades: [] })}
        onRetest={onRetest}
        defaultParams={{ fastWindow: 20, slowWindow: 60, feesBps: 5, slippageBps: 10 }}
      />,
    );

    await act(async () => {
      await userEvent.clear(screen.getByLabelText(/fenêtre rapide/i));
      await userEvent.type(screen.getByLabelText(/fenêtre rapide/i), "25");
      await userEvent.clear(screen.getByLabelText(/fenêtre lente/i));
      await userEvent.type(screen.getByLabelText(/fenêtre lente/i), "80");
      await userEvent.clear(screen.getByLabelText(/frais/i));
      await userEvent.type(screen.getByLabelText(/frais/i), "12.5");
      await userEvent.clear(screen.getByLabelText(/slippage/i));
      await userEvent.type(screen.getByLabelText(/slippage/i), "3.2");
      await userEvent.click(screen.getByTestId("retest-button"));
    });

    await waitFor(() => {
      expect(onRetest).toHaveBeenCalledWith({
        fastWindow: 25,
        slowWindow: 80,
        feesBps: 12.5,
        slippageBps: 3.2,
      });
    });
  });

  it("falls back to an empty trades message", () => {
    render(<BacktestReportArtifact artifact={buildArtifact({ trades: [] })} />);

    expect(screen.getByText(/aucun trade exécuté/i)).toBeInTheDocument();
  });
});
