"use client";

import { useMemo } from "react";
import { ColorType, createChart } from "lightweight-charts";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Skeleton } from "@/components/ui/skeleton";
import { Artifact } from "@/components/create-artifact";
import type { UIArtifact } from "@/components/artifact";
import FinanceChartArtifact, {
  type ChartApi,
  type ChartArtifactResponse,
  type ChartCandleDetails,
  type ChartRangeModel,
  type OhlcvRow,
  type OverlayPointModel,
  type OverlaySeriesModel,
} from "~~/chart-components/finance-chart-artifact";

export type FinanceStepDelta = {
  event: string;
  payload: unknown;
};

type StreamLevel = {
  price: number | null;
  kind: string;
  strength: number;
  label: string;
  tsRange: [number, number];
};

type StreamPattern = {
  name: string;
  score: number;
  confidence: number;
  startTs: number;
  endTs: number;
  points: Array<[number, number]>;
  metadata?: Record<string, unknown>;
};

type FinanceMetadata = {
  chart: ChartArtifactResponse;
  steps: FinanceStepDelta[];
  summaryTokens: string[];
  indicators: Record<string, Record<string, number>>;
  levels: Record<string, StreamLevel[]>;
  patterns: Record<string, StreamPattern[]>;
  error?: string;
};

function createEmptyChart(): ChartArtifactResponse {
  return {
    status: "empty",
    symbol: "",
    timeframe: "",
    rows: [],
    range: null,
    selected: null,
    details: [],
    overlays: [],
  };
}

function createInitialMetadata(): FinanceMetadata {
  return {
    chart: createEmptyChart(),
    steps: [],
    summaryTokens: [],
    indicators: {},
    levels: {},
    patterns: {},
    error: undefined,
  };
}

function mapOhlcvRow(row: OhlcvRow): OhlcvRow {
  return {
    ts: row.ts,
    open: row.open,
    high: row.high,
    low: row.low,
    close: row.close,
    volume: row.volume,
  };
}

function mapRange(range: ChartRangeModel | null | undefined): ChartRangeModel | null {
  if (!range) {
    return null;
  }
  return {
    firstTs: range.firstTs,
    lastTs: range.lastTs,
    high: range.high,
    low: range.low,
    totalVolume: range.totalVolume,
  };
}

function mapCandle(payload: any): ChartCandleDetails {
  return {
    ts: Number(payload.ts),
    open: Number(payload.open),
    high: Number(payload.high),
    low: Number(payload.low),
    close: Number(payload.close),
    volume: Number(payload.volume),
    previousClose: Number(payload.previousClose ?? payload.previous_close ?? payload.prevClose ?? 0),
    changeAbs: Number(payload.changeAbs ?? payload.change_abs ?? 0),
    changePct: Number(payload.changePct ?? payload.change_pct ?? 0),
    range: Number(payload.range ?? payload.trading_range ?? 0),
    body: Number(payload.body ?? 0),
    bodyPct: Number(payload.bodyPct ?? payload.body_pct ?? 0),
    upperWick: Number(payload.upperWick ?? payload.upper_wick ?? 0),
    lowerWick: Number(payload.lowerWick ?? payload.lower_wick ?? 0),
    direction:
      payload.direction === "bearish"
        ? "bearish"
        : payload.direction === "bullish"
          ? "bullish"
          : "neutral",
  };
}

function mapOverlayPoint(point: any): OverlayPointModel {
  return {
    ts: Number(point.ts),
    value: typeof point.value === "number" ? point.value : point.value === null ? null : Number(point.value ?? 0),
  };
}

function mapOverlaySeries(series: any): OverlaySeriesModel {
  return {
    id: String(series.identifier ?? series.id ?? "overlay"),
    type: series.kind === "ema" ? "ema" : "sma",
    window: Number(series.window ?? 0),
    points: Array.isArray(series.points) ? series.points.map(mapOverlayPoint) : [],
  };
}

