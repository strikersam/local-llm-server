import React from "react";

export interface AgentStatus {
  id: string;
  name: string;
  role: string;
  status: "idle" | "running" | "waiting" | "error" | "done";
  current_task?: string;
  last_active?: string;
  tools_used?: string[];
  messages_sent?: number;
}

interface AgentStatusPanelProps {
  sessionId?: string;
  agents?: AgentStatus[];
  loading?: boolean;
  error?: string | null;
  className?: string;
}

const STATUS_STYLES: Record<string, string> = {
  idle: "bg-gray-500/20 text-gray-400 border-gray-500/30",
  running: "bg-green-500/20 text-green-400 border-green-500/30 animate-pulse",
  waiting: "bg-yellow-500/20 text-yellow-400 border-yellow-500/30",
  error: "bg-red-500/20 text-red-400 border-red-500/30",
  done: "bg-blue-500/20 text-blue-400 border-blue-500/30",
};

const STATUS_DOTS: Record<string, string> = {
  idle: "bg-gray-500",
  running: "bg-green-400 animate-pulse",
  waiting: "bg-yellow-400",
  error: "bg-red-500",
  done: "bg-blue-400",
};

const ROLE_ICONS: Record<string, string> = {
  planner: "🗺️",
  implementer: "⚡",
  reviewer: "🔍",
  judge: "⚖️",
  scout: "🔭",
  coordinator: "🎯",
};

export const AgentStatusPanel: React.FC<AgentStatusPanelProps> = ({
  sessionId,
  agents = [],
  loading = false,
  error = null,
  className = "",
}) => {
  const activeCount = agents.filter((a) => a.status === "running").length;
  const waitingCount = agents.filter((a) => a.status === "waiting").length;

  return (
    <div className={`bg-gray-950 rounded-xl border border-gray-800 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-900">
        <div className="flex items-center gap-2">
          <span className="text-sm font-semibold text-gray-200">Agent Status</span>
          {sessionId && (
            <span className="text-xs text-gray-500 font-mono">#{sessionId.slice(0, 8)}</span>
          )}
        </div>
        <div className="flex items-center gap-3 text-xs text-gray-500">
          {activeCount > 0 && (
            <span className="text-green-400">
              {activeCount} running
            </span>
          )}
          {waitingCount > 0 && (
            <span className="text-yellow-400">
              {waitingCount} waiting
            </span>
          )}
          <span>{agents.length} agents</span>
        </div>
      </div>

      {/* Content */}
      <div className="p-3">
        {loading && (
          <div className="flex items-center justify-center py-8 text-gray-600 text-sm">
            Loading agents…
          </div>
        )}
        {error && (
          <div className="flex items-center justify-center py-8 text-red-500 text-sm">
            {error}
          </div>
        )}
        {!loading && !error && agents.length === 0 && (
          <div className="flex flex-col items-center justify-center py-8 text-gray-600 gap-2">
            <span className="text-2xl">🤖</span>
            <span className="text-sm">No active agents</span>
          </div>
        )}
        <div className="grid grid-cols-1 gap-2 sm:grid-cols-2">
          {agents.map((agent) => (
            <AgentCard key={agent.id} agent={agent} />
          ))}
        </div>
      </div>
    </div>
  );
};

const AgentCard: React.FC<{ agent: AgentStatus }> = ({ agent }) => {
  const statusStyle = STATUS_STYLES[agent.status] ?? STATUS_STYLES.idle;
  const dotStyle = STATUS_DOTS[agent.status] ?? STATUS_DOTS.idle;
  const icon = ROLE_ICONS[agent.role?.toLowerCase()] ?? "🤖";

  return (
    <div className={`rounded-lg border p-3 text-xs ${statusStyle}`}>
      <div className="flex items-center gap-2 mb-2">
        <span className="text-base">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <div className={`w-1.5 h-1.5 rounded-full flex-shrink-0 ${dotStyle}`} />
            <span className="font-semibold truncate">{agent.name}</span>
          </div>
          <div className="text-[10px] opacity-60 capitalize">{agent.role}</div>
        </div>
        <span className={`px-1.5 py-0.5 rounded text-[10px] font-medium capitalize border ${statusStyle}`}>
          {agent.status}
        </span>
      </div>

      {agent.current_task && (
        <div className="mb-2 p-1.5 bg-black/20 rounded text-[11px] leading-relaxed">
          {agent.current_task}
        </div>
      )}

      <div className="flex items-center justify-between opacity-60">
        {agent.last_active && (
          <span>
            {formatRelative(agent.last_active)}
          </span>
        )}
        {agent.messages_sent !== undefined && (
          <span>{agent.messages_sent} msgs</span>
        )}
      </div>

      {agent.tools_used && agent.tools_used.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {agent.tools_used.slice(-4).map((tool) => (
            <span
              key={tool}
              className="px-1.5 py-0.5 rounded bg-black/20 text-[10px] font-mono"
            >
              {tool}
            </span>
          ))}
        </div>
      )}
    </div>
  );
};

function formatRelative(isoString: string): string {
  try {
    const diff = Date.now() - new Date(isoString).getTime();
    if (diff < 5000) return "just now";
    if (diff < 60000) return `${Math.floor(diff / 1000)}s ago`;
    if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`;
    return `${Math.floor(diff / 3600000)}h ago`;
  } catch {
    return isoString;
  }
}

export default AgentStatusPanel;
