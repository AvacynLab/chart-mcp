import { FormEvent, useMemo, useState } from "react";
import { z } from "zod";

/**
 * Metrics describing the performance of a simulated backtest.
 *
 * Values are expressed as ratios (e.g. ``0.42`` = ``42 %``) so the UI can
 * decide how to present them without additional context from the backend.
 */
export interface BacktestMetrics {
  readonly totalReturn: number;
  readonly cagr: number;
  readonly maxDrawdown: number;
  readonly winRate: number;
  readonly sharpe: number;
  readonly profitFactor: number;
}

/** Point composing the simulated equity curve. */
export interface EquityPoint {
  readonly ts: number;
  readonly equity: number;
}

/** Single trade extracted from the backtest execution log. */
export interface BacktestTrade {
  readonly entryTs: number;
  readonly exitTs: number;
  readonly entryPrice: number;
  readonly exitPrice: number;
  readonly returnPct: number;
}

/** Payload returned by the backend for the finance backtest artefact. */
export interface BacktestReportArtifactData {
  readonly symbol: string;
  readonly timeframe: string;
  readonly metrics: BacktestMetrics;
  readonly equityCurve: readonly EquityPoint[];
  readonly trades: readonly BacktestTrade[];
}

/** Parameters accepted when the user requests a new backtest run. */
export interface BacktestRetestParams {
  readonly fastWindow: number;
  readonly slowWindow: number;
  readonly feesBps: number;
  readonly slippageBps: number;
}

export interface BacktestReportArtifactProps {
  /** Artefact payload describing the simulated performance. */
  readonly artifact: BacktestReportArtifactData;
  /** Callback invoked after successful client-side validation. */
  readonly onRetest?: (params: BacktestRetestParams) => Promise<void> | void;
  /** Default parameter values surfaced in the retest form. */
  readonly defaultParams?: Partial<BacktestRetestParams>;
}

/**
 * Schema used to coerce and validate retest parameters before invoking the
 * backend. Using ``z.coerce.number`` allows the component to keep native HTML
 * inputs while still benefitting from numerical validation.
 */
const RetestSchema = z
  .object({
    fastWindow: z
      .coerce
      .number({
        invalid_type_error: "La fenêtre rapide doit être un entier.",
      })
      .int("La fenêtre rapide doit être un entier.")
      .min(2, "La fenêtre rapide doit être >= 2")
      .max(500, "La fenêtre rapide doit être <= 500"),
    slowWindow: z
      .coerce
      .number({
        invalid_type_error: "La fenêtre lente doit être un entier.",
      })
      .int("La fenêtre lente doit être un entier.")
      .min(3, "La fenêtre lente doit être >= 3")
      .max(1000, "La fenêtre lente doit être <= 1000"),
    feesBps: z
      .coerce
      .number({ invalid_type_error: "Les frais doivent être un nombre." })
      .min(0, "Les frais doivent être positifs.")
      .max(500, "Les frais doivent être <= 500 bps."),
    slippageBps: z
      .coerce
      .number({ invalid_type_error: "Le slippage doit être un nombre." })
      .min(0, "Le slippage doit être positif.")
      .max(500, "Le slippage doit être <= 500 bps."),
  })
  .superRefine((value, ctx) => {
    if (value.fastWindow >= value.slowWindow) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["fastWindow"],
        message: "La fenêtre rapide doit être strictement inférieure à la fenêtre lente.",
      });
    }
  });

/** Format helper used for displaying ratios as percentages. */
function formatPercent(value: number): string {
  return `${(value * 100).toFixed(2)} %`;
}

/** Format helper used for displaying equity values. */
function formatCurrency(value: number): string {
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2,
  }).format(value);
}

/** Format helper used for timestamps (seconds) rendered in tables. */
function formatTimestamp(ts: number): string {
  return new Date(ts * 1000).toLocaleString();
}

/**
 * Finance backtest artefact rendering aggregate metrics, trades and allowing
 * the user to trigger an additional simulation with validated parameters.
 */
