import type { NextRequest } from "next/server";

import {
  FINANCE_STREAM_FIXTURE,
  buildFinanceEventChunk,
} from "@/lib/test/finance-stream-fixture";

/**
 * Deterministic finance SSE fixture consumed by Playwright tests.
 *
 * The handler mirrors the backend `/stream/analysis` endpoint closely enough
 * for the finance artifact to exercise its full mapping logic while keeping the
 * end-to-end suite hermetic. Events are emitted synchronously to keep the
 * implementation simple; the client still receives a well-formed event stream.
 */
const encoder = new TextEncoder();

export const runtime = "nodejs";

export function GET(_request: NextRequest): Response {
  const stream = new ReadableStream<Uint8Array>({
    start(controller) {
      for (const event of FINANCE_STREAM_FIXTURE) {
        const chunk = `${buildFinanceEventChunk(event)}\n\n`;
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });

  return new Response(stream, {
    status: 200,
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
