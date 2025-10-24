import { build } from "esbuild";
import path from "node:path";

import type { Page } from "@playwright/test";

let cachedBundle: string | null = null;

async function loadBundle(): Promise<string> {
  if (cachedBundle) {
    return cachedBundle;
  }

  const result = await build({
    entryPoints: [path.resolve(__dirname, "./harness.tsx")],
    bundle: true,
    write: false,
    format: "esm",
    platform: "browser",
    target: "es2020",
    jsx: "automatic",
    sourcemap: false,
    loader: {
      ".ts": "ts",
      ".tsx": "tsx",
    },
    define: {
      "process.env.NODE_ENV": '"test"',
    },
  });

  const [output] = result.outputFiles ?? [];
  if (!output) {
    throw new Error("Failed to compile the Playwright harness bundle");
  }

  cachedBundle = output.text;
  return cachedBundle;
}

/**
 * Mount the finance harness inside the Playwright page by inlining the bundled
 * React script into a `data:` URL. The `<base>` tag ensures all relative fetch
 * requests are issued against the usual Next.js origin (127.0.0.1:3000).
 */
export async function mountFinanceHarness(page: Page): Promise<void> {
  const script = await loadBundle();
  const html = `<!DOCTYPE html>
    <html lang="fr">
      <head>
        <meta charset="utf-8" />
        <base href="http://127.0.0.1:3000/" />
        <title>Finance Harness</title>
      </head>
      <body>
        <div id="root"></div>
        <script type="module">${script}</script>
      </body>
    </html>`;

  await page.goto(`data:text/html,${encodeURIComponent(html)}`);
}

