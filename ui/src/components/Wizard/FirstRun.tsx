/**
 * FirstRun.tsx
 *
 * Main first-run wizard shell. Drives a state machine through setup steps:
 *   loading -> picker -> oauth | key_wizard | ollama -> complete
 *
 * On mount: GET /health.
 *   - setup_complete=true  -> redirect to main chat (replace history)
 *   - ha_connected=false   -> show HA startup loading screen, poll /health every 2s
 *   - otherwise            -> show provider picker
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { getHealth, HealthResponse } from "../../api/client";
import { ProviderPicker } from "./ProviderPicker";
import { OAuthFlow } from "./OAuthFlow";
import { KeyWizard } from "./KeyWizard";
import { OllamaSetup } from "./OllamaSetup";
import { ManagedSignIn } from "./ManagedSignIn";
import { ConnectChatbot } from "./ConnectChatbot";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type WizardStep = "loading" | "welcome" | "connect" | "picker" | "oauth" | "key_wizard" | "ollama" | "managed" | "complete";

export interface ProviderConfig {
  id: "anthropic" | "openai" | "gemini" | "ollama" | "openrouter" | "groq" | "custom" | "aloha";
  name: string;
  emoji: string;
  tagline: string;
  authBadge: "oauth" | "key" | "local" | "managed";
  /** Featured/recommended provider — highlighted in the picker grid */
  recommended?: boolean;
  requires_api_key: boolean;
  models: string[];
  default_model: string;
  // Steps shown in KeyWizard for API-key providers
  steps: Array<{
    title: string;
    instruction: string;
    url?: string;
  }>;
}

// ---------------------------------------------------------------------------
// HA startup loading screen
// ---------------------------------------------------------------------------

