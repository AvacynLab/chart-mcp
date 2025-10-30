import type { Metadata } from "next";
import { FinanceHarness } from "./finance-harness-client";

/**
 * Dedicated entry point used exclusively by Playwright to exercise the finance
 * streaming lifecycle against a deterministic fixture. Keeping the harness in
 * the `/playwright` segment avoids polluting the main chat surface while still
 * exposing a fully fledged page for end-to-end assertions.
 */
export const metadata: Metadata = {
  title: "Finance Stream Harness",
};

export default function FinanceHarnessPage(): JSX.Element {
  return <FinanceHarness />;
}

