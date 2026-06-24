import React from "react";
import { useChatStore } from "../../stores/chat";

// ---------------------------------------------------------------------------
// Suggestion chip data
// ---------------------------------------------------------------------------

const SUGGESTIONS = [
  "What lights are on?",
  "Create a bedtime routine",
  "Why did an automation fail yesterday?",
  "Show all devices by area",
] as const;

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function Suggestions(): React.ReactElement {
  const sendMessage = useChatStore((s) => s.sendMessage);

  return (
    <div className="flex flex-col items-center gap-6 select-none">
      {/* Logo mark */}
      <div className="text-5xl" role="img" aria-label="Aloha">
        🌺
      </div>

      <div className="text-center space-y-1">
        <h2 className="text-xl font-semibold text-slate-100">How can I help?</h2>
        <p className="text-sm text-muted">
          Ask anything about your Home Assistant setup.
        </p>
      </div>

      {/* Suggestion chips */}
      <div className="flex flex-wrap justify-center gap-3 max-w-xl">
        {SUGGESTIONS.map((text) => (
          <button
            key={text}
            onClick={() => sendMessage(text)}
            className="
              px-4 py-2 rounded-full
              bg-surface-raised border border-surface-border
              text-sm text-slate-200
              hover:bg-sky-500/10 hover:border-sky-500/50 hover:text-sky-300
              transition-colors duration-150
              focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-900
            "
          >
            {text}
          </button>
        ))}
      </div>
    </div>
  );
}
