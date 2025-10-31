import type { Page } from "@playwright/test";
import { getUnixTime } from "date-fns";
import { test as baseTest, expect } from "../fixtures";
import { createAuthenticatedContext, type UserContext } from "../helpers";

/**
 * Block until the client-side data stream has observed the full finance
 * lifecycle. The helper keeps the assertions deterministic by ensuring
 * step/start, metric, token, and finish payloads are already buffered before
 * the test inspects the stream snapshot.
 */
async function waitForFinanceLifecycle(page: Page) {
  await page.waitForFunction(() => {
    const stream = (window as typeof window & { __chartMcpDataStream?: any[] })
      .__chartMcpDataStream;
    if (!Array.isArray(stream) || !stream.length) {
      return false;
    }

    let hasStepStart = false;
    let hasStepEnd = false;
    let hasMetric = false;
    let hasToken = false;
    let hasFinish = false;

    for (const part of stream) {
      if (part?.type === "data-finance:step") {
        const eventName = part?.data?.event;
        if (eventName === "step:start") {
          hasStepStart = true;
        }
        if (eventName === "step:end") {
          hasStepEnd = true;
        }
        if (eventName === "metric") {
          hasMetric = true;
        }
      }
      if (
        part?.type === "data-finance:token" &&
        typeof part?.data === "string"
      ) {
        hasToken = true;
      }
      if (part?.type === "data-finish") {
        hasFinish = true;
      }
    }

    return hasStepStart && hasStepEnd && hasMetric && hasToken && hasFinish;
  });
}

const HARNESS_PATH = "/playwright/finance-harness" as const;

const test = baseTest.extend<{ adaContext: UserContext }>({
  adaContext: [
    async ({ browser }, use, workerInfo) => {
      const ada = await createAuthenticatedContext({
        browser,
        name: `ada-finance-${workerInfo.workerIndex}-${getUnixTime(new Date())}`,
        redirectPath: HARNESS_PATH,
      });

      await use(ada);
      await ada.context.close();
    },
    { scope: "worker" },
  ],
});

test.describe("Finance artifact streaming lifecycle", () => {
  test("replays the finance fixture and surfaces lifecycle markers", async ({
    adaContext,
  }) => {
    const { page } = adaContext;

    await page.waitForURL(new RegExp(`${HARNESS_PATH}$`));
    await expect(
      page.getByRole("heading", { name: "Résumé IA" })
    ).toBeVisible();

    await waitForFinanceLifecycle(page);

    const snapshot = await page.evaluate(() => {
      const stream =
        (window as typeof window & { __chartMcpDataStream?: any[] })
          .__chartMcpDataStream || [];

      const steps = stream
        .filter((part: any) => part?.type === "data-finance:step")
        .map((part: any) => ({
          event: part?.data?.event,
          payload: part?.data?.payload,
        }));

      const tokens = stream
        .filter((part: any) => part?.type === "data-finance:token")
        .map((part: any) => part?.data);

      const finishes = stream.filter(
        (part: any) => part?.type === "data-finish"
      ).length;

      return { steps, tokens, finishes };
    });

    const stepEvents = snapshot.steps.map((step) => step.event);
    expect(stepEvents).toEqual(
      expect.arrayContaining([
        "step:start",
        "metric",
        "result_partial",
        "step:end",
      ])
    );
    expect(
      snapshot.tokens.some((token) => token.includes("Analyse complète"))
    ).toBe(true);
    expect(snapshot.finishes).toBeGreaterThanOrEqual(1);

    await expect(page.getByTestId("artifact")).toBeVisible();
    await expect(page.getByTestId("artifact")).toContainText(
      "Analyse complète sur BTC/USDT."
    );
  });
});
