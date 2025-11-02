"use client";

import { useEffect, useMemo, useRef } from "react";
import type { DataUIPart } from "ai";
import { DataStreamProvider, useDataStream } from "@/components/data-stream-provider";
import type { CustomUIDataTypes } from "@/lib/types";

/**
 * Minimal representation of a search result as exposed by the search artefact.
 * Keeping the type aligned with {@link CustomUIDataTypes} guarantees the
 * Playwright harness exercises the exact payload shape produced in production.
 */
type SearchResult = CustomUIDataTypes["search:batch"][number];

type SearchHarnessProps = {
  /** Prompt forwarded to the FastAPI backend to seed the search. */
  query: string;
  /** Normalised search results returned by the backend. */
  results: SearchResult[];
};

type SearchDataPart = DataUIPart<CustomUIDataTypes>;

function SearchStreamEmitter({ results }: { results: SearchResult[] }) {
  const { setDataStream } = useDataStream();
  const hasEmittedRef = useRef(false);

  useEffect(() => {
    if (hasEmittedRef.current) {
      return;
    }
    hasEmittedRef.current = true;

    const parts: SearchDataPart[] = [
      { type: "data-search:batch", data: results },
      { type: "data-finish", data: null },
    ];

    setDataStream((current) => [...current, ...parts]);
  }, [results, setDataStream]);

  return null;
}

function SearchHarnessContent({ query, results }: SearchHarnessProps) {
  const { dataStream } = useDataStream();

  const finishCount = useMemo(
    () => dataStream.filter((part) => part.type === "data-finish").length,
    [dataStream],
  );

  return (
    <section aria-labelledby="search-harness-heading" className="space-y-4 p-6">
      <header className="space-y-1">
        <h1 id="search-harness-heading" data-testid="search-harness-heading" className="text-2xl font-semibold">
          Résultats de recherche Playwright
        </h1>
        <p data-testid="search-harness-query" className="text-muted-foreground">
          {query}
        </p>
      </header>

      <ul data-testid="search-results" className="space-y-3">
        {results.map((result, index) => (
          <li
            key={`${result.url}-${index}`}
            data-testid="search-result-card"
            className="rounded-md border border-border p-4 shadow-sm"
          >
            <a
              data-testid="search-result-title"
              className="text-lg font-medium text-primary"
              href={result.url}
              rel="noreferrer"
              target="_blank"
            >
              {result.title || "Résultat sans titre"}
            </a>
            <p data-testid="search-result-snippet" className="mt-1 text-sm text-muted-foreground">
              {result.snippet || "Aucun extrait disponible."}
            </p>
            <div className="mt-2 flex flex-wrap gap-3 text-xs uppercase tracking-wide text-muted-foreground">
              <span data-testid="search-result-source">{result.source || "source inconnue"}</span>
              <span data-testid="search-result-score">score: {result.score.toFixed(2)}</span>
            </div>
          </li>
        ))}
      </ul>

      <footer className="text-sm text-muted-foreground">
        <span data-testid="search-finish-count">Événements de fin reçus : {finishCount}</span>
      </footer>
    </section>
  );
}

export function SearchHarness(props: SearchHarnessProps) {
  return (
    <DataStreamProvider>
      <SearchStreamEmitter results={props.results} />
      <SearchHarnessContent {...props} />
    </DataStreamProvider>
  );
}
