import { expect, test } from "@playwright/test";

const ohlcvPayload = {
  symbol: "BTC/USDT",
  timeframe: "1h",
  rows: [
    { ts: 1_700_000_000, o: 10000, h: 10200, l: 9950, c: 10100, v: 120 },
    { ts: 1_700_000_600, o: 10100, h: 10300, l: 10050, c: 10250, v: 150 },
  ],
};

const indicatorPayload = {
  series: [
    {
      ts: 1_700_000_000,
      values: {
        ema_50: 10080,
        rsi_14: 55,
        macd: 12,
        macd_signal: 10,
        macd_hist: 2,
        bb_upper: 10300,
        bb_lower: 9900,
        bb_middle: 10100,
      },
    },
  ],
};

test.describe("chart analysis page", () => {
  test("renders SSE-driven analysis", async ({ page }) => {
    await page.route("**/api/v1/market/ohlcv**", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(ohlcvPayload),
      });
    });

    await page.route("**/api/v1/indicators/compute", async (route) => {
      await route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(indicatorPayload),
      });
    });

    await page.route("**/stream/analysis**", async (route) => {
      const events = [
        'event: step:end\ndata: {"payload":{"stage":"indicators"}}\n\n',
        'event: result_partial\ndata: {"payload":{"levels":[{"kind":"support","label":"fort","strength":0.8,"price":10100}]}}\n\n',
        'event: token\ndata: {"payload":{"text":"Résumé "}}\n\n',
        'event: token\ndata: {"payload":{"text":"final"}}\n\n',
        'event: result_final\ndata: {"payload":{"summary":"Résumé final","levels":[{"kind":"resistance","label":"général","strength":0.6,"price":10500,"ts_range":[1,2]}],"patterns":[{"name":"Head & Shoulders","score":0.9}]}}\n\n',
        'event: done\ndata: {"payload":{"status":"ok"}}\n\n',
      ];
      await route.fulfill({
        status: 200,
        headers: {
          "content-type": "text/event-stream",
          "cache-control": "no-cache",
          connection: "keep-alive",
        },
        body: events.join(""),
      });
    });

    await page.goto("/chart");
    await page.getByTestId("chart-start").click();

    await expect(page.getByTestId("analysis-summary")).toContainText("Résumé final");
    await expect(page.getByTestId("analysis-patterns")).toContainText("Head & Shoulders");
  });
});
