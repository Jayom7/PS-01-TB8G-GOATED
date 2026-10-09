"use client";
import { useState, type FormEvent } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy) return;
    setBusy(true); setError(""); setMessage("");
    try {
      const { error } = await createClient().auth.resetPasswordForEmail(email, {
        redirectTo: `${window.location.origin}/auth/callback?next=/reset-password`,
      });
      if (error) setError("The reset email could not be requested. Please retry later.");
      else setMessage("If this email belongs to an account, a recovery link is on its way. Open it in this browser; links expire and can only be used once.");
    } catch { setError("Authentication is unavailable. Please try again when the connection recovers."); }
    finally { setBusy(false); }
  }
  return <main className="login-shell"><section className="login-content"><Link className="brand-name login-brand" href="/login">Clearframe</Link><h1>Reset your password</h1><p className="login-intro">We’ll send a recovery link to your organization email.</p><form className="login-form" onSubmit={submit}><label htmlFor="email">Email</label><input id="email" type="email" autoComplete="email" required value={email} onChange={(event) => setEmail(event.target.value)} />{message && <p className="auth-message" role="status">{message}</p>}{error && <p className="login-error" role="alert">{error}</p>}<button className="login-submit" disabled={busy}>{busy ? "Sending…" : "Send recovery link"}</button></form><Link className="auth-link" href="/login">Back to sign in</Link></section></main>;
}
