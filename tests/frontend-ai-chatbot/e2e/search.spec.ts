import { getUnixTime } from "date-fns";
import { expect, test as baseTest } from "../fixtures";
import { createAuthenticatedContext, type UserContext } from "../helpers";

/** Dedicated Playwright harness exposing deterministic search artefact data. */
const HARNESS_PATH = "/playwright/search-harness" as const;

const test = baseTest.extend<{ searchContext: UserContext }>({
  searchContext: [
    async ({ browser }, use, workerInfo) => {
      const context = await createAuthenticatedContext({
        browser,
        name: `search-${workerInfo.workerIndex}-${getUnixTime(new Date())}`,
        redirectPath: HARNESS_PATH,
      });

      await use(context);
      await context.context.close();
    },
    { scope: "worker" },
  ],
});

test.describe("Search artefact streaming", () => {
  test("streams a batch of results and signals completion", async ({ searchContext }) => {
    const { page } = searchContext;

    await page.waitForURL(new RegExp(`${HARNESS_PATH}$`));
    await expect(page.getByTestId("search-harness-heading")).toBeVisible();

    await page.waitForFunction(() => {
      const stream = (window as typeof window & { __chartMcpDataStream?: any[] })
        .__chartMcpDataStream;
      if (!Array.isArray(stream) || stream.length === 0) {
        return false;
      }

      const hasBatch = stream.some(
        (part) =>
          part?.type === "data-search:batch" &&
          Array.isArray(part?.data) &&
          part.data.length > 0,
      );
      const hasFinish = stream.some((part) => part?.type === "data-finish");
      return hasBatch && hasFinish;
    });

    const snapshot = await page.evaluate(() => {
      const stream = (window as typeof window & { __chartMcpDataStream?: any[] })
        .__chartMcpDataStream || [];
      const batches = stream
        .filter((part: any) => part?.type === "data-search:batch")
        .flatMap((part: any) => (Array.isArray(part?.data) ? part.data : []));
      const finishCount = stream.filter((part: any) => part?.type === "data-finish").length;
      return { batches, finishCount };
    });

    expect(snapshot.batches.length).toBeGreaterThan(0);
    for (const result of snapshot.batches) {
      expect(typeof result.title).toBe("string");
      expect(result.title.length).toBeGreaterThan(0);
      expect(typeof result.url).toBe("string");
      expect(result.url.length).toBeGreaterThan(0);
      expect(typeof result.snippet).toBe("string");
      expect(result.snippet.length).toBeGreaterThan(0);
      expect(typeof result.source).toBe("string");
      expect(result.source.length).toBeGreaterThan(0);
      expect(typeof result.score).toBe("number");
    }
    expect(snapshot.finishCount).toBeGreaterThanOrEqual(1);

    const cards = await page.getByTestId("search-result-card").all();
    expect(cards.length).toBeGreaterThan(0);

    const firstCard = cards[0];
    await expect(firstCard.getByTestId("search-result-title")).not.toHaveText("");
    await expect(firstCard.getByTestId("search-result-snippet")).not.toHaveText("");
    await expect(firstCard.getByTestId("search-result-source")).not.toHaveText("");
    await expect(firstCard.getByTestId("search-result-score")).toContainText("score:");

    const finishLabel = await page.getByTestId("search-finish-count").innerText();
    expect(finishLabel).toMatch(/\d+/);
  });
});
