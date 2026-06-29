/**
 * ManagedSignIn.tsx
 *
 * The "Aloha managed" wizard step — sign in (or up) to the hosted Aloha service.
 * No API key: the box proxies auth to the relay (/api/managed/{login,signup}),
 * stores the returned relay token, and switches the box onto the managed tier.
 * On an active account → straight to chat. On a pending beta signup → waitlist.
 */

import React, { useState } from "react";

interface Props {
  onSuccess: () => void;
  onBack: () => void;
}

export function ManagedSignIn({ onSuccess, onBack }: Props) {
  const [mode, setMode] = useState<"login" | "signup">("signup");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [pending, setPending] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await fetch(`/api/managed/${mode}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: email.trim(), password }),
      });
      const data = await res.json().catch(() => ({}));
      if (!res.ok) {
        throw new Error(
          typeof data.detail === "string" ? data.detail : "Something went wrong. Try again."
        );
      }
      if (data.status === "active") {
        onSuccess();
      } else {
        setPending(true); // beta: account created, awaiting activation
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not reach Aloha.");
    } finally {
      setBusy(false);
    }
  }

  if (pending) {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center px-6">
        <div className="w-full max-w-md text-center space-y-4">
          <div className="text-5xl">🌺</div>
          <h1 className="text-2xl font-bold text-slate-100">You're on the list!</h1>
          <p className="text-slate-400">
            Aloha managed is in private beta. Your account is created — we'll email{" "}
            <span className="text-sky-400">{email}</span> the moment it's activated, and
            you'll be chatting with your home with zero setup.
          </p>
          <button
            onClick={onBack}
            className="text-sm text-slate-500 hover:text-sky-400 underline underline-offset-2"
          >
            ← use a different option
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-6 py-16">
      <div className="w-full max-w-md space-y-7">
        <div className="text-center space-y-2">
          <div className="text-4xl">🌺</div>
          <h1 className="text-2xl font-bold text-slate-100">
            {mode === "signup" ? "Create your Aloha account" : "Welcome back"}
          </h1>
          <p className="text-slate-400 text-sm">
            No API key needed — Aloha runs the AI for you. Just {mode === "signup" ? "sign up" : "sign in"}.
          </p>
        </div>

        <form onSubmit={submit} className="space-y-3">
          <input
            type="email"
            required
            placeholder="you@example.com"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
          <input
            type="password"
            required
            minLength={8}
            placeholder="Password (8+ characters)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            className="w-full bg-slate-800 border border-slate-700 rounded-lg px-3 py-2.5 text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
          {error && <p className="text-sm text-rose-400">{error}</p>}
          <button
            type="submit"
            disabled={busy}
            className="w-full bg-sky-500 hover:bg-sky-400 disabled:opacity-40 text-white font-semibold rounded-lg py-2.5 transition-colors"
          >
            {busy ? "…" : mode === "signup" ? "Create account" : "Sign in"}
          </button>
        </form>

        <div className="text-center text-sm space-y-2">
          <button
            onClick={() => { setMode(mode === "signup" ? "login" : "signup"); setError(null); }}
            className="text-slate-400 hover:text-sky-400"
          >
            {mode === "signup" ? "Already have an account? Sign in" : "Need an account? Sign up"}
          </button>
          <div>
            <button onClick={onBack} className="text-slate-600 hover:text-slate-400 underline underline-offset-2">
              ← or bring your own AI key
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
