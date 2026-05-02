import React, { useState, useEffect, useCallback } from 'react';
import { RefreshCw, AlertTriangle, Zap } from 'lucide-react';
import { getActivity, getStats, getDecisionLog, getSavings, getUsage, fmtErr } from '../api';

const C = {
  bg: '#0F0F13', surface: '#141418', border: 'rgba(255,255,255,0.06)',
  primary: '#F2F2F6', secondary: '#B2B2C4', tertiary: '#808094', muted: '#565666',
  accent: '#002FA7',
};

function relTime(ts) {
  if (!ts) return '—';
  const diff = (Date.now() / 1000) - (typeof ts === 'string' ? new Date(ts).getTime() / 1000 : ts);
  if (diff < 60)    return `${Math.round(diff)}s ago`;
  if (diff < 3600)  return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return `${Math.round(diff / 86400)}d ago`;
}

function StatusDot({ status }) {
  const COLOR = {
    completed: '#10B981', done: '#10B981', success: '#10B981',
    failed: '#EF4444', error: '#EF4444',
    running: '#F59E0B', in_progress: '#F59E0B',
    escalated: '#F59E0B',
    pending: '#6E6E80', todo: '#6E6E80',
  };
  return <span className="w-2 h-2 rounded-full shrink-0" style={{ background: COLOR[status] || C.muted }} />;
}

function TabBar({ tabs, active, onChange }) {
  return (
    <div className="flex border rounded-lg overflow-hidden" style={{ borderColor: 'rgba(255,255,255,0.10)' }}>
      {tabs.map(([id, label]) => (
        <button key={id} onClick={() => onChange(id)}
          className="px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider transition-colors"
          style={active === id ? { background: C.accent, color: C.primary } : { color: C.tertiary }}
          onMouseEnter={e => { if (active !== id) e.currentTarget.style.color = C.secondary; }}
          onMouseLeave={e => { if (active !== id) e.currentTarget.style.color = C.tertiary; }}>
          {label}
        </button>
      ))}
    </div>
  );
}

