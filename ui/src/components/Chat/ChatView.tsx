import React, { useEffect, useRef } from "react";
import { useChatStore } from "../../stores/chat";
import { Message } from "./Message";
import { InputBar } from "./InputBar";
import { Suggestions } from "./Suggestions";
import { DiffPanel } from "./DiffPanel";

// ---------------------------------------------------------------------------
// Typing indicator
// ---------------------------------------------------------------------------

function TypingIndicator() {
  return (
    <div className="px-4 py-2 flex items-center gap-1" aria-label="Assistant is typing">
      {[0, 1, 2].map((i) => (
        <span
          key={i}
          className="w-2 h-2 rounded-full bg-sky-500/70 animate-bounce"
          style={{ animationDelay: `${i * 150}ms`, animationDuration: "0.9s" }}
        />
      ))}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main ChatView
// ---------------------------------------------------------------------------

export function ChatView(): React.ReactElement {
  const { fetchSessions, createSession, activeSessionId, messages, streaming } = useChatStore();
  const bottomRef = useRef<HTMLDivElement>(null);

  // On mount: load sessions and ensure there's an active one
  useEffect(() => {
    async function init() {
      await fetchSessions();
      const { sessions, activeSessionId: currentActive } = useChatStore.getState();
      if (!currentActive) {
        if (sessions.length > 0) {
          // Sessions exist but none is active — select most recent
          await useChatStore.getState().selectSession(sessions[0].id);
        } else {
          await createSession();
        }
      }
    }
    init();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // Auto-scroll to bottom when messages or streaming state changes
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, streaming]);

  // Find the first message with a pending diff (status === "pending")
  const pendingDiffMessage = messages.find(
    (m) => m.pending_diff?.status === "pending"
  );

  const showEmpty = messages.length === 0 && !streaming;
  const showTyping = streaming && messages.length > 0;

  // For streaming: the last assistant message is streaming
  const streamingMsgId = streaming
    ? [...messages].reverse().find((m) => m.role === "assistant")?.id
    : undefined;

  return (
    <div className="flex flex-col h-full relative">
      {/* Messages area */}
      <div className="flex-1 overflow-y-auto py-4 space-y-1">
        {showEmpty ? (
          <div className="h-full flex items-center justify-center">
            <Suggestions />
          </div>
        ) : (
          <>
            {messages.map((msg) => (
              <Message
                key={msg.id}
                message={msg}
                isStreaming={streaming && msg.id === streamingMsgId}
              />
            ))}

            {/* Typing indicator: shown when streaming but the assistant message content is empty */}
            {showTyping && streamingMsgId === undefined && <TypingIndicator />}
          </>
        )}

        {/* Scroll anchor */}
        <div ref={bottomRef} />
      </div>

      {/* Input bar */}
      <InputBar />

      {/* Diff overlay — rendered on top of everything when there's a pending diff */}
      {pendingDiffMessage?.pending_diff && (
        <DiffPanel diff={pendingDiffMessage.pending_diff} />
      )}
    </div>
  );
}
