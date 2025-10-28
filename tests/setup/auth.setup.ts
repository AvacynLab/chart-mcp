import type { FullConfig } from "@playwright/test";
import fs from "node:fs/promises";
import path from "node:path";

const STORAGE_DIR = path.resolve(__dirname, "../.auth");
const STORAGE_STATE = path.join(STORAGE_DIR, "regular.json");

interface CookieState {
  readonly name: string;
  readonly value: string;
  readonly domain: string;
  readonly path: string;
  readonly expires: number;
  readonly httpOnly: boolean;
  readonly secure: boolean;
  readonly sameSite: "Strict" | "Lax" | "None";
}

interface SerializableStorageState {
  readonly cookies: readonly CookieState[];
  readonly origins: ReadonlyArray<{
    readonly origin: string;
    readonly localStorage?: readonly { readonly name: string; readonly value: string }[];
    readonly sessionStorage?: readonly { readonly name: string; readonly value: string }[];
  }>;
}

/**
 * Construct a deterministic storage state that mimics the cookies emitted by
 * the demo login flow. Persisting the JSON directly keeps the global setup
 * independent from a running Next.js server which simplifies local and CI
 * workflows alike.
 */
async function writeStorageState(baseURL: string): Promise<void> {
  await fs.mkdir(STORAGE_DIR, { recursive: true });

  const target = new URL(baseURL);
  const domain = target.hostname || "127.0.0.1";
  const expires = Math.floor(Date.now() / 1000) + 86_400; // 24h validity window.

  const state: SerializableStorageState = {
    cookies: [
      {
        name: "sessionType",
        value: "regular",
        domain,
        path: "/",
        expires,
        httpOnly: false,
        secure: false,
        sameSite: "Lax",
      },
      {
        name: "sessionName",
        value: encodeURIComponent("regular@example.com"),
        domain,
        path: "/",
        expires,
        httpOnly: false,
        secure: false,
        sameSite: "Lax",
      },
    ],
    origins: [],
  };

  await fs.writeFile(STORAGE_STATE, JSON.stringify(state, null, 2), "utf8");
}

export default async function globalSetup(config: FullConfig): Promise<void> {
  const projectBaseURL = config.projects[0]?.use?.baseURL;
  const baseURL = projectBaseURL ?? process.env.PLAYWRIGHT_BASE_URL ?? "http://127.0.0.1:3000";
  await writeStorageState(baseURL);
}

export { STORAGE_STATE };
