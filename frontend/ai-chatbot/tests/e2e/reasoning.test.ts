import { expect, test } from "../fixtures";
import { ChatPage } from "../pages/chat";

/**
 * Guard against nullable assistant messages so reasoning assertions do not
 * rely on non-null assertions.
 */
function requireAssistantMessage(
  message: Awaited<ReturnType<ChatPage["getRecentAssistantMessage"]>>
) {
  if (!message) {
    throw new Error("Assistant message should be available after generation.");
  }
  return message;
}

test.describe("chat activity with reasoning", () => {
  let chatPage: ChatPage;

  test.beforeEach(async ({ curieContext }) => {
    chatPage = new ChatPage(curieContext.page);
    await chatPage.createNewChat();
  });

  test("Curie can send message and generate response with reasoning", async () => {
    await chatPage.sendUserMessage("Why is the sky blue?");
    await chatPage.isGenerationComplete();

    const assistantMessage = await chatPage.getRecentAssistantMessage();
    const renderedAssistantMessage = requireAssistantMessage(assistantMessage);
    expect(renderedAssistantMessage.content).toBe("It's just blue duh!");

    expect(renderedAssistantMessage.reasoning).toBe(
      "The sky is blue because of rayleigh scattering!"
    );
  });

  test("Curie can toggle reasoning visibility", async () => {
    await chatPage.sendUserMessage("Why is the sky blue?");
    await chatPage.isGenerationComplete();

    const assistantMessage = await chatPage.getRecentAssistantMessage();
    const renderedAssistantMessage = requireAssistantMessage(assistantMessage);
    const reasoningElement =
      renderedAssistantMessage.element.getByTestId("message-reasoning");
    expect(reasoningElement).toBeVisible();

    await renderedAssistantMessage.toggleReasoningVisibility();
    await expect(reasoningElement).not.toBeVisible();

    await renderedAssistantMessage.toggleReasoningVisibility();
    await expect(reasoningElement).toBeVisible();
  });

  test("Curie can edit message and resubmit", async () => {
    await chatPage.sendUserMessage("Why is the sky blue?");
    await chatPage.isGenerationComplete();

    const assistantMessage = await chatPage.getRecentAssistantMessage();
    const renderedAssistantMessage = requireAssistantMessage(assistantMessage);
    const reasoningElement =
      renderedAssistantMessage.element.getByTestId("message-reasoning");
    expect(reasoningElement).toBeVisible();

    const userMessage = await chatPage.getRecentUserMessage();

    await userMessage.edit("Why is grass green?");
    await chatPage.isGenerationComplete();

    const updatedAssistantMessage = await chatPage.getRecentAssistantMessage();
    const renderedUpdatedAssistantMessage = requireAssistantMessage(
      updatedAssistantMessage
    );

    expect(renderedUpdatedAssistantMessage.content).toBe(
      "It's just green duh!"
    );

    expect(renderedUpdatedAssistantMessage.reasoning).toBe(
      "Grass is green because of chlorophyll absorption!"
    );
  });
});
