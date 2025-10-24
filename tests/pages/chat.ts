import { expect, Locator, Page } from "@playwright/test";

/**
 * Dedicated page-object encapsulating the selectors and actions exercised by the
 * Playwright suites targeting the protected chat experience. Centralising the
 * queries here keeps the specs readable and resilient to future UI tweaks.
 */
export class ChatPage {
  private readonly page: Page;

  public constructor(page: Page) {
    this.page = page;
  }

  /** Navigate to the chat route and ensure the auth guard grants access. */
  public async goto(path: string = "/chat"): Promise<void> {
    await this.page.goto(path);
    await this.waitForReady();
  }

  /** Wait for the main chat container to be rendered. */
  public async waitForReady(): Promise<void> {
    await expect(this.root).toBeVisible();
  }

  /** Root chat locator exposed for assertions. */
  public get root(): Locator {
    return this.page.getByTestId("chat-root");
  }

  /** Locator targeting the scrolling message container. */
  public get messages(): Locator {
    return this.page.getByTestId("chat-messages");
  }

  /** Locator for the finance chart artefact rendered within the conversation. */
  public get financeChart(): Locator {
    return this.page.getByTestId("finance-chart-artifact");
  }

  /** Locator exposing the candle details pane accompanying the chart. */
  public get financeDetails(): Locator {
    return this.page.getByTestId("finance-chart-details");
  }

  /** Retrieve the checkbox toggle for a given overlay identifier. */
  public overlayToggle(id: string): Locator {
    return this.page.getByTestId(`overlay-toggle-${id}`).locator("input[type=checkbox]");
  }

  /** Locator referencing the active overlay pill list item. */
  public overlayPill(id: string): Locator {
    return this.page.getByTestId(`overlay-pill-${id}`);
  }
}

/**
 * Freeze the client-side clock to a deterministic instant so date formatting in
 * the UI remains stable across runs.
 */
export async function freezeTime(page: Page, isoTimestamp = "2024-01-01T00:00:00.000Z"): Promise<void> {
  const millis = Date.parse(isoTimestamp);
  await page.addInitScript((fixed) => {
    const FixedDate = class extends Date {
      public constructor(...args: ConstructorParameters<typeof Date>) {
        if (args.length === 0) {
          super(fixed);
          return;
        }
        super(...args);
      }

      public static now(): number {
        return fixed;
      }
    };

    // @ts-expect-error - override global constructors for deterministic behaviour
    window.Date = FixedDate;
  }, millis);
}
