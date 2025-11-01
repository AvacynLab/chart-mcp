import { createPool } from '@vercel/postgres';

const shouldMockDatabase =
  process.env.PLAYWRIGHT === '1' &&
  process.env.PLAYWRIGHT_USE_REAL_SERVICES !== '1' &&
  !process.env.POSTGRES_URL;

export const pool = shouldMockDatabase
  ? {
      connect: () => Promise.resolve(),
      query: () => Promise.resolve({ rows: [] }),
      end: () => Promise.resolve(),
    }
  : createPool({
      connectionString: process.env.POSTGRES_URL,
    });