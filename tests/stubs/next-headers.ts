/**
 * Minimal stub for `next/headers` so Vitest can resolve the module when
 * executing React unit tests outside of a real Next.js environment.
 */
export function cookies() {
  return {
    get() {
      return undefined;
    },
  };
}
