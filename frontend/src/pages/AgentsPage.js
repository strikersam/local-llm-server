/**
 * AgentsPage — Manage agent profiles.
 *
 * Shows all agents with their status, preferred runtime, last activity,
 * and allows creating/editing/deleting agent profiles.
 */
import React, { useState, useEffect, useCallback } from 'react';
import { Bot, Plus, Trash2, Edit3, ChevronRight, Loader2, CheckCircle, AlertCircle, Zap, Brain, X, Save } from 'lucide-react';
import { listAgents, createAgent, updateAgent, deleteAgent, fmtErr } from '../api';

function cls(...parts) { return parts.filter(Boolean).join(' '); }

const STATUS_STYLE = {
  idle:    'text-gray-400 border-gray-500/20 bg-gray-500/8',
  running: 'text-emerald-400 border-emerald-500/20 bg-emerald-500/8',
  error:   'text-red-400 border-red-500/20 bg-red-500/8',
};

const RUNTIME_OPTIONS = ['hermes', 'opencode', 'goose', 'aider', 'openhands'];
const TASK_TYPES = ['general', 'code_generation', 'code_review', 'repo_editing', 'reasoning', 'scheduled'];

function AgentCard({ agent, onEdit, onDelete }) {
  const status = agent.status || 'idle';
  const style = STATUS_STYLE[status] || STATUS_STYLE.idle;
  return (
    <div className="bg-[#111] border border-white/8 rounded-xl p-4 hover:border-white/14 transition-all group"
      data-testid={`agent-card-${agent.agent_id}`}>
      <div className="flex items-start justify-between mb-3">
        <div className="flex items-center gap-2.5">
          <div className="w-9 h-9 rounded-lg flex items-center justify-center bg-[#002FA7]/10 border border-[#002FA7]/20">
            <Bot size={15} className="text-[#4477FF]" />
          </div>
          <div>
            <div className="text-[13px] font-semibold text-white">{agent.name}</div>
            <div className="text-[10px] text-[#555]">{agent.role || 'General'}</div>
          </div>
        </div>
        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button onClick={() => onEdit(agent)}
            className="p-1.5 text-[#555] hover:text-white transition-colors rounded">
            <Edit3 size={12} />
          </button>
          <button onClick={() => onDelete(agent.agent_id)}
            className="p-1.5 text-[#555] hover:text-red-400 transition-colors rounded">
            <Trash2 size={12} />
          </button>
        </div>
      </div>

      {agent.description && (
        <p className="text-[11px] text-[#666] mb-3 line-clamp-2">{agent.description}</p>
      )}

      <div className="flex flex-wrap gap-1.5 mb-3">
        {agent.preferred_runtime && (
          <span className="text-[9px] font-mono px-2 py-0.5 rounded border border-[#002FA7]/20 bg-[#002FA7]/8 text-[#4477FF]">
            {agent.preferred_runtime}
          </span>
        )}
        {agent.task_specializations?.slice(0, 3).map(t => (
          <span key={t} className="text-[9px] font-mono px-2 py-0.5 rounded border border-white/8 bg-white/4 text-[#666]">
            {t}
          </span>
        ))}
      </div>

      <div className="flex items-center justify-between">
        <span className={cls('inline-flex items-center gap-1 text-[9px] px-2 py-0.5 rounded-full border', style)}>
          <span className={cls('w-1.5 h-1.5 rounded-full', status === 'running' ? 'bg-emerald-400 animate-pulse' : 'bg-current opacity-60')} />
          {status}
        </span>
        {agent.last_active && (
          <span className="text-[9px] text-[#444]">
            {new Date(agent.last_active * 1000).toLocaleDateString()}
          </span>
        )}
      </div>
    </div>
  );
}

