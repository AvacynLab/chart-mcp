import type { Metadata } from "next";
import type { PropsWithChildren } from "react";

/**
 * Lightweight layout for the login demo so Playwright-driven authentication can
 * reuse the root layout while surfacing dedicated metadata.
 */
export const metadata: Metadata = {
  title: "Chart MCP — Connexion",
  description: "Portail de connexion de démonstration pour les tests Playwright.",
};

export default function LoginLayout({ children }: PropsWithChildren): JSX.Element {
  return <>{children}</>;
}
