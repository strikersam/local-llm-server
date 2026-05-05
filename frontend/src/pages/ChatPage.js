import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { chatSend, listSessions, getSession, deleteSession, listProviders, listProviderModels, getAgentChatJob, cancelAgentChatJob, fmtErr } from '../api';
import { Send, Plus, Trash2, MessageSquare, Bot, User, Loader2, Zap, Clock, Settings, X, ChevronDown } from 'lucide-react';

const LS_PROVIDER_ID = 'llmrelay_provider_id';
const LS_MODEL       = 'llmrelay_model';
const LS_TEMPERATURE = 'llmrelay_temperature';
const LS_MODE        = 'llmrelay_mode'; // 'auto' | 'manual'

// ── helpers ───────────────────────────────────────────────────────────────────
function modelType(name = '') {
  if (/coder|code/i.test(name))                     return 'coder';
  if (/r1|reasoner|thinking|deepseek/i.test(name))  return 'reasoning';
  return 'general';
}
function modelTypeBadge(name) {
  const t = modelType(name);
  if (t === 'coder')     return 'border-blue-500/40 bg-blue-500/10 text-blue-300';
  if (t === 'reasoning') return 'border-emerald-500/40 bg-emerald-500/10 text-emerald-300';
  return 'border-white/20 bg-white/5 text-[#737373]';
}
function short(s = '', max = 28) {
  return s.length <= max ? s : s.slice(0, max - 1) + '…';
}

// ── ThinkingBubble ────────────────────────────────────────────────────────────
function ThinkingBubble({ elapsed }) {
  return (
    <div className="flex gap-3 animate-fade-in">
      <div className="w-7 h-7 bg-[#002FA7] flex items-center justify-center shrink-0">
        <Bot size={14} />
      </div>
      <div className="bg-[#1A1A1A] border border-white/10 px-4 py-3 flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#737373] font-mono uppercase tracking-wider">Thinking</span>
          <span className="flex gap-1">
            {[0, 1, 2].map(i => (
              <span
                key={i}
                className="w-1.5 h-1.5 rounded-full bg-[#002FA7]"
                style={{ animation: `thinkingDot 1.4s ease-in-out ${i * 0.16}s infinite` }}
              />
            ))}
          </span>
        </div>
        {elapsed >= 10 && (
          <div className="flex items-center gap-1.5 text-[9px] text-[#737373] font-mono">
            <Clock size={9} />
            <span>{elapsed}s — model may be reasoning deeply, please wait…</span>
          </div>
        )}
      </div>
    </div>
  );
}

