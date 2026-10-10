import { Suspense } from "react";
import { connection } from "next/server";
import { redirect } from "next/navigation";
import Workspace, { type View } from "@/components/workspace";
import { createClient } from "@/lib/supabase/server";

export default function AuthenticatedWorkspace({ view, savedConversation }: { view: View; savedConversation?: string }) {
  return (
    <Suspense fallback={<main className="auth-loading" aria-live="polite">Loading your workspace…</main>}>
      <AuthenticatedContent view={view} savedConversation={savedConversation} />
    </Suspense>
  );
}

async function AuthenticatedContent({ view, savedConversation }: { view: View; savedConversation?: string }) {
  await connection();
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getClaims();
  const claims = data?.claims;
  if (error || typeof claims?.sub !== "string") redirect("/login");

  const email = typeof claims.email === "string" ? claims.email : "Authenticated user";
  return <Workspace identity={email} view={view} savedConversation={savedConversation} />;
}
