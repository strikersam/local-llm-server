/**
 * ControlPlanePage — v3 unified post-login landing page.
 *
 * Shows:
 *   - Active agents panel
 *   - Task queue (queued / running / in_review / blocked)
 *   - Recent executions & escalation events
 *   - Provider / runtime health
 *   - Schedules due soon
 *   - Alerts requiring human attention
 *   - Rate-limit / cost / token summaries
 *   - Overall system health state
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, AlertTriangle, Bot, CheckCircle, ChevronRight,
  Clock, DollarSign, Layers, PlayCircle, RefreshCw,
  RotateCcw, Server, Shield, Zap, XCircle, Calendar,
  ArrowUpRight, Cpu, TrendingUp, Database,
} from 'lucide-react';
import {
  getStats, healthCheck, listRuntimes, listTasks,
  getDueSoonTasks, getDecisionLog, fmtErr
} from '../api';

// ── Tiny helpers ───────────────────────────────────────────────────────────────

function cls(...parts) { return parts.filter(Boolean).join(' '); }

function relTime(ts) {
  if (!ts) return '—';
  const diff = (Date.now() / 1000) - ts;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

const STATUS_DOT = {
  idle:        'bg-gray-500',
  running:     'bg-emerald-400 animate-pulse',
  waiting:     'bg-amber-400',
  error:       'bg-red-500',
  done:        'bg-blue-400',
  todo:        'bg-gray-500',
  in_progress: 'bg-emerald-400 animate-pulse',
  in_review:   'bg-amber-400',
  blocked:     'bg-red-400',
};

const STATUS_BADGE = {
  todo:        'border-white/10 bg-white/4 text-[#888]',
  in_progress: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400',
  in_review:   'border-amber-500/25 bg-amber-500/10 text-amber-400',
  blocked:     'border-red-500/25 bg-red-500/10 text-red-400',
  done:        'border-blue-500/25 bg-blue-500/10 text-blue-400',
};

const PRIORITY_DOT = {
  urgent: 'bg-red-500',
  high:   'bg-amber-500',
  medium: 'bg-blue-500',
  low:    'bg-gray-500',
};

// ── Section header ─────────────────────────────────────────────────────────────

function SectionHeader({ icon: Icon, title, count, onRefresh, loading, to }) {
  const nav = useNavigate();
  return (
    <div className="flex items-center justify-between mb-3">
      <div className="flex items-center gap-2">
        <Icon size={13} className="text-[#555]" />
        <span className="text-[11px] font-semibold tracking-[0.15em] uppercase text-[#555]">{title}</span>
        {count != null && (
          <span className="text-[10px] font-mono bg-white/5 border border-white/8 rounded-full px-2 py-0.5 text-[#777]">
            {count}
          </span>
        )}
      </div>
      <div className="flex items-center gap-2">
        {onRefresh && (
          <button onClick={onRefresh} disabled={loading}
            className="text-[#444] hover:text-[#888] transition-colors disabled:opacity-40">
            <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
          </button>
        )}
        {to && (
          <button onClick={() => nav(to)}
            className="flex items-center gap-1 text-[10px] text-[#444] hover:text-[#002FA7] transition-colors">
            View all <ArrowUpRight size={10} />
          </button>
        )}
      </div>
    </div>
  );
}

// ── Stat card ──────────────────────────────────────────────────────────────────

function StatCard({ icon: Icon, label, value, accent, sublabel, to }) {
  const nav = useNavigate();
  return (
    <button
      onClick={to ? () => nav(to) : undefined}
      className={cls(
        'group relative bg-[#111] border border-white/8 rounded-xl p-4 text-left transition-all duration-200',
        to ? 'hover:border-white/16 hover:bg-[#141414] hover:shadow-[0_8px_24px_rgba(0,0,0,0.4)]' : 'cursor-default',
      )}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="w-8 h-8 rounded-lg flex items-center justify-center"
          style={{ background: `${accent}15`, border: `1px solid ${accent}25` }}>
          <Icon size={14} style={{ color: accent }} />
        </div>
        {to && <ArrowUpRight size={12} className="text-[#333] opacity-0 group-hover:opacity-100 transition-opacity" />}
      </div>
      <div className="text-[26px] font-bold tracking-tight text-white leading-none mb-0.5"
        style={{ fontFamily: 'Outfit, sans-serif' }}>
        {value ?? '—'}
      </div>
      <div className="text-[10px] text-[#555] font-medium">{label}</div>
      {sublabel && <div className="text-[10px] text-[#444] mt-0.5">{sublabel}</div>}
    </button>
  );
}

// ── Health pill ────────────────────────────────────────────────────────────────

function HealthPill({ label, ok, latency }) {
  return (
    <div className={cls(
      'inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[10px] font-medium border',
      ok
        ? 'border-emerald-500/20 bg-emerald-500/8 text-emerald-400'
        : 'border-red-500/20 bg-red-500/8 text-red-400',
    )}>
      {ok ? <CheckCircle size={10} /> : <XCircle size={10} />}
      {label}
      {latency != null && <span className="opacity-60">{Math.round(latency)}ms</span>}
    </div>
  );
}

// ── Runtime card ───────────────────────────────────────────────────────────────

function RuntimeRow({ runtime }) {
  const h = runtime.health || {};
  const available = h.available;
  const circuitOpen = runtime.circuit_open;
  const status = circuitOpen ? 'circuit-open' : available ? 'online' : h.available === null ? 'unknown' : 'offline';
  const dot = { online: 'bg-emerald-500', offline: 'bg-red-500', 'circuit-open': 'bg-amber-500', unknown: 'bg-gray-600' }[status] || 'bg-gray-600';
  return (
    <div className="flex items-center justify-between py-2 border-b border-white/4 last:border-0">
      <div className="flex items-center gap-2.5">
        <div className={cls('w-2 h-2 rounded-full flex-shrink-0', dot, available && !circuitOpen ? '' : '')} />
        <div>
          <div className="text-[12px] text-white font-medium">{runtime.display_name}</div>
          <div className="text-[10px] text-[#555]">{runtime.tier?.replace('_', ' ')}</div>
        </div>
      </div>
      <div className="text-right">
        <div className={cls('text-[10px] font-mono', available && !circuitOpen ? 'text-emerald-400' : 'text-[#555]')}>
          {circuitOpen ? 'circuit open' : available ? 'online' : available === null ? 'checking' : 'offline'}
        </div>
        {h.latency_ms != null && <div className="text-[9px] text-[#444]">{Math.round(h.latency_ms)}ms</div>}
      </div>
    </div>
  );
}

// ── Task row ───────────────────────────────────────────────────────────────────

function TaskRow({ task, onClick }) {
  const dot = STATUS_DOT[task.status] || 'bg-gray-500';
  const badge = STATUS_BADGE[task.status] || 'border-white/10 bg-white/4 text-[#888]';
  return (
    <button
      onClick={onClick}
      className="w-full flex items-start gap-2.5 py-2.5 px-3 rounded-lg hover:bg-white/[0.03] transition-colors text-left group"
    >
      <div className={cls('w-1.5 h-1.5 rounded-full mt-1.5 flex-shrink-0', dot)} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[12px] text-white font-medium truncate">{task.title}</span>
          {task.priority === 'urgent' && (
            <span className="text-[9px] text-red-400 font-mono uppercase">URGENT</span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className={cls('text-[9px] px-1.5 py-0.5 rounded border font-mono', badge)}>
            {task.status.replace('_', ' ')}
          </span>
          {task.agent_id && (
            <span className="text-[9px] text-[#555] font-mono">@{task.agent_id}</span>
          )}
          {task.runtime_id && (
            <span className="text-[9px] text-[#444] font-mono">{task.runtime_id}</span>
          )}
          <span className="text-[9px] text-[#444]">{relTime(task.updated_at)}</span>
        </div>
      </div>
      <ChevronRight size={12} className="text-[#333] opacity-0 group-hover:opacity-100 transition-opacity flex-shrink-0 mt-1" />
    </button>
  );
}

// ── Routing decision row ───────────────────────────────────────────────────────

function DecisionRow({ d }) {
  return (
    <div className="py-2 border-b border-white/4 last:border-0">
      <div className="flex items-center justify-between mb-0.5">
        <span className="text-[11px] text-white font-mono truncate">{d.task_id}</span>
        <span className="text-[9px] text-[#444]">{relTime(d.timestamp)}</span>
      </div>
      <div className="flex items-center gap-2 flex-wrap">
        <span className="text-[10px] text-[#555]">{d.selected_runtime_id}</span>
        <span className="text-[10px] text-[#444]">{d.task_type}</span>
        {d.escalated && (
          <span className="text-[9px] text-amber-400 font-mono">ESCALATED</span>
        )}
        {d.fallback_attempted && (
          <span className="text-[9px] text-blue-400 font-mono">FALLBACK→{d.fallback_runtime_id}</span>
        )}
      </div>
      {d.reason && (
        <div className="text-[9px] text-[#444] mt-0.5 line-clamp-1">{d.reason}</div>
      )}
    </div>
  );
}

// ── Due-soon row ───────────────────────────────────────────────────────────────

function DueSoonRow({ task }) {
  const now = Date.now() / 1000;
  const hoursLeft = task.due_date ? Math.max(0, (task.due_date - now) / 3600) : null;
  const urgent = hoursLeft != null && hoursLeft < 2;
  return (
    <div className="flex items-center gap-2.5 py-2 border-b border-white/4 last:border-0">
      <Calendar size={11} className={urgent ? 'text-red-400' : 'text-amber-400'} />
      <div className="flex-1 min-w-0">
        <div className="text-[11px] text-white truncate">{task.title}</div>
        <div className="text-[9px] text-[#555]">
          {hoursLeft != null ? `Due in ${hoursLeft < 1 ? `${Math.round(hoursLeft * 60)}m` : `${Math.round(hoursLeft)}h`}` : 'Due soon'}
        </div>
      </div>
      <div className={cls(
        'w-1.5 h-1.5 rounded-full flex-shrink-0',
        PRIORITY_DOT[task.priority] || 'bg-gray-500',
      )} />
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function ControlPlanePage() {
  const nav = useNavigate();
  const [loading, setLoading] = useState(true);
  const [rLoading, setRLoading] = useState(false);
  const [tLoading, setTLoading] = useState(false);

  const [health, setHealth]     = useState(null);
  const [stats, setStats]       = useState(null);
  const [runtimes, setRuntimes] = useState([]);
  const [tasks, setTasks]       = useState([]);
  const [dueSoon, setDueSoon]   = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [error, setError]       = useState('');

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const results = await Promise.allSettled([
        healthCheck().then(r => setHealth(r.data)),
        getStats().then(r => setStats(r.data)),
        listRuntimes().then(r => setRuntimes(r.data.runtimes || [])),
        listTasks({ limit: 10 }).then(r => setTasks(r.data.tasks || [])),
        getDueSoonTasks(24).then(r => setDueSoon(r.data.tasks || [])),
        getDecisionLog(20).then(r => setDecisions(r.data.decisions || [])),
      ]);
      const failed = results.filter(r => r.status === 'rejected');
      if (failed.length > 3) setError('Some data sources are unavailable');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadAll(); }, [loadAll]);

  const reloadRuntimes = async () => {
    setRLoading(true);
    try { const r = await listRuntimes(); setRuntimes(r.data.runtimes || []); } finally { setRLoading(false); }
  };

  const reloadTasks = async () => {
    setTLoading(true);
    try { const r = await listTasks({ limit: 10 }); setTasks(r.data.tasks || []); } finally { setTLoading(false); }
  };

  const isHealthy = health?.status === 'ok';

  // Alerts: blocked tasks + circuit-open runtimes
  const alerts = [
    ...tasks.filter(t => t.status === 'blocked').map(t => ({ type: 'task', label: `Blocked: ${t.title}`, id: t.task_id })),
    ...runtimes.filter(r => r.circuit_open).map(r => ({ type: 'runtime', label: `Runtime offline: ${r.display_name}`, id: r.runtime_id })),
  ];

  // Active tasks (running + in_review)
  const activeTasks = tasks.filter(t => ['in_progress', 'in_review'].includes(t.status));
  const queuedTasks = tasks.filter(t => t.status === 'todo');

  // Cost savings from local vs paid (from stats)
  const costSaved = stats?.cost_saved_usd != null ? `$${stats.cost_saved_usd.toFixed(2)}` : null;
  const tokenUsed = stats?.total_tokens != null ? `${(stats.total_tokens / 1000).toFixed(1)}K` : null;

  return (
    <div className="p-5 sm:p-6 lg:p-8 max-w-7xl mx-auto" data-testid="control-plane-page">

      {/* ── Header ── */}
      <div className="mb-6 animate-fade-in">
        <div className="flex items-center gap-2 mb-2">
          <div className={`w-2 h-2 rounded-full transition-colors ${
            loading ? 'bg-amber-500 animate-pulse' :
            isHealthy ? 'bg-emerald-500' : 'bg-amber-500'
          }`} />
          <span className="text-[11px] font-mono tracking-[0.2em] uppercase text-[#444]">
            {loading ? 'Loading...' : isHealthy ? 'All systems operational' : 'Partial outage detected'}
          </span>
          <span className="text-[10px] font-mono text-[#333] border border-white/8 px-2 py-0.5 rounded-full">v3.0</span>
        </div>
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-3xl sm:text-4xl font-bold tracking-[-0.03em] text-white"
              style={{ fontFamily: 'Outfit, sans-serif' }}>
              Control Plane
            </h1>
            <p className="text-sm text-[#555] mt-1">Unified AI Agent Operations Dashboard</p>
          </div>
          <button onClick={loadAll} disabled={loading}
            className="flex items-center gap-2 px-3 py-2 text-[11px] text-[#555] border border-white/8 rounded-lg hover:border-white/16 hover:text-[#888] transition-all disabled:opacity-40">
            <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
            Refresh
          </button>
        </div>
      </div>

      {error && (
        <div className="mb-4 flex items-center gap-2 px-4 py-3 bg-amber-500/8 border border-amber-500/20 rounded-lg text-[12px] text-amber-400">
          <AlertTriangle size={13} /> {error}
        </div>
      )}

      {/* ── Health pills ── */}
      <div className="flex flex-wrap gap-2 mb-6">
        <HealthPill label="MongoDB"  ok={health?.mongo}     />
        <HealthPill label="Ollama"   ok={health?.ollama}    />
        <HealthPill label="Langfuse" ok={stats?.langfuse_configured} />
        {runtimes.filter(r => r.health?.available).slice(0, 3).map(r => (
          <HealthPill key={r.runtime_id} label={r.display_name}
            ok={!r.circuit_open && r.health?.available}
            latency={r.health?.latency_ms} />
        ))}
      </div>

      {/* ── Stat row ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3 mb-6">
        <StatCard icon={Bot}       label="Active Agents"    value={activeTasks.length} accent="#22C55E" to="/agents" />
        <StatCard icon={PlayCircle} label="Running Tasks"   value={activeTasks.filter(t => t.status === 'in_progress').length} accent="#3B82F6" to="/tasks" />
        <StatCard icon={Clock}     label="Queued Tasks"     value={queuedTasks.length} accent="#F59E0B" to="/tasks" />
        <StatCard icon={DollarSign} label="Cost Saved"      value={costSaved || '—'} accent="#10B981" sublabel="vs paid providers" />
        <StatCard icon={Zap}       label="Tokens (session)" value={tokenUsed || '—'} accent="#8B5CF6" />
      </div>

      {/* ── Alerts ── */}
      {alerts.length > 0 && (
        <div className="mb-6 p-4 bg-red-500/5 border border-red-500/15 rounded-xl">
          <div className="flex items-center gap-2 mb-2">
            <AlertTriangle size={13} className="text-red-400" />
            <span className="text-[11px] font-semibold tracking-[0.15em] uppercase text-red-400">
              {alerts.length} Alert{alerts.length > 1 ? 's' : ''} Requiring Attention
            </span>
          </div>
          <div className="space-y-1.5">
            {alerts.map((a, i) => (
              <button key={i}
                onClick={() => nav(a.type === 'task' ? `/tasks` : '/runtimes')}
                className="w-full flex items-center gap-2 px-3 py-2 bg-black/30 border border-white/5 rounded-lg text-left hover:border-white/10 transition-colors">
                {a.type === 'task' ? <AlertTriangle size={11} className="text-amber-400" /> : <Server size={11} className="text-red-400" />}
                <span className="text-[11px] text-[#A0A0A0]">{a.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* ── Main grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Active / Queued Tasks */}
        <div className="lg:col-span-2 bg-[#111] border border-white/8 rounded-xl p-4">
          <SectionHeader icon={Activity} title="Task Queue" count={tasks.length}
            onRefresh={reloadTasks} loading={tLoading} to="/tasks" />
          {tasks.length === 0 ? (
            <div className="py-8 text-center text-[11px] text-[#444]">No tasks yet</div>
          ) : (
            <div>
              {activeTasks.length > 0 && (
                <div className="mb-2">
                  <div className="text-[9px] uppercase tracking-widest text-[#444] mb-1 px-3">Active</div>
                  {activeTasks.map(t => (
                    <TaskRow key={t.task_id} task={t} onClick={() => nav('/tasks')} />
                  ))}
                </div>
              )}
              {queuedTasks.length > 0 && (
                <div>
                  <div className="text-[9px] uppercase tracking-widest text-[#444] mb-1 px-3">Queued</div>
                  {queuedTasks.slice(0, 5).map(t => (
                    <TaskRow key={t.task_id} task={t} onClick={() => nav('/tasks')} />
                  ))}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Right column */}
        <div className="space-y-4">

          {/* Runtime health */}
          <div className="bg-[#111] border border-white/8 rounded-xl p-4">
            <SectionHeader icon={Cpu} title="Runtimes"
              onRefresh={reloadRuntimes} loading={rLoading} to="/runtimes" />
            {runtimes.length === 0 ? (
              <div className="py-4 text-center text-[11px] text-[#444]">No runtimes configured</div>
            ) : (
              runtimes.map(r => <RuntimeRow key={r.runtime_id} runtime={r} />)
            )}
          </div>

          {/* Due soon */}
          {dueSoon.length > 0 && (
            <div className="bg-[#111] border border-white/8 rounded-xl p-4">
              <SectionHeader icon={Calendar} title="Due Soon" count={dueSoon.length} to="/tasks" />
              {dueSoon.slice(0, 5).map(t => <DueSoonRow key={t.task_id} task={t} />)}
            </div>
          )}

          {/* Recent routing decisions */}
          {decisions.length > 0 && (
            <div className="bg-[#111] border border-white/8 rounded-xl p-4">
              <SectionHeader icon={TrendingUp} title="Routing Log" count={decisions.length} to="/observability" />
              {decisions.slice(0, 5).map((d, i) => <DecisionRow key={i} d={d} />)}
            </div>
          )}
        </div>
      </div>

      {/* ── Provider health row ── */}
      <div className="mt-4 bg-[#111] border border-white/8 rounded-xl p-4">
        <SectionHeader icon={Layers} title="Infrastructure Health" to="/providers" />
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { label: 'MongoDB', ok: health?.mongo, icon: Database },
            { label: 'Ollama', ok: health?.ollama, icon: Cpu },
            { label: 'Langfuse', ok: stats?.langfuse_configured, icon: BarChartStub },
            { label: 'Scheduler', ok: health?.scheduler, icon: Calendar },
          ].map(({ label, ok, icon: Icon }) => (
            <div key={label} className={cls(
              'flex items-center gap-2 px-3 py-2.5 rounded-lg border',
              ok ? 'border-emerald-500/15 bg-emerald-500/5' : 'border-white/5 bg-white/2'
            )}>
              <div className={cls('w-1.5 h-1.5 rounded-full', ok ? 'bg-emerald-500' : 'bg-[#444]')} />
              <span className={cls('text-[11px] font-medium', ok ? 'text-emerald-400' : 'text-[#555]')}>{label}</span>
            </div>
          ))}
        </div>
      </div>

    </div>
  );
}

// Minimal stub to avoid import issues if BarChart2 not imported
const BarChartStub = (props) => <TrendingUp {...props} />;
