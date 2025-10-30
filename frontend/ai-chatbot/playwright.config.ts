import { readFileSync, existsSync } from "node:fs";
import { defineConfig, devices } from "@playwright/test";

/** Minimal `.env` loader to keep the Playwright config self-contained. */
function loadEnvFile(path: string): void {
  if (!existsSync(path)) {
    return;
  }

  const contents = readFileSync(path, "utf8");
  for (const rawLine of contents.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) {
      continue;
    }
    const [key, ...rest] = line.split("=");
    if (!key) {
      continue;
    }
    const value = rest.join("=").trim().replace(/^"|"$/g, "");
    if (!(key in process.env)) {
      process.env[key] = value;
    }
  }
}

loadEnvFile(".env.local");

/* Use process.env.PORT by default and fallback to port 3000 */
const PORT = process.env.PORT || 3000;
// Auth.js requires a stable secret even during local smoke tests. Ensure the
// value is set before Playwright spawns the Next.js dev server so every worker
// (and the server itself) inherits the same key.
process.env.AUTH_SECRET = process.env.AUTH_SECRET || "playwright-secret";
// Flag the runtime as being driven by Playwright. The frontend falls back to a
// hermetic in-memory database when this marker is present which keeps the
// end-to-end suite independent from external Postgres services.
process.env.PLAYWRIGHT = process.env.PLAYWRIGHT || "1";
// Route Playwright finance flows to the deterministic SSE fixture exposed by
// the Next.js dev server. Allow overrides so developers can opt into bespoke
// backends without editing the config.
const apiBaseURL = process.env.MCP_API_BASE || `http://localhost:${PORT}/api/test-backend`;
const sessionUser = process.env.MCP_SESSION_USER || "playwright-e2e";
const streamDebugFlag =
  process.env.NEXT_PUBLIC_ENABLE_E2E_STREAM_DEBUG || "1";

/**
 * Set webServer.url and use.baseURL with the location
 * of the WebServer respecting the correct set port
 */
const baseURL = `http://localhost:${PORT}`;

/** Allow external servers to satisfy the Playwright web server contract. */
const shouldStartWebServer = !process.env.PLAYWRIGHT_SKIP_WEB_SERVER;

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: "./tests",
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 2 : 8,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: "html",
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: "retain-on-failure",
  },

  /* Configure global timeout for each test */
  timeout: 240 * 1000, // 120 seconds
  expect: {
    timeout: 240 * 1000,
  },

  /* Configure projects */
  projects: [
    {
      name: "e2e",
      // Accept both `.test.ts` and `.spec.ts` filenames so locally-scoped runs
      // (e.g. `pnpm exec playwright test tests/e2e/foo.spec.ts`) align with the
      // suite Playwright executes in CI. Relying on a single suffix previously
      // meant the newly added finance scenario never ran on GitHub Actions.
      testMatch: /e2e\/.*\.(test|spec)\.ts$/,
      use: {
        ...devices["Desktop Chrome"],
      },
    },
    {
      name: "routes",
      // Keep parity with the e2e project by supporting the `.spec.ts` suffix
      // as well. The dual extension format mirrors Vitest defaults and removes
      // accidental friction when porting regression scenarios across runners.
      testMatch: /routes\/.*\.(test|spec)\.ts$/,
      // The finance/search route mappers are exercised via Vitest because they
      // rely on extensive request mocking and stream synthesis. Excluding them
      // here prevents Playwright from attempting to require the Vitest runtime
      // and failing with CommonJS import errors in CI.
      testIgnore: [
        /routes\/tools-finance\.spec\.ts$/,
        /routes\/tools-search\.spec\.ts$/,
      ],
      use: {
        ...devices["Desktop Chrome"],
      },
    },

    // {
    //   name: 'firefox',
    //   use: { ...devices['Desktop Firefox'] },
    // },

    // {
    //   name: 'webkit',
    //   use: { ...devices['Desktop Safari'] },
    // },

    /* Test against mobile viewports. */
    // {
    //   name: 'Mobile Chrome',
    //   use: { ...devices['Pixel 5'] },
    // },
    // {
    //   name: 'Mobile Safari',
    //   use: { ...devices['iPhone 12'] },
    // },

    /* Test against branded browsers. */
    // {
    //   name: 'Microsoft Edge',
    //   use: { ...devices['Desktop Edge'], channel: 'msedge' },
    // },
    // {
    //   name: 'Google Chrome',
    //   use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    // },
  ],

  /* Run your local dev server before starting the tests */
  webServer: shouldStartWebServer
    ? {
        // Turbopack currently panics in CI ("Next.js package not found"),
        // preventing the finance scenario from even starting. Force the legacy
        // webpack-based dev server which is slower but significantly more stable
        // for automated end-to-end smoke tests by delegating to the dedicated
        // `dev:playwright` script.
        command: "pnpm --filter ai-chatbot dev:playwright",
        url: `${baseURL}/ping`,
        timeout: 120 * 1000,
        reuseExistingServer: false,
        env: {
          MCP_API_BASE: apiBaseURL,
          NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL || apiBaseURL,
          MCP_API_TOKEN: process.env.MCP_API_TOKEN || "test-token",
          MCP_SESSION_USER: sessionUser,
          NEXT_PUBLIC_ENABLE_E2E_STREAM_DEBUG: streamDebugFlag,
          // Auth.js refuses to start without a secret key. Provide a deterministic
          // fallback so local contributors are not forced to create an `.env` when
          // running the smoke suite.
          AUTH_SECRET: process.env.AUTH_SECRET || "playwright-secret",
          PLAYWRIGHT: process.env.PLAYWRIGHT || "1",
        },
      }
    : undefined,
});
