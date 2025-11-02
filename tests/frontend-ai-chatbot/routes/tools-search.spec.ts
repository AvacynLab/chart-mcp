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

import { searchDocumentHandler } from "@/artifacts/search/server";
import { setSearchArtifactConfig } from "@/lib/artifacts/search-config";
import { saveDocument } from "@/lib/db/queries";

type StreamEnvelope = {
  type: string;
  data: unknown;
  transient?: boolean;
};

/**
 * Deterministic headers injected by the document handler during fetch calls.
 * Keeping them here avoids string duplication across assertions and highlights
 * the contract expected by the backend FastAPI route.
 */
const EXPECTED_HEADERS = {
  Accept: "application/json",
  Authorization: "Bearer mock-token",
  "X-Session-User": "regular",
};

describe("searchDocumentHandler", () => {
  const documentId = "search-doc";
  const session = { user: { id: "user-42" } } as any;
  const originalFetch = globalThis.fetch;

  beforeEach(() => {
    vi.clearAllMocks();
    process.env.MCP_API_BASE = "http://127.0.0.1:8000";
    process.env.MCP_API_TOKEN = "mock-token";
    process.env.MCP_SESSION_USER = "regular";
  });

  afterEach(() => {
    delete process.env.MCP_API_BASE;
    delete process.env.MCP_API_TOKEN;
    delete process.env.MCP_SESSION_USER;
    if (originalFetch) {
      globalThis.fetch = originalFetch;
    }
  });

  it("streams search batches and persists the rendered summary", async () => {
    const writes: StreamEnvelope[] = [];
    const dataStream = {
      write: vi.fn((payload: StreamEnvelope) => {
        writes.push(payload);
      }),
    };

    const results = [
      {
        title: "Bitcoin halving recap",
        url: "https://news.example/halving",
        snippet: "Key takeaways from the latest halving window.",
        source: "gnews",
        score: 14.2,
      },
      {
        title: "On-chain flows cool down",
        url: "https://data.example/flows",
        snippet: "Exchange reserves suggest consolidation.",
        source: "reddit",
        score: 8.1,
      },
    ];

    const response = new Response(
      JSON.stringify({
        query: "bitcoin",
        categories: ["news", "science"],
        results,
      }),
      {
        status: 200,
        headers: { "Content-Type": "application/json" },
      },
    );

    const fetchMock = vi
      .fn<typeof fetch>()
      .mockResolvedValue(response as unknown as Response);
    globalThis.fetch = fetchMock as unknown as typeof fetch;

    setSearchArtifactConfig(documentId, {
      query: "bitcoin",
      categories: ["news", "science"],
      timeRange: "day",
    });

    await searchDocumentHandler.onCreateDocument({
      id: documentId,
      title: "Recherche actualités",
      dataStream: dataStream as any,
      session,
    });

    expect(fetchMock).toHaveBeenCalledTimes(1);
    const [requestedUrl, requestOptions] = fetchMock.mock.calls[0];
    expect(requestedUrl).toBe(
      "http://127.0.0.1:8000/api/v1/search?q=bitcoin&categories=news%2Cscience&time_range=day",
    );
    expect(requestOptions).toMatchObject({
      cache: "no-store",
      headers: EXPECTED_HEADERS,
    });

    expect(writes).toEqual([
      { type: "data-search:batch", data: results },
      { type: "data-finish", data: null, transient: true },
    ]);

    const mockedSaveDocument = vi.mocked(saveDocument);
    expect(mockedSaveDocument).toHaveBeenCalledTimes(1);
    expect(mockedSaveDocument).toHaveBeenCalledWith({
      id: documentId,
      title: "Recherche actualités",
      kind: "search",
      userId: "user-42",
      content: "Recherche actualités — 2 résultats.",
    });
  });
});
