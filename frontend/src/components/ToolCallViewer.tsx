import React, { useState } from "react";

export interface ToolCall {
  id: string;
  tool_name: string;
  agent: string;
  status: "pending" | "running" | "success" | "error";
  input?: Record<string, unknown>;
  output?: string;
  error?: string;
  started_at?: string;
  completed_at?: string;
  duration_ms?: number;
}

interface ToolCallViewerProps {
  toolCalls: ToolCall[];
  className?: string;
}

const TOOL_ICONS: Record<string, string> = {
  bash: "💻",
  read_file: "📄",
  write_file: "✏️",
  search: "🔍",
  web_fetch: "🌐",
  git: "🌿",
  github: "🐙",
  python: "🐍",
  list_directory: "📁",
  grep: "🔎",
  default: "⚙️",
};

const STATUS_STYLES: Record<string, string> = {
  pending: "border-gray-600 bg-gray-800/50",
  running: "border-blue-500/50 bg-blue-900/20",
  success: "border-green-500/50 bg-green-900/20",
  error: "border-red-500/50 bg-red-900/20",
};

const STATUS_BADGES: Record<string, string> = {
  pending: "bg-gray-600 text-gray-300",
  running: "bg-blue-600 text-blue-100 animate-pulse",
  success: "bg-green-700 text-green-100",
  error: "bg-red-700 text-red-100",
};

function getToolIcon(name: string): string {
  const lower = name.toLowerCase();
  for (const [key, icon] of Object.entries(TOOL_ICONS)) {
    if (lower.includes(key)) return icon;
  }
  return TOOL_ICONS.default;
}

export const ToolCallViewer: React.FC<ToolCallViewerProps> = ({
  toolCalls,
  className = "",
}) => {
  const running = toolCalls.filter((t) => t.status === "running").length;
  const succeeded = toolCalls.filter((t) => t.status === "success").length;
  const failed = toolCalls.filter((t) => t.status === "error").length;

  return (
    <div className={`bg-gray-950 rounded-xl border border-gray-800 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-900">
        <span className="text-sm font-semibold text-gray-200">Tool Calls</span>
        <div className="flex items-center gap-3 text-xs">
          {running > 0 && <span className="text-blue-400">{running} running</span>}
          {succeeded > 0 && <span className="text-green-400">{succeeded} ok</span>}
          {failed > 0 && <span className="text-red-400">{failed} failed</span>}
          <span className="text-gray-500">{toolCalls.length} total</span>
        </div>
      </div>

      {/* List */}
      <div className="p-3 space-y-2 max-h-96 overflow-y-auto font-mono text-xs">
        {toolCalls.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-gray-600 gap-2">
            <span className="text-2xl">⚙️</span>
            <span>No tool calls yet</span>
          </div>
        )}
        {[...toolCalls].reverse().map((call) => (
          <ToolCallRow key={call.id} call={call} />
        ))}
      </div>
    </div>
  );
};

const ToolCallRow: React.FC<{ call: ToolCall }> = ({ call }) => {
  const [expanded, setExpanded] = useState(false);
  const icon = getToolIcon(call.tool_name);
  const borderStyle = STATUS_STYLES[call.status] ?? STATUS_STYLES.pending;
  const badgeStyle = STATUS_BADGES[call.status] ?? STATUS_BADGES.pending;

  return (
    <div
      className={`rounded-lg border p-2 cursor-pointer transition-colors hover:opacity-90 ${borderStyle}`}
      onClick={() => setExpanded((v) => !v)}
    >
      <div className="flex items-center gap-2">
        <span>{icon}</span>
        <span className="font-semibold text-gray-200 flex-1 truncate">{call.tool_name}</span>
        <span className="text-gray-500 text-[10px]">{call.agent}</span>
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium ${badgeStyle}`}>
          {call.status}
        </span>
        {call.duration_ms !== undefined && (
          <span className="text-gray-500 text-[10px] tabular-nums">
            {call.duration_ms < 1000
              ? `${call.duration_ms}ms`
              : `${(call.duration_ms / 1000).toFixed(1)}s`}
          </span>
        )}
        <span className="text-gray-600 text-[10px]">{expanded ? "▲" : "▼"}</span>
      </div>

      {expanded && (
        <div className="mt-2 space-y-2">
          {call.input && Object.keys(call.input).length > 0 && (
            <div>
              <div className="text-[10px] text-gray-500 mb-1 uppercase tracking-wide">Input</div>
              <pre className="p-2 bg-black/30 rounded text-[10px] overflow-x-auto text-gray-300 whitespace-pre-wrap">
                {JSON.stringify(call.input, null, 2)}
              </pre>
            </div>
          )}
          {call.output && (
            <div>
              <div className="text-[10px] text-gray-500 mb-1 uppercase tracking-wide">Output</div>
              <pre className="p-2 bg-black/30 rounded text-[10px] overflow-x-auto text-green-300 whitespace-pre-wrap max-h-40">
                {call.output}
              </pre>
            </div>
          )}
          {call.error && (
            <div>
              <div className="text-[10px] text-gray-500 mb-1 uppercase tracking-wide">Error</div>
              <pre className="p-2 bg-red-900/20 rounded text-[10px] overflow-x-auto text-red-300 whitespace-pre-wrap">
                {call.error}
              </pre>
            </div>
          )}
        </div>
      )}
    </div>
  );
};

export default ToolCallViewer;
