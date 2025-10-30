import { beforeAll, beforeEach, describe, expect, test, vi } from "vitest";
import { setSearchArtifactConfig } from "@/lib/artifacts/search-config";

vi.mock("@/lib/artifacts/server", () => ({
  createDocumentHandler: (config: any) => config,
}));

let searchDocumentHandler: typeof import("@/artifacts/search/server")["searchDocumentHandler"];

type StreamWrite = { type: string; data: unknown; transient?: boolean };

describe("searchDocumentHandler", () => {
  beforeAll(async () => {
    ({ searchDocumentHandler } = await import("@/artifacts/search/server"));
  });
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  test("fetches search results and streams batch", async () => {
    const writes: StreamWrite[] = [];
    setSearchArtifactConfig("search-1", {
      query: "bitcoin halving",
      categories: ["news"],
      timeRange: "day",
    });

    const payload = {
      results: [
        {
          title: "Bitcoin hits new ATH",
          url: "https://example.com/article",
          snippet: "Markets react to the halving.",
          source: "gnews",
          score: 0.9,
        },
      ],
    };

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response(JSON.stringify(payload), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      })
    );

    const summary = await searchDocumentHandler.onCreateDocument({
      id: "search-1",
      title: "Actualités BTC",
      dataStream: { write: (part: StreamWrite) => writes.push(part) } as any,
      session: {} as any,
    });

    expect(summary).toContain("1 résultats");
    const batch = writes.find((part) => part.type === "data-search:batch");
    expect(batch).toBeTruthy();
    expect(writes.some((part) => part.type === "data-finish")).toBe(true);
  });

  test("propagates upstream errors", async () => {
    const writes: StreamWrite[] = [];
    setSearchArtifactConfig("search-err", {
      query: "ethereum",
    });

    vi.spyOn(globalThis, "fetch").mockResolvedValue(
      new Response("", { status: 502 })
    );

    const summary = await searchDocumentHandler.onCreateDocument({
      id: "search-err",
      title: "Erreur search",
      dataStream: { write: (part: StreamWrite) => writes.push(part) } as any,
      session: {} as any,
    });

    expect(summary).toContain("erreur");
    const errorPart = writes.find((part) => part.type === "data-error");
    expect(errorPart).toBeTruthy();
  });
});
