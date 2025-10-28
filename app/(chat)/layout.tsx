import type { Metadata } from "next";
import type { PropsWithChildren } from "react";

/**
 * Layout for the chat segment so metadata reflects the conversational surface
 * without re-rendering the root `<html>` scaffold provided upstream.
 */
export const metadata: Metadata = {
  title: "Chart MCP — Chat",
  description: "Expérience de chat pour agents et utilisateurs réguliers.",
};

export default function ChatLayout({ children }: PropsWithChildren): JSX.Element {
  return <>{children}</>;
}
