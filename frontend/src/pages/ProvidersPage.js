import React, { useState, useEffect } from 'react';
import { listProviders, createProvider, deleteProvider, testProvider, updateProvider } from '../api';
import { Layers, Plus, Trash2, Zap, CheckCircle, XCircle, AlertCircle, Server, Globe, Loader2, Star, X } from 'lucide-react';

const PROVIDER_TYPES = [
  { id: 'ollama', label: 'Ollama', desc: 'Local LLM via Ollama API' },
  { id: 'openai-compatible', label: 'OpenAI Compatible', desc: 'HuggingFace, OpenRouter, etc.' },
  { id: 'huggingface', label: 'HuggingFace', desc: 'HF serverless inference' },
];

function FormField({ label, children }) {
  return (
    <div>
      <label className="block text-[11px] font-semibold tracking-widest uppercase text-[#555555] mb-1.5">{label}</label>
      {children}
    </div>
  );
}

function TextInput({ value, onChange, placeholder, type = 'text', testId }) {
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      data-testid={testId}
      className="w-full bg-black/30 border border-white/8 rounded-md px-3 py-2.5 text-sm text-white placeholder-[#444] outline-none focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7]/25 transition-all min-h-[40px]"
    />
  );
}

function StatusIcon({ status }) {
  if (status === 'online') return <CheckCircle size={13} className="text-emerald-500" />;
  if (status === 'error')  return <XCircle    size={13} className="text-[#FF3333]" />;
  return <AlertCircle size={13} className="text-[#F59E0B]" />;
}

