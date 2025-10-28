import type { Metadata } from "next";
import type { PropsWithChildren } from "react";

/**
 * Root layout wrapping every Next.js route with a consistent `<html>` scaffold
 * and metadata matching the crypto analysis dashboard.
 */
export const metadata: Metadata = {
  title: "Chart MCP",
  description: "Interface d'analyse chartiste pilotée par SSE et outils MCP",
};

export default function RootLayout({ children }: PropsWithChildren): JSX.Element {
  return (
    <html lang="fr">
      <body>{children}</body>
    </html>
  );
}
