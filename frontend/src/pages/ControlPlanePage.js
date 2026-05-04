import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  Activity,
  AlertTriangle,
  ArrowRight,
  Bot,
  BrainCircuit,
  Calendar,
  Cpu,
  Database,
  FolderGit2,
  Layers,
  RefreshCw,
  Rocket,
  ShieldCheck,
  Sparkles,
  TrendingUp,
} from 'lucide-react';
import {
  fmtErr,
  getDecisionLog,
  getDueSoonTasks,
  getSavings,
  getStats,
  getUsage,
  healthCheck,
  listAgents,
  listProviders,
  listRuntimes,
  listSchedules,
  listTasks,
} from '../api';

const C = {
  surface: 'var(--bg-surface)',
  border: 'var(--border)',
  primary: 'var(--text-primary)',
  secondary: 'var(--text-secondary)',
  tertiary: 'var(--text-tertiary)',
  muted: 'var(--text-muted)',
  accent: 'var(--accent)',
};

function cls(...parts) {
  return parts.filter(Boolean).join(' ');
}

function toMillis(value) {
  if (value == null) return 0;
  if (typeof value === 'number') {
    return value > 1e12 ? value : value * 1000;
  }
  const parsed = new Date(value).getTime();
  return Number.isNaN(parsed) ? 0 : parsed;
}

function relTime(value) {
  const timestamp = toMillis(value);
  if (!timestamp) return '—';
  const diff = Date.now() - timestamp;
  if (diff < 60_000) return `${Math.max(1, Math.round(diff / 1000))}s ago`;
  if (diff < 3_600_000) return `${Math.round(diff / 60_000)}m ago`;
  if (diff < 86_400_000) return `${Math.round(diff / 3_600_000)}h ago`;
  return `${Math.round(diff / 86_400_000)}d ago`;
}

function formatMoney(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `$${Number(value).toFixed(2)}`;
}

function formatCount(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return Number(value).toLocaleString();
}

function formatCompactTokens(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  const total = Number(value);
  if (total >= 1_000_000) return `${(total / 1_000_000).toFixed(1)}M`;
  if (total >= 1_000) return `${(total / 1_000).toFixed(1)}k`;
  return `${total}`;
}

function formatPercent(value) {
  if (value == null || Number.isNaN(Number(value))) return '—';
  return `${Math.round(Number(value) * 100)}%`;
}

function formatStatusLabel(value) {
  if (!value) return 'Unknown';
  return String(value)
    .replace(/_/g, ' ')
    .replace(/\b\w/g, (char) => char.toUpperCase());
}

function sortByUpdated(items) {
  return [...items].sort((left, right) => toMillis(right.updated_at || right.updatedAt || right.last_run) - toMillis(left.updated_at || left.updatedAt || left.last_run));
}

function statusColor(status) {
  const value = String(status || '').toLowerCase();
  if (value === 'running' || value === 'active' || value === 'online' || value === 'completed') {
    return '#10B981';
  }
  if (value === 'in_progress' || value === 'provisioning' || value === 'in_review') {
    return '#F59E0B';
  }
  if (value === 'blocked' || value === 'failed' || value === 'error' || value === 'offline') {
    return '#EF4444';
  }
  return C.muted;
}

function PageCard({ title, description, actionLabel, onAction, children, className = '' }) {
  return (
    <section
      className={cls('overflow-hidden rounded-2xl border', className)}
      style={{ background: C.surface, borderColor: C.border }}
    >
      <div className="flex items-start justify-between gap-3 border-b px-4 py-4 sm:px-5" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="min-w-0">
          <h2 className="text-sm font-semibold text-white">{title}</h2>
          {description ? (
            <p className="mt-1 text-xs leading-relaxed" style={{ color: C.tertiary }}>{description}</p>
          ) : null}
        </div>
        {onAction ? (
          <button
            onClick={onAction}
            className="shrink-0 text-[10px] font-mono uppercase tracking-[0.18em] transition-colors"
            style={{ color: C.muted }}
            onMouseEnter={(event) => { event.currentTarget.style.color = C.secondary; }}
            onMouseLeave={(event) => { event.currentTarget.style.color = C.muted; }}
          >
            {actionLabel || 'Open'}
          </button>
        ) : null}
      </div>
      <div className="p-4 sm:p-5">{children}</div>
    </section>
  );
}

