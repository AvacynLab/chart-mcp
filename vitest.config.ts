import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const rootDir = dirname(fileURLToPath(new URL(import.meta.url)));

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    setupFiles: [resolve(rootDir, "vitest.setup.ts")],
    include: [
      "app/**/*.test.{ts,tsx}",
      "components/**/*.test.{ts,tsx}",
      "lib/**/*.test.ts",
    ],
    coverage: {
      reporter: ["text", "lcov"],
      include: ["components/**/*.tsx", "app/**/*.tsx", "lib/**/*.ts"],
    },
    globals: true,
    css: false,
    exclude: ["tests/e2e/**", "tests/setup/**"],
  },
  resolve: {
    alias: {
      "@app": resolve(rootDir, "app"),
      "@components": resolve(rootDir, "components"),
      "@lib": resolve(rootDir, "lib"),
      "next/headers": resolve(rootDir, "tests/stubs/next-headers.ts"),
    },
  },
});
