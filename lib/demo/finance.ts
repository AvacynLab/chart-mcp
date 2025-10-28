import type { ChatMessage } from "@components/messages";
import type { ChartArtifactResponse } from "@components/finance/ChartArtifact";
import type { BacktestReportArtifactData } from "@components/finance/backtest-report-artifact";
import type { FundamentalsSnapshot, QuoteSnapshot } from "@components/finance/fundamentals-card";
import type { NewsItemModel } from "@components/finance/news-list";

/**
 * Deterministic finance artefacts used by the chat demo and the Playwright
 * harness. Keeping the payloads centralised avoids the usual drift between the
 * backend fixtures, the UI, and the automated tests.
 */
interface FinanceDemoArtifacts {
  readonly chart: ChartArtifactResponse;
  readonly backtest: BacktestReportArtifactData;
  readonly fundamentals: FundamentalsSnapshot;
  readonly quote: QuoteSnapshot;
  readonly news: {
    readonly symbol: string;
    readonly items: readonly NewsItemModel[];
  };
}

/** Timestamp of the first OHLCV candle in the demo chart (UTC). */
export const FINANCE_DEMO_FIRST_CANDLE_TS = Date.UTC(2024, 0, 2);
/** Timestamp of the second OHLCV candle in the demo chart (UTC). */
export const FINANCE_DEMO_SECOND_CANDLE_TS = Date.UTC(2024, 0, 3);

/**
 * Base payload used to seed the deterministic finance artefacts. The `satisfies`
 * operator guarantees that any refactor of the shape required by the UI will be
 * caught at compile-time instead of silently breaking the runtime behaviour.
 */
const BASE_ARTIFACTS = {
  chart: {
    status: "ready",
    symbol: "BTCUSD",
    timeframe: "1d",
    rows: [
      {
        ts: FINANCE_DEMO_FIRST_CANDLE_TS,
        open: 42_000,
        high: 43_200,
        low: 41_500,
        close: 43_000,
        volume: 1_250,
      },
      {
        ts: FINANCE_DEMO_SECOND_CANDLE_TS,
        open: 43_000,
        high: 44_000,
        low: 42_500,
        close: 43_250,
        volume: 1_100,
      },
    ],
    range: {
      firstTs: FINANCE_DEMO_FIRST_CANDLE_TS,
      lastTs: FINANCE_DEMO_SECOND_CANDLE_TS,
      high: 44_000,
      low: 41_500,
      totalVolume: 2_350,
    },
    selected: {
      ts: FINANCE_DEMO_SECOND_CANDLE_TS,
      open: 43_000,
      high: 44_000,
      low: 42_500,
      close: 43_250,
      volume: 1_100,
      previousClose: 43_000,
      changeAbs: 250,
      changePct: 0.581395,
      range: 1_500,
      body: 250,
      bodyPct: 0.581395,
      upperWick: 750,
      lowerWick: 500,
      direction: "bullish",
    },
    details: [
      {
        ts: FINANCE_DEMO_FIRST_CANDLE_TS,
        open: 42_000,
        high: 43_200,
        low: 41_500,
        close: 43_000,
        volume: 1_250,
        previousClose: 41_000,
        changeAbs: 2_000,
        changePct: 4.878049,
        range: 1_700,
        body: 1_000,
        bodyPct: 2.439024,
        upperWick: 200,
        lowerWick: 500,
        direction: "bullish",
      },
      {
        ts: FINANCE_DEMO_SECOND_CANDLE_TS,
        open: 43_000,
        high: 44_000,
        low: 42_500,
        close: 43_250,
        volume: 1_100,
        previousClose: 43_000,
        changeAbs: 250,
        changePct: 0.581395,
        range: 1_500,
        body: 250,
        bodyPct: 0.581395,
        upperWick: 750,
        lowerWick: 500,
        direction: "bullish",
      },
    ],
    overlays: [
      {
        id: "sma-50",
        type: "sma",
        window: 50,
        points: [
          { ts: FINANCE_DEMO_FIRST_CANDLE_TS, value: 42_500 },
          { ts: FINANCE_DEMO_SECOND_CANDLE_TS, value: 42_750 },
        ],
      },
      {
        id: "sma-200",
        type: "sma",
        window: 200,
        points: [
          { ts: FINANCE_DEMO_FIRST_CANDLE_TS, value: 41_000 },
          { ts: FINANCE_DEMO_SECOND_CANDLE_TS, value: 41_100 },
        ],
      },
      {
        id: "ema-21",
        type: "ema",
        window: 21,
        points: [
          { ts: FINANCE_DEMO_FIRST_CANDLE_TS, value: 42_800 },
          { ts: FINANCE_DEMO_SECOND_CANDLE_TS, value: 43_150 },
        ],
      },
    ],
  },
  backtest: {
    symbol: "AAPL",
    timeframe: "1d",
    metrics: {
      totalReturn: 0.75,
      cagr: 0.18,
      maxDrawdown: -0.12,
      winRate: 0.62,
      sharpe: 1.5,
      profitFactor: 1.9,
    },
    equityCurve: [
      { ts: 1_609_459_200, equity: 100_000 },
      { ts: 1_640_995_200, equity: 145_000 },
      { ts: 1_672_531_200, equity: 175_000 },
    ],
    trades: [
      {
        entryTs: 1_612_137_600,
        exitTs: 1_614_729_600,
        entryPrice: 320,
        exitPrice: 340,
        returnPct: 0.0625,
      },
      {
        entryTs: 1_622_505_600,
        exitTs: 1_625_097_600,
        entryPrice: 335,
        exitPrice: 330,
        returnPct: -0.0149,
      },
    ],
  },
  fundamentals: {
    symbol: "NVDA",
    marketCap: 1_200_000_000_000,
    peRatio: 35.4,
    dividendYield: 0.007,
    week52High: 500,
    week52Low: 200,
  },
  quote: {
    price: 420.45,
    changePct: 0.012,
    currency: "USD",
  },
  news: {
    symbol: "NVDA",
    items: [
      {
        id: "article-1",
        title: "NVDA dépasse les attentes trimestrielles",
        url: "https://example.com/nvda-earnings",
        publishedAt: "2024-01-02T09:00:00Z",
      },
      {
        id: "article-2",
        title: "Le GPU Blackwell gagne du terrain",
        url: "https://example.com/blackwell",
        publishedAt: "2024-01-02T13:30:00Z",
      },
      {
        id: "article-3",
        title: "Partenariat stratégique avec un hyperscaler",
        url: "https://example.com/hyperscaler",
        publishedAt: "2024-01-03T08:15:00Z",
      },
    ],
  },
} satisfies FinanceDemoArtifacts;

