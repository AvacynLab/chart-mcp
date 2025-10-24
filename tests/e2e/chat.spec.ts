import { expect, test } from "@playwright/test";

/**
 * Smoke test ensuring the authenticated storage state produced by the global
 * setup grants access to the protected chat page without triggering a redirect
 * back to `/login`.
 */
test("chat page renders for regular sessions", async ({ page }) => {
  await page.goto("/chat");

  await expect(page.getByTestId("chat-root")).toBeVisible();
  await expect(page.getByTestId("chat-messages")).toBeVisible();
});
