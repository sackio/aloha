/**
 * ProviderPicker.tsx
 *
 * Step 1 of the first-run wizard. Shows a 3x2 grid of provider cards.
 * Each card has: large emoji, name, tagline, auth badge.
 * A "I already have a key" text link at the bottom reveals a plain
 * API-key input for ad-hoc provider entry.
 */

import React, { useState } from "react";
import { ProviderConfig } from "./FirstRun";

// ---------------------------------------------------------------------------
// Static provider definitions
// ---------------------------------------------------------------------------

export const PROVIDERS: ProviderConfig[] = [
  {
    id: "aloha",
    name: "Aloha managed",
    emoji: "🌺",
    tagline: "Recommended — no API key, we run it for you",
    authBadge: "managed",
    recommended: true,
    requires_api_key: false,
    models: [],
    default_model: "",
    steps: [],
  },
  {
    id: "openrouter",
    name: "OpenRouter",
    emoji: "🌐",
    tagline: "One key, every model",
    authBadge: "key",
    requires_api_key: true,
    models: [
      "anthropic/claude-sonnet-4.6",
      "anthropic/claude-opus-4.8",
      "openai/gpt-5.1",
      "google/gemini-2.5-pro",
      "anthropic/claude-haiku-4.5",
    ],
    default_model: "anthropic/claude-sonnet-4.6",
    steps: [
      {
        title: "Create an OpenRouter account",
        instruction: "Sign up free at openrouter.ai — one account, access to Claude, GPT, Gemini and more.",
        url: "https://openrouter.ai/",
      },
      {
        title: "Generate an API key",
        instruction:
          'Go to Keys and click "Create Key", then add a few dollars of credit to enable paid models.',
        url: "https://openrouter.ai/keys",
      },
      {
        title: "Enter your API key",
        instruction: "Paste the key below. It starts with sk-or-.",
      },
    ],
  },
  {
    id: "anthropic",
    name: "Claude",
    emoji: "🤖",
    tagline: "Best reasoning, direct from Anthropic",
    authBadge: "key",
    requires_api_key: true,
    models: ["claude-sonnet-4-6", "claude-opus-4-8", "claude-haiku-4-5"],
    default_model: "claude-sonnet-4-6",
    steps: [
      {
        title: "Create an Anthropic account",
        instruction: "Sign up at console.anthropic.com if you don't already have an account.",
        url: "https://console.anthropic.com/",
      },
      {
        title: "Generate an API key",
        instruction:
          'In the Anthropic console, navigate to "API Keys" and click "Create Key". Give it any name.',
        url: "https://console.anthropic.com/settings/keys",
      },
      {
        title: "Enter your API key",
        instruction: "Paste the key below. It starts with sk-ant-.",
      },
    ],
  },
  {
    id: "openai",
    name: "OpenAI",
    emoji: "✨",
    tagline: "GPT-5.1 — industry standard",
    authBadge: "key",
    requires_api_key: true,
    models: ["gpt-5.1", "gpt-5", "gpt-4.1", "gpt-4o-mini"],
    default_model: "gpt-5.1",
    steps: [
      {
        title: "Create an OpenAI account",
        instruction: "Sign up at platform.openai.com if you don't already have one.",
        url: "https://platform.openai.com/",
      },
      {
        title: "Generate an API key",
        instruction: 'Go to API Keys and click "Create new secret key".',
        url: "https://platform.openai.com/api-keys",
      },
      {
        title: "Enter your API key",
        instruction: "Paste the key below. It starts with sk-.",
      },
    ],
  },
  {
    id: "gemini",
    name: "Gemini",
    emoji: "💎",
    tagline: "Free tier available",
    authBadge: "key",
    requires_api_key: true,
    models: ["gemini-2.5-pro", "gemini-2.5-flash", "gemini-2.0-flash"],
    default_model: "gemini-2.5-flash",
    steps: [
      {
        title: "Open Google AI Studio",
        instruction: "Sign in with your Google account at aistudio.google.com.",
        url: "https://aistudio.google.com/",
      },
      {
        title: "Create an API key",
        instruction: 'Click "Get API key" then "Create API key in new project".',
        url: "https://aistudio.google.com/app/apikey",
      },
      {
        title: "Enter your API key",
        instruction: "Paste the Gemini API key below.",
      },
    ],
  },
  {
    id: "ollama",
    name: "Ollama",
    emoji: "🦙",
    tagline: "100% local, no account needed",
    authBadge: "local",
    requires_api_key: false,
    models: [
      "llama3.3",
      "llama3.1",
      "mistral",
      "gemma3",
      "phi4",
      "qwen2.5",
      "deepseek-r1",
    ],
    default_model: "llama3.3",
    steps: [],
  },
  {
    id: "groq",
    name: "Groq",
    emoji: "⚡",
    tagline: "Blazing-fast, free tier",
    authBadge: "key",
    requires_api_key: true,
    models: ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
    default_model: "llama-3.3-70b-versatile",
    steps: [
      {
        title: "Create a Groq account",
        instruction: "Sign up free at console.groq.com.",
        url: "https://console.groq.com/",
      },
      {
        title: "Create an API key",
        instruction: 'Go to API Keys and click "Create API Key".',
        url: "https://console.groq.com/keys",
      },
      {
        title: "Enter your API key",
        instruction: "Paste the key below.",
      },
    ],
  },
  {
    id: "custom",
    name: "Custom",
    emoji: "🔧",
    tagline: "Any OpenAI-compatible endpoint",
    authBadge: "key",
    requires_api_key: false,
    models: [],
    default_model: "",
    steps: [
      {
        title: "Enter your endpoint URL",
        instruction:
          "Provide the base URL of your OpenAI-compatible API (e.g. http://localhost:8080/v1).",
      },
      {
        title: "Enter your API key",
        instruction: "If your endpoint requires a key, paste it below. Otherwise leave blank.",
      },
    ],
  },
];

