import type { Metadata } from "next";

import { SearchHarness } from "./search-harness-client";

/** Default prompt forwarded to the FastAPI search endpoint for the harness. */
const SEARCH_PROMPT = "Recherche actus halving bitcoin 24h";

/**
 * Fallback dataset used when the upstream SearxNG instance cannot be reached.
 * Keeping a deterministic record prevents the Playwright suite from flaking
 * while still exercising the artefact rendering logic.
 */
const FALLBACK_RESULTS = [
  {
    title: "Bitcoin : les dernières actus sur le halving",
    url: "https://example.com/bitcoin-halving-news",
    snippet: "Synthèse fictive des tendances 24h autour du halving.",
    source: "fixture",
    score: 0.5,
  },
];

type SearchResult = (typeof FALLBACK_RESULTS)[number];

function resolveApiBase(): string {
  const candidates = [
    process.env.MCP_API_BASE,
    process.env.API_BASE_URL,
    "http://127.0.0.1:8000",
  ];
  const base = candidates.find((candidate) => candidate && candidate.length > 0);
  return (base ?? "http://127.0.0.1:8000").replace(/\/$/, "");
}

function buildHeaders(): HeadersInit {
  const headers: Record<string, string> = {
    Accept: "application/json",
    "X-Session-User": process.env.MCP_SESSION_USER || "regular",
  };
  const token = process.env.MCP_API_TOKEN || process.env.API_TOKEN;
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  return headers;
}

async function fetchSearchResults(query: string): Promise<SearchResult[]> {
  const apiBase = resolveApiBase();
  const url = new URL("/api/v1/search", apiBase);
  url.searchParams.set("q", query);
  url.searchParams.set("categories", "news,science");
  url.searchParams.set("time_range", "day");

  try {
    const response = await fetch(url.toString(), {
      headers: buildHeaders(),
      cache: "no-store",
    });
    if (!response.ok) {
      console.warn("[search-harness] backend responded with", response.status);
      return FALLBACK_RESULTS;
    }
    const payload = await response.json();
    const results = Array.isArray(payload?.results) ? payload.results : [];
    if (!results.length) {
      return FALLBACK_RESULTS;
    }
    return results.map((entry: Record<string, unknown>) => ({
      title: String(entry.title ?? ""),
      url: String(entry.url ?? ""),
      snippet: String(entry.snippet ?? entry.content ?? ""),
      source: String(entry.source ?? entry.engine ?? ""),
      score: Number.parseFloat(String(entry.score ?? "0")) || 0,
    }));
  } catch (error) {
    console.error("[search-harness] failed to fetch results", error);
    return FALLBACK_RESULTS;
  }
}

export const metadata: Metadata = {
  title: "Search Stream Harness",
  description:
    "Page dédiée aux scénarios Playwright vérifiant la diffusion des résultats SearxNG.",
};

export default async function SearchHarnessPage(): Promise<JSX.Element> {
  const results = await fetchSearchResults(SEARCH_PROMPT);
  return <SearchHarness query={SEARCH_PROMPT} results={results} />;
}
