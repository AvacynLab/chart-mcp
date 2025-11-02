import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { MessageContent } from "@/components/elements/message";

/**
 * Ensure message content forwards props and retains the prose styling required
 * by the Playwright E2E selectors.
 */
describe("Message content propagation", () => {
  it("exposes the requested data-testid attribute", () => {
    const markup = renderToStaticMarkup(
      <MessageContent data-testid="message-content">Hello</MessageContent>
    );

    expect(markup).toContain('data-testid="message-content"');
    expect(markup).toContain('class="prose');
  });
});
