import { act, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import FinanceChartArtifact, {
  type ChartArtifactResponse,
  type ChartCandleDetails,
  type ChartEventPayload,
  type LineSeriesApi,
} from "./finance-chart-artifact";

class FakeCandlestickSeries {
  public readonly setData = vi.fn();
}

class FakeLineSeries implements LineSeriesApi {
  public readonly setData = vi.fn();
  public readonly remove = vi.fn();
}

class FakeChart implements ChartApi {
  public readonly candlestick = new FakeCandlestickSeries();
  public readonly lineSeries: FakeLineSeries[] = [];
  public readonly remove = vi.fn();
  public clickHandlers: Array<(payload: ChartEventPayload) => void> = [];
  public crosshairHandlers: Array<(payload: ChartEventPayload) => void> = [];

  addCandlestickSeries() {
    return this.candlestick;
  }

  addLineSeries() {
    const series = new FakeLineSeries();
    this.lineSeries.push(series);
    return series;
  }

  subscribeClick(handler: (param: ChartEventPayload) => void): void {
    this.clickHandlers.push(handler);
  }

  unsubscribeClick(handler: (param: ChartEventPayload) => void): void {
    this.clickHandlers = this.clickHandlers.filter((candidate) => candidate !== handler);
  }

  subscribeCrosshairMove(handler: (param: ChartEventPayload) => void): void {
    this.crosshairHandlers.push(handler);
  }

  unsubscribeCrosshairMove(handler: (param: ChartEventPayload) => void): void {
    this.crosshairHandlers = this.crosshairHandlers.filter((candidate) => candidate !== handler);
  }
}

const baseDetails: ChartCandleDetails[] = [
  {
    ts: 1,
    open: 100,
    high: 110,
    low: 90,
    close: 105,
    volume: 1_000,
    previousClose: 95,
    changeAbs: 10,
    changePct: 10.53,
    range: 20,
    body: 15,
    bodyPct: 75,
    upperWick: 5,
    lowerWick: 5,
    direction: "bullish",
  },
  {
    ts: 2,
    open: 105,
    high: 112,
    low: 101,
    close: 108,
    volume: 900,
    previousClose: 105,
    changeAbs: 3,
    changePct: 2.86,
    range: 11,
    body: 7,
    bodyPct: 63.6,
    upperWick: 4,
    lowerWick: 3,
    direction: "bullish",
  },
];

function buildArtifact(overrides: Partial<ChartArtifactResponse> = {}): ChartArtifactResponse {
  const rows = baseDetails.map(({ ts, open, high, low, close, volume }) => ({
    ts,
    open,
    high,
    low,
    close,
    volume,
  }));

  return {
    status: "ready",
    symbol: "BTCUSD",
    timeframe: "1D",
    rows,
    range: {
      firstTs: rows[0]?.ts ?? 0,
      lastTs: rows.at(-1)?.ts ?? 0,
      high: Math.max(...rows.map((row) => row.high)),
      low: Math.min(...rows.map((row) => row.low)),
      totalVolume: rows.reduce((total, row) => total + row.volume, 0),
    },
    selected: baseDetails[0] ?? null,
    details: baseDetails,
    overlays: [],
    ...overrides,
  };
}

describe("FinanceChartArtifact", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders an empty state when no market data is available", () => {
    const artifact = buildArtifact({
      status: "empty",
      rows: [],
      details: [],
      selected: null,
      range: null,
    });
    const createChart = vi.fn(() => new FakeChart());

    render(
      <FinanceChartArtifact artifact={artifact} createChart={createChart} />,
    );

    expect(createChart).not.toHaveBeenCalled();
    expect(screen.getByText(/aucune donnée de marché/i)).toBeInTheDocument();
  });

  it("creates the chart once and hydrates candles", () => {
    let lastChart: FakeChart | null = null;
    const createChart = vi.fn(() => {
      lastChart = new FakeChart();
      return lastChart;
    });

    const artifact = buildArtifact();

    render(
      <FinanceChartArtifact artifact={artifact} createChart={createChart} />,
    );

    expect(createChart).toHaveBeenCalledTimes(1);
    expect(lastChart?.candlestick.setData).toHaveBeenCalled();
    const call = lastChart?.candlestick.setData.mock.calls.at(-1);
    expect(call?.[0]).toHaveLength(artifact.rows.length);
  });

  it("cleans up listeners and overlays on unmount", () => {
    let lastChart: FakeChart | null = null;
    const createChart = vi.fn(() => {
      lastChart = new FakeChart();
      return lastChart;
    });

    const artifact = buildArtifact({
      overlays: [
        {
          id: "sma-50",
          type: "sma",
          window: 50,
          points: [
            { ts: 1, value: 101 },
            { ts: 2, value: 102 },
          ],
        },
      ],
    });

    const { unmount } = render(
      <FinanceChartArtifact artifact={artifact} createChart={createChart} />,
    );

    expect(lastChart?.lineSeries[0]?.setData).toHaveBeenCalled();

    unmount();

    expect(lastChart?.remove).toHaveBeenCalledTimes(1);
    expect(lastChart?.lineSeries[0]?.remove).toHaveBeenCalledTimes(1);
    expect(lastChart?.clickHandlers).toHaveLength(0);
    expect(lastChart?.crosshairHandlers).toHaveLength(0);
  });

  it("updates the candle details when a point is selected", () => {
    let lastChart: FakeChart | null = null;
    const onSelect = vi.fn();
    const createChart = vi.fn(() => {
      lastChart = new FakeChart();
      return lastChart;
    });

    const artifact = buildArtifact();

    render(
      <FinanceChartArtifact
        artifact={artifact}
        createChart={createChart}
        onSelectCandle={onSelect}
      />,
    );

    act(() => {
      lastChart?.clickHandlers[0]?.({ time: artifact.details[1]?.ts });
    });

    expect(onSelect).toHaveBeenCalledWith(artifact.details[1]);
    expect(screen.getByText(artifact.details[1]?.close.toFixed(2) ?? "")).toBeInTheDocument();
  });

  it("refreshes the details panel on hover and restores the last selection", () => {
    let lastChart: FakeChart | null = null;
    const createChart = vi.fn(() => {
      lastChart = new FakeChart();
      return lastChart;
    });

    const artifact = buildArtifact();

    render(<FinanceChartArtifact artifact={artifact} createChart={createChart} />);

    act(() => {
      lastChart?.crosshairHandlers[0]?.({ time: artifact.details[1]?.ts });
    });

    expect(screen.getByText(artifact.details[1]?.close.toFixed(2) ?? "")).toBeInTheDocument();

    act(() => {
      lastChart?.crosshairHandlers[0]?.({ time: null });
    });

    expect(screen.getByText(artifact.selected?.close.toFixed(2) ?? "")).toBeInTheDocument();
  });

  it("removes overlay series that disappear from the payload", () => {
    let lastChart: FakeChart | null = null;
    const createChart = vi.fn(() => {
      lastChart = new FakeChart();
      return lastChart;
    });

    const initial = buildArtifact({
      overlays: [
        {
          id: "ema-21",
          type: "ema",
          window: 21,
          points: [
            { ts: 1, value: 102 },
            { ts: 2, value: 103 },
          ],
        },
      ],
    });

    const { rerender } = render(
      <FinanceChartArtifact artifact={initial} createChart={createChart} />,
    );

    expect(lastChart?.lineSeries).toHaveLength(1);
    const [series] = lastChart?.lineSeries ?? [];

    rerender(
      <FinanceChartArtifact
        artifact={{ ...initial, overlays: [] }}
        createChart={createChart}
      />,
    );

    expect(series?.remove).toHaveBeenCalledTimes(1);
  });
});
