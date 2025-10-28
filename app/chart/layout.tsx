import type { Metadata } from "next";
import type { PropsWithChildren } from "react";

/**
 * Layout dedicated to the `/chart` route so we can tailor the metadata to the
 * streaming analysis workspace without duplicating the global HTML shell.
 */
export const metadata: Metadata = {
  title: "Chart MCP — Analyse graphique",
  description: "Dashboard SSE avec Lightweight Charts et indicateurs techniques.",
};

export default function ChartLayout({ children }: PropsWithChildren): JSX.Element {
  return <>{children}</>;
}
