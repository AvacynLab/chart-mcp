import fs from "node:fs";
import path from "node:path";
import {
  type APIRequestContext,
  type Browser,
  type BrowserContext,
  expect,
  type Page,
} from "@playwright/test";
import { generateId } from "ai";
import { getUnixTime } from "date-fns";
import { ChatPage } from "./pages/chat";

/**
 * Default origin used to craft absolute URLs during Playwright runs. The
 * fallback matches the value defined in {@link playwright.config.ts}.
 */
// Resolve base URL for tests. Prefer explicit Playwright test override,
// then public API base vars, then fall back to the configured PORT.
export const DEFAULT_BASE_URL =
  process.env.PLAYWRIGHT_TEST_BASE_URL ||
  process.env.NEXT_PUBLIC_API_BASE_URL ||
  process.env.MCP_API_BASE ||
  process.env.PLAYWRIGHT_BASE_URL ||
  `http://127.0.0.1:${process.env.PORT || 3000}`;

/** Convenience guard that flips to `true` for hermetic Playwright flows. */
const isPlaywrightEnvironment = Boolean(
  process.env.PLAYWRIGHT ?? process.env.CI_PLAYWRIGHT
);

export type UserContext = {
  context: BrowserContext;
  page: Page;
  request: APIRequestContext;
};

export async function createAuthenticatedContext({
  browser,
  name,
  redirectPath = "/",
}: {
  browser: Browser;
  name: string;
  /** Optional path that Playwright should land on immediately after the guest
   * authentication redirect completes. Providing a lightweight target keeps
   * the expensive chat surface from compiling when a specialised harness can
   * exercise the behaviour instead.
   */
  redirectPath?: string;
}): Promise<UserContext> {
  const directory = path.join(__dirname, "../playwright/.sessions");

  if (!fs.existsSync(directory)) {
    fs.mkdirSync(directory, { recursive: true });
  }

  const storageFile = path.join(directory, `${name}.json`);

  const context = await browser.newContext();
  const page = await context.newPage();

  const chatPage = new ChatPage(page);

  const normalisedRedirectPath = redirectPath.startsWith("/")
    ? redirectPath
    : `/${redirectPath}`;

  if (isPlaywrightEnvironment) {
    // Playwright-driven runs only need a privileged guest session. Skipping
    // the interactive registration page avoids the expensive module graph
    // compilation that previously caused repeated timeouts in CI.
    console.info("[createAuthenticatedContext] signing in with guest credentials");
    const guestAuthUrl = new URL(
      `/api/auth/guest?redirectUrl=${encodeURIComponent(normalisedRedirectPath)}`,
      DEFAULT_BASE_URL
    ).toString();

    await page.goto(guestAuthUrl, { waitUntil: "domcontentloaded" });
    console.info("[createAuthenticatedContext] guest redirect complete");
  } else {
    // When running exploratory flows we still exercise the public registration
    // form to ensure regressions surface in the smoke suite.
    const email = `test-${name}@playwright.com`;
    const password = generateId();

    await page.goto(new URL("/register", DEFAULT_BASE_URL).toString());
    await page.getByPlaceholder("user@acme.com").click();
    await page.getByPlaceholder("user@acme.com").fill(email);
    await page.getByLabel("Password").click();
    await page.getByLabel("Password").fill(password);
    await page.getByRole("button", { name: "Sign Up" }).click();

    await expect(page.getByTestId("toast")).toContainText(
      "Account created successfully!"
    );
  }

  if (!isPlaywrightEnvironment || normalisedRedirectPath === "/") {
    await chatPage.createNewChat();
  }

  if (!isPlaywrightEnvironment) {
    await chatPage.chooseModelFromSelector("chat-model-reasoning");
    await expect(chatPage.getSelectedModel()).resolves.toEqual("Reasoning model");
  }

  if (!isPlaywrightEnvironment) {
    await page.waitForTimeout(1000);
  }

  if (isPlaywrightEnvironment) {
    return {
      context,
      page,
      request: context.request,
    };
  }

  await context.storageState({ path: storageFile });
  await page.close();

  const newContext = await browser.newContext({ storageState: storageFile });
  const newPage = await newContext.newPage();

  return {
    context: newContext,
    page: newPage,
    request: newContext.request,
  };
}

export function generateRandomTestUser() {
  const email = `test-${getUnixTime(new Date())}@playwright.com`;
  const password = generateId();

  return {
    email,
    password,
  };
}