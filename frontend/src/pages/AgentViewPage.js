/**
 * AgentViewPage — native Agent UI embedded in the dashboard.
 *
 * Makes direct fetch() calls to the configurable backend URL
 * (default: http://localhost:8000).  Because browsers treat
 * localhost as a "potentially trustworthy" origin, fetch from an
 * HTTPS page to http://localhost is allowed in Chrome/Firefox/Safari —
 * no tunnel or iframe required.
 */
import React, { useEffect, useMemo, useRef, useState } from 'react';
import {
  Bot, Send, Zap, Settings, Settings2, Plus, RefreshCw,
  ChevronDown, X, Loader2, FileText, Clock,
} from 'lucide-react';

// ── localStorage keys ─────────────────────────────────────────────────────────
const LS_BACKEND  = 'agv_backend_url';
const LS_API_KEY  = 'agv_api_key';
const LS_PROVIDER = 'agv_provider';
const LS_MODEL    = 'agv_model';
const LS_MODE     = 'agv_mode';      // 'auto' | 'manual'
const LS_SESSION  = 'agv_session';

const DEFAULT_BACKEND = 'http://localhost:8000';

// ── API helpers ───────────────────────────────────────────────────────────────
function makeHeaders(apiKey, backendUrl = '') {
  return {
    'Content-Type': 'application/json',
    ...(apiKey ? { Authorization: `Bearer ${apiKey}` } : {}),
    // Bypass ngrok's browser-warning interstitial when accessed from code
    ...(backendUrl.includes('ngrok') ? { 'ngrok-skip-browser-warning': 'true' } : {}),
  };
}

async function apiFetch(backendUrl, path, apiKey, opts = {}) {
  const base = backendUrl.replace(/\/+$/, '');
  const res  = await fetch(`${base}${path}`, {
    headers: makeHeaders(apiKey, backendUrl),
    ...opts,
  });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try { const d = await res.json(); detail = d.detail || detail; } catch {}
    throw new Error(detail);
  }
  return res.json();
}

async function getProviders(backendUrl, apiKey) {
  const d = await apiFetch(backendUrl, '/ui/api/providers', apiKey);
  return d.providers ?? [];
}

async function getModels(backendUrl, apiKey, providerId) {
  const d = await apiFetch(backendUrl, `/ui/api/providers/${encodeURIComponent(providerId)}/models`, apiKey);
  return d.models ?? [];
}

async function createSession(backendUrl, apiKey, providerId) {
  return apiFetch(backendUrl, '/agent/sessions', apiKey, {
    method: 'POST',
    body: JSON.stringify({
      title: `Session (${new Date().toISOString().slice(0, 16).replace('T', ' ')})`,
      provider_id: providerId || 'prov_local',
      workspace_id: 'ws_current',
    }),
  });
}

async function runAgentStep(backendUrl, apiKey, sessionId, instruction, model) {
  return apiFetch(backendUrl, `/agent/sessions/${encodeURIComponent(sessionId)}/run`, apiKey, {
    method: 'POST',
    body: JSON.stringify({
      instruction,
      max_steps: 8,
      ...(model ? { model } : {}),
    }),
  });
}

// ── Small helpers ─────────────────────────────────────────────────────────────
function short(s = '', max = 24) {
  return s.length <= max ? s : s.slice(0, max - 1) + '…';
}
function modelType(name = '') {
  if (/coder|code/i.test(name))                    return 'coder';
  if (/r1|reasoner|thinking|deepseek/i.test(name)) return 'reasoning';
  return 'general';
}
function typeBadgeCls(name) {
  const t = modelType(name);
  if (t === 'coder')     return 'border-blue-500/40 bg-blue-500/10 text-blue-300';
  if (t === 'reasoning') return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300';
  return 'border-white/20 bg-white/5 text-[#737373]';
}

