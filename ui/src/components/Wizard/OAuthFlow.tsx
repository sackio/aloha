/**
 * OAuthFlow.tsx
 *
 * Handles OAuth-based provider sign-in. Opens /auth/{id}/start in the same
 * tab then polls GET /health every 2s to detect when setup_complete becomes
 * true (the OAuth callback will have saved credentials by then).
 *
 * Props:
 *   provider    - the selected ProviderConfig
 *   onSuccess   - called when polling detects setup_complete=true
 *   onBack      - go back to provider picker
 *   onUseKey    - switch to KeyWizard for the same provider
 */

import React, { useCallback, useEffect, useRef, useState } from "react";
import { getHealth } from "../../api/client";
import { ProviderConfig } from "./FirstRun";

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface OAuthFlowProps {
  provider: ProviderConfig;
  onSuccess: () => void;
  onBack: () => void;
  onUseKey: () => void;
}

type OAuthState = "idle" | "polling" | "error";

export function OAuthFlow({ provider, onSuccess, onBack, onUseKey }: OAuthFlowProps) {
  const [state, setState] = useState<OAuthState>("idle");
  const [errorMsg, setErrorMsg] = useState<string | null>(null);
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const stopPoll = useCallback(() => {
    if (pollRef.current !== null) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
  }, []);

  // Clean up on unmount
  useEffect(() => () => stopPoll(), [stopPoll]);

  // ---------------------------------------------------------------------------
  // Start OAuth flow
  // ---------------------------------------------------------------------------

  function handleSignIn() {
    // Navigate to OAuth start — same tab; backend will redirect back to / when done
    window.location.href = `/auth/${provider.id}/start`;

    // Immediately start polling so when the callback returns, we detect it
    setState("polling");
    setErrorMsg(null);
    startPolling();
  }

  function startPolling() {
    stopPoll();
    pollRef.current = setInterval(async () => {
      try {
        const health = await getHealth();
        if (health.setup_complete) {
          stopPoll();
          onSuccess();
        }
      } catch {
        // Network blip — keep polling
      }
    }, 2000);
  }

  function handleCancel() {
    stopPoll();
    setState("idle");
  }

  // ---------------------------------------------------------------------------
  // Render
  // ---------------------------------------------------------------------------

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-md space-y-8">
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
          {/* Provider header */}
          <div className="flex flex-col items-center gap-3 text-center">
            <div className="text-5xl select-none">{provider.emoji}</div>
            <div>
              <h2 className="text-xl font-semibold text-slate-100">
                Sign in with {provider.name}
              </h2>
              <p className="text-sm text-slate-400 mt-1">
                You'll be redirected to {provider.name} to authorize Aloha.
              </p>
            </div>
          </div>

          {/* Error message */}
          {state === "error" && errorMsg && (
            <div className="rounded-lg bg-red-900/30 border border-red-700/40 px-4 py-3 text-sm text-red-300">
              {errorMsg}
            </div>
          )}

          {/* CTA */}
          {state === "idle" || state === "error" ? (
            <button
              onClick={handleSignIn}
              className="w-full flex items-center justify-center gap-2 bg-sky-500 hover:bg-sky-400 text-white font-medium rounded-xl py-3 text-sm transition-colors"
            >
              <span className="text-base">{provider.emoji}</span>
              Sign in with {provider.name}
            </button>
          ) : (
            /* Polling state */
            <div className="space-y-4">
              <div className="flex flex-col items-center gap-3">
                {/* Spinner */}
                <div className="relative w-10 h-10">
                  <div className="absolute inset-0 rounded-full border-4 border-slate-700" />
                  <div className="absolute inset-0 rounded-full border-4 border-sky-500 border-t-transparent animate-spin" />
                </div>
                <p className="text-sm text-slate-400">
                  Waiting for authorization
                  <span className="inline-block ml-0.5 animate-pulse">…</span>
                </p>
                <p className="text-xs text-slate-600 text-center">
                  Complete sign-in in the {provider.name} window, then return here.
                </p>
              </div>

              <button
                onClick={handleCancel}
                className="w-full text-sm text-slate-500 hover:text-slate-300 transition-colors py-2 border border-slate-700 rounded-lg"
              >
                Cancel
              </button>
            </div>
          )}

          {/* Divider */}
          <div className="flex items-center gap-3">
            <div className="flex-1 h-px bg-slate-700" />
            <span className="text-xs text-slate-600">or</span>
            <div className="flex-1 h-px bg-slate-700" />
          </div>

          {/* Use API key instead */}
          <p className="text-center text-sm text-slate-500">
            <button
              onClick={onUseKey}
              className="text-sky-400 hover:text-sky-300 underline underline-offset-2 transition-colors"
            >
              Use API key instead
            </button>
          </p>
        </div>
      </div>
    </div>
  );
}
