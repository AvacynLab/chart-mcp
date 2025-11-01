// Minimal typings for the @ai-sdk/openai-compatible helper so TypeScript can
// compile the OpenAI provider wiring without needing the upstream package to
// ship full type declarations.
declare module "@ai-sdk/openai-compatible" {
  import type { LanguageModelV2 } from "ai";

  interface OpenAICompatibleOptions {
    apiKey: string;
    baseURL?: string;
    name?: string;
  }

  interface OpenAICompatibleProvider {
    languageModel(modelId: string): LanguageModelV2;
  }

  export function createOpenAICompatible(
    options: OpenAICompatibleOptions
  ): OpenAICompatibleProvider;
}