function ExecutionsTab() {
  const [decisions, setDecisions] = useState([]);
  const [loading, setLoading]     = useState(true);
  const [error, setError]         = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await getDecisionLog(50);
      setDecisions(r.data?.decisions || r.data || []);
    } catch (e) {
      setError(fmtErr(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  if (loading) return <div className="py-12 text-center text-[11px] font-mono" style={{ color: C.muted }}>Loading…</div>;
  if (error)   return <div className="text-[10px] text-amber-400 font-mono flex items-center gap-2 py-4"><AlertTriangle size={11} /> {error}</div>;
  if (!decisions.length) return <div className="py-12 text-center text-[11px] font-mono" style={{ color: C.muted }}>No executions yet — submit a task to see activity</div>;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between mb-2">
        <span className="text-[9px] font-mono uppercase tracking-wider" style={{ color: C.muted }}>{decisions.length} entries</span>
        <button onClick={load} className="text-[9px] font-mono flex items-center gap-1 transition-colors" style={{ color: C.muted }}
          onMouseEnter={e => e.currentTarget.style.color = C.secondary}
          onMouseLeave={e => e.currentTarget.style.color = C.muted}>
          <RefreshCw size={9} /> Refresh
        </button>
      </div>
      {decisions.map((d, i) => (
        <div key={d.id || i} className="rounded-xl px-4 py-3 border transition-all"
          style={{ background: C.surface, borderColor: C.border }}
          onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'}
          onMouseLeave={e => e.currentTarget.style.borderColor = C.border}>
          <div className="flex items-center gap-3 mb-1.5">
            <StatusDot status={d.escalated ? 'escalated' : 'completed'} />
            <span className="text-[12px] font-medium flex-1 truncate" style={{ color: '#D8D8E8' }}>
              {d.task_id || d.id}
            </span>
            {d.escalated && (
              <span className="px-1.5 py-px text-[8px] font-mono border rounded"
                style={{ borderColor: 'rgba(245,158,11,0.25)', background: 'rgba(245,158,11,0.08)', color: '#F59E0B' }}>
                ↑ escalated
              </span>
            )}
            <span className="text-[9px] font-mono shrink-0" style={{ color: C.muted }}>{relTime(d.timestamp)}</span>
          </div>
          <div className="flex items-center gap-4 text-[9px] font-mono" style={{ color: C.tertiary }}>
            {d.selected_runtime_id && <span>{d.selected_runtime_id}</span>}
            {d.agent_id && <span>@{d.agent_id}</span>}
            <span style={{ color: d.provider_used === 'ollama' ? '#10B981' : C.secondary }}>
              {d.model_used || d.task_type || '—'}
            </span>
            {d.tokens_used && <span>{d.tokens_used.toLocaleString()} tokens</span>}
            {d.latency_ms && <span>{Math.round(d.latency_ms)}ms</span>}
            {d.escalation_reason && (
              <span className="truncate max-w-[180px]" style={{ color: 'rgba(245,158,11,0.8)' }}>{d.escalation_reason}</span>
            )}
          </div>
        </div>
      ))}
    </div>
  );
}

function ActivityTab() {
  const [events, setEvents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]    = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await getActivity(100);
      setEvents(Array.isArray(r.data) ? r.data : r.data?.events || r.data?.activity || []);
    } catch (e) {
      setError(fmtErr(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const catColor = (cat) => ({
    chat:     '#A78BFA',
    ingest:   '#10B981',
    provider: '#F59E0B',
    wiki:     C.accent,
    keys:     '#EC4899',
    auth:     '#3B82F6',
    task:     '#06B6D4',
    agent:    '#8B5CF6',
  })[cat] || C.muted;

  if (loading) return <div className="py-12 text-center text-[11px] font-mono" style={{ color: C.muted }}>Loading…</div>;
  if (error)   return <div className="text-[10px] text-amber-400 font-mono flex items-center gap-2 py-4"><AlertTriangle size={11} /> {error}</div>;
  if (!events.length) return <div className="py-12 text-center text-[11px] font-mono" style={{ color: C.muted }}>No activity recorded yet</div>;

  return (
    <div>
      <div className="flex justify-end mb-2">
        <button onClick={load} className="text-[9px] font-mono flex items-center gap-1 transition-colors" style={{ color: C.muted }}
          onMouseEnter={e => e.currentTarget.style.color = C.secondary}
          onMouseLeave={e => e.currentTarget.style.color = C.muted}>
          <RefreshCw size={9} /> Refresh
        </button>
      </div>
      <div className="rounded-xl overflow-hidden" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
        <div className="divide-y" style={{ '--tw-divide-color': 'rgba(255,255,255,0.05)' }}>
          {events.map((a, i) => {
            const cat = a.category || a.type || 'other';
            const msg = a.message || a.description || a.action || JSON.stringify(a);
            const time = a.timestamp ? relTime(a.timestamp) : a.time || '—';
            return (
              <div key={a.id || i} className="flex items-center gap-3 px-5 py-3 transition-colors"
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.015)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                <div className="w-2 h-2 rounded-full shrink-0" style={{ background: catColor(cat) }} />
                <span className="flex-1 text-[11px] truncate" style={{ color: C.secondary }}>{msg}</span>
                <span className="text-[9px] font-mono shrink-0" style={{ color: C.muted }}>{time}</span>
                <span className="text-[8px] font-mono uppercase shrink-0 w-16 text-right" style={{ color: C.muted }}>{cat}</span>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}

function MetricsTab() {
  const [stats, setStats]     = useState(null);
  const [savings, setSavings] = useState(null);
  const [usage, setUsage]     = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      getStats().then(r => setStats(r.data)),
      getSavings('month', 'day').then(r => setSavings(r.data)),
      getUsage('month').then(r => setUsage(r.data)),
    ])
      .catch(e => setError(fmtErr(e)))
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="py-12 text-center text-[11px] font-mono" style={{ color: C.muted }}>Loading metrics…</div>;

  const totalSaved   = savings?.total_saved_usd ?? stats?.cost_saved_usd ?? 0;
  const monthlySaved = savings?.period_saved_usd ?? 0;
  const todaySaved   = savings?.today_saved_usd ?? 0;
  const dailyBuckets = savings?.buckets || [];
  const maxSaving    = dailyBuckets.length ? Math.max(...dailyBuckets.map(d => d.saved_usd || 0), 1) : 1;

  const totalTokens  = usage?.total_tokens ?? stats?.total_tokens ?? 0;
  const localRatio   = usage?.local_ratio ?? stats?.local_ratio ?? null;
  const requests24h  = usage?.requests_24h ?? stats?.requests_24h ?? 0;
  const escalations  = usage?.escalations ?? stats?.escalations ?? 0;
  const escalPct     = requests24h > 0 ? ((escalations / requests24h) * 100).toFixed(1) : '—';

  const userBreakdown = savings?.by_user || stats?.user_savings || [];
  const providerHealth = stats?.providers || [];

  return (
    <div className="space-y-5">
      {error && <div className="text-[10px] text-amber-400 font-mono flex items-center gap-2"><AlertTriangle size={11} /> {error}</div>}

      {/* Cost savings hero */}
      <div className="rounded-xl p-5" style={{ background: 'rgba(16,185,129,0.05)', border: '1px solid rgba(16,185,129,0.20)' }}>
        <div className="flex items-center gap-2 mb-4">
          <Zap size={14} style={{ color: '#10B981' }} />
          <span className="text-[11px] font-mono font-bold uppercase tracking-wider" style={{ color: '#10B981' }}>
            Cost Saved by Using Open Source LLMs
          </span>
        </div>
        <div className="grid grid-cols-3 gap-4 mb-4">
          {[
            { label: 'All time',   value: `$${totalSaved.toFixed(2)}`,   sub: 'vs commercial equivalents' },
            { label: 'This month', value: `$${monthlySaved.toFixed(2)}`, sub: new Date().toLocaleString('default', { month: 'long', year: 'numeric' }) },
            { label: 'Today',      value: `$${todaySaved.toFixed(2)}`,   sub: new Date().toLocaleDateString() },
          ].map(s => (
            <div key={s.label} className="text-center">
              <div className="text-[26px] font-bold leading-none mb-0.5" style={{ color: '#10B981', fontFamily: 'var(--font-main)' }}>{s.value}</div>
              <div className="text-[10px] font-medium" style={{ color: '#CACADA' }}>{s.label}</div>
              <div className="text-[8px] font-mono mt-0.5" style={{ color: C.muted }}>{s.sub}</div>
            </div>
          ))}
        </div>

        {dailyBuckets.length > 0 && (
          <div>
            <div className="text-[8px] font-mono uppercase tracking-wider mb-2" style={{ color: C.muted }}>
              Daily savings — last {dailyBuckets.length} days
            </div>
            <div className="flex items-end gap-1 h-12">
              {dailyBuckets.map((d, i) => (
                <div key={i} className="flex-1 flex flex-col items-center gap-1">
                  <div className="w-full rounded-sm transition-colors"
                    style={{ height: `${Math.max(2, Math.round(((d.saved_usd || 0) / maxSaving) * 40))}px`, background: 'rgba(16,185,129,0.4)' }}
                    title={`$${(d.saved_usd || 0).toFixed(2)}`}
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(16,185,129,0.7)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'rgba(16,185,129,0.4)'} />
                  <span className="text-[7px] font-mono" style={{ color: C.muted }}>{(d.date || '').slice(-4) || d.label || ''}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Usage stats */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
        {[
          { label: 'Requests (24h)', value: requests24h.toLocaleString(), sub: 'total calls' },
          { label: 'Total tokens',   value: totalTokens > 0 ? `${(totalTokens / 1000).toFixed(1)}k` : '—', sub: '~$0 local cost' },
          { label: 'Escalations',    value: escalations.toLocaleString(), sub: `${escalPct}% rate`, accent: '#F59E0B' },
          { label: 'Local ratio',    value: localRatio != null ? `${Math.round(localRatio * 100)}%` : '—', sub: 'on-device', accent: '#10B981' },
        ].map(s => (
          <div key={s.label} className="rounded-xl p-4" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
            <div className="text-[22px] font-bold leading-none mb-1 tracking-tight"
              style={{ color: s.accent || C.primary, fontFamily: 'var(--font-main)' }}>{s.value}</div>
            <div className="text-[10px] font-medium" style={{ color: C.tertiary }}>{s.label}</div>
            <div className="text-[9px] font-mono mt-0.5" style={{ color: C.muted }}>{s.sub}</div>
          </div>
        ))}
      </div>

      {/* User breakdown */}
      {userBreakdown.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          <div className="px-4 py-3 border-b flex items-center gap-2" style={{ borderColor: C.border }}>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider" style={{ color: '#9A9AAE' }}>Savings by User</span>
            <span className="text-[8px] font-mono ml-auto" style={{ color: C.muted }}>open source vs GPT-4o equivalent</span>
          </div>
          <div className="divide-y" style={{ '--tw-divide-color': 'rgba(255,255,255,0.05)' }}>
            {userBreakdown.map(u => (
              <div key={u.user || u.user_id} className="flex items-center gap-4 px-4 py-3">
                <div className="w-6 h-6 rounded-full flex items-center justify-center text-[9px] font-bold text-white shrink-0"
                  style={{ background: C.accent }}>
                  {(u.user || u.name || '?')[0].toUpperCase()}
                </div>
                <span className="flex-1 text-[11px] font-medium" style={{ color: '#CACADA' }}>{u.user || u.name || u.user_id}</span>
                <div className="flex items-center gap-3 text-[9px] font-mono" style={{ color: C.tertiary }}>
                  {u.local_requests != null && <span>{u.local_requests} local · {u.cloud_requests || 0} cloud</span>}
                  <span style={{ color: '#10B981', fontWeight: '700' }}>${(u.saved_usd || u.saved || 0).toFixed(2)} saved</span>
                  {u.local_pct != null && <span style={{ color: C.muted }}>{u.local_pct}%</span>}
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Provider table */}
      {providerHealth.length > 0 && (
        <div className="rounded-xl overflow-hidden" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          <div className="px-4 py-3 border-b" style={{ borderColor: C.border }}>
            <span className="text-[10px] font-mono uppercase tracking-wider" style={{ color: '#9A9AAE' }}>Provider Performance</span>
          </div>
          <table className="w-full text-[10px] font-mono">
            <thead>
              <tr className="border-b" style={{ borderColor: 'rgba(255,255,255,0.05)', color: C.tertiary }}>
                {['Provider','Latency','Success %','Rate Limit','Cost (24h)'].map(h => (
                  <th key={h} className="px-4 py-2 text-left font-medium uppercase text-[8px] tracking-wider">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y" style={{ '--tw-divide-color': 'rgba(255,255,255,0.05)' }}>
              {providerHealth.map(p => (
                <tr key={p.name || p.id}
                  onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.015)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <td className="px-4 py-2.5">
                    <div className="flex items-center gap-2">
                      <StatusDot status={p.status || (p.available ? 'completed' : 'failed')} />
                      {p.name || p.id}
                    </div>
                  </td>
                  <td className="px-4 py-2.5" style={{ color: '#9A9AAE' }}>{p.latency_ms ? `${Math.round(p.latency_ms)}ms` : p.latency || '—'}</td>
                  <td className="px-4 py-2.5" style={{ color: '#9A9AAE' }}>{p.success_rate != null ? `${p.success_rate}%` : '—'}</td>
                  <td className="px-4 py-2.5" style={{ color: '#9A9AAE' }}>{p.rate_limit || '—'}</td>
                  <td className="px-4 py-2.5" style={{ color: '#9A9AAE' }}>{p.cost_24h || p.cost || '—'}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}

export default function LogsPage() {
  const [tab, setTab] = useState('executions');

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-4 px-5 py-3.5 border-b shrink-0" style={{ borderColor: C.border }}>
        <h1 className="text-[15px] font-bold tracking-tight flex-1"
          style={{ color: C.primary, fontFamily: 'var(--font-main)' }}>Logs</h1>
        <TabBar
          tabs={[['executions','Executions'],['activity','Activity'],['metrics','Metrics & Savings']]}
          active={tab}
          onChange={setTab}
        />
      </div>

      <div className="flex-1 overflow-y-auto p-5">
        {tab === 'executions' && <ExecutionsTab />}
        {tab === 'activity'   && <ActivityTab />}
        {tab === 'metrics'    && <MetricsTab />}
      </div>
    </div>
  );
}
