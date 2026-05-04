import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { chatSend, listSessions, getSession, deleteSession, listProviders, listProviderModels, getGithubStatus, createTask, createSchedule, fmtErr, getBackendUrl } from '../api';
import { Send, Plus, Trash2, MessageSquare, Bot, User, Loader2, Zap, Clock, Settings, X, ChevronDown } from 'lucide-react';
import AgentStatusPanel from '../components/AgentStatusPanel.jsx';
import AgentActivityFeed from '../components/AgentActivityFeed.jsx';
import ToolCallViewer from '../components/ToolCallViewer.jsx';

const LS_PROVIDER_ID = 'llmrelay_provider_id';
const LS_MODEL       = 'llmrelay_model';
const LS_TEMPERATURE = 'llmrelay_temperature';
const LS_MODE        = 'llmrelay_mode'; // 'auto' | 'manual'
const DIRECT_CHAT_GITHUB_KEYWORDS = ['github', 'pull request', 'open pr', 'open a pr', 'branch', 'commit changes', 'push', 'clone'];
const DIRECT_CHAT_WORKSPACE_KEYWORDS = ['repository', 'repo', 'workspace', 'codebase', 'multi-file', 'multiple files', 'edit code', 'edit file', 'exact file edits', 'tests to add', 'merge strategy'];
const DIRECT_CHAT_RUNTIME_KEYWORDS = ['docker', 'dockerfile', 'container', 'runtime', 'run tests', 'build image', 'install dependency', 'copy package', 'start server'];
const DIRECT_CHAT_EXPLANATION_PREFIXES = ['explain', 'why', 'how do', 'how does', 'what is', 'what are', 'walk me through', 'help me understand'];
const DIRECT_CHAT_EXECUTION_SIGNALS = ['fix ', 'edit ', 'update ', 'change the code', 'apply the fix', 'make the fix', 'run tests', 'run the tests', 'commit the changes', 'push the', 'merge the', 'add a regression test', 'add tests'];
const DIRECT_CHAT_RECURRING_KEYWORDS = ['every day', 'daily', 'every morning', 'every night', 'every week', 'weekly', 'every month', 'monthly', 'every hour', 'hourly', 'cron', 'schedule this', 'scheduled', 'automatically'];

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
function normalizeSessionMessages(messages = []) {
  return messages.map((message) => ({
    ...message,
    agentHandoff: message.agentHandoff || message.assistant_meta || null,
  }));
}
function deriveWorkItemTitle(content = '', fallback = 'Follow up on direct chat request') {
  let text = content.replace(/\s+/g, ' ').trim();
  ['\n', '.', '?', '!'].some((delimiter) => {
    if (!text.includes(delimiter)) return false;
    text = text.split(delimiter, 1)[0].trim();
    return true;
  });
  if (!text) return fallback;
  if (text.length > 72) {
    const trimmed = text.slice(0, 72).replace(/\s+\S*$/, '').trim();
    text = `${trimmed || text.slice(0, 72).trim()}…`;
  }
  return text.charAt(0).toUpperCase() + text.slice(1);
}
function inferTaskPriority(content = '') {
  const lower = content.toLowerCase();
  if (['urgent', 'sev1', 'critical', 'outage'].some((keyword) => lower.includes(keyword))) return 'urgent';
  if (['production', 'regression', 'broken', 'fix'].some((keyword) => lower.includes(keyword))) return 'high';
  return 'medium';
}
function inferSchedulePreset(content = '') {
  const lower = content.toLowerCase();
  if (lower.includes('every hour') || lower.includes('hourly')) return { cron: '0 * * * *', cadence: 'Hourly' };
  if (lower.includes('every week') || lower.includes('weekly')) return { cron: '0 9 * * 1', cadence: 'Weekly' };
  if (lower.includes('every month') || lower.includes('monthly')) return { cron: '0 9 1 * *', cadence: 'Monthly' };
  return { cron: '0 9 * * *', cadence: 'Daily' };
}
function buildDirectChatTags(reasonCodes = []) {
  return reasonCodes.filter((code) => ['github', 'workspace', 'runtime'].includes(code));
}
function buildWorkflowSuggestions(content = '', reasonCodes = []) {
  const title = deriveWorkItemTitle(content);
  const taskType = reasonCodes.includes('github') || reasonCodes.includes('workspace')
    ? 'repository_change'
    : reasonCodes.includes('runtime')
      ? 'runtime_change'
      : 'general';

  const suggestions = [{
    kind: 'task',
    label: 'Create Task',
    route: '/tasks',
    payload: {
      title,
      description: 'Created from a Direct Chat handoff so the work can be tracked in the task board.',
      prompt: content,
      priority: inferTaskPriority(content),
      task_type: taskType,
      requires_approval: reasonCodes.includes('github'),
      tags: buildDirectChatTags(reasonCodes),
    },
  }];

  const lower = content.toLowerCase();
  if (DIRECT_CHAT_RECURRING_KEYWORDS.some((keyword) => lower.includes(keyword))) {
    const { cron, cadence } = inferSchedulePreset(content);
    suggestions.push({
      kind: 'schedule',
      label: 'Create Schedule',
      route: '/schedules',
      payload: {
        name: `${cadence}: ${title}`,
        cron,
        instruction: content,
        approval_gate: reasonCodes.includes('github'),
        tags: buildDirectChatTags(reasonCodes),
      },
    });
  }

  return suggestions;
}
function detectAgentModeRecommendation(content = '', githubConnected = false) {
  const lower = content.toLowerCase().trim();
  if (!lower) return null;

  const reasonCodes = [];
  const reasons = [];

  if (DIRECT_CHAT_GITHUB_KEYWORDS.some((keyword) => lower.includes(keyword))) {
    reasonCodes.push('github');
    reasons.push('GitHub branch / PR actions');
  }
  if (DIRECT_CHAT_WORKSPACE_KEYWORDS.some((keyword) => lower.includes(keyword))) {
    reasonCodes.push('workspace');
    reasons.push('repository / file changes');
  }
  if (DIRECT_CHAT_RUNTIME_KEYWORDS.some((keyword) => lower.includes(keyword))) {
    reasonCodes.push('runtime');
    reasons.push('workspace or container execution');
  }

  const asksForConcreteChanges = ['exact file edits', 'tests to add', 'commit message', 'apply the fix', 'make the fix', 'change the code', 'open a pr', 'open pr', 'run tests', 'merge strategy']
    .some((phrase) => lower.includes(phrase));
  const asksForExplanation = DIRECT_CHAT_EXPLANATION_PREFIXES.some((prefix) => lower.startsWith(prefix));
  const hasExecutionSignal = DIRECT_CHAT_EXECUTION_SIGNALS.some((signal) => lower.includes(signal));

  if (!reasonCodes.length) return null;
  if (asksForExplanation && !hasExecutionSignal) return null;
  if (reasonCodes.length === 1 && !asksForConcreteChanges) return null;

  return {
    recommended_mode: 'agent',
    reason_codes: reasonCodes,
    reasons,
    workflow_suggestions: buildWorkflowSuggestions(content, reasonCodes),
    settings_route: reasonCodes.includes('github') && !githubConnected ? '/settings' : null,
  };
}

