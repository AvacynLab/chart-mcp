import { readFileSync, existsSync } from "node:fs";
import path from "node:path";
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

// Try loading .env.local from several likely locations so Playwright picks up
// the environment variables developers often store at the repository root
// (e.g. when they pull secrets from Vercel into `./.env.local`). We prefer
// the frontend folder `.env.local` first, then the repository root.
const candidateEnvPaths = [
  path.resolve(__dirname, ".env.local"),
  path.resolve(__dirname, "..", ".env.local"),
  path.resolve(process.cwd(), ".env.local"),
];

for (const p of candidateEnvPaths) {
  if (existsSync(p)) {
    // loadEnvFile expects a relative path; call with the absolute path
    loadEnvFile(p);
    // expose which file we loaded for easier debugging in CI logs
    // eslint-disable-next-line no-console
    console.log(`Loaded environment variables from: ${p}`);
    break;
  }
}

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
const useRealServices = process.env.PLAYWRIGHT_USE_REAL_SERVICES === "1";

/**
 * Set webServer.url and use.baseURL with the location of the web server while
 * defaulting to `http://localhost`.  NextAuth's strict host validation treats
 * `localhost` as a trusted origin, whereas `127.0.0.1` can trigger "Host must
 * be trusted" responses even when `AUTH_TRUST_HOST` is exported.  The explicit
 * override remains available through `PLAYWRIGHT_TEST_BASE_URL` for advanced
 * scenarios.
 */
const baseURL =
  process.env.PLAYWRIGHT_TEST_BASE_URL || `http://localhost:${PORT}`;

/** Allow external servers to satisfy the Playwright web server contract. */
const shouldStartWebServer = !process.env.PLAYWRIGHT_SKIP_WEB_SERVER;

/**
 * See https://playwright.dev/docs/test-configuration.
 */
export default defineConfig({
  testDir: "../../tests/frontend-ai-chatbot",
  testMatch: "**/*.{test,spec}.ts",
  /* Run tests in files in parallel */
  fullyParallel: true,
  /* Fail the build on CI if you accidentally left test.only in the source code. */
  forbidOnly: !!process.env.CI,
  /* Retry on CI only */
  retries: process.env.CI ? 1 : 0,
  /* Opt out of parallel tests on CI. */
  workers: process.env.CI ? 2 : 8,
  /* Reporter to use. See https://playwright.dev/docs/test-reporters */
  reporter: "html",
  /* Shared settings for all the projects below. See https://playwright.dev/docs/api/class-testoptions. */
  use: {
    /* Base URL to use in actions like `await page.goto('/')`. */
    baseURL,

    /* Collect trace when retrying the failed test. See https://playwright.dev/docs/trace-viewer */
    trace: "on-first-retry",
    /* Capture screenshots on failure to simplify diagnosis without bloating the
       happy-path artifact footprint. */
    screenshot: "only-on-failure",
    /* Add safe launch options for CI / container environments to avoid
       sandbox-related crashes when running headless browsers inside Docker
       or limited containers. These flags are harmless locally and improve
       stability in automated runs. */
    // Force headless by default; can be disabled by setting PLAYWRIGHT_HEADLESS=false
    headless: process.env.PLAYWRIGHT_HEADLESS !== "false",
    launchOptions: {
      args: [
        "--no-sandbox",
        "--disable-setuid-sandbox",
        "--disable-dev-shm-usage",
        "--disable-gpu",
        "--disable-extensions",
      ],
    },
  },

  /* Configure global timeout for each test */
  timeout: 240 * 1000, // 240 seconds
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
        command:
          "sh -c 'if [ \"${CI:-}\" = \"true\" ]; then pnpm --filter ai-chatbot exec next build && pnpm --filter ai-chatbot exec next start --hostname 127.0.0.1 --port ${PORT}; else pnpm --filter ai-chatbot dev:playwright; fi'",
        url: `${baseURL}/ping`,
  // Allow a longer startup window for Next.js compilation in dev mode
  timeout: 300 * 1000,
  // Allow reusing an already-running Next.js instance to avoid races
  // when developers start the server manually before running tests.
  reuseExistingServer: true,
        env: {
          MCP_API_BASE: apiBaseURL,
          NEXT_PUBLIC_API_BASE: process.env.NEXT_PUBLIC_API_BASE || apiBaseURL,
          MCP_API_TOKEN: process.env.MCP_API_TOKEN || "test-token",
          MCP_SESSION_USER: sessionUser,
          NEXT_PUBLIC_ENABLE_E2E_STREAM_DEBUG: streamDebugFlag,
          NEXTAUTH_URL: baseURL,
          NEXTAUTH_URL_INTERNAL: baseURL,
          AUTH_TRUST_HOST: process.env.AUTH_TRUST_HOST || "true",
          PLAYWRIGHT_USE_REAL_SERVICES: useRealServices ? "1" : "0",
          // Auth.js refuses to start without a secret key. Provide a deterministic
          // fallback so local contributors are not forced to create an `.env` when
          // running the smoke suite.
          AUTH_SECRET: process.env.AUTH_SECRET || "playwright-secret",
          PLAYWRIGHT: process.env.PLAYWRIGHT || "1",
        },
      }
    : undefined,
});
