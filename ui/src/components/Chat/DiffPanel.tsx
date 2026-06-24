import React from "react";
import ReactDiffViewer, { DiffMethod } from "react-diff-viewer-continued";
import { useChatStore, PendingDiff } from "../../stores/chat";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface DiffPanelProps {
  diff: PendingDiff;
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

export function DiffPanel({ diff }: DiffPanelProps): React.ReactElement {
  const approveDiff = useChatStore((s) => s.approveDiff);
  const [applying, setApplying] = React.useState(false);

  async function handleAction(action: "apply" | "reject") {
    setApplying(true);
    try {
      await approveDiff(diff.id, action);
    } finally {
      setApplying(false);
    }
  }

  // Derive a display-friendly filename from the full path
  const displayPath = diff.path.replace(/^\/data\/homeassistant\//, "");

  return (
    // Full-screen backdrop overlay
    <div className="fixed inset-0 z-50 flex flex-col bg-slate-900/90 backdrop-blur-sm">
      {/* Header bar */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-surface-border bg-surface shrink-0">
        <div className="flex items-center gap-3 min-w-0">
          <span className="text-slate-400 text-sm font-mono shrink-0">Proposed change to</span>
          <span className="text-sky-400 font-mono text-sm truncate" title={diff.path}>
            {displayPath}
          </span>
        </div>

        <div className="flex items-center gap-2 shrink-0">
          <button
            onClick={() => handleAction("reject")}
            disabled={applying}
            className="
              px-4 py-1.5 rounded-md text-sm font-medium
              bg-red-600/20 border border-red-500/40 text-red-400
              hover:bg-red-600/30 hover:border-red-500/60
              disabled:opacity-40 disabled:cursor-not-allowed
              transition-colors duration-150
              focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 focus:ring-offset-slate-800
            "
          >
            Reject
          </button>

          <button
            onClick={() => handleAction("apply")}
            disabled={applying}
            className="
              px-4 py-1.5 rounded-md text-sm font-medium
              bg-emerald-600/20 border border-emerald-500/40 text-emerald-400
              hover:bg-emerald-600/30 hover:border-emerald-500/60
              disabled:opacity-40 disabled:cursor-not-allowed
              transition-colors duration-150
              focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:ring-offset-2 focus:ring-offset-slate-800
            "
          >
            {applying ? "Applying…" : "Apply"}
          </button>
        </div>
      </div>

      {/* Diff viewer — scrollable */}
      <div className="flex-1 overflow-auto">
        <ReactDiffViewer
          oldValue={diff.before}
          newValue={diff.after}
          splitView={false}
          compareMethod={DiffMethod.LINES}
          useDarkTheme
          styles={{
            variables: {
              dark: {
                diffViewerBackground: "#0f172a",
                addedBackground: "#052e16",
                addedColor: "#86efac",
                removedBackground: "#450a0a",
                removedColor: "#fca5a5",
                wordAddedBackground: "#166534",
                wordRemovedBackground: "#7f1d1d",
                addedGutterBackground: "#052e16",
                removedGutterBackground: "#450a0a",
                gutterBackground: "#1e293b",
                gutterBackgroundDark: "#1e293b",
                highlightBackground: "#2d4a6e",
                highlightGutterBackground: "#2d4a6e",
                codeFoldGutterBackground: "#334155",
                codeFoldBackground: "#1e293b",
                emptyLineBackground: "#0f172a",
                gutterColor: "#64748b",
                addedGutterColor: "#4ade80",
                removedGutterColor: "#f87171",
                codeFoldContentColor: "#64748b",
                diffViewerTitleBackground: "#1e293b",
                diffViewerTitleColor: "#e2e8f0",
                diffViewerTitleBorderColor: "#334155",
              },
            },
          }}
        />
      </div>

      {/* Status bar if diff is already resolved */}
      {diff.status !== "pending" && (
        <div className={`
          px-4 py-2 text-sm text-center font-medium shrink-0
          ${diff.status === "applied"
            ? "bg-emerald-900/40 text-emerald-400 border-t border-emerald-700/40"
            : "bg-red-900/40 text-red-400 border-t border-red-700/40"
          }
        `}>
          {diff.status === "applied" ? "Change applied" : "Change rejected"}
        </div>
      )}
    </div>
  );
}
