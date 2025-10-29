import { tool, type UIMessageStreamWriter } from "ai";
import type { Session } from "next-auth";
import { z } from "zod";
import { setFinanceArtifactConfig } from "@/lib/artifacts/finance-config";
import { documentHandlersByArtifactKind } from "@/lib/artifacts/server";
import type { ChatMessage } from "@/lib/types";
import { generateUUID } from "@/lib/utils";

export type CreateFinanceArtifactProps = {
  session: Session;
  dataStream: UIMessageStreamWriter<ChatMessage>;
};

export const createFinanceArtifact = ({
  session,
  dataStream,
}: CreateFinanceArtifactProps) =>
  tool({
    description:
      "Génère un artefact finance avec graphiques, indicateurs et résumé en se connectant au backend chart-mcp.",
    inputSchema: z.object({
      title: z.string().min(3),
      symbol: z.string().min(3).max(20),
      timeframe: z.string().min(1).max(10),
      indicators: z.array(z.string().min(2)).max(10).optional(),
      limit: z.number().int().min(50).max(5000).default(500),
      includeLevels: z.boolean().default(true),
      includePatterns: z.boolean().default(true),
      maxLevels: z.number().int().min(1).max(100).default(10),
    }),
    execute: async ({
      title,
      symbol,
      timeframe,
      indicators = [],
      limit,
      includeLevels,
      includePatterns,
      maxLevels,
    }) => {
      const id = generateUUID();

      setFinanceArtifactConfig(id, {
        symbol,
        timeframe,
        indicators,
        limit,
        includeLevels,
        includePatterns,
        maxLevels,
      });

      dataStream.write({ type: "data-kind", data: "finance", transient: true });
      dataStream.write({ type: "data-id", data: id, transient: true });
      dataStream.write({ type: "data-title", data: title, transient: true });
      dataStream.write({ type: "data-clear", data: null, transient: true });

      const handler = documentHandlersByArtifactKind.find((candidate) => candidate.kind === "finance");
      if (!handler) {
        throw new Error("Finance document handler unavailable");
      }

      await handler.onCreateDocument({ id, title, dataStream, session });

      dataStream.write({ type: "data-finish", data: null, transient: true });

      return {
        id,
        title,
        kind: "finance" as const,
        content: "Analyse finance diffusée via SSE.",
      };
    },
  });
