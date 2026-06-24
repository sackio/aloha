import React, { useState } from "react";
import { useChatStore, Session } from "../../stores/chat";
import { useSettingsStore } from "../../stores/settings";
import { SettingsPanel } from "../Settings/SettingsPanel";

// ---------------------------------------------------------------------------
// Relative date helper
// ---------------------------------------------------------------------------

function relativeDate(isoString: string): string {
  const diff = Date.now() - new Date(isoString).getTime();
  const seconds = Math.floor(diff / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  if (days === 1) return "yesterday";
  if (days < 7) return `${days}d ago`;
  return new Date(isoString).toLocaleDateString(undefined, {
    month: "short",
    day: "numeric",
  });
}

// ---------------------------------------------------------------------------
// Session list item
// ---------------------------------------------------------------------------

interface SessionItemProps {
  session: Session;
  isActive: boolean;
  onSelect: () => void;
  onDelete: () => void;
}

function SessionItem({ session, isActive, onSelect, onDelete }: SessionItemProps) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      role="button"
      tabIndex={0}
      onClick={onSelect}
      onKeyDown={(e) => e.key === "Enter" && onSelect()}
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      className={`
        group flex items-center gap-2 px-3 py-2 rounded-lg cursor-pointer
        transition-colors duration-150 select-none
        focus:outline-none focus:ring-1 focus:ring-sky-500
        ${isActive
          ? "bg-sky-600/20 border border-sky-500/30 text-slate-100"
          : "hover:bg-slate-700/50 border border-transparent text-slate-300 hover:text-slate-100"
        }
      `}
    >
      {/* Session title + date */}
      <div className="flex-1 min-w-0">
        <p className="text-sm truncate font-medium leading-snug">
          {session.title}
        </p>
        <p className="text-xs text-slate-500 mt-0.5">
          {relativeDate(session.updated_at)}
        </p>
      </div>

      {/* Delete button — visible on hover */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          onDelete();
        }}
        className={`
          shrink-0 p-1 rounded text-slate-500 hover:text-red-400
          focus:outline-none transition-colors duration-150
          ${hovered || isActive ? "opacity-100" : "opacity-0 group-hover:opacity-100"}
        `}
        aria-label={`Delete session: ${session.title}`}
        title="Delete session"
      >
        <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
        </svg>
      </button>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Hamburger icon
// ---------------------------------------------------------------------------

function HamburgerIcon({ open }: { open: boolean }) {
  return (
    <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
      {open ? (
        <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
      ) : (
        <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
      )}
    </svg>
  );
}

// ---------------------------------------------------------------------------
// Main Sidebar component
// ---------------------------------------------------------------------------

interface SidebarProps {
  showContextPanel: boolean;
  onToggleContext: () => void;
}

