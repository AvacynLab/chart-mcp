import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const workspaceRoot = path.resolve(fileURLToPath(new URL(".", import.meta.url)));

/**
 * Vitest configuration mirroring the workspace path aliases so that tests can
 * import application modules via the same `@/` prefix used in production
 * source code. Coverage is generated with v8 to align with the CI reporting
 * requirements configured in the workflow.
 */
export default defineConfig({
  resolve: {
    alias: {
      "@": workspaceRoot,
      "~~/chart-components": path.join(workspaceRoot, "thirdparty/chart-components"),
    },
  },
  test: {
    alias: {
      "@": workspaceRoot,
      "~~/chart-components": path.join(workspaceRoot, "thirdparty/chart-components"),
    },
    environment: "node",
    globals: true,
    include: [
      "tests/routes/**/*.spec.ts",
      "tests/routes/**/*.spec.tsx",
      "tests/**/*.{vitest,unit}.ts",
      "tests/**/*.{vitest,unit}.tsx",
    ],
    exclude: [
      "tests/e2e/**",
      "tests/pages/**",
      "tests/fixtures.ts",
      "tests/prompts/**",
    ],
    coverage: {
      provider: "v8",
      reporter: ["text", "lcov", "json-summary"],
      reportsDirectory: path.join(workspaceRoot, "coverage"),
      include: [
        "app/**/*.{ts,tsx}",
        "artifacts/**/*.{ts,tsx}",
        "components/**/*.{ts,tsx}",
        "hooks/**/*.{ts,tsx}",
        "lib/**/*.{ts,tsx}",
      ],
    },
  },
});
