import { Suspense } from "react";
import { connection } from "next/server";
import Workspace from "@/components/workspace";
import { createClient } from "@/lib/supabase/server";
import { redirect } from "next/navigation";

export default function Home() {
  return (
    <Suspense fallback={<main className="auth-loading" aria-live="polite">Loading your workspace…</main>}>
      <AuthenticatedWorkspace />
    </Suspense>
  );
}

async function AuthenticatedWorkspace() {
  // Keep cookie-bound Supabase auth and GoTrue's Date.now() work out of the
  // prerendered shell; this subtree depends on the incoming request session.
  await connection();
  const supabase = await createClient();
  const { data, error } = await supabase.auth.getClaims();
  const claims = data?.claims;
  const subject = claims?.sub;
  if (error || typeof subject !== "string") redirect("/login");

  const email = typeof claims?.email === "string" ? claims.email : "Authenticated user";
  return <Workspace identity={email} />;
}
