import React, { useEffect, useState, useCallback, useRef } from "react";
import { getContext, refreshContext, ContextResponse } from "../../api/client";
import { useSettingsStore } from "../../stores/settings";

// ---------------------------------------------------------------------------
// Helper
// ---------------------------------------------------------------------------

function formatRelativeTime(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  return `${Math.floor(hours / 24)}d ago`;
}

// ---------------------------------------------------------------------------
// Domain badge
// ---------------------------------------------------------------------------

// We parse the summary or use entity_count split per domain when available.
// Since the API only returns `entity_count` total, we show one badge for now.
// The panel shows domain breakdown if summary includes it (future extension).

interface DomainBadgeProps {
  domain: string;
  count: number;
}

function DomainBadge({ domain, count }: DomainBadgeProps) {
  return (
    <span
      className="
        inline-flex items-center gap-1 px-2 py-0.5 rounded-full
        bg-slate-700/60 border border-slate-600/40
        text-xs text-slate-300
      "
    >
      <span className="text-slate-400 capitalize">{domain}</span>
      <span className="text-sky-400 font-medium">{count}</span>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Panel
// ---------------------------------------------------------------------------

interface ContextPanelProps {
  onClose?: () => void;
}

export function ContextPanel({ onClose }: ContextPanelProps): React.ReactElement {
  const settings = useSettingsStore((s) => s.settings);
  const refreshMinutes = settings?.context_refresh_minutes ?? 5;

  const [context, setContext] = useState<ContextResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const load = useCallback(async () => {
    try {
      const data = await getContext();
      setContext(data);
      setError(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load context");
    } finally {
      setLoading(false);
    }
  }, []);

  // Initial load + polling every refreshMinutes
  useEffect(() => {
    load();

    // Poll at the configured interval (convert minutes to ms)
    const ms = Math.max(refreshMinutes, 1) * 60 * 1000;
    intervalRef.current = setInterval(load, ms);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [load, refreshMinutes]);

  async function handleRefresh() {
    setRefreshing(true);
    try {
      await refreshContext();
      await load();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Refresh failed");
    } finally {
      setRefreshing(false);
    }
  }

  // Try to parse domain counts from summary (graceful fallback to total)
  // The summary field is free text; we display what we have.

  return (
    <div className="w-64 shrink-0 bg-surface border-l border-surface-border flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border">
        <h2 className="text-sm font-semibold text-slate-200">HA Context</h2>
        <button
          onClick={onClose}
          className="
            text-slate-500 hover:text-slate-300 transition-colors
            focus:outline-none focus:ring-1 focus:ring-slate-500 rounded
          "
          aria-label="Close context panel"
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-4">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="w-5 h-5 rounded-full border-2 border-sky-500/30 border-t-sky-500 animate-spin" />
          </div>
        )}

        {error && !loading && (
          <div className="rounded-md bg-red-900/30 border border-red-700/40 px-3 py-2 text-xs text-red-400">
            {error}
          </div>
        )}

        {context && !loading && (
          <>
            {/* Entity count */}
            <section>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Entities
              </h3>
              <div className="flex flex-wrap gap-1.5">
                <DomainBadge domain="total" count={context.entity_count} />
              </div>
            </section>

            {/* Automations */}
            <section>
              <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                Automations
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-2xl font-bold text-slate-100">
                  {context.automation_count}
                </span>
                <span className="text-xs text-slate-500">active rules</span>
              </div>
            </section>

            {/* Summary excerpt */}
            {context.summary && (
              <section>
                <h3 className="text-xs font-semibold text-slate-500 uppercase tracking-wider mb-2">
                  Summary
                </h3>
                <p className="text-xs text-slate-400 leading-relaxed line-clamp-6">
                  {context.summary}
                </p>
              </section>
            )}

            {/* Last refreshed */}
            <section className="pt-2 border-t border-surface-border">
              <div className="flex items-center justify-between">
                <span className="text-xs text-slate-600">
                  Updated {formatRelativeTime(context.last_refreshed)}
                </span>
                <button
                  onClick={handleRefresh}
                  disabled={refreshing}
                  className="
                    flex items-center gap-1 text-xs text-sky-500 hover:text-sky-400
                    disabled:opacity-40 disabled:cursor-not-allowed
                    transition-colors focus:outline-none
                  "
                  aria-label="Refresh context"
                >
                  <svg
                    className={`w-3 h-3 ${refreshing ? "animate-spin" : ""}`}
                    fill="none"
                    viewBox="0 0 24 24"
                    stroke="currentColor"
                    strokeWidth={2}
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"
                    />
                  </svg>
                  {refreshing ? "Refreshing…" : "Refresh"}
                </button>
              </div>
            </section>
          </>
        )}
      </div>
    </div>
  );
}
