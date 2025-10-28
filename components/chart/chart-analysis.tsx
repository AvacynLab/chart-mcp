"use client";

import {
  FormEvent,
  MutableRefObject,
  ReactNode,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  CandlestickData,
  HistogramData,
  IChartApi,
  ISeriesApi,
  LineData,
  Time,
  createChart,
} from "lightweight-charts";
import { fetchEventSource, type EventSourceMessage } from "@microsoft/fetch-event-source";

/**
 * Shape of a single OHLCV row returned by the backend REST endpoint.
 */
interface OhlcvRow {
  readonly ts: number;
  readonly o: number;
  readonly h: number;
  readonly l: number;
  readonly c: number;
  readonly v: number;
}

/**
 * Response produced by ``/api/v1/market/ohlcv``. The component only needs a
 * subset of the metadata fields so we model the minimal shape here.
 */
interface OhlcvResponseBody {
  readonly symbol: string;
  readonly timeframe: string;
  readonly rows: readonly OhlcvRow[];
}

/**
 * Canonical indicator identifiers exposed by the backend.
 */
type IndicatorName = "ema" | "rsi" | "macd" | "bbands";

/**
 * Request payload forwarded to ``/api/v1/indicators/compute``.
 */
interface IndicatorRequestBody {
  readonly symbol: string;
  readonly timeframe: string;
  readonly indicator: string;
  readonly params: Record<string, number>;
  readonly limit: number;
}

/**
 * Shape of a single indicator record returned by the backend.
 */
interface IndicatorValue {
  readonly ts: number;
  readonly values: Record<string, number>;
}

/**
 * Response envelope produced by ``/api/v1/indicators/compute``.
 */
interface IndicatorResponseBody {
  readonly series: readonly IndicatorValue[];
}

/**
 * Compact snapshot of a level extracted from the SSE partial payload.
 */
interface LevelPreview {
  readonly kind: string;
  readonly strength: number;
  readonly label: string;
  readonly price: number | null;
}

/**
 * Payload emitted by the SSE ``result_partial`` event.
 */
interface ResultPartialPayload {
  readonly indicators?: Record<string, Record<string, number>> | null;
  readonly levels?: readonly LevelPreview[];
  readonly progress?: number | null;
  readonly steps?: readonly ProgressStep[];
}

/**
 * Payload emitted by the SSE ``result_final`` event.
 */
interface ResultFinalPayload {
  readonly summary: string;
  readonly levels: ReadonlyArray<LevelPreview & { readonly ts_range: readonly [number, number]; }>;
  readonly patterns: ReadonlyArray<{ readonly name: string; readonly score: number }>;
}

/**
 * Structured description of an SSE progress step.
 */
interface ProgressStep {
  readonly name: string;
  readonly status: "pending" | "in_progress" | "completed" | "skipped";
  readonly progress?: number | null;
}

/**
 * SSE event describing a pipeline stage lifecycle update.
 */
interface StepEventPayload {
  readonly stage: "ohlcv" | "indicators" | "levels" | "patterns" | "summary";
  readonly description?: string | null;
  readonly elapsed_ms?: number | null;
  readonly metadata?: Record<string, unknown>;
}

/**
 * Minimal subset of the ``MessageEvent`` interface leveraged by the component.
 */
interface JsonMessageEvent {
  readonly data: string;
}

/**
 * Factory signature used to instantiate the ``EventSource`` implementation.
 * Allowing dependency injection keeps the component testable because Vitest can
 * provide a deterministic mock instead of relying on the browser primitive.
 */
type EventSourceListener = (event: MessageEvent<string>) => void;

export interface EventSourceLike {
  addEventListener(type: string, listener: EventSourceListener): void;
  close(): void;
}

export type EventSourceFactory = (url: string, init: { headers: Record<string, string> }) => EventSourceLike;

/**
 * Union representing chart overlays so we can manage the lifecycle of each
 * Lightweight Charts series in a type-safe fashion.
 */
interface OverlaySeries {
  readonly id: string;
  readonly kind: "line" | "histogram";
  readonly pane: "main" | "rsi" | "macd";
  readonly color: string;
  readonly data: readonly (LineData | HistogramData)[];
}

