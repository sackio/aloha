import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface PendingDiff {
  id: string;
  path: string;
  before: string;
  after: string;
  content: string;
  status: "pending" | "applied" | "rejected";
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "tool";
  content: string;
  tool_call?: {
    id: string;
    name: string;
    args: Record<string, unknown>;
    result?: string;
    error?: boolean;
  };
  pending_diff?: PendingDiff;
  created_at: string;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

// ---------------------------------------------------------------------------
// SSE event shapes (discriminated union on `type`)
// ---------------------------------------------------------------------------

interface ContentEvent {
  type: "content";
  delta: string;
}

interface ToolCallEvent {
  type: "tool_call";
  id: string;
  name: string;
  args: Record<string, unknown>;
}

interface ToolResultEvent {
  type: "tool_result";
  id: string;
  name: string;
  result: string;
  error: boolean;
}

interface DiffEvent {
  type: "diff";
  id: string;
  path: string;
  before: string;
  after: string;
  content: string;
}

interface DoneEvent {
  type: "done";
  usage?: Record<string, number>;
}

interface ErrorEvent {
  type: "error";
  message: string;
  code?: string;
}

type SSEEvent =
  | ContentEvent
  | ToolCallEvent
  | ToolResultEvent
  | DiffEvent
  | DoneEvent
  | ErrorEvent;

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function generateId(prefix: string): string {
  const hex = Array.from(crypto.getRandomValues(new Uint8Array(8)))
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
  return `${prefix}${hex}`;
}

function now(): string {
  return new Date().toISOString();
}

// ---------------------------------------------------------------------------
// Store state & actions
// ---------------------------------------------------------------------------

export interface ChatState {
  sessions: Session[];
  activeSessionId: string | null;
  messages: ChatMessage[];
  streaming: boolean;
  error: string | null;

  // Internal — not exposed in public interface
  _abortController: AbortController | null;

  // Actions
  fetchSessions: () => Promise<void>;
  createSession: (title?: string) => Promise<string>;
  selectSession: (id: string) => Promise<void>;
  deleteSession: (id: string) => Promise<void>;
  sendMessage: (content: string) => Promise<void>;
  approveDiff: (diffId: string, action: "apply" | "reject") => Promise<void>;
  cancelStream: () => void;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useChatStore = create<ChatState>((set, get) => ({
  sessions: [],
  activeSessionId: null,
  messages: [],
  streaming: false,
  error: null,
  _abortController: null,

  // -------------------------------------------------------------------------
  // fetchSessions
  // -------------------------------------------------------------------------
  fetchSessions: async () => {
    try {
      const res = await fetch("/api/sessions");
      if (!res.ok) {
        throw new Error(`Failed to fetch sessions: ${res.status}`);
      }
      const data: Session[] = await res.json();
      set({ sessions: data });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error fetching sessions";
      set({ error: message });
    }
  },

  // -------------------------------------------------------------------------
  // createSession
  // -------------------------------------------------------------------------
  createSession: async (title = "New session") => {
    const res = await fetch("/api/sessions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    });
    if (!res.ok) {
      throw new Error(`Failed to create session: ${res.status}`);
    }
    const session: Session = await res.json();
    set((state) => ({
      sessions: [session, ...state.sessions],
      activeSessionId: session.id,
      messages: [],
    }));
    return session.id;
  },

  // -------------------------------------------------------------------------
  // selectSession
  // -------------------------------------------------------------------------
  selectSession: async (id: string) => {
    try {
      const res = await fetch(`/api/sessions/${id}`);
      if (!res.ok) {
        throw new Error(`Failed to load session: ${res.status}`);
      }
      const data = await res.json();
      // Server returns { id, title, created_at, updated_at, messages: [...] }
      const rawMessages: Array<{
        role: "user" | "assistant" | "tool";
        content: string;
        tool_call_id?: string;
        tool_name?: string;
      }> = data.messages ?? [];

      const messages: ChatMessage[] = rawMessages.map((m) => ({
        id: generateId("msg_"),
        role: m.role,
        content: m.content,
        created_at: now(),
      }));

      set({ activeSessionId: id, messages, error: null });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error loading session";
      set({ error: message });
    }
  },

  // -------------------------------------------------------------------------
  // deleteSession
  // -------------------------------------------------------------------------
  deleteSession: async (id: string) => {
    const res = await fetch(`/api/sessions/${id}`, { method: "DELETE" });
    if (!res.ok && res.status !== 204) {
      throw new Error(`Failed to delete session: ${res.status}`);
    }
    set((state) => {
      const sessions = state.sessions.filter((s) => s.id !== id);
      const activeSessionId =
        state.activeSessionId === id
          ? (sessions[0]?.id ?? null)
          : state.activeSessionId;
      const messages = state.activeSessionId === id ? [] : state.messages;
      return { sessions, activeSessionId, messages };
    });
  },

  // -------------------------------------------------------------------------
  // sendMessage
  // -------------------------------------------------------------------------
  sendMessage: async (content: string) => {
    const { activeSessionId } = get();
    if (!activeSessionId) {
      set({ error: "No active session. Create a session before sending a message." });
      return;
    }

    // Cancel any in-flight stream
    get().cancelStream();

    // Optimistically append user message and an empty streaming assistant message
    const userMsg: ChatMessage = {
      id: generateId("msg_"),
      role: "user",
      content,
      created_at: now(),
    };
    const assistantMsgId = generateId("msg_");
    const assistantMsg: ChatMessage = {
      id: assistantMsgId,
      role: "assistant",
      content: "",
      created_at: now(),
    };

    set((state) => ({
      messages: [...state.messages, userMsg, assistantMsg],
      streaming: true,
      error: null,
    }));

    const controller = new AbortController();
    set({ _abortController: controller });

    try {
      const res = await fetch("/api/chat", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: activeSessionId, message: content }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Chat request failed: ${res.status} ${body}`);
      }

      if (!res.body) {
        throw new Error("Response body is null — SSE stream unavailable");
      }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });

        // Split on SSE double-newline boundaries
        const parts = buffer.split("\n\n");
        // The last part may be incomplete; keep it in the buffer
        buffer = parts.pop() ?? "";

        for (const part of parts) {
          const trimmed = part.trim();
          if (!trimmed) continue;

          // Each SSE message may have multiple lines; we care about `data:` lines
          for (const line of trimmed.split("\n")) {
            if (!line.startsWith("data:")) continue;
            const jsonStr = line.slice(5).trim();
            if (!jsonStr) continue;

            let event: SSEEvent;
            try {
              event = JSON.parse(jsonStr) as SSEEvent;
            } catch {
              // Malformed JSON — skip
              continue;
            }

            // Dispatch on event type
            switch (event.type) {
              case "content": {
                // Append delta to the streaming assistant message
                set((state) => ({
                  messages: state.messages.map((m) =>
                    m.id === assistantMsgId
                      ? { ...m, content: m.content + event.delta }
                      : m
                  ),
                }));
                break;
              }

              case "tool_call": {
                // Insert a dedicated tool-call message
                const toolMsg: ChatMessage = {
                  id: generateId("msg_"),
                  role: "tool",
                  content: "",
                  tool_call: {
                    id: event.id,
                    name: event.name,
                    args: event.args,
                  },
                  created_at: now(),
                };
                // Insert before the streaming assistant message so the order is
                // user → tool_call → assistant
                set((state) => {
                  const idx = state.messages.findIndex((m) => m.id === assistantMsgId);
                  const msgs = [...state.messages];
                  msgs.splice(idx, 0, toolMsg);
                  return { messages: msgs };
                });
                break;
              }

              case "tool_result": {
                // Find the matching tool_call message by tool_call.id and patch it
                set((state) => ({
                  messages: state.messages.map((m) => {
                    if (m.role === "tool" && m.tool_call?.id === event.id) {
                      return {
                        ...m,
                        tool_call: {
                          ...m.tool_call!,
                          result: event.result,
                          error: event.error,
                        },
                      };
                    }
                    return m;
                  }),
                }));
                break;
              }

              case "diff": {
                const pendingDiff: PendingDiff = {
                  id: event.id,
                  path: event.path,
                  before: event.before,
                  after: event.after,
                  content: event.content,
                  status: "pending",
                };
                // Attach the diff to the current assistant message
                set((state) => ({
                  messages: state.messages.map((m) =>
                    m.id === assistantMsgId ? { ...m, pending_diff: pendingDiff } : m
                  ),
                }));
                break;
              }

              case "done": {
                // Finalise: mark the assistant message as no longer streaming
                set((state) => ({
                  messages: state.messages.map((m) =>
                    m.id === assistantMsgId ? { ...m } : m
                  ),
                  streaming: false,
                  _abortController: null,
                }));
                break;
              }

              case "error": {
                set((state) => ({
                  messages: state.messages.map((m) =>
                    m.id === assistantMsgId
                      ? { ...m, content: m.content || `Error: ${event.message}` }
                      : m
                  ),
                  error: event.message,
                  streaming: false,
                  _abortController: null,
                }));
                break;
              }
            }
          }
        }
      }
    } catch (err) {
      if ((err as Error).name === "AbortError") {
        // Cancelled intentionally — leave messages as-is
        set({ streaming: false, _abortController: null });
        return;
      }
      const message = err instanceof Error ? err.message : "Unknown error during chat";
      set((state) => ({
        messages: state.messages.map((m) =>
          m.id === assistantMsgId
            ? { ...m, content: m.content || `Error: ${message}` }
            : m
        ),
        error: message,
        streaming: false,
        _abortController: null,
      }));
    }
  },

  // -------------------------------------------------------------------------
  // approveDiff
  // -------------------------------------------------------------------------
  approveDiff: async (diffId: string, action: "apply" | "reject") => {
    const res = await fetch("/api/approve", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ diff_id: diffId, action }),
    });
    if (!res.ok) {
      const body = await res.text();
      throw new Error(`Failed to ${action} diff: ${res.status} ${body}`);
    }
    // Update the diff status in any message that holds it
    set((state) => ({
      messages: state.messages.map((m) => {
        if (m.pending_diff?.id === diffId) {
          return {
            ...m,
            pending_diff: {
              ...m.pending_diff,
              status: action === "apply" ? "applied" : "rejected",
            },
          };
        }
        return m;
      }),
    }));
  },

  // -------------------------------------------------------------------------
  // cancelStream
  // -------------------------------------------------------------------------
  cancelStream: () => {
    const { _abortController } = get();
    if (_abortController) {
      _abortController.abort();
    }
    set({ streaming: false, _abortController: null });
  },
}));
