import "@testing-library/jest-dom/vitest";

// Ensure console.error remains visible during tests except when explicitly mocked.
// Vitest already fails tests on console.error by default, so we rely on that behaviour.
