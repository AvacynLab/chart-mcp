/**
 * Server-side handler for the search artefact.
 *
 * It issues a single HTTP request against the FastAPI `/api/v1/search` route
 * and forwards the normalised results to the UI stream so the client renders
 * the search cards immediately.
 */
import { createDocumentHandler } from "@/lib/artifacts/server";
import { consumeSearchArtifactConfig } from "@/lib/artifacts/search-config";

const DEFAULT_BASE_URL = "http://localhost:8000";

function resolveApiBase(): string {
  const candidates = [
    process.env.MCP_API_BASE,
    process.env.NEXT_PUBLIC_API_BASE_URL,
    DEFAULT_BASE_URL,
  ];
  const base = candidates.find((value) => value && value.length > 0) ?? DEFAULT_BASE_URL;
  return base.replace(/\/$/, "");
}

function resolveApiHeaders(): Record<string, string> {
  const headers: Record<string, string> = { Accept: "application/json" };
  const token =
    process.env.MCP_API_TOKEN ||
    process.env.API_TOKEN ||
    process.env.NEXT_PUBLIC_API_TOKEN;
  if (token) {
    headers.Authorization = `Bearer ${token}`;
  }
  const sessionUser = process.env.MCP_SESSION_USER || "regular";
  headers["X-Session-User"] = sessionUser;
  return headers;
}

export const searchDocumentHandler = createDocumentHandler<"search">({
  kind: "search",
  onCreateDocument: async ({ id, title, dataStream }) => {
    const config = consumeSearchArtifactConfig(id);
    if (!config) {
      const message = "No search configuration found for document";
      dataStream.write({
        type: "data-error",
        data: { code: "search_missing_config", message },
      });
      throw new Error(message);
    }

    const params = new URLSearchParams({ q: config.query });
    if (config.categories?.length) {
      params.set("categories", config.categories.join(","));
    }
    if (config.timeRange) {
      params.set("time_range", config.timeRange);
    }

    const url = `${resolveApiBase()}/api/v1/search?${params.toString()}`;

    try {
      const response = await fetch(url, {
        headers: resolveApiHeaders(),
        cache: "no-store",
      });
      if (!response.ok) {
        const message = `Search request failed with status ${response.status}`;
        dataStream.write({
          type: "data-error",
          data: { code: "search_request_failed", message },
        });
        throw new Error(message);
      }

      const payload = await response.json();
      const results = payload?.results ?? [];
      dataStream.write({ type: "data-search:batch", data: results });
      dataStream.write({ type: "data-finish", data: null, transient: true });
      if (Array.isArray(results) && results.length > 0) {
        return `${title} — ${results.length} résultats.`;
      }
      return `${title} — aucun résultat.`;
    } catch (error) {
      dataStream.write({
        type: "data-error",
        data: {
          code: "search_request_error",
          message: "La récupération des résultats a échoué.",
        },
      });
      return `${title} — erreur lors de la recherche.`;
    }
  },
  onUpdateDocument: async ({ document, dataStream }) => {
    dataStream.write({
      type: "data-error",
      data: {
        code: "search_update_not_supported",
        message:
          "Les artefacts de recherche sont statiques. Relancez une nouvelle requête pour actualiser les résultats.",
      },
    });
    return document.content ?? "";
  },
});
