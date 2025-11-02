import { createPool } from '@vercel/postgres';

const isPlaywrightRuntime =
  process.env.PLAYWRIGHT === '1' ||
  Boolean(
    process.env.PLAYWRIGHT_TEST_BASE_URL || process.env.CI_PLAYWRIGHT,
  );

/**
 * Mirror the drizzle in-memory fallback that powers `lib/db/queries`.  We
 * intentionally short-circuit whenever Postgres credentials are absent so
 * Auth.js guest sign-ins continue to succeed during local Playwright runs
 * without requiring a database server.
 */
const shouldMockDatabase =
  process.env.PLAYWRIGHT_USE_REAL_SERVICES !== '1' &&
  (!process.env.POSTGRES_URL || isPlaywrightRuntime);

export const pool = shouldMockDatabase
  ? {
      connect: () => Promise.resolve(),
      query: () => Promise.resolve({ rows: [] }),
      end: () => Promise.resolve(),
    }
  : createPool({
      connectionString: process.env.POSTGRES_URL,
    });