function buildChartFactory(): (container: HTMLElement) => ChartApi {
  return (container: HTMLElement): ChartApi => {
    const chart = createChart(container, {
      autoSize: true,
      layout: {
        background: { type: ColorType.Solid, color: "transparent" },
        textColor: "#CBD5F5",
      },
      grid: {
        horzLines: { color: "#1E293B" },
        vertLines: { color: "#1E293B" },
      },
      timeScale: {
        borderColor: "#334155",
      },
      rightPriceScale: {
        borderColor: "#334155",
      },
    });
    return chart as unknown as ChartApi;
  };
}

function renderLevels(levels: Record<string, StreamLevel[]>): JSX.Element | null {
  const entries = Object.entries(levels);
  if (!entries.length) {
    return null;
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Niveaux détectés</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-3">
        {entries.map(([kind, items]) => (
          <div key={kind} className="space-y-1">
            <p className="text-sm font-medium text-slate-300">{kind}</p>
            <div className="flex flex-wrap gap-2">
              {items.map((item, index) => (
                <Badge key={`${kind}-${index}`} variant="outline">
                  {item.price ? item.price.toFixed(2) : "?"} · force {item.strength.toFixed(2)}
                </Badge>
              ))}
            </div>
          </div>
        ))}
      </CardContent>
    </Card>
  );
}

function renderPatterns(patterns: Record<string, StreamPattern[]>): JSX.Element | null {
  const entries = Object.entries(patterns);
  if (!entries.length) {
    return null;
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Figures chartistes</CardTitle>
      </CardHeader>
      <CardContent className="flex flex-col gap-2">
        {entries.flatMap(([name, items]) =>
          items.map((pattern, index) => (
            <div key={`${name}-${index}`} className="rounded border border-slate-700 p-2 text-sm text-slate-200">
              <p className="font-semibold">{pattern.name}</p>
              <p className="text-xs text-slate-400">
                Confiance {pattern.confidence.toFixed(2)} · Score {pattern.score.toFixed(2)}
              </p>
            </div>
          )),
        )}
      </CardContent>
    </Card>
  );
}

function renderSummary(content: string, isStreaming: boolean): JSX.Element {
  if (!content && isStreaming) {
    return <Skeleton className="h-24 w-full" />;
  }
  return (
    <Card>
      <CardHeader>
        <CardTitle>Résumé IA</CardTitle>
      </CardHeader>
      <CardContent>
        <p className="whitespace-pre-line text-sm leading-relaxed text-slate-200">{content || "En attente du flux..."}</p>
      </CardContent>
    </Card>
  );
}

