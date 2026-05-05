import React, { useState, useEffect, useCallback } from 'react';
import { Calendar, Play, Pause, Plus, CheckCircle, XCircle, Clock, AlertTriangle } from 'lucide-react';
import { listSchedules, createSchedule, triggerSchedule, pauseSchedule, resumeSchedule, fmtErr } from '../api';

const C = {
  bg: '#0F0F13', surface: '#141418', border: 'rgba(255,255,255,0.06)',
  primary: '#F2F2F6', secondary: '#B2B2C4', tertiary: '#808094', muted: '#565666',
  accent: '#002FA7',
};

const FREQ_OPTS = {
  daily:   'Daily 08:00',
  weekly:  'Weekly Mon 02:00',
  hourly:  'Every hour',
  monthly: 'Monthly 1st 09:00',
};

const FREQ_TO_CRON = {
  daily:   '0 8 * * *',
  weekly:  '0 2 * * 1',
  hourly:  '0 * * * *',
  monthly: '0 9 1 * *',
};

function Toggle({ active, onClick }) {
  return (
    <button onClick={onClick}
      className="w-9 h-5 rounded-full border shrink-0 relative transition-all"
      style={{ background: active ? C.accent : '#1E1E26', borderColor: active ? 'rgba(0,47,167,0.4)' : 'rgba(255,255,255,0.1)' }}>
      <span className={`absolute top-0.5 w-3.5 h-3.5 rounded-full bg-white transition-all ${active ? 'left-[18px]' : 'left-0.5'}`} />
    </button>
  );
}

function StatusBadge({ status }) {
  const map = {
    active:    { color: '#10B981', label: 'active' },
    paused:    { color: '#6E6E80', label: 'paused' },
    running:   { color: '#F59E0B', label: 'running' },
    failed:    { color: '#EF4444', label: 'failed' },
    completed: { color: '#3B82F6', label: 'done' },
  };
  const { color, label } = map[status] || { color: C.muted, label: status };
  return (
    <span className="flex items-center gap-1 text-[9px] font-mono uppercase tracking-wider px-2 py-1 rounded-md border"
      style={{ color, borderColor: color + '30', background: color + '10' }}>
      <span className="w-1.5 h-1.5 rounded-full" style={{ background: color }} />
      {label}
    </span>
  );
}

