import { describe, expect, it } from "vitest";
import { isRedirectError, redirect } from "./navigation";

describe("navigation helpers", () => {
  it("throws a redirect error with the destination", () => {
    try {
      redirect("/login");
      throw new Error("Redirect did not throw");
    } catch (error) {
      expect(isRedirectError(error)).toBe(true);
      if (isRedirectError(error)) {
        expect(error.destination).toBe("/login");
      }
    }
  });
});
