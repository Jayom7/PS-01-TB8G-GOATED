import { NextResponse } from "next/server";
import { createClient } from "@/lib/supabase/server";
import { authDestination } from "@/lib/auth-redirect";

export async function GET(request: Request) {
  const url = new URL(request.url);
  const code = url.searchParams.get("code");
  const next = authDestination(url.searchParams.get("next"));
  if (code) {
    try {
      const supabase = await createClient();
      const { error } = await supabase.auth.exchangeCodeForSession(code);
      if (!error) return NextResponse.redirect(new URL(next, url.origin));
    } catch {
      return NextResponse.redirect(new URL("/login?reason=auth-unavailable", url.origin));
    }
  }
  return NextResponse.redirect(new URL("/login?reason=invalid-link", url.origin));
}