export default function BacktestReportArtifact({
  artifact,
  onRetest,
  defaultParams,
}: BacktestReportArtifactProps): JSX.Element {
  const [formValues, setFormValues] = useState({
    fastWindow: String(defaultParams?.fastWindow ?? 50),
    slowWindow: String(defaultParams?.slowWindow ?? 200),
    feesBps: String(defaultParams?.feesBps ?? 0),
    slippageBps: String(defaultParams?.slippageBps ?? 0),
  });
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const equityExtrema = useMemo(() => {
    if (artifact.equityCurve.length === 0) {
      return null;
    }
    const start = artifact.equityCurve[0];
    const end = artifact.equityCurve[artifact.equityCurve.length - 1];
    return { start, end };
  }, [artifact.equityCurve]);

  async function handleSubmit(event: FormEvent<HTMLFormElement>): Promise<void> {
    event.preventDefault();
    if (!onRetest) {
      return;
    }

    setError(null);
    const result = RetestSchema.safeParse(formValues);
    if (!result.success) {
      const firstIssue = result.error.issues[0];
      setError(firstIssue?.message ?? "Paramètres invalides");
      return;
    }

    try {
      setSubmitting(true);
      await onRetest(result.data);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <section
      aria-label={`Rapport de backtest pour ${artifact.symbol}`}
      data-testid="finance-backtest-report"
      className="finance-backtest-report"
    >
      <header>
        <h2>{artifact.symbol}</h2>
        <p>Intervalle analysé : {artifact.timeframe}</p>
      </header>

      <table aria-describedby="backtest-metrics-caption">
        <caption id="backtest-metrics-caption">Métriques principales</caption>
        <thead>
          <tr>
            <th scope="col">Indicateur</th>
            <th scope="col">Valeur</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <th scope="row">Performance cumulée</th>
            <td>{formatPercent(artifact.metrics.totalReturn)}</td>
          </tr>
          <tr>
            <th scope="row">CAGR</th>
            <td>{formatPercent(artifact.metrics.cagr)}</td>
          </tr>
          <tr>
            <th scope="row">Max drawdown</th>
            <td>{formatPercent(artifact.metrics.maxDrawdown)}</td>
          </tr>
          <tr>
            <th scope="row">Taux de réussite</th>
            <td>{formatPercent(artifact.metrics.winRate)}</td>
          </tr>
          <tr>
            <th scope="row">Sharpe</th>
            <td>{artifact.metrics.sharpe.toFixed(2)}</td>
          </tr>
          <tr>
            <th scope="row">Profit factor</th>
            <td>{artifact.metrics.profitFactor.toFixed(2)}</td>
          </tr>
        </tbody>
      </table>

      <section aria-live="polite" className="equity-summary">
        <h3>Évolution du capital</h3>
        {equityExtrema ? (
          <p>
            De {formatCurrency(equityExtrema.start.equity)} ( {formatTimestamp(equityExtrema.start.ts)} ) à
            {" "}
            {formatCurrency(equityExtrema.end.equity)} ({formatTimestamp(equityExtrema.end.ts)})
          </p>
        ) : (
          <p>Aucune courbe d&apos;équité disponible.</p>
        )}
      </section>

      <section aria-live="polite" className="trades-list">
        <h3>Transactions</h3>
        {artifact.trades.length === 0 ? (
          <p>Aucun trade exécuté durant la période.</p>
        ) : (
          <table>
            <caption>Historique des positions</caption>
            <thead>
              <tr>
                <th scope="col">Entrée</th>
                <th scope="col">Sortie</th>
                <th scope="col">Prix entrée</th>
                <th scope="col">Prix sortie</th>
                <th scope="col">Performance</th>
              </tr>
            </thead>
            <tbody>
              {artifact.trades.map((trade) => (
                <tr key={`${trade.entryTs}-${trade.exitTs}`}>
                  <td>{formatTimestamp(trade.entryTs)}</td>
                  <td>{formatTimestamp(trade.exitTs)}</td>
                  <td>{formatCurrency(trade.entryPrice)}</td>
                  <td>{formatCurrency(trade.exitPrice)}</td>
                  <td>{formatPercent(trade.returnPct)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <form aria-label="Relancer le backtest" onSubmit={handleSubmit}>
        <fieldset disabled={submitting}>
          <legend>Re-tester la stratégie</legend>
          <div>
            <label htmlFor="fastWindow">Fenêtre rapide</label>
            <input
              id="fastWindow"
              name="fastWindow"
              type="number"
              min={2}
              max={500}
              value={formValues.fastWindow}
              onChange={(event) =>
                setFormValues((prev) => ({ ...prev, fastWindow: event.target.value }))
              }
              required
            />
          </div>
          <div>
            <label htmlFor="slowWindow">Fenêtre lente</label>
            <input
              id="slowWindow"
              name="slowWindow"
              type="number"
              min={3}
              max={1000}
              value={formValues.slowWindow}
              onChange={(event) =>
                setFormValues((prev) => ({ ...prev, slowWindow: event.target.value }))
              }
              required
            />
          </div>
          <div>
            <label htmlFor="feesBps">Frais (bps)</label>
            <input
              id="feesBps"
              name="feesBps"
              type="number"
              min={0}
              max={500}
              step={0.1}
              value={formValues.feesBps}
              onChange={(event) =>
                setFormValues((prev) => ({ ...prev, feesBps: event.target.value }))
              }
              required
            />
          </div>
          <div>
            <label htmlFor="slippageBps">Slippage (bps)</label>
            <input
              id="slippageBps"
              name="slippageBps"
              type="number"
              min={0}
              max={500}
              step={0.1}
              value={formValues.slippageBps}
              onChange={(event) =>
                setFormValues((prev) => ({ ...prev, slippageBps: event.target.value }))
              }
              required
            />
          </div>
          <button type="submit" data-testid="retest-button">
            {submitting ? "Re-test en cours..." : "Re-tester"}
          </button>
        </fieldset>
        {error ? (
          <p role="alert" data-testid="retest-error">
            {error}
          </p>
        ) : null}
      </form>
    </section>
  );
}
