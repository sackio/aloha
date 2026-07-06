/**
 * RelaySubscribe.tsx
 *
 * The $1/mo Aloha relay sign-up / subscribe flow, shown when the user picks the
 * relay tunnel but isn't entitled yet. Steps: create/log in to an Aloha account
 * → Subscribe ($1/mo, Stripe Checkout in a new tab) → poll until entitled →
 * onEntitled() (the picker then starts the tunnel).
 */

import React, { useEffect, useRef, useState } from "react";
import { relayStatus, relaySignup, relayLogin, relaySubscribe } from "../../api/client";

type Step = "loading" | "account" | "subscribe" | "waiting";

export function RelaySubscribe({ onEntitled, onCancel }: { onEntitled: () => void; onCancel: () => void }) {
  const [step, setStep] = useState<Step>("loading");
  const [mode, setMode] = useState<"signup" | "login">("signup");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");
  const poll = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPoll = () => { if (poll.current) { clearInterval(poll.current); poll.current = null; } };

  useEffect(() => {
    relayStatus()
      .then((s) => setStep(s.entitled ? (onEntitled(), "loading") : s.has_account ? "subscribe" : "account"))
      .catch(() => setStep("account"));
    return stopPoll;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function submitAccount() {
    setErr(""); setBusy(true);
    try {
      await (mode === "signup" ? relaySignup(email.trim(), password) : relayLogin(email.trim(), password));
      const s = await relayStatus();
      setStep(s.entitled ? (onEntitled(), "loading") : "subscribe");
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Couldn't sign in.");
    } finally { setBusy(false); }
  }

  async function subscribe() {
    setErr(""); setBusy(true);
    try {
      const { url } = await relaySubscribe();
      window.open(url, "_blank", "noopener");
      setStep("waiting");
      poll.current = setInterval(async () => {
        try {
          const s = await relayStatus();
          if (s.entitled) { stopPoll(); onEntitled(); }
        } catch { /* keep polling */ }
      }, 3000);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Couldn't start checkout.");
    } finally { setBusy(false); }
  }

  const field = "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500";

  return (
    <div className="rounded-xl border border-sky-500/40 bg-slate-900/60 p-4 space-y-3">
      <div className="flex items-center justify-between">
        <div className="text-sm font-semibold text-slate-100">🌺 Aloha relay — $1/mo</div>
        <button onClick={() => { stopPoll(); onCancel(); }} className="text-xs text-slate-500 hover:text-slate-300">cancel</button>
      </div>

      {step === "loading" && <p className="text-sm text-slate-400">Checking your account…</p>}

      {step === "account" && (
        <div className="space-y-2">
          <p className="text-sm text-slate-400">
            {mode === "signup" ? "Create an Aloha account to subscribe." : "Log in to your Aloha account."}
          </p>
          <input className={field} type="email" placeholder="you@email.com" value={email} onChange={(e) => setEmail(e.target.value)} />
          <input className={field} type="password" placeholder="Password (8+ chars)" value={password} onChange={(e) => setPassword(e.target.value)} />
          <div className="flex items-center gap-3">
            <button onClick={submitAccount} disabled={busy || !email.trim() || password.length < 8}
                    className="text-sm bg-sky-500 hover:bg-sky-400 disabled:opacity-40 text-white font-medium rounded-lg px-4 py-2">
              {busy ? "…" : mode === "signup" ? "Create account" : "Log in"}
            </button>
            <button onClick={() => { setMode(mode === "signup" ? "login" : "signup"); setErr(""); }}
                    className="text-xs text-sky-400 hover:text-sky-300">
              {mode === "signup" ? "I already have an account" : "Create one instead"}
            </button>
          </div>
        </div>
      )}

      {step === "subscribe" && (
        <div className="space-y-2">
          <p className="text-sm text-slate-400">You're signed in. Subscribe to get a stable public MCP URL — cancel anytime.</p>
          <button onClick={subscribe} disabled={busy}
                  className="text-sm bg-sky-500 hover:bg-sky-400 disabled:opacity-40 text-white font-medium rounded-lg px-4 py-2">
            {busy ? "Opening checkout…" : "Subscribe — $1/mo"}
          </button>
        </div>
      )}

      {step === "waiting" && (
        <div className="flex items-center gap-2 text-sm text-slate-300">
          <div className="w-4 h-4 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
          Finishing in the Stripe tab… this updates automatically once payment completes.
        </div>
      )}

      {err && <div className="rounded-lg bg-red-900/30 border border-red-700/40 px-3 py-2 text-sm text-red-300">{err}</div>}
    </div>
  );
}
