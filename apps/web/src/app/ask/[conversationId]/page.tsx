import { notFound } from "next/navigation";
import { Suspense } from "react";
import AuthenticatedWorkspace from "@/components/authenticated-workspace";

export const metadata = {title: "Saved conversation · Clearframe"};

export default function ConversationPage({ params }: {params: Promise<{conversationId: string}>}) {
  return <Suspense fallback={<main className="auth-loading" role="status">Loading your conversation…</main>}>
    <SavedConversation params={params} />
  </Suspense>;
}

async function SavedConversation({ params }: {params: Promise<{conversationId: string}>}) {
  const {conversationId} = await params;
  if (!/^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i.test(conversationId)) notFound();
  return <AuthenticatedWorkspace view="Ask" savedConversation={conversationId} />;
}
