import { describe, expect, test } from "vitest";

import {
  describeMigrationSkipDecision,
  shouldSkipMigrations,
} from "@/lib/db/helpers/should-skip-migrations";

describe("shouldSkipMigrations", () => {
  test("skips when SKIP_DB_MIGRATIONS is explicitly enabled", () => {
    const decision = shouldSkipMigrations({
      NODE_ENV: "test",
      SKIP_DB_MIGRATIONS: "1",
    });

    expect(decision).toEqual({
      skip: true,
      reason: "Skipping migrations because SKIP_DB_MIGRATIONS=1 was provided.",
    });
    expect(describeMigrationSkipDecision(decision)).toContain(
      "SKIP_DB_MIGRATIONS=1",
    );
  });

  test("skips for the mocked Playwright environment", () => {
    const decision = shouldSkipMigrations({
      NODE_ENV: "test",
      PLAYWRIGHT: "1",
      PLAYWRIGHT_USE_REAL_SERVICES: "0",
    });

    expect(decision).toEqual({
      skip: true,
      reason:
        "Skipping migrations for Playwright mock environment (POSTGRES_URL is optional).",
    });
    expect(describeMigrationSkipDecision(decision)).toContain(
      "Playwright mock environment",
    );
  });

  test("skips when no Postgres URL is configured", () => {
    const decision = shouldSkipMigrations({ NODE_ENV: "test" });

    expect(decision).toEqual({
      skip: true,
      reason:
        "Skipping migrations because POSTGRES_URL is not configured for this build.",
    });
    expect(describeMigrationSkipDecision(decision)).toContain(
      "POSTGRES_URL is not configured",
    );
  });

  test("requires migrations when Postgres URL is provided", () => {
    const decision = shouldSkipMigrations({
      NODE_ENV: "test",
      POSTGRES_URL: "postgres://example.com/db",
    });

    expect(decision).toEqual({ skip: false });
    expect(describeMigrationSkipDecision(decision)).toBe(
      "Running migrations because a Postgres URL is available.",
    );
  });
});
