import { createOpenAICompatible } from "@ai-sdk/openai-compatible";
import {
  customProvider,
  extractReasoningMiddleware,
  wrapLanguageModel,
} from "ai";
import { isTestEnvironment } from "../constants";

export const myProvider = isTestEnvironment
  ? (() => {
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
    })()
  : (() => {
      const apiKey = process.env.OPENAI_API_KEY;
      if (!apiKey) {
        throw new Error(
          "OPENAI_API_KEY must be configured when running with live AI services."
        );
      }

      const baseURL =
        process.env.OPENAI_BASE_URL ?? "https://api.openai.com/v1";

      const openai = createOpenAICompatible({
        apiKey,
        baseURL,
        /**
         * Explicitly tag the provider so downstream telemetry can distinguish
         * real OpenAI traffic from other compatibility-mode integrations.
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
           * The reasoning scenarios stream structured <reasoning> sections from
           * the o4-mini family which we unwrap into dedicated UI panes.
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
    })();
