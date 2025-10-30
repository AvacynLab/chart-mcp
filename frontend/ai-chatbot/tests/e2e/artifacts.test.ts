import { expect, test } from "../fixtures";
import { ArtifactPage } from "../pages/artifact";
import { ChatPage } from "../pages/chat";

/** Ensure artifact scenarios never dereference a nullable assistant message. */
function requireAssistantMessage(
  message: Awaited<ReturnType<ChatPage["getRecentAssistantMessage"]>>
) {
  if (!message) {
    throw new Error("Assistant message should be available after generation.");
  }
  return message;
}

test.describe("Artifacts activity", () => {
  let chatPage: ChatPage;
  let artifactPage: ArtifactPage;

  test.beforeEach(async ({ page }) => {
    chatPage = new ChatPage(page);
    artifactPage = new ArtifactPage(page);

    await chatPage.createNewChat();
  });

  test("Create a text artifact", async () => {
    test.fixme();
    await chatPage.createNewChat();

    await chatPage.sendUserMessage(
      "Help me write an essay about Silicon Valley"
    );
    await artifactPage.isGenerationComplete();

    expect(artifactPage.artifact).toBeVisible();

    const assistantMessage = await chatPage.getRecentAssistantMessage();
    const renderedAssistantMessage = requireAssistantMessage(assistantMessage);
    expect(renderedAssistantMessage.content).toBe(
      "A document was created and is now visible to the user."
    );

    await chatPage.hasChatIdInUrl();
  });

  test("Toggle artifact visibility", async () => {
    test.fixme();
    await chatPage.createNewChat();

    await chatPage.sendUserMessage(
      "Help me write an essay about Silicon Valley"
    );
    await artifactPage.isGenerationComplete();

    expect(artifactPage.artifact).toBeVisible();

    const assistantMessage = await chatPage.getRecentAssistantMessage();
    const renderedAssistantMessage = requireAssistantMessage(assistantMessage);
    expect(renderedAssistantMessage.content).toBe(
      "A document was created and is now visible to the user."
    );

    await artifactPage.closeArtifact();
    await chatPage.isElementNotVisible("artifact");
  });

  test("Send follow up message after generation", async () => {
    test.fixme();
    await chatPage.createNewChat();

    await chatPage.sendUserMessage(
      "Help me write an essay about Silicon Valley"
    );
    await artifactPage.isGenerationComplete();

    expect(artifactPage.artifact).toBeVisible();

    const assistantMessage = await artifactPage.getRecentAssistantMessage();
    const renderedAssistantMessage = requireAssistantMessage(assistantMessage);
    expect(renderedAssistantMessage.content).toBe(
      "A document was created and is now visible to the user."
    );

    await artifactPage.sendUserMessage("Thanks!");
    await artifactPage.isGenerationComplete();

    const secondAssistantMessage = await chatPage.getRecentAssistantMessage();
    const renderedSecondMessage = requireAssistantMessage(
      secondAssistantMessage
    );
    expect(renderedSecondMessage.content).toBe("You're welcome!");
  });
});
