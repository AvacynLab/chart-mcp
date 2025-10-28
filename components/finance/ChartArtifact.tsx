"use client";

import { useEffect, useMemo, useRef, useState } from "react";

/** OHLCV row returned by the backend finance service. */
export interface OhlcvRow {
  readonly ts: number;
  readonly open: number;
  readonly high: number;
  readonly low: number;
  readonly close: number;
  readonly volume: number;
}

/** Aggregated range metrics for the rendered period. */
export interface ChartRangeModel {
  readonly firstTs: number;
  readonly lastTs: number;
  readonly high: number;
  readonly low: number;
  readonly totalVolume: number;
}

/** Detailed analytics for an individual candle. */
export interface ChartCandleDetails {
  readonly ts: number;
  readonly open: number;
  readonly high: number;
  readonly low: number;
  readonly close: number;
  readonly volume: number;
  readonly previousClose: number;
  readonly changeAbs: number;
  readonly changePct: number;
  readonly range: number;
  readonly body: number;
  readonly bodyPct: number;
  readonly upperWick: number;
  readonly lowerWick: number;
  readonly direction: "bullish" | "bearish" | "neutral";
}

/** Overlay point sampled from the moving-average series. */
export interface OverlayPointModel {
  readonly ts: number;
  readonly value: number | null;
}

/** Overlay series descriptor returned by the API. */
export interface OverlaySeriesModel {
  readonly id: string;
  readonly type: "sma" | "ema";
  readonly window: number;
  readonly points: readonly OverlayPointModel[];
}

/** Serialized chart artefact consumed by the component. */
export interface ChartArtifactResponse {
  readonly status: "empty" | "ready";
  readonly symbol: string;
  readonly timeframe: string;
  readonly rows: readonly OhlcvRow[];
  readonly range: ChartRangeModel | null;
  readonly selected: ChartCandleDetails | null;
  readonly details: readonly ChartCandleDetails[];
  readonly overlays: readonly OverlaySeriesModel[];
}

/** Minimal click/crosshair payload emitted by lightweight charts. */
export interface ChartEventPayload {
  readonly time?: number | null;
}

/** Candlestick series API subset used by the component. */
export interface CandlestickSeriesApi {
  setData(data: readonly unknown[]): void;
}

/** Overlay series API subset used by the component. */
export interface LineSeriesApi {
  setData(data: readonly unknown[]): void;
  remove?: () => void;
}

/** Chart instance API subset we rely on. */
export interface ChartApi {
  addCandlestickSeries(): CandlestickSeriesApi;
  addLineSeries(): LineSeriesApi;
  remove(): void;
  subscribeClick(handler: (param: ChartEventPayload) => void): void;
  unsubscribeClick(handler: (param: ChartEventPayload) => void): void;
  subscribeCrosshairMove(handler: (param: ChartEventPayload) => void): void;
  unsubscribeCrosshairMove(handler: (param: ChartEventPayload) => void): void;
}

export interface ChartArtifactProps {
  /** Payload delivered by the backend finance service. */
  readonly artifact: ChartArtifactResponse;
  /** Factory that constructs the underlying chart instance. */
  readonly createChart: (container: HTMLElement) => ChartApi;
  /** Optional callback triggered when a candle is explicitly selected. */
  readonly onSelectCandle?: (details: ChartCandleDetails | null) => void;
  /** Optional callback triggered when the hover candle changes. */
  readonly onHoverCandle?: (details: ChartCandleDetails | null) => void;
}

/**
 * Translate an overlay descriptor into the lightweight-charts data format.
 */
function mapOverlayPoints(points: readonly OverlayPointModel[]): readonly { time: number; value: number | null }[] {
  return points.map((point) => ({ time: point.ts, value: point.value ?? null }));
}

function mapOhlcvRows(rows: readonly OhlcvRow[]): readonly unknown[] {
  return rows.map((row) => ({
    time: row.ts,
    open: row.open,
    high: row.high,
    low: row.low,
    close: row.close,
    volume: row.volume,
  }));
}

