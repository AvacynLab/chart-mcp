import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";

import { PromptInputSubmit } from "@/components/elements/prompt-input";

describe("PromptInput accessibility affordances", () => {
  it("exposes a descriptive label for the send control", () => {
    const html = renderToStaticMarkup(
      <PromptInputSubmit status="ready" data-testid="send-button" />
    );

    expect(html).toContain('aria-label="Send message"');
    expect(html).toContain(
      '<span class="sr-only">Send message</span>'
    );
  });
});
