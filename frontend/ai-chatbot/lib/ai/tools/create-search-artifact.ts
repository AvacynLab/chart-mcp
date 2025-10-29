import { tool, type UIMessageStreamWriter } from "ai";
import type { Session } from "next-auth";
import { z } from "zod";
import { setSearchArtifactConfig } from "@/lib/artifacts/search-config";
import { documentHandlersByArtifactKind } from "@/lib/artifacts/server";
import type { ChatMessage } from "@/lib/types";
import { generateUUID } from "@/lib/utils";

export type CreateSearchArtifactProps = {
  session: Session;
  dataStream: UIMessageStreamWriter<ChatMessage>;
};

export const createSearchArtifact = ({
  session,
  dataStream,
}: CreateSearchArtifactProps) =>
  tool({
    description:
      "Lance une recherche SearxNG (actualités, documentation) et affiche un artefact de résultats formatés.",
    inputSchema: z.object({
      title: z.string().min(3),
      query: z.string().min(3),
      categories: z.array(z.string().min(2)).max(6).optional(),
      timeRange: z.string().min(2).max(16).optional(),
    }),
    execute: async ({ title, query, categories = [], timeRange }) => {
      const id = generateUUID();
      setSearchArtifactConfig(id, {
        query,
        categories,
        timeRange,
      });

      dataStream.write({ type: "data-kind", data: "search", transient: true });
      dataStream.write({ type: "data-id", data: id, transient: true });
      dataStream.write({ type: "data-title", data: title, transient: true });
      dataStream.write({ type: "data-clear", data: null, transient: true });

      const handler = documentHandlersByArtifactKind.find((candidate) => candidate.kind === "search");
      if (!handler) {
        throw new Error("Search document handler unavailable");
      }

      await handler.onCreateDocument({ id, title, dataStream, session });

      return {
        id,
        title,
        kind: "search" as const,
        content: `Résultats SearxNG pour ${query}`,
      };
    },
  });
