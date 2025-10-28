import Chat from "@components/chat";
import { getFinanceDemoMessages } from "@lib/demo/finance";
import { redirect } from "@lib/navigation";
import { getServerSession } from "@lib/session";

/**
 * Server component responsible for rendering the chat experience.
 *
 * The page intentionally checks the authenticated session on every request in
 * order to enforce the "regular" account requirement defined by the product
 * brief. Using the shared :func:`redirect` helper keeps the control flow close
 * to what Next.js performs internally when calling `redirect()`.
 */
export default async function ChatPage(): Promise<JSX.Element> {
  const session = await getServerSession();

  if (!session || session.user?.type !== "regular") {
    redirect("/login");
  }

  const initialMessages = getFinanceDemoMessages();

  // Surfacing the deterministic finance conversation here ensures that manual
  // and automated flows land on the BTCUSD chart scenario without having to
  // trigger a backend round-trip from the client components.
  return <Chat initialMessages={initialMessages} />;
}
