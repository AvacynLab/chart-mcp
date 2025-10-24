/**
 * Fundamental metrics for a given symbol. All fields are optional to ensure the
 * UI remains resilient when upstream data is incomplete.
 */
export interface FundamentalsSnapshot {
  readonly symbol: string;
  readonly marketCap?: number | null;
  readonly peRatio?: number | null;
  readonly dividendYield?: number | null;
  readonly week52High?: number | null;
  readonly week52Low?: number | null;
}

/** Optional quote data surfaced alongside the fundamentals snapshot. */
export interface QuoteSnapshot {
  readonly price?: number | null;
  readonly changePct?: number | null;
  readonly currency?: string | null;
}

export interface FundamentalsCardProps {
  /** Fundamental dataset returned by the finance API. */
  readonly fundamentals?: FundamentalsSnapshot | null;
  /** Optional quote information to enrich the card. */
  readonly quote?: QuoteSnapshot | null;
}

/** Format helper returning a currency string or a placeholder. */
function formatCurrency(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  return new Intl.NumberFormat("fr-FR", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(value);
}

/** Format helper returning a percentage string or a placeholder. */
function formatPercent(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  return `${(value * 100).toFixed(2)} %`;
}

/** Format helper returning a raw number string or a placeholder. */
function formatNumber(value: number | null | undefined): string {
  if (value === null || value === undefined) {
    return "—";
  }
  return new Intl.NumberFormat("fr-FR", { maximumFractionDigits: 2 }).format(value);
}

/**
 * Fundamentals card rendered inside the assistant artefact panel. The component
 * focuses on clarity and resilience: each metric includes a label, units, and a
 * safe fallback when data is missing.
 */
export default function FundamentalsCard({
  fundamentals,
  quote,
}: FundamentalsCardProps): JSX.Element {
  if (!fundamentals) {
    return (
      <section data-testid="fundamentals-card-empty">
        <h2>Données fondamentales indisponibles</h2>
        <p>Cette société ne dispose pas encore d&apos;informations exploitables.</p>
      </section>
    );
  }

  const changeLabel = quote?.changePct ?? null;

  return (
    <section data-testid="fundamentals-card" aria-label={`Données fondamentales ${fundamentals.symbol}`}>
      <header>
        <h2>{fundamentals.symbol}</h2>
        {quote?.price !== undefined && quote?.price !== null ? (
          <p>
            Cours : {formatCurrency(quote.price)} (
            <span aria-live="polite">{formatPercent(changeLabel)}</span>)
          </p>
        ) : (
          <p>Cours : —</p>
        )}
      </header>
      <dl>
        <div>
          <dt>Capitalisation</dt>
          <dd>{formatCurrency(fundamentals.marketCap ?? null)}</dd>
        </div>
        <div>
          <dt>PER</dt>
          <dd>{formatNumber(fundamentals.peRatio ?? null)}</dd>
        </div>
        <div>
          <dt>Rendement dividende</dt>
          <dd>{formatPercent(fundamentals.dividendYield ?? null)}</dd>
        </div>
        <div>
          <dt>Plus haut 52s</dt>
          <dd>{formatCurrency(fundamentals.week52High ?? null)}</dd>
        </div>
        <div>
          <dt>Plus bas 52s</dt>
          <dd>{formatCurrency(fundamentals.week52Low ?? null)}</dd>
        </div>
      </dl>
    </section>
  );
}