function NewScheduleForm({ agents, onCancel, onCreate }) {
  const [name, setName] = useState('');
  const [agentId, setAgentId] = useState(agents[0]?.id || agents[0]?.agent_id || '');
  const [freq, setFreq] = useState('daily');
  const [approval, setApproval] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState('');

  async function submit() {
    if (!name.trim()) { setError('Name is required'); return; }
    setSubmitting(true);
    setError('');
    try {
      const payload = {
        name: name.trim(),
        cron: FREQ_TO_CRON[freq] || freq,
        instruction: name.trim(),
        agent_id: agentId || undefined,
        requires_approval: approval,
        task_type: 'scheduled',
      };
      const r = await createSchedule(payload);
      onCreate(r.data);
    } catch (e) {
      setError(fmtErr(e));
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div className="rounded-xl p-4 mb-5 space-y-3"
      style={{ background: 'rgba(0,47,167,0.05)', border: '1px solid rgba(0,47,167,0.25)' }}>
      <div className="text-[10px] font-mono uppercase tracking-wider" style={{ color: C.tertiary }}>New Schedule</div>
      {error && (
        <div className="text-[10px] text-red-400 font-mono">{error}</div>
      )}
      <input value={name} onChange={e => setName(e.target.value)} placeholder="Schedule name"
        className="w-full px-3 py-2 text-[12px] font-mono rounded-lg outline-none transition-colors placeholder:text-[#565666]"
        style={{ background: '#18181D', border: '1px solid rgba(255,255,255,0.1)', color: C.primary }}
        onFocus={e => e.target.style.borderColor = C.accent}
        onBlur={e => e.target.style.borderColor = 'rgba(255,255,255,0.1)'} />
      <div className="flex gap-2">
        <select value={agentId} onChange={e => setAgentId(e.target.value)}
          className="flex-1 px-3 py-2 text-[11px] font-mono rounded-lg outline-none"
          style={{ background: '#18181D', border: '1px solid rgba(255,255,255,0.1)', color: C.primary }}>
          {agents.length === 0
            ? <option value="">No agents configured</option>
            : agents.map(a => <option key={a.id || a.agent_id} value={a.id || a.agent_id}>{a.name}</option>)
          }
        </select>
        <select value={freq} onChange={e => setFreq(e.target.value)}
          className="flex-1 px-3 py-2 text-[11px] font-mono rounded-lg outline-none"
          style={{ background: '#18181D', border: '1px solid rgba(255,255,255,0.1)', color: C.primary }}>
          {Object.entries(FREQ_OPTS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
      </div>
      <label className="flex items-center gap-2 text-[11px] font-mono cursor-pointer" style={{ color: '#8E8EA2' }}>
        <input type="checkbox" checked={approval} onChange={e => setApproval(e.target.checked)}
          style={{ accentColor: C.accent }} />
        Require approval before execution
      </label>
      <div className="flex gap-2">
        <button onClick={submit} disabled={submitting}
          className="flex-1 py-2 text-[10px] font-mono uppercase tracking-wider text-white rounded-lg disabled:opacity-50"
          style={{ background: C.accent }}>
          {submitting ? 'Creating…' : 'Create'}
        </button>
        <button onClick={onCancel}
          className="flex-1 py-2 text-[10px] font-mono uppercase tracking-wider rounded-lg border transition-colors"
          style={{ color: C.tertiary, borderColor: 'rgba(255,255,255,0.1)' }}
          onMouseEnter={e => e.currentTarget.style.color = C.primary}
          onMouseLeave={e => e.currentTarget.style.color = C.tertiary}>
          Cancel
        </button>
      </div>
    </div>
  );
}

export default function SchedulesPage() {
  const [schedules, setSchedules] = useState([]);
  const [agents, setAgents]       = useState([]);
  const [loading, setLoading]     = useState(true);
  const [creating, setCreating]   = useState(false);
  const [running, setRunning]     = useState(null);
  const [error, setError]         = useState('');

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const r = await listSchedules();
      setSchedules(Array.isArray(r.data) ? r.data : r.data?.schedules || r.data?.jobs || []);
    } catch (e) {
      if (e?.response?.status !== 404) setError(fmtErr(e));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  // Load agents for the "assign" dropdown
  useEffect(() => {
    import('../api').then(({ listAgents }) => {
      listAgents().then(r => setAgents(r.data?.agents || r.data || [])).catch(() => {});
    });
  }, []);

  async function toggle(schedule) {
    const isPaused = schedule.status === 'paused';
    try {
      if (isPaused) await resumeSchedule(schedule.id || schedule.job_id);
      else          await pauseSchedule(schedule.id || schedule.job_id);
      setSchedules(prev => prev.map(s =>
        (s.id || s.job_id) === (schedule.id || schedule.job_id)
          ? { ...s, status: isPaused ? 'active' : 'paused' }
          : s
      ));
    } catch (e) {
      setError(fmtErr(e));
    }
  }

  async function runNow(schedule) {
    const id = schedule.id || schedule.job_id;
    setRunning(id);
    try {
      await triggerSchedule(id);
    } catch (e) {
      setError(fmtErr(e));
    } finally {
      setTimeout(() => setRunning(r => r === id ? null : r), 2000);
    }
  }

  const active = schedules.filter(s => s.status === 'active').length;
  const failures = schedules.reduce((n, s) => n + (s.failures || s.fail_count || 0), 0);
  const withGate = schedules.filter(s => s.approval_gate).length;
  const recentRuns = schedules
    .filter(s => s.last_run)
    .slice()
    .sort((a, b) => new Date(b.last_run).getTime() - new Date(a.last_run).getTime())
    .slice(0, 10);

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-5 max-w-5xl">

        {/* Header */}
        <div className="flex items-center justify-between mb-5">
          <div>
            <h1 className="text-[15px] font-bold tracking-tight" style={{ color: C.primary, fontFamily: 'var(--font-main)' }}>Schedules</h1>
            <p className="text-[10px] font-mono mt-0.5" style={{ color: C.muted }}>{active} active autopilot jobs</p>
          </div>
          <button onClick={() => setCreating(c => !c)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-white rounded-lg"
            style={{ background: C.accent }}>
            <Plus size={11} /> New Schedule
          </button>
        </div>

        {error && (
          <div className="mb-4 flex items-center gap-2 px-4 py-3 rounded-lg border text-amber-400 text-[11px] font-mono"
            style={{ background: 'rgba(245,158,11,0.06)', borderColor: 'rgba(245,158,11,0.15)' }}>
            <AlertTriangle size={12} /> {error}
          </div>
        )}

        {creating && (
          <NewScheduleForm
            agents={agents}
            onCancel={() => setCreating(false)}
            onCreate={s => { setSchedules(prev => [s, ...prev]); setCreating(false); }}
          />
        )}

        {/* Stats row */}
        <div className="grid grid-cols-3 gap-3 mb-5">
          {[
            { label: 'Total runs',     value: schedules.reduce((n, s) => n + (s.runs || s.run_count || 0), 0).toLocaleString() },
            { label: 'Failures',       value: failures,  accent: failures > 0 ? '#EF4444' : undefined },
            { label: 'Approval gates', value: withGate },
          ].map(s => (
            <div key={s.label} className="rounded-xl px-4 py-3"
              style={{ background: C.surface, border: `1px solid ${C.border}` }}>
              <div className="text-[20px] font-bold leading-none mb-0.5 tracking-tight"
                style={{ color: s.accent || C.primary, fontFamily: 'var(--font-main)' }}>{s.value}</div>
              <div className="text-[10px] font-mono" style={{ color: C.tertiary }}>{s.label}</div>
            </div>
          ))}
        </div>

        {/* Schedule table */}
        <div className="rounded-xl overflow-hidden mb-4" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          <div className="px-4 py-3 border-b" style={{ borderColor: C.border }}>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider" style={{ color: C.tertiary }}>Autopilot Jobs</span>
          </div>

          {loading ? (
            <div className="py-12 text-center text-[11px] font-mono" style={{ color: C.muted }}>Loading schedules…</div>
          ) : schedules.length === 0 ? (
            <div className="py-12 text-center">
              <Calendar size={24} className="mx-auto mb-3" style={{ color: C.muted }} />
              <div className="text-[12px] font-medium mb-1" style={{ color: C.secondary }}>No schedules yet</div>
              <div className="text-[10px] font-mono" style={{ color: C.muted }}>Create one to automate agent runs</div>
            </div>
          ) : (
            <div className="divide-y" style={{ '--tw-divide-color': 'rgba(255,255,255,0.05)' }}>
              {schedules.map(s => {
                const id = s.id || s.job_id;
                const isActive = s.status === 'active';
                const isRunningNow = running === id;
                const agentName = s.agent_name || s.agent_id || '—';
                const freqLabel = FREQ_OPTS[s.schedule] || s.schedule || s.cron || '—';
                return (
                  <div key={id} className="flex items-center gap-4 px-4 py-3.5 transition-colors"
                    onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.015)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                    <Toggle active={isActive} onClick={() => toggle(s)} />
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-[12.5px] font-medium" style={{ color: '#D8D8E8' }}>{s.name}</span>
                        {s.approval_gate && (
                          <span className="px-1.5 py-px text-[8px] font-mono rounded border"
                            style={{ borderColor: 'rgba(245,158,11,0.25)', background: 'rgba(245,158,11,0.08)', color: '#F59E0B' }}>
                            approval gate
                          </span>
                        )}
                      </div>
                      <div className="flex items-center gap-2 text-[9px] font-mono" style={{ color: C.muted }}>
                        <span style={{ color: C.tertiary }}>{agentName}</span>
                        <span style={{ color: C.muted }}>·</span>
                        <span>{freqLabel}</span>
                        {s.next_run && <><span style={{ color: C.muted }}>· next</span> <span>{s.next_run}</span></>}
                      </div>
                    </div>
                    <div className="hidden sm:flex flex-col items-end text-[9px] font-mono shrink-0" style={{ color: C.muted }}>
                      <span>{(s.run_count || s.runs || 0)} runs · {(s.fail_count || s.failures || 0)} fail{(s.fail_count || s.failures || 0) !== 1 ? 's' : ''}</span>
                    </div>
                    <StatusBadge status={s.status} />
                    <button onClick={() => runNow(s)} disabled={isRunningNow}
                      className="flex items-center gap-1 px-2.5 py-1.5 text-[9px] font-mono rounded-lg border transition-colors disabled:opacity-50 shrink-0"
                      style={{ borderColor: 'rgba(255,255,255,0.08)', color: C.tertiary }}
                      onMouseEnter={e => { e.currentTarget.style.color = C.primary; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.2)'; }}
                      onMouseLeave={e => { e.currentTarget.style.color = C.tertiary; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; }}>
                      {isRunningNow
                        ? <span style={{ color: '#10B981' }} className="animate-pulse">running…</span>
                        : <><Play size={9} /> Run</>
                      }
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Recent runs */}
        <div className="rounded-xl overflow-hidden" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          <div className="px-4 py-3 border-b" style={{ borderColor: C.border }}>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider" style={{ color: C.tertiary }}>Recent Runs</span>
          </div>
          {recentRuns.length === 0 ? (
            <div className="px-4 py-10 text-center text-[11px] font-mono" style={{ color: C.muted }}>
              No recent runs yet.
            </div>
          ) : (
            <div className="divide-y" style={{ '--tw-divide-color': 'rgba(255,255,255,0.05)' }}>
              {recentRuns.map((r) => {
                const dotColor = (r.fail_count || r.failures || 0) > 0 ? '#EF4444' : '#10B981';
                return (
                  <div key={r.id || r.job_id} className="flex items-center gap-3 px-4 py-2.5">
                    <div className="w-2 h-2 rounded-full shrink-0" style={{ background: dotColor }} />
                    <span className="flex-1 text-[11px] truncate" style={{ color: C.secondary }}>{r.name}</span>
                    <span className="text-[9px] font-mono shrink-0" style={{ color: C.muted }}>{r.model || '—'}</span>
                    <span className="text-[9px] font-mono shrink-0" style={{ color: '#565666' }}>{r.last_run}</span>
                  </div>
                );
              })}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
