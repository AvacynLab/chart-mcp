import { act, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import ChartAnalysis, { type EventSourceFactory, type EventSourceLike } from "./chart-analysis";

type ListenerRegistry = Record<string, Set<(event: MessageEvent<string>) => void>>;

class MockEventSource implements EventSourceLike {
  public static lastInstance: MockEventSource | null = null;
  public readonly url: string;
  private readonly listeners: ListenerRegistry;
  public closed = false;

  constructor(url: string) {
    this.url = url;
    this.listeners = {} as ListenerRegistry;
    MockEventSource.lastInstance = this;
  }

  public addEventListener(type: string, listener: (event: MessageEvent<string>) => void): void {
    if (!this.listeners[type]) {
      this.listeners[type] = new Set();
    }
    this.listeners[type].add(listener);
  }

  public dispatch(type: string, payload: unknown): void {
    const listeners = this.listeners[type];
    if (!listeners) {
      return;
    }
    const event = { data: JSON.stringify(payload) } as MessageEvent<string>;
    for (const listener of listeners) {
      listener(event);
    }
  }

  public close(): void {
    this.closed = true;
  }
}

declare module "lightweight-charts" {
  interface TimeScaleApi {
    fitContent(): void;
  }
}

const { createChartMock } = vi.hoisted(() => ({
  createChartMock: vi.fn(),
}));

vi.mock("lightweight-charts", () => ({
  createChart: createChartMock,
}));

const buildChartStub = () => {
  const setData = vi.fn();
  const series = {
    setData,
  };
  return {
    addCandlestickSeries: vi.fn(() => series),
    addLineSeries: vi.fn(() => ({ setData: vi.fn() })),
    addHistogramSeries: vi.fn(() => ({ setData: vi.fn() })),
    timeScale: vi.fn(() => ({ fitContent: vi.fn() })),
    removeSeries: vi.fn(),
    remove: vi.fn(),
  };
};

describe("ChartAnalysis", () => {
  const fetchMock = vi.fn();

  beforeEach(() => {
    fetchMock.mockReset();
    MockEventSource.lastInstance = null;
    createChartMock.mockReset();
    createChartMock.mockImplementation(buildChartStub);
  });

  afterEach(() => {
    vi.clearAllMocks();
  });

  it("streams analysis events and updates the UI", async () => {
    const ohlcvBody = {
      symbol: "BTC/USDT",
      timeframe: "1h",
      rows: [
        { ts: 1_700_000_000, o: 10, h: 12, l: 9, c: 11, v: 1000 },
        { ts: 1_700_000_600, o: 11, h: 13, l: 10, c: 12, v: 1200 },
      ],
    };
    const indicatorBody = {
      series: [
        { ts: 1_700_000_000, values: { ema_50: 10.5, rsi_14: 55, macd: 0.4, macd_signal: 0.2, macd_hist: 0.1, bb_upper: 12, bb_lower: 9, bb_middle: 10.5 } },
        { ts: 1_700_000_600, values: { ema_50: 11.2, rsi_14: 58, macd: 0.6, macd_signal: 0.3, macd_hist: 0.3, bb_upper: 13, bb_lower: 10, bb_middle: 11 } },
      ],
    };
    fetchMock.mockImplementation(async (url: string) => {
      if (url.includes("/api/v1/market/ohlcv")) {
        return new Response(JSON.stringify(ohlcvBody), { status: 200 });
      }
      if (url.includes("/api/v1/indicators/compute")) {
        return new Response(JSON.stringify(indicatorBody), { status: 200 });
      }
      throw new Error(`Unexpected fetch call: ${url}`);
    });

    const user = userEvent.setup();

    render(
      <ChartAnalysis
        apiBaseUrl=""
        apiToken="demo"
        fetchImpl={fetchMock}
        eventSourceFactory={(url, _init) => new MockEventSource(url)}
      />,
    );

    await act(async () => {
      await user.click(screen.getByTestId("chart-start"));
    });

    expect(fetchMock).toHaveBeenCalledWith(
      "/api/v1/market/ohlcv?symbol=BTC%2FUSDT&timeframe=1h&limit=500",
      expect.any(Object),
    );

    const source = MockEventSource.lastInstance;
    expect(source).toBeTruthy();
    await act(async () => {
      source!.dispatch("heartbeat", { payload: { ts: 1_700_000_999_000 } });
      source!.dispatch("result_partial", {
        payload: {
          levels: [{ kind: "support", label: "fort", strength: 0.8, price: 10.5 }],
          steps: [{ name: "ohlcv", status: "completed" }],
        },
      });
      source!.dispatch("step:end", { payload: { stage: "indicators" } });
      await Promise.resolve();
    });

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        "/api/v1/indicators/compute",
        expect.objectContaining({ method: "POST" }),
      );
    });

    await act(async () => {
      source!.dispatch("token", { payload: { text: "Analyse " } });
      source!.dispatch("token", { payload: { text: "terminée." } });
      source!.dispatch("result_final", {
        payload: {
          summary: "Résumé final",
          levels: [{ kind: "resistance", label: "général", strength: 0.6, price: 12, ts_range: [1, 2] }],
          patterns: [{ name: "Head & Shoulders", score: 0.9 }],
        },
      });
      source!.dispatch("done", { payload: { status: "ok" } });
      await Promise.resolve();
    });

    expect(await screen.findByText(/Résumé final/)).toBeVisible();
    expect(screen.getByTestId("analysis-levels").textContent).toContain("RESISTANCE");
    expect(screen.getByTestId("analysis-patterns").textContent).toContain("Head & Shoulders");
    expect(screen.getByTestId("analysis-summary").textContent).toContain("Résumé final");
    expect(source!.closed).toBe(true);
  });
});
