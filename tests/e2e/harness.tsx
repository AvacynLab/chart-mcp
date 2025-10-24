import { useEffect, useMemo, useState } from "react";
import ReactDOM from "react-dom/client";

import Chat from "../../components/chat";
import type { ChatArtifactBase } from "../../components/messages";
import type {
  ChartArtifactResponse,
  ChartCandleDetails,
} from "../../components/finance/finance-chart-artifact";
import type { BacktestReportArtifactData } from "../../components/finance/backtest-report-artifact";
import type {
  FundamentalsSnapshot,
  QuoteSnapshot,
} from "../../components/finance/fundamentals-card";
import type { NewsItemModel } from "../../components/finance/news-list";

/** Shape of the backtest response returned by the finance API. */
interface BacktestResponseBody extends BacktestReportArtifactData {}

/** Response structure returned by the finance fundamentals endpoint. */
interface FundamentalsResponseBody extends FundamentalsSnapshot {}

/** Response structure returned by the quote endpoint. */
interface QuoteResponseBody extends QuoteSnapshot {
  readonly symbol: string;
  readonly updatedAt: string;
}

/** Response structure returned by the news endpoint. */
interface NewsResponseBody {
  readonly symbol: string;
  readonly items: readonly NewsItemModel[];
}

/** Simple discriminated union describing the harness loading state. */
type HarnessStatus = "idle" | "loading" | "ready" | "error";

/**
 * React harness rendered exclusively during Playwright runs.
 *
 * The component mirrors the behaviour of the real chat experience by fetching
 * the finance artefacts from the backend endpoints and surfacing them through
 * the :component:`Chat` widget. A set of deterministic buttons allows the test
 * suite to switch the active candle without depending on the underlying chart
 * implementation.
 */
function FinanceChatHarness(): JSX.Element {
  const [status, setStatus] = useState<HarnessStatus>("idle");
  const [chart, setChart] = useState<ChartArtifactResponse | null>(null);
  const [backtest, setBacktest] = useState<BacktestResponseBody | null>(null);
  const [fundamentals, setFundamentals] = useState<FundamentalsSnapshot | null>(
    null,
  );
  const [quote, setQuote] = useState<QuoteSnapshot | null>(null);
  const [news, setNews] = useState<NewsResponseBody | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [selectedTs, setSelectedTs] = useState<number | null>(null);

  useEffect(() => {
    async function load(): Promise<void> {
      setStatus("loading");
      setError(null);

      try {
        const overlayPayload = encodeURIComponent(
          JSON.stringify([
            { id: "sma-50", type: "sma", window: 50 },
            { id: "sma-200", type: "sma", window: 200 },
            { id: "ema-21", type: "ema", window: 21 },
          ]),
        );

        const [chartRes, backtestRes, fundamentalsRes, quoteRes, newsRes] =
          await Promise.all([
            fetch(
              `/api/v1/finance/chart?symbol=BTCUSD&timeframe=1d&limit=200&overlays=${overlayPayload}`,
            ),
            fetch(`/api/v1/finance/backtest`, {
              method: "POST",
              headers: { "Content-Type": "application/json" },
              body: JSON.stringify({
                symbol: "AAPL",
                timeframe: "1d",
                start: "2020-01-01",
                end: "2024-01-01",
                limit: 1000,
                feesBps: 25,
                slippageBps: 10,
                strategy: {
                  kind: "sma_crossover",
                  parameters: {
                    fastWindow: 50,
                    slowWindow: 200,
                  },
                },
              }),
            }),
            fetch(`/api/v1/finance/fundamentals?symbol=NVDA`),
            fetch(`/api/v1/finance/quote?symbol=NVDA`),
            fetch(`/api/v1/finance/news?symbol=NVDA&limit=3`),
          ]);

        if (!chartRes.ok) {
          throw new Error(`chart request failed: ${chartRes.status}`);
        }
        if (!backtestRes.ok) {
          throw new Error(`backtest request failed: ${backtestRes.status}`);
        }
        if (!fundamentalsRes.ok) {
          throw new Error(`fundamentals request failed: ${fundamentalsRes.status}`);
        }
        if (!quoteRes.ok) {
          throw new Error(`quote request failed: ${quoteRes.status}`);
        }
        if (!newsRes.ok) {
          throw new Error(`news request failed: ${newsRes.status}`);
        }

        const chartJson = (await chartRes.json()) as ChartArtifactResponse;
        const backtestJson = (await backtestRes.json()) as BacktestResponseBody;
        const fundamentalsJson = (await fundamentalsRes.json()) as FundamentalsResponseBody;
        const quoteJson = (await quoteRes.json()) as QuoteResponseBody;
        const newsJson = (await newsRes.json()) as NewsResponseBody;

        setChart(chartJson);
        setBacktest(backtestJson);
        setFundamentals(fundamentalsJson);
        setQuote({
          price: quoteJson.price,
          changePct: quoteJson.changePct,
          currency: quoteJson.currency,
        });
        setNews(newsJson);
        setSelectedTs(chartJson.selected?.ts ?? null);
        setStatus("ready");
      } catch (caughtError) {
        console.error("Unable to bootstrap the finance harness", caughtError);
        setError("Impossible de charger les données financières de démonstration.");
        setStatus("error");
      }
    }

    void load();
  }, []);

  const resolvedChart = useMemo<ChartArtifactResponse | null>(() => {
    if (!chart) {
      return null;
    }

    if (selectedTs === null) {
      return chart;
    }

    const selectedDetail: ChartCandleDetails | null =
      chart.details.find((detail) => detail.ts === selectedTs) ?? null;

    return {
      ...chart,
      selected: selectedDetail,
    };
  }, [chart, selectedTs]);

  const artifacts = useMemo<ChatArtifactBase[]>(() => {
    if (!resolvedChart || !backtest || !fundamentals || !news) {
      return [];
    }

    return [
      {
        id: "chart-btcusd",
        type: "finance:chart",
        title: "BTCUSD 1D",
        data: resolvedChart,
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
    ];
  }, [resolvedChart, backtest, fundamentals, quote, news]);

  if (status === "loading" || status === "idle") {
    return <p data-testid="harness-loading">Chargement des artefacts…</p>;
  }

  if (status === "error" || error) {
    return (
      <div data-testid="harness-error" role="alert">
        {error ?? "Une erreur inattendue est survenue."}
      </div>
    );
  }

  return (
    <main>
      <section data-testid="candle-controls" aria-label="Contrôles de sélection de bougie">
        <h1>Démo finance</h1>
        <p>Choisissez une bougie pour mettre à jour le panneau de détails.</p>
        <div>
          {resolvedChart.details.map((detail) => (
            <button
              key={detail.ts}
              type="button"
              data-testid={`select-candle-${detail.ts}`}
              onClick={() => setSelectedTs(detail.ts)}
            >
              Sélection {new Date(detail.ts).toLocaleString()}
            </button>
          ))}
        </div>
      </section>

      <Chat
        initialMessages={[
          {
            id: "assistant-initial",
            role: "assistant",
            content: "Voici les artefacts financiers demandés.",
            artifacts,
          },
        ]}
        activeArtifacts={[]}
      />
    </main>
  );
}

const root = document.getElementById("root");

if (!root) {
  throw new Error("Root container missing from Playwright harness");
}

ReactDOM.createRoot(root).render(<FinanceChatHarness />);