function cloneArtifacts(): FinanceDemoArtifacts {
  if (typeof structuredClone === "function") {
    return structuredClone(BASE_ARTIFACTS);
  }
  return JSON.parse(JSON.stringify(BASE_ARTIFACTS)) as FinanceDemoArtifacts;
}

/**
 * Retrieve a deep-cloned copy of the finance demo artefacts.
 */
export function getFinanceDemoArtifacts(): FinanceDemoArtifacts {
  return cloneArtifacts();
}

/**
 * Build the initial chat history displayed on the protected `/chat` route.
 * The assistant message mirrors the user scenario exercised in the end-to-end
 * suite: requesting the BTCUSD chart alongside the SMA/EMA overlays and the
 * supporting finance reports.
 */
export function getFinanceDemoMessages(): ChatMessage[] {
  const { chart, backtest, fundamentals, quote, news } = cloneArtifacts();

  const assistantMessage: ChatMessage = {
    id: "finance-demo-assistant",
    role: "assistant",
    content: "Voici le point complet sur BTCUSD et NVDA comme demandé.",
    artifacts: [
      {
        id: "chart-btcusd",
        type: "finance:chart",
        title: "BTCUSD 1D",
        data: chart,
      },
      {
        id: "backtest-aapl",
        type: "finance:backtest_report",
        title: "Backtest SMA 50/200 AAPL",
        data: backtest,
      },
      {
        id: "fundamentals-nvda",
        type: "finance:fundamentals",
        title: "Bilan NVDA",
        data: {
          fundamentals,
          quote,
        },
      },
      {
        id: "news-nvda",
        type: "finance:news",
        title: "Actualités NVDA",
        data: news,
      },
    ],
  };

  return [assistantMessage];
}
