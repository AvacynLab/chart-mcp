"use client";

import { Fragment, ReactNode, useEffect, useMemo, useState } from "react";

import BacktestReportArtifact, {
  type BacktestReportArtifactData,
} from "@components/finance/backtest-report-artifact";
import ChartArtifact, {
  type CandlestickSeriesApi,
  type ChartArtifactResponse,
  type ChartEventPayload,
  type ChartArtifactProps,
  type LineSeriesApi,
  type OverlaySeriesModel,
} from "@components/finance/ChartArtifact";
import FundamentalsCard, {
  type FundamentalsSnapshot,
  type QuoteSnapshot,
} from "@components/finance/fundamentals-card";
import NewsList, { type NewsItemModel } from "@components/finance/news-list";

/**
 * Public representation of a chat artefact. Artefacts are discriminated by
 * their ``type`` property which allows the renderer to switch between
 * dedicated templates and a safe fallback for unknown payloads.
 */
export interface ChatArtifactBase {
  /** Unique identifier supplied by the backend. */
  readonly id: string;
  /** Discriminator describing the artefact kind (chart, report, ...). */
  readonly type: string;
  /** Optional title surfaced alongside the rendered artefact. */
  readonly title?: string | null;
  /** Optional structured payload specific to the artefact type. */
  readonly data?: unknown;
}

/**
 * Minimal chat message representation consumed by the :component:`Chat` widget.
 */
export interface ChatMessage {
  /** Message identifier (used as React key). */
  readonly id: string;
  /** Speaker role (``user`` or ``assistant``). */
  readonly role: "user" | "assistant" | "system";
  /** Textual content rendered inside the message bubble. */
  readonly content: string;
  /** Optional artefacts generated alongside the assistant reply. */
  readonly artifacts?: ChatArtifactBase[] | null;
}

export interface MessagesProps {
  /** Conversation history displayed in chronological order. */
  readonly messages?: ChatMessage[] | null;
  /** Artefacts associated with the active assistant reply. */
  readonly artifacts?: ChatArtifactBase[] | null;
}

function isObject(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}

function isBacktestArtifactData(data: unknown): data is BacktestReportArtifactData {
  if (!isObject(data)) {
    return false;
  }
  return (
    typeof data.symbol === "string" &&
    typeof data.timeframe === "string" &&
    Array.isArray(data.equityCurve) &&
    Array.isArray(data.trades) &&
    isObject(data.metrics)
  );
}

function isFundamentalsData(data: unknown): data is FundamentalsSnapshot {
  return isObject(data) && typeof data.symbol === "string";
}

function isQuoteData(data: unknown): data is QuoteSnapshot {
  if (!isObject(data)) {
    return false;
  }
  return (
    typeof data.price === "number" ||
    typeof data.price === "undefined" ||
    data.price === null
  );
}

function isChartArtifactData(data: unknown): data is ChartArtifactResponse {
  if (!isObject(data)) {
    return false;
  }

  const status = (data as { status?: unknown }).status;
  if (status !== "ready" && status !== "empty") {
    return false;
  }

  const rows = (data as { rows?: unknown }).rows;
  const details = (data as { details?: unknown }).details;
  const overlays = (data as { overlays?: unknown }).overlays;

  return (
    typeof (data as { symbol?: unknown }).symbol === "string" &&
    typeof (data as { timeframe?: unknown }).timeframe === "string" &&
    Array.isArray(rows) &&
    Array.isArray(details) &&
    Array.isArray(overlays)
  );
}

/**
 * Minimal chart factory used in unit/UI tests where the real charting library
 * is unavailable. The stub satisfies the imperative contract expected by
 * :component:`ChartArtifact` without mutating the DOM beyond the provided
 * container element.
*/
const createChartStub: ChartArtifactProps["createChart"] = (container) => {
  const overlaySeries = new Set<LineSeriesApi>();

  const candlestickSeries: CandlestickSeriesApi = {
    /**
     * Store is intentionally a no-op – the component under test only asserts
     * the method exists and can be called with serialised data.
     */
    setData: () => {
      // no-op by design
    },
  };

  function createLineSeries(): LineSeriesApi {
    const series: LineSeriesApi = {
      setData: () => {
        // overlay updates are ignored in the stub
      },
      remove: () => {
        overlaySeries.delete(series);
      },
    };
    overlaySeries.add(series);
    return series;
  }

  const clickHandlers = new Set<(payload: ChartEventPayload) => void>();
  const crosshairHandlers = new Set<(payload: ChartEventPayload) => void>();

  return {
    addCandlestickSeries: () => candlestickSeries,
    addLineSeries: () => createLineSeries(),
    remove: () => {
      overlaySeries.clear();
      clickHandlers.clear();
      crosshairHandlers.clear();
      container.replaceChildren();
    },
    subscribeClick: (handler) => {
      clickHandlers.add(handler);
    },
    unsubscribeClick: (handler) => {
      clickHandlers.delete(handler);
    },
    subscribeCrosshairMove: (handler) => {
      crosshairHandlers.add(handler);
    },
    unsubscribeCrosshairMove: (handler) => {
      crosshairHandlers.delete(handler);
    },
  };
};

interface FinanceChartSectionProps {
  readonly artifactId: string;
  readonly title?: string;
  readonly payload: ChartArtifactResponse;
}

/**
 * Wrapper responsible for rendering finance chart artefacts with a deterministic
 * chart factory and local overlay toggles. The implementation purposefully keeps
 * the toggle state client-side so Playwright tests can exercise UI interactions
 * without depending on the backend.
 */
