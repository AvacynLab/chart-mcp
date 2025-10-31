import { generateDummyPassword } from "./db/utils";

export const isProductionEnvironment = process.env.NODE_ENV === "production";
export const isDevelopmentEnvironment = process.env.NODE_ENV === "development";
export const isTestEnvironment = Boolean(
  process.env.PLAYWRIGHT_TEST_BASE_URL ||
    process.env.PLAYWRIGHT ||
    process.env.CI_PLAYWRIGHT
);

/**
 * Match the ephemeral guest identifiers generated during Playwright runs.
 * They follow the shape `guest-<timestamp>-<uuid>`, however older fixtures
 * (and some unit tests) still rely on the shorter `guest-<timestamp>` form.
 * Allowing both keeps the regex resilient while ensuring the UI continues to
 * treat these synthetic accounts as guests.
 */
export const guestRegex = /^guest-\d+(?:-[a-z0-9-]+)?$/i;

export const DUMMY_PASSWORD = generateDummyPassword();
