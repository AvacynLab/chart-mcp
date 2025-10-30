import { beforeAll, beforeEach, describe, expect, test, vi } from "vitest";
import { setFinanceArtifactConfig } from "@/lib/artifacts/finance-config";

vi.mock("@/lib/artifacts/server", () => ({
  createDocumentHandler: (config: any) => config,
}));

type StreamWrite = { type: string; data: unknown; transient?: boolean };

const encoder = new TextEncoder();
let financeDocumentHandler: typeof import("@/artifacts/finance/server")["financeDocumentHandler"];

/**
 * Helper to encode a single SSE frame. Using JSON.stringify keeps the payloads
 * readable while mimicking the backend event envelope closely.
 */
function encodeEvent(event: string, payload: unknown): Uint8Array {
  const json = payload === undefined ? "{}" : JSON.stringify(payload);
  return encoder.encode(`event: ${event}\ndata: ${json}\n\n`);
}

/** Safely coerce an unknown value into a record when possible. */
function asRecord(value: unknown): Record<string, any> | undefined {
  if (value && typeof value === "object") {
    return value as Record<string, any>;
  }
  return;
}

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

    /**
     * The fixture mirrors a realistic happy-path flow where the backend sends
     * progress steps, market data, metrics, and incremental tokens before the
     * stream completes.
     */
    const eventChunks = [
      encodeEvent("step:start", { payload: { step: "bootstrap" } }),
      encodeEvent("ohlcv", {
        payload: {
          symbol: "BTCUSDT",
          timeframe: "1h",
          rows: [
            { ts: 1, open: 1, high: 2, low: 0.5, close: 1.8, volume: 150 },
            { ts: 2, open: 1.8, high: 2.2, low: 1.5, close: 2.1, volume: 170 },
          ],
        },
      }),
      encodeEvent("metric", {
        payload: { name: "latency_ms", value: 1200 },
      }),
      encodeEvent("result_partial", {
        payload: {
          step: "analysis",
          status: "running",
          ohlcv: { points: 2 },
          indicators: { overlays: [{ id: "ema:21", latest: 2.1 }] },
          levels: { support: [{ price: 1.5, strength: 0.6 }] },
          patterns: { bearish: [{ name: "head_shoulders", score: 0.74 }] },
        },
      }),
      encodeEvent("indicators", {
        payload: { overlays: [{ id: "ema:21", values: [1.6, 1.8] }] },
      }),
      encodeEvent("levels", {
        payload: { support: [{ price: 1.5, strength: 0.6 }] },
      }),
      encodeEvent("patterns", {
        payload: { bearish: [{ name: "head_shoulders", score: 0.74 }] },
      }),
      encodeEvent("step:end", {
        payload: { step: "analysis", status: "completed" },
      }),
      encodeEvent("token", { payload: { text: "Analyse" } }),
      encodeEvent("done", {}),
    ];

    const body = new ReadableStream<Uint8Array>({
      start(controller) {
        for (const event of eventChunks) {
          controller.enqueue(event);
        }
        controller.close();
      },
    });

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(body, { status: 200 })
    );

    const summary = await financeDocumentHandler.onCreateDocument({
      id: "doc-1",
      title: "Analyse BTC",
      dataStream: { write: (part: StreamWrite) => writes.push(part) } as any,
      session: {} as any,
    });

    expect(summary).toBe("Analyse");

    const hasType = (type: string) => writes.some((part) => part.type === type);
    expect(hasType("data-finance:ohlcv")).toBe(true);
    expect(hasType("data-finance:indicators")).toBe(true);
    expect(hasType("data-finance:levels")).toBe(true);
    expect(hasType("data-finance:patterns")).toBe(true);
    expect(
      writes.some(
        (part) => part.type === "data-finance:token" && part.data === "Analyse"
      )
    ).toBe(true);
    expect(hasType("data-finish")).toBe(true);

    const stepEvents = writes.filter(
      (part) => part.type === "data-finance:step"
    );
    expect(stepEvents).toEqual(
      expect.arrayContaining([
        expect.objectContaining({
          data: expect.objectContaining({ event: "step:start" }),
        }),
        expect.objectContaining({
          data: expect.objectContaining({ event: "metric" }),
        }),
        expect.objectContaining({
          data: expect.objectContaining({ event: "result_partial" }),
        }),
        expect.objectContaining({
          data: expect.objectContaining({ event: "step:end" }),
        }),
      ])
    );

    const partialStep = stepEvents.find((part) => {
      const data = asRecord(part.data);
      return data?.event === "result_partial";
    });

    const partialStepData = asRecord(partialStep?.data);
    expect(partialStepData?.event).toBe("result_partial");
    const partialPayload = asRecord(partialStepData?.payload);
    expect(partialPayload?.levels).toBeDefined();
    expect(partialPayload?.patterns).toBeDefined();
  });

  test("surfaces HTTP errors via error stream", async () => {
    const writes: StreamWrite[] = [];
    setFinanceArtifactConfig("doc-err", {
      symbol: "ETHUSDT",
      timeframe: "4h",
      includeLevels: true,
      includePatterns: false,
    });

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("", { status: 500 })
    );

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
