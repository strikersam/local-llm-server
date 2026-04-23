/**
 * TasksPage — Task / Issue management.
 *
 * Shows tasks with status (todo / in_progress / in_review / blocked / done),
 * priority, agent assignment, and runtime info.  Supports create/update/retry/escalate.
 */
import React, { useState, useEffect, useCallback } from 'react';
import {
  CheckCircle2, AlertTriangle, Clock, PlayCircle, Pause,
  Plus, Filter, RefreshCw, ChevronDown, RotateCcw, ArrowUpCircle,
  Loader2, X, Save, Calendar, Tag, Bot, Cpu, AlertCircle,
} from 'lucide-react';
import { listTasks, createTask, updateTask, retryTask, escalateTask, fmtErr } from '../api';

function cls(...p) { return p.filter(Boolean).join(' '); }

const STATUS_META = {
  todo:        { label: 'To Do',      dot: 'bg-gray-500',              badge: 'border-white/10 bg-white/4 text-[#888]' },
  in_progress: { label: 'Running',    dot: 'bg-emerald-400 animate-pulse', badge: 'border-emerald-500/25 bg-emerald-500/10 text-emerald-400' },
  in_review:   { label: 'In Review',  dot: 'bg-amber-400',             badge: 'border-amber-500/25 bg-amber-500/10 text-amber-400' },
  blocked:     { label: 'Blocked',    dot: 'bg-red-500',               badge: 'border-red-500/25 bg-red-500/10 text-red-400' },
  done:        { label: 'Done',       dot: 'bg-blue-400',              badge: 'border-blue-500/25 bg-blue-500/10 text-blue-400' },
};

const PRIORITY_META = {
  urgent: { label: 'Urgent', color: 'text-red-400', dot: 'bg-red-500' },
  high:   { label: 'High',   color: 'text-amber-400', dot: 'bg-amber-500' },
  medium: { label: 'Medium', color: 'text-blue-400', dot: 'bg-blue-400' },
  low:    { label: 'Low',    color: 'text-gray-500', dot: 'bg-gray-600' },
};

function relTime(ts) {
  if (!ts) return '—';
  const diff = (Date.now() / 1000) - ts;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return new Date(ts * 1000).toLocaleDateString();
}

// ── Task card ─────────────────────────────────────────────────────────────────

