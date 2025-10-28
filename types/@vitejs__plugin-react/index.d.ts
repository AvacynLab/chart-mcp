import type { PluginOption } from "vite";

/**
 * Minimal subset of the React plugin options required for our Vitest setup.
 * The real package exposes many additional knobs, but we only need the
 * capability to register the plugin within the Vite configuration used by
 * Vitest.
 */
export interface ReactPluginOptions {
  readonly babel?: Record<string, unknown>;
}

declare function reactPlugin(options?: ReactPluginOptions): PluginOption;

export default reactPlugin;
export type { ReactPluginOptions as Options };