// ---------------------------------------------------------------------------
// Auth badge component
// ---------------------------------------------------------------------------

function AuthBadge({ badge }: { badge: ProviderConfig["authBadge"] }) {
  const variants = {
    oauth: "bg-emerald-500/20 text-emerald-300 border border-emerald-500/30",
    key: "bg-sky-500/20 text-sky-300 border border-sky-500/30",
    local: "bg-violet-500/20 text-violet-300 border border-violet-500/30",
    managed: "bg-amber-500/20 text-amber-300 border border-amber-500/30",
  };
  const labels = { oauth: "OAuth", key: "API Key", local: "Local", managed: "Hosted" };

  return (
    <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${variants[badge]}`}>
      {labels[badge]}
    </span>
  );
}

// ---------------------------------------------------------------------------
// Provider card
// ---------------------------------------------------------------------------

function ProviderCard({
  provider,
  onClick,
}: {
  provider: ProviderConfig;
  onClick: () => void;
}) {
  const [hovered, setHovered] = useState(false);

  return (
    <button
      onClick={onClick}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`
        relative flex flex-col items-start gap-3 p-5 rounded-xl text-left
        bg-slate-800 border transition-all duration-150 cursor-pointer
        ${hovered || provider.recommended
          ? "border-sky-500 shadow-[0_0_0_2px_rgba(14,165,233,0.25)]"
          : "border-slate-700"
        }
      `}
    >
      {provider.recommended && (
        <span className="absolute -top-2 left-4 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-sky-500 text-white">
          ★ Recommended
        </span>
      )}
      <div className="text-4xl select-none">{provider.emoji}</div>
      <div className="flex-1 space-y-1">
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-base font-semibold text-slate-100">
            {provider.name}
          </span>
          <AuthBadge badge={provider.authBadge} />
        </div>
        <p className="text-sm text-slate-400">{provider.tagline}</p>
      </div>
    </button>
  );
}

// ---------------------------------------------------------------------------
// Quick-key input (revealed by "I already have a key" link)
// ---------------------------------------------------------------------------

function QuickKeyEntry({
  onConfirm,
  onClose,
}: {
  onConfirm: (provider: ProviderConfig, key: string) => void;
  onClose: () => void;
}) {
  const [selectedId, setSelectedId] = useState<ProviderConfig["id"]>("anthropic");
  const [key, setKey] = useState("");

  const keyProviders = PROVIDERS.filter((p) => p.requires_api_key);

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    const provider = PROVIDERS.find((p) => p.id === selectedId)!;
    onConfirm(provider, key.trim());
  }

  return (
    <div className="mt-6 p-5 rounded-xl bg-slate-800 border border-slate-700 space-y-4">
      <div className="flex items-center justify-between">
        <p className="text-sm font-medium text-slate-200">
          Connect with an existing API key
        </p>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-slate-300 transition-colors text-sm"
        >
          Cancel
        </button>
      </div>

      <form onSubmit={handleSubmit} className="space-y-3">
        <div>
          <label className="block text-xs text-slate-400 mb-1">Provider</label>
          <select
            value={selectedId}
            onChange={(e) =>
              setSelectedId(e.target.value as ProviderConfig["id"])
            }
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 focus:outline-none focus:ring-2 focus:ring-sky-500"
          >
            {keyProviders.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
        </div>

        <div>
          <label className="block text-xs text-slate-400 mb-1">API Key</label>
          <input
            type="password"
            value={key}
            onChange={(e) => setKey(e.target.value)}
            placeholder="sk-..."
            autoFocus
            className="w-full bg-slate-900 border border-slate-700 rounded-lg px-3 py-2 text-sm text-slate-100 placeholder-slate-600 focus:outline-none focus:ring-2 focus:ring-sky-500"
          />
        </div>

        <button
          type="submit"
          disabled={!key.trim()}
          className="w-full bg-sky-500 hover:bg-sky-400 disabled:opacity-40 disabled:cursor-not-allowed text-white font-medium rounded-lg py-2 text-sm transition-colors"
        >
          Connect
        </button>
      </form>
    </div>
  );
}

// ---------------------------------------------------------------------------
// ProviderPicker
// ---------------------------------------------------------------------------

interface ProviderPickerProps {
  onSelect: (provider: ProviderConfig, forceKey?: boolean) => void;
}

export function ProviderPicker({ onSelect }: ProviderPickerProps) {
  const [showQuickKey, setShowQuickKey] = useState(false);

  function handleQuickKeyConfirm(provider: ProviderConfig) {
    onSelect(provider, true);
  }

  return (
    <div className="min-h-screen bg-slate-900 flex flex-col items-center justify-center px-6 py-16">
      <div className="w-full max-w-2xl space-y-8">
        {/* Header */}
        <div className="text-center space-y-2">
          <h1 className="text-3xl font-bold text-slate-100">
            Welcome to{" "}
            <span className="text-sky-400">Aloha</span>
          </h1>
          <p className="text-slate-400">
            Choose your AI provider to get started. You can change this later.
          </p>
        </div>

        {/* Provider grid — 3 columns, 2 rows */}
        <div className="grid grid-cols-3 gap-4">
          {PROVIDERS.map((provider) => (
            <ProviderCard
              key={provider.id}
              provider={provider}
              onClick={() => onSelect(provider)}
            />
          ))}
        </div>

        {/* Quick-key link / inline form */}
        {showQuickKey ? (
          <QuickKeyEntry
            onConfirm={handleQuickKeyConfirm}
            onClose={() => setShowQuickKey(false)}
          />
        ) : (
          <div className="text-center">
            <button
              onClick={() => setShowQuickKey(true)}
              className="text-sm text-slate-500 hover:text-sky-400 underline underline-offset-2 transition-colors"
            >
              I already have a key
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
