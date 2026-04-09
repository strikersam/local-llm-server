import React, { useState, useEffect } from 'react';
import { listApiKeys, createApiKey, deleteApiKey } from '../api';
import { Key, Plus, Trash2, Copy, CheckCircle } from 'lucide-react';

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
    } catch (err) { alert(err?.response?.data?.detail || 'Failed'); }
  };

  const copyKey = () => {
    navigator.clipboard.writeText(newKey);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="p-5 lg:p-7 max-w-5xl" data-testid="api-keys-page">
      <div className="flex items-center justify-between mb-6 animate-fade-in">
        <div>
          <h1 className="text-2xl font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>API Keys</h1>
          <p className="text-xs text-[#737373] mt-0.5">Manage API keys for authenticating with the proxy. Use with Cursor, Claude Code, Aider, etc.</p>
        </div>
        <button onClick={() => setShowAdd(!showAdd)} className="flex items-center gap-1.5 bg-[#002FA7] hover:bg-[#002585] text-white px-4 py-2 text-[10px] tracking-wider uppercase font-mono" data-testid="create-key-button">
          <Plus size={12} /> ISSUE KEY
        </button>
      </div>

      {/* New key display */}
      {newKey && (
        <div className="border border-green-500/30 bg-green-500/5 p-4 mb-5 animate-fade-in" data-testid="new-key-display">
          <div className="text-[10px] text-green-500 font-mono font-bold mb-2">NEW API KEY — COPY NOW (shown once)</div>
          <div className="flex items-center gap-2">
            <code className="flex-1 bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono break-all">{newKey}</code>
            <button onClick={copyKey} className="flex items-center gap-1 border border-white/10 hover:border-green-500 text-[#A0A0A0] hover:text-green-500 px-3 py-2 text-[10px] font-mono transition-all" data-testid="copy-key-button">
              {copied ? <CheckCircle size={12} /> : <Copy size={12} />} {copied ? 'COPIED' : 'COPY'}
            </button>
          </div>
          <button onClick={() => setNewKey(null)} className="text-[9px] text-[#737373] hover:text-white mt-2 font-mono">DISMISS</button>
        </div>
      )}

      {/* Add form */}
      {showAdd && (
        <div className="border border-[#002FA7]/30 bg-[#141414] p-5 mb-5 animate-fade-in space-y-3" data-testid="add-key-form">
          <div className="grid grid-cols-3 gap-3">
            <div>
              <label className="block text-[9px] tracking-[0.15em] uppercase text-[#737373] mb-1 font-mono">Email</label>
              <input value={form.email} onChange={e => setForm({ ...form, email: e.target.value })} placeholder="user@company.com"
                className="w-full bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]" data-testid="key-email-input" />
            </div>
            <div>
              <label className="block text-[9px] tracking-[0.15em] uppercase text-[#737373] mb-1 font-mono">Department</label>
              <input value={form.department} onChange={e => setForm({ ...form, department: e.target.value })}
                className="w-full bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]" data-testid="key-dept-input" />
            </div>
            <div>
              <label className="block text-[9px] tracking-[0.15em] uppercase text-[#737373] mb-1 font-mono">Label (optional)</label>
              <input value={form.label} onChange={e => setForm({ ...form, label: e.target.value })} placeholder="Cursor, Aider..."
                className="w-full bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]" data-testid="key-label-input" />
            </div>
          </div>
          <button onClick={handleCreate} className="bg-[#002FA7] hover:bg-[#002585] text-white px-5 py-2 text-[10px] tracking-wider uppercase font-mono" data-testid="issue-key-button">ISSUE API KEY</button>
        </div>
      )}

      {/* Keys table */}
      <div className="border border-white/10 bg-[#141414]">
        <div className="grid grid-cols-[1fr_1fr_120px_150px_40px] gap-3 px-4 py-2.5 border-b border-white/10 text-[9px] tracking-[0.15em] uppercase text-[#737373] font-mono font-bold">
          <span>EMAIL</span><span>DEPARTMENT</span><span>KEY PREFIX</span><span>CREATED</span><span></span>
        </div>
        <div className="divide-y divide-white/5">
          {keys.map(k => (
            <div key={k.key_id} className="grid grid-cols-[1fr_1fr_120px_150px_40px] gap-3 px-4 py-2.5 items-center hover:bg-white/[0.02]" data-testid={`key-${k.key_id}`}>
              <div className="flex items-center gap-2 min-w-0">
                <Key size={12} className="text-[#002FA7] shrink-0" />
                <span className="text-[11px] text-white truncate">{k.email}</span>
              </div>
              <span className="text-[11px] text-[#A0A0A0] truncate">{k.department}</span>
              <span className="text-[10px] text-[#737373] font-mono">{k.prefix}</span>
              <span className="text-[10px] text-[#737373] font-mono">{k.created_at?.split('T')[0]}</span>
              <button onClick={() => deleteApiKey(k.key_id).then(load)} className="p-1 text-[#737373] hover:text-[#FF3333] transition-colors" data-testid={`delete-key-${k.key_id}`}>
                <Trash2 size={12} />
              </button>
            </div>
          ))}
          {keys.length === 0 && <div className="py-8 text-center text-[11px] text-[#737373]">No API keys issued yet</div>}
        </div>
      </div>
    </div>
  );
}