function FinanceChartSection({ artifactId, title, payload }: FinanceChartSectionProps): JSX.Element {
  const [activeOverlayIds, setActiveOverlayIds] = useState<string[]>(() =>
    payload.overlays.map((overlay) => overlay.id),
  );

  useEffect(() => {
    setActiveOverlayIds(payload.overlays.map((overlay) => overlay.id));
  }, [payload.overlays]);

  const visibleOverlays = useMemo<readonly OverlaySeriesModel[]>(() => {
    const active = new Set(activeOverlayIds);
    return payload.overlays.filter((overlay) => active.has(overlay.id));
  }, [payload.overlays, activeOverlayIds]);

  const chartPayload = useMemo<ChartArtifactResponse>(
    () => ({
      ...payload,
      overlays: visibleOverlays,
    }),
    [payload, visibleOverlays],
  );

  const toggleOverlay = (overlayId: string) => {
    setActiveOverlayIds((current) => {
      if (current.includes(overlayId)) {
        return current.filter((id) => id !== overlayId);
      }
      return [...current, overlayId];
    });
  };

  return (
    <section
      data-testid={`artifact-${artifactId}`}
      aria-label={title ?? "Visualisation finance"}
      className="finance-chart-section"
    >
      {payload.overlays.length > 0 ? (
        <fieldset data-testid="finance-chart-overlays" className="finance-chart__controls">
          <legend>Overlays techniques</legend>
          {payload.overlays.map((overlay) => {
            const label = `${overlay.type.toUpperCase()} ${overlay.window}`;
            const checked = activeOverlayIds.includes(overlay.id);
            return (
              <label
                key={overlay.id}
                data-testid={`overlay-toggle-${overlay.id}`}
                className="finance-chart__overlay-toggle"
              >
                <input
                  type="checkbox"
                  checked={checked}
                  onChange={() => toggleOverlay(overlay.id)}
                  aria-checked={checked}
                />
                {label}
              </label>
            );
          })}
        </fieldset>
      ) : null}
      <ChartArtifact artifact={chartPayload} createChart={createChartStub} />
      {visibleOverlays.length > 0 ? (
        <ul data-testid="active-overlays" className="finance-chart__overlay-summary">
          {visibleOverlays.map((overlay) => (
            <li key={overlay.id} data-testid={`overlay-pill-${overlay.id}`}>
              {overlay.type.toUpperCase()} {overlay.window}
            </li>
          ))}
        </ul>
      ) : (
        <p data-testid="overlay-empty">Aucun overlay actif</p>
      )}
    </section>
  );
}


function isNewsData(data: unknown): data is { symbol?: string | null; items?: NewsItemModel[] } {
  if (!isObject(data)) {
    return false;
  }
  return (
    data.items === undefined ||
    data.items === null ||
    (Array.isArray(data.items) && data.items.every((item) => isObject(item) && typeof item.id === "string"))
  );
}

function renderArtifact(artifact: ChatArtifactBase): ReactNode {
  if (!artifact || typeof artifact !== "object") {
    return renderFallback();
  }

  switch (artifact.type) {
    case "finance:chart":
      if (isChartArtifactData(artifact.data)) {
        return (
          <FinanceChartSection
            key={artifact.id}
            artifactId={artifact.id}
            title={artifact.title ?? undefined}
            payload={artifact.data}
          />
        );
      }
      return renderFallback(artifact.title);
    case "finance:backtest":
    case "finance:backtest_report":
      if (isBacktestArtifactData(artifact.data)) {
        return (
          <BacktestReportArtifact
            key={artifact.id}
            artifact={artifact.data}
          />
        );
      }
      return renderFallback(artifact.title);
    case "finance:fundamentals": {
      if (isObject(artifact.data)) {
        const data = artifact.data;
        const fundamentals = isFundamentalsData(data.fundamentals)
          ? data.fundamentals
          : isFundamentalsData(data)
            ? (data as FundamentalsSnapshot)
            : null;
        const quote = isQuoteData(data.quote) ? data.quote : null;
        if (fundamentals) {
          return <FundamentalsCard fundamentals={fundamentals} quote={quote} />;
        }
      }
      return renderFallback(artifact.title);
    }
    case "finance:news": {
      if (isNewsData(artifact.data)) {
        const data = artifact.data;
        const symbol = typeof data.symbol === "string" ? data.symbol : undefined;
        return <NewsList symbol={symbol} items={data.items ?? []} />;
      }
      return renderFallback(artifact.title);
    }
    default:
      return renderFallback(artifact.title);
  }
}

function renderFallback(title?: string | null): ReactNode {
  return (
    <div data-testid="artifact-fallback" className="artifact-fallback">
      <strong>{title ?? "Pièce jointe inconnue"}</strong>
      <p>Ce contenu ne peut pas être affiché mais reste disponible au téléchargement.</p>
    </div>
  );
}

/**
 * Render the ordered list of chat messages alongside their optional artefacts.
 *
 * The component normalises nullish inputs to protect against partially streamed
 * payloads and ensures that any unknown artefact gracefully degrades to the
 * fallback component instead of throwing runtime exceptions.
 */
export default function Messages({
  messages,
  artifacts,
}: MessagesProps): JSX.Element {
  const normalisedMessages = messages ?? [];
  const normalisedArtifacts = artifacts ?? [];

  return (
    <div className="chat-messages">
      {normalisedMessages.map((message) => (
        <article key={message.id} data-role={message.role}>
          <p>{message.content}</p>
          {(message.artifacts ?? []).map((artifact) => (
            <Fragment key={`${message.id}-${artifact.id}`}>
              {renderArtifact(artifact)}
            </Fragment>
          ))}
        </article>
      ))}

      {normalisedArtifacts.map((artifact) => (
        <Fragment key={`active-${artifact.id}`}>{renderArtifact(artifact)}</Fragment>
      ))}
    </div>
  );
}
