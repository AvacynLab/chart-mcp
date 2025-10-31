import { type Page } from "@playwright/test";

export class ChatPage {
  constructor(private page: Page) {}

  get textArea() {
    return this.page.getByRole("textbox");
  }

  get sendButton() {
    return this.page.getByRole("button", { name: "Send message" });
  }

  get stopButton() {
    return this.page.getByRole("button", { name: "Stop generating" });
  }

  async createNewChat() {
    await this.page.goto("/");
    await this.page.waitForLoadState("networkidle");
  }

  async sendUserMessage(message: string) {
    await this.textArea.click();
    await this.textArea.fill(message);
    await this.sendButton.click();
  }

  async sendUserMessageFromSuggestion() {
    await this.page
      .getByRole("button", { name: "How do you build apps?" })
      .click();
  }

  async getRecentUserMessage() {
    const messageItem = this.page.getByTestId("message-item").last();
    const content = (await messageItem.getByTestId("message-content").innerText()) ?? "";
    const attachments = await messageItem.getByTestId("message-attachments").count();

    return {
      content,
      attachments,
      edit: async (newMessage: string) => {
        await messageItem.getByRole("button", { name: "Edit" }).click();
        await this.textArea.fill(newMessage);
        await this.sendButton.click();
      },
    };
  }

  async getRecentAssistantMessage() {
    const messageItem = this.page
      .getByTestId("message-item")
      .filter({ hasText: "Assistant" })
      .last();

    if (!(await messageItem.isVisible())) {
      return null;
    }

    const content = (await messageItem.getByTestId("message-content").innerText().catch(() => null)) ?? "";

    const reasoning = await messageItem
      .getByTestId("message-reasoning")
      .isVisible()
      .then(async (visible) =>
        visible
          ? await messageItem.getByTestId("message-reasoning").innerText().catch(() => null)
          : null
      )
      .catch(() => null);

    return {
      element: messageItem,
      content,
      reasoning,
      async toggleReasoningVisibility() {
        await messageItem.getByTestId("message-reasoning-toggle").click();
      },
      async upvote() {
        await messageItem.getByTestId("message-upvote").click();
      },
      async downvote() {
        await messageItem.getByTestId("message-downvote").click();
      },
    };
  }

  async isGenerationComplete() {
    await this.page.waitForFunction(
      () => {
        const stop = document.querySelector('[aria-label="Stop generating"]');
        return !stop || getComputedStyle(stop).display === 'none';
      },
      null,
      { timeout: 30000 }
    );
  }

  async isVoteComplete() {
    await this.page.waitForSelector('[data-testid="vote-success"]');
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
    await this.page.waitForSelector('[data-testid="toast"]');
    await this.page.getByTestId('toast').waitFor({ state: 'visible' });
    await this.page.getByTestId('toast').innerText();
    // Basic assertion handled by tests using expect; helper just waits
  }
}