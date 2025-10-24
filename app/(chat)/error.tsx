"use client";

import { useEffect } from "react";

/**
 * Segment-level error boundary dedicated to the chat experience.
 *
 * The component mirrors Next.js conventions: it logs the error once the
 * boundary is mounted and exposes a retry button wired to the provided
 * `reset()` callback. The JSX layout is deliberately simple and accessible so
 * automated Playwright flows can recover from transient client issues without
 * showing the default Next.js overlay.
 */
export default function ChatError({
  error,
  reset,
}: {
  error: Error & { digest?: string };
  reset: () => void;
}): JSX.Element {
  useEffect(() => {
    console.error(error);
  }, [error]);

  return (
    <div role="alert" className="chat-error">
      <h1>Une erreur est survenue</h1>
      <p>
        Merci de réessayer. Si le problème persiste, veuillez contacter le
        support avec l’identifiant suivant : <code>{error.digest ?? "n/a"}</code>.
      </p>
      <button type="button" onClick={reset}>
        Réessayer
      </button>
    </div>
  );
}
