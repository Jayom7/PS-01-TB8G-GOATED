export class SupabaseConfigurationError extends Error {
  constructor() {
    super("Workspace sign-in is not configured. Contact your workspace administrator.");
    this.name = "SupabaseConfigurationError";
  }
}

export function getSupabaseConfig() {
  const url = process.env.NEXT_PUBLIC_SUPABASE_URL;
  const publishableKey = process.env.NEXT_PUBLIC_SUPABASE_PUBLISHABLE_KEY;

  if (!url?.trim() || !publishableKey?.trim()) {
    throw new SupabaseConfigurationError();
  }
  try {
    const parsed = new URL(url);
    if (!["http:", "https:"].includes(parsed.protocol) || !parsed.hostname) {
      throw new SupabaseConfigurationError();
    }
  } catch {
    throw new SupabaseConfigurationError();
  }

  return { url, publishableKey };
}
