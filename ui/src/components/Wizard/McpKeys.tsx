/**
 * McpKeys.tsx
 *
 * Manage MCP access keys (key + secret). The secret is shown once, at mint /
 * regenerate. Reports the freshly-revealed secret up via onSecret so the connect
 * snippets can embed the Authorization header.
 */

import React, { useEffect, useState } from "react";
import { getMcpKeys, mintMcpKey, regenMcpKey, deleteMcpKey, McpKey } from "../../api/client";

function Copy({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button onClick={() => { navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1200); }}
            className="shrink-0 text-xs px-2 py-1 rounded-md bg-slate-700 hover:bg-sky-600 text-slate-200">
      {done ? "Copied ✓" : "Copy"}
    </button>
  );
}

export function McpKeys({ onSecret }: { onSecret?: (secret: string) => void }) {
  const [keys, setKeys] = useState<McpKey[]>([]);
  const [name, setName] = useState("");
  const [reveal, setReveal] = useState<{ id: string; secret: string } | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState("");

  async function refresh() {
    try { setKeys(await getMcpKeys()); } catch { /* ignore */ }
  }
  useEffect(() => { refresh(); }, []);

  async function mint() {
    setErr(""); setBusy(true);
    try {
      const k = await mintMcpKey(name.trim() || "MCP key");
      setReveal({ id: k.id, secret: k.secret });
      onSecret?.(k.secret);
      setName("");
      await refresh();
    } catch (e) { setErr(e instanceof Error ? e.message : "Could not create key."); }
    finally { setBusy(false); }
  }

  async function regen(id: string) {
    setErr("");
    try { const k = await regenMcpKey(id); setReveal({ id, secret: k.secret }); onSecret?.(k.secret); await refresh(); }
    catch (e) { setErr(e instanceof Error ? e.message : "Could not regenerate."); }
  }

  async function remove(id: string) {
    if (!confirm("Terminate this key? Any chatbot using it will lose access.")) return;
    setErr("");
    try { await deleteMcpKey(id); if (reveal?.id === id) setReveal(null); await refresh(); }
    catch (e) { setErr(e instanceof Error ? e.message : "Could not delete."); }
  }

  const field = "flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500";

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-3">
      <div>
        <h3 className="font-semibold text-slate-100">🔑 Access keys</h3>
        <p className="text-sm text-slate-400">
          Require an access key so only you can drive this MCP. <b className="text-slate-300">Create one before
          exposing a public URL.</b> The secret is shown once — copy it into your chatbot's config.
        </p>
      </div>

      {reveal && (
        <div className="rounded-lg bg-amber-900/20 border border-amber-700/40 px-4 py-3 space-y-1.5">
          <div className="text-xs text-amber-300/90">New secret — copy it now, it won't be shown again:</div>
          <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2">
            <code className="flex-1 text-[12px] text-amber-200 font-mono break-all">{reveal.secret}</code>
            <Copy text={reveal.secret} />
          </div>
        </div>
      )}

      {keys.length > 0 && (
        <div className="space-y-1.5">
          {keys.map((k) => (
            <div key={k.id} className="flex items-center gap-2 text-sm bg-slate-900/60 border border-slate-700 rounded-lg px-3 py-2">
              <span className="text-slate-200">{k.name}</span>
              <span className="text-xs text-slate-500 font-mono">{k.secret_prefix}…</span>
              <span className="flex-1" />
              <button onClick={() => regen(k.id)} className="text-xs text-sky-400 hover:text-sky-300">regenerate</button>
              <button onClick={() => remove(k.id)} className="text-xs text-red-400 hover:text-red-300">terminate</button>
            </div>
          ))}
        </div>
      )}

      <div className="flex items-center gap-2">
        <input value={name} onChange={(e) => setName(e.target.value)} placeholder="Key name (e.g. my-laptop)" className={field} />
        <button onClick={mint} disabled={busy}
                className="text-sm bg-sky-500 hover:bg-sky-400 disabled:opacity-40 text-white font-medium rounded-lg px-4 py-2">
          {busy ? "…" : "Create key"}
        </button>
      </div>

      {err && <div className="rounded-lg bg-red-900/30 border border-red-700/40 px-3 py-2 text-sm text-red-300">{err}</div>}
    </div>
  );
}
