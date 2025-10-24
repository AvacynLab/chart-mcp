"use client";

import {
  createContext,
  FormEvent,
  ReactNode,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import Messages, { ChatArtifactBase, ChatMessage } from "./messages";

/**
 * Shape of the context shared with child components that need to interact with
 * the chat store (e.g. to enqueue streaming deltas).
 */
export interface ChatStoreValue {
  /** Send a message to the backend. */
  readonly sendMessage?: (content: string) => Promise<void> | void;
  /** Whether the assistant is currently streaming a response. */
  readonly isStreaming?: boolean;
}

const ChatContext = createContext<ChatStoreValue | null>(null);

export interface ChatProviderProps {
  readonly value?: ChatStoreValue | null;
  readonly children: ReactNode;
}

/**
 * Context provider exposed for tests and future UI wiring.
 */
export function ChatProvider({ value, children }: ChatProviderProps): JSX.Element {
  return <ChatContext.Provider value={value ?? null}>{children}</ChatContext.Provider>;
}

export interface ChatProps {
  /** Initial history displayed before the user sends new prompts. */
  readonly initialMessages?: ChatMessage[] | null;
  /** Artefacts associated with the live assistant response. */
  readonly activeArtifacts?: ChatArtifactBase[] | null;
  /** Placeholder text for the prompt input. */
  readonly placeholder?: string;
  /** Enable automatic scrolling when new messages arrive. */
  readonly autoScroll?: boolean;
  /** Local fallback used when the context does not expose `sendMessage`. */
  readonly onSend?: (content: string) => Promise<void> | void;
}

/**
 * Chat widget implementing the streaming safety guards requested in the brief.
 */
export default function Chat({
  initialMessages,
  activeArtifacts,
  placeholder = "Écrire un message…",
  autoScroll = true,
  onSend,
}: ChatProps = {}): JSX.Element {
  const listRef = useRef<HTMLDivElement | null>(null);
  const isMountedRef = useRef(false);
  const [messages, setMessages] = useState<ChatMessage[]>(() => initialMessages ?? []);
  const [inputValue, setInputValue] = useState<string>("");

  const store = useContext(ChatContext);
  const effectiveSend = store?.sendMessage ?? onSend;
  const isStreaming = store?.isStreaming ?? false;

  useEffect(() => {
    isMountedRef.current = true;
    return () => {
      isMountedRef.current = false;
    };
  }, []);

  useEffect(() => {
    if (!autoScroll || !isMountedRef.current) {
      return;
    }

    const node = listRef.current;
    if (!node) {
      return;
    }
    node.scrollTop = node.scrollHeight;
  }, [messages, autoScroll]);

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    const trimmed = inputValue.trim();
    if (!trimmed) {
      return;
    }

    const nextMessage: ChatMessage = {
      id: `local-${Date.now()}`,
      role: "user",
      content: trimmed,
    };
    setMessages((current) => [...current, nextMessage]);
    setInputValue("");

    if (!effectiveSend) {
      return;
    }

    try {
      await effectiveSend(trimmed);
    } catch (error) {
      console.error("Impossible d'envoyer le message", error);
    }
  };

  const disableInput = isStreaming;
  const placeholderText = useMemo(() => {
    if (disableInput) {
      return "Réponse en cours…";
    }
    return placeholder;
  }, [disableInput, placeholder]);

  return (
    <div className="chat" data-testid="chat-root">
      <div ref={listRef} className="chat__messages" data-testid="chat-messages">
        <Messages messages={messages} artifacts={activeArtifacts} />
      </div>
      <form className="chat__form" onSubmit={handleSubmit}>
        <label htmlFor="chat-input" className="sr-only">
          Votre message
        </label>
        <input
          id="chat-input"
          value={inputValue}
          onChange={(event) => setInputValue(event.target.value)}
          placeholder={placeholderText}
          disabled={disableInput}
          autoComplete="off"
        />
        <button type="submit" disabled={disableInput}>
          Envoyer
        </button>
      </form>
    </div>
  );
}
