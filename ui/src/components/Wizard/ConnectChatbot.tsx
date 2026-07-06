/**
 * ConnectChatbot.tsx
 *
 * The "bring your own chatbot" door. Aloha's box exposes an MCP endpoint + a
 * skill library; point any MCP-capable chatbot (Claude Code, Cursor, Claude
 * Desktop, …) at it and it can drive Home Assistant. No AI key on the box.
 */

import React, { useState } from "react";
import { useSettingsStore } from "../../stores/settings";
import { PublicUrlPicker } from "./PublicUrlPicker";

function Copy({ text }: { text: string }) {
  const [done, setDone] = useState(false);
  return (
    <button
      onClick={() => { navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1200); }}
      className="shrink-0 text-xs px-2.5 py-1 rounded-md bg-slate-700 hover:bg-sky-600 text-slate-200 transition-colors"
    >
      {done ? "Copied ✓" : "Copy"}
    </button>
  );
}

function Snippet({ label, code }: { label: string; code: string }) {
  return (
    <div className="space-y-1.5">
      <div className="text-xs text-slate-400">{label}</div>
      <div className="flex items-center gap-2 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2">
        <code className="flex-1 text-[13px] text-sky-200 font-mono overflow-x-auto whitespace-pre">{code}</code>
        <Copy text={code} />
      </div>
    </div>
  );
}

export function ConnectChatbot({ onDone, onBack }: { onDone: () => void; onBack: () => void }) {
  const setSetupComplete = useSettingsStore((s) => s.setSetupComplete);
  const origin = typeof window !== "undefined" ? window.location.origin : "http://aloha.local:7123";
  const [publicUrl, setPublicUrl] = useState("");
  // Prefer the public URL (reachable from the cloud) once one is live.
  const mcpUrl = publicUrl || `${origin}/mcp`;

  async function finish() {
    try { await setSetupComplete(true); } catch { /* non-fatal */ }
    onDone();
  }

  return (
    <div className="min-h-screen bg-slate-900 flex items-center justify-center px-6 py-16">
      <div className="w-full max-w-2xl space-y-8">
        <div className="space-y-2">
          <h1 className="text-2xl font-bold text-slate-100">Connect your chatbot 🔌</h1>
          <p className="text-slate-400">
            Aloha exposes your Home Assistant as an <b className="text-slate-200">MCP server</b>. Point any
            MCP-capable chatbot at it and it can read and control your home — no API key on this box.
          </p>
        </div>

        <PublicUrlPicker onUrl={setPublicUrl} />

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-5">
          {publicUrl && (
            <div className="text-xs text-emerald-300/80">
              Using your public URL — paste these into a cloud chatbot.
            </div>
          )}
          <Snippet label="Your Aloha MCP endpoint" code={mcpUrl} />
          <Snippet label="Claude Code — one command" code={`claude mcp add --transport sse aloha ${mcpUrl}`} />
          <Snippet
            label="Cursor / Claude Desktop / VS Code — mcp config"
            code={`{\n  "mcpServers": {\n    "aloha": { "url": "${mcpUrl}", "type": "sse" }\n  }\n}`}
          />
        </div>

        <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-2">
          <h3 className="font-semibold text-slate-100">📚 Add the HA skills</h3>
          <p className="text-sm text-slate-400">
            Aloha ships curated Home-Assistant playbooks (installing integrations, debugging automations,
            backups, and more). Browse them, or drop the files into your chatbot to make it great at HA:
          </p>
          <div className="flex flex-wrap gap-3 text-sm">
            <a href={`${origin}/api/skills`} target="_blank" rel="noreferrer"
               className="text-sky-400 hover:text-sky-300 underline underline-offset-2">
              {origin}/api/skills
            </a>
            <span className="text-slate-600">·</span>
            <a href="https://github.com/sackio/aloha/tree/main/aloha/skills/library" target="_blank" rel="noreferrer"
               className="text-sky-400 hover:text-sky-300 underline underline-offset-2">
              skills on GitHub ↗
            </a>
          </div>
        </div>

        <div className="flex items-center justify-between">
          <button onClick={onBack} className="text-sm text-slate-500 hover:text-slate-300 underline underline-offset-2">
            ← back
          </button>
          <button onClick={finish}
                  className="bg-sky-500 hover:bg-sky-400 text-white font-semibold rounded-lg px-6 py-2.5 transition-colors">
            Done — I've connected
          </button>
        </div>
      </div>
    </div>
  );
}
