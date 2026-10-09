"use client";
import { useEffect, useState, type FormEvent } from "react";
import Link from "next/link";
import { createClient } from "@/lib/supabase/client";

export default function ResetPasswordPage() {
  const [state, setState] = useState<"loading" | "ready" | "invalid" | "unavailable" | "saved">("loading");
  const [password, setPassword] = useState("");
  const [confirmation, setConfirmation] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  useEffect(() => {
    let current = true;
    void createClient().auth.getUser().then(({data, error}) => {
      if (current) setState(error && (!error.status || error.status >= 500) ? "unavailable" : data.user ? "ready" : "invalid");
    }).catch(() => {if (current) setState("unavailable");});
    return () => {current = false;};
  }, []);
  async function submit(event: FormEvent) {
    event.preventDefault(); if (busy || state !== "ready") return;
    if (password !== confirmation) {setError("The passwords do not match.");return;}
    setBusy(true); setError("");
    try {
      const { error } = await createClient().auth.updateUser({password});
      if (error) setError(error.status === 401 ? "This recovery session expired. Request a new link." : "The password could not be updated. Check the requirements and retry.");
      else { await createClient().auth.signOut(); setPassword(""); setConfirmation(""); setState("saved"); }
    } catch {setError("Authentication is unavailable. Please retry later.");}
    finally {setBusy(false);}
  }
  return <main className="login-shell"><section className="login-content"><Link className="brand-name login-brand" href="/login">Clearframe</Link><h1>Choose a new password</h1>{state === "loading" ? <p className="login-intro" role="status">Checking your recovery session…</p> : state === "invalid" ? <><p className="login-intro" role="alert">This link is invalid or expired.</p><Link className="auth-link" href="/forgot-password">Request a new recovery link</Link></> : state === "unavailable" ? <p className="login-error" role="alert">Authentication is unavailable. Reload when the connection recovers.</p> : state === "saved" ? <><p className="auth-message" role="status">Password updated. Sign in with your new password.</p><Link className="auth-link" href="/login">Sign in</Link></> : <form className="login-form" onSubmit={submit}><p className="login-intro">Use at least 12 characters, with a mix of letters and numbers.</p><label htmlFor="password">New password</label><input id="password" type="password" autoComplete="new-password" required minLength={12} maxLength={128} value={password} onChange={(event) => setPassword(event.target.value)} /><label htmlFor="confirmation">Confirm password</label><input id="confirmation" type="password" autoComplete="new-password" required minLength={12} value={confirmation} onChange={(event) => setConfirmation(event.target.value)} />{error && <p className="login-error" role="alert">{error}</p>}<button className="login-submit" disabled={busy}>{busy ? "Updating…" : "Update password"}</button></form>}</section></main>;
}
