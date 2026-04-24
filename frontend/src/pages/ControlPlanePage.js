/**
 * ControlPlanePage — v3.1 unified post-login landing.
 *
 * Design: lifted directly from the Control Plane design bundle.
 * Colors: #0F0F13 base / #141418 surface / #0D0D11 sidebar
 * Text:   #F2F2F6 primary / #B2B2C4 secondary / #808094 tertiary / #565666 muted
 */
import React, { useEffect, useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity, AlertTriangle, Bot, CheckCircle, Clock,
  DollarSign, Layers, PlayCircle, RefreshCw, Server,
  Zap, XCircle, Calendar, ArrowUpRight, Cpu, TrendingUp,
  Database, BarChart3,
} from 'lucide-react';
import {
  getStats, healthCheck, listRuntimes, listTasks,
  getDueSoonTasks, getDecisionLog, fmtErr,
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

// ── Design tokens (match design bundle) ───────────────────────────────────────

const C = {
  bg:      '#0F0F13',
  surface: '#141418',
  border:  'rgba(255,255,255,0.06)',
  primary: '#F2F2F6',
  secondary:'#B2B2C4',
  tertiary: '#808094',
  muted:    '#565666',
  accent:   '#002FA7',
};

const STATUS_DOT = {
  todo:        '#6E6E80',
  in_progress: '#10B981',
  in_review:   '#F59E0B',
  blocked:     '#EF4444',
  done:        '#3B82F6',
  running:     '#10B981',
  idle:        '#6E6E80',
  error:       '#EF4444',
  offline:     '#565666',
  online:      '#10B981',
};

// ── Stat card ─────────────────────────────────────────────────────────────────

function StatCard({ label, value, sub, accent = C.accent, to }) {
  const nav = useNavigate();
  return (
    <button
      onClick={to ? () => nav(to) : undefined}
      className="group text-left transition-all duration-200"
      style={{
        background: C.surface,
        border: `1px solid ${C.border}`,
        borderRadius: '12px',
        padding: '16px',
        cursor: to ? 'pointer' : 'default',
      }}
      onMouseEnter={e => { if (to) { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'; e.currentTarget.style.background = '#18181D'; }}}
      onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.background = C.surface; }}
      data-testid={`stat-${label.toLowerCase().replace(/\s/g,'-')}`}
    >
      <div className="text-[28px] font-bold tracking-tight leading-none mb-1"
        style={{ fontFamily: 'var(--font-main)', color: accent }}>{value ?? '—'}</div>
      <div className="text-[11px] font-medium" style={{ color: C.secondary }}>{label}</div>
      {sub && <div className="text-[9px] font-mono mt-0.5" style={{ color: C.muted }}>{sub}</div>}
    </button>
  );
}

// ── Runtime row ────────────────────────────────────────────────────────────────

function RuntimeRow({ runtime }) {
  const h = runtime.health || {};
  const available = h.available;
  const circuitOpen = runtime.circuit_open;
  const status = circuitOpen ? 'circuit-open' : available ? 'online' : 'offline';
  const dotColor = { online: '#10B981', offline: '#565666', 'circuit-open': '#F59E0B' }[status] || '#565666';
  return (
    <div className="flex items-center justify-between py-2.5 border-b last:border-0"
      style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
      <div className="flex items-center gap-2.5">
        <div className="w-2 h-2 rounded-full shrink-0" style={{ background: dotColor }} />
        <div>
          <div className="text-[12px] font-medium" style={{ color: C.secondary }}>{runtime.display_name}</div>
          <div className="text-[10px] font-mono" style={{ color: C.muted }}>{runtime.tier?.replace('_', ' ')}</div>
        </div>
      </div>
      <div className="text-right">
        <div className="text-[10px] font-mono" style={{ color: available && !circuitOpen ? '#10B981' : C.muted }}>
          {circuitOpen ? 'circuit open' : available ? 'online' : available === null ? 'checking' : 'offline'}
        </div>
        {h.latency_ms != null && (
          <div className="text-[9px] font-mono" style={{ color: C.muted }}>{Math.round(h.latency_ms)}ms</div>
        )}
      </div>
    </div>
  );
}

// ── Task row ───────────────────────────────────────────────────────────────────

function TaskRow({ task, onClick }) {
  const dot = STATUS_DOT[task.status] || C.muted;
  const statusLabel = task.status?.replace('_', ' ') || 'todo';
  return (
    <button
      onClick={onClick}
      className="w-full flex items-start gap-2.5 py-2.5 px-3 rounded-lg text-left transition-colors"
      style={{ '--tw-bg': 'transparent' }}
      onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.015)'}
      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
    >
      <div className="w-1.5 h-1.5 rounded-full mt-1.5 shrink-0" style={{ background: dot }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[12px] font-medium truncate" style={{ color: C.secondary }}>{task.title}</span>
          {task.priority === 'urgent' && (
            <span className="text-[9px] font-mono uppercase" style={{ color: '#EF4444' }}>URGENT</span>
          )}
        </div>
        <div className="flex items-center gap-2 flex-wrap">
          <span className="text-[9px] font-mono capitalize" style={{ color: C.tertiary }}>{statusLabel}</span>
          {task.agent_id && (
            <span className="text-[9px] font-mono" style={{ color: C.muted }}>@{task.agent_id}</span>
          )}
          <span className="text-[9px]" style={{ color: C.muted }}>{relTime(task.updated_at)}</span>
        </div>
      </div>
    </button>
  );
}

// ── Execution row (live feed) ──────────────────────────────────────────────────

function ExecRow({ decision }) {
  const dot = decision.escalated ? '#F59E0B' : '#10B981';
  return (
    <div className="flex items-start gap-3 px-4 py-3 border-b last:border-0"
      style={{ borderColor: 'rgba(255,255,255,0.04)' }}>
      <div className="mt-1 shrink-0 w-2 h-2 rounded-full" style={{ background: dot }} />
      <div className="flex-1 min-w-0">
        <div className="flex items-center gap-2 mb-0.5">
          <span className="text-[12px] font-medium truncate" style={{ color: '#D8D8E8' }}>{decision.task_id}</span>
          {decision.escalated && (
            <span className="shrink-0 px-1.5 py-px text-[8px] font-mono uppercase border"
              style={{ borderColor: 'rgba(245,158,11,0.25)', background: 'rgba(245,158,11,0.08)', color: '#F59E0B' }}>
              escalated
            </span>
          )}
        </div>
        <div className="flex items-center gap-3 text-[10px] font-mono" style={{ color: C.muted }}>
          <span>{decision.selected_runtime_id}</span>
          <span style={{ color: '#3A3A4A' }}>·</span>
          <span style={{ color: decision.provider_used === 'ollama' ? '#10B981' : C.tertiary }}>
            {decision.model_used || decision.task_type}
          </span>
          {decision.escalation_reason && (
            <>
              <span style={{ color: '#3A3A4A' }}>·</span>
              <span className="truncate max-w-[150px]" style={{ color: 'rgba(245,158,11,0.8)' }}>
                {decision.escalation_reason}
              </span>
            </>
          )}
        </div>
      </div>
      <div className="text-[9px] font-mono shrink-0 mt-0.5" style={{ color: C.muted }}>
        {relTime(decision.timestamp)}
      </div>
    </div>
  );
}

// ── Section header ─────────────────────────────────────────────────────────────

function SectionHeader({ title, to, count, loading, onRefresh }) {
  const nav = useNavigate();
  return (
    <div className="flex items-center justify-between px-4 py-3 border-b"
      style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
      <div className="flex items-center gap-2">
        <span className="text-[11px] font-semibold tracking-wide uppercase font-mono"
          style={{ color: C.tertiary }}>{title}</span>
        {count != null && (
          <span className="text-[9px] font-mono px-1.5 py-0.5 rounded"
            style={{ background: 'rgba(255,255,255,0.05)', color: C.muted }}>{count}</span>
        )}
      </div>
      <div className="flex items-center gap-2">
        {onRefresh && (
          <button onClick={onRefresh} disabled={loading}
            className="transition-colors disabled:opacity-40"
            style={{ color: C.muted }}
            onMouseEnter={e => e.currentTarget.style.color = C.secondary}
            onMouseLeave={e => e.currentTarget.style.color = C.muted}>
            <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
          </button>
        )}
        {to && (
          <button onClick={() => nav(to)}
            className="text-[10px] font-mono transition-colors"
            style={{ color: C.muted }}
            onMouseEnter={e => e.currentTarget.style.color = C.secondary}
            onMouseLeave={e => e.currentTarget.style.color = C.muted}>
            View all →
          </button>
        )}
      </div>
    </div>
  );
}

// ── Card wrapper ───────────────────────────────────────────────────────────────

function Card({ children, className = '' }) {
  return (
    <div className={`overflow-hidden ${className}`}
      style={{ background: C.surface, border: `1px solid ${C.border}`, borderRadius: '12px' }}>
      {children}
    </div>
  );
}

// ── Infrastructure health row ──────────────────────────────────────────────────

function InfraItem({ label, ok, icon: Icon }) {
  return (
    <div className="flex items-center gap-2 px-3 py-2.5 rounded-lg border"
      style={{
        borderColor: ok ? 'rgba(16,185,129,0.15)' : 'rgba(255,255,255,0.05)',
        background: ok ? 'rgba(16,185,129,0.05)' : 'rgba(255,255,255,0.02)',
      }}>
      <div className="w-1.5 h-1.5 rounded-full shrink-0"
        style={{ background: ok ? '#10B981' : C.muted }} />
      <span className="text-[11px] font-medium"
        style={{ color: ok ? '#10B981' : C.muted }}>{label}</span>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function ControlPlanePage() {
  const nav = useNavigate();
  const [loading, setLoading] = useState(true);
  const [rLoading, setRLoading] = useState(false);
  const [tLoading, setTLoading] = useState(false);

  const [health, setHealth]       = useState(null);
  const [stats, setStats]         = useState(null);
  const [runtimes, setRuntimes]   = useState([]);
  const [tasks, setTasks]         = useState([]);
  const [dueSoon, setDueSoon]     = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [alertDismissed, setAlertDismissed] = useState(false);
  const [error, setError]         = useState('');

  const loadAll = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      await Promise.allSettled([
        healthCheck().then(r => setHealth(r.data)),
        getStats().then(r => setStats(r.data)),
        listRuntimes().then(r => setRuntimes(r.data.runtimes || [])),
        listTasks({ limit: 10 }).then(r => setTasks(r.data.tasks || [])),
        getDueSoonTasks(24).then(r => setDueSoon(r.data.tasks || [])),
        getDecisionLog(20).then(r => setDecisions(r.data.decisions || [])),
      ]);
    } catch {
      setError('Some data sources unavailable — check backend connectivity.');
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
  const blockedTasks    = tasks.filter(t => t.status === 'blocked');
  const inReviewTasks   = tasks.filter(t => t.status === 'in_review');
  const activeTasks     = tasks.filter(t => t.status === 'in_progress');
  const queuedTasks     = tasks.filter(t => t.status === 'todo');
  const offlineRuntimes = runtimes.filter(r => r.circuit_open);
  const showAlert = !alertDismissed && (blockedTasks.length > 0 || inReviewTasks.length > 0 || offlineRuntimes.length > 0);

  const costSaved  = stats?.cost_saved_usd != null ? `$${stats.cost_saved_usd.toFixed(2)}` : '—';
  const tokenUsed  = stats?.total_tokens   != null ? `${(stats.total_tokens / 1000).toFixed(1)}k` : '—';
  const localRatio = stats?.local_ratio    != null ? `${Math.round(stats.local_ratio * 100)}%` : '—';

  const today = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });

  return (
    <div className="h-full overflow-y-auto p-5 lg:p-6 space-y-5 animate-fade-in"
      data-testid="control-plane-page">

      {/* ── Header ── */}
      <div className="flex items-start justify-between">
        <div>
          <div className="flex items-center gap-2 mb-1">
            <div className={`w-1.5 h-1.5 rounded-full ${loading ? 'bg-amber-400' : isHealthy ? 'bg-emerald-500 animate-pulse' : 'bg-amber-400'}`} />
            <span className="text-[10px] font-mono tracking-[0.18em] uppercase" style={{ color: C.muted }}>
              {loading ? 'Loading…' : isHealthy ? 'All systems operational' : 'Partial outage detected'}
            </span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'var(--font-main)', color: C.primary }}>
            Control Plane
          </h1>
          <p className="text-[12px] mt-0.5" style={{ color: C.tertiary }}>{today} · LLM Relay v3.1</p>
        </div>
        <button onClick={loadAll} disabled={loading}
          className="flex items-center gap-2 px-3 py-2 text-[11px] font-mono uppercase tracking-wider border rounded-lg transition-colors disabled:opacity-40"
          style={{ borderColor: 'rgba(255,255,255,0.1)', color: C.tertiary }}
          onMouseEnter={e => { e.currentTarget.style.color = C.primary; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = C.tertiary; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.1)'; }}>
          <RefreshCw size={11} className={loading ? 'animate-spin' : ''} />
          Refresh
        </button>
      </div>

      {/* ── Alert bar ── */}
      {showAlert && (
        <div className="flex items-center gap-3 px-4 py-3 rounded-lg border"
          style={{ background: 'rgba(245,158,11,0.08)', borderColor: 'rgba(245,158,11,0.2)' }}>
          <AlertTriangle size={13} className="text-amber-400 shrink-0" />
          <div className="flex-1 text-[11px] font-mono text-amber-300">
            {blockedTasks.length > 0 && (
              <span className="mr-3">
                <strong>{blockedTasks.length} task{blockedTasks.length > 1 ? 's' : ''} blocked</strong> — needs attention
              </span>
            )}
            {inReviewTasks.length > 0 && (
              <span className="mr-3">
                <strong>{inReviewTasks.length} task{inReviewTasks.length > 1 ? 's' : ''} in review</strong> — awaiting approval
              </span>
            )}
            {offlineRuntimes.length > 0 && (
              <span>
                <strong>{offlineRuntimes.map(r => r.display_name).join(', ')}</strong> — circuit open
              </span>
            )}
          </div>
          <button onClick={() => setAlertDismissed(true)}
            style={{ color: C.tertiary }}
            onMouseEnter={e => e.currentTarget.style.color = C.primary}
            onMouseLeave={e => e.currentTarget.style.color = C.tertiary}>
            <XCircle size={13} />
          </button>
        </div>
      )}

      {error && (
        <div className="flex items-center gap-2 px-4 py-3 rounded-lg border text-[12px] text-amber-400"
          style={{ background: 'rgba(245,158,11,0.06)', borderColor: 'rgba(245,158,11,0.15)' }}>
          <AlertTriangle size={13} /> {error}
        </div>
      )}

      {/* ── Stat row ── */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-5 gap-3">
        <StatCard label="Active Agents" value={activeTasks.length} sub={`${runtimes.filter(r=>r.health?.available).length} runtimes`} accent="#10B981" to="/agents" />
        <StatCard label="Open Tasks"    value={queuedTasks.length + activeTasks.length} sub={`${activeTasks.length} running`} accent={C.accent} to="/tasks" />
        <StatCard label="In Review"     value={inReviewTasks.length} sub="awaiting approval" accent="#F59E0B" to="/tasks" />
        <StatCard label="Cost Saved"    value={costSaved} sub="vs cloud APIs" accent="#10B981" />
        <StatCard label="Local Ratio"   value={localRatio} sub="requests on-device" accent="#8B5CF6" to="/observability" />
      </div>

      {/* ── Main grid ── */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Live execution feed (2-col) */}
        <Card className="lg:col-span-2">
          <SectionHeader title="Live Execution Feed" to="/observability" />
          {decisions.length === 0 ? (
            <div className="py-10 text-center text-[11px] font-mono" style={{ color: C.muted }}>
              No routing decisions yet — submit a task to see live activity
            </div>
          ) : (
            <div>
              {decisions.slice(0, 8).map((d, i) => <ExecRow key={i} decision={d} />)}
            </div>
          )}
        </Card>

        {/* Right column */}
        <div className="space-y-4">

          {/* Agents */}
          <Card>
            <SectionHeader title="Runtimes" to="/runtimes" onRefresh={reloadRuntimes} loading={rLoading} />
            {runtimes.length === 0 ? (
              <div className="py-6 text-center text-[11px] font-mono px-4" style={{ color: C.muted }}>
                No runtimes configured
              </div>
            ) : (
              <div className="px-4">
                {runtimes.map(r => <RuntimeRow key={r.runtime_id} runtime={r} />)}
              </div>
            )}
          </Card>

          {/* Task queue */}
          <Card>
            <SectionHeader title="Task Queue" to="/tasks" count={tasks.length} onRefresh={reloadTasks} loading={tLoading} />
            {tasks.length === 0 ? (
              <div className="py-6 text-center text-[11px] font-mono px-4" style={{ color: C.muted }}>
                No tasks yet
              </div>
            ) : (
              <div>
                {activeTasks.slice(0, 3).map(t => (
                  <TaskRow key={t.task_id} task={t} onClick={() => nav('/tasks')} />
                ))}
                {queuedTasks.slice(0, 3).map(t => (
                  <TaskRow key={t.task_id} task={t} onClick={() => nav('/tasks')} />
                ))}
              </div>
            )}
          </Card>
        </div>
      </div>

      {/* ── Upcoming schedules / due soon ── */}
      {dueSoon.length > 0 && (
        <Card>
          <SectionHeader title="Due Soon" count={dueSoon.length} to="/activity" />
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 divide-y sm:divide-y-0 sm:divide-x"
            style={{ '--tw-divide-color': 'rgba(255,255,255,0.05)' }}>
            {dueSoon.slice(0, 3).map(t => {
              const now = Date.now() / 1000;
              const hoursLeft = t.due_date ? Math.max(0, (t.due_date - now) / 3600) : null;
              return (
                <div key={t.task_id} className="px-4 py-3">
                  <div className="text-[12px] font-medium mb-0.5" style={{ color: C.secondary }}>{t.title}</div>
                  <div className="text-[9px] font-mono" style={{ color: C.muted }}>
                    {t.agent_id ? `@${t.agent_id} · ` : ''}
                    {hoursLeft != null ? `Due in ${hoursLeft < 1 ? `${Math.round(hoursLeft * 60)}m` : `${Math.round(hoursLeft)}h`}` : 'Due soon'}
                  </div>
                </div>
              );
            })}
          </div>
        </Card>
      )}

      {/* ── Infrastructure health ── */}
      <Card>
        <SectionHeader title="Infrastructure" to="/providers" />
        <div className="p-4 grid grid-cols-2 sm:grid-cols-4 gap-3">
          <InfraItem label="MongoDB"   ok={health?.mongo}                icon={Database} />
          <InfraItem label="Ollama"    ok={health?.ollama}               icon={Cpu} />
          <InfraItem label="Langfuse"  ok={stats?.langfuse_configured}   icon={BarChart3} />
          <InfraItem label="Scheduler" ok={health?.scheduler}            icon={Calendar} />
        </div>
      </Card>

    </div>
  );
}
