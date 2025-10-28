import ChartAnalysis from "@components/chart/chart-analysis";
import { redirect } from "@lib/navigation";
import { getServerSession } from "@lib/session";

/**
 * Server component responsible for gating access to the chart analysis surface.
 *
 * The route mirrors the behaviour of the chat experience by requiring a
 * ``regular`` session before exposing the SSE-driven UI. Environment variables
 * allow operators to point the frontend to a remote API when necessary while
 * still supporting the default localhost workflow.
 */
export default async function ChartPage(): Promise<JSX.Element> {
  const session = await getServerSession();
  if (!session || session.user?.type !== "regular") {
    redirect("/login");
  }

  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? process.env.API_BASE_URL ?? "";
  const apiToken = process.env.NEXT_PUBLIC_API_TOKEN ?? process.env.API_TOKEN ?? "";

  return (
    <ChartAnalysis
      apiBaseUrl={apiBaseUrl}
      apiToken={apiToken}
      defaultSymbol="BTC/USDT"
      defaultTimeframe="1h"
    />
  );
}
