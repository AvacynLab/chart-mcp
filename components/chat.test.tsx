import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";
import Chat, { ChatProvider } from "./chat";
import type { ChatMessage } from "./messages";

describe("Chat component", () => {
  it("sends messages via the provided callback when no context is available", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn().mockResolvedValue(undefined);

    render(<Chat onSend={onSend} />);

    await act(async () => {
      await user.type(screen.getByRole("textbox"), "Bonjour");
      await user.click(screen.getByRole("button", { name: /envoyer/i }));
    });
    await screen.findByText("Bonjour");

    expect(onSend).toHaveBeenCalledWith("Bonjour");
    expect(screen.getByTestId("chat-messages").textContent).toContain("Bonjour");
  });

  it("does not send empty messages", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn().mockResolvedValue(undefined);

    render(<Chat onSend={onSend} />);

    await act(async () => {
      await user.click(screen.getByRole("button", { name: /envoyer/i }));
    });

    expect(onSend).not.toHaveBeenCalled();
  });

  it("uses the context store when available", async () => {
    const user = userEvent.setup();
    const sendMessage = vi.fn().mockResolvedValue(undefined);

    render(
      <ChatProvider value={{ sendMessage }}>
        <Chat />
      </ChatProvider>,
    );

    await act(async () => {
      await user.type(screen.getByRole("textbox"), "Salut");
      await user.click(screen.getByRole("button", { name: /envoyer/i }));
    });
    await screen.findByText("Salut");

    expect(sendMessage).toHaveBeenCalledWith("Salut");
  });

  it("auto-scrolls when new messages arrive", async () => {
    const user = userEvent.setup();
    const onSend = vi.fn();

    render(<Chat onSend={onSend} initialMessages={[]} />);

    const container = screen.getByTestId("chat-messages");
    let internalScrollTop = 0;

    Object.defineProperties(container, {
      scrollHeight: { value: 200, configurable: true },
      scrollTop: {
        get: () => internalScrollTop,
        set: (value) => {
          internalScrollTop = value as number;
        },
        configurable: true,
      },
    });

    await act(async () => {
      await user.type(screen.getByRole("textbox"), "Nouveau message");
      await user.click(screen.getByRole("button", { name: /envoyer/i }));
    });
    await screen.findByText("Nouveau message");

    expect(internalScrollTop).toBe(200);
  });

  it("disables input while streaming", () => {
    render(
      <ChatProvider value={{ isStreaming: true }}>
        <Chat />
      </ChatProvider>,
    );

    expect(screen.getByRole("textbox")).toBeDisabled();
    expect(screen.getByRole("button", { name: /envoyer/i })).toBeDisabled();
  });

  it("renders initial messages", () => {
    const initial: ChatMessage[] = [
      { id: "1", role: "assistant", content: "Bonjour" },
      { id: "2", role: "user", content: "Salut" },
    ];

    render(<Chat initialMessages={initial} />);

    const articles = within(screen.getByTestId("chat-messages")).getAllByRole("article");
    expect(articles).toHaveLength(2);
  });
});
