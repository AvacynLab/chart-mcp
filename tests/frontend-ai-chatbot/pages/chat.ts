import { expect, type Page } from "@playwright/test";

export class ChatPage {
  constructor(private page: Page) {}

  get textArea() {
    return this.page.getByTestId("multimodal-input");
  }

  get sendButton() {
    // Anchor the lookup on the explicit test identifier so the suite remains
    // resilient to future accessibility tweaks (e.g. aria-label vs. sr-only
    // content) while still asserting the button stays visible.
    return this.page.getByTestId("send-button");
  }

  get stopButton() {
    return this.page.getByTestId("stop-button");
  }

  async createNewChat() {
    await this.page.goto("/");
    await this.page.waitForLoadState("domcontentloaded");
    // The Next.js dev server may keep retrying failed font downloads when
    // outbound TLS is blocked inside CI containers. Waiting for "networkidle"
    // would therefore hang the suite, so instead wait for the chat composer to
    // appear which signals that the shell finished hydrating.
    await this.page.waitForSelector('[data-testid="send-button"]', {
      state: "visible",
    });
  }

  async sendUserMessage(message: string) {
    await this.textArea.click();
    await this.textArea.fill(message);
    await expect(this.sendButton).toBeEnabled();
    await this.sendButton.click();
  }

  async sendUserMessageFromSuggestion() {
    const suggestion = this.page.getByRole("button", { name: "How do you build apps?" });
    await suggestion.waitFor({ state: "visible" });
    await suggestion.click();
  }

  async getRecentUserMessage() {
    const messageItem = this.page
      .locator('[data-message-item="true"][data-role="user"]')
      .last();
    await messageItem.waitFor({ state: "visible" });

    const contentLocator = messageItem.getByTestId("message-content");
    await contentLocator.waitFor({ state: "visible" });
    const content = (await contentLocator.innerText()) ?? "";

    const attachmentsLocator = messageItem.getByTestId("message-attachments");
    const attachments = (await attachmentsLocator.count().catch(() => 0)) ?? 0;

    return {
      content,
      attachments,
      edit: async (newMessage: string) => {
        await messageItem.getByRole("button", { name: "Edit" }).click();
        const editor = this.page.getByTestId("message-editor");
        await editor.waitFor({ state: "visible" });
        await editor.fill(newMessage);

        const editorSubmit = this.page.getByTestId("message-editor-send-button");
        await expect(editorSubmit).toBeEnabled();
        await editorSubmit.click();
      },
    };
  }

  async getRecentAssistantMessage() {
    const messageItem = this.page
      .locator('[data-message-item="true"][data-role="assistant"]')
      .last();

    if ((await messageItem.count()) === 0) {
      return null;
    }

    await messageItem.waitFor({ state: "visible" });

    const contentLocator = messageItem.getByTestId("message-content");
    await contentLocator.waitFor({ state: "visible" });
    const content = (await contentLocator.innerText().catch(() => null)) ?? "";

    const reasoningLocator = messageItem.getByTestId("message-reasoning");
    const reasoning =
      (await reasoningLocator
        .getAttribute("data-reasoning-text")
        .catch(() => null)) ?? (await reasoningLocator.innerText().catch(() => null));

    return {
      element: messageItem,
      content,
      reasoning,
      async toggleReasoningVisibility() {
        const toggle = messageItem.getByTestId("message-reasoning-toggle");
        await toggle.waitFor({ state: "visible" });
        await toggle.click();
      },
      async upvote() {
        const upvoteButton = messageItem.getByTestId("message-upvote");
        await upvoteButton.waitFor({ state: "visible" });
        await upvoteButton.click();
      },
      async downvote() {
        const downvoteButton = messageItem.getByTestId("message-downvote");
        await downvoteButton.waitFor({ state: "visible" });
        await downvoteButton.click();
      },
    };
  }

  async isGenerationComplete() {
    await this.page.waitForFunction(
      () => {
        const stop = document.querySelector('[data-testid="stop-button"]');
        return !stop || getComputedStyle(stop).display === "none";
      },
      null,
      { timeout: 30000 }
    );
  }

  async isVoteComplete() {
    // Wait for the PATCH vote request to settle instead of relying on toast
    // notifications which can stack and trigger Playwright's strict mode.
    await this.page.waitForResponse(
      (response) =>
        response.url().includes("/api/vote") && response.request().method() === "PATCH"
    );
  }

  async chooseModelFromSelector(modelId: string) {
    await this.page.getByRole("button", { name: "Choose a model" }).click();
    await this.page.getByRole("menuitem", { name: modelId }).click();
  }

  async getSelectedModel() {
    const modelButton = this.page.getByRole("button", {
      name: "Choose a model",
    });
    return modelButton.textContent();
  }

  async addImageAttachment() {
    // Simulate a file input with a base64 encoded image
    await this.page.evaluate(() => {
      const dataTransfer = new DataTransfer();
      const file = new File(["test"], "test.png", { type: "image/png" });
      dataTransfer.items.add(file);
      const input = document.querySelector('input[type="file"]');
      if (input) {
        Object.defineProperty(input, "files", {
          value: dataTransfer.files,
        });
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
    });
  }

  async hasChatIdInUrl() {
    await this.page.waitForURL(/\/chat\/[^/]+$/);
  }

  async isElementVisible(testId: string) {
    await this.page.waitForSelector(`[data-testid="${testId}"]`, {
      state: "visible",
    });
  }

  async isElementNotVisible(testId: string) {
    await this.page.waitForSelector(`[data-testid="${testId}"]`, {
      state: "hidden",
    });
  }

  get scrollToBottomButton() {
    return this.page.getByRole("button", { name: "Scroll to bottom" });
  }

  async scrollToTop() {
    await this.page.evaluate(() => {
      window.scrollTo(0, 0);
    });
  }

  async waitForScrollToBottom() {
    await this.page.waitForFunction(() => {
      const { scrollHeight, scrollTop, clientHeight } = document.documentElement;
      const isAtBottom = Math.abs(scrollHeight - scrollTop - clientHeight) < 10;
      return isAtBottom;
    });
  }

  async sendMultipleMessages(count: number, getMessage: (i: number) => string) {
    for (let i = 0; i < count; i++) {
      await this.sendUserMessage(getMessage(i));
      await this.isGenerationComplete();
    }
  }

  async expectToastToContain(text: string) {
    const toast = this.page.getByTestId("toast").last();
    await toast.waitFor({ state: "visible" });
    await expect(toast).toContainText(text);
  }
}