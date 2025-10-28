import { afterEach, describe, expect, it, vi } from "vitest";

import ChartPage from "./page";
import ChartAnalysis from "@components/chart/chart-analysis";
import { RedirectError } from "@lib/navigation";
import { registerSessionResolver, resetSessionResolver } from "@lib/session";

vi.mock("@components/chart/chart-analysis", () => ({
  __esModule: true,
  default: vi.fn(() => <div data-testid="chart-analysis-mock" />),
}));

describe("ChartPage", () => {
  afterEach(() => {
    resetSessionResolver();
    vi.resetAllMocks();
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.NEXT_PUBLIC_API_TOKEN;
    delete process.env.API_BASE_URL;
    delete process.env.API_TOKEN;
  });

  it("redirects guests to the login flow", async () => {
    await expect(ChartPage()).rejects.toBeInstanceOf(RedirectError);
  });

  it("renders the chart analysis component for regular sessions", async () => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://localhost:8000";
    process.env.NEXT_PUBLIC_API_TOKEN = "test-token";
    registerSessionResolver(() => ({ user: { type: "regular" } }));

    const element = await ChartPage();

    expect(element.type).toBe(ChartAnalysis);
    expect(element.props).toMatchObject({
      apiBaseUrl: "http://localhost:8000",
      apiToken: "test-token",
      defaultSymbol: "BTC/USDT",
      defaultTimeframe: "1h",
    });
  });

  it("falls back to backend-only environment variables when public ones are missing", async () => {
    process.env.API_BASE_URL = "http://internal:8000";
    process.env.API_TOKEN = "internal";
    registerSessionResolver(() => ({ user: { type: "regular" } }));

    const element = await ChartPage();

    expect(element.type).toBe(ChartAnalysis);
    expect(element.props).toMatchObject({ apiBaseUrl: "http://internal:8000", apiToken: "internal" });
  });
});
