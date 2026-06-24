import React, { useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Highlight, themes } from "prism-react-renderer";
import { ChatMessage } from "../../stores/chat";
import { DiffPanel } from "./DiffPanel";

// ---------------------------------------------------------------------------
// Props
// ---------------------------------------------------------------------------

interface MessageProps {
  message: ChatMessage;
  isStreaming?: boolean;
}

// ---------------------------------------------------------------------------
// Code block renderer for ReactMarkdown
// ---------------------------------------------------------------------------

function CodeBlock({
  className,
  children,
}: {
  className?: string;
  children?: React.ReactNode;
}) {
  const match = /language-(\w+)/.exec(className ?? "");
  const language = match ? match[1] : "text";
  const code = String(children ?? "").trimEnd();

  return (
    <Highlight theme={themes.oneDark} code={code} language={language}>
      {({ className: cls, style, tokens, getLineProps, getTokenProps }) => (
        <pre
          className={`${cls} rounded-md p-4 overflow-x-auto text-sm my-3`}
          style={style}
        >
          {tokens.map((line, i) => (
            <div key={i} {...getLineProps({ line })}>
              {line.map((token, j) => (
                <span key={j} {...getTokenProps({ token })} />
              ))}
            </div>
          ))}
        </pre>
      )}
    </Highlight>
  );
}

// ---------------------------------------------------------------------------
// Tool call pill
// ---------------------------------------------------------------------------

interface ToolCallPillProps {
  name: string;
  args: Record<string, unknown>;
  result?: string;
  error?: boolean;
}

