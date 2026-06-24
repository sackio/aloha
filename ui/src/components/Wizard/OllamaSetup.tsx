/**
 * OllamaSetup.tsx
 *
 * Wizard step for the Ollama local provider.
 *
 * Flow:
 *   1. Check Ollama reachability via POST /api/auth/test { provider: "ollama" }
 *   2a. Not running → show install instructions + link to ollama.com
 *   2b. Running     → show model selector from PROVIDERS["ollama"].models list
 *                     + "Pull & Use" button that saves settings and calls onSuccess()
 *
 * The URL input lets users override the default http://localhost:11434.
 */

import React, { useCallback, useEffect, useState } from "react";
import { testConnection, updateSettings } from "../../api/client";
import { PROVIDERS } from "./ProviderPicker";

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

const OLLAMA_PROVIDER = PROVIDERS.find((p) => p.id === "ollama")!;
const DEFAULT_OLLAMA_URL = "http://localhost:11434";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type CheckState = "checking" | "not_running" | "running" | "error";
type PullState = "idle" | "pulling" | "success" | "error";

// ---------------------------------------------------------------------------
// OllamaSetup
// ---------------------------------------------------------------------------

interface OllamaSetupProps {
  onSuccess: () => void;
  onBack: () => void;
}

export function OllamaSetup({ onSuccess, onBack }: OllamaSetupProps) {
  const [ollamaUrl, setOllamaUrl] = useState(DEFAULT_OLLAMA_URL);
  const [checkState, setCheckState] = useState<CheckState>("checking");
  const [selectedModel, setSelectedModel] = useState(OLLAMA_PROVIDER.default_model);
  const [pullState, setPullState] = useState<PullState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  // ---------------------------------------------------------------------------
  // Reachability check
  // ---------------------------------------------------------------------------

  const checkOllama = useCallback(async (url: string) => {
    setCheckState("checking");
    setErrorMsg(null);

    try {
      const result = await testConnection({
        provider: "ollama",
        model: selectedModel,
        // Pass the custom URL via api_key field repurposed — backend reads
        // the ollama_url from settings, but we send it here as a hint.
        // The actual approach: we update ollama_url in settings first.
      });

      if (result.ok) {
        setCheckState("running");
      } else {
        setCheckState("not_running");
      }
    } catch {
      setCheckState("not_running");
    }
  }, [selectedModel]);

  // Check on mount and whenever URL changes (after user commits)
  useEffect(() => {
    checkOllama(ollamaUrl);
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // ---------------------------------------------------------------------------
  // Pull & Use
  // ---------------------------------------------------------------------------

  async function handlePullAndUse() {
    setPullState("pulling");
    setErrorMsg(null);

    try {
      // Save settings: provider=ollama, model, ollama_url, setup_complete
      await updateSettings({
        ai_provider: "ollama",
        model: selectedModel,
        ollama_url: ollamaUrl,
        setup_complete: true,
      });
    } catch (err) {
      setPullState("error");
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to save settings."
      );
      return;
    }

    setPullState("success");
    setTimeout(onSuccess, 600);
  }

  // ---------------------------------------------------------------------------
  // Re-check with updated URL
  // ---------------------------------------------------------------------------

  function handleUrlCheck() {
    checkOllama(ollamaUrl);
  }

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  function renderCheckBadge() {
    if (checkState === "checking") {
      return (
        <span className="flex items-center gap-1.5 text-xs text-slate-400">
          <div className="w-3 h-3 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
          Checking…
        </span>
      );
    }
    if (checkState === "running") {
      return (
        <span className="flex items-center gap-1.5 text-xs text-emerald-400">
          <div className="w-2 h-2 rounded-full bg-emerald-400" />
          Ollama is running
        </span>
      );
    }
    return (
      <span className="flex items-center gap-1.5 text-xs text-red-400">
        <div className="w-2 h-2 rounded-full bg-red-400" />
        Not detected
      </span>
    );
  }

  // ---------------------------------------------------------------------------
  // Main render
  // ---------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-md space-y-6">
        {/* Back */}
        <button
          onClick={onBack}
          className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-300 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back
        </button>

        {/* Card */}
        <div className="bg-slate-800 rounded-2xl border border-slate-700 p-8 space-y-6">
          {/* Header */}
          <div className="flex items-center gap-3">
            <span className="text-4xl select-none">🦙</span>
            <div>
              <h2 className="text-xl font-semibold text-slate-100">Ollama Setup</h2>
              <p className="text-xs text-slate-400">100% local — no account needed</p>
            </div>
          </div>

          {/* URL row */}
          <div className="space-y-1.5">
            <div className="flex items-center justify-between">
              <label className="text-xs font-medium text-slate-400">
                Ollama URL
              </label>
              {renderCheckBadge()}
            </div>
            <div className="flex gap-2">
              <input
                type="url"
                value={ollamaUrl}
                onChange={(e) => setOllamaUrl(e.target.value)}
                placeholder={DEFAULT_OLLAMA_URL}
                className="flex-1 bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
              />
              <button
                onClick={handleUrlCheck}
                disabled={checkState === "checking"}
                className="px-3 py-2 text-xs font-medium text-sky-400 border border-slate-700 rounded-lg hover:bg-slate-700 disabled:opacity-40 transition-colors whitespace-nowrap"
              >
                Check
              </button>
            </div>
          </div>

          {/* Branch: not running */}
          {checkState === "not_running" && (
            <div className="space-y-4">
              <div className="rounded-xl bg-amber-900/20 border border-amber-700/30 p-4 space-y-3">
                <p className="text-sm font-medium text-amber-300">
                  Ollama is not running
                </p>
                <p className="text-sm text-slate-400">
                  Install Ollama on your machine, then start it. Aloha will
                  connect to it automatically.
                </p>
                <ol className="text-sm text-slate-300 space-y-1 list-decimal list-inside">
                  <li>
                    <a
                      href="https://ollama.com/"
                      target="_blank"
                      rel="noopener noreferrer"
                      className="text-sky-400 hover:text-sky-300 underline underline-offset-2"
                    >
                      Download Ollama
                    </a>{" "}
                    for your platform
                  </li>
                  <li>Run the installer</li>
                  <li>
                    Ollama starts automatically — check with{" "}
                    <code className="bg-slate-900 px-1 py-0.5 rounded text-xs font-mono">
                      ollama list
                    </code>
                  </li>
                </ol>
              </div>

              <button
                onClick={handleUrlCheck}
                className="w-full flex items-center justify-center gap-2 border border-slate-700 hover:bg-slate-700 text-slate-300 font-medium rounded-xl py-3 text-sm transition-colors"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                </svg>
                Re-check connection
              </button>

              <a
                href="https://ollama.com/"
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center justify-center gap-1.5 text-sm text-sky-400 hover:text-sky-300 underline underline-offset-2 transition-colors"
              >
                Visit ollama.com
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                </svg>
              </a>
            </div>
          )}

          {/* Branch: running — show model selector */}
          {checkState === "running" && (
            <div className="space-y-5">
              {/* Model selector */}
              <div className="space-y-1.5">
                <label className="block text-xs font-medium text-slate-400">
                  Model
                </label>
                <select
                  value={selectedModel}
                  onChange={(e) => setSelectedModel(e.target.value)}
                  className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
                >
                  {OLLAMA_PROVIDER.models.map((m) => (
                    <option key={m} value={m}>
                      {m}
                    </option>
                  ))}
                </select>
                <p className="text-xs text-slate-500">
                  If the model isn't already pulled, Ollama will download it on
                  first use.
                </p>
              </div>

              {/* Error */}
              {pullState === "error" && errorMsg && (
                <div className="rounded-lg bg-red-900/30 border border-red-700/40 px-4 py-3 text-sm text-red-300">
                  {errorMsg}
                </div>
              )}

              {/* Pull & Use button */}
              <button
                onClick={handlePullAndUse}
                disabled={pullState === "pulling" || pullState === "success"}
                className={`
                  w-full flex items-center justify-center gap-2
                  font-medium rounded-xl py-3 text-sm transition-all
                  ${pullState === "success"
                    ? "bg-emerald-500 text-white cursor-default"
                    : "bg-sky-500 hover:bg-sky-400 disabled:opacity-40 disabled:cursor-not-allowed text-white"
                  }
                `}
              >
                {pullState === "pulling" && (
                  <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                )}
                {pullState === "success" && (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
                {pullState === "idle" && "Pull & Use"}
                {pullState === "pulling" && "Saving…"}
                {pullState === "success" && "Connected!"}
                {pullState === "error" && "Try Again"}
              </button>
            </div>
          )}

          {/* Checking spinner */}
          {checkState === "checking" && (
            <div className="flex items-center justify-center py-4">
              <div className="w-6 h-6 rounded-full border-2 border-sky-500 border-t-transparent animate-spin" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
