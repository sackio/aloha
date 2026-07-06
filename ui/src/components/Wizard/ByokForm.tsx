/**
 * ByokForm.tsx
 *
 * "Bring your own AI" — one simple form: pick a provider, enter credentials,
 * connect. No multi-step wizard. Reuses the same submit path as before
 * (test connection → save settings → onSuccess).
 */

import React, { useMemo, useState } from "react";
import { testConnection, updateSettings } from "../../api/client";
import { ProviderConfig } from "./FirstRun";
import { PROVIDERS } from "./ProviderPicker";

type ConnectState = "idle" | "loading" | "success" | "error";

const OLLAMA_DEFAULT = "http://localhost:11434";
const CUSTOM_DEFAULT = "http://localhost:8080/v1";

export function ByokForm({ onSuccess }: { onSuccess: () => void }) {
  // Everything except the managed option.
  const providers = useMemo(() => PROVIDERS.filter((p) => p.id !== "aloha"), []);

  const [providerId, setProviderId] = useState<ProviderConfig["id"]>(providers[0].id);
  const provider = providers.find((p) => p.id === providerId)!;

  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState(CUSTOM_DEFAULT);
  const [ollamaUrl, setOllamaUrl] = useState(OLLAMA_DEFAULT);
  const [model, setModel] = useState(provider.default_model);
  const [state, setState] = useState<ConnectState>("idle");
  const [error, setError] = useState<string | null>(null);

  const isCustom = provider.id === "custom";
  const isOllama = provider.id === "ollama";
  const needsKey = provider.requires_api_key;

  function pickProvider(id: ProviderConfig["id"]) {
    const p = providers.find((x) => x.id === id)!;
    setProviderId(id);
    setModel(p.default_model);
    setApiKey("");
    setState("idle");
    setError(null);
  }

  const canSubmit =
    state !== "loading" &&
    state !== "success" &&
    (!needsKey || apiKey.trim().length > 0);

  async function connect() {
    setState("loading");
    setError(null);
    const key = apiKey.trim();
    try {
      const result = await testConnection({
        provider: provider.id,
        api_key: key || undefined,
        model: model || undefined,
      });
      if (!result.ok) {
        setState("error");
        setError(result.error ?? "Connection test failed — check your credentials.");
        return;
      }
    } catch (err) {
      setState("error");
      setError(err instanceof Error ? err.message : "Couldn't reach the Aloha backend.");
      return;
    }

    try {
      await updateSettings({
        ai_provider: provider.id,
        model: model || provider.default_model || "auto",
        api_key: key || undefined,
        ...(isCustom ? { custom_base_url: baseUrl.trim() } : {}),
        ...(isOllama ? { ollama_url: ollamaUrl.trim() } : {}),
        setup_complete: true,
      });
    } catch (err) {
      setState("error");
      setError(err instanceof Error ? err.message : "Failed to save settings.");
      return;
    }

    setState("success");
    setTimeout(onSuccess, 600);
  }

  const field =
    "w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500";
  const label = "block text-xs font-medium text-slate-400 mb-1.5";

  return (
    <div className="bg-slate-800 border border-slate-700 rounded-xl p-5 space-y-4">
      {/* Provider */}
      <div>
        <label className={label}>Provider</label>
        <select
          value={providerId}
          onChange={(e) => pickProvider(e.target.value as ProviderConfig["id"])}
          className={field}
        >
          {providers.map((p) => (
            <option key={p.id} value={p.id}>
              {p.emoji}  {p.name}
            </option>
          ))}
        </select>
      </div>

      {/* Ollama host */}
      {isOllama && (
        <div>
          <label className={label}>Ollama URL</label>
          <input type="url" value={ollamaUrl} onChange={(e) => setOllamaUrl(e.target.value)}
                 placeholder={OLLAMA_DEFAULT} className={field} />
        </div>
      )}

      {/* Custom base URL */}
      {isCustom && (
        <div>
          <label className={label}>Base URL</label>
          <input type="url" value={baseUrl} onChange={(e) => setBaseUrl(e.target.value)}
                 placeholder={CUSTOM_DEFAULT} className={field} />
        </div>
      )}

      {/* API key */}
      {needsKey && (
        <div>
          <label className={label}>API key</label>
          <input
            type="password"
            value={apiKey}
            onChange={(e) => { setApiKey(e.target.value); if (state === "error") { setState("idle"); setError(null); } }}
            placeholder="Paste your key"
            autoFocus
            className={`${field} font-mono`}
          />
        </div>
      )}

      {/* Model (when the provider advertises a list) */}
      {provider.models.length > 0 && (
        <div>
          <label className={label}>Model <span className="text-slate-600">(optional)</span></label>
          <select value={model} onChange={(e) => setModel(e.target.value)} className={field}>
            {provider.models.map((m) => (
              <option key={m} value={m}>{m}</option>
            ))}
          </select>
        </div>
      )}

      {/* Custom needs a free-text model */}
      {isCustom && (
        <div>
          <label className={label}>Model</label>
          <input type="text" value={model} onChange={(e) => setModel(e.target.value)}
                 placeholder="model name" className={field} />
        </div>
      )}

      {state === "error" && error && (
        <div className="rounded-lg bg-red-900/30 border border-red-700/40 px-4 py-3 text-sm text-red-300">
          {error}
        </div>
      )}

      <button
        onClick={connect}
        disabled={!canSubmit}
        className={`w-full flex items-center justify-center gap-2 font-medium rounded-lg py-2.5 text-sm transition-all ${
          state === "success"
            ? "bg-emerald-500 text-white cursor-default"
            : "bg-sky-500 hover:bg-sky-400 disabled:opacity-40 disabled:cursor-not-allowed text-white"
        }`}
      >
        {state === "loading" && <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />}
        {state === "idle" && "Connect"}
        {state === "loading" && "Verifying…"}
        {state === "success" && "Connected!"}
        {state === "error" && "Try again"}
      </button>
    </div>
  );
}
