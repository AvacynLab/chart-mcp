import { describe, expect, it, afterEach } from "vitest";
import ChatPage from "./page";
import Chat from "@components/chat";
import { getFinanceDemoMessages } from "@lib/demo/finance";
import { registerSessionResolver, resetSessionResolver } from "@lib/session";
import { RedirectError } from "@lib/navigation";

const regularSession = { user: { type: "regular" } };

describe("ChatPage", () => {
  afterEach(() => {
    resetSessionResolver();
  });

  it("redirects guests to the login page", async () => {
    await expect(ChatPage()).rejects.toMatchObject({
      destination: "/login",
    });
  });

  it("redirects non-regular users to the login page", async () => {
    registerSessionResolver(() => ({ user: { type: "guest" } }));
    await expect(ChatPage()).rejects.toBeInstanceOf(RedirectError);
  });

  it("renders the chat component seeded with the finance demo message", async () => {
    registerSessionResolver(() => regularSession);

    const element = await ChatPage();

    expect(element.type).toBe(Chat);
    expect(element.props.initialMessages).toEqual(getFinanceDemoMessages());
  });
});
