/**
 * TasksPage — Multica-style kanban swim-lane task board.
 *
 * Design: lifted from cp-tasks.jsx in the Control Plane design bundle.
 * Wired to the real tasks API: listTasks, createTask, updateTask, retryTask, escalateTask.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Plus, RefreshCw, X, Loader2, AlertTriangle, RotateCcw, ArrowUpCircle } from 'lucide-react';
import {
  listTasks,
  createTask,
  updateTask,
  retryTask,
  escalateTask,
  addTaskComment,
  listAgents,
  listRuntimes,
  runTask,
  fmtErr,
} from '../api';

function cls(...p) { return p.filter(Boolean).join(' '); }

function relTime(ts) {
  if (!ts) return '—';
  const diff = (Date.now() / 1000) - ts;
  if (diff < 60) return `${Math.round(diff)}s ago`;
  if (diff < 3600) return `${Math.round(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.round(diff / 3600)}h ago`;
  return new Date(ts * 1000).toLocaleDateString();
}

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

const COLS = [
  { id: 'todo',        label: 'TODO',        color: '#6E6E80' },
  { id: 'in_progress', label: 'IN PROGRESS', color: '#002FA7' },
  { id: 'in_review',   label: 'IN REVIEW',   color: '#F59E0B' },
  { id: 'blocked',     label: 'BLOCKED',     color: '#EF4444' },
  { id: 'done',        label: 'DONE',        color: '#10B981' },
  { id: 'failed',      label: 'FAILED',      color: '#7C3AED' },
];

const PRIORITY_DOT = {
  urgent: '#EF4444',
  high:   '#F59E0B',
  medium: '#3B82F6',
  low:    '#6E6E80',
};

function PriorityDot({ priority }) {
  const color = PRIORITY_DOT[priority] || PRIORITY_DOT.medium;
  return <div className="w-2 h-2 rounded-full shrink-0 mt-0.5" style={{ background: color }} />;
}

function StatusDot({ status }) {
  const colors = {
    todo: '#6E6E80', in_progress: '#10B981', in_review: '#F59E0B',
    blocked: '#EF4444', done: '#3B82F6', failed: '#7C3AED',
  };
  return <div className="w-2 h-2 rounded-full shrink-0" style={{ background: colors[status] || '#6E6E80' }} />;
}

// ── Task card ──────────────────────────────────────────────────────────────────

function TaskCard({ task, isSelected, onClick }) {
  return (
    <div
      onClick={onClick}
      className="cursor-pointer rounded-lg px-3.5 py-3 transition-all duration-150"
      style={{
        background: isSelected ? 'rgba(0,47,167,0.05)' : C.surface,
        border: `1px solid ${isSelected ? 'rgba(0,47,167,0.4)' : C.border}`,
      }}
      onMouseEnter={e => { if (!isSelected) { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'; e.currentTarget.style.background = '#18181D'; }}}
      onMouseLeave={e => { if (!isSelected) { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.background = C.surface; }}}
    >
      {/* Priority + title */}
      <div className="flex items-start gap-2 mb-2">
        <PriorityDot priority={task.priority} />
        <span className="text-[12px] leading-snug font-medium flex-1" style={{ color: '#D8D8E8' }}>
          {task.title}
        </span>
      </div>

      {/* Meta */}
      <div className="flex items-center gap-2 flex-wrap">
        {task.agent_id && (
          <span className="text-[9px] font-mono" style={{ color: C.tertiary }}>@{task.agent_id}</span>
        )}
        {task.tags && task.tags.slice(0, 2).map(tag => (
          <span key={tag} className="text-[8px] font-mono px-1.5 py-0.5 rounded"
            style={{ background: 'rgba(255,255,255,0.05)', color: C.tertiary }}>
            {tag}
          </span>
        ))}
        {task.due_date && (
          <span className="ml-auto text-[8px] font-mono" style={{ color: C.muted }}>
            {new Date(task.due_date * 1000).toLocaleDateString([], { month: 'short', day: 'numeric' })}
          </span>
        )}
      </div>

      {/* Blocked reason */}
      {task.blocked_reason && (
        <div className="mt-2 text-[9px] font-mono rounded px-2 py-1 leading-snug"
          style={{ color: 'rgba(239,68,68,0.7)', border: '1px solid rgba(239,68,68,0.15)', background: 'rgba(239,68,68,0.05)' }}>
          {task.blocked_reason}
        </div>
      )}

      {/* Footer */}
      <div className="mt-1.5 text-[8px] font-mono" style={{ color: C.muted }}>
        {relTime(task.updated_at)}
      </div>
    </div>
  );
}