// ── ModelPickerModal ──────────────────────────────────────────────────────────
function ModelPickerModal({ backendUrl, apiKey, providers, initProvider, initModel, onConfirm, onClose }) {
  const [tab,     setTab]     = useState(initProvider || providers[0]?.provider_id || '');
  const [models,  setModels]  = useState([]);
  const [picked,  setPicked]  = useState(initModel || '');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!tab) return;
    setLoading(true);
    getModels(backendUrl, apiKey, tab)
      .then(ms => { setModels(ms); if (!picked || !ms.includes(picked)) setPicked(ms[0] || ''); })
      .catch(() => setModels([]))
      .finally(() => setLoading(false));
  }, [tab]); // eslint-disable-line

  return (
    <div className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-end md:items-center justify-center p-0 md:p-6"
         onClick={onClose}>
      <div className="w-full md:max-w-md bg-[#111] border border-white/10 rounded-t-2xl md:rounded-2xl flex flex-col overflow-hidden shadow-2xl max-h-[88vh]"
           onClick={e => e.stopPropagation()}>
        {/* header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10 shrink-0">
          <span className="text-sm font-bold font-mono">Select Provider &amp; Model</span>
          <button onClick={onClose} className="text-[#555] hover:text-white p-1 transition-colors"><X size={15} /></button>
        </div>
        {/* provider tabs */}
        <div className="flex gap-2 px-5 py-3 border-b border-white/10 overflow-x-auto shrink-0">
          {providers.map(p => (
            <button key={p.provider_id} onClick={() => setTab(p.provider_id)}
              className={`px-3 py-1.5 rounded-full text-[10px] font-mono uppercase tracking-wider whitespace-nowrap border transition-colors
                ${tab === p.provider_id ? 'border-[#002FA7] bg-[#002FA7]/20 text-white' : 'border-white/10 text-[#737373] hover:border-white/20'}`}>
              {p.name}
            </button>
          ))}
        </div>
        {/* models */}
        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2 min-h-0">
          {loading ? (
            <div className="flex justify-center items-center py-10 gap-2">
              <Loader2 size={16} className="animate-spin text-[#555]" />
              <span className="text-xs font-mono text-[#555]">Loading…</span>
            </div>
          ) : models.length === 0 ? (
            <div className="py-10 text-center text-xs text-[#555] font-mono">No models found.</div>
          ) : models.map(m => (
            <button key={m} onClick={() => setPicked(m)}
              className={`w-full flex items-center justify-between px-4 py-3 border text-left transition-colors
                ${picked === m ? 'border-[#002FA7] bg-[#002FA7]/10' : 'border-white/10 hover:border-white/20 hover:bg-white/[0.02]'}`}>
              <span className="text-xs font-mono text-white truncate pr-3">{m}</span>
              <span className={`text-[9px] font-mono uppercase tracking-wider px-2 py-0.5 border rounded-sm shrink-0 ${typeBadgeCls(m)}`}>
                {modelType(m)}
              </span>
            </button>
          ))}
        </div>
        {/* footer */}
        <div className="flex gap-3 px-5 py-4 border-t border-white/10 shrink-0">
          <button onClick={onClose} className="flex-1 py-2.5 border border-white/10 text-xs font-mono uppercase tracking-wider text-[#737373] hover:text-white transition-colors">Cancel</button>
          <button disabled={!picked} onClick={() => onConfirm(tab, picked)}
            className="flex-1 py-2.5 bg-[#002FA7] hover:bg-[#002585] text-white text-xs font-mono uppercase tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
            Use {picked ? short(picked, 18) : 'model'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ── ConnectionBar ─────────────────────────────────────────────────────────────
function ConnectionBar({ backendUrl, apiKey, onBackendChange, onKeyChange, status }) {
  const [editBackend, setEditBackend] = useState(backendUrl);
  const [editKey,     setEditKey]     = useState(apiKey);
  const [open,        setOpen]        = useState(!apiKey);

  function apply() {
    onBackendChange(editBackend.trim().replace(/\/+$/, '') || DEFAULT_BACKEND);
    onKeyChange(editKey.trim());
    setOpen(false);
  }

  const dot = status === 'ok'      ? 'bg-green-500'
            : status === 'error'   ? 'bg-red-500'
            : 'bg-yellow-500 animate-pulse';

  return (
    <div className="border-b border-white/10 bg-[#0D0D0D] shrink-0">
      {/* collapsed bar */}
      <div className="flex items-center gap-3 px-4 h-10">
        <div className={`w-2 h-2 rounded-full shrink-0 ${dot}`} title={status} />
        <span className="text-[10px] font-mono text-[#555] truncate flex-1">
          {backendUrl} {apiKey ? '· key set' : '· no key'}
        </span>
        <button onClick={() => setOpen(o => !o)}
          className="flex items-center gap-1 text-[10px] font-mono text-[#555] hover:text-[#A0A0A0] transition-colors px-2 py-1 border border-white/10 hover:border-white/20">
          <Settings2 size={10} /> Configure
        </button>
      </div>
      {/* expanded form */}
      {open && (
        <div className="px-4 pb-3 space-y-2 border-t border-white/10 pt-3">
          <div className="flex gap-2 items-center">
            <span className="text-[10px] font-mono text-[#555] w-20 shrink-0">Backend</span>
            <input value={editBackend} onChange={e => setEditBackend(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && apply()}
              placeholder="http://localhost:8000"
              className="flex-1 bg-[#1A1A1A] border border-white/10 focus:border-[#002FA7] px-3 py-1.5 text-[11px] font-mono text-white outline-none" />
          </div>
          <div className="flex gap-2 items-center">
            <span className="text-[10px] font-mono text-[#555] w-20 shrink-0">API key</span>
            <input type="password" value={editKey} onChange={e => setEditKey(e.target.value)}
              onKeyDown={e => e.key === 'Enter' && apply()}
              placeholder="sk-qwen-… (from /admin/keys)"
              className="flex-1 bg-[#1A1A1A] border border-white/10 focus:border-[#002FA7] px-3 py-1.5 text-[11px] font-mono text-white outline-none" />
          </div>
          <div className="flex justify-end gap-2">
            <button onClick={() => setOpen(false)} className="px-3 py-1.5 text-[10px] font-mono text-[#555] hover:text-white border border-white/10 hover:border-white/20 transition-colors">Cancel</button>
            <button onClick={apply} className="px-3 py-1.5 bg-[#002FA7] hover:bg-[#002585] text-[10px] font-mono text-white uppercase tracking-wider transition-colors">Connect</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function AgentViewPage() {
  const [backendUrl, setBackendUrl] = useState(() => localStorage.getItem(LS_BACKEND)  || DEFAULT_BACKEND);
  const [apiKey,     setApiKey]     = useState(() => localStorage.getItem(LS_API_KEY)  || '');
  const [providerId, setProviderId] = useState(() => localStorage.getItem(LS_PROVIDER) || '');
  const [model,      setModel]      = useState(() => localStorage.getItem(LS_MODEL)    || '');
  const [mode,       setMode]       = useState(() => localStorage.getItem(LS_MODE)     || 'auto');

  const [providers,   setProviders]   = useState([]);
  const [connStatus,  setConnStatus]  = useState('idle');   // idle | ok | error
  const [session,     setSession]     = useState(null);
  const [busy,        setBusy]        = useState(false);
  const [err,         setErr]         = useState(null);
  const [instruction, setInstruction] = useState('');
  const [showPicker,  setShowPicker]  = useState(false);
  const [elapsed,     setElapsed]     = useState(0);

  const chatEndRef   = useRef(null);
  const inputRef     = useRef(null);
  const timerRef     = useRef(null);

  // ── Persist ─────────────────────────────────────────────────────────────────
  useEffect(() => localStorage.setItem(LS_BACKEND,  backendUrl), [backendUrl]);
  useEffect(() => localStorage.setItem(LS_API_KEY,  apiKey),     [apiKey]);
  useEffect(() => localStorage.setItem(LS_PROVIDER, providerId), [providerId]);
  useEffect(() => localStorage.setItem(LS_MODEL,    model),      [model]);
  useEffect(() => localStorage.setItem(LS_MODE,     mode),       [mode]);

  // ── Load providers on connect ────────────────────────────────────────────────
  useEffect(() => {
    if (!apiKey) { setConnStatus('idle'); return; }
    setConnStatus('checking');
    getProviders(backendUrl, apiKey)
      .then(ps => {
        setProviders(ps);
        setConnStatus('ok');
        if (!providerId && ps.length) setProviderId(ps[0].provider_id);
      })
      .catch(() => { setConnStatus('error'); setProviders([]); });
  }, [backendUrl, apiKey]); // eslint-disable-line

  // ── Auto-scroll ──────────────────────────────────────────────────────────────
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [session?.history?.length, busy]);

  // ── Restore session id ───────────────────────────────────────────────────────
  useEffect(() => {
    const sid = localStorage.getItem(LS_SESSION);
    if (sid) setSession({ session_id: sid, history: [], last_plan: null, last_result: null });
  }, []);

  const providerName = useMemo(
    () => providers.find(p => p.provider_id === providerId)?.name || providerId,
    [providers, providerId],
  );

  // ── Send ─────────────────────────────────────────────────────────────────────
  async function send() {
    if (!instruction.trim() || !apiKey) return;
    const text        = instruction.trim();
    const modelToSend = mode === 'auto' ? null : (model || null);
    setInstruction('');
    setBusy(true);
    setErr(null);
    setElapsed(0);
    timerRef.current = setInterval(() => setElapsed(p => p + 1), 1000);

    try {
      let s = session;
      if (!s?.session_id) {
        s = await createSession(backendUrl, apiKey, mode === 'manual' ? providerId : null);
        setSession(s);
        localStorage.setItem(LS_SESSION, s.session_id);
      }
      const out = await runAgentStep(backendUrl, apiKey, s.session_id, text, modelToSend);
      setSession(out.session);
    } catch (e) {
      setErr(e?.message || 'Agent run failed');
    } finally {
      clearInterval(timerRef.current);
      setBusy(false);
      setElapsed(0);
    }
  }

  function handleKey(e) {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') { e.preventDefault(); if (!busy) send(); }
  }

  function newSession() {
    setSession(null);
    localStorage.removeItem(LS_SESSION);
    setErr(null);
  }

  const history = session?.history ?? [];

  return (
    <div className="flex flex-col h-full bg-[#0A0A0A]">

      {/* Model picker modal */}
      {showPicker && (
        <ModelPickerModal
          backendUrl={backendUrl} apiKey={apiKey} providers={providers}
          initProvider={providerId} initModel={model}
          onClose={() => setShowPicker(false)}
          onConfirm={(pid, m) => { setProviderId(pid); setModel(m); setShowPicker(false); }}
        />
      )}

      {/* ── Connection bar ── */}
      <ConnectionBar
        backendUrl={backendUrl} apiKey={apiKey} status={connStatus}
        onBackendChange={u => { setBackendUrl(u); setSession(null); }}
        onKeyChange={k => { setApiKey(k); setSession(null); }}
      />

      {/* ── Chat header ── */}
      <div className="flex items-center gap-2 px-4 py-2.5 border-b border-white/10 bg-[#0D0D0D] shrink-0 flex-wrap">
        <Bot size={14} className="text-[#002FA7] shrink-0" />
        <span className="text-[11px] font-mono font-bold text-[#A0A0A0] tracking-wide uppercase">Agent</span>

        {/* Mode toggle */}
        <div className="flex border border-white/10 rounded overflow-hidden ml-1">
          <button onClick={() => setMode('auto')}
            className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-mono uppercase tracking-wider transition-colors border-r border-white/10
              ${mode === 'auto' ? 'bg-[#002FA7]/20 text-white' : 'text-[#555] hover:text-[#A0A0A0]'}`}>
            <Zap size={9} /> Auto
          </button>
          <button onClick={() => setMode('manual')}
            className={`flex items-center gap-1 px-2.5 py-1.5 text-[10px] font-mono uppercase tracking-wider transition-colors
              ${mode === 'manual' ? 'bg-[#002FA7]/20 text-white' : 'text-[#555] hover:text-[#A0A0A0]'}`}>
            <Settings size={9} /> Manual
          </button>
        </div>

        {/* Manual: model selector */}
        {mode === 'manual' && (
          <button onClick={() => setShowPicker(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 border border-white/10 hover:border-white/20 text-[10px] font-mono text-[#A0A0A0] hover:text-white transition-colors">
            <span className="truncate max-w-[160px]">
              {model ? `${short(providerName, 10)} · ${short(model, 14)}` : 'Select model'}
            </span>
            <ChevronDown size={9} />
          </button>
        )}

        {mode === 'auto' && (
          <span className="text-[9px] font-mono text-[#444]">router picks best model per message</span>
        )}

        <div className="flex-1" />

        {/* New session */}
        <button onClick={newSession}
          className="flex items-center gap-1.5 px-2.5 py-1.5 border border-white/10 hover:border-white/20 text-[10px] font-mono text-[#555] hover:text-[#A0A0A0] transition-colors">
          <Plus size={10} /> New
        </button>
      </div>

      {/* ── Error pill ── */}
      {err && (
        <div className="mx-4 mt-2 shrink-0 flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/20 text-[11px] font-mono text-red-400">
          <span className="flex-1">{err}</span>
          <button onClick={() => setErr(null)}><X size={11} /></button>
        </div>
      )}

      {/* ── Chat messages ── */}
      <div className="flex-1 overflow-y-auto px-4 py-4 space-y-3 min-h-0">

        {!apiKey && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3 px-4">
            <Bot size={36} className="text-[#002FA7]" />
            <p className="text-sm font-bold text-white">Connect to your local agent</p>
            <p className="text-[11px] text-[#555] max-w-sm leading-relaxed font-mono">
              Click <strong className="text-[#A0A0A0]">Configure</strong> above, enter your backend URL
              (<code className="bg-white/5 px-1">http://localhost:8000</code>) and API key
              (from <code className="bg-white/5 px-1">/admin/keys</code>).
              No tunnel needed — browsers allow direct calls to localhost.
            </p>
          </div>
        )}

        {apiKey && connStatus === 'error' && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-3 px-4">
            <div className="w-2 h-2 rounded-full bg-red-500" />
            <p className="text-[12px] font-mono text-red-400">Cannot reach {backendUrl}</p>
            <p className="text-[10px] text-[#555] font-mono">
              Make sure the proxy is running: <code className="bg-white/5 px-1">uvicorn proxy:app --port 8000</code>
            </p>
            <button onClick={() => { setConnStatus('idle'); setTimeout(() => setApiKey(k => k), 0); }}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-white/10 hover:border-white/20 text-[10px] font-mono text-[#555] hover:text-white transition-colors">
              <RefreshCw size={10} /> Retry
            </button>
          </div>
        )}

        {apiKey && connStatus === 'ok' && history.length === 0 && !busy && (
          <div className="flex flex-col items-center justify-center h-full text-center gap-2 px-4">
            <Bot size={32} className="text-[#002FA7]" />
            <p className="text-sm font-bold text-white">Agent ready</p>
            <p className="text-[10px] text-[#555] font-mono">
              {mode === 'auto'
                ? 'Auto mode — router picks the best local model for each message.'
                : model ? `Using ${short(model, 26)}` : 'Manual mode — select a model above.'}
            </p>
          </div>
        )}

        {history.map((m, i) => (
          <div key={i} className={`flex gap-2.5 ${m.role === 'user' ? 'justify-end' : ''}`}>
            {m.role !== 'user' && (
              <div className="w-6 h-6 bg-[#002FA7] flex items-center justify-center shrink-0 mt-0.5">
                <Bot size={12} />
              </div>
            )}
            <div className={`max-w-[85%] px-3.5 py-2.5 text-[12px] leading-relaxed whitespace-pre-wrap break-words
              ${m.role === 'user'
                ? 'bg-[#002FA7]/15 border border-[#002FA7]/25 text-white'
                : 'bg-[#1A1A1A] border border-white/8 text-[#C0C0C0]'}`}>
              {m.role !== 'user' && (
                <div className="text-[9px] font-mono uppercase tracking-wider text-[#444] mb-1.5">{m.role}</div>
              )}
              {m.content}
            </div>
          </div>
        ))}

        {session?.last_result?.summary && (
          <div className="flex gap-2.5">
            <div className="w-6 h-6 bg-[#002FA7] flex items-center justify-center shrink-0 mt-0.5">
              <FileText size={12} />
            </div>
            <div className="max-w-[85%] px-3.5 py-2.5 bg-[#1A1A1A] border border-white/8 text-[12px] text-[#C0C0C0] leading-relaxed">
              <div className="text-[9px] font-mono uppercase tracking-wider text-[#444] mb-1.5">Result</div>
              {session.last_result.summary}
            </div>
          </div>
        )}

        {/* Thinking animation */}
        {busy && (
          <div className="flex gap-2.5">
            <div className="w-6 h-6 bg-[#002FA7] flex items-center justify-center shrink-0 mt-0.5">
              <Bot size={12} />
            </div>
            <div className="px-3.5 py-2.5 bg-[#1A1A1A] border border-white/8 flex items-center gap-2.5">
              <span className="flex gap-1">
                {[0,1,2].map(i => (
                  <span key={i} className="w-1.5 h-1.5 rounded-full bg-[#002FA7]"
                    style={{ animation: `thinkingDot 1.4s ease-in-out ${i*0.16}s infinite` }} />
                ))}
              </span>
              <span className="text-[10px] font-mono text-[#555]">
                {mode === 'auto' ? 'Routing & running agent…' : `Running with ${short(model || 'selected model', 20)}…`}
              </span>
              {elapsed >= 8 && (
                <span className="flex items-center gap-1 text-[9px] font-mono text-[#444]">
                  <Clock size={9} /> {elapsed}s
                </span>
              )}
            </div>
          </div>
        )}

        <div ref={chatEndRef} />
      </div>

      {/* ── Composer ── */}
      <div className="border-t border-white/10 px-4 py-3 bg-[#0D0D0D] shrink-0">
        <div className="flex gap-2 items-end">
          <textarea
            ref={inputRef}
            value={instruction}
            onChange={e => setInstruction(e.target.value)}
            onKeyDown={handleKey}
            placeholder={
              !apiKey              ? 'Connect above to start…'
              : mode === 'auto'   ? 'Ask anything — Ctrl+Enter to send…'
              : !model            ? 'Select a model above first…'
              : `Using ${short(model, 20)} — Ctrl+Enter to send…`
            }
            rows={2}
            style={{ fontSize: '16px' }}
            disabled={!apiKey || busy || (mode === 'manual' && !model)}
            className="flex-1 bg-[#141414] border border-white/10 focus:border-[#002FA7] px-3 py-2.5 text-sm text-white font-mono outline-none resize-none transition-colors disabled:opacity-40"
          />
          <button onClick={send}
            disabled={!instruction.trim() || !apiKey || busy || (mode === 'manual' && !model)}
            className="bg-[#002FA7] hover:bg-[#002585] text-white p-2.5 transition-colors disabled:opacity-40 disabled:cursor-not-allowed shrink-0">
            {busy ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
          </button>
        </div>
      </div>
    </div>
  );
}
