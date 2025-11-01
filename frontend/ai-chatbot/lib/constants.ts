import { generateDummyPassword } from "./db/utils";

/**
 * Allow CI to opt into exercising the "real" infrastructure (database,
 * providers, streaming backends, …) while still defaulting to the hermetic
 * mocks that keep local runs lightweight.  When `PLAYWRIGHT_USE_REAL_SERVICES`
 * is exported we treat the runtime as a fully fledged environment even if the
 * Playwright markers are present.
 */
const playWrightWantsRealServices =
  process.env.PLAYWRIGHT_USE_REAL_SERVICES === "1";

export const isProductionEnvironment = process.env.NODE_ENV === "production";
export const isDevelopmentEnvironment = process.env.NODE_ENV === "development";
export const isTestEnvironment = playWrightWantsRealServices
  ? false
  : Boolean(
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
