import { expect, test } from "@playwright/test";

import { mountFinanceHarness } from "./harness-utils";
import { interceptFinanceRoutes } from "./finance-fixtures";
import { freezeTime } from "../pages/chat";

test.describe("Finance artefact accessibility", () => {
  test.beforeEach(async ({ page }) => {
    await freezeTime(page);
    await interceptFinanceRoutes(page);
    await mountFinanceHarness(page);
    await expect(page.getByTestId("finance-chart-artifact")).toBeVisible();
  });

  test("exposes accessible semantics and resilient fallbacks", async ({ page }) => {
    await expect(page.getByRole("heading", { level: 2, name: /BTCUSD/i })).toBeVisible();

    const toggles = ["sma-50", "sma-200", "ema-21"];
    for (const id of toggles) {
      await page.getByTestId(`overlay-toggle-${id}`).locator("input[type=checkbox]").uncheck();
    }
    await expect(page.getByTestId("overlay-empty")).toBeVisible();

    const metricsTable = page.getByRole("table", { name: "Métriques principales" });
    await expect(metricsTable).toBeVisible();
    const tradesTable = page.getByRole("table", { name: "Historique des positions" });
    await expect(tradesTable).toBeVisible();

    const fundamentals = page.getByTestId("fundamentals-card");
    await expect(fundamentals).toHaveAttribute("aria-label", /NVDA/i);

    const newsSection = page.getByTestId("finance-news");
    await expect(newsSection.getByRole("listitem")).toHaveCount(3);

    await expect(page.getByText(/Application error: a client-side exception/i)).toHaveCount(0);
  });
});

