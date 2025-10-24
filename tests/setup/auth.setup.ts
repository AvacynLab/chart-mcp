import { chromium, expect, FullConfig } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const STORAGE_DIR = path.resolve(__dirname, "../.auth");
const STORAGE_STATE = path.join(STORAGE_DIR, "regular.json");

/**
 * Global Playwright setup that provisions a regular user session once per test
 * suite. The flow mirrors the manual steps an operator would perform on the
 * login page: visit `/login`, submit credentials, wait for the redirect to
 * `/chat`, and finally persist the storage state for downstream tests.
 */
async function storageStateExists(): Promise<boolean> {
  try {
    await fs.access(STORAGE_STATE);
    return true;
  } catch {
    return false;
  }
}

async function performLogin(baseURL: string): Promise<void> {
  await fs.mkdir(STORAGE_DIR, { recursive: true });

  if (await storageStateExists()) {
    return;
  }

  const browser = await chromium.launch();
  const page = await browser.newPage();

  try {
    await page.goto(`${baseURL}/login`);
    await expect(page.getByTestId("auth-root")).toBeVisible();
    await expect(page.getByTestId("auth-email")).toBeVisible();
    await page.getByTestId("auth-email").fill("regular@example.com");
    await page.getByTestId("auth-password").fill("super-secret");
    await Promise.all([
      page.waitForURL(`${baseURL}/chat`),
      page.getByTestId("auth-submit").click(),
    ]);

    await expect(page).toHaveURL(`${baseURL}/chat`);
    await page.context().storageState({ path: STORAGE_STATE });
  } finally {
    await browser.close();
  }
}

export default async function globalSetup(config: FullConfig): Promise<void> {
  const projectBaseURL = config.projects[0]?.use?.baseURL;
  const baseURL = projectBaseURL ?? process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
  await performLogin(baseURL);
}

export { STORAGE_STATE };
