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
  ai_provider: "anthropic" | "openai" | "gemini" | "ollama" | "openrouter" | "groq" | "custom" | "aloha";
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
    // Read the body ONCE, then try to parse it as JSON. Reading the stream
    // twice (res.json() then res.text()) throws "body stream already read".
    const raw = await res.text().catch(() => "");
    let body: unknown = raw;
    try {
      body = raw ? JSON.parse(raw) : null;
    } catch {
      /* not JSON — keep the raw text */
    }
    const detail =
      typeof body === "object" && body !== null && "detail" in body
        ? (body as Record<string, unknown>).detail
        : undefined;
    const message = detail
      ? (typeof detail === "string" ? detail : JSON.stringify(detail))
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

// ---------------------------------------------------------------------------
// Skills
// ---------------------------------------------------------------------------

export interface SkillInfo {
  name: string;
  category: string;
  description: string;
  editable: boolean;
  url: string;
}

export function getSkills(): Promise<SkillInfo[]> {
  return request<SkillInfo[]>("/api/skills");
}

export async function getSkillMarkdown(name: string): Promise<string> {
  const res = await fetch(`/api/skills/${encodeURIComponent(name)}`);
  if (!res.ok) throw new APIError(res.status, `HTTP ${res.status}`);
  return res.text();
}

export function addSkill(name: string, content: string): Promise<{ ok: boolean; name: string }> {
  return request<{ ok: boolean; name: string }>("/api/skills", {
    method: "POST",
    body: JSON.stringify({ name, content }),
  });
}

export function deleteSkill(name: string): Promise<{ ok: boolean }> {
  return request<{ ok: boolean }>(`/api/skills/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}

// ---------------------------------------------------------------------------
// Public MCP URL (relay / cloudflared / ngrok tunnels)
// ---------------------------------------------------------------------------

export interface PublicUrlStatus {
  provider: "none" | "relay" | "cloudflared" | "ngrok";
  url: string;
  online: boolean;
  error: string;
}

export function getPublicUrl(): Promise<PublicUrlStatus> {
  return request<PublicUrlStatus>("/api/public-url");
}

export function setPublicUrl(
  provider: "relay" | "cloudflared" | "ngrok",
  ngrok_authtoken?: string,
): Promise<PublicUrlStatus> {
  return request<PublicUrlStatus>("/api/public-url", {
    method: "POST",
    body: JSON.stringify({ provider, ngrok_authtoken }),
  });
}

export function disablePublicUrl(): Promise<PublicUrlStatus> {
  return request<PublicUrlStatus>("/api/public-url/disable", { method: "POST" });
}

// ---------------------------------------------------------------------------
// Aloha relay account ($1/mo tunnel subscription)
// ---------------------------------------------------------------------------

export interface RelayStatus { has_account: boolean; entitled: boolean }

export function relayStatus(): Promise<RelayStatus> {
  return request<RelayStatus>("/api/relay/status");
}

export function relaySignup(email: string, password: string): Promise<{ ok: boolean }> {
  return request("/api/relay/signup", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function relayLogin(email: string, password: string): Promise<{ ok: boolean }> {
  return request("/api/relay/login", { method: "POST", body: JSON.stringify({ email, password }) });
}

export function relaySubscribe(): Promise<{ url: string }> {
  return request<{ url: string }>("/api/relay/subscribe", { method: "POST" });
}

// ---------------------------------------------------------------------------
// MCP access keys (Authorization: Bearer <secret> on /mcp)
// ---------------------------------------------------------------------------

export interface McpKey { key: string; name: string; created_at: string; secret_prefix: string }
export interface McpCred { key: string; secret: string; name?: string }

export function getMcpKeys(): Promise<McpKey[]> {
  return request<McpKey[]>("/api/mcp-keys");
}

export function mintMcpKey(name: string): Promise<McpCred> {
  return request<McpCred>("/api/mcp-keys", { method: "POST", body: JSON.stringify({ name }) });
}

export function regenMcpKey(key: string): Promise<McpCred> {
  return request<McpCred>(`/api/mcp-keys/${encodeURIComponent(key)}/regenerate`, { method: "POST" });
}

export function deleteMcpKey(key: string): Promise<{ ok: boolean }> {
  return request(`/api/mcp-keys/${encodeURIComponent(key)}`, { method: "DELETE" });
}