function emptyAgentSnapshot() {
  return {
    has_events: false,
    agents: [],
    tool_calls: [],
    latest_summary: '',
    latest_error: '',
  };
}

// ── ThinkingBubble ────────────────────────────────────────────────────────────
function ThinkingBubble({ elapsed, agentMode }) {
  return (
    <div className="flex gap-3 animate-fade-in">
      <div className="w-7 h-7 bg-[#002FA7] flex items-center justify-center shrink-0">
        <Bot size={14} />
      </div>
      <div className="bg-[#1A1A1A] border border-white/10 px-4 py-3 flex flex-col gap-1.5">
        <div className="flex items-center gap-2">
          <span className="text-[10px] text-[#737373] font-mono uppercase tracking-wider">
            {agentMode ? 'Agent running' : 'Thinking'}
          </span>
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
            <span>
              {agentMode
                ? `${elapsed}s — Plan → Execute → Verify may take up to 45s`
                : `${elapsed}s — model may be reasoning deeply, please wait…`}
            </span>
          </div>
        )}
        {agentMode && (
          <div className="flex flex-wrap gap-1.5 pt-1">
            {['Plan', 'Execute', 'Verify'].map((step) => (
              <span key={step} className="border border-white/10 px-1.5 py-0.5 text-[9px] font-mono uppercase tracking-wider text-[#737373]">
                {step}
              </span>
            ))}
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
  const [githubStatus, setGithubStatus] = useState({ connected: false, login: '' });
  const [workflowAction, setWorkflowAction] = useState('');
  const [agentSnapshot, setAgentSnapshot] = useState(emptyAgentSnapshot);
  const [agentConsoleTab, setAgentConsoleTab] = useState('progress');

  const messagesEndRef = useRef(null);
  const inputRef       = useRef(null);
  const elapsedTimerRef = useRef(null);

  // Persist
  useEffect(() => { localStorage.setItem(LS_PROVIDER_ID, providerId); }, [providerId]);
  useEffect(() => { localStorage.setItem(LS_MODEL, model); }, [model]);
  useEffect(() => { localStorage.setItem(LS_TEMPERATURE, String(temperature)); }, [temperature]);
  useEffect(() => { localStorage.setItem(LS_MODE, mode); }, [mode]);
  useEffect(() => { localStorage.setItem('llmrelay_agent_mode', String(agentMode)); }, [agentMode]);

  useEffect(() => { loadSessions(); loadProviders(); loadGithubAccess(); }, []); // eslint-disable-line
  useEffect(() => { if (paramSid) loadSession(paramSid); }, [paramSid]); // eslint-disable-line
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => {
    if (!sessionId) {
      setAgentSnapshot(emptyAgentSnapshot());
      return undefined;
    }

    let cancelled = false;

    const loadAgentSnapshot = async () => {
      try {
        const base = (getBackendUrl() || '').replace(/\/$/, '');
        const response = await fetch(`${base}/api/agent/status?session_id=${encodeURIComponent(sessionId)}`);
        if (!response.ok) {
          if (!cancelled) setAgentSnapshot(emptyAgentSnapshot());
          return;
        }
        const data = await response.json();
        if (!cancelled) {
          setAgentSnapshot({
            has_events: Boolean(data.has_events),
            agents: Array.isArray(data.agents) ? data.agents : [],
            tool_calls: Array.isArray(data.tool_calls) ? data.tool_calls : [],
            latest_summary: data.latest_summary || '',
            latest_error: data.latest_error || '',
          });
        }
      } catch {
        if (!cancelled) setAgentSnapshot(emptyAgentSnapshot());
      }
    };

    loadAgentSnapshot();
    const timer = setInterval(loadAgentSnapshot, 2000);
    return () => {
      cancelled = true;
      clearInterval(timer);
    };
  }, [sessionId]);

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

  const loadGithubAccess = async () => {
    try {
      const { data } = await getGithubStatus();
      setGithubStatus({ connected: Boolean(data.connected), login: data.github_login || data.login || '' });
    } catch {
      setGithubStatus({ connected: false, login: '' });
    }
  };

  const loadSession = async (sid) => {
    try {
      const { data } = await getSession(sid);
      setSessionId(sid);
      setCurrentSession(data);
      setMessages(normalizeSessionMessages(data.messages || []));
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

  const sendMessage = async ({ content, nextSessionId = sessionId, allowCommercialFallbackOnce = false, appendUserBubble = true, agentModeOverride = agentMode }) => {
    if (!content.trim() || sending) return;
    setSending(true);
    if (agentModeOverride) setAgentConsoleTab('activity');
    setThinkingElapsed(0);
    elapsedTimerRef.current = setInterval(() => setThinkingElapsed(p => p + 1), 1000);
    if (appendUserBubble) {
      setMessages(prev => [...prev, { role: 'user', content }]);
    }

    // Auto mode: pass null model+provider so the backend router can pick a model.
    // Agent orchestration is controlled strictly by the Agent Mode toggle.
    const sendModel      = mode === 'auto' ? null : (model || null);
    const sendProviderId = mode === 'auto' ? null : (providerId || null);

    try {
      const { data } = await chatSend(
        content,
        nextSessionId,
        sendModel,
        sendProviderId,
        temperature,
        agentModeOverride,
        allowCommercialFallbackOnce,
      );
      setSessionId(data.session_id);
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.response,
        agentHandoff: data.assistant_meta || null,
      }]);
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

  const handleRetryWithAgentMode = async (meta) => {
    const retryablePrompt = meta?.retryable_prompt;
    if (!retryablePrompt || sending) return;
    setAgentMode(true);
    await sendMessage({
      content: retryablePrompt,
      nextSessionId: sessionId,
      appendUserBubble: false,
      agentModeOverride: true,
    });
  };

  const handleOpenSettings = () => {
    navigate('/settings');
  };

  const handleCreateTaskFromSuggestion = async (suggestion) => {
    const payload = suggestion?.payload;
    if (!payload || workflowAction) return;
    setWorkflowAction('task');
    try {
      const { data } = await createTask(payload);
      const createdTask = data?.task || data;
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Created task **${createdTask?.title || payload.title}**. Opening Tasks so you can track it.`,
      }]);
      navigate('/tasks');
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error creating task: ${fmtErr(err?.response?.data?.detail) || err?.message || 'Please try again from Tasks.'}`,
      }]);
    } finally {
      setWorkflowAction('');
    }
  };

  const handleCreateScheduleFromSuggestion = async (suggestion) => {
    const payload = suggestion?.payload;
    if (!payload || workflowAction) return;
    setWorkflowAction('schedule');
    try {
      const { data } = await createSchedule(payload);
      const createdSchedule = data?.schedule || data;
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Created schedule **${createdSchedule?.name || payload.name}**. Opening Schedules so you can manage it.`,
      }]);
      navigate('/schedules');
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error creating schedule: ${fmtErr(err?.response?.data?.detail) || err?.message || 'Please try again from Schedules.'}`,
      }]);
    } finally {
      setWorkflowAction('');
    }
  };

  const handleDelete = async (sid, e) => {
    e.stopPropagation();
    await deleteSession(sid);
    if (sessionId === sid) startNew();
    loadSessions();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend(); }
  };

  const providerName = providers.find(p => p.provider_id === providerId)?.name || '';
  const composerRecommendation = !agentMode
    ? detectAgentModeRecommendation(input, githubStatus.connected)
    : null;
  const composerTaskSuggestion = composerRecommendation?.workflow_suggestions?.find((suggestion) => suggestion.kind === 'task');
  const composerScheduleSuggestion = composerRecommendation?.workflow_suggestions?.find((suggestion) => suggestion.kind === 'schedule');
  const showAgentConsole = Boolean(
    sessionId && (
      sending ||
      agentMode ||
      agentSnapshot.has_events ||
      agentSnapshot.agents.length ||
      agentSnapshot.tool_calls.length ||
      agentSnapshot.latest_summary ||
      agentSnapshot.latest_error
    )
  );

  return (
    <div className="h-full min-h-0 flex bg-[#0B0D12]" data-testid="chat-page">
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
      <div className="flex-1 flex flex-col min-w-0 min-h-0">

        {/* ── Header ── */}
        <div className="sticky top-0 z-20 px-4 md:px-6 py-3 border-b border-white/10 flex items-center gap-3 flex-wrap bg-[#0B0D12]/95 backdrop-blur supports-[backdrop-filter]:bg-[#0B0D12]/80">
          <Bot size={16} className="text-[#002FA7] shrink-0" />
          <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold truncate">
            {currentSession ? currentSession.title?.slice(0, 40) : 'New Chat Session'}
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
            <div className="hidden lg:flex items-center gap-2 text-[9px] font-mono uppercase tracking-[0.18em] text-[#737373]">
              <span className={`w-1.5 h-1.5 rounded-full ${githubStatus.connected ? 'bg-green-500' : 'bg-[#737373]'}`} />
              <span>{githubStatus.connected ? `GitHub ready${githubStatus.login ? ` · ${githubStatus.login}` : ''}` : 'GitHub not connected'}</span>
            </div>
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

        {showAgentConsole && (
          <div className="px-3 pt-3 md:px-6 md:pt-4">
            <div className="rounded-[28px] border border-white/10 bg-[#11151D]/90 shadow-[0_16px_50px_rgba(0,0,0,0.28)] backdrop-blur-xl overflow-hidden" data-testid="agent-console">
              <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/10 bg-white/[0.03]">
                <div>
                  <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-[#AFC4FF]">Live agent workspace</div>
                  <div className="text-xs text-white mt-1">
                    {agentSnapshot.latest_error
                      ? agentSnapshot.latest_error
                      : agentSnapshot.latest_summary || 'Track planning, tool use, and verification in real time.'}
                  </div>
                </div>
                <div className="hidden md:flex items-center gap-2 text-[10px] font-mono text-[#737373]">
                  <span className="border border-white/10 px-2 py-1 rounded-full">{agentSnapshot.agents.length} agents</span>
                  <span className="border border-white/10 px-2 py-1 rounded-full">{agentSnapshot.tool_calls.length} tools</span>
                </div>
              </div>

              <div className="md:hidden px-3 pt-3 flex gap-2 overflow-x-auto scrollbar-hide">
                {[
                  ['progress', 'Progress'],
                  ['activity', 'Activity'],
                  ['tools', 'Tools'],
                ].map(([value, label]) => (
                  <button
                    key={value}
                    onClick={() => setAgentConsoleTab(value)}
                    className={`px-3 py-1.5 rounded-full border text-[10px] font-mono uppercase tracking-[0.18em] whitespace-nowrap transition-colors ${
                      agentConsoleTab === value
                        ? 'border-[#002FA7]/60 bg-[#002FA7]/20 text-white'
                        : 'border-white/10 text-[#737373]'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>

              <div className="p-3 md:p-4 md:grid md:grid-cols-2 md:gap-4 space-y-3 md:space-y-0">
                <div className={`${agentConsoleTab !== 'progress' ? 'hidden md:block' : ''}`}>
                  <AgentStatusPanel sessionId={sessionId} className="h-full min-h-[220px]" />
                </div>
                <div className={`${agentConsoleTab !== 'tools' ? 'hidden md:block' : ''}`}>
                  <ToolCallViewer toolCalls={agentSnapshot.tool_calls} className="h-full min-h-[220px]" />
                </div>
                <div className={`${agentConsoleTab !== 'activity' ? 'hidden md:block' : ''} md:col-span-2`}>
                  <div className="h-[320px] md:h-[360px]">
                    <AgentActivityFeed sessionId={sessionId} className="h-full" />
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ── Messages ── */}
        <div className="flex-1 overflow-y-auto px-4 pb-32 pt-4 md:px-6 md:pb-40 md:pt-6 space-y-4">
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
                  <>
                    <div className="wiki-content text-xs text-[#A0A0A0]">
                      <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                    </div>
                    {m.agentHandoff?.recommended_mode === 'agent' && (
                      <div className="mt-3 border-t border-white/10 pt-3 space-y-2" data-testid="agent-handoff-actions">
                        <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#737373]">
                          Recommended next step
                        </div>
                        <div className="flex flex-wrap gap-2">
                          <button
                            onClick={() => handleRetryWithAgentMode(m.agentHandoff)}
                            className="px-3 py-2 bg-[#002FA7] hover:bg-[#002585] text-white text-[10px] font-mono uppercase tracking-wider transition-colors"
                            data-testid="retry-with-agent-mode-button"
                          >
                            Retry with Agent Mode
                          </button>
                          {m.agentHandoff?.workflow_suggestions?.some((suggestion) => suggestion.kind === 'task') && (
                            <button
                              onClick={() => handleCreateTaskFromSuggestion(m.agentHandoff.workflow_suggestions.find((suggestion) => suggestion.kind === 'task'))}
                              className="px-3 py-2 border border-white/10 hover:border-white/20 text-[#A0A0A0] hover:text-white text-[10px] font-mono uppercase tracking-wider transition-colors"
                              data-testid="agent-handoff-create-task-button"
                            >
                              {workflowAction === 'task' ? 'Creating Task…' : 'Create Task'}
                            </button>
                          )}
                          {m.agentHandoff?.workflow_suggestions?.some((suggestion) => suggestion.kind === 'schedule') && (
                            <button
                              onClick={() => handleCreateScheduleFromSuggestion(m.agentHandoff.workflow_suggestions.find((suggestion) => suggestion.kind === 'schedule'))}
                              className="px-3 py-2 border border-white/10 hover:border-white/20 text-[#A0A0A0] hover:text-white text-[10px] font-mono uppercase tracking-wider transition-colors"
                              data-testid="agent-handoff-create-schedule-button"
                            >
                              {workflowAction === 'schedule' ? 'Creating Schedule…' : 'Create Schedule'}
                            </button>
                          )}
                          {m.agentHandoff?.settings_route && (
                            <button
                              onClick={handleOpenSettings}
                              className="px-3 py-2 border border-white/10 hover:border-white/20 text-[#A0A0A0] hover:text-white text-[10px] font-mono uppercase tracking-wider transition-colors"
                              data-testid="agent-handoff-settings-button"
                            >
                              Open Settings
                            </button>
                          )}
                        </div>
                      </div>
                    )}
                  </>
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

          {sending && <ThinkingBubble elapsed={thinkingElapsed} agentMode={agentMode} />}
          <div ref={messagesEndRef} />
        </div>

        {/* ── Composer ── */}
        <div className="sticky bottom-0 z-20 border-t border-white/10 p-3 md:p-4 bg-[#0B0D12]/95 backdrop-blur supports-[backdrop-filter]:bg-[#0B0D12]/80 pb-[calc(env(safe-area-inset-bottom,0px)+0.75rem)]">
          {composerRecommendation && (
            <div className="mb-3 border border-[#002FA7]/30 bg-[#002FA7]/10 px-3 py-3" data-testid="agent-mode-preflight-banner">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#AFC4FF]">
                    Agent Mode recommended before send
                  </div>
                  <div className="text-xs text-white leading-relaxed">
                    This looks like a request for {composerRecommendation.reasons.join(', ')}.
                    Direct chat can explain patterns, but Agent Mode is safer for real repo, GitHub, or runtime actions.
                  </div>
                  <div className="flex flex-wrap gap-2 text-[10px] font-mono uppercase tracking-[0.18em] text-[#737373]">
                    <span className="border border-white/10 px-2 py-1">GitHub {githubStatus.connected ? 'connected' : 'not connected'}</span>
                    <span className="border border-white/10 px-2 py-1">{mode === 'auto' ? 'Auto routing' : 'Manual model selection'}</span>
                  </div>
                </div>
                <div className="flex flex-wrap gap-2">
                  <button
                    onClick={() => setAgentMode(true)}
                    className="px-3 py-2 bg-[#002FA7] hover:bg-[#002585] text-white text-[10px] font-mono uppercase tracking-wider transition-colors"
                    data-testid="preflight-enable-agent-mode-button"
                  >
                    Enable Agent Mode
                  </button>
                  {composerTaskSuggestion && (
                    <button
                      onClick={() => handleCreateTaskFromSuggestion(composerTaskSuggestion)}
                      className="px-3 py-2 border border-white/10 hover:border-white/20 text-[#A0A0A0] hover:text-white text-[10px] font-mono uppercase tracking-wider transition-colors"
                      data-testid="preflight-create-task-button"
                    >
                      {workflowAction === 'task' ? 'Creating Task…' : 'Create Task'}
                    </button>
                  )}
                  {composerScheduleSuggestion && (
                    <button
                      onClick={() => handleCreateScheduleFromSuggestion(composerScheduleSuggestion)}
                      className="px-3 py-2 border border-white/10 hover:border-white/20 text-[#A0A0A0] hover:text-white text-[10px] font-mono uppercase tracking-wider transition-colors"
                      data-testid="preflight-create-schedule-button"
                    >
                      {workflowAction === 'schedule' ? 'Creating Schedule…' : 'Create Schedule'}
                    </button>
                  )}
                  {composerRecommendation.settings_route && (
                    <button
                      onClick={handleOpenSettings}
                      className="px-3 py-2 border border-white/10 hover:border-white/20 text-[#A0A0A0] hover:text-white text-[10px] font-mono uppercase tracking-wider transition-colors"
                      data-testid="preflight-open-settings-button"
                    >
                      Connect GitHub
                    </button>
                  )}
                </div>
              </div>
            </div>
          )}

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
