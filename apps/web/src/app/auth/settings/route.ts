import { getSupabaseConfig } from "@/lib/supabase/env";

export async function GET() {
  try {
    const { url, publishableKey } = getSupabaseConfig();
    const response = await fetch(`${url}/auth/v1/settings`, {
      headers: { apikey: publishableKey }, cache: "no-store", signal: AbortSignal.timeout(5000),
    });
    if (!response.ok) throw new Error("Auth unavailable");
    const settings = await response.json();
    return Response.json({ google: settings.external?.google === true }, {headers: {"Cache-Control": "no-store"}});
  } catch {
    return Response.json({ google: false, unavailable: true }, { status: 503 });
  }
}
