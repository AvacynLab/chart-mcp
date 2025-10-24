import type { Page } from "@playwright/test";

import {
  FINANCE_DEMO_FIRST_CANDLE_TS,
  FINANCE_DEMO_SECOND_CANDLE_TS,
  getFinanceDemoArtifacts,
} from "@lib/demo/finance";

export const FIRST_CANDLE_TS = FINANCE_DEMO_FIRST_CANDLE_TS;
export const SECOND_CANDLE_TS = FINANCE_DEMO_SECOND_CANDLE_TS;

const screenFixture = {
  results: [
    { symbol: "MSFT", sector: "Technology", score: 0.82, marketCap: 2_800_000_000_000 },
  ],
};

export async function interceptFinanceRoutes(page: Page): Promise<void> {
  await page.route("**/api/v1/finance/chart**", async (route) => {
    const { chart } = getFinanceDemoArtifacts();
    await route.fulfill({ json: chart });
  });
  await page.route("**/api/v1/finance/backtest", async (route) => {
    const { backtest } = getFinanceDemoArtifacts();
    await route.fulfill({ json: backtest });
  });
  await page.route("**/api/v1/finance/fundamentals**", async (route) => {
    const { fundamentals } = getFinanceDemoArtifacts();
    await route.fulfill({ json: fundamentals });
  });
  await page.route("**/api/v1/finance/quote**", async (route) => {
    const { quote } = getFinanceDemoArtifacts();
    await route.fulfill({
      json: {
        symbol: "NVDA",
        updatedAt: "2024-01-03T15:30:00Z",
        ...quote,
      },
    });
  });
  await page.route("**/api/v1/finance/news**", async (route) => {
    const { news } = getFinanceDemoArtifacts();
    await route.fulfill({ json: news });
  });
  await page.route("**/api/v1/finance/history**", async (route) => {
    await route.fulfill({ json: { symbol: "BTCUSD", timeframe: "1d", rows: [] } });
  });
  await page.route("**/api/v1/finance/screen**", async (route) => {
    await route.fulfill({ json: screenFixture });
  });
}

