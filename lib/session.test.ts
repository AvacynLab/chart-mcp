import { afterEach, describe, expect, it, vi } from "vitest";

/**
 * Helper to import a fresh copy of the session module so each test can control
 * the resolver state and any mocked dependencies (e.g. `next/headers`).
 */
async function loadSessionModule() {
  const sessionModule = await import("./session");
  return sessionModule;
}

describe("session helpers", () => {
  afterEach(() => {
    vi.resetAllMocks();
    vi.resetModules();
  });

  it("returns null by default", async () => {
    const session = await loadSessionModule();
    session.resetSessionResolver();
    await expect(session.getServerSession()).resolves.toBeNull();
  });

  it("uses the registered resolver when provided", async () => {
    const session = await loadSessionModule();
    const customSession = { user: { type: "regular", name: "Ada" } };
    session.registerSessionResolver(() => customSession);

    await expect(session.getServerSession()).resolves.toEqual(customSession);
  });

  it("derives a regular session from cookies when present", async () => {
    vi.doMock("next/headers", () => ({
      cookies: () => ({
        get: (name: string) => {
          if (name === "sessionType") {
            return { value: "regular" };
          }
          if (name === "sessionName") {
            return { value: encodeURIComponent("Ada Lovelace") };
          }
          return undefined;
        },
      }),
    }));

    const session = await loadSessionModule();
    await expect(session.getServerSession()).resolves.toEqual({
      user: { type: "regular", name: "Ada Lovelace" },
    });
  });

  it("ignores cookies when the regular marker is absent", async () => {
    vi.doMock("next/headers", () => ({
      cookies: () => ({
        get: (name: string) => {
          if (name === "sessionName") {
            return { value: "Guest" };
          }
          return undefined;
        },
      }),
    }));

    const session = await loadSessionModule();
    await expect(session.getServerSession()).resolves.toBeNull();
  });
});