function AgentForm({ agent, onSave, onCancel }) {
  const [form, setForm] = useState(agent || {
    name: '', description: '', role: '', system_prompt: '',
    preferred_runtime: 'hermes', fallback_runtimes: [],
    task_specializations: [], requires_approval: false,
    cost_policy: 'local_only',
  });

  const set = (k, v) => setForm(f => ({ ...f, [k]: v }));

  const handleSave = () => {
    if (!form.name?.trim()) return;
    onSave(form);
  };

  return (
    <div className="bg-[#111] border border-white/10 rounded-xl p-5">
      <div className="flex items-center justify-between mb-4">
        <span className="text-[13px] font-semibold text-white">
          {agent ? 'Edit Agent' : 'New Agent Profile'}
        </span>
        <button onClick={onCancel} className="text-[#555] hover:text-white transition-colors">
          <X size={14} />
        </button>
      </div>

      <div className="space-y-3">
        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-[10px] uppercase tracking-widest text-[#555] mb-1">Name *</label>
            <input value={form.name} onChange={e => set('name', e.target.value)}
              placeholder="e.g. CodeBot Alpha"
              className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2 text-[12px] text-white placeholder-[#444] outline-none focus:border-[#002FA7] transition-colors" />
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-widest text-[#555] mb-1">Role</label>
            <input value={form.role} onChange={e => set('role', e.target.value)}
              placeholder="e.g. Senior Engineer"
              className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2 text-[12px] text-white placeholder-[#444] outline-none focus:border-[#002FA7] transition-colors" />
          </div>
        </div>

        <div>
          <label className="block text-[10px] uppercase tracking-widest text-[#555] mb-1">Description</label>
          <input value={form.description} onChange={e => set('description', e.target.value)}
            placeholder="What this agent does"
            className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2 text-[12px] text-white placeholder-[#444] outline-none focus:border-[#002FA7] transition-colors" />
        </div>

        <div>
          <label className="block text-[10px] uppercase tracking-widest text-[#555] mb-1">System Prompt</label>
          <textarea value={form.system_prompt} onChange={e => set('system_prompt', e.target.value)}
            rows={4} placeholder="You are a helpful AI engineer..."
            className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2 text-[12px] text-white placeholder-[#444] outline-none focus:border-[#002FA7] transition-colors resize-none font-mono" />
        </div>

        <div className="grid grid-cols-2 gap-3">
          <div>
            <label className="block text-[10px] uppercase tracking-widest text-[#555] mb-1">Preferred Runtime</label>
            <select value={form.preferred_runtime} onChange={e => set('preferred_runtime', e.target.value)}
              className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2 text-[12px] text-white outline-none focus:border-[#002FA7] transition-colors">
              {RUNTIME_OPTIONS.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <label className="block text-[10px] uppercase tracking-widest text-[#555] mb-1">Cost Policy</label>
            <select value={form.cost_policy} onChange={e => set('cost_policy', e.target.value)}
              className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2 text-[12px] text-white outline-none focus:border-[#002FA7] transition-colors">
              <option value="local_only">Local Only</option>
              <option value="local_first">Local First (allow escalation)</option>
              <option value="ask_before_paid">Ask Before Paid</option>
            </select>
          </div>
        </div>

        <div>
          <label className="block text-[10px] uppercase tracking-widest text-[#555] mb-1">Task Specializations</label>
          <div className="flex flex-wrap gap-1.5">
            {TASK_TYPES.map(t => (
              <button key={t} type="button"
                onClick={() => {
                  const cur = form.task_specializations || [];
                  set('task_specializations', cur.includes(t) ? cur.filter(x => x !== t) : [...cur, t]);
                }}
                className={cls(
                  'text-[9px] font-mono px-2 py-1 rounded border transition-colors',
                  (form.task_specializations || []).includes(t)
                    ? 'border-[#002FA7]/40 bg-[#002FA7]/15 text-[#4477FF]'
                    : 'border-white/8 bg-white/3 text-[#555] hover:text-[#888]',
                )}>
                {t}
              </button>
            ))}
          </div>
        </div>

        <div className="flex items-center gap-2">
          <input type="checkbox" id="requires_approval" checked={form.requires_approval}
            onChange={e => set('requires_approval', e.target.checked)}
            className="w-3.5 h-3.5 accent-[#002FA7]" />
          <label htmlFor="requires_approval" className="text-[11px] text-[#777]">
            Require human approval before sensitive executions
          </label>
        </div>

        <div className="flex gap-2 pt-1">
          <button onClick={handleSave}
            className="flex items-center gap-1.5 px-4 py-2 bg-[#002FA7] hover:bg-[#002585] text-white text-[11px] font-medium rounded-md transition-colors">
            <Save size={11} /> Save Agent
          </button>
          <button onClick={onCancel}
            className="px-4 py-2 text-[#555] text-[11px] border border-white/8 rounded-md hover:text-white hover:border-white/16 transition-colors">
            Cancel
          </button>
        </div>
      </div>
    </div>
  );
}

export default function AgentsPage() {
  const [agents, setAgents] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [showForm, setShowForm] = useState(false);
  const [editAgent, setEditAgent] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    setError('');
    try {
      const r = await listAgents();
      setAgents(r.data.agents || []);
    } catch (e) {
      setError(fmtErr(e?.response?.data?.detail) || e.message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSave = async (form) => {
    try {
      if (editAgent) {
        await updateAgent(editAgent.agent_id, form);
      } else {
        await createAgent(form);
      }
      setShowForm(false);
      setEditAgent(null);
      await load();
    } catch (e) {
      setError(fmtErr(e?.response?.data?.detail) || e.message);
    }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this agent profile?')) return;
    try {
      await deleteAgent(id);
      await load();
    } catch (e) {
      setError(fmtErr(e?.response?.data?.detail) || e.message);
    }
  };

  return (
    <div className="p-5 sm:p-6 lg:p-8 max-w-7xl mx-auto">
      <div className="mb-6">
        <h1 className="text-2xl font-bold tracking-tight text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>
          Agent Profiles
        </h1>
        <p className="text-sm text-[#555] mt-1">Configure autonomous agent personas with runtime preferences and cost policies</p>
      </div>

      {error && (
        <div className="mb-4 px-4 py-3 bg-red-500/8 border border-red-500/15 rounded-lg text-[12px] text-red-400 flex items-center gap-2">
          <AlertCircle size={13} /> {error}
        </div>
      )}

      {(showForm || editAgent) ? (
        <div className="mb-6">
          <AgentForm agent={editAgent} onSave={handleSave} onCancel={() => { setShowForm(false); setEditAgent(null); }} />
        </div>
      ) : (
        <button onClick={() => setShowForm(true)}
          className="mb-6 flex items-center gap-2 px-4 py-2.5 bg-[#002FA7] hover:bg-[#002585] text-white text-[12px] font-medium rounded-lg transition-colors">
          <Plus size={13} /> New Agent Profile
        </button>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-[#555] text-sm py-8 justify-center">
          <Loader2 size={15} className="animate-spin" /> Loading agents...
        </div>
      ) : agents.length === 0 ? (
        <div className="text-center py-16 text-[#444]">
          <Bot size={32} className="mx-auto mb-3 opacity-30" />
          <p className="text-sm">No agent profiles yet.</p>
          <p className="text-[11px] mt-1">Create your first agent profile to get started.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {agents.map(a => (
            <AgentCard key={a.agent_id} agent={a}
              onEdit={a => { setEditAgent(a); setShowForm(false); }}
              onDelete={handleDelete} />
          ))}
        </div>
      )}
    </div>
  );
}
