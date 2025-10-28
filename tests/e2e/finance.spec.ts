import { expect, test } from "@playwright/test";

import { mountFinanceHarness } from "./harness-utils";
import { interceptFinanceRoutes, FIRST_CANDLE_TS, SECOND_CANDLE_TS } from "./finance-fixtures";
import { freezeTime } from "../pages/chat";

test.describe("Finance artefact harness", () => {
  test.beforeEach(async ({ page }) => {
    await freezeTime(page);
    await interceptFinanceRoutes(page);
    await mountFinanceHarness(page);
    await expect(page.getByTestId("chart-artifact")).toBeVisible();
  });

  test("displays chart details and supports overlay toggles", async ({ page }) => {
    const details = page.getByTestId("finance-chart-details");
    await expect(details).toContainText("43250.00");

    await page.getByTestId(`select-candle-${FIRST_CANDLE_TS}`).click();
    await expect(details).toContainText("43000.00");
    await expect(details).toContainText("2000.00");

    const overlaysList = page.getByTestId("active-overlays");
    await expect(overlaysList).toContainText("SMA 50");

    const smaToggle = page.getByTestId("overlay-toggle-sma-50").locator("input[type=checkbox]");
    await smaToggle.uncheck();
    await expect(overlaysList).not.toContainText("SMA 50");
    await smaToggle.check();
    await expect(overlaysList).toContainText("SMA 50");
  });

  test("renders backtest metrics and trade history", async ({ page }) => {
    const report = page.getByTestId("finance-backtest-report");
    await expect(report).toContainText("Performance cumulée");
    await expect(report).toContainText("75.00 %");
    await expect(report).toContainText("CAGR");

    const tradesTable = report.getByRole("table", { name: "Historique des positions" });
    await expect(tradesTable).toBeVisible();
    await expect(tradesTable).toContainText("Entrée");
    await expect(tradesTable).toContainText("Sortie");
  });

  test("shows fundamentals and latest news artefacts", async ({ page }) => {
    const fundamentals = page.getByTestId("fundamentals-card");
    await expect(fundamentals).toContainText("NVDA");
    await expect(fundamentals).toContainText("Capitalisation");

    const news = page.getByTestId("finance-news");
    await expect(news).toContainText("NVDA dépasse les attentes trimestrielles");
    await expect(news).toContainText("Le GPU Blackwell gagne du terrain");
    await expect(news).toContainText("Partenariat stratégique");
  });
});

