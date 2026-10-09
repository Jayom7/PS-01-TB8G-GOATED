/** A single refresh attempt; network failures never masquerade as sign-out. */
type Session = { access_token: string; expires_at?: number };
type AuthResult = { data: { session: Session | null }; error: { status?: number; message: string } | null };
type Auth = { getSession: () => Promise<AuthResult>; refreshSession: () => Promise<AuthResult> };
export async function sessionToken(auth: Auth, expired: () => void, refresh = false): Promise<string> {
  let result = await (refresh ? auth.refreshSession() : auth.getSession());
  if (!refresh && result.data.session?.expires_at && result.data.session.expires_at * 1000 <= Date.now() + 30_000) {
    result = await auth.refreshSession();
  }
  if (result.error && (!result.error.status || result.error.status >= 500)) {
    throw new Error("Authentication is temporarily unavailable. Please retry when the connection recovers.");
  }
  if (result.error || !result.data.session) {
    expired();
    throw new Error("Your session expired. Sign in again to continue.");
  }
  return result.data.session.access_token;
}
