import React, { useRef, useEffect, KeyboardEvent } from "react";
import { useChatStore } from "../../stores/chat";

// ---------------------------------------------------------------------------
// Mode toggle
// ---------------------------------------------------------------------------

type ChatMode = "supervised" | "autonomous";

interface ModeToggleProps {
  mode: ChatMode;
  onChange: (mode: ChatMode) => void;
}

function ModeToggle({ mode, onChange }: ModeToggleProps) {
  return (
    <div
      className="
        inline-flex rounded-full border border-surface-border
        bg-slate-800 text-xs font-medium overflow-hidden
        shrink-0
      "
      role="group"
      aria-label="Interaction mode"
    >
      <button
        onClick={() => onChange("supervised")}
        className={`
          px-3 py-1 transition-colors duration-150 focus:outline-none
          ${mode === "supervised"
            ? "bg-sky-600 text-white"
            : "text-slate-400 hover:text-slate-200"
          }
        `}
      >
        Supervised
      </button>
      <button
        onClick={() => onChange("autonomous")}
        className={`
          px-3 py-1 transition-colors duration-150 focus:outline-none
          ${mode === "autonomous"
            ? "bg-sky-600 text-white"
            : "text-slate-400 hover:text-slate-200"
          }
        `}
      >
        Autonomous
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Send icon
// ---------------------------------------------------------------------------

function SendIcon() {
  return (
    <svg
      className="w-4 h-4"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={2}
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <line x1="22" y1="2" x2="11" y2="13" />
      <polygon points="22 2 15 22 11 13 2 9 22 2" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Stop icon
// ---------------------------------------------------------------------------

function StopIcon() {
  return (
    <svg className="w-4 h-4" viewBox="0 0 24 24" fill="currentColor">
      <rect x="4" y="4" width="16" height="16" rx="2" />
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Main InputBar component
// ---------------------------------------------------------------------------

export function InputBar(): React.ReactElement {
  const sendMessage = useChatStore((s) => s.sendMessage);
  const cancelStream = useChatStore((s) => s.cancelStream);
  const streaming = useChatStore((s) => s.streaming);
  const activeSessionId = useChatStore((s) => s.activeSessionId);

  const [value, setValue] = React.useState("");
  const [mode, setMode] = React.useState<ChatMode>("supervised");
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  // Auto-resize textarea — min 1 row, max 5 rows
  useEffect(() => {
    const el = textareaRef.current;
    if (!el) return;
    el.style.height = "auto";
    const lineHeight = 24; // px per row (matches leading-6 in Tailwind)
    const maxHeight = lineHeight * 5 + 16; // 5 rows + padding
    el.style.height = `${Math.min(el.scrollHeight, maxHeight)}px`;
  }, [value]);

  // Focus on session change
  useEffect(() => {
    textareaRef.current?.focus();
  }, [activeSessionId]);

  function handleSubmit() {
    const trimmed = value.trim();
    if (!trimmed || streaming || !activeSessionId) return;
    setValue("");
    sendMessage(trimmed);
  }

  function handleKeyDown(e: KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
    // Shift+Enter — allow natural textarea newline
  }

  const disabled = !activeSessionId;
  const canSend = value.trim().length > 0 && !streaming && !disabled;

  return (
    <div className="border-t border-surface-border bg-slate-900 px-4 py-3">
      <div
        className="
          flex items-end gap-2
          bg-surface rounded-xl border border-surface-border
          px-3 py-2
          focus-within:border-sky-500/50 focus-within:ring-1 focus-within:ring-sky-500/20
          transition-shadow duration-150
        "
      >
        {/* Mode toggle — aligned to bottom left */}
        <div className="pb-0.5">
          <ModeToggle mode={mode} onChange={setMode} />
        </div>

        {/* Textarea */}
        <textarea
          ref={textareaRef}
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={
            disabled
              ? "Select or create a session to start chatting…"
              : "Ask about your home…"
          }
          disabled={disabled}
          rows={1}
          className="
            flex-1 resize-none bg-transparent outline-none
            text-sm text-slate-100 placeholder-slate-500
            leading-6 py-0.5
            disabled:cursor-not-allowed disabled:opacity-40
            min-h-[24px] max-h-[120px]
            scrollbar-thin scrollbar-thumb-slate-600
          "
          style={{ overflowY: "auto" }}
          aria-label="Chat input"
        />

        {/* Send / Stop button */}
        {streaming ? (
          <button
            onClick={cancelStream}
            className="
              shrink-0 p-2 rounded-lg
              bg-red-600/20 border border-red-500/40 text-red-400
              hover:bg-red-600/30 hover:border-red-500/60
              transition-colors duration-150
              focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-slate-800
            "
            aria-label="Stop generation"
            title="Stop generation"
          >
            <StopIcon />
          </button>
        ) : (
          <button
            onClick={handleSubmit}
            disabled={!canSend}
            className="
              shrink-0 p-2 rounded-lg
              bg-sky-600 text-white
              hover:bg-sky-500
              disabled:opacity-30 disabled:cursor-not-allowed
              transition-colors duration-150
              focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-800
            "
            aria-label="Send message"
            title="Send message (Enter)"
          >
            <SendIcon />
          </button>
        )}
      </div>

      {/* Hint text */}
      <p className="mt-1.5 text-center text-xs text-slate-600">
        Enter to send · Shift+Enter for newline
      </p>
    </div>
  );
}
