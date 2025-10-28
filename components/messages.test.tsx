import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import Messages, { ChatArtifactBase, ChatMessage } from "./messages";

describe("Messages", () => {
  it("renders an empty state safely when lists are null", () => {
    render(<Messages messages={null} artifacts={null} />);
    expect(screen.queryAllByRole("article")).toHaveLength(0);
  });

  it("renders unknown artefacts with a fallback", () => {
    const messages: ChatMessage[] = [
      {
        id: "1",
        role: "assistant",
        content: "Here is something",
        artifacts: [
          { id: "a", type: "unsupported", title: "Résumé" },
        ],
      },
    ];

    render(<Messages messages={messages} />);

    expect(screen.getByTestId("artifact-fallback")).toBeInTheDocument();
  });

  it("renders finance chart artefacts with overlay toggles", () => {
    const artifact: ChatArtifactBase = {
      id: "chart-1",
      type: "finance:chart",
      data: {
        status: "ready",
        symbol: "BTCUSD",
        timeframe: "1D",
        rows: [
          { ts: 1_700_000_000_000, open: 10, high: 15, low: 9, close: 14, volume: 100 },
        ],
        range: {
          firstTs: 1_700_000_000_000,
          lastTs: 1_700_000_000_000,
          high: 15,
          low: 9,
          totalVolume: 100,
        },
        selected: {
          ts: 1_700_000_000_000,
          open: 10,
          high: 15,
          low: 9,
          close: 14,
          volume: 100,
          previousClose: 9,
          changeAbs: 5,
          changePct: 55.56,
          range: 6,
          body: 4,
          bodyPct: 44.44,
          upperWick: 1,
          lowerWick: 1,
          direction: "bullish",
        },
        details: [
          {
            ts: 1_700_000_000_000,
            open: 10,
            high: 15,
            low: 9,
            close: 14,
            volume: 100,
            previousClose: 9,
            changeAbs: 5,
            changePct: 55.56,
            range: 6,
            body: 4,
            bodyPct: 44.44,
            upperWick: 1,
            lowerWick: 1,
            direction: "bullish",
          },
        ],
        overlays: [
          {
            id: "sma-50",
            type: "sma",
            window: 50,
            points: [{ ts: 1_700_000_000_000, value: 12 }],
          },
          {
            id: "ema-21",
            type: "ema",
            window: 21,
            points: [{ ts: 1_700_000_000_000, value: 13 }],
          },
        ],
      },
    };

    render(<Messages messages={[]} artifacts={[artifact]} />);

    expect(screen.getByTestId("chart-artifact")).toBeInTheDocument();
    expect(screen.getByTestId("overlay-toggle-sma-50")).toBeInTheDocument();
    expect(screen.getByTestId("overlay-toggle-ema-21")).toBeInTheDocument();
  });

  it("renders finance backtest artefacts with the dedicated component", () => {
    const artifact: ChatArtifactBase = {
      id: "backtest-1",
      type: "finance:backtest_report",
      data: {
        symbol: "BTCUSD",
        timeframe: "1D",
        metrics: {
          totalReturn: 0.1,
          cagr: 0.05,
          maxDrawdown: -0.2,
          winRate: 0.55,
          sharpe: 1.2,
          profitFactor: 1.4,
        },
        equityCurve: [],
        trades: [],
      },
    };

    render(<Messages messages={[]} artifacts={[artifact]} />);

    expect(screen.getByTestId("finance-backtest-report")).toBeInTheDocument();
  });

  it("renders fundamentals artefacts", () => {
    const artifact: ChatArtifactBase = {
      id: "fundamentals-1",
      type: "finance:fundamentals",
      data: {
        symbol: "NVDA",
        marketCap: 100,
      },
    };

    render(<Messages messages={[]} artifacts={[artifact]} />);

    expect(screen.getByTestId("fundamentals-card")).toBeInTheDocument();
  });

  it("renders news artefacts with fallbacks", () => {
    const artifact: ChatArtifactBase = {
      id: "news-1",
      type: "finance:news",
      data: {
        symbol: "NVDA",
        items: [
          {
            id: "1",
            title: "", // intentionally blank to trigger fallback
            url: null,
            publishedAt: null,
          },
        ],
      },
    };

    render(<Messages messages={[]} artifacts={[artifact]} />);

    expect(screen.getByText(/titre indisponible/i)).toBeInTheDocument();
  });
});
