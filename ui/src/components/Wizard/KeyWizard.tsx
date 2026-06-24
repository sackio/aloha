/**
 * KeyWizard.tsx
 *
 * Step-by-step wizard for API-key–based providers (Anthropic, OpenAI, Gemini,
 * Custom). Uses provider.steps to render each step, with progress dots at top.
 *
 * Final step: API key input + "Connect" button.
 *   1. POST /api/auth/test  — validates credentials
 *   2. POST /api/settings   — saves provider + api_key + setup_complete:true
 *   3. onSuccess()          — signals FirstRun to redirect
 *
 * For the "custom" provider, step 0 is a URL input; the key step is last.
 */

import React, { useState } from "react";
import { testConnection, updateSettings } from "../../api/client";
import { ProviderConfig } from "./FirstRun";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

type ConnectState = "idle" | "loading" | "success" | "error";

// ---------------------------------------------------------------------------
// Progress dots
// ---------------------------------------------------------------------------

function ProgressDots({
  total,
  current,
}: {
  total: number;
  current: number;
}) {
  return (
    <div className="flex items-center justify-center gap-2">
      {Array.from({ length: total }).map((_, i) => (
        <div
          key={i}
          className={`h-1.5 rounded-full transition-all duration-300 ${
            i < current
              ? "w-4 bg-sky-500"
              : i === current
              ? "w-4 bg-sky-400"
              : "w-1.5 bg-slate-700"
          }`}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// KeyWizard
// ---------------------------------------------------------------------------

interface KeyWizardProps {
  provider: ProviderConfig;
  onSuccess: () => void;
  onBack: () => void;
}

export function KeyWizard({ provider, onSuccess, onBack }: KeyWizardProps) {
  const isCustom = provider.id === "custom";

  // For custom provider we may have no formal steps; derive them
  const steps = provider.steps.length > 0 ? provider.steps : [
    {
      title: `Connect ${provider.name}`,
      instruction: "Enter your API key to connect.",
    },
  ];

  const [stepIndex, setStepIndex] = useState(0);
  const [apiKey, setApiKey] = useState("");
  const [customUrl, setCustomUrl] = useState("http://localhost:8080/v1");
  const [selectedModel, setSelectedModel] = useState(provider.default_model);
  const [connectState, setConnectState] = useState<ConnectState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  const currentStep = steps[stepIndex];
  const isLastStep = stepIndex === steps.length - 1;
  const totalDots = steps.length;

  // ---------------------------------------------------------------------------
  // Navigation
  // ---------------------------------------------------------------------------

  function handleBack() {
    if (stepIndex === 0) {
      onBack();
    } else {
      setStepIndex((i) => i - 1);
    }
  }

  function handleNext() {
    if (stepIndex < steps.length - 1) {
      setStepIndex((i) => i + 1);
    }
  }

  // ---------------------------------------------------------------------------
  // Connect (final step)
  // ---------------------------------------------------------------------------

  async function handleConnect() {
    setConnectState("loading");
    setErrorMsg(null);

    const keyToTest = apiKey.trim();
    const baseUrl = isCustom ? customUrl.trim() : "";

    // 1. Test connection
    try {
      const result = await testConnection({
        provider: provider.id,
        api_key: keyToTest || undefined,
        model: selectedModel || undefined,
      });

      if (!result.ok) {
        setConnectState("error");
        setErrorMsg(result.error ?? "Connection test failed. Check your key and try again.");
        return;
      }
    } catch (err) {
      setConnectState("error");
      setErrorMsg(
        err instanceof Error ? err.message : "Could not reach the Aloha backend."
      );
      return;
    }

    // 2. Save settings
    try {
      await updateSettings({
        ai_provider: provider.id,
        model: selectedModel || provider.default_model || "auto",
        api_key: keyToTest || undefined,
        ...(isCustom && baseUrl ? { custom_base_url: baseUrl } : {}),
        setup_complete: true,
      });
    } catch (err) {
      setConnectState("error");
      setErrorMsg(
        err instanceof Error ? err.message : "Failed to save settings."
      );
      return;
    }

    setConnectState("success");
    // Brief pause so user sees the checkmark
    setTimeout(onSuccess, 600);
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-md space-y-6">
        {/* Back */}
        <button
          onClick={handleBack}
          className="flex items-center gap-1 text-sm text-slate-500 hover:text-slate-300 transition-colors"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 19l-7-7 7-7" />
          </svg>
          Back
        </button>

        {/* Card */}
        <div className="bg-slate-800 rounded-2xl border border-slate-700 p-8 space-y-7">
          {/* Progress dots */}
          <ProgressDots total={totalDots} current={stepIndex} />

          {/* Provider icon */}
          <div className="flex items-center gap-3">
            <span className="text-3xl select-none">{provider.emoji}</span>
            <div>
              <h2 className="text-lg font-semibold text-slate-100">
                {currentStep.title}
              </h2>
              <p className="text-xs text-slate-400 capitalize">{provider.name}</p>
            </div>
          </div>

          {/* Step instruction */}
          <p className="text-sm text-slate-300 leading-relaxed">
            {currentStep.instruction}
          </p>

          {/* Open URL button (optional) */}
          {currentStep.url && (
            <a
              href={currentStep.url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm text-sky-400 hover:text-sky-300 underline underline-offset-2 transition-colors"
            >
              Open {new URL(currentStep.url).hostname}
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
              </svg>
            </a>
          )}

          {/* Final step inputs */}
          {isLastStep && (
            <div className="space-y-4">
              {/* Custom URL input (custom provider only) */}
              {isCustom && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    Base URL
                  </label>
                  <input
                    type="url"
                    value={customUrl}
                    onChange={(e) => setCustomUrl(e.target.value)}
                    placeholder="http://localhost:8080/v1"
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
                  />
                </div>
              )}

              {/* Model selector (if models available and not custom) */}
              {!isCustom && provider.models.length > 0 && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    Model
                  </label>
                  <select
                    value={selectedModel}
                    onChange={(e) => setSelectedModel(e.target.value)}
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
                  >
                    {provider.models.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))}
                  </select>
                </div>
              )}

              {/* API Key input */}
              {provider.requires_api_key && (
                <div>
                  <label className="block text-xs font-medium text-slate-400 mb-1.5">
                    API Key
                  </label>
                  <input
                    type="password"
                    value={apiKey}
                    onChange={(e) => {
                      setApiKey(e.target.value);
                      if (connectState === "error") {
                        setConnectState("idle");
                        setErrorMsg(null);
                      }
                    }}
                    placeholder="Paste your key here"
                    autoFocus
                    className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2.5 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500 font-mono"
                  />
                </div>
              )}

              {/* Error message */}
              {connectState === "error" && errorMsg && (
                <div className="rounded-lg bg-red-900/30 border border-red-700/40 px-4 py-3 text-sm text-red-300">
                  {errorMsg}
                </div>
              )}

              {/* Connect button */}
              <button
                onClick={handleConnect}
                disabled={
                  connectState === "loading" ||
                  connectState === "success" ||
                  (provider.requires_api_key && !apiKey.trim())
                }
                className={`
                  w-full flex items-center justify-center gap-2
                  font-medium rounded-xl py-3 text-sm transition-all
                  ${connectState === "success"
                    ? "bg-emerald-500 text-white cursor-default"
                    : "bg-sky-500 hover:bg-sky-400 disabled:opacity-40 disabled:cursor-not-allowed text-white"
                  }
                `}
              >
                {connectState === "loading" && (
                  <div className="w-4 h-4 rounded-full border-2 border-white border-t-transparent animate-spin" />
                )}
                {connectState === "success" && (
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
                    <path strokeLinecap="round" strokeLinejoin="round" d="M5 13l4 4L19 7" />
                  </svg>
                )}
                {connectState === "idle" && "Connect"}
                {connectState === "loading" && "Verifying…"}
                {connectState === "success" && "Connected!"}
                {connectState === "error" && "Try Again"}
              </button>
            </div>
          )}

          {/* Non-final step: Next button */}
          {!isLastStep && (
            <button
              onClick={handleNext}
              className="w-full bg-sky-500 hover:bg-sky-400 text-white font-medium rounded-xl py-3 text-sm transition-colors"
            >
              Next
            </button>
          )}
        </div>

        {/* Step counter */}
        <p className="text-center text-xs text-slate-600">
          Step {stepIndex + 1} of {steps.length}
        </p>
      </div>
    </div>
  );
}
