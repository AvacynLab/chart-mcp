import type { LanguageModelV2CallOptions, LanguageModelV2StreamPart } from "ai";
import { describe, expect, it } from "vitest";

import { chatModel, reasoningModel } from "@/lib/ai/models.mock";

function buildCallOptions(text: string): LanguageModelV2CallOptions {
  return {
    prompt: [
      {
        role: "user",
        content: [
          {
            type: "text",
            text,
          },
        ],
      },
    ],
  } as LanguageModelV2CallOptions;
}

async function readStream(
  stream: ReadableStream<LanguageModelV2StreamPart>
): Promise<LanguageModelV2StreamPart[]> {
  const reader = stream.getReader();
  const chunks: LanguageModelV2StreamPart[] = [];

  while (true) {
    const result = await reader.read();
    if (result.done) {
      break;
    }
    chunks.push(result.value);
  }

  return chunks;
}

describe("mock language models", () => {
  it("emits a deterministic chat completion", async () => {
    const { stream } = await chatModel.doStream(buildCallOptions("Why is grass green?"));

    const parts = await readStream(stream);
    const textDelta = parts.find((part) => part.type === "text-delta");
    const finish = parts.find((part) => part.type === "finish");

    if (!textDelta || textDelta.type !== "text-delta") {
      throw new Error("expected text delta in mock stream");
    }
    expect(textDelta.delta).toBe("It's just green duh!");
    expect(finish?.type).toBe("finish");
  });

  it("provides reasoning traces for the reasoning model", async () => {
    const { stream } = await reasoningModel.doStream(
      buildCallOptions("Why is the sky blue?")
    );

    const parts = await readStream(stream);
    const reasoning = parts.filter((part) => part.type?.startsWith("reasoning"));
    const textDelta = parts.find((part) => part.type === "text-delta");

    expect(reasoning.map((part) => part.type)).toEqual([
      "reasoning-start",
      "reasoning-delta",
      "reasoning-end",
    ]);
    if (!textDelta || textDelta.type !== "text-delta") {
      throw new Error("expected text delta in reasoning mock stream");
    }
    expect(textDelta.delta).toBe("It's just blue duh!");
  });
});