function HAStartupScreen() {
  const [dots, setDots] = useState(0);

  useEffect(() => {
    const id = setInterval(() => setDots((d) => (d + 1) % 4), 500);
    return () => clearInterval(id);
  }, []);

  const dotStr = ".".repeat(dots);

  return (
    <div className="flex flex-col items-center justify-center min-h-screen bg-slate-900 text-slate-100 gap-8">
      {/* Animated pulse icon */}
      <div className="relative">
        <div className="w-20 h-20 rounded-full bg-sky-500/20 flex items-center justify-center animate-pulse">
          <div className="w-12 h-12 rounded-full bg-sky-500/40 flex items-center justify-center">
            <div className="w-6 h-6 rounded-full bg-sky-500" />
          </div>
        </div>
        {/* Ripple rings */}
        <div className="absolute inset-0 rounded-full border-2 border-sky-500/30 animate-ping" />
      </div>

      <div className="text-center space-y-2">
        <p className="text-xl font-semibold text-slate-100">
          Home Assistant is starting{dotStr}
        </p>
        <p className="text-sm text-slate-400">
          This may take a minute on first boot
        </p>
      </div>

      {/* Progress bar (indeterminate) */}
      <div className="w-64 h-1.5 bg-slate-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-sky-500 rounded-full animate-[slide_1.5s_ease-in-out_infinite]"
          style={{
            width: "40%",
            animation: "slideBar 1.5s ease-in-out infinite",
          }}
        />
      </div>

      <style>{`
        @keyframes slideBar {
          0%   { transform: translateX(-150%); }
          100% { transform: translateX(400%); }
        }
      `}</style>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main wizard shell
// ---------------------------------------------------------------------------

export function FirstRun() {
  const [step, setStep] = useState<WizardStep>("loading");
  const [selectedProvider, setSelectedProvider] = useState<ProviderConfig | null>(null);
  const [useKey, setUseKey] = useState(false);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPoll = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // On mount: check health once
  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      let health: HealthResponse;
      try {
        health = await getHealth();
      } catch {
        // Backend not reachable yet — treat as HA starting
        if (!cancelled) setStep("loading");
        return;
      }

      if (cancelled) return;

      if (health.setup_complete) {
        // Redirect to main app — replace history so Back doesn't loop
        window.location.replace("/");
        return;
      }

      if (!health.ha_connected) {
        setStep("loading");
        startHAPoller();
        return;
      }

      setStep("welcome");
    }

    checkHealth();

    return () => {
      cancelled = true;
      stopPoll();
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  function startHAPoller() {
    stopPoll();
    pollRef.current = setInterval(async () => {
      try {
        const health = await getHealth();
        if (health.setup_complete) {
          stopPoll();
          window.location.replace("/");
          return;
        }
        if (health.ha_connected) {
          stopPoll();
          setStep("welcome");
        }
      } catch {
        // Keep polling
      }
    }, 2000);
  }

  // Clean up poller on unmount
  useEffect(() => () => stopPoll(), [stopPoll]);

  // ---------------------------------------------------------------------------
  // Provider selected callback from ProviderPicker
  // ---------------------------------------------------------------------------

  function handleProviderSelect(provider: ProviderConfig, forceKey = false) {
    setSelectedProvider(provider);
    setUseKey(forceKey);

    if (provider.id === "aloha") {
      setStep("managed");
    } else if (provider.id === "ollama") {
      setStep("ollama");
    } else if (forceKey || provider.authBadge !== "oauth") {
      setStep("key_wizard");
    } else {
      setStep("oauth");
    }
  }

  // ---------------------------------------------------------------------------
  // Success
  // ---------------------------------------------------------------------------

  function handleSuccess() {
    setStep("complete");
    // Redirect after brief delay so user sees the success state
    setTimeout(() => window.location.replace("/"), 800);
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  if (step === "loading") {
    return <HAStartupScreen />;
  }

  if (step === "complete") {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-slate-900 text-slate-100 gap-4">
        <div className="w-16 h-16 rounded-full bg-emerald-500/20 flex items-center justify-center">
          <svg className="w-8 h-8 text-emerald-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
          </svg>
        </div>
        <p className="text-lg font-semibold">Setup complete — launching Aloha</p>
      </div>
    );
  }

  if (step === "welcome") {
    return (
      <div className="min-h-screen bg-slate-900 flex items-center justify-center px-6 py-16">
        <div className="w-full max-w-3xl space-y-10">
          <div className="text-center space-y-2">
            <div className="text-5xl">🌺</div>
            <h1 className="text-3xl font-bold text-slate-100">
              Welcome to <span className="text-sky-400">Aloha</span>
            </h1>
            <p className="text-slate-400">Your Home Assistant, driven by an AI agent. Two ways to start:</p>
          </div>
          <div className="grid md:grid-cols-2 gap-5">
            <button
              onClick={() => setStep("connect")}
              className="text-left p-7 rounded-2xl bg-slate-800 border border-slate-700 hover:border-sky-500 hover:-translate-y-0.5 transition-all"
            >
              <div className="text-4xl mb-3">🔌</div>
              <div className="text-lg font-semibold text-slate-100 mb-1">Use your own chatbot</div>
              <p className="text-sm text-slate-400">
                Point Claude, Cursor, or any MCP chatbot at Aloha and it can run your home.
                Free — no AI key on the box.
              </p>
            </button>
            <button
              onClick={() => setStep("picker")}
              className="text-left p-7 rounded-2xl bg-slate-800 hover:-translate-y-0.5 transition-all"
              style={{
                background:
                  "linear-gradient(#1e293b,#1e293b) padding-box, linear-gradient(105deg,#ff7d5c,#ffb866) border-box",
                border: "1.5px solid transparent",
              }}
            >
              <div className="text-4xl mb-3">🤖</div>
              <div className="text-lg font-semibold text-slate-100 mb-1">Let Aloha be your agent</div>
              <p className="text-sm text-slate-400">
                Chat right here. Sign in for the managed service (no API key), or bring your own AI key.
              </p>
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (step === "connect") {
    return (
      <ConnectChatbot
        onDone={() => window.location.replace("/")}
        onBack={() => setStep("welcome")}
      />
    );
  }

  if (step === "picker") {
    return (
      <ProviderPicker
        onSelect={(provider, forceKey) => handleProviderSelect(provider, forceKey)}
        onSuccess={handleSuccess}
      />
    );
  }

  if (step === "oauth" && selectedProvider) {
    return (
      <OAuthFlow
        provider={selectedProvider}
        onSuccess={handleSuccess}
        onBack={() => setStep("picker")}
        onUseKey={() => {
          setUseKey(true);
          setStep("key_wizard");
        }}
      />
    );
  }

  if (step === "key_wizard" && selectedProvider) {
    return (
      <KeyWizard
        provider={selectedProvider}
        onSuccess={handleSuccess}
        onBack={() => setStep("picker")}
      />
    );
  }

  if (step === "ollama") {
    return (
      <OllamaSetup
        onSuccess={handleSuccess}
        onBack={() => setStep("picker")}
      />
    );
  }

  if (step === "managed") {
    return (
      <ManagedSignIn
        onSuccess={handleSuccess}
        onBack={() => setStep("picker")}
      />
    );
  }

  return null;
}