// ── Task detail panel ──────────────────────────────────────────────────────────

function TaskDetailPanel({ task, onClose, onStatusChange, onRetry, onEscalate, onComment, onRunNow }) {
  const STATUSES = ['todo', 'in_progress', 'in_review', 'blocked', 'done', 'failed'];
  const [actionLoading, setActionLoading] = useState('');
  const [commentBody, setCommentBody] = useState('');

  async function doStatusChange(s) {
    setActionLoading('status');
    try { await onStatusChange(task.task_id, s); } finally { setActionLoading(''); }
  }
  async function doRetry() {
    setActionLoading('retry');
    try { await onRetry(task.task_id); } finally { setActionLoading(''); }
  }
  async function doEscalate() {
    setActionLoading('escalate');
    try { await onEscalate(task.task_id); } finally { setActionLoading(''); }
  }
  async function doRunNow() {
    setActionLoading('run');
    try { await onRunNow(task.task_id); } finally { setActionLoading(''); }
  }
  async function doComment() {
    const body = commentBody.trim();
    if (!body) return;
    setActionLoading('comment');
    try {
      await onComment(task.task_id, body);
      setCommentBody('');
    } finally {
      setActionLoading('');
    }
  }

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-md flex flex-col z-30 shadow-2xl"
      style={{ background: '#111116', borderLeft: '1px solid rgba(255,255,255,0.08)', top: 0 }}>

      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-4 border-b shrink-0"
        style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <PriorityDot priority={task.priority} />
        <div className="flex-1 min-w-0">
          <div className="text-[13px] font-semibold truncate" style={{ color: C.primary }}>{task.title}</div>
          <div className="text-[9px] font-mono mt-0.5" style={{ color: C.muted }}>{task.task_id}</div>
        </div>
        <button onClick={onClose}
          style={{ color: C.tertiary }}
          onMouseEnter={e => e.currentTarget.style.color = C.primary}
          onMouseLeave={e => e.currentTarget.style.color = C.tertiary}>
          <X size={14} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto p-5 space-y-5">

        {/* Status mover */}
        <div>
          <div className="text-[9px] font-mono uppercase tracking-wider mb-2" style={{ color: C.muted }}>Status</div>
          <div className="flex flex-wrap gap-1.5">
            {STATUSES.map(s => (
              <button key={s} onClick={() => doStatusChange(s)}
                disabled={actionLoading === 'status'}
                className="px-2.5 py-1 text-[9px] font-mono uppercase tracking-wider border rounded transition-colors"
                style={{
                  borderColor: task.status === s ? C.accent : 'rgba(255,255,255,0.08)',
                  background: task.status === s ? 'rgba(0,47,167,0.1)' : 'transparent',
                  color: task.status === s ? C.primary : C.tertiary,
                }}>
                {s.replace(/_/g, ' ')}
              </button>
            ))}
          </div>
        </div>

        {/* Description */}
        {task.description && (
          <div>
            <div className="text-[9px] font-mono uppercase tracking-wider mb-2" style={{ color: C.muted }}>Description</div>
            <p className="text-[11px] leading-relaxed" style={{ color: C.secondary }}>{task.description}</p>
          </div>
        )}

        {/* Meta */}
        <div className="space-y-2">
          {[
            { label: 'Agent',    value: task.agent_id || '—' },
            { label: 'Runtime',  value: task.last_runtime_id || task.runtime_id || '—' },
            { label: 'Model',    value: task.last_model_used || task.model_preference || '—' },
            { label: 'Priority', value: task.priority || 'medium' },
            { label: 'Updated',  value: relTime(task.updated_at) },
          ].map(({ label, value }) => (
            <div key={label} className="flex justify-between items-center py-2 border-b"
              style={{ borderColor: 'rgba(255,255,255,0.05)' }}>
              <span className="text-[10px] font-mono" style={{ color: C.muted }}>{label}</span>
              <span className="text-[10px] font-mono" style={{ color: C.secondary }}>{value}</span>
            </div>
          ))}
        </div>

        {/* Blocked reason */}
        {task.blocked_reason && (
          <div className="p-3 border rounded-lg"
            style={{ borderColor: 'rgba(239,68,68,0.2)', background: 'rgba(239,68,68,0.05)' }}>
            <div className="text-[9px] font-mono uppercase tracking-wider mb-1" style={{ color: '#EF4444' }}>Blocked — reason</div>
            <div className="text-[11px] font-mono leading-relaxed" style={{ color: 'rgba(252,165,165,0.8)' }}>{task.blocked_reason}</div>
          </div>
        )}

        {/* Review reason */}
        {task.review_reason && (
          <div className="p-3 border rounded-lg"
            style={{ borderColor: 'rgba(245,158,11,0.2)', background: 'rgba(245,158,11,0.05)' }}>
            <div className="text-[9px] font-mono uppercase tracking-wider mb-1" style={{ color: '#F59E0B' }}>In review</div>
            <div className="text-[11px] font-mono leading-relaxed" style={{ color: 'rgba(253,230,138,0.85)' }}>{task.review_reason}</div>
          </div>
        )}

        {/* Error */}
        {task.error_message && (
          <div className="p-3 border rounded-lg"
            style={{ borderColor: 'rgba(239,68,68,0.2)', background: 'rgba(239,68,68,0.05)' }}>
            <div className="text-[9px] font-mono uppercase tracking-wider mb-1" style={{ color: '#EF4444' }}>Error</div>
            <div className="text-[10px] font-mono leading-relaxed" style={{ color: 'rgba(252,165,165,0.7)' }}>{task.error_message}</div>
          </div>
        )}

        {/* Actions */}
        <div className="flex gap-2">
          {!['blocked', 'in_review', 'done'].includes(task.status) && (
            <button onClick={doRunNow} disabled={!!actionLoading}
              className="flex items-center gap-1.5 px-3 py-2 text-[10px] font-mono uppercase tracking-wider border rounded-lg transition-colors disabled:opacity-40"
              style={{ borderColor: 'rgba(59,130,246,0.3)', color: '#60A5FA' }}>
              {actionLoading === 'run'
                ? <Loader2 size={11} className="animate-spin" />
                : <RefreshCw size={11} />}
              Run now
            </button>
          )}
          <button onClick={doRetry} disabled={!!actionLoading}
            className="flex items-center gap-1.5 px-3 py-2 text-[10px] font-mono uppercase tracking-wider border rounded-lg transition-colors disabled:opacity-40"
            style={{ borderColor: 'rgba(255,255,255,0.1)', color: C.tertiary }}>
            {actionLoading === 'retry'
              ? <Loader2 size={11} className="animate-spin" />
              : <RotateCcw size={11} />}
            Retry
          </button>
          <button onClick={doEscalate} disabled={!!actionLoading}
            className="flex items-center gap-1.5 px-3 py-2 text-[10px] font-mono uppercase tracking-wider border rounded-lg transition-colors disabled:opacity-40"
            style={{ borderColor: 'rgba(245,158,11,0.3)', color: '#F59E0B' }}>
            {actionLoading === 'escalate'
              ? <Loader2 size={11} className="animate-spin" />
              : <ArrowUpCircle size={11} />}
            Escalate
          </button>
        </div>

        {/* Comments */}
        <div>
          <div className="text-[9px] font-mono uppercase tracking-wider mb-2" style={{ color: C.muted }}>Discussion</div>
          <div className="space-y-2">
            {(task.comments || []).length === 0 && (
              <div className="text-[10px] font-mono" style={{ color: C.muted }}>No comments yet.</div>
            )}
            {(task.comments || []).map(comment => (
              <div key={comment.comment_id} className="rounded-lg border px-3 py-2"
                style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}>
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[10px] font-mono" style={{ color: C.secondary }}>{comment.author}</span>
                  <span className="text-[9px] font-mono" style={{ color: C.muted }}>{relTime(comment.created_at)}</span>
                </div>
                <div className="text-[11px] leading-relaxed" style={{ color: C.primary }}>{comment.body}</div>
              </div>
            ))}
          </div>
          <div className="mt-2 space-y-2">
            <textarea
              value={commentBody}
              onChange={e => setCommentBody(e.target.value)}
              rows={3}
              placeholder="Add a comment to continue the task…"
              className="w-full rounded-lg border bg-transparent px-3 py-2 text-[11px] outline-none resize-y"
              style={{ borderColor: 'rgba(255,255,255,0.08)', color: C.primary }}
            />
            <button onClick={doComment} disabled={actionLoading === 'comment' || !commentBody.trim()}
              className="px-3 py-2 text-[10px] font-mono uppercase tracking-wider rounded-lg disabled:opacity-40"
              style={{ background: C.accent, color: 'white' }}>
              {actionLoading === 'comment' ? 'Posting…' : 'Post Comment'}
            </button>
          </div>
        </div>

        {/* Execution history */}
        <div>
          <div className="text-[9px] font-mono uppercase tracking-wider mb-2" style={{ color: C.muted }}>Execution history</div>
          <div className="space-y-2">
            {(task.execution_log || []).length === 0 && (
              <div className="text-[10px] font-mono" style={{ color: C.muted }}>No history yet.</div>
            )}
            {(task.execution_log || []).slice().reverse().map((entry, idx) => (
              <div key={`${entry.timestamp}-${idx}`} className="rounded-lg border px-3 py-2"
                style={{ borderColor: 'rgba(255,255,255,0.06)', background: 'rgba(255,255,255,0.02)' }}>
                <div className="flex items-center justify-between gap-2 mb-1">
                  <span className="text-[9px] font-mono uppercase tracking-wider" style={{ color: C.tertiary }}>
                    {entry.event_type || entry.level}
                  </span>
                  <span className="text-[9px] font-mono" style={{ color: C.muted }}>{relTime(entry.timestamp)}</span>
                </div>
                <div className="text-[11px] leading-relaxed" style={{ color: C.primary }}>{entry.message}</div>
                {(entry.runtime_id || entry.model_used || entry.actor) && (
                  <div className="mt-1 text-[9px] font-mono" style={{ color: C.muted }}>
                    {[entry.actor, entry.runtime_id, entry.model_used].filter(Boolean).join(' · ')}
                  </div>
                )}
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}

// ── New task form ──────────────────────────────────────────────────────────────

function NewTaskForm({ colId, agents, runtimes, onAdd, onCancel }) {
  const [title, setTitle] = useState('');
  const [prompt, setPrompt] = useState('');
  const [agentId, setAgentId] = useState('');
  const [runtimeId, setRuntimeId] = useState('');
  const [taskType, setTaskType] = useState('general');
  const [priority, setPriority] = useState('medium');
  const [modelPreference, setModelPreference] = useState('');
  const [requiresApproval, setRequiresApproval] = useState(false);
  const [saving, setSaving] = useState(false);

  async function submit(runNow = false) {
    if (!title.trim() || saving) return;
    setSaving(true);
    try {
      await onAdd({
        title: title.trim(),
        prompt: prompt.trim(),
        agent_id: agentId || null,
        runtime_id: runtimeId || null,
        task_type: taskType,
        priority,
        model_preference: modelPreference.trim() || null,
        requires_approval: requiresApproval,
        status: runNow || colId === 'in_progress' ? 'in_progress' : 'todo',
        runNow,
      });
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg p-3 border space-y-2.5"
      style={{ borderColor: 'rgba(0,47,167,0.4)', background: 'rgba(0,47,167,0.05)' }}>
      <textarea
        autoFocus
        value={title}
        onChange={e => setTitle(e.target.value)}
        data-testid="task-form-title"
        onKeyDown={e => {
          if (e.key === 'Enter' && (e.metaKey || e.ctrlKey)) { e.preventDefault(); submit(true); }
          if (e.key === 'Escape') onCancel();
        }}
        rows={2}
        placeholder="Task title…"
        className="w-full bg-transparent text-[12px] font-mono resize-none outline-none"
        style={{ color: C.primary }}
      />

      <textarea
        value={prompt}
        onChange={e => setPrompt(e.target.value)}
        data-testid="task-form-prompt"
        rows={4}
        placeholder="Execution prompt / acceptance criteria…"
        className="w-full rounded border bg-transparent px-2.5 py-2 text-[11px] resize-y outline-none"
        style={{ color: C.primary, borderColor: 'rgba(255,255,255,0.08)' }}
      />

      <div className="grid grid-cols-2 gap-2">
        <label className="space-y-1 text-[9px] font-mono uppercase" style={{ color: C.muted }}>
          Agent
          <select value={agentId} onChange={e => setAgentId(e.target.value)} data-testid="task-form-agent"
            className="w-full rounded border bg-transparent px-2 py-1.5 text-[11px] outline-none"
            style={{ color: C.primary, borderColor: 'rgba(255,255,255,0.08)' }}>
            <option value="">Auto-select</option>
            {agents.map(agent => (
              <option key={agent.agent_id} value={agent.agent_id}>{agent.name || agent.agent_id}</option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-[9px] font-mono uppercase" style={{ color: C.muted }}>
          Runtime
          <select value={runtimeId} onChange={e => setRuntimeId(e.target.value)} data-testid="task-form-runtime"
            className="w-full rounded border bg-transparent px-2 py-1.5 text-[11px] outline-none"
            style={{ color: C.primary, borderColor: 'rgba(255,255,255,0.08)' }}>
            <option value="">Route automatically</option>
            {runtimes.map(runtime => (
              <option key={runtime.runtime_id} value={runtime.runtime_id}>{runtime.display_name || runtime.runtime_id}</option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-[9px] font-mono uppercase" style={{ color: C.muted }}>
          Task type
          <select value={taskType} onChange={e => setTaskType(e.target.value)} data-testid="task-form-type"
            className="w-full rounded border bg-transparent px-2 py-1.5 text-[11px] outline-none"
            style={{ color: C.primary, borderColor: 'rgba(255,255,255,0.08)' }}>
            {['general', 'code_generation', 'code_review', 'repo_editing', 'git_operations', 'web_browse'].map(type => (
              <option key={type} value={type}>{type.replace(/_/g, ' ')}</option>
            ))}
          </select>
        </label>

        <label className="space-y-1 text-[9px] font-mono uppercase" style={{ color: C.muted }}>
          Priority
          <select value={priority} onChange={e => setPriority(e.target.value)} data-testid="task-form-priority"
            className="w-full rounded border bg-transparent px-2 py-1.5 text-[11px] outline-none"
            style={{ color: C.primary, borderColor: 'rgba(255,255,255,0.08)' }}>
            {['low', 'medium', 'high', 'urgent'].map(level => (
              <option key={level} value={level}>{level}</option>
            ))}
          </select>
        </label>
      </div>

      <input
        value={modelPreference}
        onChange={e => setModelPreference(e.target.value)}
        data-testid="task-form-model"
        placeholder="Optional model preference"
        className="w-full rounded border bg-transparent px-2.5 py-2 text-[11px] outline-none"
        style={{ color: C.primary, borderColor: 'rgba(255,255,255,0.08)' }}
      />

      <label className="flex items-center gap-2 text-[10px] font-mono" style={{ color: C.secondary }}>
        <input type="checkbox" checked={requiresApproval} onChange={e => setRequiresApproval(e.target.checked)} />
        Require human approval before done
      </label>

      <div className="flex gap-1.5 mt-1.5 flex-wrap">
        <button onClick={() => submit(false)} disabled={saving}
          className="px-2 py-1 text-[9px] font-mono uppercase text-white rounded disabled:opacity-50"
          style={{ background: C.accent }}>
          {saving ? '…' : 'Add to board'}
        </button>
        <button onClick={() => submit(true)} disabled={saving}
          className="px-2 py-1 text-[9px] font-mono uppercase rounded disabled:opacity-50"
          style={{ border: '1px solid rgba(59,130,246,0.3)', color: '#60A5FA' }}>
          Create & run
        </button>
        <button onClick={onCancel}
          className="px-2 py-1 text-[9px] font-mono uppercase border rounded transition-colors"
          style={{ borderColor: 'rgba(255,255,255,0.1)', color: C.tertiary }}>
          Cancel
        </button>
      </div>
    </div>
  );
}

// ── Main page ──────────────────────────────────────────────────────────────────

export default function TasksPage() {
  const [tasks, setTasks]           = useState([]);
  const [agents, setAgents]         = useState([]);
  const [runtimes, setRuntimes]     = useState([]);
  const [loading, setLoading]       = useState(true);
  const [selected, setSelected]     = useState(null);
  const [newTaskCol, setNewTaskCol] = useState(null);
  const [filter, setFilter]         = useState('all');
  const [error, setError]           = useState('');

  const load = useCallback(async () => {
    setLoading(prev => prev && tasks.length === 0);
    setError('');
    try {
      const r = await listTasks({ limit: 200 });
      const nextTasks = r.data.tasks || [];
      setTasks(nextTasks);
      setSelected(prev => prev ? nextTasks.find(t => t.task_id === prev.task_id) || null : null);
    } catch (e) {
      setError(fmtErr(e));
    } finally {
      setLoading(false);
    }
  }, [tasks.length]);

  const loadMeta = useCallback(async () => {
    try {
      const [agentsResponse, runtimesResponse] = await Promise.all([
        listAgents(),
        listRuntimes(),
      ]);
      setAgents(agentsResponse.data.agents || []);
      setRuntimes(runtimesResponse.data.runtimes || []);
    } catch (e) {
      setError(prev => prev || fmtErr(e));
    }
  }, []);

  useEffect(() => { load(); }, [load]);
  useEffect(() => { loadMeta(); }, [loadMeta]);
  useEffect(() => {
    const timer = setInterval(() => { load(); }, 5000);
    return () => clearInterval(timer);
  }, [load]);

  // Agents derived from task data
  const agentFilters = [...new Set(tasks.map(t => t.agent_id).filter(Boolean))];

  const filtered = filter === 'all' ? tasks : tasks.filter(t => t.agent_id === filter);

  async function handleAdd(payload) {
    const { runNow: shouldRunNow, ...taskPayload } = payload;
    const createResponse = await createTask(taskPayload);
    const createdTask = createResponse.data.task;
    setTasks(prev => [createdTask, ...prev]);
    if (shouldRunNow) {
      await runTask(createdTask.task_id);
      await load();
    }
    setNewTaskCol(null);
  }

  async function handleStatusChange(taskId, status) {
    const r = await updateTask(taskId, { status });
    setTasks(prev => prev.map(t => t.task_id === taskId ? r.data.task : t));
    if (selected?.task_id === taskId) setSelected(r.data.task);
    if (status === 'in_progress' && r.data.task?.pending_agent_run) {
      await runTask(taskId);
      await load();
    }
  }

  async function handleRetry(taskId) {
    const r = await retryTask(taskId);
    setTasks(prev => prev.map(t => t.task_id === taskId ? r.data.task : t));
    if (selected?.task_id === taskId) setSelected(r.data.task);
    if (r.data.task?.pending_agent_run) {
      await runTask(taskId);
      await load();
    }
  }

  async function handleEscalate(taskId) {
    const r = await escalateTask(taskId);
    setTasks(prev => prev.map(t => t.task_id === taskId ? r.data.task : t));
    if (selected?.task_id === taskId) setSelected(r.data.task);
  }

  async function handleComment(taskId, body) {
    const r = await addTaskComment(taskId, { body });
    setTasks(prev => prev.map(t => t.task_id === taskId ? r.data.task : t));
    if (selected?.task_id === taskId) setSelected(r.data.task);
    if (r.data.task?.pending_agent_run) {
      await runTask(taskId);
      await load();
    }
  }

  async function handleRunNow(taskId) {
    await runTask(taskId);
    await load();
  }

  const openCount = tasks.filter(t => t.status !== 'done').length;
  const doneCount = tasks.filter(t => t.status === 'done').length;

  return (
    <div className="h-full flex flex-col overflow-hidden" style={{ background: C.bg }} data-testid="tasks-page">

      {/* Header */}
      <div className="flex items-center gap-3 px-5 py-3.5 border-b shrink-0 flex-wrap"
        style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex-1">
          <h1 className="text-[15px] font-bold tracking-tight" style={{ fontFamily: 'var(--font-main)', color: C.primary }}>
            Tasks
          </h1>
          <p className="text-[10px] font-mono" style={{ color: C.muted }}>
            {openCount} open · {doneCount} done
          </p>
        </div>

        {/* Agent filter pills */}
        <div className="flex items-center gap-1.5 flex-wrap">
          <button onClick={() => setFilter('all')}
            className="px-2.5 py-1 text-[10px] font-mono border rounded transition-colors"
            style={{
              borderColor: filter === 'all' ? C.accent : 'rgba(255,255,255,0.08)',
              background: filter === 'all' ? 'rgba(0,47,167,0.1)' : 'transparent',
              color: filter === 'all' ? C.primary : C.tertiary,
            }}>
            All
          </button>
          {agentFilters.map(ag => (
            <button key={ag} onClick={() => setFilter(ag)}
              className="px-2.5 py-1 text-[10px] font-mono border rounded transition-colors"
              style={{
                borderColor: filter === ag ? C.accent : 'rgba(255,255,255,0.08)',
                background: filter === ag ? 'rgba(0,47,167,0.1)' : 'transparent',
                color: filter === ag ? C.primary : C.tertiary,
              }}>
              {ag.split('-')[0]}
            </button>
          ))}
        </div>

        <button onClick={load} disabled={loading}
          className="p-2 border rounded-lg transition-colors disabled:opacity-40"
          style={{ borderColor: 'rgba(255,255,255,0.08)', color: C.tertiary }}>
          <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
        </button>

        <button
          className="flex items-center gap-1.5 px-3 py-2 text-[10px] font-mono uppercase tracking-wider text-white rounded-lg transition-colors"
          style={{ background: C.accent }}
          onClick={() => { setNewTaskCol('todo'); setSelected(null); }}>
          <Plus size={11} /> New Task
        </button>
      </div>

      {error && (
        <div className="mx-5 mt-3 flex items-center gap-2 px-4 py-3 rounded-lg text-[11px] text-amber-400 border"
          style={{ background: 'rgba(245,158,11,0.06)', borderColor: 'rgba(245,158,11,0.15)' }}>
          <AlertTriangle size={12} /> {error}
        </div>
      )}

      {/* Kanban board */}
      <div className="flex-1 flex overflow-x-auto overflow-y-hidden">
        {COLS.map(col => {
          const colTasks = filtered.filter(t => t.status === col.id);
          return (
            <div key={col.id} className="flex-shrink-0 w-72 flex flex-col border-r last:border-r-0"
              style={{ borderColor: 'rgba(255,255,255,0.05)' }}>

              {/* Column header */}
              <div className="flex items-center gap-2 px-3.5 py-3 border-b shrink-0"
                style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
                <div className="w-2 h-2 rounded-full" style={{ background: col.color }} />
                <span className="text-[10px] font-mono font-bold tracking-[0.15em] uppercase"
                  style={{ color: col.color }}>{col.label}</span>
                <span className="ml-auto text-[9px] font-mono px-1.5 py-0.5 rounded"
                  style={{ background: 'rgba(255,255,255,0.05)', color: C.muted }}>
                  {colTasks.length}
                </span>
              </div>

              {/* Cards */}
              <div className="flex-1 overflow-y-auto p-2 space-y-1.5">

                {/* New task input for this column */}
                {newTaskCol === col.id && (
                  <NewTaskForm
                    colId={col.id}
                    agents={agents}
                    runtimes={runtimes}
                    onAdd={handleAdd}
                    onCancel={() => setNewTaskCol(null)}
                  />
                )}

                {/* Placeholder if empty */}
                {colTasks.length === 0 && newTaskCol !== col.id && (
                  <div className="py-6 text-center text-[10px] font-mono" style={{ color: C.muted }}>
                    — empty —
                  </div>
                )}

                {colTasks.map(task => (
                  <TaskCard
                    key={task.task_id}
                    task={task}
                    isSelected={selected?.task_id === task.task_id}
                    onClick={() => setSelected(selected?.task_id === task.task_id ? null : task)}
                  />
                ))}

                {/* Add button */}
                {newTaskCol !== col.id && (
                  <button
                    onClick={() => { setNewTaskCol(col.id); setSelected(null); }}
                    className="w-full flex items-center gap-1.5 px-3 py-2 text-[10px] font-mono rounded-lg transition-colors"
                    style={{ color: C.muted }}
                    onMouseEnter={e => { e.currentTarget.style.color = C.secondary; e.currentTarget.style.background = 'rgba(255,255,255,0.02)'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = C.muted; e.currentTarget.style.background = 'transparent'; }}>
                    <Plus size={10} /> Add task
                  </button>
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Task detail panel */}
      {selected && (
        <TaskDetailPanel
          task={selected}
          onClose={() => setSelected(null)}
          onStatusChange={handleStatusChange}
          onRetry={handleRetry}
          onEscalate={handleEscalate}
          onComment={handleComment}
          onRunNow={handleRunNow}
        />
      )}
    </div>
  );
}
