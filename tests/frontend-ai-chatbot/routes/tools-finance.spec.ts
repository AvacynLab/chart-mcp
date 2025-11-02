import { ReadableStream } from "node:stream/web";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

vi.mock("@/lib/db/queries", () => ({
  saveDocument: vi.fn().mockResolvedValue(undefined),
}));

vi.mock("@/lib/artifacts/server", () => ({
  createDocumentHandler: <T extends string>(config: {
    kind: T;
    onCreateDocument: (args: any) => Promise<string>;
    onUpdateDocument: (args: any) => Promise<string>;
  }) => ({
    kind: config.kind,
    onCreateDocument: async (args: any) => {
      const content = await config.onCreateDocument(args);
      if (args.session?.user?.id) {
        const { saveDocument } = await import("@/lib/db/queries");
        await saveDocument({
          id: args.id,
          title: args.title,
          content,
          kind: config.kind,
          userId: args.session.user.id,
        });
      }
    },
    onUpdateDocument: async (args: any) => {
      const content = await config.onUpdateDocument(args);
      if (args.session?.user?.id) {
        const { saveDocument } = await import("@/lib/db/queries");
        await saveDocument({
          id: args.document.id,
          title: args.document.title,
          content,
          kind: config.kind,
          userId: args.session.user.id,
        });
      }
    },
  }),
}));

import { financeDocumentHandler } from "@/artifacts/finance/server";
import { setFinanceArtifactConfig } from "@/lib/artifacts/finance-config";
import { saveDocument } from "@/lib/db/queries";

type StreamEnvelope = {
  type: string;
  data: unknown;
  transient?: boolean;
};

const encoder = new TextEncoder();

/** Build an SSE chunk following the ``event:`` / ``data:`` wire format. */
function buildChunk(event: string, payload: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(payload)}\n\n`;
}

function createStreamFromChunks(chunks: string[]): ReadableStream<Uint8Array> {
  return new ReadableStream<Uint8Array>({
    start(controller) {
      for (const chunk of chunks) {
        controller.enqueue(encoder.encode(chunk));
      }
      controller.close();
    },
  });
}

describe("financeDocumentHandler", () => {
  const documentId = "finance-doc";
  const session = { user: { id: "trader-7" } } as any;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    process.env.MCP_API_BASE = "http://127.0.0.1:8000";
    process.env.MCP_API_TOKEN = "mock-token";
    process.env.MCP_SESSION_USER = "vip";
  });

  afterEach(() => {
    delete process.env.MCP_API_BASE;
    delete process.env.MCP_API_TOKEN;
    delete process.env.MCP_SESSION_USER;
    if (originalFetch) {
      globalThis.fetch = originalFetch;
    }
  });

  it("maps SSE deltas to finance stream envelopes and stores the summary", async () => {
    const writes: StreamEnvelope[] = [];
    const dataStream = {
      write: vi.fn((payload: StreamEnvelope) => {
        writes.push(payload);
      }),
    };

    const chunks = [
      buildChunk("step:start", { payload: { step: "collect_data" } }),
      buildChunk("result_partial", {
        payload: {
          ohlcv: [{ ts: 1_700_000_000, o: 1, h: 2, l: 0.5, c: 1.5, v: 1200 }],
          indicators: { rsi: 56 },
          levels: [{ price: 68000, kind: "resistance" }],
          patterns: [{ name: "triangle", score: 0.62 }],
        },
      }),
      buildChunk("token", { payload: { text: "Momentum building " } }),
      buildChunk("token", { payload: { text: "fast." } }),
      buildChunk("result_final", {
        payload: {
          summary: "Momentum building rapidly.",
          levels: [{ price: 67000, strength: 0.81 }],
          patterns: [{ name: "double_top", score: 0.71 }],
        },
      }),
      buildChunk("indicators", { payload: { macd: { fast: 12, slow: 26 } } }),
      buildChunk("ohlcv", { payload: [{ ts: 1_700_000_600, o: 2, h: 2.5, l: 1.4, c: 2.3, v: 980 }] }),
      buildChunk("levels", { payload: [{ price: 66000, strength: 0.55 }] }),
      buildChunk("patterns", { payload: [{ name: "ascending_channel", score: 0.64 }] }),
      buildChunk("done", { payload: null }),
    ];

    const stream = createStreamFromChunks(chunks);
    const response = new Response(stream, { status: 200 });

    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(response as unknown as Response);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    setFinanceArtifactConfig(documentId, {
      symbol: "BTCUSDT",
      timeframe: "1h",
      indicators: ["ema:21"],
      limit: 250,
      includeLevels: false,
      includePatterns: false,
      maxLevels: 5,
    });

    await financeDocumentHandler.onCreateDocument({
      id: documentId,
      title: "Analyse BTC",
      dataStream: dataStream as any,
      session,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requestedUrl, requestOptions] = fetchMock.mock.calls[0];
    expect(requestedUrl).toContain("/stream/analysis?");
    expect(requestedUrl).toContain("symbol=BTCUSDT");
    expect(requestedUrl).toContain("timeframe=1h");
    expect(requestedUrl).toContain("indicators=ema%3A21");
    expect(requestedUrl).toContain("limit=250");
    expect(requestedUrl).toContain("include_levels=false");
    expect(requestedUrl).toContain("include_patterns=false");
    expect(requestedUrl).toContain("max=5");
    expect(requestOptions).toMatchObject({
      cache: "no-store",
      headers: {
        Accept: "text/event-stream",
        "Cache-Control": "no-cache",
        Authorization: "Bearer mock-token",
        "X-Session-User": "vip",
      },
    });

    const eventTypes = writes.map((entry) => entry.type);
    expect(eventTypes).toEqual([
      "data-finance:step",
      "data-finance:step",
      "data-finance:token",
      "data-finance:token",
      "data-finance:token",
      "data-finance:levels",
      "data-finance:patterns",
      "data-finance:indicators",
      "data-finance:ohlcv",
      "data-finance:levels",
      "data-finance:patterns",
      "data-finish",
    ]);

    const summaryEvents = writes.filter((entry) => entry.type === "data-finance:token");
    expect(summaryEvents[0]).toMatchObject({ data: "Momentum building " });
    expect(summaryEvents[1]).toMatchObject({ data: "fast." });
    expect(summaryEvents[2]).toMatchObject({ data: "Momentum building rapidly." });

    expect(writes.find((entry) => entry.type === "data-finish")).toEqual({
      type: "data-finish",
      data: null,
      transient: true,
    });

    const mockedSaveDocument = vi.mocked(saveDocument);
    expect(mockedSaveDocument).toHaveBeenCalledWith({
      id: documentId,
      title: "Analyse BTC",
      kind: "finance",
      userId: "trader-7",
      content: "Momentum building rapidly.",
    });
  });
});
