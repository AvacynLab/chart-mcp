import {
  customProvider,
  extractReasoningMiddleware,
  wrapLanguageModel,
} from "ai";
import { isTestEnvironment } from "../constants";

function loadOpenAICompatible() {
  try {
    const moduleName = ["@ai-sdk", "openai-compatible"].join("/");
    const dynamicRequire =
      typeof require === "function"
        ? // Use `eval("require")` so bundlers do not eagerly include the optional
          // dependency while still allowing Node.js to resolve it at runtime.
          ((eval("require") as NodeRequire) ?? undefined)
        : undefined;
    if (!dynamicRequire) {
      return undefined;
    }
    const { createOpenAICompatible } = dynamicRequire(moduleName);
    return createOpenAICompatible as typeof import("@ai-sdk/openai-compatible")["createOpenAICompatible"];
  } catch (error) {
    // Provide a descriptive warning so production environments without the
    // optional dependency can fall back to the deterministic mock provider.
    // eslint-disable-next-line no-console
    console.warn(
      "@ai-sdk/openai-compatible is not available; continuing with the mock provider.",
      error,
    );
    return undefined;
  }
}

/**
 * Build the deterministic mock provider that powers hermetic tests and falls
 * back when the real OpenAI credentials are not available. The `require`
 * statement keeps the mock bundle out of production builds.
 */
function createMockProvider() {
  const {
    artifactModel,
    chatModel,
    reasoningModel,
    titleModel,
  } = require("./models.mock");
  return customProvider({
    languageModels: {
      "chat-model": chatModel,
      "chat-model-reasoning": reasoningModel,
      "title-model": titleModel,
      "artifact-model": artifactModel,
    },
  });
}

/**
 * Factory wrapper that either yields the mock provider or a live OpenAI backed
 * provider depending on the environment variables exported for the run.
 */
function createProvider() {
  if (isTestEnvironment) {
    return createMockProvider();
  }

  const apiKey = process.env.OPENAI_API_KEY;
  if (!apiKey) {
    if (process.env.CI) {
      // In CI we surface a helpful log before falling back so the missing key is
      // still visible in the aggregated logs without breaking the suite.
      // eslint-disable-next-line no-console
      console.warn(
        "OPENAI_API_KEY is not set; falling back to the deterministic mock provider."
      );
    }
    return createMockProvider();
  }

  const baseURL = process.env.OPENAI_BASE_URL ?? "https://api.openai.com/v1";

  const createOpenAICompatible = loadOpenAICompatible();
  if (!createOpenAICompatible) {
    return createMockProvider();
  }

  const openai = createOpenAICompatible({
    apiKey,
    baseURL,
    /**
     * Explicitly tag the provider so downstream telemetry can distinguish real
     * OpenAI traffic from other compatibility-mode integrations.
     */
    name: "openai",
  });

  return customProvider({
    languageModels: {
      /**
       * Default chat completions lean on gpt-4o-mini for a good balance of
       * latency and quality during E2E runs.
       */
      "chat-model": openai.languageModel("openai/gpt-4o-mini"),
      /**
       * The reasoning scenarios stream structured <reasoning> sections from the
       * o4-mini family which we unwrap into dedicated UI panes.
       */
      "chat-model-reasoning": wrapLanguageModel({
        model: openai.languageModel("openai/o4-mini"),
        middleware: extractReasoningMiddleware({ tagName: "reasoning" }),
      }),
      /**
       * Title/artifact generation are fine to reuse the lower-latency model
       * because they only need short deterministic responses.
       */
      "title-model": openai.languageModel("openai/gpt-4o-mini"),
      "artifact-model": openai.languageModel("openai/gpt-4o-mini"),
    },
  });
}

export const myProvider = createProvider();
