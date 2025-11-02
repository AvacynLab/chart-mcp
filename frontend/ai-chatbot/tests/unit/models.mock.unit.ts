import type {
  LanguageModelV2CallOptions,
  LanguageModelV2StreamPart,
} from "@ai-sdk/provider";
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
    const textDeltaParts = parts.filter(
      (part): part is Extract<LanguageModelV2StreamPart, { type: "text-delta" }> =>
        part.type === "text-delta"
    );
    const finish = parts.find((part) => part.type === "finish");

    const aggregatedText = textDeltaParts.map((part) => part.delta).join("");
    expect(aggregatedText).toBe("It's just green duh!");
    expect(finish?.type).toBe("finish");
  });

  it("provides reasoning traces for the reasoning model", async () => {
    const { stream } = await reasoningModel.doStream(
      buildCallOptions("Why is the sky blue?")
    );

    const parts = await readStream(stream);
    const reasoning = parts.filter((part) => part.type?.startsWith("reasoning"));
    const textDeltaParts = parts.filter(
      (part): part is Extract<LanguageModelV2StreamPart, { type: "text-delta" }> =>
        part.type === "text-delta"
    );

    expect(reasoning[0]?.type).toBe("reasoning-start");
    expect(reasoning.at(-1)?.type).toBe("reasoning-end");
    expect(
      reasoning.slice(1, -1).every((part) => part.type === "reasoning-delta")
    ).toBe(true);

    const aggregatedReasoning = reasoning
      .filter(
        (part): part is Extract<LanguageModelV2StreamPart, { type: "reasoning-delta" }> =>
          part.type === "reasoning-delta"
      )
      .map((part) => part.delta)
      .join("");

    const aggregatedText = textDeltaParts.map((part) => part.delta).join("");

    expect(aggregatedReasoning).toBe(
      "The sky is blue because of rayleigh scattering!"
    );
    expect(aggregatedText).toBe("It's just blue duh!");
  });
});
