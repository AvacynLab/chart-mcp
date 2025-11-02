import { describe, expect, it } from "vitest";

import { authConfig } from "@/app/(auth)/auth.config";

/**
 * Regression coverage ensuring that Auth.js explicitly trusts the host header
 * forwarded by Playwright.  Without `trustHost=true` the guest bootstrap would
 * fail with HTTP 400 responses and the chat UI would never render during the
 * end-to-end suite.
 */
describe("authConfig host trust", () => {
  it("enables trustHost to unblock Playwright guest sign-ins", () => {
    expect(authConfig.trustHost).toBe(true);
  });
});