function ToolCallPill({ name, args, result, error }: ToolCallPillProps) {
  const [expanded, setExpanded] = useState(false);

  const argsPreview = Object.entries(args)
    .map(([k, v]) => `${k}: ${JSON.stringify(v)}`)
    .join(", ");

  return (
    <div className="my-1">
      <button
        onClick={() => setExpanded((e) => !e)}
        className="
          inline-flex items-center gap-1.5 px-3 py-1 rounded-full
          bg-slate-700/60 border border-slate-600/50
          text-xs text-slate-400
          hover:bg-slate-700 hover:text-slate-300
          transition-colors duration-150
          focus:outline-none focus:ring-1 focus:ring-slate-500
        "
      >
        <span>⚙</span>
        <span className="font-mono font-medium text-slate-300">{name}</span>
        <span className="truncate max-w-[200px]">({argsPreview})</span>
        <span className="ml-1 text-slate-500">{expanded ? "▲" : "▼"}</span>
      </button>

      {expanded && (
        <div className="mt-1 ml-2 rounded-md border border-slate-700 bg-slate-800/80 text-xs font-mono text-slate-400 p-3 space-y-2">
          <div>
            <span className="text-slate-500">args: </span>
            <span className="text-slate-300">{JSON.stringify(args, null, 2)}</span>
          </div>
          {result !== undefined && (
            <div>
              <span className={error ? "text-red-400" : "text-slate-500"}>
                {error ? "error: " : "result: "}
              </span>
              <span className={error ? "text-red-300" : "text-slate-300"}>
                {result.slice(0, 500)}
                {result.length > 500 ? "…" : ""}
              </span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Tool result pill (standalone — for role=tool messages without tool_call)
// ---------------------------------------------------------------------------

function ToolResultCompact({ content }: { content: string }) {
  const [expanded, setExpanded] = useState(false);
  const PREVIEW_LEN = 200;
  const truncated = content.length > PREVIEW_LEN;

  return (
    <div
      className="
        my-1 px-3 py-2 rounded-md
        bg-slate-800/60 border border-slate-700/50
        text-xs font-mono text-slate-500
      "
    >
      {expanded ? content : content.slice(0, PREVIEW_LEN)}
      {truncated && (
        <button
          onClick={() => setExpanded((e) => !e)}
          className="ml-2 text-sky-500 hover:text-sky-400 focus:outline-none"
        >
          {expanded ? "collapse" : "expand"}
        </button>
      )}
    </div>
  );
}

// ---------------------------------------------------------------------------
// Streaming cursor
// ---------------------------------------------------------------------------

function StreamingCursor() {
  return (
    <span
      className="inline-block w-0.5 h-4 bg-sky-400 ml-0.5 align-middle animate-[blink_1s_step-end_infinite]"
      style={{
        animation: "blink 1s step-end infinite",
      }}
    >
      <style>{`
        @keyframes blink {
          0%, 100% { opacity: 1; }
          50% { opacity: 0; }
        }
      `}</style>
    </span>
  );
}

// ---------------------------------------------------------------------------
// Main Message component
// ---------------------------------------------------------------------------

export function Message({ message, isStreaming = false }: MessageProps): React.ReactElement | null {
  const { role, content, tool_call, pending_diff } = message;

  // ---
  // Render pending diff overlay when this message carries an unresolved diff
  // ---
  if (pending_diff && pending_diff.status === "pending") {
    return <DiffPanel diff={pending_diff} />;
  }

  // ---
  // Tool call message (role === "tool" with tool_call data)
  // ---
  if (role === "tool" && tool_call) {
    return (
      <div className="py-1 px-4">
        <ToolCallPill
          name={tool_call.name}
          args={tool_call.args}
          result={tool_call.result}
          error={tool_call.error}
        />
      </div>
    );
  }

  // ---
  // Tool result without a tool_call object (bare role=tool)
  // ---
  if (role === "tool" && !tool_call) {
    return (
      <div className="py-1 px-4">
        <ToolResultCompact content={content} />
      </div>
    );
  }

  // ---
  // User message
  // ---
  if (role === "user") {
    return (
      <div className="flex justify-end px-4 py-1">
        <div
          className="
            max-w-[70%] px-4 py-2.5 rounded-2xl rounded-tr-sm
            bg-sky-600 text-white text-sm leading-relaxed
            whitespace-pre-wrap break-words
          "
        >
          {content}
        </div>
      </div>
    );
  }

  // ---
  // Assistant message
  // ---
  return (
    <div className="px-4 py-1">
      <div className="max-w-none">
        {/* Resolved diff badge */}
        {pending_diff && pending_diff.status !== "pending" && (
          <div
            className={`
              inline-flex items-center gap-1.5 mb-2 px-2.5 py-1 rounded-full text-xs
              ${pending_diff.status === "applied"
                ? "bg-emerald-900/40 text-emerald-400 border border-emerald-700/40"
                : "bg-red-900/40 text-red-400 border border-red-700/40"
              }
            `}
          >
            <span>{pending_diff.status === "applied" ? "✓" : "✗"}</span>
            <span>
              {pending_diff.status === "applied" ? "Applied" : "Rejected"}:{" "}
              <code className="font-mono">
                {pending_diff.path.replace(/^\/data\/homeassistant\//, "")}
              </code>
            </span>
          </div>
        )}

        {/* Markdown content */}
        <div className="prose prose-invert prose-sm max-w-none text-slate-200">
          <ReactMarkdown
            remarkPlugins={[remarkGfm]}
            components={{
              // Use custom code block renderer with Prism
              code({ className, children, ...props }) {
                const isBlock = className?.startsWith("language-");
                if (isBlock) {
                  return <CodeBlock className={className}>{children}</CodeBlock>;
                }
                return (
                  <code
                    {...props}
                    className="bg-slate-700/60 text-sky-300 px-1 py-0.5 rounded text-xs font-mono"
                  >
                    {children}
                  </code>
                );
              },
              // Tables
              table({ children }) {
                return (
                  <div className="overflow-x-auto my-3">
                    <table className="border-collapse w-full text-sm">{children}</table>
                  </div>
                );
              },
              th({ children }) {
                return (
                  <th className="border border-slate-600 bg-slate-700/50 px-3 py-1.5 text-left text-slate-200 font-semibold">
                    {children}
                  </th>
                );
              },
              td({ children }) {
                return (
                  <td className="border border-slate-700 px-3 py-1.5 text-slate-300">
                    {children}
                  </td>
                );
              },
            }}
          >
            {content}
          </ReactMarkdown>
          {isStreaming && content.length === 0 && (
            <StreamingCursor />
          )}
          {isStreaming && content.length > 0 && (
            <span className="inline">
              <StreamingCursor />
            </span>
          )}
        </div>
      </div>
    </div>
  );
}