function TaskCard({ task, onStatusChange, onRetry, onEscalate }) {
  const sm = STATUS_META[task.status] || STATUS_META.todo;
  const pm = PRIORITY_META[task.priority] || PRIORITY_META.medium;
  const [expanded, setExpanded] = useState(false);

  return (
    <div className={cls(
      'bg-[#111] border rounded-xl transition-all',
      task.status === 'blocked' ? 'border-red-500/20' : 'border-white/8 hover:border-white/14',
    )}>
      <button className="w-full p-4 text-left" onClick={() => setExpanded(e => !e)}>
        <div className="flex items-start gap-3">
          <div className={cls('w-2 h-2 rounded-full mt-1.5 flex-shrink-0', sm.dot)} />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="text-[13px] font-medium text-white">{task.title}</span>
              <span className={cls('text-[9px] px-1.5 py-0.5 rounded border font-mono', sm.badge)}>
                {sm.label}
              </span>
              <span className={cls('text-[9px] font-mono', pm.color)}>{pm.label}</span>
            </div>
            {task.description && !expanded && (
              <p className="text-[11px] text-[#555] mt-0.5 line-clamp-1">{task.description}</p>
            )}
            <div className="flex items-center gap-3 mt-1.5 flex-wrap">
              {task.agent_id && (
                <span className="flex items-center gap-1 text-[10px] text-[#555]">
                  <Bot size={9} /> {task.agent_id}
                </span>
              )}
              {task.runtime_id && (
                <span className="flex items-center gap-1 text-[10px] text-[#444]">
                  <Cpu size={9} /> {task.runtime_id}
                </span>
              )}
              <span className="text-[10px] text-[#444]">{relTime(task.updated_at)}</span>
            </div>
          </div>
          <ChevronDown size={13} className={cls('text-[#444] flex-shrink-0 transition-transform', expanded ? 'rotate-180' : '')} />
        </div>
      </button>

      {expanded && (
        <div className="px-4 pb-4 border-t border-white/5 pt-3 space-y-3">
          {task.description && (
            <p className="text-[12px] text-[#888]">{task.description}</p>
          )}
          {task.prompt && (
            <div>
              <div className="text-[9px] uppercase tracking-widest text-[#444] mb-1">Prompt</div>
              <pre className="text-[10px] font-mono text-[#777] bg-black/30 rounded-md px-3 py-2 whitespace-pre-wrap line-clamp-5">
                {task.prompt}
              </pre>
            </div>
          )}

          {/* Tags */}
          {task.tags?.length > 0 && (
            <div className="flex flex-wrap gap-1.5">
              {task.tags.map(t => (
                <span key={t} className="text-[9px] font-mono px-2 py-0.5 rounded border border-white/8 bg-white/4 text-[#555]">
                  {t}
                </span>
              ))}
            </div>
          )}

          {/* Execution log (last 3 entries) */}
          {task.execution_log?.length > 0 && (
            <div>
              <div className="text-[9px] uppercase tracking-widest text-[#444] mb-1">Recent Log</div>
              <div className="space-y-1">
                {task.execution_log.slice(-3).map((e, i) => (
                  <div key={i} className="flex items-start gap-2 text-[10px] font-mono">
                    <span className={cls('mt-0.5', e.level === 'error' ? 'text-red-400' : e.level === 'warning' ? 'text-amber-400' : 'text-[#555]')}>
                      {e.level === 'error' ? '✗' : e.level === 'warning' ? '!' : '·'}
                    </span>
                    <span className="text-[#666] flex-1">{e.message}</span>
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Actions */}
          <div className="flex flex-wrap gap-2 pt-1">
            {['todo', 'in_progress', 'in_review', 'done'].map(s => (
              s !== task.status && (
                <button key={s} onClick={() => onStatusChange(task.task_id, s)}
                  className="text-[10px] px-3 py-1.5 border border-white/8 text-[#666] rounded-md hover:text-white hover:border-white/20 transition-colors">
                  → {STATUS_META[s]?.label || s}
                </button>
              )
            ))}
            {task.status !== 'todo' && (
              <button onClick={() => onRetry(task.task_id)}
                className="flex items-center gap-1 text-[10px] px-3 py-1.5 border border-amber-500/20 text-amber-400 rounded-md hover:bg-amber-500/8 transition-colors">
                <RotateCcw size={10} /> Retry
              </button>
            )}
            {task.status !== 'blocked' && (
              <button onClick={() => onEscalate(task.task_id)}
                className="flex items-center gap-1 text-[10px] px-3 py-1.5 border border-red-500/20 text-red-400 rounded-md hover:bg-red-500/8 transition-colors">
                <ArrowUpCircle size={10} /> Escalate
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

// ── Create form ───────────────────────────────────────────────────────────────

function CreateTaskForm({ onSave, onCancel }) {
  const [form, setForm] = useState({
    title: '', description: '', prompt: '',
    agent_id: '', runtime_id: '', priority: 'medium',
    task_type: 'general', tags: '',
    requires_approval: false,
  });
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSave = async () => {
    if (!form.title.trim()) { setErr('Title is required'); return; }
    setSaving(true);
    setErr('');
    try {
      await onSave({
        ...form,
        tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
      });
    } catch (e) {
      setErr(fmtErr(e?.response?.data?.detail) || e.message);
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="bg-[#111] border border-white/10 rounded-xl p-5 mb-6">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[13px] font-semibold text-white">New Task</span>
        <button onClick={onCancel} className="text-[#555] hover:text-white transition-colors"><X size={14} /></button>
      </div>

      {err && <div className="mb-3 text-[11px] text-red-400">{err}</div>}

      <div className="space-y-3">
        <input value={form.title} onChange={e => set('title', e.target.value)}
          placeholder="Task title *"
          className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2 text-[13px] text-white placeholder-[#444] outline-none focus:border-[#002FA7]" />

        <textarea value={form.description} onChange={e => set('description', e.target.value)}
          placeholder="Description (optional)" rows={2}
          className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2 text-[12px] text-white placeholder-[#444] outline-none focus:border-[#002FA7] resize-none" />

        <textarea value={form.prompt} onChange={e => set('prompt', e.target.value)}
          placeholder="Agent instruction / prompt" rows={3}
          className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2 text-[12px] font-mono text-white placeholder-[#444] outline-none focus:border-[#002FA7] resize-none" />

        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
          <div>
            <label className="block text-[9px] uppercase text-[#555] mb-1">Priority</label>
            <select value={form.priority} onChange={e => set('priority', e.target.value)}
              className="w-full bg-black/30 border border-white/8 rounded-md px-2 py-1.5 text-[11px] text-white outline-none focus:border-[#002FA7]">
              {['urgent','high','medium','low'].map(p => <option key={p} value={p}>{p}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[9px] uppercase text-[#555] mb-1">Type</label>
            <select value={form.task_type} onChange={e => set('task_type', e.target.value)}
              className="w-full bg-black/30 border border-white/8 rounded-md px-2 py-1.5 text-[11px] text-white outline-none focus:border-[#002FA7]">
              {['general','code_generation','code_review','repo_editing','reasoning'].map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[9px] uppercase text-[#555] mb-1">Agent ID</label>
            <input value={form.agent_id} onChange={e => set('agent_id', e.target.value)}
              placeholder="(optional)"
              className="w-full bg-black/30 border border-white/8 rounded-md px-2 py-1.5 text-[11px] text-white placeholder-[#444] outline-none focus:border-[#002FA7]" />
          </div>
          <div>
            <label className="block text-[9px] uppercase text-[#555] mb-1">Runtime</label>
            <select value={form.runtime_id} onChange={e => set('runtime_id', e.target.value)}
              className="w-full bg-black/30 border border-white/8 rounded-md px-2 py-1.5 text-[11px] text-white outline-none focus:border-[#002FA7]">
              <option value="">Auto</option>
              {['hermes','opencode','goose','aider'].map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
        </div>

        <input value={form.tags} onChange={e => set('tags', e.target.value)}
          placeholder="Tags (comma-separated)"
          className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2 text-[11px] text-white placeholder-[#444] outline-none focus:border-[#002FA7]" />

        <div className="flex items-center gap-2">
          <input type="checkbox" id="task_requires_approval" checked={form.requires_approval}
            onChange={e => set('requires_approval', e.target.checked)} className="accent-[#002FA7]" />
          <label htmlFor="task_requires_approval" className="text-[11px] text-[#666]">
            Require approval before execution
          </label>
        </div>

        <div className="flex gap-2">
          <button onClick={handleSave} disabled={saving}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#002FA7] hover:bg-[#002585] text-white text-[11px] font-medium rounded-md transition-colors disabled:opacity-50">
            {saving ? <Loader2 size={11} className="animate-spin" /> : <Save size={11} />}
            Create Task
          </button>
          <button onClick={onCancel}
            className="px-4 py-2 text-[#555] text-[11px] border border-white/8 rounded-md hover:text-white transition-colors">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

// ── Main page ─────────────────────────────────────────────────────────────────

export default function TasksPage() {
  const [tasks, setTasks] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showCreate, setShowCreate] = useState(false);
  const [statusFilter, setStatusFilter] = useState('');

  const load = useCallback(async (status) => {
    setLoading(true);
    setError('');
    try {
      const r = await listTasks({ status: status || undefined, limit: 100 });
      setTasks(r.data.tasks || []);
    } catch (e) {
      setError(fmtErr(e?.response?.data?.detail) || e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(statusFilter); }, [load, statusFilter]);

  const handleCreate = async (form) => {
    await createTask(form);
    setShowCreate(false);
    await load(statusFilter);
  };

  const handleStatusChange = async (taskId, newStatus) => {
    try {
      await updateTask(taskId, { status: newStatus });
      await load(statusFilter);
    } catch (e) {
      setError(fmtErr(e?.response?.data?.detail) || e.message);
    }
  };

  const handleRetry = async (taskId) => {
    try { await retryTask(taskId); await load(statusFilter); }
    catch (e) { setError(fmtErr(e?.response?.data?.detail) || e.message); }
  };

  const handleEscalate = async (taskId) => {
    try { await escalateTask(taskId); await load(statusFilter); }
    catch (e) { setError(fmtErr(e?.response?.data?.detail) || e.message); }
  };

  // Count by status
  const counts = tasks.reduce((acc, t) => { acc[t.status] = (acc[t.status] || 0) + 1; return acc; }, {});

  return (
    <div className="p-5 sm:p-6 lg:p-8 max-w-5xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>
          Tasks
        </h1>
        <p className="text-sm text-[#555] mt-1">Track agent work items through their lifecycle</p>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 bg-red-500/8 border border-red-500/15 rounded-lg text-[12px] text-red-400 flex items-center gap-2">
          <AlertCircle size={13} /> {error}
          <button onClick={() => setError('')} className="ml-auto"><X size={11} /></button>
        </div>
      )}

      {/* Status filter chips */}
      <div className="flex items-center gap-2 mb-4 flex-wrap">
        {[{ v: '', l: 'All' }, ...Object.keys(STATUS_META).map(k => ({ v: k, l: STATUS_META[k].label }))].map(({ v, l }) => (
          <button key={v} onClick={() => setStatusFilter(v)}
            className={cls(
              'text-[10px] font-mono px-3 py-1.5 rounded-full border transition-colors',
              statusFilter === v
                ? 'border-[#002FA7]/40 bg-[#002FA7]/15 text-[#4477FF]'
                : 'border-white/8 bg-white/3 text-[#555] hover:text-[#888]',
            )}>
            {l}
            {counts[v] > 0 && v && <span className="ml-1 text-[#333]">({counts[v]})</span>}
          </button>
        ))}
        <button onClick={() => load(statusFilter)} className="ml-auto text-[#444] hover:text-[#888] transition-colors">
          <RefreshCw size={12} />
        </button>
      </div>

      {showCreate && (
        <CreateTaskForm onSave={handleCreate} onCancel={() => setShowCreate(false)} />
      )}

      {!showCreate && (
        <button onClick={() => setShowCreate(true)}
          className="mb-5 flex items-center gap-2 px-4 py-2.5 bg-[#002FA7] hover:bg-[#002585] text-white text-[12px] font-medium rounded-lg transition-colors">
          <Plus size={13} /> New Task
        </button>
      )}

      {loading ? (
        <div className="flex items-center gap-2 justify-center text-[#555] py-12 text-sm">
          <Loader2 size={15} className="animate-spin" /> Loading tasks...
        </div>
      ) : tasks.length === 0 ? (
        <div className="text-center py-16 text-[#444]">
          <CheckCircle2 size={32} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No tasks {statusFilter ? `with status '${statusFilter}'` : 'yet'}.</p>
        </div>
      ) : (
        <div className="space-y-3">
          {tasks.map(t => (
            <TaskCard key={t.task_id} task={t}
              onStatusChange={handleStatusChange}
              onRetry={handleRetry}
              onEscalate={handleEscalate} />
          ))}
        </div>
      )}
    </div>
  );
}
