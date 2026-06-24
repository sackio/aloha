import { create } from "zustand";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type Provider = "anthropic" | "openai" | "gemini" | "ollama" | "custom";
export type SafetyMode = "strict" | "normal" | "permissive";
export type RuntimeMode = "bundled" | "standalone" | "addon";

export interface SettingsData {
  ai_provider: Provider;
  model: string;
  safety_mode: SafetyMode;
  ha_url: string;
  context_refresh_minutes: number;
  mode: RuntimeMode;
  port: number;
  ollama_url: string;
  custom_base_url: string;
  setup_complete: boolean;
  has_api_key: boolean;
  has_ha_token: boolean;
}

export interface SettingsUpdatePatch extends Partial<SettingsData> {
  api_key?: string;
  ha_token?: string;
}

export interface SettingsState {
  settings: SettingsData | null;
  loading: boolean;
  error: string | null;

  // Actions
  fetchSettings: () => Promise<void>;
  updateSettings: (patch: SettingsUpdatePatch) => Promise<void>;
  setSetupComplete: (complete: boolean) => Promise<void>;
}

// ---------------------------------------------------------------------------
// Store
// ---------------------------------------------------------------------------

export const useSettingsStore = create<SettingsState>((set, get) => ({
  settings: null,
  loading: false,
  error: null,

  fetchSettings: async () => {
    set({ loading: true, error: null });
    try {
      const res = await fetch("/api/settings");
      if (!res.ok) {
        throw new Error(`Failed to fetch settings: ${res.status} ${res.statusText}`);
      }
      const data: SettingsData = await res.json();
      set({ settings: data, loading: false });
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error fetching settings";
      set({ error: message, loading: false });
    }
  },

  updateSettings: async (patch: SettingsUpdatePatch) => {
    set({ loading: true, error: null });
    try {
      const res = await fetch("/api/settings", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(patch),
      });
      if (!res.ok) {
        const body = await res.text();
        throw new Error(`Failed to update settings: ${res.status} ${body}`);
      }
      // Re-fetch to get the authoritative state (server may normalise values)
      await get().fetchSettings();
    } catch (err) {
      const message = err instanceof Error ? err.message : "Unknown error updating settings";
      set({ error: message, loading: false });
      throw err;
    }
  },

  setSetupComplete: async (complete: boolean) => {
    await get().updateSettings({ setup_complete: complete });
  },
}));
