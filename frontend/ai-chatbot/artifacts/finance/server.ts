/**
 * Server-side document handler responsible for orchestrating the finance
 * streaming artefact.
 *
 * The handler bridges the Vercel AI SDK streaming primitives with the
 * FastAPI `/stream/analysis` endpoint emitted by the backend. It parses the
 * Server-Sent Events payload, forwards structured deltas to the UI layer and
 * finally persists the generated summary as the document content.
 */
import type { UIMessageStreamWriter } from "ai";

import { createDocumentHandler } from "@/lib/artifacts/server";
import { consumeFinanceArtifactConfig } from "@/lib/artifacts/finance-config";
import {
  FINANCE_STREAM_FIXTURE,
  buildFinanceEventChunk,
} from "@/lib/test/finance-stream-fixture";
import type { ChatMessage } from "@/lib/types";

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
  const headers: Record<string, string> = {
    Accept: "text/event-stream",
    "Cache-Control": "no-cache",
  };
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

function parseEventChunk(chunk: string): { event: string | null; payload: any } {
  const lines = chunk.split(/\r?\n/);
  let eventName: string | null = null;
  const dataLines: string[] = [];

  for (const line of lines) {
    if (!line) {
      continue;
    }
    if (line.startsWith(":")) {
      continue;
    }
    if (line.startsWith("event: ")) {
      eventName = line.slice("event: ".length).trim();
      continue;
    }
    if (line.startsWith("data: ")) {
      dataLines.push(line.slice("data: ".length));
    }
  }

  let payload: any = null;
  if (dataLines.length > 0) {
    const raw = dataLines.join("\n");
    try {
      payload = JSON.parse(raw);
    } catch (error) {
      return { event: eventName, payload: null };
    }
  }

  return { event: eventName, payload };
}

async function streamFinanceAnalysis(
  url: string,
  dataStream: UIMessageStreamWriter<ChatMessage>,
): Promise<string> {
  const decoder = new TextDecoder();
  let buffer = "";
  let summary = "";

  const stepEvents = new Set(["step:start", "step:end", "metric", "result_partial"]);

  async function handleChunk(chunk: string): Promise<void> {
    const { event, payload } = parseEventChunk(chunk);
    if (!event || event === "heartbeat") {
      return;
    }

    const envelopePayload = payload?.payload ?? payload;

    if (event === "token") {
      const tokenText = envelopePayload?.text ?? "";
      if (tokenText) {
        summary += tokenText;
        dataStream.write({
          type: "data-finance:token",
          data: tokenText,
          transient: true,
        });
      }
      return;
    }

    if (event === "result_final") {
      if (typeof envelopePayload?.summary === "string") {
        const finalSummary = envelopePayload.summary;
        const trimmedSummary = finalSummary.trim();
        if (trimmedSummary.length > 0 && trimmedSummary !== summary) {
          dataStream.write({ type: "data-finance:token", data: finalSummary });
        }
        summary = trimmedSummary;
      }
      if (envelopePayload?.levels) {
        dataStream.write({ type: "data-finance:levels", data: envelopePayload.levels });
      }
      if (envelopePayload?.patterns) {
        dataStream.write({ type: "data-finance:patterns", data: envelopePayload.patterns });
      }
      return;
    }

    if (event === "done") {
      dataStream.write({ type: "data-finish", data: null, transient: true });
      return;
    }

    if (event === "error") {
      const errorPayload = envelopePayload ?? {};
      dataStream.write({
        type: "data-error",
        data: {
          code: errorPayload.code ?? "finance_stream_error",
          message: errorPayload.message ?? "Finance streaming failed",
        },
      });
      return;
    }

    if (stepEvents.has(event)) {
      dataStream.write({
        type: "data-finance:step",
        data: {
          event,
          payload: envelopePayload,
        },
      });
      return;
    }

    switch (event) {
      case "ohlcv":
      case "range":
      case "selected":
      case "indicators":
      case "levels":
      case "patterns":
        dataStream.write({ type: `data-finance:${event}`, data: envelopePayload });
        return;
      default:
        return;
    }
  }

  const shouldUseFixture = Boolean(
    (process.env.PLAYWRIGHT ?? process.env.CI_PLAYWRIGHT) &&
      process.env.PLAYWRIGHT_USE_REAL_SERVICES !== "1",
  );

  /**
   * During Playwright runs we bypass the network hop and replay the shared
   * fixture directly. The deterministic sequence keeps the e2e test hermetic
   * while still exercising the event mapping performed by the artifact
   * handler.
   */

  if (shouldUseFixture) {
    for (const event of FINANCE_STREAM_FIXTURE) {
      await handleChunk(buildFinanceEventChunk(event));
    }
    return summary.trim();
  }

  const response = await fetch(url, {
    headers: resolveApiHeaders(),
    cache: "no-store",
  });

  if (!response.ok) {
    const message = `Finance stream request failed with status ${response.status}`;
    dataStream.write({
      type: "data-error",
      data: { code: "finance_request_failed", message },
    });
    throw new Error(message);
  }

  const reader = response.body?.getReader();
  if (!reader) {
    const message = "Finance stream response did not include a readable body";
    dataStream.write({
      type: "data-error",
      data: { code: "finance_stream_empty", message },
    });
    throw new Error(message);
  }

  while (true) {
    const { value, done } = await reader.read();
    if (done) {
      if (buffer.length > 0) {
        await handleChunk(buffer);
      }
      break;
    }

    buffer += decoder.decode(value, { stream: true });
    let boundaryIndex = buffer.indexOf("\n\n");
    while (boundaryIndex !== -1) {
      const chunk = buffer.slice(0, boundaryIndex);
      buffer = buffer.slice(boundaryIndex + 2);
      await handleChunk(chunk);
      boundaryIndex = buffer.indexOf("\n\n");
    }
  }

  return summary.trim();
}

export const financeDocumentHandler = createDocumentHandler<"finance">({
  kind: "finance",
  onCreateDocument: async ({ id, title, dataStream }) => {
    const config = consumeFinanceArtifactConfig(id);
    if (!config) {
      const message = "No finance configuration found for document";
      dataStream.write({
        type: "data-error",
        data: { code: "finance_missing_config", message },
      });
      throw new Error(message);
    }

    const params = new URLSearchParams({
      symbol: config.symbol,
      timeframe: config.timeframe,
      streaming: "true",
    });
    if (config.indicators?.length) {
      params.set("indicators", config.indicators.join(","));
    }
    if (typeof config.limit === "number") {
      params.set("limit", config.limit.toString());
    }
    if (!config.includeLevels) {
      params.set("include_levels", "false");
    }
    if (!config.includePatterns) {
      params.set("include_patterns", "false");
    }
    if (typeof config.maxLevels === "number") {
      params.set("max", config.maxLevels.toString());
    }

    const url = `${resolveApiBase()}/stream/analysis?${params.toString()}`;

    try {
      const summary = await streamFinanceAnalysis(url, dataStream);
      return summary.length > 0 ? summary : `${title} — analyse générée.`;
    } catch (error) {
      return `${title} — échec de l'analyse.`;
    }
  },
  onUpdateDocument: async ({ document, dataStream }) => {
    dataStream.write({
      type: "data-error",
      data: {
        code: "finance_update_not_supported",
        message:
          "Les artefacts finance sont en lecture seule pour le moment. Relancez une nouvelle analyse pour actualiser les données.",
      },
    });
    return document.content ?? "";
  },
});
