import type { LanguageModelV2StreamPart } from "@ai-sdk/provider";

/**
 * Helper returning deterministic streaming chunks used by the mocked models in
 * tests. Keeping the logic centralised avoids duplicating fixtures across
 * suites and guarantees that both chat and reasoning prompts remain in sync
 * whenever we tweak the structure.
 */
export type MockResponseChunk = LanguageModelV2StreamPart;

/**
 * Generate a minimal-yet-expressive chunk sequence tailored to the provided
 * prompt. The `includeReasoning` flag allows tests targeting the reasoning
 * model to append an auxiliary chain-of-thought stream alongside the textual
 * response.
 */
export function getResponseChunksByPrompt(
  prompt: unknown,
  includeReasoning = false,
): MockResponseChunk[] {
  const promptLabel = typeof prompt === "string" && prompt.length > 0 ? prompt : "prompt";
  const baseChunks: MockResponseChunk[] = [
    { id: "message-1", type: "text-start" },
    { id: "message-1", type: "text-delta", delta: `Response for ${promptLabel}.` },
    { id: "message-1", type: "text-end" },
    {
      type: "finish",
      finishReason: "stop",
      usage: { inputTokens: 12, outputTokens: 24, totalTokens: 36 },
    },
  ];

  if (!includeReasoning) {
    return baseChunks;
  }

  return [
    { id: "reasoning-1", type: "reasoning-start" },
    { id: "reasoning-1", type: "reasoning-delta", delta: `Considering prompt: ${promptLabel}` },
    { id: "reasoning-1", type: "reasoning-end" },
    ...baseChunks,
  ];
}
