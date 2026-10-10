"use client";

import { Suspense, useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { AuthFrame } from "@/components/auth-frame";
import { useRouter, useSearchParams } from "next/navigation";
import { createClient } from "@/lib/supabase/client";
import { SupabaseConfigurationError } from "@/lib/supabase/env";

function LoginForm() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [google, setGoogle] = useState<boolean | null>(null);
  const [googleUnavailable, setGoogleUnavailable] = useState(false);
  const [configurationError, setConfigurationError] = useState(false);
  const reason = useSearchParams().get("reason");
  const notice = reason === "session-expired" ? "Your session ended. Sign in again to continue." : reason === "invalid-link" ? "This authentication link is invalid or expired. Please try again or request a new recovery link." : reason === "auth-unavailable" ? "Authentication is temporarily unavailable. Please retry later." : "";
  useEffect(() => {
    void fetch("/auth/settings", {cache: "no-store"}).then((response) => response.json()).then((data) => {
      setGoogle(data.google === true);
      setGoogleUnavailable(data.unavailable === true);
      setConfigurationError(data.configuration_error === true);
    }).catch(() => { setGoogle(false); setGoogleUnavailable(true); });
  }, []);
  async function signInGoogle() {
    if (!google || busy) return;
    setBusy(true); setError(null);
    try {
      const { error } = await createClient().auth.signInWithOAuth({provider: "google", options: {redirectTo: `${window.location.origin}/auth/callback`}});
      if (error) {setError("Google sign-in could not start. Check the provider configuration or use email."); setBusy(false);}
    } catch (error) {setError(error instanceof SupabaseConfigurationError ? error.message : "Google sign-in is unavailable. Please use email or retry later."); setBusy(false);}
  }

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (busy) return;
    setError(null);
    setBusy(true);
    try {
      const supabase = createClient();
      const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
      if (authError) {
        if (authError.status === 0 || (authError.name === "AuthRetryableFetchError" && !authError.status)) {
          setError("Cannot reach the sign-in service. Check that Supabase is running and your connection is available, then try again.");
        } else if (authError.name === "AuthRetryableFetchError" || (authError.status ?? 0) >= 500) {
          setError("The sign-in service is temporarily unavailable. Please try again later.");
        } else if (authError.status === 429) {
          setError("Too many sign-in attempts. Please wait before trying again.");
        } else if (authError.code === "invalid_credentials") {
          setError("Sign-in failed. Check your email and password, then try again.");
        } else if (authError.code === "email_not_confirmed") {
          setError("Confirm your email before signing in. Contact your workspace administrator if you need help.");
        } else {
          setError("Sign-in could not be completed. Please retry or contact your workspace administrator.");
        }
        return;
      }
      router.replace("/");
      router.refresh();
    } catch (error) {
      setError(error instanceof SupabaseConfigurationError ? error.message : "Cannot reach the sign-in service. Check your connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthFrame>
      <section className="login-content" aria-labelledby="login-title">
        <Link className="brand-name login-brand" href="/" aria-label="Clearframe home">Clearframe</Link>
        <h1 id="login-title">Sign in to your workspace</h1>
        <p className="login-intro">Use your organization account to access authorized knowledge.</p>
        {notice && <p className="auth-message" role="status">{notice}</p>}
        <button className="oauth-button" type="button" disabled={!google || busy} onClick={() => void signInGoogle()}>{google === null ? "Checking Google sign-in…" : "Continue with Google"}</button>
        {google === false && <p className="auth-configuration">{configurationError ? "Workspace sign-in is not configured. Contact your workspace administrator." : googleUnavailable ? "Sign-in service is unavailable. Check the Supabase service and connection, then reload this page." : "Google sign-in is not configured for this workspace. Use email and password."}</p>}
        <div className="auth-divider">or use email</div>
        <form className="login-form" onSubmit={signIn}>
          <label htmlFor="email">Email</label>
          <input
            autoComplete="username"
            id="email"
            name="email"
            type="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />
          <label htmlFor="password">Password</label>
          <input
            autoComplete="current-password"
            id="password"
            name="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />
          {error && <p className="login-error" role="alert">{error}</p>}
          <button className="login-submit" type="submit" disabled={busy}>
            {busy ? "Signing in…" : "Sign in"}
          </button>
        </form>
        <Link className="auth-link" href="/forgot-password">Forgot password?</Link>
        <p className="auth-configuration">Access is provisioned by your organization. Signing in never grants a workspace role automatically.</p>
      </section>
    </AuthFrame>
  );
}

export default function LoginPage() {
  return <Suspense fallback={<main className="auth-loading">Loading sign in…</main>}><LoginForm /></Suspense>;
}
