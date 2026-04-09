import React, { useState, useEffect } from 'react';
import { listProviders, createProvider, deleteProvider, testProvider, updateProvider } from '../api';
import { Layers, Plus, Trash2, Zap, CheckCircle, XCircle, AlertCircle, Server, Globe, Loader2, Star } from 'lucide-react';

const PROVIDER_TYPES = [
  { id: 'ollama', label: 'Ollama', desc: 'Local LLM via Ollama API' },
  { id: 'openai-compatible', label: 'OpenAI Compatible', desc: 'Any OpenAI-compat API (HuggingFace, OpenRouter, etc.)' },
  { id: 'huggingface', label: 'HuggingFace', desc: 'HuggingFace Inference API' },
];

export default function ProvidersPage() {
  const [providers, setProviders] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({ provider_id: '', name: '', type: 'openai-compatible', base_url: '', api_key: '', default_model: '', is_default: false });
  const [testing, setTesting] = useState(null);
  const [testResult, setTestResult] = useState({});

  useEffect(() => { load(); }, []);
  const load = () => listProviders().then(r => setProviders(r.data.providers || [])).catch(() => {});

  const handleCreate = async () => {
    if (!form.provider_id || !form.name || !form.base_url) return;
    try {
      await createProvider(form);
      setShowAdd(false);
      setForm({ provider_id: '', name: '', type: 'openai-compatible', base_url: '', api_key: '', default_model: '', is_default: false });
      load();
    } catch (err) { alert(err?.response?.data?.detail || 'Failed'); }
  };

  const handleTest = async (id) => {
    setTesting(id);
    try {
      const { data } = await testProvider(id);
      setTestResult(prev => ({ ...prev, [id]: data }));
    } catch { setTestResult(prev => ({ ...prev, [id]: { ok: false, error: 'Connection failed' } })); }
    finally { setTesting(null); }
  };

  const handleSetDefault = async (id) => {
    await updateProvider(id, { is_default: true });
    load();
  };

  const statusIcon = (s) => s === 'online' ? <CheckCircle size={12} className="text-green-500" /> :
    s === 'error' ? <XCircle size={12} className="text-[#FF3333]" /> : <AlertCircle size={12} className="text-[#F59E0B]" />;

  return (
    <div className="p-5 lg:p-7 max-w-5xl" data-testid="providers-page">
      <div className="flex items-center justify-between mb-6 animate-fade-in">
        <div>
          <h1 className="text-2xl font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>Providers</h1>
          <p className="text-xs text-[#737373] mt-0.5">Configure LLM providers — local Ollama, HuggingFace, OpenRouter, or any OpenAI-compat API</p>
        </div>
        <button onClick={() => setShowAdd(!showAdd)} className="flex items-center gap-1.5 bg-[#002FA7] hover:bg-[#002585] text-white px-4 py-2 text-[10px] tracking-wider uppercase font-mono" data-testid="add-provider-button">
          <Plus size={12} /> ADD PROVIDER
        </button>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="border border-[#002FA7]/30 bg-[#141414] p-5 mb-5 animate-fade-in space-y-3" data-testid="add-provider-form">
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[9px] tracking-[0.15em] uppercase text-[#737373] mb-1 font-mono">Provider ID</label>
              <input value={form.provider_id} onChange={e => setForm({ ...form, provider_id: e.target.value })} placeholder="my-ollama-cloud" className="w-full bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]" data-testid="provider-id-input" />
            </div>
            <div>
              <label className="block text-[9px] tracking-[0.15em] uppercase text-[#737373] mb-1 font-mono">Display Name</label>
              <input value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="My Cloud Ollama" className="w-full bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]" data-testid="provider-name-input" />
            </div>
          </div>
          <div>
            <label className="block text-[9px] tracking-[0.15em] uppercase text-[#737373] mb-1 font-mono">Type</label>
            <div className="flex gap-2">
              {PROVIDER_TYPES.map(t => (
                <button key={t.id} onClick={() => setForm({ ...form, type: t.id })}
                  className={`flex-1 border px-3 py-2 text-[10px] font-mono transition-all ${form.type === t.id ? 'border-[#002FA7] bg-[#002FA7]/10 text-white' : 'border-white/10 text-[#737373] hover:border-white/20'}`}
                  data-testid={`provider-type-${t.id}`}>
                  {t.label}
                </button>
              ))}
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[9px] tracking-[0.15em] uppercase text-[#737373] mb-1 font-mono">Base URL</label>
              <input value={form.base_url} onChange={e => setForm({ ...form, base_url: e.target.value })}
                placeholder={form.type === 'ollama' ? 'http://localhost:11434' : form.type === 'huggingface' ? 'https://api-inference.huggingface.co/v1' : 'https://openrouter.ai/api/v1'}
                className="w-full bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]" data-testid="provider-url-input" />
            </div>
            <div>
              <label className="block text-[9px] tracking-[0.15em] uppercase text-[#737373] mb-1 font-mono">API Key (optional)</label>
              <input value={form.api_key} onChange={e => setForm({ ...form, api_key: e.target.value })} type="password" placeholder="sk-..." className="w-full bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]" data-testid="provider-key-input" />
            </div>
          </div>
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="block text-[9px] tracking-[0.15em] uppercase text-[#737373] mb-1 font-mono">Default Model</label>
              <input value={form.default_model} onChange={e => setForm({ ...form, default_model: e.target.value })} placeholder="llama3.2" className="w-full bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]" data-testid="provider-model-input" />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" checked={form.is_default} onChange={e => setForm({ ...form, is_default: e.target.checked })} className="accent-[#002FA7]" />
                <span className="text-xs text-[#A0A0A0]">Set as default provider</span>
              </label>
            </div>
          </div>
          <button onClick={handleCreate} className="bg-[#002FA7] hover:bg-[#002585] text-white px-5 py-2 text-[10px] tracking-wider uppercase font-mono" data-testid="save-provider-button">CREATE PROVIDER</button>
        </div>
      )}

      {/* Provider list */}
      <div className="space-y-3">
        {providers.map(p => (
          <div key={p.provider_id} className="border border-white/10 bg-[#141414] animate-fade-in" data-testid={`provider-${p.provider_id}`}>
            <div className="flex items-center gap-3 px-5 py-3">
              <div className={`w-8 h-8 flex items-center justify-center ${p.is_default ? 'bg-[#002FA7]' : 'bg-white/5'}`}>
                {p.type === 'ollama' ? <Server size={15} /> : <Globe size={15} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-sm text-white font-bold">{p.name}</span>
                  {p.is_default && <span className="text-[8px] bg-[#002FA7] text-white px-1.5 py-0.5 tracking-wider uppercase font-mono">DEFAULT</span>}
                </div>
                <div className="text-[10px] text-[#737373] font-mono mt-0.5 flex items-center gap-3">
                  <span>{p.type}</span>
                  <span>{p.base_url}</span>
                  {p.default_model && <span>model: {p.default_model}</span>}
                  {p.api_key_masked && <span>key: {p.api_key_masked}</span>}
                </div>
              </div>
              <div className="flex items-center gap-2">
                {statusIcon(p.status)}
                {!p.is_default && (
                  <button onClick={() => handleSetDefault(p.provider_id)} className="p-1.5 text-[#737373] hover:text-[#F59E0B] transition-colors" title="Set as default">
                    <Star size={13} />
                  </button>
                )}
                <button onClick={() => handleTest(p.provider_id)} disabled={testing === p.provider_id}
                  className="flex items-center gap-1 border border-white/10 hover:border-[#002FA7] text-[#A0A0A0] hover:text-white px-2.5 py-1.5 text-[9px] tracking-wider uppercase font-mono transition-all"
                  data-testid={`test-provider-${p.provider_id}`}>
                  {testing === p.provider_id ? <Loader2 size={11} className="animate-spin" /> : <Zap size={11} />} TEST
                </button>
                <button onClick={() => { deleteProvider(p.provider_id).then(load); }}
                  className="p-1.5 text-[#737373] hover:text-[#FF3333] transition-colors" data-testid={`delete-provider-${p.provider_id}`}>
                  <Trash2 size={13} />
                </button>
              </div>
            </div>
            {testResult[p.provider_id] && (
              <div className={`border-t border-white/5 px-5 py-2 text-[10px] font-mono ${testResult[p.provider_id].ok ? 'text-green-500' : 'text-[#FF3333]'}`}>
                {testResult[p.provider_id].ok ? 'Connected successfully' : `Error: ${testResult[p.provider_id].error}`}
                {testResult[p.provider_id].models && <span className="text-[#737373] ml-2">({testResult[p.provider_id].models.length} models)</span>}
              </div>
            )}
          </div>
        ))}
        {providers.length === 0 && <div className="border border-white/10 bg-[#141414] p-8 text-center text-xs text-[#737373]">No providers configured</div>}
      </div>
    </div>
  );
}