function MetricTile({ label, value, supportingText, accent = C.accent }) {
  return (
    <div className="rounded-xl border px-4 py-4" style={{ borderColor: 'rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.02)' }}>
      <div className="text-[10px] font-mono uppercase tracking-[0.18em]" style={{ color: C.muted }}>{label}</div>
      <div className="mt-2 text-2xl font-semibold tracking-tight" style={{ color: accent }}>{value}</div>
      {supportingText ? (
        <div className="mt-2 text-xs leading-relaxed" style={{ color: C.tertiary }}>{supportingText}</div>
      ) : null}
    </div>
  );
}

function HealthPill({ label, ok }) {
  return (
    <div
      className="inline-flex items-center gap-2 rounded-full border px-3 py-1.5 text-[11px]"
      style={{
        borderColor: ok ? 'rgba(16,185,129,0.18)' : 'rgba(255,255,255,0.08)',
        background: ok ? 'rgba(16,185,129,0.08)' : 'rgba(255,255,255,0.03)',
        color: ok ? '#10B981' : C.tertiary,
      }}
    >
      <span className="h-1.5 w-1.5 rounded-full" style={{ background: ok ? '#10B981' : C.muted }} />
      {label}
    </div>
  );
}

function QuickAction({ icon: Icon, label, description, onClick }) {
  return (
    <button
      onClick={onClick}
      className="group flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left transition-all duration-150"
      style={{ background: 'rgba(255,255,255,0.02)', borderColor: 'rgba(255,255,255,0.08)' }}
      onMouseEnter={(event) => {
        event.currentTarget.style.borderColor = 'rgba(255,255,255,0.14)';
        event.currentTarget.style.background = 'rgba(255,255,255,0.04)';
      }}
      onMouseLeave={(event) => {
        event.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
        event.currentTarget.style.background = 'rgba(255,255,255,0.02)';
      }}
    >
      <div className="mt-0.5 flex h-9 w-9 shrink-0 items-center justify-center rounded-lg border" style={{ borderColor: 'rgba(0,47,167,0.25)', background: 'rgba(0,47,167,0.12)' }}>
        <Icon size={16} className="text-[#7FA1FF]" />
      </div>
      <div className="min-w-0 flex-1">
        <div className="flex items-center justify-between gap-3">
          <span className="text-sm font-medium text-white">{label}</span>
          <ArrowRight size={14} className="shrink-0 text-[#5E6B87] transition-transform duration-150 group-hover:translate-x-0.5 group-hover:text-white" />
        </div>
        <p className="mt-1 text-xs leading-relaxed" style={{ color: C.tertiary }}>{description}</p>
      </div>
    </button>
  );
}

function EmptyState({ title, description }) {
  return (
    <div className="rounded-xl border border-dashed px-4 py-10 text-center" style={{ borderColor: 'rgba(255,255,255,0.10)', background: 'rgba(255,255,255,0.02)' }}>
      <p className="text-sm font-medium text-white">{title}</p>
      <p className="mt-2 text-xs leading-relaxed" style={{ color: C.tertiary }}>{description}</p>
    </div>
  );
}

function TaskPreviewRow({ task, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-start gap-3 rounded-xl border px-4 py-3 text-left transition-colors"
      style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}
      onMouseEnter={(event) => { event.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
      onMouseLeave={(event) => { event.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
    >
      <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: statusColor(task.status) }} />
      <div className="min-w-0 flex-1">
        <div className="flex items-center gap-2">
          <p className="truncate text-sm font-medium text-white">{task.title || task.name}</p>
          {task.priority === 'urgent' ? (
            <span className="rounded-full border px-2 py-0.5 text-[9px] font-mono uppercase tracking-[0.18em] text-red-300" style={{ borderColor: 'rgba(239,68,68,0.25)', background: 'rgba(239,68,68,0.10)' }}>
              Urgent
            </span>
          ) : null}
        </div>
        <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px]" style={{ color: C.tertiary }}>
          <span>{formatStatusLabel(task.status)}</span>
          {task.agent_id ? <span>• @{task.agent_id}</span> : null}
          <span>• {relTime(task.updated_at || task.updatedAt)}</span>
        </div>
      </div>
    </button>
  );
}

