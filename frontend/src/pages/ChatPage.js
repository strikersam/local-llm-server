import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { chatSend, listSessions, getSession, deleteSession, listProviders, listProviderModels, getAgentChatJob, cancelAgentChatJob, getGithubStatus, createTask, createSchedule, fmtErr, getBackendUrl } from '../api';
import { Send, Plus, Trash2, MessageSquare, Bot, User, Loader2, Zap, Clock, Settings, X, ChevronDown, AlertCircle, History } from 'lucide-react';
import AgentStatusPanel from '../components/AgentStatusPanel.jsx';
import AgentActivityFeed from '../components/AgentActivityFeed.jsx';
import ToolCallViewer from '../components/ToolCallViewer.jsx';
import { fetchAgentWorkspaceSnapshot } from '../utils/agentWorkspaceTransport';

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
      <div className="w-7 h-7 bg-[var(--accent)] flex items-center justify-center shrink-0">
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
                className="w-1.5 h-1.5 rounded-full bg-[var(--accent)]"
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
        className="w-full md:max-w-md app-modal-sheet md:rounded-[28px] flex flex-col overflow-hidden max-h-[90vh]"
        onClick={e => e.stopPropagation()}
      >
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10 shrink-0">
          <span className="text-sm font-bold font-mono tracking-wide">Select Provider &amp; Model</span>
          <button onClick={onClose} className="text-[#737373] hover:text-white transition-colors p-1 min-h-[2.5rem] min-w-[2.5rem] flex items-center justify-center rounded-full">
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
                  ? 'border-[var(--accent)] bg-[rgba(93,162,255,0.15)] text-white'
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
                className={`w-full flex items-center justify-between rounded-[18px] px-4 py-3 border text-left transition-colors ${
                  pickerModel === m
                    ? 'border-[var(--accent)] bg-[rgba(93,162,255,0.08)]'
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
            className="app-button-secondary flex-1 rounded-full text-[0.7rem]"
          >
            Cancel
          </button>
          <button
            disabled={!pickerModel}
            onClick={() => onConfirm(pickerProvider, pickerModel)}
            className="app-button-primary flex-1 rounded-full text-[0.7rem] disabled:opacity-40 disabled:cursor-not-allowed"
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
      <div className="w-full max-w-lg app-panel-elevated overflow-hidden">
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
                  className="px-2.5 py-1 rounded-full border border-[rgba(93,162,255,0.25)] bg-[rgba(93,162,255,0.08)] text-[10px] font-mono text-[var(--accent)]"
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
            className="app-button-secondary flex-1 rounded-full text-[0.7rem]"
            data-testid="commercial-approval-cancel-button"
          >
            Stay on local/free
          </button>
          <button
            onClick={onApprove}
            className="app-button-primary flex-1 rounded-full text-[0.7rem]"
            data-testid="commercial-approval-approve-button"
          >
            Approve this request
          </button>
        </div>
      </div>
    </div>
  );
}

/**
 * Render the full chat page UI including session list/selection, message composer, model/provider controls, agent orchestration console, and workflow suggestions.
 *
 * This component manages session loading, provider/model persistence, message sending (including agent jobs and polling), live agent workspace snapshots, commercial-fallback approval flow, and creation of tasks/schedules from suggestions; it coordinates related modals, panels, and client-side state for the chat experience.
 *
 * @returns {JSX.Element} The ChatPage React element containing the chat UI and its related controls.
 */
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
  const [githubStatus, setGithubStatus] = useState({ connected: false, login: '' });
  const [workflowAction, setWorkflowAction] = useState('');
  const [agentSnapshot, setAgentSnapshot] = useState(emptyAgentSnapshot);
  const [agentConsoleTab, setAgentConsoleTab] = useState('progress');
  const [agentWorkspaceState, setAgentWorkspaceState] = useState('idle');
  const [agentWorkspaceError, setAgentWorkspaceError] = useState('');
  const [mobileAgentConsoleOpen, setMobileAgentConsoleOpen] = useState(false);
  const [showSessionsSheet, setShowSessionsSheet] = useState(false);

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

  useEffect(() => { loadSessions(); loadProviders(); loadGithubAccess(); }, []); // eslint-disable-line
  useEffect(() => { if (paramSid) loadSession(paramSid); }, [paramSid]); // eslint-disable-line
  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages]);
  useEffect(() => () => jobPollRef.current && clearInterval(jobPollRef.current), []);
  useEffect(() => { setMobileAgentConsoleOpen(false); }, [sessionId]);
  useEffect(() => {
    if (!inputRef.current) return;
    inputRef.current.style.height = '0px';
    const nextHeight = Math.min(inputRef.current.scrollHeight, 192);
    inputRef.current.style.height = `${Math.max(nextHeight, 52)}px`;
  }, [input]);

  const startJobPolling = (jobId) => {
    if (jobPollRef.current) clearInterval(jobPollRef.current);
    jobPollRef.current = setInterval(async () => {
      try {
        const { data } = await getAgentChatJob(jobId);
        setAgentJob(data);
        if (['succeeded', 'failed', 'cancelled'].includes(data.status)) {
          clearInterval(jobPollRef.current);
          jobPollRef.current = null;
          // Extract a human-friendly assistant message from the job result.
          const extractAssistantMessage = (job) => {
            if (!job) return null;
            // Prefer normalized response
            if (job.result?.response) return job.result.response;
            // Fallbacks into common runtime keys
            const raw = job.result?.raw || job.result || {};
            return raw?.response || raw?.summary || raw?.report || raw?.output || raw?.metadata?.agent_comment || null;
          };
          const assistantMsg = extractAssistantMessage(data);
          if (data.status === 'succeeded' && assistantMsg) {
            setMessages(prev => [...prev, { role: 'assistant', content: assistantMsg }]);
            loadSessions();
          } else if (data.status === 'succeeded' && !assistantMsg) {
            // No usable assistant text produced — show structured summary instead of raw JSON
            const summary = data.result?.raw?.summary || data.result?.raw?.report || data.result?.raw?.output || 'Agent completed with no textual summary.';
            setMessages(prev => [...prev, { role: 'assistant', content: summary }]);
            loadSessions();
          } else if (data.status !== 'succeeded') {
            setMessages(prev => [...prev, {
              role: 'assistant',
              content: `Agent job ${data.status}: ${data.error?.message || 'Execution stopped.'}`,
              isError: true,
            }]);
          }
        }
      } catch {
        clearInterval(jobPollRef.current);
        jobPollRef.current = null;
      }
    }, 1500);
  };

  useEffect(() => {
    if (!sessionId) {
      setAgentSnapshot(emptyAgentSnapshot());
      return undefined;
    }

    let cancelled = false;

    const loadAgentSnapshot = async () => {
      try {
        const data = await fetchAgentWorkspaceSnapshot(sessionId);
        if (!cancelled) {
          setAgentSnapshot(data);
          setAgentWorkspaceState('connected');
          setAgentWorkspaceError('');
        }
      } catch (error) {
        if (!cancelled) {
          setAgentSnapshot(emptyAgentSnapshot());
          setAgentWorkspaceState(error?.code === 'auth' ? 'auth_error' : 'reconnecting');
          setAgentWorkspaceError(error instanceof Error ? error.message : 'Live agent workspace is reconnecting.');
        }
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
      if (data.job_id) {
        setAgentJob(data);
        startJobPolling(data.job_id);
      } else {
        setMessages(prev => [...prev, {
          role: 'assistant',
          content: data.response,
          agentHandoff: data.assistant_meta || null,
        }]);
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
        isError: true,
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
    navigate('/settings', { state: { from: sessionId ? `/chat/${sessionId}` : '/chat' } });
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
        isError: true,
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
        isError: true,
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
  const composerRecommendation = !agentMode
    ? detectAgentModeRecommendation(input, githubStatus.connected)
    : null;
  const composerTaskSuggestion = composerRecommendation?.workflow_suggestions?.find((suggestion) => suggestion.kind === 'task');
  const composerScheduleSuggestion = composerRecommendation?.workflow_suggestions?.find((suggestion) => suggestion.kind === 'schedule');
  const showAgentConsole = Boolean(
    sessionId && (
      sending ||
      agentMode ||
      agentWorkspaceState === 'reconnecting' ||
      agentWorkspaceState === 'auth_error' ||
      agentSnapshot.has_events ||
      agentSnapshot.agents.length ||
      agentSnapshot.tool_calls.length ||
      agentSnapshot.latest_summary ||
      agentSnapshot.latest_error
    )
  );

  const renderAgentConsolePanel = () => (
    <div className="rounded-[28px] border border-white/10 bg-[#11151D]/90 shadow-[0_16px_50px_rgba(0,0,0,0.28)] backdrop-blur-xl overflow-hidden" data-testid="agent-console">
      <div className="flex items-center justify-between gap-3 px-4 py-3 border-b border-white/10 bg-white/[0.03]">
        <div>
          <div className="text-[10px] font-mono uppercase tracking-[0.2em] text-[var(--accent)]">Live agent workspace</div>
          <div className="text-xs text-white mt-1">
            {agentWorkspaceError
              ? agentWorkspaceError
              : agentSnapshot.latest_error
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
                ? 'border-[rgba(93,162,255,0.6)] bg-[rgba(93,162,255,0.15)] text-white'
                : 'border-white/10 text-[#737373]'
            }`}
          >
            {label}
          </button>
        ))}
      </div>

      {agentWorkspaceState === 'reconnecting' && (
        <div className="mx-4 mt-3 rounded-md border border-amber-400/20 bg-amber-400/10 px-3 py-2 text-[11px] text-amber-200" data-testid="agent-workspace-reconnect-banner">
          Reconnecting live agent updates…
        </div>
      )}

      {agentWorkspaceState === 'auth_error' && (
        <div className="mx-4 mt-3 rounded-md border border-red-500/20 bg-red-500/10 px-3 py-2 text-[11px] text-red-200" data-testid="agent-workspace-auth-banner">
          Agent workspace session expired. Sign in again to restore live agent updates.
        </div>
      )}

      <div className="p-3 md:p-4 md:grid md:grid-cols-2 md:gap-4 space-y-3 md:space-y-0">
        <div className={`${agentConsoleTab !== 'progress' ? 'hidden md:block' : ''}`}>
          <AgentStatusPanel
            sessionId={sessionId}
            agents={agentSnapshot.agents}
            loading={agentWorkspaceState === 'idle'}
            error={agentWorkspaceState === 'auth_error' ? agentWorkspaceError : null}
            className="h-full min-h-[220px]"
          />
        </div>
        <div className={`${agentConsoleTab !== 'tools' ? 'hidden md:block' : ''}`}>
          <ToolCallViewer toolCalls={agentSnapshot.tool_calls} className="h-full min-h-[220px]" />
        </div>
        <div className={`${agentConsoleTab !== 'activity' ? 'hidden md:block' : ''} md:col-span-2`}>
          <div className="h-[320px] md:h-[360px]">
            <AgentActivityFeed
              sessionId={sessionId}
              className="h-full"
              onConnectionChange={(state) => {
                if (state === 'connected') {
                  setAgentWorkspaceState('connected');
                  setAgentWorkspaceError('');
                } else if (state === 'reconnecting') {
                  setAgentWorkspaceState((current) => current === 'auth_error' ? current : 'reconnecting');
                }
              }}
            />
          </div>
        </div>
      </div>
    </div>
  );

  return (
    <div className="flex h-full min-h-0 overflow-hidden app-shell" data-testid="chat-page">
      {/* Mobile sessions bottom sheet — P3 */}
      {showSessionsSheet && (
        <div
          className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm md:hidden"
          onClick={() => setShowSessionsSheet(false)}
        >
          <div
            className="absolute bottom-0 left-0 right-0 bg-[#0a0c0f] border-t border-white/10 rounded-t-[28px] max-h-[78vh] flex flex-col overflow-hidden"
            onClick={e => e.stopPropagation()}
          >
            <div className="flex items-center justify-between px-5 py-4 border-b border-white/10 shrink-0">
              <span className="text-sm font-bold tracking-tight">Chat History</span>
              <button
                onClick={() => setShowSessionsSheet(false)}
                className="w-10 h-10 flex items-center justify-center text-[#737373] hover:text-white transition-colors rounded-full"
              >
                <X size={16} />
              </button>
            </div>
            <div className="px-4 py-3 border-b border-white/10 shrink-0">
              <button
                onClick={() => { startNew(); setShowSessionsSheet(false); }}
                className="app-button-primary w-full rounded-[18px] text-[0.72rem]"
              >
                <Plus size={14} /> New session
              </button>
            </div>
            <div className="flex-1 overflow-y-auto divide-y divide-white/5">
              {sessions.map(s => (
                <div
                  key={s._id}
                  onClick={() => { navigate(`/chat/${s._id}`); loadSession(s._id); setShowSessionsSheet(false); }}
                  className={`flex items-center gap-2 px-4 py-3 hover:bg-white/[0.03] transition-colors group cursor-pointer
                    ${sessionId === s._id ? 'bg-white/5 border-l-2 border-[var(--accent)]' : 'border-l-2 border-transparent'}`}
                >
                  <MessageSquare size={13} className="text-[#737373] shrink-0" />
                  <div className="flex-1 min-w-0">
                    <div className="text-xs text-[#A0A0A0] truncate">{s.title || 'Untitled'}</div>
                    <div className="text-[10px] text-[#737373]">{s.updated_at?.split('T')[0]}</div>
                  </div>
                  <button
                    onClick={e => handleDelete(s._id, e)}
                    className="p-2.5 min-h-[44px] min-w-[44px] flex items-center justify-center hover:text-[#FF3333] text-[#737373] transition-all opacity-0 group-hover:opacity-100"
                  >
                    <Trash2 size={12} />
                  </button>
                </div>
              ))}
              {sessions.length === 0 && (
                <div className="p-8 text-center text-xs text-[#737373]">No sessions yet</div>
              )}
            </div>
          </div>
        </div>
      )}

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
      <aside className="w-72 border-r border-white/10 bg-[rgba(10,12,15,0.94)] flex-col shrink-0 hidden md:flex backdrop-blur-xl">
        <div className="p-4 border-b border-white/10">
          <button
            onClick={startNew}
            className="app-button-primary w-full rounded-[18px] text-[0.72rem]"
            data-testid="new-chat-button"
          >
            <Plus size={14} /> New session
          </button>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-white/5">
          {sessions.map(s => (
            <div
              key={s._id}
              onClick={() => { navigate(`/chat/${s._id}`); loadSession(s._id); }}
              className={`w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-white/[0.03] transition-colors group cursor-pointer
                ${sessionId === s._id ? 'bg-white/5 border-l-2 border-[var(--accent)]' : 'border-l-2 border-transparent'}`}
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
      </aside>

      {/* Chat area */}
      <div className="flex-1 flex flex-col min-w-0 min-h-0">

        {/* ── Header ── */}
        <div className="sticky top-0 z-20 border-b border-white/10 bg-[rgba(5,6,8,0.88)] backdrop-blur-xl">
          {/* Row 1 — session identity */}
          <div className="px-4 pt-3 pb-2 md:px-6 flex items-center gap-2.5">
            <button
              onClick={() => setShowSessionsSheet(true)}
              className="md:hidden flex items-center justify-center w-10 h-10 rounded-xl border border-white/10 bg-white/[0.03] text-[#737373] hover:text-white transition-colors shrink-0"
              aria-label="Chat history"
            >
              <History size={15} />
            </button>
            <Bot size={15} className="text-[var(--accent)] shrink-0 hidden md:block" />
            <span className="text-xs tracking-[0.12em] uppercase text-[#A0A0A0] font-mono font-bold flex-1 truncate min-w-0">
              {currentSession ? currentSession.title?.slice(0, 44) : 'New Chat Session'}
            </span>
            <button
              onClick={startNew}
              className="flex items-center justify-center w-10 h-10 rounded-xl bg-[var(--accent)] text-[#06111f] hover:bg-[var(--accent-hover)] transition-colors shrink-0 shadow-[0_4px_14px_rgba(93,162,255,0.25)]"
              aria-label="New chat"
              data-testid="new-chat-header-button"
            >
              <Plus size={15} />
            </button>
          </div>
          {/* Row 2 — model & agent controls */}
          <div className="px-4 pb-2.5 md:px-6 flex items-center gap-2 overflow-x-auto scrollbar-hide">
            <div className="flex border border-white/10 rounded-full overflow-hidden shrink-0 bg-white/[0.03]">
              <button
                onClick={() => setMode('auto')}
                className={`flex min-h-[2rem] items-center gap-1 px-2.5 py-1 text-[9px] font-mono uppercase tracking-wider transition-colors ${
                  mode === 'auto'
                    ? 'bg-[rgba(93,162,255,0.15)] border-r border-[rgba(93,162,255,0.3)] text-white'
                    : 'border-r border-white/10 text-[#737373] hover:text-[#A0A0A0]'
                }`}
                title="Model routing: Auto lets the backend pick the best available model"
              >
                <Zap size={9} className={mode === 'auto' ? 'text-[var(--accent)]' : 'text-[#737373]'} />
                Auto
              </button>
              <button
                onClick={() => setMode('manual')}
                className={`flex min-h-[2rem] items-center gap-1 px-2.5 py-1 text-[9px] font-mono uppercase tracking-wider transition-colors ${
                  mode === 'manual'
                    ? 'bg-[rgba(93,162,255,0.15)] text-white'
                    : 'text-[#737373] hover:text-[#A0A0A0]'
                }`}
                title="Model routing: Manual — choose your provider and model"
              >
                <Settings size={9} className={mode === 'manual' ? 'text-[var(--accent)]' : 'text-[#737373]'} />
                Manual
              </button>
            </div>
            {mode === 'manual' && (
              <button
                onClick={() => setShowPicker(true)}
                className="flex min-h-[2rem] items-center gap-1 rounded-full px-2.5 py-1 border border-white/10 hover:border-white/20 text-[9px] font-mono text-[#A0A0A0] hover:text-white transition-colors shrink-0"
                data-testid="change-model-btn"
              >
                <span className="truncate max-w-[130px]">
                  {model ? `${short(providerName, 10)} · ${short(model, 14)}` : 'Select model'}
                </span>
                <ChevronDown size={9} />
              </button>
            )}
            <div className="flex-1 min-w-0" />
            <div className="hidden lg:flex items-center gap-1.5 text-[9px] font-mono text-[#737373] shrink-0">
              <span className={`w-1.5 h-1.5 rounded-full ${githubStatus.connected ? 'bg-green-500' : 'bg-[#444]'}`} />
              <span>{githubStatus.connected ? `GitHub · ${githubStatus.login || 'connected'}` : 'GitHub not connected'}</span>
            </div>
            <button
              onClick={() => setAgentMode(m => !m)}
              title={agentMode ? 'Agent ON — Plan→Execute→Verify loop. Click to disable.' : 'Agent OFF — direct chat. Enable for code or GitHub tasks.'}
              className={`flex min-h-[2rem] items-center gap-1 rounded-full px-2.5 py-1 border text-[9px] font-mono transition-colors shrink-0 ${
                agentMode
                  ? 'border-[rgba(93,162,255,0.5)] bg-[rgba(93,162,255,0.15)] text-white'
                  : 'border-white/15 bg-white/5 text-[#737373] hover:border-white/25 hover:text-[#A0A0A0]'
              }`}
            >
              <Zap size={9} className={agentMode ? 'text-[var(--accent)]' : 'text-[#737373]'} />
              Agent {agentMode ? 'ON' : 'OFF'}
            </button>
            <div className={`w-1.5 h-1.5 rounded-full shrink-0 ${agentMode ? 'bg-green-500' : 'bg-[#444]'}`} />
          </div>
        </div>

        {agentJob && (
          <div className="px-4 md:px-6 py-3 border-b border-white/10 bg-[rgba(17,20,25,0.72)]">
            <div className="app-panel p-3 md:p-4 flex flex-col gap-2 md:flex-row md:items-center md:justify-between">
              <div className="min-w-0">
                <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[var(--accent)]">Agent job</div>
                <div className="mt-1 text-sm text-white">{agentJob.status} · {agentJob.phase}</div>
                <div className="mt-1 text-[11px] text-[#A0A0A0] leading-relaxed">
                  {(agentJob.progress_events || []).slice(-1)[0]?.message || 'Waiting for progress...'}
                </div>
              </div>
              {['queued', 'running'].includes(agentJob.status) && (
                <button
                  onClick={handleCancelAgentJob}
                  className="app-button-secondary self-start md:self-auto rounded-full text-[0.7rem]"
                >
                  Cancel
                </button>
              )}
            </div>
          </div>
        )}

        {showAgentConsole && (
          <>
            <div className="hidden md:block px-3 pt-3 md:px-6 md:pt-4">
              {renderAgentConsolePanel()}
            </div>
            <div className="px-4 pt-3 md:hidden">
              <button
                type="button"
                onClick={() => setMobileAgentConsoleOpen(true)}
                className="w-full rounded-[24px] border border-[rgba(93,162,255,0.25)] bg-[rgba(17,20,25,0.88)] px-4 py-3 text-left"
              >
                <div className="flex items-center justify-between gap-3">
                  <div>
                    <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[var(--accent)]">Live agent workspace</div>
                    <div className="mt-1 text-xs text-white">{agentJob?.phase || agentSnapshot.latest_summary || 'Open progress, activity, and tool usage'}</div>
                  </div>
                  <div className="text-[10px] font-mono text-[#A0A0A0]">Open</div>
                </div>
              </button>
            </div>
            {mobileAgentConsoleOpen && (
              <div className="fixed inset-0 z-40 bg-black/70 backdrop-blur-sm p-3 pt-[calc(env(safe-area-inset-top,0px)+0.75rem)] pb-[calc(env(safe-area-inset-bottom,0px)+0.75rem)] md:hidden">
                <div className="flex h-full flex-col gap-3">
                  <div className="flex items-center justify-between px-1">
                    <div className="text-xs font-mono uppercase tracking-[0.18em] text-white">Agent workspace</div>
                    <button type="button" onClick={() => setMobileAgentConsoleOpen(false)} className="text-[11px] font-mono uppercase tracking-[0.16em] text-[#A0A0A0]">Close</button>
                  </div>
                  <div className="min-h-0 flex-1 overflow-y-auto">
                    {renderAgentConsolePanel()}
                  </div>
                </div>
              </div>
            )}
          </>
        )}
        {/* ── Messages ── */}
        <div className="flex-1 overflow-y-auto overscroll-contain px-4 pb-24 pt-4 md:px-6 md:pb-32 md:pt-6 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center animate-fade-in px-4">
              <Bot size={40} className="text-[var(--accent)] mb-4" />
              <h3 className="text-lg font-bold tracking-tight mb-2" style={{ fontFamily: 'var(--font-main)' }}>
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
                    className="text-[10px] text-[#A0A0A0] border border-white/10 px-3 py-2 hover:border-[var(--accent)] hover:text-white transition-all font-mono text-left"
                    data-testid={`quick-prompt-${i}`}
                  >
                    {p}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 items-end ${m.role === 'user' ? 'justify-end' : ''} animate-fade-in`}>
              {m.role === 'assistant' && (
                <div className={`w-7 h-7 flex items-center justify-center shrink-0 mt-1 ${m.isError ? 'bg-red-500/20 rounded-full' : 'bg-[var(--accent)]'}`}>
                  {m.isError ? <AlertCircle size={13} className="text-red-400" /> : <Bot size={14} />}
                </div>
              )}
              <div className={`max-w-[88%] md:max-w-[70%] rounded-[24px] ${
                m.isError
                  ? 'bg-red-500/[0.07] border border-red-500/25'
                  : m.role === 'user'
                    ? 'bg-[rgba(93,162,255,0.15)] border border-[rgba(93,162,255,0.3)]'
                    : 'bg-[#151922] border border-white/10'
              } px-4 py-3 shadow-[0_12px_36px_rgba(0,0,0,0.18)]`}>
                {m.role === 'assistant' ? (
                  <>
                    {m.isError ? (
                      <div className="space-y-2.5">
                        <div className="flex items-start gap-2">
                          <AlertCircle size={13} className="text-red-400 shrink-0 mt-0.5" />
                          <p className="text-xs text-red-300 leading-relaxed">{m.content.replace(/^Error:\s*/i, '')}</p>
                        </div>
                        <button
                          onClick={handleSend}
                          className="text-[9px] font-mono uppercase tracking-wider text-red-400/80 border border-red-500/20 px-2.5 py-1 rounded-full hover:bg-red-500/10 transition-colors"
                        >
                          Retry last message
                        </button>
                      </div>
                    ) : (<>
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
                            className="px-3 py-2 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-[10px] font-mono uppercase tracking-wider transition-colors"
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
                    </>)}
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
        <div className="sticky bottom-0 z-20 border-t border-white/10 p-3 md:p-4 bg-[rgba(5,6,8,0.92)] backdrop-blur-xl pb-[calc(env(safe-area-inset-bottom,0px)+0.75rem)]">
          {composerRecommendation && (
            <div className="mb-3 border border-[rgba(93,162,255,0.3)] bg-[rgba(93,162,255,0.08)] px-3 py-3" data-testid="agent-mode-preflight-banner">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="text-[10px] font-mono uppercase tracking-[0.18em] text-[var(--accent)]">
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
                    className="px-3 py-2 bg-[var(--accent)] hover:bg-[var(--accent-hover)] text-white text-[10px] font-mono uppercase tracking-wider transition-colors"
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
                <Zap size={9} className="text-[var(--accent)]" /> {agentMode ? 'Agent mode active' : 'Auto routing active'}
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

          <div className="app-panel rounded-[28px] px-3 py-3 flex gap-3 items-end">
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
              className="flex-1 min-h-[52px] max-h-48 overflow-y-auto bg-transparent border-0 px-3 py-2 text-sm text-white font-mono outline-none resize-none transition-colors"
              data-testid="chat-input"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending || (mode === 'manual' && !model)}
              className="app-button-primary rounded-full min-h-[3rem] min-w-[3rem] px-4 shrink-0 flex items-center gap-2"
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
