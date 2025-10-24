import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import ChatError from "./error";

describe("ChatError boundary", () => {
  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("logs the captured error", () => {
    const mockError = new Error("Boom");
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(<ChatError error={mockError} reset={() => undefined} />);

    expect(spy).toHaveBeenCalledWith(mockError);
  });

  it("invokes reset when retry is clicked", async () => {
    const user = userEvent.setup();
    const reset = vi.fn();
    const mockError = Object.assign(new Error("Erreur"), { digest: "abc123" });
    const spy = vi.spyOn(console, "error").mockImplementation(() => undefined);

    render(<ChatError error={mockError} reset={reset} />);

    await user.click(screen.getByRole("button", { name: /réessayer/i }));

    expect(reset).toHaveBeenCalledTimes(1);
    expect(spy).toHaveBeenCalledWith(mockError);
  });
});
