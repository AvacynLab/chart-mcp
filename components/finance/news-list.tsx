/** Single news article returned by the finance API. */
export interface NewsItemModel {
  readonly id: string;
  readonly title?: string | null;
  readonly url?: string | null;
  readonly publishedAt?: string | null;
}

export interface NewsListProps {
  /** Symbol the news relate to (used for labelling). */
  readonly symbol?: string | null;
  /** Collection of news items (may be empty). */
  readonly items?: readonly NewsItemModel[] | null;
}

/** Format helper converting an ISO datetime string into a friendly label. */
function formatDate(value: string | null | undefined): string {
  if (!value) {
    return "Date inconnue";
  }
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) {
    return "Date inconnue";
  }
  return date.toLocaleString();
}

/**
 * News list component capable of degrading gracefully when information is
 * missing. Articles are rendered as accessible list items with explicit dates
 * and resilient fallbacks for broken URLs or titles.
 */
export default function NewsList({ symbol, items }: NewsListProps): JSX.Element {
  const entries = items ?? [];

  if (entries.length === 0) {
    return (
      <section data-testid="finance-news-empty">
        <h2>Actualités {symbol ?? "financières"}</h2>
        <p>Aucun article disponible pour le moment.</p>
      </section>
    );
  }

  return (
    <section data-testid="finance-news" aria-label={`Actualités ${symbol ?? "financières"}`}>
      <h2>Actualités {symbol ?? "financières"}</h2>
      <ul>
        {entries.map((item) => {
          const title = item.title?.trim() || "Titre indisponible";
          const href = item.url ?? undefined;

          return (
            <li key={item.id}>
              <article>
                <h3>
                  {href ? (
                    <a href={href} target="_blank" rel="noreferrer">
                      {title}
                    </a>
                  ) : (
                    title
                  )}
                </h3>
                <p>{formatDate(item.publishedAt)}</p>
              </article>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
