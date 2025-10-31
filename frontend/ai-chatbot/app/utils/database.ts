import { createPool } from '@vercel/postgres';

export const pool = process.env.PLAYWRIGHT === '1'
  ? {
      connect: () => Promise.resolve(),
      query: () => Promise.resolve({ rows: [] }),
      end: () => Promise.resolve(),
    }
  : createPool({
      connectionString: process.env.POSTGRES_URL,
    });