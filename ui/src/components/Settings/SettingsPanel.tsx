import React, { useEffect, useState } from "react";
import { useSettingsStore } from "../../stores/settings";
import { getProviders, ProviderInfo } from "../../api/client";

// ---------------------------------------------------------------------------
// Section heading
// ---------------------------------------------------------------------------

function SectionHeading({ children }: { children: React.ReactNode }) {
  return (
    <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-3">
      {children}
    </h3>
  );
}

// ---------------------------------------------------------------------------
// SettingsPanel
// ---------------------------------------------------------------------------

interface SettingsPanelProps {
  onClose: () => void;
}

export function SettingsPanel({ onClose }: SettingsPanelProps): React.ReactElement {
  const { settings, loading, updateSettings } = useSettingsStore();
  const [providers, setProviders] = useState<ProviderInfo[]>([]);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);
  const [savedOk, setSavedOk] = useState(false);

  // Local editable copies
  const [model, setModel] = useState(settings?.model ?? "auto");
  const [safetyMode, setSafetyMode] = useState(settings?.safety_mode ?? "normal");
  const [contextRefresh, setContextRefresh] = useState(
    settings?.context_refresh_minutes ?? 5
  );

  useEffect(() => {
    if (settings) {
      setModel(settings.model);
      setSafetyMode(settings.safety_mode);
      setContextRefresh(settings.context_refresh_minutes);
    }
  }, [settings]);

  useEffect(() => {
    getProviders()
      .then(setProviders)
      .catch(() => {/* silently ignore */});
  }, []);

  const currentProvider = providers.find((p) => p.id === settings?.ai_provider);
  const availableModels = currentProvider?.models ?? [];

  async function handleSave() {
    setSaving(true);
    setSaveError(null);
    setSavedOk(false);
    try {
      await updateSettings({
        model,
        safety_mode: safetyMode as "strict" | "normal" | "permissive",
        context_refresh_minutes: contextRefresh,
      });
      setSavedOk(true);
      setTimeout(() => setSavedOk(false), 2000);
    } catch (err) {
      setSaveError(err instanceof Error ? err.message : "Failed to save");
    } finally {
      setSaving(false);
    }
  }

  return (
    // Modal backdrop
    <div
      className="fixed inset-0 z-40 flex items-end sm:items-center justify-center bg-black/60 backdrop-blur-sm"
      onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
      role="dialog"
      aria-modal="true"
      aria-label="Settings"
    >
      <div className="
        w-full sm:w-[480px] max-h-[85vh] flex flex-col
        bg-surface border border-surface-border rounded-t-2xl sm:rounded-2xl
        shadow-2xl overflow-hidden
      ">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-surface-border shrink-0">
          <h2 className="text-base font-semibold text-slate-100">Settings</h2>
          <button
            onClick={onClose}
            className="
              text-slate-500 hover:text-slate-300 transition-colors
              focus:outline-none focus:ring-1 focus:ring-slate-500 rounded p-1
            "
            aria-label="Close settings"
          >
            <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Scrollable content */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-6">
          {loading && !settings ? (
            <div className="flex items-center justify-center py-8">
              <div className="w-5 h-5 rounded-full border-2 border-sky-500/30 border-t-sky-500 animate-spin" />
            </div>
          ) : (
            <>
              {/* AI Provider section */}
              <section>
                <SectionHeading>AI Provider</SectionHeading>
                <div className="flex items-center justify-between rounded-lg bg-slate-800/60 border border-surface-border px-4 py-3">
                  <div className="flex items-center gap-2">
                    <span className="w-2 h-2 rounded-full bg-emerald-500 shrink-0" />
                    <span className="text-sm text-slate-200 font-medium">
                      {currentProvider?.name ?? settings?.ai_provider ?? "—"}
                    </span>
                    {settings?.has_api_key && (
                      <span className="text-xs text-slate-500">· key stored</span>
                    )}
                  </div>
                  <button
                    onClick={() => {
                      onClose();
                      // Navigating to the setup wizard is handled outside this component.
                      // Dispatch a custom event that App.tsx can listen to.
                      window.dispatchEvent(new CustomEvent("aloha:showWizard"));
                    }}
                    className="
                      text-xs text-sky-400 hover:text-sky-300 border border-sky-500/30
                      hover:border-sky-500/60 px-2.5 py-1 rounded-md transition-colors
                      focus:outline-none focus:ring-1 focus:ring-sky-500
                    "
                  >
                    Switch
                  </button>
                </div>
              </section>

              {/* Model section */}
              <section>
                <SectionHeading>Model</SectionHeading>
                <select
                  value={model}
                  onChange={(e) => setModel(e.target.value)}
                  className="
                    w-full bg-slate-800/60 border border-surface-border
                    text-sm text-slate-200 rounded-lg px-3 py-2.5
                    focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500
                    appearance-none
                  "
                >
                  {availableModels.length > 0 ? (
                    availableModels.map((m) => (
                      <option key={m} value={m}>
                        {m}
                      </option>
                    ))
                  ) : (
                    <option value={model}>{model}</option>
                  )}
                </select>
              </section>

              {/* Safety mode section */}
              <section>
                <SectionHeading>Safety Mode</SectionHeading>
                <div className="space-y-2">
                  {(["strict", "normal", "permissive"] as const).map((mode) => {
                    const descriptions: Record<string, string> = {
                      strict: "All writes require approval",
                      normal: "Soft writes auto-approved; config changes require approval",
                      permissive: "All operations auto-approved",
                    };
                    return (
                      <label
                        key={mode}
                        className={`
                          flex items-start gap-3 rounded-lg px-4 py-3 cursor-pointer
                          border transition-colors duration-150
                          ${safetyMode === mode
                            ? "bg-sky-500/10 border-sky-500/40"
                            : "bg-slate-800/40 border-surface-border hover:border-slate-500"
                          }
                        `}
                      >
                        <input
                          type="radio"
                          name="safety_mode"
                          value={mode}
                          checked={safetyMode === mode}
                          onChange={() => setSafetyMode(mode)}
                          className="mt-0.5 accent-sky-500"
                        />
                        <div>
                          <span className="text-sm font-medium text-slate-200 capitalize">
                            {mode}
                          </span>
                          <p className="text-xs text-slate-500 mt-0.5">
                            {descriptions[mode]}
                          </p>
                        </div>
                      </label>
                    );
                  })}
                </div>
              </section>

              {/* Context refresh */}
              <section>
                <SectionHeading>Context Refresh (minutes)</SectionHeading>
                <div className="flex items-center gap-3">
                  <input
                    type="number"
                    min={1}
                    max={60}
                    value={contextRefresh}
                    onChange={(e) => setContextRefresh(Math.max(1, Number(e.target.value)))}
                    className="
                      w-24 bg-slate-800/60 border border-surface-border
                      text-sm text-slate-200 rounded-lg px-3 py-2
                      focus:outline-none focus:ring-2 focus:ring-sky-500 focus:border-sky-500
                    "
                  />
                  <span className="text-xs text-slate-500">
                    How often Aloha re-reads your HA state
                  </span>
                </div>
              </section>

              {/* About */}
              <section>
                <SectionHeading>About</SectionHeading>
                <div className="rounded-lg bg-slate-800/40 border border-surface-border px-4 py-3 space-y-1 text-xs text-slate-500">
                  <div className="flex justify-between">
                    <span>HA URL</span>
                    <span className="font-mono text-slate-400">{settings?.ha_url ?? "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Mode</span>
                    <span className="font-mono text-slate-400">{settings?.mode ?? "—"}</span>
                  </div>
                  <div className="flex justify-between">
                    <span>Port</span>
                    <span className="font-mono text-slate-400">{settings?.port ?? "—"}</span>
                  </div>
                </div>
              </section>
            </>
          )}
        </div>

        {/* Footer */}
        <div className="shrink-0 px-5 py-4 border-t border-surface-border flex items-center justify-between">
          {saveError && (
            <p className="text-xs text-red-400 mr-3 truncate">{saveError}</p>
          )}
          {savedOk && (
            <p className="text-xs text-emerald-400 mr-3">Saved!</p>
          )}
          {!saveError && !savedOk && <span />}

          <button
            onClick={handleSave}
            disabled={saving || loading}
            className="
              px-5 py-2 rounded-lg text-sm font-medium
              bg-sky-600 text-white
              hover:bg-sky-500
              disabled:opacity-40 disabled:cursor-not-allowed
              transition-colors duration-150
              focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-800
            "
          >
            {saving ? "Saving…" : "Save changes"}
          </button>
        </div>
      </div>
    </div>
  );
}