/**
 * Form state captured from the control panel. The ``limit`` is currently kept
 * constant to reduce the amount of configuration surfaced to the operator.
 */
interface ChartFormState {
  readonly symbol: string;
  readonly timeframe: string;
  readonly indicators: readonly IndicatorName[];
  readonly limit: number;
}

/**
 * Props exposed by the chart analysis component.
 */
export interface ChartAnalysisProps {
  /** Base URL used for REST and SSE calls (defaults to the current origin). */
  readonly apiBaseUrl?: string | null;
  /** Bearer token injected into the ``Authorization`` header. */
  readonly apiToken?: string | null;
  /** Optional placeholder symbol surfaced to the operator. */
  readonly defaultSymbol?: string;
  /** Optional placeholder timeframe value. */
  readonly defaultTimeframe?: string;
  /**
   * Factory used to créer un client SSE compatible (ex: fetch-event-source).
   * Tests injectent un mock pour simuler le pipeline sans backend réel.
   */
  readonly eventSourceFactory?: EventSourceFactory;
  /**
   * Fetch implementation leveraged for REST calls. Keeping it injectable allows
   * unit tests to provide a deterministic stub while the runtime defaults to
   * ``window.fetch``.
   */
  readonly fetchImpl?: typeof fetch;
}

/** Default symbol/timeframe used when the operator first lands on the page. */
const DEFAULT_SYMBOL = "BTC/USDT";
const DEFAULT_TIMEFRAME = "1h";
const DEFAULT_LIMIT = 500;

/**
 * Mapping that connects indicator identifiers to their canonical API payloads
 * and default rendering hints.
 */
const INDICATOR_PRESETS: Record<IndicatorName, { readonly params: Record<string, number>; readonly color: string }> = {
  ema: { params: { window: 50 }, color: "#ff9800" },
  rsi: { params: { window: 14 }, color: "#2962ff" },
  macd: { params: { fast: 12, slow: 26, signal: 9 }, color: "#8e24aa" },
  bbands: { params: { window: 20, stddev: 2 }, color: "#26a69a" },
};

/**
 * Helper that converts a Unix timestamp in seconds or milliseconds to the
 * representation expected by Lightweight Charts.
 */
function toChartTime(ts: number): number {
  if (ts > 10_000_000_000) {
    return Math.floor(ts / 1000);
  }
  return ts;
}

/**
 * Small helper returning a defensive copy of the default form state.
 */
function buildInitialFormState(symbol?: string, timeframe?: string): ChartFormState {
  return {
    symbol: symbol ?? DEFAULT_SYMBOL,
    timeframe: timeframe ?? DEFAULT_TIMEFRAME,
    indicators: ["ema", "rsi", "macd", "bbands"],
    limit: DEFAULT_LIMIT,
  };
}

class FetchEventSourceClient implements EventSourceLike {
  private readonly listeners = new Map<string, Set<EventSourceListener>>();
  private readonly controller = new AbortController();

  constructor(private readonly url: string, private readonly headers: Record<string, string>) {
    void this.start();
  }

  public addEventListener(type: string, listener: EventSourceListener): void {
    if (!this.listeners.has(type)) {
      this.listeners.set(type, new Set());
    }
    this.listeners.get(type)!.add(listener);
  }

  public close(): void {
    this.controller.abort();
    this.listeners.clear();
  }

  private dispatch(type: string, data: string): void {
    const handlers = this.listeners.get(type);
    if (!handlers || handlers.size === 0) {
      return;
    }
    const event = { data } as MessageEvent<string>;
    handlers.forEach((handler) => handler(event));
  }

