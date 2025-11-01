import type {
  LanguageModelV2,
  LanguageModelV2CallOptions,
  LanguageModelV2Message,
  LanguageModelV2StreamPart,
  LanguageModelV2TextPart,
} from "@ai-sdk/provider";

/**
 * Narrow a generic content part to the concrete text variant so we can
 * safely read the string payload without resorting to `any` casts.
 */
function isTextPart(part: LanguageModelV2TextPart | { type: string }):
  part is LanguageModelV2TextPart {
  return part.type === "text";
}

type MockResponse = {
  text: string;
  reasoning?: string;
};

const MOCK_RESPONSES = new Map<string, MockResponse>([
  [
    "why is grass green?",
    {
      text: "It's just green duh!",
      reasoning: "Grass is green because of chlorophyll absorption!",
    },
  ],
  [
    "why is the sky blue?",
    {
      text: "It's just blue duh!",
      reasoning: "The sky is blue because of rayleigh scattering!",
    },
  ],
  ["how do you build apps?", { text: "With Next.js, you can ship fast!" }],
  ["who painted this?", { text: "This painting is by Monet!" }],
  [
    "what's the weather in sf?",
    { text: "The current temperature in San Francisco is 17°C." },
  ],
]);

function normalisePrompt(prompt: LanguageModelV2CallOptions["prompt"]): string {
  for (let index = prompt.length - 1; index >= 0; index -= 1) {
    const message = prompt[index] as LanguageModelV2Message;
    if (message.role !== "user") {
      continue;
    }

    const textParts = message.content
      .filter((part): part is LanguageModelV2TextPart => isTextPart(part))
      .map((part) => part.text.trim())
      .filter(Boolean);

    if (textParts.length > 0) {
      return textParts.join(" ").toLowerCase();
    }
  }

  return "";
}

function resolveMockResponse(promptText: string): MockResponse {
  if (!promptText) {
    return { text: "Response for prompt." };
  }

  const directMatch = MOCK_RESPONSES.get(promptText);
  if (directMatch) {
    return directMatch;
  }

  return {
    text: `Response for ${promptText}.`,
    reasoning: `Considering prompt: ${promptText}.`,
  };
}

function createMockStream({
  prompt,
  includeReasoning,
}: {
  prompt: LanguageModelV2CallOptions["prompt"];
  includeReasoning: boolean;
}): ReadableStream<LanguageModelV2StreamPart> {
  const promptText = normalisePrompt(prompt);
  const { text, reasoning } = resolveMockResponse(promptText);

  const words = text.split(/(\s+)/).filter(Boolean);
  const reasoningWords = reasoning?.split(/(\s+)/).filter(Boolean) ?? [];
  const textTokenCount = text.split(/\s+/).filter(Boolean).length;
  const reasoningTokenCount = reasoning?.split(/\s+/).filter(Boolean).length ?? 0;

  const usage = {
    inputTokens: Math.max(8, promptText.split(/\s+/).filter(Boolean).length + 3),
    outputTokens: Math.max(8, textTokenCount + reasoningTokenCount + 3),
    totalTokens: Math.max(
      16,
      Math.max(8, promptText.split(/\s+/).filter(Boolean).length + 3) +
        Math.max(8, textTokenCount + reasoningTokenCount + 3),
    ),
    reasoningTokens:
      includeReasoning && reasoningTokenCount > 0
        ? Math.max(4, reasoningTokenCount)
        : undefined,
  };

  let cancelled = false;

  return new ReadableStream<LanguageModelV2StreamPart>({
    async start(controller) {
      /**
       * Space out tokens so the UI has time to reveal the stop button and the
       * Playwright tests can interact with it. Immediate completion caused the
       * button to disappear before the assertions executed which in turn made
       * the suite flaky.
       */
      const delay = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

      const enqueueWithDelay = async (
        part: LanguageModelV2StreamPart,
        delayMs = 60
      ) => {
        if (cancelled) {
          return;
        }
        controller.enqueue(part);
        if (delayMs > 0) {
          await delay(delayMs);
        }
      };

      try {
        await enqueueWithDelay({ type: "stream-start", warnings: [] });

        if (includeReasoning && reasoning) {
          await enqueueWithDelay({ type: "reasoning-start", id: "reasoning-1" });
          for (const chunk of reasoningWords) {
            await enqueueWithDelay(
              { type: "reasoning-delta", id: "reasoning-1", delta: chunk },
              80
            );
          }
          await enqueueWithDelay({ type: "reasoning-end", id: "reasoning-1" });
        }

        // Allow the UI to mount the stop button before text tokens start
        // streaming. This mirrors real-world latency more closely than
        // immediate completion.
        await delay(120);

        await enqueueWithDelay({ type: "text-start", id: "message-1" });
        for (const chunk of words) {
          await enqueueWithDelay(
            { type: "text-delta", id: "message-1", delta: chunk },
            80
          );
        }
        await enqueueWithDelay({ type: "text-end", id: "message-1" });
        await enqueueWithDelay({ type: "finish", finishReason: "stop", usage }, 0);
        controller.close();
      } catch (error) {
        controller.error(error);
      }
    },
    cancel() {
      cancelled = true;
    },
  });
}

const createMockModel = ({
  includeReasoning = false,
}: { includeReasoning?: boolean } = {}): LanguageModelV2 => {
  // Build a minimal `LanguageModelV2` implementation so the mock provider used in
  // tests satisfies the current AI SDK contract without relying on deprecated
  // v1 helper types.
  return {
    specificationVersion: "v2",
    provider: "mock",
    modelId: includeReasoning ? "mock-reasoning-model" : "mock-model",
    supportedUrls: {},
    doGenerate: async (options: LanguageModelV2CallOptions) => {
      const promptText = normalisePrompt(options.prompt);
      const { text } = resolveMockResponse(promptText);

      return {
        finishReason: "stop",
        usage: {
          inputTokens: Math.max(8, promptText.split(/\s+/).filter(Boolean).length + 3),
          outputTokens: Math.max(8, text.split(/\s+/).filter(Boolean).length + 3),
          totalTokens: Math.max(16, text.split(/\s+/).filter(Boolean).length + 3),
        },
        content: [{ type: "text", text }],
        warnings: [],
      };
    },
    doStream: async (options: LanguageModelV2CallOptions) => ({
      stream: createMockStream({
        prompt: options.prompt,
        includeReasoning,
      }),
    }),
  };
};

export const chatModel = createMockModel();
export const reasoningModel = createMockModel({ includeReasoning: true });
export const titleModel = createMockModel();
export const artifactModel = createMockModel();
