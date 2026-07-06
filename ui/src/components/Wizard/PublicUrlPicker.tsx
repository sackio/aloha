/**
 * PublicUrlPicker.tsx
 *
 * Give the box's /mcp a public URL so a *cloud* chatbot can reach it from
 * outside the home network. Three options: Cloudflared (free), ngrok (BYOK),
 * or the Aloha relay ($1/mo). Reports the resulting public URL up to the parent.
 */

import React, { useEffect, useState } from "react";
import { getPublicUrl, setPublicUrl, disablePublicUrl, PublicUrlStatus } from "../../api/client";
import { RelaySubscribe } from "./RelaySubscribe";

type Provider = "cloudflared" | "ngrok" | "relay";

const OPTIONS: Array<{ id: Provider; emoji: string; title: string; blurb: string; tag: string }> = [
  { id: "cloudflared", emoji: "☁️", title: "Cloudflare tunnel", tag: "Free",
    blurb: "Built-in, zero setup. URL changes each restart." },
  { id: "ngrok", emoji: "🔗", title: "ngrok", tag: "Your account",
    blurb: "Bring your own ngrok authtoken." },
  { id: "relay", emoji: "🌺", title: "Aloha relay", tag: "$1/mo",
    blurb: "Stable branded URL, nothing to install. Cancel anytime." },
];

// Static design preview (preview.html) has no backend — simulate so the flow
// is clickable without live API calls.
const DEMO = typeof window !== "undefined" && window.location.pathname.includes("preview");
const DEMO_URL: Record<Provider, string> = {
  cloudflared: "https://calm-otter-8123.trycloudflare.com/mcp",
  ngrok: "https://a1b2-203-0-113-7.ngrok-free.app/mcp",
  relay: "https://aloha.pushbuild.com/box/DEMO7xk29fQ/mcp",
};

export function PublicUrlPicker({ onUrl }: { onUrl?: (url: string) => void }) {
  const [status, setStatus] = useState<PublicUrlStatus | null>(null);
  const [busy, setBusy] = useState<Provider | null>(null);
  const [ngrokTok, setNgrokTok] = useState("");
  const [showNgrok, setShowNgrok] = useState(false);
  const [relayFlow, setRelayFlow] = useState(false);
  const [err, setErr] = useState("");

  useEffect(() => {
    if (DEMO) return;
    getPublicUrl().then((s) => { setStatus(s); if (s.url) onUrl?.(s.url); }).catch(() => {});
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function choose(p: Provider) {
    setErr("");
    if (p === "ngrok" && !showNgrok) { setShowNgrok(true); return; }
    if (DEMO) {
      setBusy(p);
      await new Promise((r) => setTimeout(r, 500));
      const s: PublicUrlStatus = { provider: p, url: DEMO_URL[p], online: true, error: "" };
      setStatus(s); onUrl?.(s.url); setBusy(null);
      return;
    }
    // The relay is paid — run the sign-up/subscribe flow first; it calls
    // startProvider("relay") once the account is entitled.
    if (p === "relay") { setRelayFlow(true); return; }
    await startProvider(p);
  }

  async function startProvider(p: Provider) {
    setBusy(p); setRelayFlow(false);
    try {
      const s = await setPublicUrl(p, p === "ngrok" ? ngrokTok.trim() : undefined);
      setStatus(s);
      if (s.error) setErr(s.error);
      if (s.url) onUrl?.(s.url);
    } catch (e) {
      setErr(e instanceof Error ? e.message : "Failed to start tunnel.");
    } finally {
      setBusy(null);
    }
  }

  async function turnOff() {
    setBusy("relay");
    try {
      if (DEMO) { setStatus(null); onUrl?.(""); setShowNgrok(false); return; }
      const s = await disablePublicUrl(); setStatus(s); onUrl?.(""); setShowNgrok(false);
    } finally { setBusy(null); }
  }

  const active = status?.online ? status.provider : null;

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-4">
      <div>
        <h3 className="font-semibold text-slate-100">🌐 Make it reachable from the cloud</h3>
        <p className="text-sm text-slate-400">
          Your box is on your home network. To point a <b className="text-slate-300">cloud</b> chatbot
          (claude.ai, ChatGPT) at it, give it a public URL. On the same network? You can skip this.
        </p>
      </div>

      {active && status?.url ? (
        <div className="rounded-lg bg-emerald-900/25 border border-emerald-700/40 px-4 py-3 space-y-1">
          <div className="text-xs text-emerald-300/80">Public MCP URL live via {active}</div>
          <div className="text-sm text-emerald-200 font-mono break-all">{status.url}</div>
          <button onClick={turnOff} disabled={busy !== null}
                  className="text-xs text-slate-400 hover:text-slate-200 underline underline-offset-2">
            turn off
          </button>
        </div>
      ) : (
        <div className="grid sm:grid-cols-3 gap-3">
          {OPTIONS.map((o) => (
            <button key={o.id} onClick={() => choose(o.id)} disabled={busy !== null}
              className="text-left p-4 rounded-xl bg-slate-900 border border-slate-700 hover:border-sky-500 transition-colors disabled:opacity-50">
              <div className="flex items-center justify-between">
                <span className="text-2xl">{o.emoji}</span>
                <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-slate-700 text-slate-300">{o.tag}</span>
              </div>
              <div className="mt-2 text-sm font-semibold text-slate-100">{o.title}</div>
              <p className="text-xs text-slate-400 mt-0.5">{o.blurb}</p>
              {busy === o.id && <div className="mt-2 text-xs text-sky-400">starting…</div>}
            </button>
          ))}
        </div>
      )}

      {relayFlow && !active && (
        <RelaySubscribe onEntitled={() => startProvider("relay")} onCancel={() => setRelayFlow(false)} />
      )}

      {showNgrok && !active && (
        <div className="space-y-2">
          <input type="password" value={ngrokTok} onChange={(e) => setNgrokTok(e.target.value)}
                 placeholder="ngrok authtoken"
                 className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono" />
          <button onClick={() => choose("ngrok")} disabled={!ngrokTok.trim() || busy !== null}
                  className="text-sm bg-sky-500 hover:bg-sky-400 disabled:opacity-40 text-white rounded-lg px-4 py-1.5">
            Start ngrok
          </button>
        </div>
      )}

      {err && (
        <div className="rounded-lg bg-red-900/30 border border-red-700/40 px-4 py-2 text-sm text-red-300">{err}</div>
      )}
    </div>
  );
}
