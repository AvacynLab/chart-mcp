import { defineConfig } from "vitest/config";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const rootDir = dirname(fileURLToPath(new URL(import.meta.url)));

export default defineConfig(async () => {
  // Chargement dynamique du plugin React pour éviter les conflits CJS/ESM
  // lorsqu'il est importé par Vitest en environnement Node.
  const react = (await import("@vitejs/plugin-react")).default;

  return {
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
  };
});
