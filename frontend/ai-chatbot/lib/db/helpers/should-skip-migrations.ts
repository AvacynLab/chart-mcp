/**
 * Structured outcome describing whether the migrations should be bypassed for
 * the current environment along with a short human-readable explanation. The
 * explanation doubles as a log message so contributors immediately understand
 * which branch ran when the build script finishes.
 */
export type MigrationSkipDecision =
  | { skip: false }
  | { skip: true; reason: string };

type ProcessEnv = NodeJS.ProcessEnv;

/**
 * Determine whether the build should skip running Drizzle migrations. The
 * command is normally executed before a `next build`, however a large portion
 * of our continuous integration and local developer workflows run against the
 * hermetic in-memory database that powers the Playwright test harness. In that
 * scenario we explicitly avoid talking to Postgres because CI runners do not
 * expose the service and local contributors should not need to provision one
 * just to build the UI for smoke tests.
 */
export function shouldSkipMigrations(env: ProcessEnv): MigrationSkipDecision {
  if (env.SKIP_DB_MIGRATIONS === "1") {
    return {
      skip: true,
      reason: "Skipping migrations because SKIP_DB_MIGRATIONS=1 was provided.",
    };
  }

  const playwrightWantsMockServices =
    env.PLAYWRIGHT === "1" && env.PLAYWRIGHT_USE_REAL_SERVICES !== "1";

  if (playwrightWantsMockServices) {
    return {
      skip: true,
      reason:
        "Skipping migrations for Playwright mock environment (POSTGRES_URL is optional).",
    };
  }

  if (!env.POSTGRES_URL) {
    return {
      skip: true,
      reason:
        "Skipping migrations because POSTGRES_URL is not configured for this build.",
    };
  }

  return { skip: false };
}

/**
 * Convert the structured migration decision to a friendly message. Keeping the
 * formatter in a dedicated helper makes the unit tests easier to assert on and
 * centralises the wording for when we want to tweak the phrasing in the future.
 */
export function describeMigrationSkipDecision(
  decision: MigrationSkipDecision,
): string {
  if (!decision.skip) {
    return "Running migrations because a Postgres URL is available.";
  }

  return decision.reason;
}
