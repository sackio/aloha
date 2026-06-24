import React, { useEffect, useState } from "react";
import { getHealth, HealthResponse } from "./api/client";
import { useSettingsStore } from "./stores/settings";
import { FirstRun } from "./components/Wizard/FirstRun";
import { Sidebar } from "./components/Layout/Sidebar";
import { ChatView } from "./components/Chat/ChatView";
import { ContextPanel } from "./components/Context/ContextPanel";

// ---------------------------------------------------------------------------
// Loading screen shown while health check is in flight
// ---------------------------------------------------------------------------

function LoadingScreen() {
  return (
    <div className="flex items-center justify-center min-h-screen bg-slate-900">
      <div className="flex flex-col items-center gap-4">
        <div className="w-10 h-10 rounded-full border-2 border-sky-500/30 border-t-sky-500 animate-spin" />
        <p className="text-sm text-muted">Starting Aloha…</p>
      </div>
    </div>
  );
}

// ---------------------------------------------------------------------------
// Main layout (shown after setup is complete)
// ---------------------------------------------------------------------------

interface MainLayoutProps {
  onShowWizard: () => void;
}

function MainLayout({ onShowWizard }: MainLayoutProps) {
  const [showContext, setShowContext] = useState(false);

  // Listen for the custom event dispatched by SettingsPanel's "Switch" button
  useEffect(() => {
    function handleShowWizard() {
      onShowWizard();
    }
    window.addEventListener("aloha:showWizard", handleShowWizard);
    return () => window.removeEventListener("aloha:showWizard", handleShowWizard);
  }, [onShowWizard]);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-900 text-slate-100">
      {/* Left sidebar */}
      <Sidebar
        showContextPanel={showContext}
        onToggleContext={() => setShowContext((v) => !v)}
      />

      {/* Main content area */}
      <main className="flex-1 flex flex-col overflow-hidden min-w-0">
        <ChatView />
      </main>

      {/* Right context panel — conditionally visible */}
      {showContext && (
        <ContextPanel onClose={() => setShowContext(false)} />
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// App root
// ---------------------------------------------------------------------------

type AppPhase = "loading" | "setup" | "main";

export default function App(): React.ReactElement {
  const fetchSettings = useSettingsStore((s) => s.fetchSettings);
  const settings = useSettingsStore((s) => s.settings);

  const [phase, setPhase] = useState<AppPhase>("loading");

  useEffect(() => {
    let cancelled = false;

    async function checkHealth() {
      let health: HealthResponse;
      try {
        health = await getHealth();
      } catch {
        // Backend unreachable — show setup (FirstRun handles its own state)
        if (!cancelled) setPhase("setup");
        return;
      }

      if (cancelled) return;

      if (health.setup_complete) {
        // Load settings and go to main chat
        await fetchSettings();
        if (!cancelled) setPhase("main");
      } else {
        if (!cancelled) setPhase("setup");
      }
    }

    checkHealth();

    return () => {
      cancelled = true;
    };
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  // When FirstRun completes, it redirects via window.location.replace("/").
  // If instead we want a SPA transition we catch the wizard-complete event.
  useEffect(() => {
    function handleSetupComplete() {
      fetchSettings().then(() => setPhase("main"));
    }
    window.addEventListener("aloha:setupComplete", handleSetupComplete);
    return () => window.removeEventListener("aloha:setupComplete", handleSetupComplete);
  }, [fetchSettings]);

  if (phase === "loading") {
    return <LoadingScreen />;
  }

  if (phase === "setup") {
    return (
      <FirstRun />
    );
  }

  // phase === "main"
  return (
    <MainLayout
      onShowWizard={() => setPhase("setup")}
    />
  );
}
