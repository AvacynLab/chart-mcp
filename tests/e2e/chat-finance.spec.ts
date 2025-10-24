import { expect, test } from "@playwright/test";

import { ChatPage, freezeTime } from "../pages/chat";

/**
 * Full-stack regression test exercising the protected `/chat` route with the
 * deterministic finance artefacts exposed by the server component. The assertions
 * mirror the manual validation checklist: the chart details render without the
 * Next.js error overlay and the overlay toggles remain interactive.
 */
test.describe("Chat page finance demo", () => {
  test.beforeEach(async ({ page }) => {
    await freezeTime(page);
  });

  test("renders the BTCUSD chart with stable overlays", async ({ page }) => {
    const chat = new ChatPage(page);
    await chat.goto();

    await expect(chat.financeChart).toBeVisible();
    await expect(chat.financeDetails).toContainText("43250.00");
    await expect(chat.financeDetails).toContainText("250.00 (0.58%)");

    // The SMA 50 overlay is enabled by default – toggling it off removes the pill
    // element from the summary list and re-enabling it restores the badge.
    const smaToggle = chat.overlayToggle("sma-50");
    await expect(smaToggle).toBeChecked();
    await smaToggle.uncheck();
    await expect(chat.overlayPill("sma-50")).toHaveCount(0);
    await smaToggle.check();
    await expect(chat.overlayPill("sma-50")).toHaveCount(1);

    const overlayWarning = page.locator(
      "text=Application error: a client-side exception has occurred",
    );
    await expect(overlayWarning).toHaveCount(0);
  });
});