export default function ProvidersPage() {
  const [providers, setProviders] = useState([]);
  const [showAdd, setShowAdd] = useState(false);
  const [form, setForm] = useState({
    provider_id: '', name: '', type: 'openai-compatible',
    base_url: '', api_key: '', default_model: '', is_default: false,
  });
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
    } catch (err) { alert(err?.response?.data?.detail || 'Failed to create provider'); }
  };

  const handleTest = async (id) => {
    setTesting(id);
    try {
      const { data } = await testProvider(id);
      setTestResult(prev => ({ ...prev, [id]: data }));
    } catch {
      setTestResult(prev => ({ ...prev, [id]: { ok: false, error: 'Connection failed' } }));
    } finally { setTesting(null); }
  };

  const handleSetDefault = async (id) => {
    await updateProvider(id, { is_default: true });
    load();
  };

  const urlPlaceholder = form.type === 'ollama'
    ? 'http://localhost:11434'
    : form.type === 'huggingface'
    ? 'https://router.huggingface.co'
    : 'https://openrouter.ai/api/v1';

  return (
    <div className="p-5 sm:p-6 lg:p-8 max-w-5xl mx-auto" data-testid="providers-page">

      {/* Header */}
      <div className="flex flex-wrap items-start justify-between gap-4 mb-7 animate-fade-in">
        <div>
          <h1 className="text-3xl font-bold tracking-[-0.03em] text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Providers</h1>
          <p className="text-sm text-[#555555] mt-1">Configure LLM providers — Ollama, HuggingFace, OpenRouter, or any OpenAI-compatible API</p>
        </div>
        <button
          onClick={() => setShowAdd(s => !s)}
          className="inline-flex items-center gap-2 bg-[#002FA7] hover:bg-[#0038CC] text-white px-4 py-2.5 rounded-lg text-sm font-semibold transition-all shadow-[0_4px_12px_rgba(0,47,167,0.3)] min-h-[42px]"
          data-testid="add-provider-button"
        >
          <Plus size={14} />
          Add Provider
        </button>
      </div>

      {/* Add form */}
      {showAdd && (
        <div className="bg-[#111111] border border-[#002FA7]/20 rounded-xl p-5 sm:p-6 mb-6 animate-fade-in" data-testid="add-provider-form">
          <div className="flex items-center justify-between mb-5">
            <h2 className="text-base font-semibold text-white">New Provider</h2>
            <button onClick={() => setShowAdd(false)} className="p-1.5 text-[#555555] hover:text-white rounded-lg hover:bg-white/5 transition-colors">
              <X size={15} />
            </button>
          </div>

          <div className="space-y-4">
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField label="Provider ID">
                <TextInput value={form.provider_id} onChange={e => setForm({ ...form, provider_id: e.target.value })} placeholder="my-ollama" testId="provider-id-input" />
              </FormField>
              <FormField label="Display Name">
                <TextInput value={form.name} onChange={e => setForm({ ...form, name: e.target.value })} placeholder="My Ollama" testId="provider-name-input" />
              </FormField>
            </div>

            <FormField label="Type">
              <div className="grid grid-cols-1 xs:grid-cols-3 gap-2">
                {PROVIDER_TYPES.map(t => (
                  <button
                    key={t.id}
                    onClick={() => setForm({ ...form, type: t.id })}
                    data-testid={`provider-type-${t.id}`}
                    className={`flex flex-col items-start px-3.5 py-2.5 rounded-lg border text-left transition-all ${
                      form.type === t.id
                        ? 'border-[#002FA7] bg-[#002FA7]/10 text-white'
                        : 'border-white/8 text-[#666666] hover:border-white/16 hover:bg-white/[0.025]'
                    }`}
                  >
                    <span className="text-[12px] font-semibold">{t.label}</span>
                    <span className="text-[10px] opacity-60 mt-0.5">{t.desc}</span>
                  </button>
                ))}
              </div>
            </FormField>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField label="Base URL">
                <TextInput value={form.base_url} onChange={e => setForm({ ...form, base_url: e.target.value })} placeholder={urlPlaceholder} testId="provider-url-input" />
              </FormField>
              <FormField label="API Key (optional)">
                <TextInput value={form.api_key} onChange={e => setForm({ ...form, api_key: e.target.value })} type="password" placeholder="sk-..." testId="provider-key-input" />
              </FormField>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <FormField label="Default Model">
                <TextInput value={form.default_model} onChange={e => setForm({ ...form, default_model: e.target.value })} placeholder="llama3.2" testId="provider-model-input" />
              </FormField>
              <div className="flex items-end pb-1">
                <label className="flex items-center gap-2.5 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={form.is_default}
                    onChange={e => setForm({ ...form, is_default: e.target.checked })}
                    className="w-4 h-4 accent-[#002FA7]"
                  />
                  <span className="text-sm text-[#A0A0A0]">Set as default provider</span>
                </label>
              </div>
            </div>

            <div className="flex gap-2 pt-1">
              <button onClick={handleCreate} className="bg-[#002FA7] hover:bg-[#0038CC] text-white px-5 py-2.5 rounded-lg text-sm font-semibold transition-all min-h-[40px]" data-testid="save-provider-button">
                Create Provider
              </button>
              <button onClick={() => setShowAdd(false)} className="px-4 py-2.5 rounded-lg border border-white/8 text-sm text-[#666666] hover:text-white hover:bg-white/5 transition-all min-h-[40px]">
                Cancel
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Provider list */}
      <div className="space-y-3">
        {providers.map(p => (
          <div key={p.provider_id} className="bg-[#111111] border border-white/8 rounded-xl overflow-hidden animate-fade-in hover:border-white/14 transition-colors" data-testid={`provider-${p.provider_id}`}>
            <div className="flex items-center gap-3 px-5 py-4">
              <div className={`w-9 h-9 rounded-lg flex items-center justify-center shrink-0 ${p.is_default ? 'bg-[#002FA7]' : 'bg-white/5 border border-white/8'}`}>
                {p.type === 'ollama' ? <Server size={16} /> : <Globe size={16} />}
              </div>
              <div className="flex-1 min-w-0">
                <div className="flex flex-wrap items-center gap-2">
                  <span className="text-sm font-semibold text-white">{p.name}</span>
                  {p.is_default && (
                    <span className="text-[10px] bg-[#002FA7]/15 text-[#4477FF] border border-[#002FA7]/20 px-2 py-0.5 rounded-full font-mono tracking-wide">Default</span>
                  )}
                  <StatusIcon status={p.status} />
                </div>
                <div className="text-[11px] text-[#555555] font-mono mt-1 flex flex-wrap items-center gap-x-3 gap-y-0.5">
                  <span>{p.type}</span>
                  <span className="truncate max-w-[200px]">{p.base_url}</span>
                  {p.default_model && <span>model: {p.default_model}</span>}
                  {p.api_key_masked && <span>key: {p.api_key_masked}</span>}
                </div>
              </div>
              <div className="flex items-center gap-1.5 shrink-0">
                {!p.is_default && (
                  <button
                    onClick={() => handleSetDefault(p.provider_id)}
                    className="p-2 rounded-lg text-[#555555] hover:text-[#F59E0B] hover:bg-[#F59E0B]/8 transition-all"
                    title="Set as default"
                  >
                    <Star size={14} />
                  </button>
                )}
                <button
                  onClick={() => handleTest(p.provider_id)}
                  disabled={testing === p.provider_id}
                  className="flex items-center gap-1.5 border border-white/8 hover:border-[#002FA7]/40 hover:bg-[#002FA7]/5 text-[#888888] hover:text-white px-3 py-1.5 rounded-lg text-[12px] font-medium transition-all disabled:opacity-50 min-h-[34px]"
                  data-testid={`test-provider-${p.provider_id}`}
                >
                  {testing === p.provider_id ? <Loader2 size={12} className="animate-spin" /> : <Zap size={12} />}
                  Test
                </button>
                <button
                  onClick={() => deleteProvider(p.provider_id).then(load)}
                  className="p-2 rounded-lg text-[#555555] hover:text-[#FF3333] hover:bg-[#FF3333]/8 transition-all"
                  data-testid={`delete-provider-${p.provider_id}`}
                >
                  <Trash2 size={14} />
                </button>
              </div>
            </div>
            {testResult[p.provider_id] && (
              <div className={`border-t border-white/6 px-5 py-2.5 text-[12px] font-mono flex items-center gap-2 ${testResult[p.provider_id].ok ? 'text-emerald-400 bg-emerald-500/5' : 'text-[#FF4444] bg-[#FF3333]/5'}`}>
                {testResult[p.provider_id].ok
                  ? <><CheckCircle size={12} /> Connected successfully</>
                  : <><XCircle size={12} /> Error: {testResult[p.provider_id].error}</>
                }
                {testResult[p.provider_id].models && (
                  <span className="text-[#555555] ml-1">({testResult[p.provider_id].models.length} models)</span>
                )}
              </div>
            )}
          </div>
        ))}
        {providers.length === 0 && (
          <div className="bg-[#111111] border border-white/8 rounded-xl p-10 text-center">
            <Layers size={24} className="text-[#333333] mx-auto mb-3" />
            <p className="text-sm text-[#555555] mb-3">No providers configured yet</p>
            <button onClick={() => setShowAdd(true)} className="text-sm text-[#002FA7] hover:text-[#4477FF] font-medium transition-colors">
              Add your first provider
            </button>
          </div>
        )}
      </div>
    </div>
  );
}
