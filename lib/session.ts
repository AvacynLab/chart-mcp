/**
 * Minimal session registry used by the demo Next.js pages.
 *
 * The real application would integrate with `next-auth` or a proprietary
 * authentication layer. For the purposes of unit testing we expose a mutable
 * resolver that can be swapped by tests to emulate any authentication state.
 */
export interface SessionUser {
  /** Optional user type used to gate access to chat/finance pages. */
  readonly type?: string;
  /** Display name surfaced in the chat UI. */
  readonly name?: string | null;
}

export interface Session {
  /** Authenticated user (if any). */
  readonly user?: SessionUser | null;
}

/**
 * Function used to resolve the current session. Tests can provide their own
 * implementation to simulate login/logout scenarios.
 */
type SessionResolver = () => Promise<Session | null> | Session | null;

let resolver: SessionResolver | null = null;

/**
 * Replace the global session resolver with a custom implementation.
 */
export function registerSessionResolver(nextResolver: SessionResolver): void {
  resolver = nextResolver;
}

/**
 * Restore the resolver to its default (anonymous) behaviour.
 */
export function resetSessionResolver(): void {
  resolver = null;
}

/**
 * Resolve the active session, falling back to an anonymous user when no
 * custom resolver has been configured.
 */
async function resolveSessionFromCookies(): Promise<Session | null> {
  /**
   * Attempt to hydrate the session from HTTP cookies when running inside a
   * Next.js request context. The helper is intentionally defensive so unit
   * tests (which do not provide `next/headers`) continue to operate without
   * additional mocks.
   */
  try {
    const { cookies } = await import("next/headers");
    const jar = cookies();
    const typeCookie = jar.get("sessionType");
    if (!typeCookie || typeCookie.value !== "regular") {
      return null;
    }

    const nameCookie = jar.get("sessionName");
    const decodedName = nameCookie ? decodeURIComponent(nameCookie.value) : "Invité régulier";

    return {
      user: {
        type: "regular",
        name: decodedName,
      },
    };
  } catch (error) {
    // Accessing cookies outside of a Next.js request (e.g. Vitest) should not
    // raise; simply report an anonymous session in that scenario.
    return null;
  }
}

export async function getServerSession(): Promise<Session | null> {
  if (resolver) {
    return await resolver();
  }

  const cookieSession = await resolveSessionFromCookies();
  if (cookieSession) {
    return cookieSession;
  }

  return null;
}

export type { SessionResolver };
