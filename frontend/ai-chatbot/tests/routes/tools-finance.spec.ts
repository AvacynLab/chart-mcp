import { beforeAll, beforeEach, describe, expect, test, vi } from "vitest";
import { setFinanceArtifactConfig } from "@/lib/artifacts/finance-config";

vi.mock("@/lib/artifacts/server", () => ({
  createDocumentHandler: (config: any) => config,
}));

type StreamWrite = { type: string; data: unknown; transient?: boolean };

const encoder = new TextEncoder();
let financeDocumentHandler: typeof import("@/artifacts/finance/server")["financeDocumentHandler"];

describe("financeDocumentHandler", () => {
  beforeAll(async () => {
    ({ financeDocumentHandler } = await import("@/artifacts/finance/server"));
  });
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  test("streams SSE payloads and returns summary", async () => {
    const writes: StreamWrite[] = [];
    setFinanceArtifactConfig("doc-1", {
      symbol: "BTCUSDT",
      timeframe: "1h",
      includeLevels: true,
      includePatterns: true,
      indicators: ["ema:21"],
      limit: 100,
      maxLevels: 5,
    });

    const events = [
      "event: ohlcv\n" +
        'data: {"payload":{"symbol":"BTCUSDT","timeframe":"1h","rows":[{"ts":1,"open":1,"high":1,"low":1,"close":1,"volume":120}]}}\n\n',
      "event: token\n" + 'data: {"payload":{"text":"Analyse"}}\n\n',
      "event: done\n" + "data: {}\n\n",
    ];

    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        for (const event of events) {
          controller.enqueue(encoder.encode(event));
        }
        controller.close();
      },
    });

    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response(body, { status: 200 }));

    const summary = await financeDocumentHandler.onCreateDocument({
      id: "doc-1",
      title: "Analyse BTC",
      dataStream: { write: (part: StreamWrite) => writes.push(part) } as any,
      session: {} as any,
    });

    expect(summary).toBe("Analyse");
    expect(writes.some((part) => part.type === "data-finance:ohlcv")).toBe(true);
    expect(writes.some((part) => part.type === "data-finance:token" && part.data === "Analyse")).toBe(true);
    expect(writes.find((part) => part.type === "data-finish")).toBeTruthy();
  });

  test("surfaces HTTP errors via error stream", async () => {
    const writes: StreamWrite[] = [];
    setFinanceArtifactConfig("doc-err", {
      symbol: "ETHUSDT",
      timeframe: "4h",
      includeLevels: true,
      includePatterns: false,
    });

    vi.spyOn(globalThis, "fetch").mockResolvedValue(new Response("", { status: 500 }));

    const summary = await financeDocumentHandler.onCreateDocument({
      id: "doc-err",
      title: "Analyse ETH",
      dataStream: { write: (part: StreamWrite) => writes.push(part) } as any,
      session: {} as any,
    });

    expect(summary).toContain("échec");
    const errorPart = writes.find((part) => part.type === "data-error");
    expect(errorPart).toBeTruthy();
  });
});