/**
 * Chart artefact responsible for rendering OHLCV data and overlays.
*/
export default function ChartArtifact({
  artifact,
  createChart,
  onSelectCandle,
  onHoverCandle,
}: ChartArtifactProps): JSX.Element {
  const containerRef = useRef<HTMLDivElement | null>(null);
  const mountedRef = useRef(false);
  const chartRef = useRef<ChartApi | null>(null);
  const candlestickSeriesRef = useRef<CandlestickSeriesApi | null>(null);
  const overlaySeriesRef = useRef<Map<string, LineSeriesApi>>(new Map());
  const clickHandlerRef = useRef<((payload: ChartEventPayload) => void) | null>(null);
  const crosshairHandlerRef = useRef<((payload: ChartEventPayload) => void) | null>(null);
  const lastSelectedRef = useRef<ChartCandleDetails | null>(artifact.selected ?? null);
  const [activeDetails, setActiveDetails] = useState<ChartCandleDetails | null>(
    artifact.selected ?? null,
  );

  const hasData = artifact.status === "ready" && artifact.rows.length > 0;

  const detailsByTimestamp = useMemo(() => {
    const lookup = new Map<number, ChartCandleDetails>();
    for (const detail of artifact.details) {
      lookup.set(detail.ts, detail);
    }
    return lookup;
  }, [artifact.details]);

  useEffect(() => {
    const selected = artifact.selected ?? null;
    setActiveDetails(selected);
    lastSelectedRef.current = selected;
  }, [artifact.selected, artifact.symbol, artifact.timeframe]);

  useEffect(() => {
    mountedRef.current = true;
    return () => {
      mountedRef.current = false;
      teardownChart();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    if (!mountedRef.current) {
      return;
    }

    if (!hasData) {
      teardownChart();
      return;
    }

    if (!containerRef.current) {
      return;
    }

    if (!chartRef.current) {
      const chart = createChart(containerRef.current);
      chartRef.current = chart;
      candlestickSeriesRef.current = chart.addCandlestickSeries();

      const handleClick = (payload: ChartEventPayload) => {
        if (!mountedRef.current) {
          return;
        }
        const ts = payload.time ?? null;
        const detail = typeof ts === "number" ? detailsByTimestamp.get(ts) ?? null : null;
        if (detail) {
          lastSelectedRef.current = detail;
        }
        setActiveDetails(detail);
        onSelectCandle?.(detail ?? null);
      };
      chart.subscribeClick(handleClick);
      clickHandlerRef.current = handleClick;

      const handleHover = (payload: ChartEventPayload) => {
        if (!mountedRef.current) {
          return;
        }
        const ts = payload.time ?? null;
        const detail = typeof ts === "number" ? detailsByTimestamp.get(ts) ?? null : null;
        if (detail) {
          setActiveDetails(detail);
        } else {
          setActiveDetails(lastSelectedRef.current);
        }
        onHoverCandle?.(detail ?? null);
      };
      chart.subscribeCrosshairMove(handleHover);
      crosshairHandlerRef.current = handleHover;
    }

    const candleSeries = candlestickSeriesRef.current;
    candleSeries?.setData(mapOhlcvRows(artifact.rows));

    syncOverlays(artifact.overlays);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [artifact, detailsByTimestamp, createChart, hasData]);

  const activeRange = artifact.range;

  function teardownChart(): void {
    const chart = chartRef.current;
    if (!chart) {
      return;
    }

    if (clickHandlerRef.current) {
      chart.unsubscribeClick(clickHandlerRef.current);
      clickHandlerRef.current = null;
    }

    if (crosshairHandlerRef.current) {
      chart.unsubscribeCrosshairMove(crosshairHandlerRef.current);
      crosshairHandlerRef.current = null;
    }

    for (const series of overlaySeriesRef.current.values()) {
      series.remove?.();
    }
    overlaySeriesRef.current.clear();
    candlestickSeriesRef.current = null;
    chart.remove();
    chartRef.current = null;
  }

  function syncOverlays(overlays: readonly OverlaySeriesModel[]): void {
    const chart = chartRef.current;
    if (!chart) {
      return;
    }

    const activeIds = new Set(overlays.map((overlay) => overlay.id));
    for (const [id, series] of overlaySeriesRef.current.entries()) {
      if (!activeIds.has(id)) {
        series.remove?.();
        overlaySeriesRef.current.delete(id);
      }
    }

    for (const overlay of overlays) {
      let series = overlaySeriesRef.current.get(overlay.id);
      if (!series) {
        series = chart.addLineSeries();
        overlaySeriesRef.current.set(overlay.id, series);
      }
      series.setData(mapOverlayPoints(overlay.points));
    }
  }

  if (!hasData) {
    return (
      <section data-testid="chart-artifact" aria-live="polite">
        <p>Aucune donnée de marché disponible pour {artifact.symbol}.</p>
      </section>
    );
  }

  return (
    <section data-testid="chart-artifact" className="finance-chart">
      <header>
        <h2>
          {artifact.symbol} — {artifact.timeframe}
        </h2>
        {activeRange && (
          <p>
            Plage: {new Date(activeRange.firstTs).toLocaleString()} → {" "}
            {new Date(activeRange.lastTs).toLocaleString()} — Volume total: {" "}
            {activeRange.totalVolume.toLocaleString()}
          </p>
        )}
      </header>
      <div ref={containerRef} className="finance-chart__canvas" />
      <aside data-testid="finance-chart-details" className="finance-chart__details">
        {activeDetails ? (
          <dl>
            <div>
              <dt>Horodatage</dt>
              <dd>{new Date(activeDetails.ts).toLocaleString()}</dd>
            </div>
            <div>
              <dt>Clôture</dt>
              <dd>{activeDetails.close.toFixed(2)}</dd>
            </div>
            <div>
              <dt>Variation</dt>
              <dd>
                {activeDetails.changeAbs.toFixed(2)} ({activeDetails.changePct.toFixed(2)}%)
              </dd>
            </div>
            <div>
              <dt>Corps / Étendue</dt>
              <dd>
                {activeDetails.body.toFixed(2)} ({activeDetails.bodyPct.toFixed(2)}%) sur une
                plage de {activeDetails.range.toFixed(2)}
              </dd>
            </div>
            <div>
              <dt>Mèches</dt>
              <dd>
                Haute {activeDetails.upperWick.toFixed(2)} / Basse {" "}
                {activeDetails.lowerWick.toFixed(2)}
              </dd>
            </div>
          </dl>
        ) : (
          <p>Sélectionnez une bougie pour afficher les détails.</p>
        )}
      </aside>
    </section>
  );
}