export function Sidebar({ showContextPanel, onToggleContext }: SidebarProps): React.ReactElement {
  const { sessions, activeSessionId, createSession, selectSession, deleteSession } = useChatStore();
  const settings = useSettingsStore((s) => s.settings);

  const [mobileOpen, setMobileOpen] = useState(false);
  const [showSettings, setShowSettings] = useState(false);

  const providerName = settings?.ai_provider
    ? settings.ai_provider.charAt(0).toUpperCase() + settings.ai_provider.slice(1)
    : "Not configured";

  // Listen for the wizard re-open event dispatched from SettingsPanel
  React.useEffect(() => {
    function handleShowWizard() {
      window.dispatchEvent(new CustomEvent("aloha:showWizard"));
    }
    window.addEventListener("aloha:showWizard", handleShowWizard);
    return () => window.removeEventListener("aloha:showWizard", handleShowWizard);
  }, []);

  async function handleNewChat() {
    await createSession();
    setMobileOpen(false);
  }

  const sidebarContent = (
    <div className="flex flex-col h-full">
      {/* Logo + New chat */}
      <div className="px-3 pt-4 pb-3 border-b border-surface-border space-y-2 shrink-0">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-2xl" role="img" aria-label="Aloha">🌺</span>
            <span className="text-base font-bold text-slate-100 tracking-tight">Aloha</span>
          </div>
          {/* Mobile close */}
          <button
            className="md:hidden text-slate-500 hover:text-slate-300 transition-colors focus:outline-none p-1 rounded"
            onClick={() => setMobileOpen(false)}
            aria-label="Close sidebar"
          >
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <button
          onClick={handleNewChat}
          className="
            w-full flex items-center justify-center gap-2
            px-3 py-2 rounded-lg text-sm font-medium
            bg-sky-600 text-white hover:bg-sky-500
            transition-colors duration-150
            focus:outline-none focus:ring-2 focus:ring-sky-500 focus:ring-offset-2 focus:ring-offset-slate-800
          "
        >
          <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M12 4v16m8-8H4" />
          </svg>
          New chat
        </button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto px-2 py-2 space-y-0.5">
        {sessions.length === 0 ? (
          <p className="text-xs text-slate-600 text-center py-6">No sessions yet</p>
        ) : (
          sessions.map((session) => (
            <SessionItem
              key={session.id}
              session={session}
              isActive={session.id === activeSessionId}
              onSelect={() => {
                selectSession(session.id);
                setMobileOpen(false);
              }}
              onDelete={() => deleteSession(session.id)}
            />
          ))
        )}
      </div>

      {/* Footer: settings + context toggle + provider status */}
      <div className="shrink-0 border-t border-surface-border px-3 py-3 space-y-2">
        {/* Context panel toggle */}
        <button
          onClick={onToggleContext}
          className={`
            w-full flex items-center gap-2 px-3 py-2 rounded-lg text-sm
            transition-colors duration-150 focus:outline-none focus:ring-1 focus:ring-sky-500
            ${showContextPanel
              ? "bg-sky-600/20 border border-sky-500/30 text-sky-300"
              : "text-slate-400 hover:bg-slate-700/50 hover:text-slate-200 border border-transparent"
            }
          `}
        >
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
          </svg>
          HA Context
        </button>

        {/* Settings button + provider indicator */}
        <button
          onClick={() => setShowSettings(true)}
          className="
            w-full flex items-center gap-2.5 px-3 py-2 rounded-lg text-sm
            text-slate-400 hover:bg-slate-700/50 hover:text-slate-200
            transition-colors duration-150
            focus:outline-none focus:ring-1 focus:ring-slate-500
            border border-transparent
          "
        >
          <svg className="w-4 h-4 shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
          </svg>
          <span className="flex-1 text-left">Settings</span>
          <span className="flex items-center gap-1 text-xs">
            <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
            <span className="text-slate-500 truncate max-w-[80px]">{providerName}</span>
          </span>
        </button>
      </div>

      {/* Settings modal */}
      {showSettings && <SettingsPanel onClose={() => setShowSettings(false)} />}
    </div>
  );

  return (
    <>
      {/* Mobile hamburger trigger — fixed top-left */}
      <button
        className="
          md:hidden fixed top-3 left-3 z-30
          p-2 rounded-lg bg-surface border border-surface-border
          text-slate-400 hover:text-slate-200 transition-colors
          focus:outline-none focus:ring-1 focus:ring-sky-500
        "
        onClick={() => setMobileOpen((o) => !o)}
        aria-label={mobileOpen ? "Close sidebar" : "Open sidebar"}
      >
        <HamburgerIcon open={mobileOpen} />
      </button>

      {/* Mobile overlay backdrop */}
      {mobileOpen && (
        <div
          className="md:hidden fixed inset-0 z-20 bg-black/50 backdrop-blur-sm"
          onClick={() => setMobileOpen(false)}
        />
      )}

      {/* Sidebar panel */}
      <aside
        className={`
          fixed md:static inset-y-0 left-0 z-20
          w-60 shrink-0 bg-surface border-r border-surface-border
          flex flex-col
          transition-transform duration-200 ease-in-out
          ${mobileOpen ? "translate-x-0" : "-translate-x-full md:translate-x-0"}
        `}
        aria-label="Sidebar"
      >
        {sidebarContent}
      </aside>
    </>
  );
}