function DecisionPreviewRow({ decision }) {
  return (
    <div className="rounded-xl border px-4 py-3" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}>
      <div className="flex items-start gap-3">
        <span className="mt-1.5 h-2 w-2 shrink-0 rounded-full" style={{ background: decision.escalated ? '#F59E0B' : '#10B981' }} />
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <p className="truncate text-sm font-medium text-white">{decision.task_id || decision.id || 'Runtime decision'}</p>
            {decision.escalated ? (
              <span className="rounded-full border px-2 py-0.5 text-[9px] font-mono uppercase tracking-[0.18em] text-amber-300" style={{ borderColor: 'rgba(245,158,11,0.25)', background: 'rgba(245,158,11,0.10)' }}>
                Escalated
              </span>
            ) : null}
          </div>
          <div className="mt-1 flex flex-wrap items-center gap-2 text-[11px]" style={{ color: C.tertiary }}>
            {decision.selected_runtime_id ? <span>{decision.selected_runtime_id}</span> : null}
            {decision.model_used || decision.task_type ? <span>• {decision.model_used || decision.task_type}</span> : null}
            <span>• {relTime(decision.timestamp)}</span>
          </div>
          {decision.escalation_reason ? (
            <p className="mt-2 text-xs leading-relaxed text-amber-300/90">{decision.escalation_reason}</p>
          ) : null}
        </div>
      </div>
    </div>
  );
}

function AgentPreviewRow({ agent }) {
  return (
    <div className="flex items-center justify-between gap-3 rounded-xl border px-4 py-3" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}>
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-white">{agent.name}</p>
        <p className="mt-1 truncate text-[11px]" style={{ color: C.tertiary }}>
          {agent.role || 'General agent'}
          {agent.preferred_runtime ? ` • ${agent.preferred_runtime}` : ''}
        </p>
      </div>
      <span className="shrink-0 rounded-full border px-2 py-1 text-[10px] font-mono uppercase tracking-[0.18em]" style={{ borderColor: `${statusColor(agent.status)}33`, color: statusColor(agent.status), background: `${statusColor(agent.status)}12` }}>
        {formatStatusLabel(agent.status || 'idle')}
      </span>
    </div>
  );
}

function ProviderPreviewRow({ provider }) {
  const isPriority = provider.provider_id === 'nvidia-nim';
  return (
    <div className="rounded-xl border px-4 py-3" style={{ borderColor: isPriority ? 'rgba(0,47,167,0.24)' : 'rgba(255,255,255,0.06)', background: isPriority ? 'rgba(0,47,167,0.10)' : 'rgba(255,255,255,0.02)' }}>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <div className="flex flex-wrap items-center gap-2">
            <p className="truncate text-sm font-medium text-white">{provider.name}</p>
            {isPriority ? (
              <span className="rounded-full border px-2 py-0.5 text-[9px] font-mono uppercase tracking-[0.18em] text-[#BBD0FF]" style={{ borderColor: 'rgba(127,161,255,0.25)', background: 'rgba(127,161,255,0.12)' }}>
                Priority
              </span>
            ) : null}
            {provider.is_default ? (
              <span className="rounded-full border px-2 py-0.5 text-[9px] font-mono uppercase tracking-[0.18em] text-emerald-300" style={{ borderColor: 'rgba(16,185,129,0.25)', background: 'rgba(16,185,129,0.10)' }}>
                Default
              </span>
            ) : null}
          </div>
          <p className="mt-1 truncate text-[11px]" style={{ color: C.tertiary }}>
            {provider.default_model || provider.type}
          </p>
        </div>
        <span className="shrink-0 text-[10px] font-mono uppercase tracking-[0.18em]" style={{ color: provider.status === 'configured' ? '#10B981' : C.muted }}>
          {provider.status === 'configured' ? 'Ready' : 'Setup'}
        </span>
      </div>
    </div>
  );
}

function SchedulePreviewRow({ schedule }) {
  return (
    <div className="rounded-xl border px-4 py-3" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-white">{schedule.name}</p>
          <p className="mt-1 truncate text-[11px]" style={{ color: C.tertiary }}>
            {schedule.cron || schedule.schedule || 'Manual trigger'}
          </p>
        </div>
        <span className="shrink-0 rounded-full border px-2 py-1 text-[10px] font-mono uppercase tracking-[0.18em]" style={{ borderColor: `${statusColor(schedule.status)}33`, color: statusColor(schedule.status), background: `${statusColor(schedule.status)}12` }}>
          {formatStatusLabel(schedule.status || 'active')}
        </span>
      </div>
    </div>
  );
}

