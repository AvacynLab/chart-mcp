/**
 * Shared finance stream fixture used to drive hermetic Playwright flows.
 *
 * The dataset mirrors the sequence of events emitted by the backend
 * `/stream/analysis` endpoint so both the mocked API route exposed under
 * `app/api/test-backend/stream/analysis` and the Playwright-specific
 * shortcuts in `artifacts/finance/server.ts` can remain in sync.
 */
export type FinanceStreamEvent = {
  event: string;
  payload?: Record<string, unknown>;
};

export const FINANCE_STREAM_FIXTURE: readonly FinanceStreamEvent[] = [
  {
    event: "step:start",
    payload: {
      step: "bootstrap",
      description: "Initialisation du flux finance",
    },
  },
  {
    event: "ohlcv",
    payload: {
      symbol: "BTCUSDT",
      timeframe: "1h",
      rows: [
        { ts: 1_700_000_000_000, open: 68_500, high: 69_200, low: 68_100, close: 69_050, volume: 1_250 },
        { ts: 1_700_000_360_000, open: 69_050, high: 69_600, low: 68_900, close: 69_480, volume: 1_480 },
      ],
    },
  },
  {
    event: "metric",
    payload: {
      name: "latency_ms",
      value: 875,
    },
  },
  {
    event: "result_partial",
    payload: {
      step: "analysis",
      status: "running",
      ohlcv: { points: 2 },
      indicators: {
        overlays: [{ id: "ema:21", window: 21, latest: 69_120 }],
      },
      levels: {
        support: [
          {
            price: 68_700,
            strength: 0.66,
            label: "fort",
            tsRange: [1_700_000_000_000, 1_700_000_360_000],
          },
        ],
      },
      patterns: {
        bearish: [
          {
            name: "head_shoulders",
            score: 0.74,
            confidence: 0.69,
            startTs: 1_700_000_000_000,
            endTs: 1_700_000_360_000,
            points: [
              [1_700_000_000_000, 69_200],
              [1_700_000_180_000, 68_600],
              [1_700_000_360_000, 69_480],
            ],
          },
        ],
      },
    },
  },
  {
    event: "indicators",
    payload: {
      overlays: [
        {
          id: "ema:21",
          window: 21,
          points: [
            { ts: 1_700_000_000_000, value: 68_900 },
            { ts: 1_700_000_360_000, value: 69_150 },
          ],
        },
      ],
    },
  },
  {
    event: "levels",
    payload: {
      support: [
        {
          price: 68_700,
          strength: 0.66,
          label: "fort",
          tsRange: [1_700_000_000_000, 1_700_000_360_000],
        },
      ],
    },
  },
  {
    event: "patterns",
    payload: {
      bearish: [
        {
          name: "head_shoulders",
          score: 0.74,
          confidence: 0.69,
          startTs: 1_700_000_000_000,
          endTs: 1_700_000_360_000,
          points: [
            [1_700_000_000_000, 69_200],
            [1_700_000_180_000, 68_600],
            [1_700_000_360_000, 69_480],
          ],
        },
      ],
    },
  },
  {
    event: "step:end",
    payload: {
      step: "analysis",
      status: "completed",
    },
  },
  {
    event: "token",
    payload: {
      text: "Analyse complète sur BTC/USDT. ",
    },
  },
  {
    event: "result_final",
    payload: {
      summary: "Analyse complète sur BTC/USDT.",
      levels: {
        support: [
          {
            price: 68_700,
            strength: 0.66,
            label: "fort",
            tsRange: [1_700_000_000_000, 1_700_000_360_000],
          },
        ],
      },
      patterns: {
        bearish: [
          {
            name: "head_shoulders",
            score: 0.74,
            confidence: 0.69,
            startTs: 1_700_000_000_000,
            endTs: 1_700_000_360_000,
            points: [
              [1_700_000_000_000, 69_200],
              [1_700_000_180_000, 68_600],
              [1_700_000_360_000, 69_480],
            ],
          },
        ],
      },
    },
  },
  {
    event: "done",
    payload: {
      status: "ok",
    },
  },
] as const;

/**
 * Serialise a finance event into an SSE chunk body.
 */
export function buildFinanceEventChunk(event: FinanceStreamEvent): string {
  const payload = event.payload ?? {};
  return `event: ${event.event}\ndata: ${JSON.stringify({ payload })}`;
}
