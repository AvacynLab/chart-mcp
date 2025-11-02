import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { Action, Actions } from "@/components/elements/actions";

/**
 * Regression coverage for the message actions so `data-testid` hooks and other
 * DOM attributes reach the interactive button rendered in the UI.
 */
describe("Message actions propagation", () => {
  it("forwards DOM props to the button element", () => {
    const markup = renderToStaticMarkup(
      <Action data-testid="message-upvote" label="Upvote">
        👍
      </Action>
    );

    expect(markup).toContain('data-testid="message-upvote"');
    expect(markup).toContain('type="button"');
  });

  it("spreads attributes on the Actions container", () => {
    const markup = renderToStaticMarkup(
      <Actions data-testid="assistant-actions">
        <span />
      </Actions>
    );

    expect(markup).toContain('data-testid="assistant-actions"');
    expect(markup).toContain('class="flex items-center gap-1"');
  });
});
