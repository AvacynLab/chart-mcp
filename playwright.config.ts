import { defineConfig, devices } from "@playwright/test";
import path from "node:path";

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
    baseURL: process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000",
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
});
