import React, { useState, useEffect } from 'react';
import { listApiKeys, createApiKey, deleteApiKey } from '../api';
import { Key, Plus, Trash2, Copy, CheckCircle, X, ShieldCheck } from 'lucide-react';

export default function ApiKeysPage() {
  const [keys, setKeys] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ email: '', department: 'general', label: '' });
  const [newKey, setNewKey] = useState(null);
  const [copied, setCopied] = useState(false);

  useEffect(() => { load(); }, []);
  const load = () => listApiKeys().then(r => setKeys(r.data.keys || [])).catch(() => {});

  const handleCreate = async () => {
    if (!form.email) return;
    try {
      const { data } = await createApiKey(form);
      setNewKey(data.api_key);
      setShowAdd(false);
      setForm({ email: '', department: 'general', label: '' });
      load();
    } catch (err) { alert(err?.response?.data?.detail || 'Failed to create key'); }
  };

  const copyKey = () => {
    navigator.clipboard.writeText(newKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-5 sm:p-6 lg:p-8 max-w-5xl mx-auto" data-testid="api-keys-page">

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-7 animate-fade-in">
        <div>
          <h1 className="text-3xl font-bold tracking-[-0.03em] text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>API Keys</h1>
          <p className="text-sm text-[#555555] mt-1">Issue access credentials for Cursor, Claude Code, Aider, and other tools</p>
        </div>
        <button
          onClick={() => setShowAdd(s => !s)}
          className="inline-flex items-center gap-2 bg-[#002FA7] hover:bg-[#0038CC] text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-all shadow-[0_4px_12px_rgba(0,47,167,0.3)] min-h-[42px]"
          data-testid="create-key-button"
        >
          <Plus size={14} />
          Issue Key
        </button>
      </div>

      {/* New key banner */}
      {newKey && (
        <div className="bg-emerald-500/8 border border-emerald-500/20 rounded-xl p-5 mb-6 animate-scale-in" data-testid="new-key-display">
          <div className="flex items-center justify-between mb-3">
            <div className="flex items-center gap-2">
              <ShieldCheck size={15} className="text-emerald-400" />
              <span className="text-sm font-semibold text-emerald-400">New API Key — copy now, shown once only</span>
            </div>
            <button onClick={() => setNewKey(null)} className="p-1 text-[#555555] hover:text-white rounded transition-colors">
              <X size={14} />
            </button>
          </div>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-center gap-2">
            <code className="flex-1 bg-black/40 border border-white/8 rounded-lg px-4 py-2.5 text-sm text-white font-mono break-all">{newKey}</code>
            <button
              onClick={copyKey}
              className={`flex items-center justify-center gap-2 border rounded-lg px-4 py-2.5 text-sm font-medium transition-all min-h-[42px] whitespace-nowrap ${
                copied
                  ? 'border-emerald-500/40 text-emerald-400 bg-emerald-500/10'
                  : 'border-white/10 text-[#A0A0A0] hover:text-white hover:border-white/20'
              }`}
              data-testid="copy-key-button"
            >
              {copied ? <CheckCircle size={14} /> : <Copy size={14} />}
              {copied ? 'Copied!' : 'Copy'}
            </button>
          </div>
        </div>
      )}

      {/* Add form */}
      {showAdd && (
        <div className="bg-[#111111] border border-[#002FA7]/20 rounded-xl p-5 sm:p-6 mb-6 animate-fade-in" data-testid="add-key-form">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-base font-semibold text-white">Issue New Key</h2>
            <button onClick={() => setShowAdd(false)} className="p-1.5 text-[#555555] hover:text-white rounded-lg hover:bg-white/5 transition-colors">
              <X size={15} />
            </button>
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-4">
            <div>
              <label className="block text-[11px] font-semibold tracking-widest uppercase text-[#555555] mb-1.5">Email</label>
              <input
                value={form.email}
                onChange={e => setForm({ ...form, email: e.target.value })}
                placeholder="user@company.com"
                className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2.5 text-sm text-white placeholder-[#444] outline-none focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7]/25 transition-all min-h-[40px]"
                data-testid="key-email-input"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold tracking-widest uppercase text-[#555555] mb-1.5">Department</label>
              <input
                value={form.department}
                onChange={e => setForm({ ...form, department: e.target.value })}
                className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2.5 text-sm text-white placeholder-[#444] outline-none focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7]/25 transition-all min-h-[40px]"
                data-testid="key-dept-input"
              />
            </div>
            <div>
              <label className="block text-[11px] font-semibold tracking-widest uppercase text-[#555555] mb-1.5">Label (optional)</label>
              <input
                value={form.label}
                onChange={e => setForm({ ...form, label: e.target.value })}
                placeholder="Cursor, Aider…"
                className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2.5 text-sm text-white placeholder-[#444] outline-none focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7]/25 transition-all min-h-[40px]"
                data-testid="key-label-input"
              />
            </div>
          </div>
          <div className="flex gap-2">
            <button onClick={handleCreate} className="bg-[#002FA7] hover:bg-[#0038CC] text-white px-5 py-2.5 rounded-lg text-sm font-semibold transition-all min-h-[40px]" data-testid="issue-key-button">
              Issue Key
            </button>
            <button onClick={() => setShowAdd(false)} className="px-4 py-2.5 rounded-lg border border-white/8 text-sm text-[#666666] hover:text-white hover:bg-white/5 transition-all min-h-[40px]">
              Cancel
            </button>
          </div>
        </div>
      )}

      {/* Keys list */}
      <div className="bg-[#111111] border border-white/8 rounded-xl overflow-hidden">
        {/* Desktop table header */}
        <div className="hidden sm:grid sm:grid-cols-[1fr_auto_auto_auto_40px] gap-4 px-5 py-3 border-b border-white/6 text-[11px] font-semibold tracking-widest uppercase text-[#444444]">
          <span>Email / Label</span>
          <span>Department</span>
          <span>Key Prefix</span>
          <span>Created</span>
          <span />
        </div>

        <div className="divide-y divide-white/4">
          {keys.map(k => (
            <div
              key={k.key_id}
              className="flex flex-col sm:grid sm:grid-cols-[1fr_auto_auto_auto_40px] gap-2 sm:gap-4 px-5 py-4 items-start sm:items-center hover:bg-white/[0.02] transition-colors"
              data-testid={`key-${k.key_id}`}
            >
              {/* Email + label */}
              <div className="flex items-center gap-2.5 min-w-0 w-full sm:w-auto">
                <div className="w-7 h-7 rounded-lg bg-[#002FA7]/10 border border-[#002FA7]/15 flex items-center justify-center shrink-0">
                  <Key size={12} className="text-[#4477FF]" />
                </div>
                <div className="min-w-0">
                  <div className="text-[13px] text-white font-medium truncate">{k.email}</div>
                  {k.label && <div className="text-[10px] text-[#555555] font-mono">{k.label}</div>}
                </div>
              </div>

              {/* Mobile labels */}
              <div className="flex flex-wrap items-center gap-3 sm:contents">
                <span className="sm:hidden text-[10px] text-[#555555] uppercase tracking-wider font-mono">Dept:</span>
                <span className="text-[12px] text-[#A0A0A0]">{k.department}</span>
                <span className="sm:hidden text-[10px] text-[#555555] uppercase tracking-wider font-mono">Key:</span>
                <span className="text-[11px] text-[#555555] font-mono">{k.prefix}…</span>
                <span className="sm:hidden text-[10px] text-[#555555] uppercase tracking-wider font-mono">Created:</span>
                <span className="text-[11px] text-[#555555] font-mono">{k.created_at?.split('T')[0]}</span>
              </div>

              <button
                onClick={() => deleteApiKey(k.key_id).then(load)}
                className="p-2 rounded-lg text-[#444444] hover:text-[#FF3333] hover:bg-[#FF3333]/8 transition-all self-start sm:self-auto"
                data-testid={`delete-key-${k.key_id}`}
              >
                <Trash2 size={14} />
              </button>
            </div>
          ))}
          {keys.length === 0 && (
            <div className="py-12 text-center">
              <Key size={22} className="text-[#333333] mx-auto mb-3" />
              <p className="text-sm text-[#555555]">No API keys issued yet</p>
              <button onClick={() => setShowAdd(true)} className="text-sm text-[#002FA7] hover:text-[#4477FF] font-medium mt-1 transition-colors">
                Issue your first key
              </button>
            </div>
          )}
        </div>
      </div>

      {/* Usage hint */}
      <div className="mt-4 bg-[#111111] border border-white/8 rounded-xl px-5 py-4">
        <p className="text-[11px] text-[#444444] font-mono leading-relaxed">
          <span className="text-[#666666]">ANTHROPIC_BASE_URL=</span>https://your-relay-url &nbsp;
          <span className="text-[#666666]">ANTHROPIC_API_KEY=</span>&lt;key&gt; &nbsp;
          <span className="text-[#555555]">— then run claude or any compatible tool</span>
        </p>
      </div>
    </div>
  );
}
