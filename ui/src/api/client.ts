/**
 * Typed fetch wrappers for all Aloha API endpoints.
 * All functions throw APIError on non-2xx responses.
 */

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export class APIError extends Error {
  constructor(
    public status: number,
    message: string,
    public body?: unknown
  ) {
    super(message);
    this.name = "APIError";
  }
}

export interface HealthResponse {
  status: "ok" | "error";
  ha_connected: boolean;
  ha_version: string;
  setup_complete: boolean;
  provider: string;
}

export interface SettingsData {
  ai_provider: "anthropic" | "openai" | "gemini" | "ollama" | "openrouter" | "groq" | "custom";
  model: string;
  safety_mode: "strict" | "normal" | "permissive";
  ha_url: string;
  context_refresh_minutes: number;
  mode: "bundled" | "standalone" | "addon";
  port: number;
  ollama_url: string;
  custom_base_url: string;
  setup_complete: boolean;
  has_api_key: boolean;
  has_ha_token: boolean;
}

export type SettingsPatch = Partial<SettingsData> & {
  api_key?: string;
  ha_token?: string;
};

export interface ContextResponse {
  summary: string;
  entity_count: number;
  automation_count: number;
  last_refreshed: string;
}

export interface Session {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  message_count: number;
}

export interface SessionDetail extends Session {
  messages: Array<{
    role: "user" | "assistant" | "tool";
    content: string;
    tool_call_id?: string;
    tool_name?: string;
  }>;
}

export interface ApproveDiffRequest {
  diff_id: string;
  action: "apply" | "reject";
}

export interface ApproveDiffResponse {
  ok: boolean;
  diff_id: string;
  action: "apply" | "reject";
}

export interface ProviderInfo {
  id: "anthropic" | "openai" | "gemini" | "ollama" | "custom";
  name: string;
  requires_api_key: boolean;
  models: string[];
  default_model: string;
}

export interface TestConnectionRequest {
  provider: string;
  api_key?: string;
  model?: string;
}

export interface TestConnectionResponse {
  ok: boolean;
  model?: string;
  error?: string;
}

// ---------------------------------------------------------------------------
// Internal helpers
// ---------------------------------------------------------------------------

async function request<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const res = await fetch(path, {
    headers: {
      "Content-Type": "application/json",
      ...(init?.headers ?? {}),
    },
    ...init,
  });

  if (!res.ok) {
    let body: unknown;
    try {
      body = await res.json();
    } catch {
      body = await res.text();
    }
    const message =
      typeof body === "object" &&
      body !== null &&
      "detail" in body
        ? String((body as Record<string, unknown>).detail)
        : `HTTP ${res.status}`;
    throw new APIError(res.status, message, body);
  }

  // 204 No Content
  if (res.status === 204) {
    return undefined as unknown as T;
  }

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Health
// ---------------------------------------------------------------------------

export function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>("/health");
}

// ---------------------------------------------------------------------------
// Settings
// ---------------------------------------------------------------------------

export function getSettings(): Promise<SettingsData> {
  return request<SettingsData>("/api/settings");
}

export function updateSettings(patch: SettingsPatch): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>("/api/settings", {
    method: "POST",
    body: JSON.stringify(patch),
  });
}

// ---------------------------------------------------------------------------
// Auth / connection test
// ---------------------------------------------------------------------------

export function testConnection(
  req: TestConnectionRequest
): Promise<TestConnectionResponse> {
  return request<TestConnectionResponse>("/api/auth/test", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

// ---------------------------------------------------------------------------
// Sessions
// ---------------------------------------------------------------------------

export function getSessions(): Promise<Session[]> {
  return request<Session[]>("/api/sessions");
}

export function createSession(title?: string): Promise<Session> {
  return request<Session>("/api/sessions", {
    method: "POST",
    body: JSON.stringify({ title: title ?? "New session" }),
  });
}

export function getSession(id: string): Promise<SessionDetail> {
  return request<SessionDetail>(`/api/sessions/${id}`);
}

export function deleteSession(id: string): Promise<void> {
  return request<void>(`/api/sessions/${id}`, { method: "DELETE" });
}

// ---------------------------------------------------------------------------
// Diff approval
// ---------------------------------------------------------------------------

export function approveDiff(
  req: ApproveDiffRequest
): Promise<ApproveDiffResponse> {
  return request<ApproveDiffResponse>("/api/approve", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

// ---------------------------------------------------------------------------
// Context
// ---------------------------------------------------------------------------

export function getContext(): Promise<ContextResponse> {
  return request<ContextResponse>("/api/context");
}

export function refreshContext(): Promise<{ ok: boolean; last_refreshed: string }> {
  return request<{ ok: boolean; last_refreshed: string }>(
    "/api/context/refresh",
    { method: "POST" }
  );
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

export function getProviders(): Promise<ProviderInfo[]> {
  return request<ProviderInfo[]>("/api/providers");
}