// ── ModelPickerModal ──────────────────────────────────────────────────────────
function ModelPickerModal({ providers, onConfirm, onClose, initialProvider, initialModel }) {
  const [pickerProvider, setPickerProvider] = useState(initialProvider || providers[0]?.provider_id || '');
  const [pickerModels,   setPickerModels]   = useState([]);
  const [pickerModel,    setPickerModel]    = useState(initialModel || '');
  const [loading,        setLoading]        = useState(false);

  useEffect(() => {
    if (!pickerProvider) return;
    setLoading(true);
    listProviderModels(pickerProvider)
      .then(({ data }) => {
        const ms = data.models || [];
        setPickerModels(ms);
        if (!pickerModel || !ms.includes(pickerModel)) setPickerModel(ms[0] || '');
      })
      .catch(() => setPickerModels([]))
      .finally(() => setLoading(false));
  }, [pickerProvider]); // eslint-disable-line

  const providerName = providers.find(p => p.provider_id === pickerProvider)?.name || pickerProvider;

  return (
    <div
      className="fixed inset-0 bg-black/70 backdrop-blur-sm z-50 flex items-end md:items-center justify-center p-0 md:p-4"
      onClick={onClose}
    >
      <div
        className="w-full md:max-w-md bg-[#111111] border border-white/10 rounded-t-2xl md:rounded-2xl flex flex-col overflow-hidden shadow-2xl max-h-[90vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10 shrink-0">
          <span className="text-sm font-bold font-mono tracking-wide">Select Provider &amp; Model</span>
          <button onClick={onClose} className="text-[#737373] hover:text-white transition-colors p-1">
            <X size={16} />
          </button>
        </div>

        {/* Provider tabs */}
        <div className="flex gap-2 px-5 py-3 overflow-x-auto border-b border-white/10 shrink-0 scrollbar-hide">
          {providers.map(p => (
            <button
              key={p.provider_id}
              onClick={() => setPickerProvider(p.provider_id)}
              className={`px-3 py-1.5 rounded-full text-[10px] font-mono uppercase tracking-wider whitespace-nowrap border transition-colors ${
                pickerProvider === p.provider_id
                  ? 'border-[#002FA7] bg-[#002FA7]/20 text-white'
                  : 'border-white/10 text-[#737373] hover:border-white/20 hover:text-[#A0A0A0]'
              }`}
            >
              {p.name}
            </button>
          ))}
        </div>

        {/* Model list */}
        <div className="flex-1 overflow-y-auto px-5 py-3 space-y-2 min-h-0">
          {loading ? (
            <div className="flex items-center justify-center py-10">
              <Loader2 size={18} className="animate-spin text-[#737373]" />
              <span className="ml-2 text-xs text-[#737373] font-mono">Loading models…</span>
            </div>
          ) : pickerModels.length === 0 ? (
            <div className="py-10 text-center text-xs text-[#737373] font-mono">
              No models available for this provider.
            </div>
          ) : (
            pickerModels.map(m => (
              <button
                key={m}
                onClick={() => setPickerModel(m)}
                className={`w-full flex items-center justify-between px-4 py-3 border text-left transition-colors ${
                  pickerModel === m
                    ? 'border-[#002FA7] bg-[#002FA7]/10'
                    : 'border-white/10 hover:border-white/20 hover:bg-white/[0.02]'
                }`}
              >
                <span className="text-xs font-mono text-white truncate pr-3">{m}</span>
                <span className={`text-[9px] font-mono uppercase tracking-wider px-2 py-0.5 border rounded-sm shrink-0 ${modelTypeBadge(m)}`}>
                  {modelType(m)}
                </span>
              </button>
            ))
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-5 py-4 border-t border-white/10 shrink-0">
          <button
            onClick={onClose}
            className="flex-1 py-2.5 border border-white/10 text-xs font-mono uppercase tracking-wider text-[#737373] hover:text-white hover:border-white/20 transition-colors"
          >
            Cancel
          </button>
          <button
            disabled={!pickerModel}
            onClick={() => onConfirm(pickerProvider, pickerModel)}
            className="flex-1 py-2.5 bg-[#002FA7] hover:bg-[#002585] text-white text-xs font-mono uppercase tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
          >
            Use {pickerModel ? short(pickerModel, 20) : 'model'}
          </button>
        </div>
      </div>
    </div>
  );
}

function CommercialApprovalModal({ approval, onApprove, onCancel }) {
  if (!approval) return null;

  return (
    <div className="fixed inset-0 bg-black/75 backdrop-blur-sm z-50 flex items-center justify-center p-4" data-testid="commercial-approval-modal">
      <div className="w-full max-w-lg bg-[#111111] border border-[#002FA7]/25 rounded-2xl shadow-2xl overflow-hidden">
        <div className="px-5 py-4 border-b border-white/10">
          <div className="text-sm font-bold font-mono tracking-wide text-white" data-testid="commercial-approval-title">
            Commercial Fallback Approval
          </div>
          <p className="mt-2 text-xs text-[#A0A0A0] leading-relaxed" data-testid="commercial-approval-message">
            {approval.message || 'The system needs permission before switching to a commercial provider for this request.'}
          </p>
        </div>

        <div className="px-5 py-4 space-y-3">
          <div>
            <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#737373] mb-2">Candidate providers</div>
            <div className="flex flex-wrap gap-2" data-testid="commercial-approval-candidates">
              {(approval.candidates || []).map((candidate) => (
                <span
                  key={candidate}
                  className="px-2.5 py-1 rounded-full border border-[#002FA7]/25 bg-[#002FA7]/10 text-[10px] font-mono text-[#AFC4FF]"
                >
                  {candidate}
                </span>
              ))}
            </div>
          </div>

          <div className="rounded-xl border border-white/10 bg-white/[0.02] px-4 py-3">
            <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#737373] mb-2">Request</div>
            <p className="text-xs text-white leading-relaxed" data-testid="commercial-approval-request-preview">{approval.content}</p>
          </div>
        </div>

        <div className="px-5 py-4 border-t border-white/10 flex gap-3">
          <button
            onClick={onCancel}
            className="flex-1 py-2.5 border border-white/10 text-xs font-mono uppercase tracking-wider text-[#737373] hover:text-white hover:border-white/20 transition-colors"
            data-testid="commercial-approval-cancel-button"
          >
            Stay on local/free
          </button>
          <button
            onClick={onApprove}
            className="flex-1 py-2.5 bg-[#002FA7] hover:bg-[#002585] text-white text-xs font-mono uppercase tracking-wider transition-colors"
            data-testid="commercial-approval-approve-button"
          >
            Approve this request
          </button>
        </div>
      </div>
    </div>
  );
}

// ── ChatPage ──────────────────────────────────────────────────────────────────
export default function ChatPage() {
  const { sessionId: paramSid } = useParams();
  const navigate = useNavigate();

  const [sessions,        setSessions]        = useState([]);
  const [currentSession,  setCurrentSession]  = useState(null);
  const [messages,        setMessages]        = useState([]);
  const [input,           setInput]           = useState('');
  const [sending,         setSending]         = useState(false);
  const [thinkingElapsed, setThinkingElapsed] = useState(0);
  const [sessionId,       setSessionId]       = useState(paramSid || null);

  const [providers,   setProviders]   = useState([]);
  const [providerId,  setProviderId]  = useState(localStorage.getItem(LS_PROVIDER_ID) || '');
  const [model,       setModel]       = useState(localStorage.getItem(LS_MODEL) || '');
  const [temperature, setTemperature] = useState(Number(localStorage.getItem(LS_TEMPERATURE) || '0.3'));

  // Auto / Manual mode
  const [mode,       setMode]       = useState(localStorage.getItem(LS_MODE) || 'auto');
  const [agentMode,  setAgentMode]  = useState(localStorage.getItem('llmrelay_agent_mode') === 'true');
  const [showPicker, setShowPicker] = useState(false);
  const [approvalPrompt, setApprovalPrompt] = useState(null);
  const [agentJob, setAgentJob] = useState(null);

  const messagesEndRef = useRef(null);
  const inputRef       = useRef(null);
  const elapsedTimerRef = useRef(null);
  const jobPollRef = useRef(null);

  // Persist
  useEffect(() => { localStorage.setItem(LS_PROVIDER_ID, providerId); }, [providerId]);
  useEffect(() => { localStorage.setItem(LS_MODEL, model); }, [model]);
  useEffect(() => { localStorage.setItem(LS_TEMPERATURE, String(temperature)); }, [temperature]);
  useEffect(() => { localStorage.setItem(LS_MODE, mode); }, [mode]);
  useEffect(() => { localStorage.setItem('llmrelay_agent_mode', String(agentMode)); }, [agentMode]);

  useEffect(() => { loadSessions(); loadProviders(); }, []); // eslint-disable-line
  useEffect(() => { if (paramSid) loadSession(paramSid); }, [paramSid]); // eslint-disable-line
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => () => jobPollRef.current && clearInterval(jobPollRef.current), []);

  const startJobPolling = (jobId) => {
    if (jobPollRef.current) clearInterval(jobPollRef.current);
    jobPollRef.current = setInterval(async () => {
      try {
        const { data } = await getAgentChatJob(jobId);
        setAgentJob(data);
        if (['succeeded', 'failed', 'cancelled'].includes(data.status)) {
          clearInterval(jobPollRef.current);
          jobPollRef.current = null;
          if (data.status === 'succeeded' && data.result?.response) {
            setMessages(prev => [...prev, { role: 'assistant', content: data.result.response }]);
            loadSessions();
          } else if (data.status !== 'succeeded') {
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: `Agent job ${data.status}: ${data.error?.message || 'Execution stopped.'}`,
            }]);
          }
        }
      } catch {
        clearInterval(jobPollRef.current);
        jobPollRef.current = null;
      }
    }, 1500);
  };

  const loadSessions = async () => {
    try { const { data } = await listSessions(); setSessions(data.sessions || []); } catch {}
  };

  const loadProviders = async () => {
    try {
      const { data } = await listProviders();
      const list = data.providers || [];
      setProviders(list);
      if (!providerId && list.length) {
        const def = list.find(p => p.is_default) || list[0];
        setProviderId(def.provider_id);
      }
    } catch {}
  };

  const loadSession = async (sid) => {
    try {
      const { data } = await getSession(sid);
      setSessionId(sid);
      setCurrentSession(data);
      setMessages(data.messages || []);
      if (data.provider_id) setProviderId(data.provider_id);
      if (data.model)       setModel(data.model);
      if (data.temperature != null) setTemperature(Number(data.temperature));
    } catch {}
  };

  const startNew = () => {
    setSessionId(null);
    setCurrentSession(null);
    setMessages([]);
    navigate('/chat');
    inputRef.current?.focus();
  };

  const sendMessage = async ({ content, nextSessionId = sessionId, allowCommercialFallbackOnce = false, appendUserBubble = true }) => {
    if (!content.trim() || sending) return;
    setSending(true);
    setThinkingElapsed(0);
    elapsedTimerRef.current = setInterval(() => setThinkingElapsed(p => p + 1), 1000);
    if (appendUserBubble) {
      setMessages(prev => [...prev, { role: 'user', content }]);
    }

    // Auto mode: pass null model+provider → backend router classifies & picks best model.
    // Agent mode is controlled by the toggle; when off the backend uses _classify_complexity
    // to decide whether to invoke the agent pipeline (complex tasks) or direct LLM (chat).
    const sendModel      = mode === 'auto' ? null : (model || null);
    const sendProviderId = mode === 'auto' ? null : (providerId || null);

    try {
      const { data } = await chatSend(
        content,
        nextSessionId,
        sendModel,
        sendProviderId,
        temperature,
        agentMode,
        allowCommercialFallbackOnce,
      );
      setSessionId(data.session_id);
      if (data.job_id) {
        setAgentJob(data);
        startJobPolling(data.job_id);
      } else {
        setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      }
      if (!nextSessionId) navigate(`/chat/${data.session_id}`, { replace: true });
      setApprovalPrompt(null);
      loadSessions();
    } catch (err) {
      const detail = err?.response?.data?.detail;
      if (detail?.approval_required) {
        const approvalSessionId = detail.session_id || nextSessionId || sessionId;
        if (approvalSessionId && !nextSessionId) {
          setSessionId(approvalSessionId);
          navigate(`/chat/${approvalSessionId}`, { replace: true });
        }
        setApprovalPrompt({
          message: detail.message,
          candidates: detail.commercial_candidates || [],
          content,
          sessionId: approvalSessionId,
        });
        return;
      }
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${fmtErr(err?.response?.data?.detail) || err?.message || 'Failed — check provider config.'}`,
      }]);
    } finally {
      clearInterval(elapsedTimerRef.current);
      elapsedTimerRef.current = null;
      setSending(false);
      setThinkingElapsed(0);
    }
  };

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const content = input.trim();
    setInput('');
    await sendMessage({ content, appendUserBubble: true });
  };

  const handleApproveCommercialFallback = async () => {
    if (!approvalPrompt) return;
    await sendMessage({
      content: approvalPrompt.content,
      nextSessionId: approvalPrompt.sessionId || sessionId,
      allowCommercialFallbackOnce: true,
      appendUserBubble: false,
    });
  };

  const handleCancelCommercialFallback = () => {
    setApprovalPrompt(null);
    setMessages(prev => [...prev, {
      role: 'assistant',
      content: 'Commercial fallback cancelled. I stayed on local/free providers for this request.',
    }]);
  };

  const handleDelete = async (sid, e) => {
    e.stopPropagation();
    await deleteSession(sid);
    if (sessionId === sid) startNew();
    loadSessions();
  };

  const handleCancelAgentJob = async () => {
    if (!agentJob?.job_id) return;
    try {
      const { data } = await cancelAgentChatJob(agentJob.job_id);
      setAgentJob(data);
      if (jobPollRef.current) {
        clearInterval(jobPollRef.current);
        jobPollRef.current = null;
      }
    } catch {}
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const providerName = providers.find(p => p.provider_id === providerId)?.name || '';

  return (
    <div className="h-full flex" data-testid="chat-page">
      <CommercialApprovalModal
        approval={approvalPrompt}
        onApprove={handleApproveCommercialFallback}
        onCancel={handleCancelCommercialFallback}
      />

      {/* Model picker modal */}
      {showPicker && (
        <ModelPickerModal
          providers={providers}
          initialProvider={providerId}
          initialModel={model}
          onClose={() => setShowPicker(false)}
          onConfirm={(pid, m) => { setProviderId(pid); setModel(m); setShowPicker(false); }}
        />
      )}

      {/* Sessions sidebar — desktop only */}
      <div className="w-64 border-r border-white/10 bg-[#141414] flex-col shrink-0 hidden md:flex">
        <div className="p-4 border-b border-white/10">
          <button
            onClick={startNew}
            className="w-full flex items-center justify-center gap-2 bg-[#002FA7] hover:bg-[#002585] text-white py-2.5 text-xs tracking-wider uppercase font-mono transition-colors"
            data-testid="new-chat-button"
          >
            <Plus size={14} /> NEW SESSION
          </button>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-white/5">
          {sessions.map(s => (
            <div
              key={s._id}
              onClick={() => { navigate(`/chat/${s._id}`); loadSession(s._id); }}
              className={`w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-white/[0.03] transition-colors group cursor-pointer
                ${sessionId === s._id ? 'bg-white/5 border-l-2 border-[#002FA7]' : 'border-l-2 border-transparent'}`}
              data-testid={`session-${s._id}`}
            >
              <MessageSquare size={13} className="text-[#737373] shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-xs text-[#A0A0A0] truncate">{s.title || 'Untitled'}</div>
                <div className="text-[10px] text-[#737373]">{s.updated_at?.split('T')[0]}</div>
              </div>
              <button
                onClick={(e) => handleDelete(s._id, e)}
                className="opacity-0 group-hover:opacity-100 p-1 hover:text-[#FF3333] text-[#737373] transition-all"
                data-testid={`delete-session-${s._id}`}
              >
                <Trash2 size={12} />
              </button>
            </div>
          ))}
          {sessions.length === 0 && (
            <div className="p-4 text-center text-xs text-[#737373]">No sessions yet</div>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0">

        {/* ── Header ── */}
        <div className="px-4 md:px-6 py-3 border-b border-white/10 flex items-center gap-3 flex-wrap">
          <Bot size={16} className="text-[#002FA7] shrink-0" />
          <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold truncate">
            {currentSession ? currentSession.title?.slice(0, 40) : 'New Agent Session'}
          </span>

          {/* ── Mode toggle ── */}
          <div className="flex border border-white/10 rounded overflow-hidden shrink-0">
            <button
              onClick={() => setMode('auto')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider transition-colors ${
                mode === 'auto'
                  ? 'bg-[#002FA7]/20 border-r border-[#002FA7]/40 text-white'
                  : 'border-r border-white/10 text-[#737373] hover:text-[#A0A0A0]'
              }`}
              title="Auto: router picks the best model per message"
            >
              <Zap size={10} className={mode === 'auto' ? 'text-white' : 'text-[#737373]'} />
              Auto
            </button>
            <button
              onClick={() => setMode('manual')}
              className={`flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider transition-colors ${
                mode === 'manual'
                  ? 'bg-[#002FA7]/20 text-white'
                  : 'text-[#737373] hover:text-[#A0A0A0]'
              }`}
              title="Manual: choose your provider and model"
            >
              <Settings size={10} className={mode === 'manual' ? 'text-white' : 'text-[#737373]'} />
              Manual
            </button>
          </div>

          {/* Manual: show current selection + change button */}
          {mode === 'manual' && (
            <button
              onClick={() => setShowPicker(true)}
              className="flex items-center gap-1.5 px-3 py-1.5 border border-white/10 hover:border-white/20 text-[10px] font-mono text-[#A0A0A0] hover:text-white transition-colors"
              data-testid="change-model-btn"
            >
              <span className="truncate max-w-[160px]">
                {model ? `${short(providerName, 12)} · ${short(model, 16)}` : 'Select model'}
              </span>
              <ChevronDown size={10} />
            </button>
          )}

          {/* Auto: badge showing routing is active */}
          {mode === 'auto' && (
            <span className="text-[9px] font-mono text-[#737373] hidden md:inline">
              Router picks best model per message
            </span>
          )}

          {/* Agent mode toggle */}
          <div className="ml-auto flex items-center gap-2 shrink-0">
            <button
              onClick={() => setAgentMode(m => !m)}
              title={agentMode ? 'Agent mode ON — complex tasks use Plan→Execute→Verify. Click to disable.' : 'Agent mode OFF — direct LLM chat. Click to enable for code/GitHub tasks.'}
              className={`flex items-center gap-1.5 px-2.5 py-1 border text-[10px] font-mono transition-colors ${
                agentMode
                  ? 'border-[#002FA7]/60 bg-[#002FA7]/20 text-white'
                  : 'border-white/15 bg-white/5 text-[#737373] hover:border-white/25 hover:text-[#A0A0A0]'
              }`}
            >
              <Zap size={10} className={agentMode ? 'text-white' : 'text-[#737373]'} />
              Agent {agentMode ? 'ON' : 'OFF'}
            </button>
            <div className={`w-1.5 h-1.5 rounded-full ${agentMode ? 'bg-green-500' : 'bg-[#737373]'}`} />
          </div>
        </div>

        {agentJob && (
          <div className="px-4 md:px-6 py-3 border-b border-white/10 bg-[#101318]">
            <div className="rounded-2xl border border-[#002FA7]/25 bg-[#002FA7]/8 p-3 md:p-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div className="min-w-0">
                <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#AFC4FF]">Agent job</div>
                <div className="mt-1 text-sm text-white">{agentJob.status} · {agentJob.phase}</div>
                <div className="mt-1 text-[11px] text-[#A0A0A0] leading-relaxed">
                  {(agentJob.progress_events || []).slice(-1)[0]?.message || 'Waiting for progress...'}
                </div>
              </div>
              {['queued', 'running'].includes(agentJob.status) && (
                <button
                  onClick={handleCancelAgentJob}
                  className="self-start md:self-auto px-3 py-2 rounded-xl border border-white/10 text-[11px] font-mono uppercase tracking-wider text-[#A0A0A0] hover:text-white hover:border-white/20 transition-colors"
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        )}

        {/* ── Messages ── */}
        <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center animate-fade-in px-4">
              <Bot size={40} className="text-[#002FA7] mb-4" />
              <h3 className="text-lg font-bold tracking-tight mb-2" style={{ fontFamily: 'Outfit, sans-serif' }}>
                {agentMode ? 'Agent Mode Ready' : 'Direct Chat Ready'}
              </h3>
              <p className="text-xs text-[#737373] max-w-sm leading-relaxed mb-1">
                {agentMode
                  ? 'Agent mode — uses Plan→Execute→Verify for code edits, GitHub ops, and complex tasks.'
                  : mode === 'auto'
                    ? 'Direct chat — the router picks the best available model. Toggle Agent ON for code editing or GitHub tasks.'
                    : model
                      ? `Using ${short(model, 24)} · ${short(providerName, 20)}`
                      : 'Manual mode — tap "Select model" in the header to choose a provider and model.'}
              </p>
              <div className="mt-5 grid grid-cols-2 gap-2 w-full max-w-sm">
                {(agentMode
                  ? ['Edit a file in my repo', 'Commit changes to GitHub', 'Open a pull request', 'Analyze this codebase']
                  : ['Explain this code', 'Help me debug…', 'Write a function that…', 'What is the difference between…']
                ).map((p, i) => (
                  <button
                    key={i}
                    onClick={() => { setInput(p); inputRef.current?.focus(); }}
                    className="text-[10px] text-[#A0A0A0] border border-white/10 px-3 py-2 hover:border-[#002FA7] hover:text-white transition-all font-mono text-left"
                    data-testid={`quick-prompt-${i}`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : ''} animate-fade-in`}>
              {m.role === 'assistant' && (
                <div className="w-7 h-7 bg-[#002FA7] flex items-center justify-center shrink-0 mt-1">
                  <Bot size={14} />
                </div>
              )}
              <div className={`max-w-[85%] md:max-w-[70%] ${
                m.role === 'user'
                  ? 'bg-[#002FA7]/20 border border-[#002FA7]/30'
                  : 'bg-[#1A1A1A] border border-white/10'
              } px-4 py-3`}>
                {m.role === 'assistant' ? (
                  <div className="wiki-content text-xs text-[#A0A0A0]">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-xs text-white whitespace-pre-wrap">{m.content}</p>
                )}
              </div>
              {m.role === 'user' && (
                <div className="w-7 h-7 bg-white/10 flex items-center justify-center shrink-0 mt-1">
                  <User size={14} className="text-[#A0A0A0]" />
                </div>
              )}
            </div>
          ))}

          {sending && <ThinkingBubble elapsed={thinkingElapsed} />}
          <div ref={messagesEndRef} />
        </div>

        {/* ── Composer ── */}
        <div className="border-t border-white/10 p-3 md:p-4">
          {/* Mobile: show current mode / selection above composer */}
          <div className="flex items-center gap-2 mb-2 md:hidden">
            {mode === 'auto' ? (
              <span className="text-[9px] font-mono text-[#737373] flex items-center gap-1">
                <Zap size={9} className="text-[#002FA7]" /> {agentMode ? 'Agent mode active' : 'Auto routing active'}
              </span>
            ) : (
              <button
                onClick={() => setShowPicker(true)}
                className="flex items-center gap-1.5 text-[9px] font-mono text-[#737373] border border-white/10 px-2 py-1 rounded"
              >
                {model ? short(model, 22) : 'Select model'}
                <ChevronDown size={9} />
              </button>
            )}
          </div>

          <div className="flex gap-3 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={
                agentMode
                  ? 'Describe a task — agent will plan, execute, and verify…'
                  : mode === 'auto'
                    ? 'Message the AI — router picks the best model…'
                    : model
                      ? `Chat with ${short(model, 20)}…`
                      : 'Select a model first…'
              }
              rows={1}
              style={{ fontSize: '16px' }} /* prevent iOS zoom */
              className="flex-1 bg-[#141414] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7] resize-none transition-colors"
              data-testid="chat-input"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending || (mode === 'manual' && !model)}
              className="bg-[#002FA7] hover:bg-[#002585] text-white p-3 transition-colors disabled:opacity-50 disabled:cursor-not-allowed shrink-0 flex items-center gap-2"
              data-testid="chat-send-button"
            >
              {sending ? <Loader2 size={16} className="animate-spin" /> : <Send size={16} />}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
