import type { InferUITool, UIMessage } from "ai";
import { z } from "zod";
import type { ArtifactKind } from "@/components/artifact";
import type { createDocument } from "./ai/tools/create-document";
import type { createFinanceArtifact } from "./ai/tools/create-finance-artifact";
import type { createSearchArtifact } from "./ai/tools/create-search-artifact";
import type { getWeather } from "./ai/tools/get-weather";
import type { requestSuggestions } from "./ai/tools/request-suggestions";
import type { updateDocument } from "./ai/tools/update-document";
import type { Suggestion } from "./db/schema";
import type { AppUsage } from "./usage";

/**
 * Row description for OHLCV candles streamed by the backend.
 * Mirrors ``OhlcvRowPayload`` in the FastAPI schemas to keep rendering helpers type-safe.
 */
export type FinanceOhlcvRow = {
  ts: number;
  open: number;
  high: number;
  low: number;
  close: number;
  volume: number;
  previousClose: number;
  changeAbs: number;
  changePct: number;
  range: number;
  body: number;
  bodyPct: number;
  upperWick: number;
  lowerWick: number;
  direction: "bullish" | "bearish" | "neutral";
};

/** Aggregate range information for the analysed chart window. */
export type FinanceRangeSummary = {
  firstTs: number;
  lastTs: number;
  high: number;
  low: number;
  totalVolume: number;
};

/** Snapshot of a single candle enriched with analytics metrics. */
export type FinanceCandleSnapshot = FinanceOhlcvRow;

/**
 * Overlay series emitted by the indicator pipeline.
 * The identifiers follow the ``ema-<window>`` or ``sma-<window>`` convention.
 */
export type FinanceOverlaySeries = {
  id: string;
  type: "sma" | "ema";
  window: number;
  points: Array<{ ts: number; value: number | null }>;
};

/** Support or resistance level entry streamed to the finance artifact. */
export type FinanceLevel = {
  price: number | null;
  kind: string;
  strength: number;
  label: "fort" | "général";
  tsRange: [number, number];
};

/** Chart pattern metadata used to display heuristics such as head-and-shoulders. */
export type FinancePattern = {
  name: string;
  score: number;
  confidence: number;
  startTs: number;
  endTs: number;
  points: Array<[number, number]>;
  metadata: Record<string, unknown>;
};

/**
 * Pipeline step envelope describing lifecycle events (start/end) and diagnostics.
 * ``event`` reflects the SSE event name (e.g. ``step:start``).
 */
export type FinanceStepEnvelope = {
  event: string;
  payload?: {
    stage?: "ohlcv" | "indicators" | "levels" | "patterns" | "summary";
    description?: string | null;
    elapsed_ms?: number | null;
    metadata?: Record<string, unknown>;
  };
};

export type DataPart = { type: "append-message"; message: string };

export const messageMetadataSchema = z.object({
  createdAt: z.string(),
});

export type MessageMetadata = z.infer<typeof messageMetadataSchema>;

type weatherTool = InferUITool<typeof getWeather>;
type createDocumentTool = InferUITool<ReturnType<typeof createDocument>>;
type createFinanceArtifactTool = InferUITool<ReturnType<typeof createFinanceArtifact>>;
type createSearchArtifactTool = InferUITool<ReturnType<typeof createSearchArtifact>>;
type updateDocumentTool = InferUITool<ReturnType<typeof updateDocument>>;
type requestSuggestionsTool = InferUITool<
  ReturnType<typeof requestSuggestions>
>;

export type ChatTools = {
  getWeather: weatherTool;
  createDocument: createDocumentTool;
  createFinanceArtifact: createFinanceArtifactTool;
  createSearchArtifact: createSearchArtifactTool;
  updateDocument: updateDocumentTool;
  requestSuggestions: requestSuggestionsTool;
};

export type CustomUIDataTypes = {
  /**
   * Default AI SDK stream payloads replicated from the upstream template.
   * Keys map to ``data-${name}`` events emitted by the back-end or server tools.
   */
  textDelta: string;
  imageDelta: string;
  sheetDelta: string;
  codeDelta: string;
  suggestion: Suggestion;
  appendMessage: string;
  /** Identifier assigned to the currently streaming artifact. */
  id: string;
  /** Title communicated by the tool before streaming the content body. */
  title: string;
  /** Kind of artifact being rendered (text, code, finance, search, ...). */
  kind: ArtifactKind;
  /** Signal emitted by tools to reset the artifact content before streaming. */
  clear: null;
  /** Terminal marker signalling that the stream has finished. */
  finish: null;
  /** Aggregated usage metrics mirrored from the backend analytics. */
  usage: AppUsage;
  /**
   * Finance-specific payload describing OHLCV rows and metadata streamed from
   * the FastAPI SSE endpoint. Mirrors ``OhlcvChunk`` in the backend schemas.
   */
  "finance:ohlcv": {
    symbol: string;
    timeframe: string;
    rows: FinanceOhlcvRow[];
  };
  /** Range summary for the analysed window. */
  "finance:range": FinanceRangeSummary | null;
  /** Details about the candle currently highlighted in the UI. */
  "finance:selected": {
    selected?: FinanceCandleSnapshot | null;
    details?: FinanceCandleSnapshot[];
  };
  /** Indicator overlays and latest computed values. */
  "finance:indicators": {
    latest?: Record<string, Record<string, number>>;
    overlays?: FinanceOverlaySeries[];
  };
  /** Support and resistance levels keyed by label. */
  "finance:levels": Record<string, FinanceLevel[]>;
  /** Chart patterns grouped by pattern identifier. */
  "finance:patterns": Record<string, FinancePattern[]>;
  /** Lifecycle envelope for each processing step. */
  "finance:step": FinanceStepEnvelope;
  /** Incremental summary tokens streamed from the LLM. */
  "finance:token": string;
  /** Normalised batch of SearxNG search results. */
  "search:batch": Array<{
    title: string;
    url: string;
    snippet: string;
    source: string;
    score: number;
  }>;
  /** Structured error payload emitted by artefact handlers when failures arise. */
  error: { message?: string; code?: string };
};

export type ChatMessage = UIMessage<
  MessageMetadata,
  CustomUIDataTypes,
  ChatTools
>;

export type Attachment = {
  name: string;
  url: string;
  contentType: string;
};
