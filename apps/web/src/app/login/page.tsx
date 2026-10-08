"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { createClient } from "@/lib/supabase/client";

export default function LoginPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  async function signIn(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError(null);
    setBusy(true);
    try {
      const supabase = createClient();
      const { error: authError } = await supabase.auth.signInWithPassword({ email, password });
      if (authError) {
        setError("Sign-in failed. Check your email and password, then try again.");
        return;
      }
      router.replace("/");
      router.refresh();
    } catch {
      setError("Authentication is unavailable. Check the Supabase connection and try again.");
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-shell">
      <section className="login-content" aria-labelledby="login-title">
        <Link className="brand-name login-brand" href="/" aria-label="Clearframe home">Clearframe</Link>
        <h1 id="login-title">Sign in to your workspace</h1>
        <p className="login-intro">Use your organization account to access authorized knowledge.</p>
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
      </section>
    </main>
  );
}
