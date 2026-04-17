import React, { useEffect, useRef, useState } from "react";

export interface ActivityEvent {
  id: string;
  timestamp: string;
  agent: string;
  type: "tool_call" | "message" | "handoff" | "status" | "error" | "result";
  content: string;
  metadata?: Record<string, unknown>;
}

interface AgentActivityFeedProps {
  sessionId?: string;
  maxEvents?: number;
  className?: string;
}

const AGENT_COLORS: Record<string, string> = {
  planner: "text-blue-400 bg-blue-400/10 border-blue-400/20",
  implementer: "text-green-400 bg-green-400/10 border-green-400/20",
  reviewer: "text-yellow-400 bg-yellow-400/10 border-yellow-400/20",
  judge: "text-purple-400 bg-purple-400/10 border-purple-400/20",
  scout: "text-cyan-400 bg-cyan-400/10 border-cyan-400/20",
  coordinator: "text-orange-400 bg-orange-400/10 border-orange-400/20",
  system: "text-gray-400 bg-gray-400/10 border-gray-400/20",
};

const EVENT_ICONS: Record<string, string> = {
  tool_call: "⚙️",
  message: "💬",
  handoff: "🔀",
  status: "📊",
  error: "❌",
  result: "✅",
};

function getAgentColor(agent: string): string {
  const key = agent.toLowerCase();
  return AGENT_COLORS[key] ?? "text-gray-300 bg-gray-300/10 border-gray-300/20";
}

function formatTime(isoString: string): string {
  try {
    const d = new Date(isoString);
    return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" });
  } catch {
    return isoString;
  }
}

