/**
 * Lightweight navigation helpers mirroring Next.js redirect semantics.
 *
 * The helpers raise a dedicated error so server components or tests can
 * intercept the control flow without relying on framework internals.
 */
export class RedirectError extends Error {
  /** Target URL that should be reached after the redirect. */
  public readonly destination: string;

  constructor(destination: string) {
    super(`Redirect requested to ${destination}`);
    this.destination = destination;
    this.name = "RedirectError";
  }
}

/**
 * Trigger a redirect to the provided destination.
 *
 * The function never returns: it raises a :class:`RedirectError` so callers
 * must either terminate rendering or deliberately catch the error.
 */
export function redirect(destination: string): never {
  throw new RedirectError(destination);
}

/**
 * Type guard that identifies redirect errors emitted by :func:`redirect`.
 */
export function isRedirectError(error: unknown): error is RedirectError {
  return error instanceof RedirectError;
}
