import type { NextAuthConfig } from "next-auth";

export const authConfig = {
  pages: {
    signIn: "/login",
    newUser: "/",
  },
  /**
   * Allow Auth.js (NextAuth) to accept the host header injected by Playwright
   * and other local smoke-test harnesses.  Without this flag the guest
   * bootstrap route responds with HTTP 400 ("Host must be trusted"), which
   * prevents the E2E suite from rendering the chat interface.
   */
  trustHost: true,
  providers: [
    // added later in auth.ts since it requires bcrypt which is only compatible with Node.js
    // while this file is also used in non-Node.js environments
  ],
  callbacks: {},
} satisfies NextAuthConfig;
