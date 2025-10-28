import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

/**
 * Derive the base URL consumed by both the test runner and the web server
 * helper. The environment variable keeps GitHub Actions and local invocations
 * in sync so contributors can target alternative ports without editing the
 * configuration file.
 */
const resolvedBaseURL = process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
const resolvedUrl = new URL(resolvedBaseURL);
const resolvedHostname = resolvedUrl.hostname || "127.0.0.1";
const resolvedPort = resolvedUrl.port || "3000";

import { STORAGE_STATE } from "./tests/setup/auth.setup";

/** Shared storage state produced during the global auth setup. */
const storageStatePath = STORAGE_STATE ?? path.resolve(__dirname, "tests/.auth/regular.json");

export default defineConfig({
  testDir: "tests/e2e",
  timeout: 60_000,
  expect: {
    timeout: 5_000,
  },
  globalSetup: "./tests/setup/auth.setup.ts",
  reporter: [["html", { outputFolder: "playwright-report", open: "never" }]],
  use: {
    baseURL: resolvedBaseURL,
    storageState: storageStatePath,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { ...devices["Desktop Chrome"] },
    },
  ],
  /**
   * Automatically launch a Next.js development server for the duration of the
   * Playwright test run. This keeps local workflows and the CI pipeline in sync
   * while avoiding the fragile “remember to start pnpm dev” prerequisite.
   */
  webServer: [
    {
      command: `pnpm dev --hostname ${resolvedHostname} --port ${resolvedPort}`,
      url: `${resolvedBaseURL}/login`,
      reuseExistingServer: !process.env.CI,
      stdout: "pipe",
      stderr: "pipe",
      timeout: 120_000,
      env: {
        NEXT_TELEMETRY_DISABLED: "1",
      },
    },
  ],
});
