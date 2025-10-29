/** @type {import('postcss-load-config').Config} */
const config = {
  plugins: {
    "@tailwindcss/postcss": {},
  },
};

const isTestEnv = process.env.VITEST || process.env.NODE_ENV === "test";

export default isTestEnv ? { plugins: {} } : config;