function RuntimePreviewRow({ runtime }) {
  const available = runtime.health?.available;
  const tone = runtime.circuit_open ? '#F59E0B' : available ? '#10B981' : '#EF4444';
  return (
    <div className="rounded-xl border px-4 py-3" style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}>
      <div className="flex items-center justify-between gap-3">
        <div className="min-w-0">
          <p className="truncate text-sm font-medium text-white">{runtime.display_name}</p>
          <p className="mt-1 truncate text-[11px]" style={{ color: C.tertiary }}>
            {runtime.tier ? runtime.tier.replace(/_/g, ' ') : 'runtime'}
            {runtime.health?.latency_ms != null ? ` • ${Math.round(runtime.health.latency_ms)}ms` : ''}
          </p>
        </div>
        <span className="shrink-0 rounded-full border px-2 py-1 text-[10px] font-mono uppercase tracking-[0.18em]" style={{ borderColor: `${tone}33`, color: tone, background: `${tone}12` }}>
          {runtime.circuit_open ? 'Circuit open' : available ? 'Online' : available === null ? 'Checking' : 'Offline'}
        </span>
      </div>
    </div>
  );
}

function RecentPageRow({ page, onClick }) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-start justify-between gap-3 rounded-xl border px-4 py-3 text-left transition-colors"
      style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}
      onMouseEnter={(event) => { event.currentTarget.style.background = 'rgba(255,255,255,0.04)'; }}
      onMouseLeave={(event) => { event.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
    >
      <div className="min-w-0">
        <p className="truncate text-sm font-medium text-white">{page.title}</p>
        <p className="mt-1 truncate text-[11px]" style={{ color: C.tertiary }}>/{page.slug}</p>
      </div>
      <span className="shrink-0 text-[11px]" style={{ color: C.muted }}>{relTime(page.updated_at)}</span>
    </button>
  );
}

