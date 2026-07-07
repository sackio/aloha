/**
 * ProviderPicker.tsx
 *
 * "Let Aloha be your agent" step. Leads with the recommended no-key managed
 * option (hero card), then a single simple bring-your-own-AI form below.
 * Also exports the static PROVIDERS list used across the wizard.
 */

import React from "react";
import { ProviderConfig } from "./FirstRun";
import { ByokForm } from "./ByokForm";

// ---------------------------------------------------------------------------
// Static provider definitions
// ---------------------------------------------------------------------------

export const PROVIDERS: ProviderConfig[] = [
  { id: "aloha", name: "Aloha managed", emoji: "🌺", requires_api_key: false, models: [], default_model: "" },
  {
    id: "openrouter", name: "OpenRouter", emoji: "🌐", requires_api_key: true,
    models: ["anthropic/claude-sonnet-4.6", "anthropic/claude-opus-4.8", "openai/gpt-5.1",
             "google/gemini-2.5-pro", "anthropic/claude-haiku-4.5"],
    default_model: "anthropic/claude-sonnet-4.6",
  },
  {
    id: "anthropic", name: "Claude", emoji: "🤖", requires_api_key: true,
    models: ["claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5"],
    default_model: "claude-sonnet-4-6",
  },
  {
    id: "openai", name: "OpenAI", emoji: "✨", requires_api_key: true,
    models: ["gpt-5.1", "gpt-5", "gpt-4.1", "gpt-4o-mini"], default_model: "gpt-5.1",
  },
  {
    id: "gemini", name: "Gemini", emoji: "💎", requires_api_key: true,
    models: ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
    default_model: "gemini-2.5-flash",
  },
  {
    id: "ollama", name: "Ollama", emoji: "🦙", requires_api_key: false,
    models: ["llama3.3", "llama3.1", "mistral", "gemma3", "phi4", "qwen2.5", "deepseek-r1"],
    default_model: "llama3.3",
  },
  {
    id: "groq", name: "Groq", emoji: "⚡", requires_api_key: true,
    models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
    default_model: "llama-3.3-70b-versatile",
  },
  { id: "custom", name: "Custom", emoji: "🔧", requires_api_key: false, models: [], default_model: "" },
];

// ---------------------------------------------------------------------------
// ProviderPicker
// ---------------------------------------------------------------------------

interface ProviderPickerProps {
  onSelect: (provider: ProviderConfig) => void;
  /** Called when the bring-your-own-key form finishes saving. */
  onSuccess: () => void;
}

// Hero card for the recommended, no-key managed option.
function ManagedHero({ provider, onClick }: { provider: ProviderConfig; onClick: () => void }) {
  return (
    <button
      onClick={onClick}
      className="group w-full text-left p-6 rounded-2xl transition-all hover:-translate-y-0.5"
      style={{
        background:
          "linear-gradient(#1e293b,#1e293b) padding-box, linear-gradient(105deg,#ff7d5c,#ffb866) border-box",
        border: "1.5px solid transparent",
      }}
    >
      <div className="flex items-center gap-4">
        <div className="text-4xl select-none">{provider.emoji}</div>
        <div className="flex-1">
          <div className="text-lg font-semibold text-slate-100">{provider.name}</div>
          <p className="text-sm text-slate-400">No API key — sign in and we run the AI for you.</p>
        </div>
        <span className="shrink-0 text-sky-400 group-hover:translate-x-0.5 transition-transform">→</span>
      </div>
    </button>
  );
}

export function ProviderPicker({ onSelect, onSuccess }: ProviderPickerProps) {
  const managed = PROVIDERS.find((p) => p.id === "aloha")!;

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-md space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-slate-100">Let Aloha be your agent</h1>
          <p className="text-slate-400">The easy way, or bring your own AI. Change it anytime.</p>
        </div>

        {/* Primary: managed, no key */}
        <ManagedHero provider={managed} onClick={() => onSelect(managed)} />

        {/* Secondary: bring your own AI — one simple form */}
        <div className="space-y-3">
          <div className="text-xs uppercase tracking-wide text-slate-500 text-center">
            or bring your own AI
          </div>
          <ByokForm onSuccess={onSuccess} />
        </div>
      </div>
    </div>
  );
}
