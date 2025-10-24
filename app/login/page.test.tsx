import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, beforeEach, vi } from "vitest";
import LoginPage from "./page";

describe("LoginPage", () => {
  beforeEach(() => {
    vi.resetAllMocks();
    Object.defineProperty(window, "location", {
      value: { assign: vi.fn() },
      writable: true,
    });
  });

  it("shows an error when the form is incomplete", () => {
    render(<LoginPage />);

    fireEvent.click(screen.getByTestId("auth-submit"));

    expect(screen.getByTestId("auth-error")).toHaveTextContent(
      "Identifiants requis pour continuer",
    );
    expect(window.location.assign).not.toHaveBeenCalled();
  });

  it("persists cookies and redirects when credentials are provided", () => {
    render(<LoginPage />);

    const cookieSetter = vi.spyOn(document, "cookie", "set");

    fireEvent.change(screen.getByTestId("auth-email"), {
      target: { value: "ada@example.com" },
    });
    fireEvent.change(screen.getByTestId("auth-password"), {
      target: { value: "secret" },
    });
    fireEvent.submit(screen.getByTestId("auth-submit").closest("form")!);

    expect(cookieSetter).toHaveBeenCalledWith(expect.stringContaining("sessionType=regular"));
    expect(cookieSetter).toHaveBeenCalledWith(
      expect.stringContaining(encodeURIComponent("ada@example.com")),
    );
    expect(window.location.assign).toHaveBeenCalledWith("/chat");
  });
});