export default function ControlPlanePage() {
  const navigate = useNavigate();
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState('');
  const [health, setHealth] = useState(null);
  const [stats, setStats] = useState(null);
  const [usage, setUsage] = useState(null);
  const [savings, setSavings] = useState(null);
  const [runtimes, setRuntimes] = useState([]);
  const [tasks, setTasks] = useState([]);
  const [dueSoon, setDueSoon] = useState([]);
  const [decisions, setDecisions] = useState([]);
  const [agents, setAgents] = useState([]);
  const [providers, setProviders] = useState([]);
  const [schedules, setSchedules] = useState([]);

  const loadAll = useCallback(async ({ isRefresh = false } = {}) => {
    if (isRefresh) {
      setRefreshing(true);
    } else {
      setLoading(true);
    }
    setError('');

    const results = await Promise.allSettled([
      healthCheck(),
      getStats(),
      getUsage('month'),
      getSavings('month', 'day'),
      listRuntimes(),
      listTasks({ limit: 12 }),
      getDueSoonTasks(24),
      getDecisionLog(12),
      listAgents(),
      listProviders(),
      listSchedules(),
    ]);

    const failures = [];
    const [
      healthResult,
      statsResult,
      usageResult,
      savingsResult,
      runtimesResult,
      tasksResult,
      dueSoonResult,
      decisionsResult,
      agentsResult,
      providersResult,
      schedulesResult,
    ] = results;

    if (healthResult.status === 'fulfilled') setHealth(healthResult.value.data);
    else failures.push(healthResult.reason);

    if (statsResult.status === 'fulfilled') setStats(statsResult.value.data);
    else failures.push(statsResult.reason);

    if (usageResult.status === 'fulfilled') setUsage(usageResult.value.data);
    else failures.push(usageResult.reason);

    if (savingsResult.status === 'fulfilled') setSavings(savingsResult.value.data);
    else failures.push(savingsResult.reason);

    if (runtimesResult.status === 'fulfilled') setRuntimes(runtimesResult.value.data.runtimes || []);
    else failures.push(runtimesResult.reason);

    if (tasksResult.status === 'fulfilled') setTasks(tasksResult.value.data.tasks || []);
    else failures.push(tasksResult.reason);

    if (dueSoonResult.status === 'fulfilled') setDueSoon(dueSoonResult.value.data.tasks || []);
    else failures.push(dueSoonResult.reason);

    if (decisionsResult.status === 'fulfilled') setDecisions(decisionsResult.value.data.decisions || []);
    else failures.push(decisionsResult.reason);

    if (agentsResult.status === 'fulfilled') setAgents(agentsResult.value.data.agents || []);
    else failures.push(agentsResult.reason);

    if (providersResult.status === 'fulfilled') setProviders(providersResult.value.data.providers || []);
    else failures.push(providersResult.reason);

    if (schedulesResult.status === 'fulfilled') setSchedules(schedulesResult.value.data.schedules || []);
    else failures.push(schedulesResult.reason);

    if (failures.length > 0) {
      setError(`Some dashboard data could not be loaded. ${fmtErr(failures[0])}`);
    }

    setLoading(false);
    setRefreshing(false);
  }, []);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const taskList = useMemo(() => sortByUpdated(tasks), [tasks]);
  const activeTasks = useMemo(() => taskList.filter((task) => ['todo', 'in_progress', 'in_review', 'blocked'].includes(task.status)), [taskList]);
  const activeSchedules = useMemo(() => sortByUpdated(schedules).filter((schedule) => schedule.status !== 'completed').slice(0, 4), [schedules]);
  const preferredProviders = useMemo(() => {
    return [...providers].sort((left, right) => {
      if (left.provider_id === 'nvidia-nim') return -1;
      if (right.provider_id === 'nvidia-nim') return 1;
      if (left.is_default) return -1;
      if (right.is_default) return 1;
      return String(left.name || '').localeCompare(String(right.name || ''));
    });
  }, [providers]);
  const preferredAgents = useMemo(() => sortByUpdated(agents).slice(0, 4), [agents]);
  const preferredRuntimes = useMemo(() => sortByUpdated(runtimes).slice(0, 4), [runtimes]);
  const recentPages = stats?.recent_pages || [];

  const monthlySummary = savings?.summary || {};
  const monthlySaved = savings?.period_saved_usd ?? monthlySummary.total_savings_usd ?? 0;
  const requestCount = usage?.total_requests ?? monthlySummary.total_requests ?? 0;
  const totalTokens = usage?.total_tokens ?? monthlySummary.total_tokens ?? 0;
  const localRatio = usage?.local_ratio ?? stats?.local_ratio ?? null;
  const activeProvider = preferredProviders[0] || null;
  const nvidiaProvider = preferredProviders.find((provider) => provider.provider_id === 'nvidia-nim') || null;
  const runningRuntimes = runtimes.filter((runtime) => runtime.health?.available && !runtime.circuit_open).length;
  const onlineAgents = agents.filter((agent) => ['running', 'idle', 'done'].includes(String(agent.status || '').toLowerCase())).length;
  const blockedCount = activeTasks.filter((task) => task.status === 'blocked').length;
  const reviewCount = activeTasks.filter((task) => task.status === 'in_review').length;
  const isHealthy = health?.status === 'ok';
  const today = new Date().toLocaleDateString('en-US', { month: 'long', day: 'numeric', year: 'numeric' });

  return (
    <div className="h-full overflow-y-auto p-4 sm:p-5 lg:p-6" data-testid="control-plane-page">
      <div className="mx-auto flex max-w-7xl flex-col gap-5">
        <header className="rounded-3xl border px-5 py-5 sm:px-6" style={{ background: 'linear-gradient(135deg, rgba(0,47,167,0.18), rgba(20,20,24,0.96) 45%, rgba(20,20,24,0.96) 100%)', borderColor: 'rgba(255,255,255,0.08)' }}>
          <div className="flex flex-col gap-5 xl:flex-row xl:items-start xl:justify-between">
            <div className="max-w-3xl">
              <div className="flex flex-wrap items-center gap-2">
                <span className="inline-flex items-center gap-2 rounded-full border px-3 py-1 text-[11px] font-mono uppercase tracking-[0.18em]" style={{ borderColor: isHealthy ? 'rgba(16,185,129,0.18)' : 'rgba(245,158,11,0.18)', background: isHealthy ? 'rgba(16,185,129,0.10)' : 'rgba(245,158,11,0.10)', color: isHealthy ? '#A7F3D0' : '#FCD34D' }}>
                  <span className="h-1.5 w-1.5 rounded-full" style={{ background: isHealthy ? '#10B981' : '#F59E0B' }} />
                  {loading ? 'Loading dashboard' : isHealthy ? 'System healthy' : 'Attention needed'}
                </span>
                <span className="text-[11px] font-mono uppercase tracking-[0.18em]" style={{ color: C.muted }}>{today}</span>
              </div>

              <h1 className="mt-4 text-3xl font-semibold tracking-[-0.04em] text-white sm:text-4xl">Dashboard</h1>
              <p className="mt-3 max-w-2xl text-sm leading-relaxed sm:text-[15px]" style={{ color: C.secondary }}>
                CompanyHelm-style workspace command center for LLM Relay. Monitor agent work, keep NVIDIA-first routing visible, and move between tasks, chats, and infrastructure without leaving the root dashboard.
              </p>

              <div className="mt-4 flex flex-wrap items-center gap-2">
                <HealthPill label={`${formatCount(activeTasks.length)} open tasks`} ok={activeTasks.length > 0} />
                <HealthPill label={`${formatCount(onlineAgents)} configured agents`} ok={agents.length > 0} />
                <HealthPill label={`${formatCount(runningRuntimes)} runtimes online`} ok={runningRuntimes > 0} />
                <HealthPill label={nvidiaProvider ? 'NVIDIA priority active' : 'NVIDIA not configured'} ok={Boolean(nvidiaProvider)} />
              </div>
            </div>

            <div className="flex flex-col items-stretch gap-3 xl:min-w-[270px]">
              <button
                onClick={() => loadAll({ isRefresh: true })}
                disabled={loading || refreshing}
                className="inline-flex items-center justify-center gap-2 rounded-xl border px-4 py-3 text-[11px] font-mono uppercase tracking-[0.18em] transition-colors disabled:opacity-50"
                style={{ borderColor: 'rgba(255,255,255,0.12)', color: C.secondary }}
              >
                <RefreshCw size={13} className={refreshing ? 'animate-spin' : ''} />
                {refreshing ? 'Refreshing' : 'Refresh dashboard'}
              </button>
              <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 xl:grid-cols-1">
                <QuickAction icon={Rocket} label="Open tasks" description="Review blocked work, move tickets forward, and keep delivery status current." onClick={() => navigate('/tasks')} />
                <QuickAction icon={Sparkles} label="Start a chat" description="Jump into direct chat or the agent workflow without hunting through navigation." onClick={() => navigate('/chat')} />
              </div>
            </div>
          </div>
        </header>

        {error ? (
          <div className="flex items-start gap-3 rounded-2xl border px-4 py-3 text-sm" style={{ borderColor: 'rgba(245,158,11,0.20)', background: 'rgba(245,158,11,0.10)', color: '#FDE68A' }}>
            <AlertTriangle size={16} className="mt-0.5 shrink-0" />
            <span>{error}</span>
          </div>
        ) : null}

        <PageCard
          title="Usage and routing priorities"
          description="A compact view of spend, workload volume, and the provider posture your hosted dashboard is running with."
          actionLabel="Open logs"
          onAction={() => navigate('/logs')}
        >
          <div className="grid gap-3 lg:grid-cols-[minmax(0,2fr)_minmax(0,1fr)]">
            <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
              <MetricTile label="Monthly savings" value={formatMoney(monthlySaved)} supportingText="Calculated from observability savings against commercial equivalents." accent="#10B981" />
              <MetricTile label="Requests" value={formatCount(requestCount)} supportingText="Observed during the selected monthly window." accent="#7FA1FF" />
              <MetricTile label="Tokens" value={formatCompactTokens(totalTokens)} supportingText="Total input and output token volume." accent="#C4B5FD" />
              <MetricTile label="Local ratio" value={formatPercent(localRatio)} supportingText="How often the system stayed on-device or free-tier first." accent="#F59E0B" />
            </div>

            <div className="rounded-2xl border p-4" style={{ borderColor: 'rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.02)' }}>
              <div className="flex items-center gap-2">
                <BrainCircuit size={16} className="text-[#7FA1FF]" />
                <h3 className="text-sm font-medium text-white">Provider priority</h3>
              </div>
              {activeProvider ? (
                <div className="mt-4 space-y-3">
                  <ProviderPreviewRow provider={activeProvider} />
                  <div className="rounded-xl border px-4 py-3 text-xs leading-relaxed" style={{ borderColor: 'rgba(255,255,255,0.06)', color: C.tertiary, background: 'rgba(255,255,255,0.02)' }}>
                    {nvidiaProvider
                      ? `NVIDIA stays at the front of the queue, with ${nvidiaProvider.default_model || 'its configured default model'} prioritized for hosted work.`
                      : 'Configure NVIDIA NIM in Setup to make free hosted inference the default before paid fallbacks.'}
                  </div>
                </div>
              ) : (
                <EmptyState title="No providers configured" description="Open Setup or Providers to connect NVIDIA NIM, Ollama, or your preferred hosted APIs." />
              )}
            </div>
          </div>
        </PageCard>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.35fr)_minmax(0,1fr)]">
          <PageCard
            title="Work in motion"
            description="The same root-dashboard job CompanyHelm handles: highlight what is active, what is blocked, and what needs attention next."
            actionLabel="Open tasks"
            onAction={() => navigate('/tasks')}
          >
            <div className="grid gap-3 sm:grid-cols-3">
              <MetricTile label="Blocked" value={formatCount(blockedCount)} supportingText="Tasks that need intervention before they can move." accent="#EF4444" />
              <MetricTile label="In review" value={formatCount(reviewCount)} supportingText="Items waiting on approval or a final pass." accent="#F59E0B" />
              <MetricTile label="Due soon" value={formatCount(dueSoon.length)} supportingText="Tasks with due dates inside the next 24 hours." accent="#7FA1FF" />
            </div>

            <div className="mt-4 space-y-3">
              {activeTasks.length === 0 ? (
                <EmptyState title="No active tasks" description="Create or import work to make the dashboard light up with operational detail." />
              ) : (
                activeTasks.slice(0, 5).map((task) => (
                  <TaskPreviewRow key={task.task_id || task.id} task={task} onClick={() => navigate('/tasks')} />
                ))
              )}
            </div>
          </PageCard>

          <PageCard
            title="Recent agent decisions"
            description="A simplified activity rail so you can confirm which runtime and model the relay actually chose."
            actionLabel="Open logs"
            onAction={() => navigate('/logs')}
          >
            <div className="space-y-3">
              {decisions.length === 0 ? (
                <EmptyState title="No routing decisions yet" description="Submit a task or chat request to populate the live execution feed." />
              ) : (
                decisions.slice(0, 5).map((decision, index) => (
                  <DecisionPreviewRow key={decision.id || decision.task_id || index} decision={decision} />
                ))
              )}
            </div>
          </PageCard>
        </div>

        <div className="grid gap-5 xl:grid-cols-3">
          <PageCard
            title="Agents"
            description="Top agent profiles and their runtime preferences, mirroring the agent inventory emphasis from CompanyHelm."
            actionLabel="Open agents"
            onAction={() => navigate('/agents')}
          >
            <div className="space-y-3">
              {preferredAgents.length === 0 ? (
                <EmptyState title="No agents configured" description="Create an agent profile to assign work, store prompts, and choose a runtime." />
              ) : (
                preferredAgents.map((agent) => <AgentPreviewRow key={agent.agent_id || agent.id} agent={agent} />)
              )}
            </div>
          </PageCard>

          <PageCard
            title="Providers"
            description="The current model stack, with NVIDIA pinned first whenever it is available."
            actionLabel="Open providers"
            onAction={() => navigate('/providers')}
          >
            <div className="space-y-3">
              {preferredProviders.length === 0 ? (
                <EmptyState title="No providers configured" description="Open Setup to add NVIDIA NIM, Ollama, or other OpenAI-compatible providers." />
              ) : (
                preferredProviders.slice(0, 4).map((provider) => <ProviderPreviewRow key={provider.provider_id} provider={provider} />)
              )}
            </div>
          </PageCard>

          <PageCard
            title="Runtimes & schedules"
            description="Hosted agent execution health alongside the automations that keep your workspace moving."
            actionLabel="Open runtimes"
            onAction={() => navigate('/runtimes')}
          >
            <div className="space-y-4">
              <div>
                <div className="mb-2 flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.18em]" style={{ color: C.muted }}>
                  <Cpu size={12} /> Runtimes
                </div>
                <div className="space-y-3">
                  {preferredRuntimes.length === 0 ? (
                    <EmptyState title="No runtimes configured" description="Enable Hermes, OpenCode, Aider, or other execution backends in Setup." />
                  ) : (
                    preferredRuntimes.map((runtime) => <RuntimePreviewRow key={runtime.runtime_id} runtime={runtime} />)
                  )}
                </div>
              </div>

              <div>
                <div className="mb-2 flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.18em]" style={{ color: C.muted }}>
                  <Calendar size={12} /> Schedules
                </div>
                <div className="space-y-3">
                  {activeSchedules.length === 0 ? (
                    <EmptyState title="No schedules yet" description="Create recurring work to give the dashboard the same automation heartbeat as CompanyHelm." />
                  ) : (
                    activeSchedules.map((schedule) => <SchedulePreviewRow key={schedule.id || schedule.job_id || schedule.name} schedule={schedule} />)
                  )}
                </div>
              </div>
            </div>
          </PageCard>
        </div>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1.1fr)_minmax(0,0.9fr)]">
          <PageCard
            title="Knowledge and source memory"
            description="Recent wiki pages plus a fast path back into your repo-aware knowledge surface."
            actionLabel="Open knowledge"
            onAction={() => navigate('/knowledge')}
          >
            <div className="grid gap-3 md:grid-cols-[minmax(0,1.2fr)_minmax(0,0.8fr)]">
              <div className="space-y-3">
                {recentPages.length === 0 ? (
                  <EmptyState title="No wiki pages yet" description="Add docs, source digests, and repo notes so your agents have shared memory to work from." />
                ) : (
                  recentPages.map((page) => (
                    <RecentPageRow key={page.slug} page={page} onClick={() => navigate('/knowledge')} />
                  ))
                )}
              </div>

              <div className="rounded-2xl border p-4" style={{ borderColor: 'rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.02)' }}>
                <div className="flex items-center gap-2">
                  <FolderGit2 size={16} className="text-[#7FA1FF]" />
                  <h3 className="text-sm font-medium text-white">Workspace snapshot</h3>
                </div>
                <div className="mt-4 space-y-3 text-sm">
                  <div className="flex items-start justify-between gap-3">
                    <span style={{ color: C.tertiary }}>Wiki pages</span>
                    <span className="font-medium text-white">{formatCount(stats?.wiki_pages || 0)}</span>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <span style={{ color: C.tertiary }}>Sources</span>
                    <span className="font-medium text-white">{formatCount(stats?.sources || 0)}</span>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <span style={{ color: C.tertiary }}>Chat sessions</span>
                    <span className="font-medium text-white">{formatCount(stats?.chat_sessions || 0)}</span>
                  </div>
                  <div className="flex items-start justify-between gap-3">
                    <span style={{ color: C.tertiary }}>Activity events</span>
                    <span className="font-medium text-white">{formatCount(stats?.activity_entries || 0)}</span>
                  </div>
                  <button
                    onClick={() => navigate('/knowledge')}
                    className="mt-2 inline-flex items-center gap-2 text-[11px] font-mono uppercase tracking-[0.18em] text-[#AFC4FF]"
                  >
                    Open workspace memory <ArrowRight size={12} />
                  </button>
                </div>
              </div>
            </div>
          </PageCard>

          <PageCard
            title="Infrastructure health"
            description="Keep the core dependencies visible from the top of the workspace, especially on mobile."
            actionLabel="Open settings"
            onAction={() => navigate('/settings')}
          >
            <div className="grid gap-3 sm:grid-cols-2">
              <div className="rounded-xl border px-4 py-4" style={{ borderColor: 'rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.02)' }}>
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-white"><ShieldCheck size={16} className="text-[#7FA1FF]" /> Core services</div>
                <div className="flex flex-wrap gap-2">
                  <HealthPill label="MongoDB" ok={Boolean(health?.mongo)} />
                  <HealthPill label="Ollama" ok={Boolean(health?.ollama)} />
                  <HealthPill label="Langfuse" ok={Boolean(stats?.langfuse_configured)} />
                  <HealthPill label="Scheduler" ok={Boolean(health?.scheduler)} />
                </div>
              </div>

              <div className="rounded-xl border px-4 py-4" style={{ borderColor: 'rgba(255,255,255,0.08)', background: 'rgba(255,255,255,0.02)' }}>
                <div className="mb-3 flex items-center gap-2 text-sm font-medium text-white"><TrendingUp size={16} className="text-[#7FA1FF]" /> Priority signals</div>
                <div className="space-y-3 text-sm">
                  <div className="flex items-center justify-between gap-3">
                    <span style={{ color: C.tertiary }}>Default provider</span>
                    <span className="text-right font-medium text-white">{activeProvider?.name || stats?.llm_provider || 'None'}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span style={{ color: C.tertiary }}>Running runtimes</span>
                    <span className="font-medium text-white">{formatCount(runningRuntimes)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span style={{ color: C.tertiary }}>Queued automations</span>
                    <span className="font-medium text-white">{formatCount(schedules.length)}</span>
                  </div>
                  <div className="flex items-center justify-between gap-3">
                    <span style={{ color: C.tertiary }}>Decision feed entries</span>
                    <span className="font-medium text-white">{formatCount(decisions.length)}</span>
                  </div>
                </div>
              </div>
            </div>
          </PageCard>
        </div>

        <div className="grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
          <QuickAction icon={Bot} label="Agents" description="Edit agent profiles, runtime preferences, and approval rules." onClick={() => navigate('/agents')} />
          <QuickAction icon={Layers} label="Providers" description="Manage NVIDIA, Ollama, and commercial failover providers." onClick={() => navigate('/providers')} />
          <QuickAction icon={Activity} label="Logs" description="Inspect activity, routing decisions, and usage metrics in one place." onClick={() => navigate('/logs')} />
          <QuickAction icon={Database} label="Setup" description="Return to the guided setup flow and keep hosted defaults in sync." onClick={() => navigate('/setup')} />
        </div>
      </div>
    </div>
  );
}