  private async start(): Promise<void> {
    try {
      await fetchEventSource(this.url, {
        method: "GET",
        headers: {
          ...this.headers,
          Accept: "text/event-stream",
        },
        signal: this.controller.signal,
        onmessage: (message: EventSourceMessage) => {
          const eventName = message.event ?? "message";
          const payload = message.data ?? "";
          this.dispatch(eventName, payload);
        },
        onerror: (error: unknown) => {
          const reason = error instanceof Error ? error.message : String(error);
          this.dispatch(
            "error",
            JSON.stringify({ payload: { message: reason } }),
          );
          throw error;
        },
      });
    } catch (error) {
      if (this.controller.signal.aborted) {
        return;
      }
      const reason = error instanceof Error ? error.message : String(error);
      this.dispatch(
        "error",
        JSON.stringify({ payload: { message: reason } }),
      );
    }
  }
}

const defaultEventSourceFactory: EventSourceFactory = (url, init) =>
  new FetchEventSourceClient(url, init.headers);

/**
 * Render the main chart analysis workflow with SSE-driven progress updates.
 */
export default function ChartAnalysis({
  apiBaseUrl,
  apiToken,
  defaultSymbol,
  defaultTimeframe,
  eventSourceFactory = defaultEventSourceFactory,
  fetchImpl,
}: ChartAnalysisProps): JSX.Element {
  const formInitialState = useMemo(
    () => buildInitialFormState(defaultSymbol, defaultTimeframe),
    [defaultSymbol, defaultTimeframe],
  );
  const [formState, setFormState] = useState<ChartFormState>(formInitialState);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [summaryTokens, setSummaryTokens] = useState<string[]>([]);
  const [finalSummary, setFinalSummary] = useState<string | null>(null);
  const [levels, setLevels] = useState<readonly LevelPreview[]>([]);
  const [patterns, setPatterns] = useState<readonly string[]>([]);
  const [steps, setSteps] = useState<readonly ProgressStep[]>([]);
  const [lastHeartbeat, setLastHeartbeat] = useState<number | null>(null);

  // ``fetch`` is available in both Node.js (Next.js SSR) and the browser. Avoid
  // binding to ``window`` so the code path remains server-safe when the client
  // component is evaluated during hydration.
  const fetcher = fetchImpl ?? (typeof fetch !== "undefined" ? fetch : undefined);

  const chartContainerRef = useRef<HTMLDivElement | null>(null);
  const rsiContainerRef = useRef<HTMLDivElement | null>(null);
  const macdContainerRef = useRef<HTMLDivElement | null>(null);

  const chartRef = useRef<IChartApi | null>(null);
  const rsiChartRef = useRef<IChartApi | null>(null);
  const macdChartRef = useRef<IChartApi | null>(null);
  const candleSeriesRef = useRef<ISeriesApi<"Candlestick"> | null>(null);
  const overlaySeriesRef = useRef<Record<string, ISeriesApi<any>>>({});
  const overlayHostRef = useRef<Record<string, IChartApi>>({});

  const eventSourceRef = useRef<EventSourceLike | null>(null);
  const currentRequestRef = useRef<ChartFormState>(formInitialState);

  useEffect(() => {
    if (!chartContainerRef.current || chartRef.current) {
      return;
    }
    const chart = createChart(chartContainerRef.current, {
      height: 360,
      layout: { background: { color: "#111" }, textColor: "#f5f5f5" },
      crosshair: { mode: 1 },
      rightPriceScale: { borderVisible: false },
      timeScale: { borderVisible: false },
    });
    const candlesticks = chart.addCandlestickSeries({
      upColor: "#0ecb81",
      downColor: "#f6465d",
      borderVisible: false,
      wickUpColor: "#0ecb81",
      wickDownColor: "#f6465d",
    });
    chartRef.current = chart;
    candleSeriesRef.current = candlesticks;

    const ensurePane = (
      container: HTMLDivElement | null,
      apiRef: MutableRefObject<IChartApi | null>,
      height: number,
    ) => {
      if (!container || apiRef.current) {
        return;
      }
      const pane = createChart(container, {
        height,
        layout: { background: { color: "#111" }, textColor: "#f5f5f5" },
        rightPriceScale: { borderVisible: false },
        timeScale: { borderVisible: false },
      });
      apiRef.current = pane;
    };

    ensurePane(rsiContainerRef.current, rsiChartRef, 160);
    ensurePane(macdContainerRef.current, macdChartRef, 160);

    return () => {
      chart.remove();
      chartRef.current = null;
      candleSeriesRef.current = null;
      Object.entries(overlaySeriesRef.current).forEach(([id, series]) => {
        try {
          const host = overlayHostRef.current[id] ?? chart;
          host.removeSeries(series);
        } catch (removeError) {
          console.error("Unable to remove indicator series", removeError);
        }
      });
      overlaySeriesRef.current = {};
      overlayHostRef.current = {};
      if (rsiChartRef.current) {
        rsiChartRef.current.remove();
        rsiChartRef.current = null;
      }
      if (macdChartRef.current) {
        macdChartRef.current.remove();
        macdChartRef.current = null;
      }
    };
  }, []);

  useEffect(() => () => {
    eventSourceRef.current?.close();
  }, []);

  const headers = useMemo(() => {
    const token = apiToken?.trim();
    const baseHeaders: Record<string, string> = { "X-Session-User": "regular" };
    if (token) {
      baseHeaders.Authorization = `Bearer ${token}`;
    }
    return baseHeaders;
  }, [apiToken]);

  const baseUrl = useMemo(() => apiBaseUrl?.replace(/\/$/, "") ?? "", [apiBaseUrl]);

  const buildUrl = useCallback(
    (path: string, params?: URLSearchParams) => {
      const normalizedPath = path.startsWith("/") ? path : `/${path}`;
      const query = params ? `?${params.toString()}` : "";
      if (!baseUrl) {
        return `${normalizedPath}${query}`;
      }
      return `${baseUrl}${normalizedPath}${query}`;
    },
    [baseUrl],
  );

  const updateCandles = useCallback((rows: readonly OhlcvRow[]) => {
    if (!candleSeriesRef.current || !chartRef.current) {
      return;
    }
    const candles: CandlestickData<Time>[] = rows.map((row) => ({
      time: toChartTime(row.ts) as Time,
      open: row.o,
      high: row.h,
      low: row.l,
      close: row.c,
    }));
    candleSeriesRef.current.setData(candles);
    chartRef.current.timeScale().fitContent();
  }, []);

  const syncOverlaySeries = useCallback((seriesList: readonly OverlaySeries[]) => {
    const chart = chartRef.current;
    if (!chart) {
      return;
    }
    const ensurePaneChart = (
      pane: "main" | "rsi" | "macd",
    ): IChartApi | null => {
      if (pane === "main") {
        return chartRef.current;
      }
      if (pane === "rsi") {
        return rsiChartRef.current;
      }
      if (pane === "macd") {
        return macdChartRef.current;
      }
      return null;
    };

    const desiredIds = new Set(seriesList.map((overlay) => overlay.id));
    for (const [id, series] of Object.entries(overlaySeriesRef.current)) {
      if (desiredIds.has(id)) {
        continue;
      }
      const host = overlayHostRef.current[id] ?? chart;
      try {
        host.removeSeries(series);
      } catch (removeError) {
        console.error("Unable to detach obsolete indicator series", removeError);
      }
      delete overlaySeriesRef.current[id];
      delete overlayHostRef.current[id];
    }

    for (const overlay of seriesList) {
      const paneChart = ensurePaneChart(overlay.pane);
      if (!paneChart) {
        continue;
      }
      let series = overlaySeriesRef.current[overlay.id];
      if (!series) {
        series = overlay.kind === "line"
          ? paneChart.addLineSeries({ color: overlay.color, lineWidth: 2 })
          : paneChart.addHistogramSeries({ color: overlay.color, priceFormat: { type: "price", precision: 4 } });
        overlaySeriesRef.current[overlay.id] = series;
        overlayHostRef.current[overlay.id] = paneChart;
      }
      series.setData(overlay.data as any);
    }
  }, []);

  const resetState = useCallback(() => {
    setError(null);
    setSummaryTokens([]);
    setFinalSummary(null);
    setLevels([]);
    setPatterns([]);
    setSteps([]);
  }, []);

  const buildIndicatorsQuery = useCallback((indicators: readonly IndicatorName[]) => {
    const parts = indicators.map((name) => {
      const preset = INDICATOR_PRESETS[name];
      const params = Object.entries(preset.params)
        .map(([key, value]) => `${key}=${value}`)
        .join(";");
      return params ? `${name}:${params}` : name;
    });
    return parts.join(",");
  }, []);

  const fetchIndicators = useCallback(
    async (request: ChartFormState) => {
      if (!fetcher) {
        return;
      }
      const overlays: OverlaySeries[] = [];
      const requests = request.indicators.map(async (name) => {
        const preset = INDICATOR_PRESETS[name];
        const body: IndicatorRequestBody = {
          symbol: request.symbol,
          timeframe: request.timeframe,
          indicator: name,
          params: preset.params,
          limit: request.limit,
        };
        const url = `${baseUrl}/api/v1/indicators/compute`;
        const response = await fetcher(url, {
          method: "POST",
          headers: {
            ...headers,
            "Content-Type": "application/json",
          },
          body: JSON.stringify(body),
        });
        if (!response.ok) {
          throw new Error(`Indicator ${name} request failed (${response.status})`);
        }
        const payload = (await response.json()) as IndicatorResponseBody;
        const aggregated = new Map<string, OverlaySeries>();
        for (const entry of payload.series) {
          const time = toChartTime(entry.ts);
          for (const [key, value] of Object.entries(entry.values)) {
            const overlayId = `${name}:${key}`;
            const pane = name === "rsi" ? "rsi" : name === "macd" ? "macd" : "main";
            const kind: OverlaySeries["kind"] = key === "macd_hist" ? "histogram" : "line";
            const color =
              name === "bbands"
                ? key === "bb_upper"
                  ? "#ef6c00"
                  : key === "bb_lower"
                  ? "#ef6c00"
                  : "#90caf9"
                : INDICATOR_PRESETS[name].color;
            const existing = aggregated.get(overlayId);
            const nextPoint = { time, value } as LineData | HistogramData;
            if (existing) {
              aggregated.set(overlayId, {
                ...existing,
                data: [...existing.data, nextPoint],
              });
            } else {
              aggregated.set(overlayId, {
                id: overlayId,
                kind,
                pane,
                color,
                data: [nextPoint],
              });
            }
          }
        }
        overlays.push(
          ...Array.from(aggregated.values()).map((overlay) => ({
            ...overlay,
            data: [...overlay.data].sort((a, b) => (a.time as number) - (b.time as number)),
          })),
        );
      });
      await Promise.all(requests);
      syncOverlaySeries(overlays);
    },
    [baseUrl, fetcher, headers, syncOverlaySeries],
  );

  const handleStepEnd = useCallback(
    async (payload: StepEventPayload) => {
      if (payload.stage === "indicators") {
        try {
          await fetchIndicators(currentRequestRef.current);
        } catch (indicatorError) {
          console.error("Unable to load indicator overlays", indicatorError);
          setError("Impossible de récupérer les indicateurs (voir console)");
        }
      }
    },
    [fetchIndicators],
  );

  const handleResultPartial = useCallback((payload: ResultPartialPayload) => {
    if (payload.levels) {
      setLevels(payload.levels);
    }
    if (payload.steps) {
      setSteps(payload.steps);
    }
  }, []);

  const handleResultFinal = useCallback((payload: ResultFinalPayload) => {
    setFinalSummary(payload.summary);
    setPatterns(payload.patterns.map((pattern) => pattern.name));
    setLevels(payload.levels);
  }, []);

  const parseEvent = useCallback(<T,>(event: JsonMessageEvent): T | null => {
    try {
      return JSON.parse(event.data) as T;
    } catch (parseError) {
      console.error("Unable to parse SSE payload", parseError);
      return null;
    }
  }, []);

  const closeEventSource = useCallback(() => {
    eventSourceRef.current?.close();
    eventSourceRef.current = null;
  }, []);

  const startStream = useCallback(
    async (request: ChartFormState) => {
      if (!fetcher) {
        setError("fetch API non disponible dans cet environnement");
        return;
      }
      setIsSubmitting(true);
      resetState();
      closeEventSource();
      currentRequestRef.current = request;
      try {
        const ohlcvParams = new URLSearchParams({
          symbol: request.symbol,
          timeframe: request.timeframe,
          limit: request.limit.toString(),
        });
        const response = await fetcher(buildUrl("/api/v1/market/ohlcv", ohlcvParams), {
          headers,
        });
        if (!response.ok) {
          throw new Error(`OHLCV request failed (${response.status})`);
        }
        const payload = (await response.json()) as OhlcvResponseBody;
        updateCandles(payload.rows);
      } catch (requestError) {
        console.error("Unable to bootstrap OHLCV data", requestError);
        setError("Impossible de récupérer les données OHLCV");
        setIsSubmitting(false);
        return;
      }

      const query = new URLSearchParams({
        symbol: request.symbol,
        timeframe: request.timeframe,
        limit: request.limit.toString(),
        indicators: buildIndicatorsQuery(request.indicators),
        include_levels: "true",
        include_patterns: "true",
        streaming: "true",
      });
      const streamUrl = buildUrl("/stream/analysis", query);
      const source = eventSourceFactory(streamUrl, { headers });
      eventSourceRef.current = source;

      const onHeartbeat = (event: MessageEvent<string>) => {
        const heartbeat = parseEvent<{ payload?: { ts?: number } }>(event);
        if (heartbeat?.payload?.ts) {
          setLastHeartbeat(heartbeat.payload.ts);
        }
      };
      const onStepStart = (event: MessageEvent<string>) => {
        const payload = parseEvent<{ payload: StepEventPayload }>(event);
        if (payload?.payload) {
          setSteps((current) => {
            const filtered = current.filter((step) => step.name !== payload.payload.stage);
            return [
              ...filtered,
              { name: payload.payload.stage, status: "in_progress", progress: 0 },
            ];
          });
        }
      };
      const onStepEnd = (event: MessageEvent<string>) => {
        const payload = parseEvent<{ payload: StepEventPayload }>(event);
        if (payload?.payload) {
          void handleStepEnd(payload.payload);
          setSteps((current) => {
            const other = current.filter((step) => step.name !== payload.payload.stage);
            return [
              ...other,
              { name: payload.payload.stage, status: "completed", progress: 1 },
            ];
          });
        }
      };
      const onToken = (event: MessageEvent<string>) => {
        const payload = parseEvent<{ payload: { text: string } }>(event);
        if (payload?.payload?.text) {
          setSummaryTokens((tokens) => [...tokens, payload.payload.text]);
        }
      };
      const onPartial = (event: MessageEvent<string>) => {
        const payload = parseEvent<{ payload: ResultPartialPayload }>(event);
        if (payload?.payload) {
          handleResultPartial(payload.payload);
        }
      };
      const onFinal = (event: MessageEvent<string>) => {
        const payload = parseEvent<{ payload: ResultFinalPayload }>(event);
        if (payload?.payload) {
          handleResultFinal(payload.payload);
        }
      };
      const onErrorEvent = (event: MessageEvent<string>) => {
        const payload = parseEvent<{ payload?: { message?: string } }>(event);
        setError(payload?.payload?.message ?? "Erreur inconnue lors du streaming");
        closeEventSource();
        setIsSubmitting(false);
      };
      const onDone = () => {
        closeEventSource();
        setIsSubmitting(false);
      };

      source.addEventListener("heartbeat", onHeartbeat);
      source.addEventListener("step:start", onStepStart);
      source.addEventListener("step:end", onStepEnd);
      source.addEventListener("token", onToken);
      source.addEventListener("result_partial", onPartial);
      source.addEventListener("result_final", onFinal);
      source.addEventListener("error", onErrorEvent);
      source.addEventListener("done", onDone);
    },
    [
      buildIndicatorsQuery,
      buildUrl,
      closeEventSource,
      eventSourceFactory,
      fetcher,
      handleResultFinal,
      handleResultPartial,
      handleStepEnd,
      headers,
      parseEvent,
      resetState,
      updateCandles,
    ],
  );

  const handleSubmit = useCallback(
    (event: FormEvent<HTMLFormElement>) => {
      event.preventDefault();
      void startStream(formState);
    },
    [formState, startStream],
  );

  const renderLevel = (level: LevelPreview, index: number): ReactNode => {
    return (
      <li key={`${level.kind}-${index}`}>
        <strong>{level.kind.toUpperCase()}</strong> – {level.label} @ {level.price?.toFixed(2) ?? "N/A"}
      </li>
    );
  };

  const activeSummary = finalSummary ?? summaryTokens.join("");

  return (
    <section className="chart-analysis" data-testid="chart-analysis-root">
      <header>
        <h1>Analyse crypto en temps réel</h1>
        <p>
          Configure un symbole, un timeframe et les indicateurs désirés pour déclencher le flux SSE
          d’analyse progressive.
        </p>
      </header>
      <form className="chart-analysis__form" onSubmit={handleSubmit} data-testid="chart-form">
        <label htmlFor="chart-symbol">Symbole</label>
        <input
          id="chart-symbol"
          name="symbol"
          value={formState.symbol}
          onChange={(event) =>
            setFormState((state) => ({ ...state, symbol: event.target.value.toUpperCase() }))
          }
          placeholder="BTC/USDT"
          required
        />
        <label htmlFor="chart-timeframe">Timeframe</label>
        <select
          id="chart-timeframe"
          name="timeframe"
          value={formState.timeframe}
          onChange={(event) =>
            setFormState((state) => ({ ...state, timeframe: event.target.value }))
          }
        >
          {[
            "1m",
            "5m",
            "15m",
            "1h",
            "4h",
            "1d",
          ].map((tf) => (
            <option key={tf} value={tf}>
              {tf}
            </option>
          ))}
        </select>
        <fieldset>
          <legend>Indicateurs</legend>
          {((Object.keys(INDICATOR_PRESETS) as IndicatorName[])).map((indicator) => {
            const checked = formState.indicators.includes(indicator);
            return (
              <label key={indicator}>
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={(event) => {
                    setFormState((state) => {
                      if (event.target.checked) {
                        return {
                          ...state,
                          indicators: [...state.indicators, indicator],
                        };
                      }
                      return {
                        ...state,
                        indicators: state.indicators.filter((name) => name !== indicator),
                      };
                    });
                  }}
                />
                {indicator.toUpperCase()}
              </label>
            );
          })}
        </fieldset>
        <button type="submit" disabled={isSubmitting} data-testid="chart-start">
          {isSubmitting ? "Analyse en cours…" : "Lancer l'analyse"}
        </button>
      </form>
      {error ? (
        <p role="alert" className="chart-analysis__error" data-testid="chart-error">
          {error}
        </p>
      ) : null}
      <div className="chart-analysis__grid">
        <div ref={chartContainerRef} className="chart-canvas" data-testid="chart-candles" />
        <div ref={rsiContainerRef} className="chart-canvas" data-testid="chart-rsi" />
        <div ref={macdContainerRef} className="chart-canvas" data-testid="chart-macd" />
      </div>
      <section className="chart-analysis__sidebar">
        <h2>Résumé IA</h2>
        <article data-testid="analysis-summary">
          {activeSummary || "En attente de génération…"}
        </article>
        <h2>Niveaux détectés</h2>
        <ul data-testid="analysis-levels">{levels.map(renderLevel)}</ul>
        <h2>Figures chartistes</h2>
        <ul data-testid="analysis-patterns">
          {patterns.length === 0 ? <li>Aucun motif détecté</li> : patterns.map((name) => <li key={name}>{name}</li>)}
        </ul>
        <h2>Progression</h2>
        <ol data-testid="analysis-steps">
          {steps.map((step) => (
            <li key={step.name}>
              <strong>{step.name}</strong> – {step.status}
            </li>
          ))}
        </ol>
        <p data-testid="analysis-heartbeat">
          Dernier heartbeat : {lastHeartbeat ? new Date(lastHeartbeat).toLocaleTimeString() : "—"}
        </p>
      </section>
    </section>
  );
}