export const financeArtifact = new Artifact<"finance", FinanceMetadata>({
  kind: "finance",
  description: "Analyse de marché en direct avec graphiques, indicateurs et résumé tokenisé.",
  initialize: async ({ setMetadata }) => {
    setMetadata(createInitialMetadata());
  },
  onStreamPart: ({ streamPart, setMetadata, setArtifact }) => {
    switch (streamPart.type) {
      case "data-clear": {
        setMetadata(() => createInitialMetadata());
        setArtifact((draft) => ({
          ...draft,
          content: "",
          status: "streaming",
        }));
        break;
      }
      case "data-finance:ohlcv": {
        const payload = streamPart.data;
        setMetadata((state) => {
          const rows = Array.isArray(payload.rows) ? payload.rows.map(mapOhlcvRow) : [];
          return {
            ...state,
            chart: {
              status: rows.length ? "ready" : "empty",
              symbol: String(payload.symbol ?? state.chart.symbol ?? ""),
              timeframe: String(payload.timeframe ?? state.chart.timeframe ?? ""),
              rows,
              range: state.chart.range,
              selected: state.chart.selected,
              details: state.chart.details,
              overlays: state.chart.overlays,
            },
            error: undefined,
          };
        });
        setArtifact((draft: UIArtifact) => ({
          ...draft,
          isVisible: true,
          status: "streaming",
        }));
        break;
      }
      case "data-finance:range": {
        const payload = streamPart.data;
        setMetadata((state) => ({
          ...state,
          chart: {
            ...state.chart,
            range: mapRange(payload),
          },
        }));
        break;
      }
      case "data-finance:selected": {
        const payload = streamPart.data;
        const selected = payload?.selected ? mapCandle(payload.selected) : null;
        const details = Array.isArray(payload?.details) ? payload.details.map(mapCandle) : [];
        setMetadata((state) => ({
          ...state,
          chart: {
            ...state.chart,
            selected,
            details,
          },
        }));
        break;
      }
      case "data-finance:indicators": {
        const payload = streamPart.data;
        const overlays = Array.isArray(payload.overlays) ? payload.overlays.map(mapOverlaySeries) : [];
        setMetadata((state) => ({
          ...state,
          indicators: payload.latest ?? state.indicators,
          chart: {
            ...state.chart,
            overlays,
          },
        }));
        break;
      }
      case "data-finance:levels": {
        const payload = streamPart.data;
        setMetadata((state) => ({
          ...state,
          levels: payload,
        }));
        break;
      }
      case "data-finance:patterns": {
        const payload = streamPart.data;
        setMetadata((state) => ({
          ...state,
          patterns: payload,
        }));
        break;
      }
      case "data-finance:step": {
        const payload = streamPart.data;
        setMetadata((state) => ({
          ...state,
          steps: [...state.steps, { event: String(payload.event ?? "unknown"), payload: payload.payload }],
        }));
        break;
      }
      case "data-finance:token": {
        const tokenText = typeof streamPart.data === "string" ? streamPart.data : "";
        if (!tokenText) {
          break;
        }
        setMetadata((state) => ({
          ...state,
          summaryTokens: [...state.summaryTokens, tokenText],
        }));
        setArtifact((draft) => ({
          ...draft,
          content: `${draft.content ?? ""}${tokenText}`,
          isVisible: true,
          status: "streaming",
        }));
        break;
      }
      case "data-finish": {
        setArtifact((draft) => ({
          ...draft,
          content: (draft.content ?? "").trim(),
          isVisible: true,
          status: "idle",
        }));
        break;
      }
      case "data-error": {
        const errorPayload = streamPart.data ?? {};
        setMetadata((state) => ({
          ...state,
          error: String(errorPayload.message ?? "Une erreur inattendue est survenue."),
        }));
        setArtifact((draft) => ({
          ...draft,
          status: "idle",
        }));
        break;
      }
      default:
        break;
    }
  },
  content: ({ metadata, status, content }) => {
    const chartFactory = useMemo(buildChartFactory, []);
    const summary = useMemo(() => metadata.summaryTokens.join(""), [metadata.summaryTokens]);
    return (
      <div className="flex flex-col gap-6 p-4 lg:p-8">
        {metadata.error ? (
          <Card className="border-red-500/40 bg-red-900/10">
            <CardHeader>
              <CardTitle>Erreur finance</CardTitle>
            </CardHeader>
            <CardContent>
              <p className="text-sm text-red-200">{metadata.error}</p>
            </CardContent>
          </Card>
        ) : null}
        <div className="grid gap-6 lg:grid-cols-[2fr,1fr]">
          <Card className="overflow-hidden">
            <CardHeader>
              <CardTitle>
                {metadata.chart.symbol || "Symbole"} · {metadata.chart.timeframe || "?"}
              </CardTitle>
            </CardHeader>
            <CardContent className="h-[360px]">
              <FinanceChartArtifact artifact={metadata.chart} createChart={chartFactory} />
            </CardContent>
          </Card>
          <div className="flex flex-col gap-4">
            {renderSummary(summary || content, status === "streaming")}
            {renderLevels(metadata.levels)}
            {renderPatterns(metadata.patterns)}
          </div>
        </div>
      </div>
    );
  },
  actions: [],
  toolbar: [],
});
