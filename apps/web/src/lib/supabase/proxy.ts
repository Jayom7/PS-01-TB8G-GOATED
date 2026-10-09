import { createServerClient } from "@supabase/ssr";
import { NextResponse, type NextRequest } from "next/server";
import { getSupabaseConfig } from "./env";

export async function updateSession(request: NextRequest) {
  // API requests carry a bearer token; FastAPI validates identity and RLS.
  if (request.nextUrl.pathname.startsWith("/api/v1/")) return NextResponse.next({ request });
  // Public sign-in renders immediately even when Auth cannot be reached.
  // Protected pages still require verified claims.
  if (["/login", "/forgot-password", "/reset-password"].includes(request.nextUrl.pathname) || request.nextUrl.pathname.startsWith("/auth/")) return NextResponse.next({ request });
  const { url, publishableKey } = getSupabaseConfig();
  let response = NextResponse.next({ request });

  const supabase = createServerClient(url, publishableKey, {
    cookies: {
      getAll() {
        return request.cookies.getAll();
      },
      setAll(cookiesToSet, headers) {
        cookiesToSet.forEach(({ name, value }) =>
          request.cookies.set(name, value),
        );

        response = NextResponse.next({ request });
        cookiesToSet.forEach(({ name, value, options }) =>
          response.cookies.set(name, value, options),
        );
        Object.entries(headers).forEach(([name, value]) =>
          response.headers.set(name, value),
        );
      },
    },
  });

  // Validates the session and refreshes it when its access token is near expiry.
  try {
    await supabase.auth.getClaims();
  } catch {
    // Keep public assets and the sign-in route available during an Auth outage.
    // Protected pages validate claims again in their server component.
  }

  return response;
}