export const AgentActivityFeed: React.FC<AgentActivityFeedProps> = ({
  sessionId,
  maxEvents = 100,
  className = "",
}) => {
  const [events, setEvents] = useState<ActivityEvent[]>([]);
  const [connected, setConnected] = useState(false);
  const [paused, setPaused] = useState(false);
  const [filter, setFilter] = useState<string>("all");
  const bottomRef = useRef<HTMLDivElement>(null);
  const esRef = useRef<EventSource | null>(null);
  const pausedRef = useRef(false);
  const pendingRef = useRef<ActivityEvent[]>([]);

  pausedRef.current = paused;

  useEffect(() => {
    const url = sessionId
      ? `/api/agent/stream?session_id=${encodeURIComponent(sessionId)}`
      : `/api/agent/stream`;

    const es = new EventSource(url);
    esRef.current = es;

    es.onopen = () => setConnected(true);

    es.onmessage = (ev) => {
      try {
        const data = JSON.parse(ev.data) as ActivityEvent;
        if (pausedRef.current) {
          pendingRef.current.push(data);
          return;
        }
        setEvents((prev) => {
          const next = [...prev, data];
          return next.length > maxEvents ? next.slice(next.length - maxEvents) : next;
        });
      } catch {
        // ignore parse errors
      }
    };

    es.onerror = () => {
      setConnected(false);
    };

    return () => {
      es.close();
      setConnected(false);
    };
  }, [sessionId, maxEvents]);

  // Auto-scroll when not paused
  useEffect(() => {
    if (!paused) {
      bottomRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [events, paused]);

  const handleResume = () => {
    setPaused(false);
    if (pendingRef.current.length > 0) {
      setEvents((prev) => {
        const next = [...prev, ...pendingRef.current];
        pendingRef.current = [];
        return next.length > maxEvents ? next.slice(next.length - maxEvents) : next;
      });
    }
  };

  const filteredEvents = filter === "all"
    ? events
    : events.filter((e) => e.agent.toLowerCase() === filter || e.type === filter);

  const agents = Array.from(new Set(events.map((e) => e.agent.toLowerCase())));

  return (
    <div className={`flex flex-col h-full bg-gray-950 rounded-xl border border-gray-800 overflow-hidden ${className}`}>
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-gray-800 bg-gray-900">
        <div className="flex items-center gap-2">
          <div className={`w-2 h-2 rounded-full ${connected ? "bg-green-400 animate-pulse" : "bg-red-500"}`} />
          <span className="text-sm font-semibold text-gray-200">Agent Activity</span>
          {sessionId && (
            <span className="text-xs text-gray-500 font-mono">#{sessionId.slice(0, 8)}</span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="text-xs text-gray-500">{events.length} events</span>
          {paused ? (
            <button
              onClick={handleResume}
              className="px-2 py-1 text-xs rounded bg-green-600 hover:bg-green-500 text-white transition-colors"
            >
              Resume {pendingRef.current.length > 0 && `(+${pendingRef.current.length})`}
            </button>
          ) : (
            <button
              onClick={() => setPaused(true)}
              className="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors"
            >
              Pause
            </button>
          )}
          <button
            onClick={() => setEvents([])}
            className="px-2 py-1 text-xs rounded bg-gray-700 hover:bg-gray-600 text-gray-300 transition-colors"
          >
            Clear
          </button>
        </div>
      </div>

      {/* Filter bar */}
      <div className="flex items-center gap-1 px-4 py-2 border-b border-gray-800 bg-gray-900/50 overflow-x-auto">
        <button
          onClick={() => setFilter("all")}
          className={`px-2 py-0.5 text-xs rounded-full border transition-colors whitespace-nowrap ${
            filter === "all"
              ? "bg-gray-600 border-gray-500 text-white"
              : "border-gray-700 text-gray-400 hover:border-gray-500"
          }`}
        >
          All
        </button>
        {agents.map((agent) => (
          <button
            key={agent}
            onClick={() => setFilter(agent)}
            className={`px-2 py-0.5 text-xs rounded-full border transition-colors whitespace-nowrap ${
              filter === agent
                ? getAgentColor(agent)
                : "border-gray-700 text-gray-400 hover:border-gray-500"
            }`}
          >
            {agent}
          </button>
        ))}
      </div>

      {/* Events */}
      <div className="flex-1 overflow-y-auto p-3 space-y-2 font-mono text-xs">
        {filteredEvents.length === 0 && (
          <div className="flex flex-col items-center justify-center h-full text-gray-600 gap-2">
            <span className="text-2xl">🤖</span>
            <span>Waiting for agent activity…</span>
          </div>
        )}
        {filteredEvents.map((event) => (
          <ActivityEventRow key={event.id} event={event} />
        ))}
        <div ref={bottomRef} />
      </div>
    </div>
  );
};

const ActivityEventRow: React.FC<{ event: ActivityEvent }> = ({ event }) => {
  const [expanded, setExpanded] = useState(false);
  const colorClass = getAgentColor(event.agent);
  const icon = EVENT_ICONS[event.type] ?? "•";
  const hasMetadata = event.metadata && Object.keys(event.metadata).length > 0;

  return (
    <div
      className={`rounded-lg border p-2 transition-colors ${colorClass} ${
        hasMetadata ? "cursor-pointer hover:opacity-90" : ""
      }`}
      onClick={() => hasMetadata && setExpanded((v) => !v)}
    >
      <div className="flex items-start gap-2">
        <span className="mt-0.5 text-base leading-none">{icon}</span>
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="font-bold uppercase tracking-wide text-[10px]">{event.agent}</span>
            <span className="text-[10px] opacity-60">{event.type}</span>
            <span className="ml-auto text-[10px] opacity-50 tabular-nums">{formatTime(event.timestamp)}</span>
            {hasMetadata && (
              <span className="text-[10px] opacity-60">{expanded ? "▲" : "▼"}</span>
            )}
          </div>
          <div className="text-[11px] leading-relaxed break-words whitespace-pre-wrap opacity-90">
            {event.content}
          </div>
          {expanded && hasMetadata && (
            <pre className="mt-2 p-2 bg-black/30 rounded text-[10px] overflow-x-auto">
              {JSON.stringify(event.metadata, null, 2)}
            </pre>
          )}
        </div>
      </div>
    </div>
  );
};

export default AgentActivityFeed;
