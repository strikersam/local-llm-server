/**
 * SetupWizardPage.js — First-run Setup Wizard (5 steps)
 *
 * Steps:
 *   1 Provider Setup      — select Ollama / cloud providers
 *   2 Local Models        — detect hardware + pick default models
 *   3 Runtime Config      — enable/configure runtimes
 *   4 Default Agent       — configure your default agent
 *   5 Policy Preferences  — cost / privacy / escalation settings
 *
 * Shown automatically on first login; can be re-opened from Settings.
 *
 * Persistence:
 *   - Saved to backend via /api/setup/state (per authenticated user)
 *   - Also cached in localStorage as draft for offline/GitHub-Pages resilience
 *   - On load: backend wins; falls back to localStorage draft if no backend
 */

import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import {
  getSetupState,
  saveSetupStep,
  completeSetup,
  detectHardwareForSetup,
  detectModelsForSetup,
  createSecret,
  getBackendUrl,
  setBackendUrl,
  getPublicPath,
} from '../api';

// ─── localStorage draft helpers ──────────────────────────────────────────────

const SETUP_DRAFT_KEY = 'llm_relay_setup_draft';

function saveDraft(data) {
  try { localStorage.setItem(SETUP_DRAFT_KEY, JSON.stringify(data)); } catch {}
}

function loadDraft() {
  try {
    const s = localStorage.getItem(SETUP_DRAFT_KEY);
    return s ? JSON.parse(s) : null;
  } catch { return null; }
}

// ─── Constants ────────────────────────────────────────────────────────────────

const STEPS = [
  { num: 1, title: 'Provider Setup',     icon: '🔌' },
  { num: 2, title: 'Model Selection',    icon: '🧠' },
  { num: 3, title: 'Runtime Config',     icon: '⚙️' },
  { num: 4, title: 'Default Agent',      icon: '🤖' },
  { num: 5, title: 'Policy & Privacy',   icon: '🛡️' },
];

// Nvidia NIM free models
const NVIDIA_MODELS = {
  executor: 'qwen/qwen2.5-coder-32b-instruct',
  planner:  'nvidia/nemotron-3-super-120b-a12b',
  verifier: 'nvidia/nemotron-3-super-120b-a12b',
  default:  'nvidia/nemotron-3-super-120b-a12b',
};
const LOCAL_MODELS = {
  executor: 'qwen3-coder:30b',
  planner:  'deepseek-r1:32b',
  verifier: 'deepseek-r1:32b',
  default:  'qwen3-coder:30b',
};
const DEFAULT_LANGFUSE_HOST = process.env.REACT_APP_LANGFUSE_BASE_URL || process.env.REACT_APP_LANGFUSE_HOST || 'https://cloud.langfuse.com';

const pill = (label, color = 'green') =>
  `inline-block px-2 py-0.5 rounded text-xs font-semibold bg-${color}-100 text-${color}-800`;

// ─── Component ────────────────────────────────────────────────────────────────

export default function SetupWizardPage({ onComplete }) {
  const navigate = useNavigate();
  const [step, setStep] = useState(1);
  const [showStepMenu, setShowStepMenu] = useState(false);
  const [saving, setSaving] = useState(false);
  const [hardware, setHardware] = useState(null);
  const [models, setModels] = useState([]);
  const [done, setDone] = useState(false);
  const [setupAlreadyCompleted, setSetupAlreadyCompleted] = useState(false);
  const [saveNotice, setSaveNotice] = useState('');
  const [loadingState, setLoadingState] = useState(false);

  // Backend connection
  const [backendUrl, setBackendUrlState] = useState(getBackendUrl);
  const [backendUrlInput, setBackendUrlInput] = useState(getBackendUrl() || 'http://localhost:8000');
  const [backendConnected, setBackendConnected] = useState(false);
  const [checkingBackend, setCheckingBackend] = useState(false);
  const [connectError, setConnectError] = useState('');

  // Step 1 — Providers
  const [useNvidiaNim, setUseNvidiaNim] = useState(true); // default ON — free, no infra needed
  const [nvidiaKeyConfigured, setNvidiaKeyConfigured] = useState(false); // key already set server-side
  const [useOllama, setUseOllama] = useState(false);
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [useOpenAI, setUseOpenAI] = useState(false);
  const [openaiKey, setOpenaiKey] = useState('');
  const [openaiSecretId, setOpenaiSecretId] = useState(null);
  const [useAnthropic, setUseAnthropic] = useState(false);
  const [anthropicKey, setAnthropicKey] = useState('');
  const [anthropicSecretId, setAnthropicSecretId] = useState(null);
  const [useGoogle, setUseGoogle] = useState(false);
  const [googleKey, setGoogleKey] = useState('');
  const [googleSecretId, setGoogleSecretId] = useState(null);
  const [useAzure, setUseAzure] = useState(false);
  const [azureKey, setAzureKey] = useState('');
  const [azureSecretId, setAzureSecretId] = useState(null);
  const [useCopilot, setUseCopilot] = useState(false);
  const [copilotKey, setCopilotKey] = useState('');
  const [copilotSecretId, setCopilotSecretId] = useState(null);

  // Step 2 — Models (defaults set to Nvidia NIM; adjusted when state loads)
  const [defaultModel, setDefaultModel] = useState(NVIDIA_MODELS.default);
  const [reviewerModel, setReviewerModel] = useState(NVIDIA_MODELS.verifier);
  const [repoPath, setRepoPath] = useState('');
  const [modelsPath, setModelsPath] = useState('');
  const [daemonConnected, setDaemonConnected] = useState(false);
  const [daemonChecking, setDaemonChecking] = useState(false);
  const [proxyRunning, setProxyRunning] = useState(false);
  const [tunnelRunning, setTunnelRunning] = useState(false);

  // Step 3 — Runtimes
  const [enableHermes, setEnableHermes] = useState(true);
  const [enableOpenCode, setEnableOpenCode] = useState(false);
  const [enableTaskHarness, setEnableTaskHarness] = useState(false);
  const [enableAider, setEnableAider] = useState(false);

  // Step 4 — Agent
  const [agentName, setAgentName] = useState('My Agent');
  const [agentModel, setAgentModel] = useState(NVIDIA_MODELS.default);
  const [costPolicy, setCostPolicy] = useState('free_only');

  // Step 5 — Policy
  const [neverPaid, setNeverPaid] = useState(true);
  const [requireApproval, setRequireApproval] = useState(true);
  const [enableLangfuse, setEnableLangfuse] = useState(false);
  const [langfuseHost, setLangfuseHost] = useState(DEFAULT_LANGFUSE_HOST);

  // ─── State population helpers ───────────────────────────────────────────────

  const applyWizardState = useCallback((state) => {
    const p   = state.step1_providers || {};
    const m   = state.step2_model     || {};
    const rt  = state.step3_runtimes  || {};
    const a   = state.step4_agent     || {};
    const pol = state.step5_policy    || {};

    if (Object.keys(p).length) {
      const nvidia = p.use_nvidia_nim ?? true;
      setUseNvidiaNim(nvidia);
      setNvidiaKeyConfigured(p.nvidia_key_configured ?? false);
      setUseOllama(p.use_ollama ?? false);
      setOllamaUrl(p.ollama_base_url || 'http://localhost:11434');
      setRepoPath(p.repo_path || '');
      setModelsPath(p.models_path || '');
      setUseOpenAI(p.use_openai ?? false);
      setOpenaiSecretId(p.openai_secret_id || null);
      setUseAnthropic(p.use_anthropic ?? false);
      setAnthropicSecretId(p.anthropic_secret_id || null);
      setUseGoogle(p.use_google ?? false);
      setGoogleSecretId(p.google_secret_id || null);
      setUseAzure(p.use_azure ?? false);
      setAzureSecretId(p.azure_secret_id || null);
      setUseCopilot(p.use_copilot ?? false);
      setCopilotSecretId(p.copilot_secret_id || null);
    }
    if (Object.keys(m).length) {
      const nvidia = p.use_nvidia_nim ?? true;
      const models = nvidia ? NVIDIA_MODELS : LOCAL_MODELS;
      setDefaultModel(m.default_model || models.default);
      setReviewerModel(m.reviewer_model || models.verifier);
    }
    if (Object.keys(rt).length) {
      setEnableHermes(rt.enable_hermes ?? true);
      setEnableOpenCode(rt.enable_opencode ?? false);
      setEnableTaskHarness(rt.enable_task_harness ?? false);
      setEnableAider(rt.enable_aider ?? false);
    }
    if (Object.keys(a).length) {
      setAgentName(a.agent_name || 'My Agent');
      setAgentModel(a.agent_model || NVIDIA_MODELS.default);
      setCostPolicy(a.cost_policy || 'free_only');
    }
    if (Object.keys(pol).length) {
      setNeverPaid(pol.never_use_paid_providers ?? true);
      setRequireApproval(pol.require_approval_before_paid ?? true);
      setEnableLangfuse(pol.enable_langfuse ?? false);
      setLangfuseHost(current => pol.langfuse_host || current || DEFAULT_LANGFUSE_HOST);
    }
  }, []);

  const applyDraftState = useCallback((draft) => {
    if (!draft) return;
    const p   = draft.step1 || {};
    const m   = draft.step2 || {};
    const rt  = draft.step3 || {};
    const a   = draft.step4 || {};
    const pol = draft.step5 || {};

    if (p.useNvidiaNim !== undefined)   setUseNvidiaNim(p.useNvidiaNim);
    if (p.useOllama !== undefined)     setUseOllama(p.useOllama);
    if (p.ollamaUrl)                   setOllamaUrl(p.ollamaUrl);
    if (p.repoPath !== undefined)      setRepoPath(p.repoPath || '');
    if (p.modelsPath !== undefined)    setModelsPath(p.modelsPath || '');
    if (p.useOpenAI !== undefined)     setUseOpenAI(p.useOpenAI);
    if (p.openaiSecretId)              setOpenaiSecretId(p.openaiSecretId);
    if (p.useAnthropic !== undefined)  setUseAnthropic(p.useAnthropic);
    if (p.anthropicSecretId)           setAnthropicSecretId(p.anthropicSecretId);
    if (p.useGoogle !== undefined)     setUseGoogle(p.useGoogle);
    if (p.googleSecretId)              setGoogleSecretId(p.googleSecretId);
    if (p.useAzure !== undefined)      setUseAzure(p.useAzure);
    if (p.azureSecretId)               setAzureSecretId(p.azureSecretId);
    if (p.useCopilot !== undefined)    setUseCopilot(p.useCopilot);
    if (p.copilotSecretId)             setCopilotSecretId(p.copilotSecretId);

    if (m.defaultModel)   setDefaultModel(m.defaultModel);
    if (m.reviewerModel)  setReviewerModel(m.reviewerModel);

    if (rt.enableHermes   !== undefined) setEnableHermes(rt.enableHermes);
    if (rt.enableOpenCode !== undefined) setEnableOpenCode(rt.enableOpenCode);
    if (rt.enableTaskHarness   !== undefined) setEnableTaskHarness(rt.enableTaskHarness);
    if (rt.enableAider    !== undefined) setEnableAider(rt.enableAider);

    if (a.agentName)                   setAgentName(a.agentName);
    if (a.agentModel)                  setAgentModel(a.agentModel);
    if (a.costPolicy)                  setCostPolicy(a.costPolicy);

    if (pol.neverPaid        !== undefined) setNeverPaid(pol.neverPaid);
    if (pol.requireApproval  !== undefined) setRequireApproval(pol.requireApproval);
    if (pol.enableLangfuse   !== undefined) setEnableLangfuse(pol.enableLangfuse);
    if (pol.langfuseHost)                   setLangfuseHost(pol.langfuseHost);
  }, []);

  const loadSavedState = useCallback(async () => {
    setLoadingState(true);
    try {
      const r = await getSetupState();
      const state = r.data;
      if (state.completed) {
        setSetupAlreadyCompleted(true);
      }
      setDone(false);
      setStep(state.current_step || (state.completed ? 5 : 1));
      applyWizardState(state);
    } catch {
      // Backend unavailable — fall back to localStorage draft
      const draft = loadDraft();
      if (draft) {
        applyDraftState(draft);
        if (draft.currentStep) setStep(draft.currentStep);
      }
    } finally {
      setLoadingState(false);
    }
  }, [onComplete, applyWizardState, applyDraftState]);

  // ─── Backend connection ─────────────────────────────────────────────────────

  const testBackendConnection = useCallback(async (url) => {
    setCheckingBackend(true);
    setConnectError('');
    try {
      const r = await fetch(`${url.replace(/\/$/, '')}/api/health`);
      if (r.ok) {
        setBackendUrl(url);
        setBackendUrlState(url);
        setBackendConnected(true);
        setCheckingBackend(false);
        return true;
      }
      setConnectError(`Backend returned ${r.status}. Check the URL.`);
    } catch (e) {
      const msg = (e.message || '').toLowerCase();
      if (msg.includes('failed to fetch') || msg.includes('networkerror') || msg.includes('cors')) {
        setConnectError(
          `Cannot reach backend at ${url}. ` +
          `If running locally, ensure it's started and CORS allows ${window.location.origin}. ` +
          `If using an ngrok/tunnel URL, verify the tunnel is active.`
        );
      } else {
        setConnectError(`Connection failed: ${e.message}`);
      }
    }
    setBackendConnected(false);
    setCheckingBackend(false);
    return false;
  }, []);

  // ─── Initial load ───────────────────────────────────────────────────────────

  useEffect(() => {
    const url = getBackendUrl() || window.location.origin;
    testBackendConnection(url).then(async connected => {
      if (connected) {
        // Auto-detect server-configured providers (Nvidia key set on Render, etc.)
        try {
          const base = (getBackendUrl() || '').replace(/\/$/, '');
          const r = await fetch(`${base}/api/setup/detect/providers`);
          if (r.ok) {
            const data = await r.json();
            if (data.nvidia_nim?.configured) {
              setNvidiaKeyConfigured(true);
              setUseNvidiaNim(true);
            }
            if (data.langfuse?.host) {
              setLangfuseHost(data.langfuse.host);
            }
          }
        } catch {}
        loadSavedState();
      } else {
        const draft = loadDraft();
        if (draft) {
          applyDraftState(draft);
          if (draft.currentStep) setStep(draft.currentStep);
        }
      }
    });
  }, []); // eslint-disable-line

  // ─── Hardware / model detection (Step 2) ───────────────────────────────────

  const loadHardware = useCallback(async () => {
    try {
      const r = await detectHardwareForSetup();
      setHardware(r.data);
    } catch {}
    try {
      const r2 = await detectModelsForSetup(ollamaUrl);
      setModels(r2.data.models || []);
    } catch {}
  }, [ollamaUrl]);

  // ─── Local daemon (Step 2 — only relevant when running locally) ─────────────

  const isDeployed = window.location.hostname !== 'localhost' &&
                     window.location.hostname !== '127.0.0.1';

  const checkDaemonConnection = useCallback(async () => {
    if (isDeployed) {
      setDaemonConnected(false);
      return;
    }
    setDaemonChecking(true);
    try {
      const r = await fetch('http://localhost:3001/api/status');
      if (r.ok) {
        const data = await r.json();
        setDaemonConnected(true);
        setProxyRunning(data.proxy === 'running');
        setTunnelRunning(data.tunnel === 'running');
      } else {
        setDaemonConnected(false);
      }
    } catch {
      setDaemonConnected(false);
    } finally {
      setDaemonChecking(false);
    }
  }, [isDeployed]);

  const configureDaemon = async () => {
    if (!repoPath || !modelsPath) {
      alert('Please enter both repo and models paths');
      return;
    }
    try {
      const r = await fetch('http://localhost:3001/api/configure', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ repo_path: repoPath, models_path: modelsPath }),
      });
      const data = await r.json();
      if (data.success) {
        await checkDaemonConnection();
      } else {
        alert('Configuration failed: ' + data.message);
      }
    } catch (e) {
      alert('Failed to configure daemon: ' + e.message);
    }
  };

  const startService = async (service) => {
    try {
      const r = await fetch(`http://localhost:3001/api/services/${service}/start`, { method: 'POST' });
      const data = await r.json();
      if (data.success) {
        await checkDaemonConnection();
      } else {
        alert('Failed to start ' + service + ': ' + data.message);
      }
    } catch (e) {
      alert('Error starting service: ' + e.message);
    }
  };

  const stopService = async (service) => {
    try {
      const r = await fetch(`http://localhost:3001/api/services/${service}/stop`, { method: 'POST' });
      const data = await r.json();
      if (data.success) {
        await checkDaemonConnection();
      } else {
        alert('Failed to stop ' + service + ': ' + data.message);
      }
    } catch (e) {
      alert('Error stopping service: ' + e.message);
    }
  };

  useEffect(() => {
    if (step === 2) {
      loadHardware();
      if (useOllama && !isDeployed) checkDaemonConnection();
    }
  }, [step, loadHardware, useOllama, isDeployed, checkDaemonConnection]);

  // ─── API key storage ────────────────────────────────────────────────────────

  const storeApiKey = useCallback(async (key, keyName) => {
    if (!key) return null;
    try {
      // Use the shared axios API instance so auth token + base URL are applied
      // consistently, regardless of what backendUrl state holds.
      const result = await createSecret({
        name: `${keyName}-key-setup`,
        value: key,
        description: `${keyName} API key from setup wizard`,
      });
      return result.data?.id ?? null;
    } catch (e) {
      // Fall back to the setup-specific public endpoint when the secrets API
      // is unreachable (e.g. first-run before auth is configured).
      try {
        const baseUrl = (backendUrl || getBackendUrl() || '').replace(/\/$/, '');
        const response = await fetch(`${baseUrl}/api/setup/secret`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            ...(localStorage.getItem('access_token')
              ? { Authorization: `Bearer ${localStorage.getItem('access_token')}` }
              : {}),
          },
          body: JSON.stringify({
            name: `${keyName}-key-setup`,
            value: key,
            description: `${keyName} API key from setup wizard`,
          }),
        });
        if (!response.ok) {
          const errorData = await response.json().catch(() => ({ detail: response.statusText }));
          throw new Error(errorData.detail || `HTTP ${response.status}`);
        }
        const data = await response.json();
        return data.id ?? null;
      } catch (fallbackErr) {
        console.error(`Failed to store ${keyName} key:`, fallbackErr);
        alert(`Failed to store ${keyName} API key: ${fallbackErr.message}`);
        return null;
      }
    }
  }, [backendUrl]);

  // ─── Persist draft to localStorage ─────────────────────────────────────────

  const persistDraft = useCallback((currentStep) => {
    saveDraft({
      currentStep,
      step1: { useNvidiaNim, useOllama, ollamaUrl, repoPath, modelsPath, useOpenAI, openaiSecretId, useAnthropic, anthropicSecretId, useGoogle, googleSecretId, useAzure, azureSecretId, useCopilot, copilotSecretId },
      step2: { defaultModel, reviewerModel },
      step3: { enableHermes, enableOpenCode, enableTaskHarness, enableAider },
      step4: { agentName, agentModel, costPolicy },
      step5: { neverPaid, requireApproval, enableLangfuse, langfuseHost },
    });
  }, [useNvidiaNim, useOllama, ollamaUrl, repoPath, modelsPath, useOpenAI, openaiSecretId, useAnthropic, anthropicSecretId, useGoogle, googleSecretId, useAzure, azureSecretId, useCopilot, copilotSecretId, defaultModel, reviewerModel, enableHermes, enableOpenCode, enableTaskHarness, enableAider, agentName, agentModel, costPolicy, neverPaid, requireApproval, enableLangfuse, langfuseHost]);

  // ─── Save step ──────────────────────────────────────────────────────────────

  const handleSave = async () => {
    setSaving(true);
    setSaveNotice('');
    try {
      let newOpenaiSecretId = openaiSecretId;
      let newAnthropicSecretId = anthropicSecretId;
      let newGoogleSecretId = googleSecretId;
      let newAzureSecretId = azureSecretId;
      let newCopilotSecretId = copilotSecretId;

      if (useOpenAI && openaiKey && !openaiSecretId) {
        newOpenaiSecretId = await storeApiKey(openaiKey, 'OpenAI');
        if (newOpenaiSecretId) setOpenaiSecretId(newOpenaiSecretId);
      }
      if (useAnthropic && anthropicKey && !anthropicSecretId) {
        newAnthropicSecretId = await storeApiKey(anthropicKey, 'Anthropic');
        if (newAnthropicSecretId) setAnthropicSecretId(newAnthropicSecretId);
      }
      if (useGoogle && googleKey && !googleSecretId) {
        newGoogleSecretId = await storeApiKey(googleKey, 'Google');
        if (newGoogleSecretId) setGoogleSecretId(newGoogleSecretId);
      }
      if (useAzure && azureKey && !azureSecretId) {
        newAzureSecretId = await storeApiKey(azureKey, 'Azure');
        if (newAzureSecretId) setAzureSecretId(newAzureSecretId);
      }
      if (useCopilot && copilotKey && !copilotSecretId) {
        newCopilotSecretId = await storeApiKey(copilotKey, 'Copilot');
        if (newCopilotSecretId) setCopilotSecretId(newCopilotSecretId);
      }

      const payloads = {
        1: { use_nvidia_nim: useNvidiaNim, use_ollama: useOllama, ollama_base_url: ollamaUrl, repo_path: repoPath, models_path: modelsPath, use_openai: useOpenAI, use_anthropic: useAnthropic, use_google: useGoogle, use_azure: useAzure, openai_secret_id: newOpenaiSecretId, anthropic_secret_id: newAnthropicSecretId, google_secret_id: newGoogleSecretId, azure_secret_id: newAzureSecretId, copilot_secret_id: newCopilotSecretId },
        2: { default_model: defaultModel, coder_model: defaultModel, reviewer_model: reviewerModel },
        3: { enable_hermes: enableHermes, enable_opencode: enableOpenCode, enable_task_harness: enableTaskHarness, enable_aider: enableAider },
        4: { agent_name: agentName, agent_model: agentModel, cost_policy: costPolicy },
        5: { never_use_paid_providers: neverPaid, require_approval_before_paid: requireApproval, enable_langfuse: enableLangfuse, langfuse_host: langfuseHost },
      };

      // Always persist to localStorage first (resilient to network issues)
      persistDraft(step);

      if (backendConnected) {
        await saveSetupStep(step, payloads[step]);
      }

      if (step < 5) {
        setStep(s => s + 1);
      } else {
        if (backendConnected) await completeSetup();
        setSetupAlreadyCompleted(true);
        // Clear draft on completion
        try { localStorage.removeItem(SETUP_DRAFT_KEY); } catch {}
        if (setupAlreadyCompleted) {
          setSaveNotice('Saved your setup changes. They will be used the next time you run the control plane.');
        } else {
          setDone(true);
          if (onComplete) onComplete();
        }
      }
    } catch (error) {
      console.error(`[SetupWizard] Error saving Step ${step}:`, error);
      const detail = error.response?.data?.detail || error.message;
      alert(`Failed to save step: ${detail}`);
    } finally {
      setSaving(false);
    }
  };

  // ─── Helpers ────────────────────────────────────────────────────────────────

  const compatClass = (label) => {
    if (!hardware || !label) return '';
    const map = { compatible: 'text-green-600', degraded: 'text-yellow-600', incompatible: 'text-red-600' };
    return map[label] || '';
  };

  // Show backend banner when: no URL configured, OR we have a URL but aren't connected yet
  const showBackendBanner = !backendConnected;

  // ─── Done screen ────────────────────────────────────────────────────────────

  if (done) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-8">
        <div className="bg-white rounded-2xl shadow-lg p-10 text-center max-w-md">
          <div className="text-5xl mb-4">🎉</div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">You're all set!</h1>
          <p className="text-gray-500 mb-6">Your AI Agent Control Plane is ready to use.</p>
          <button
            onClick={() => navigate(getPublicPath('/'))}
            className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700"
          >
            Open Control Plane →
          </button>
        </div>
      </div>
    );
  }

  // ─── Render ─────────────────────────────────────────────────────────────────

  return (
    <div className="min-h-screen bg-gray-50 flex flex-col lg:flex-row">
      <div className="lg:hidden sticky top-0 z-20 border-b border-indigo-200 bg-white/95 backdrop-blur px-4 py-3 flex items-center justify-between">
        <div>
          <div className="text-sm font-bold text-indigo-950">🧠 Setup Wizard</div>
          <div className="text-[11px] text-indigo-500">Step {step} of {STEPS.length}</div>
        </div>
        <button
          type="button"
          data-testid="mobile-steps-toggle"
          onClick={() => setShowStepMenu(s => !s)}
          className="rounded-lg border border-indigo-200 bg-indigo-50 px-3 py-2 text-xs font-semibold text-indigo-700"
        >
          {showStepMenu ? 'Hide steps' : 'View steps'}
        </button>
      </div>

      {showStepMenu && (
        <div className="lg:hidden border-b border-indigo-200 bg-indigo-900 text-white px-4 py-4 space-y-2">
          {STEPS.map(s => (
            <button
              key={s.num}
              type="button"
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-left transition-colors ${
                step === s.num ? 'bg-indigo-700 text-white' : step > s.num ? 'text-indigo-200' : 'text-indigo-300'
              }`}
              onClick={() => {
                if (step >= s.num) setStep(s.num);
                setShowStepMenu(false);
              }}
            >
              <span className="text-xl">{s.icon}</span>
              <div>
                <div className="text-sm font-medium">Step {s.num}</div>
                <div className="text-xs opacity-80">{s.title}</div>
              </div>
              {step > s.num && <span className="ml-auto text-green-400">✓</span>}
            </button>
          ))}
        </div>
      )}

      {/* Sidebar */}
      <div className="hidden lg:flex w-64 bg-indigo-900 text-white p-6 flex-col">
        <div className="mb-8">
          <div className="text-lg font-bold">🧠 Setup Wizard</div>
          <div className="text-indigo-300 text-sm mt-1">{setupAlreadyCompleted ? 'Update your saved setup anytime' : "Let's get you started"}</div>
        </div>
        <nav className="space-y-1 flex-1">
          {STEPS.map(s => (
            <div
              key={s.num}
              className={`flex items-center gap-3 px-3 py-2.5 rounded-lg cursor-pointer transition-colors ${
                step === s.num ? 'bg-indigo-700 text-white' :
                step > s.num  ? 'text-indigo-300' : 'text-indigo-400'
              }`}
              onClick={() => step > s.num && setStep(s.num)}
            >
              <span className="text-xl">{s.icon}</span>
              <div>
                <div className="text-sm font-medium">Step {s.num}</div>
                <div className="text-xs opacity-70">{s.title}</div>
              </div>
              {step > s.num && <span className="ml-auto text-green-400">✓</span>}
            </div>
          ))}
        </nav>
        <div className="text-indigo-400 text-xs mt-6">v3.1 — AI Control Plane</div>
      </div>

      {/* Main */}
      <div className="flex-1 p-4 sm:p-6 lg:p-8 overflow-auto">
        <div className="max-w-2xl mx-auto">

          {/* Backend connection banner */}
          {showBackendBanner && (
            <div className={`mb-6 p-4 rounded-xl border ${backendConnected ? 'bg-green-50 border-green-200' : 'bg-amber-50 border-amber-300'}`}>
              <div className="flex items-center gap-2 mb-2 font-semibold text-sm">
                <span>{backendConnected ? '🟢' : '🟡'}</span>
                {backendConnected
                  ? `Connected to ${backendUrl}`
                  : 'Connect to your local LLM Server'}
              </div>
              {!backendConnected && (
                <>
                  <p className="text-xs text-gray-600 mb-3">
                    Enter the URL of your running local-llm-server. Use{' '}
                    <code className="bg-white px-1 rounded">http://localhost:8000</code> if
                    running locally, or your ngrok/Cloudflare tunnel URL for remote access.
                  </p>
                  <div className="flex flex-col sm:flex-row gap-2">
                    <input
                      className="flex-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 bg-white focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                      value={backendUrlInput}
                      onChange={e => setBackendUrlInput(e.target.value)}
                      placeholder="http://localhost:8000"
                      onKeyDown={e => {
                        if (e.key === 'Enter') {
                          testBackendConnection(backendUrlInput).then(ok => {
                            if (ok) loadSavedState();
                          });
                        }
                      }}
                    />
                    <button
                      onClick={() => testBackendConnection(backendUrlInput).then(ok => {
                        if (ok) loadSavedState();
                      })}
                      disabled={checkingBackend}
                      className="px-4 py-2 bg-indigo-600 text-white rounded-lg text-sm font-medium hover:bg-indigo-700 disabled:opacity-50"
                    >
                      {checkingBackend ? 'Checking…' : 'Connect'}
                    </button>
                  </div>
                  {connectError && (
                    <div className="mt-2 p-2 bg-red-50 border border-red-200 rounded text-xs text-red-700">
                      ⚠ {connectError}
                    </div>
                  )}
                  <p className="text-xs text-amber-700 mt-2">
                    ⚠ Steps will be saved locally until a backend is connected.
                  </p>
                </>
              )}
            </div>
          )}

          {/* Loading state */}
          {loadingState && (
            <div className="mb-4 flex items-center gap-2 text-sm text-indigo-600">
              <div className="w-4 h-4 border-2 border-indigo-600 border-t-transparent rounded-full animate-spin" />
              Loading your saved configuration…
            </div>
          )}

          {setupAlreadyCompleted && !done && (
            <div className="mb-4 rounded-2xl border border-indigo-200 bg-indigo-50 px-4 py-3 text-sm text-indigo-900">
              <div className="font-semibold">Saved setup loaded</div>
              <p className="mt-1 text-xs leading-relaxed text-indigo-800">
                You can change providers, runtimes, and policy settings here at any time. Save the final step again to persist your updates.
              </p>
            </div>
          )}

          {saveNotice && (
            <div className="mb-4 rounded-2xl border border-green-200 bg-green-50 px-4 py-3 text-sm text-green-800">
              {saveNotice}
            </div>
          )}

          {/* Progress bar */}
          <div className="mb-6">
            <div className="flex justify-between text-xs text-gray-500 mb-1">
              <span>Step {step} of {STEPS.length}</span>
              <span>{STEPS[step-1]?.title}</span>
            </div>
            <div className="h-2 bg-gray-200 rounded-full">
              <div
                className="h-2 bg-indigo-600 rounded-full transition-all"
                style={{ width: `${(step / STEPS.length) * 100}%` }}
              />
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow p-5 sm:p-6 lg:p-8">

            {/* ── Step 1: Provider Setup ─────────────────────────────────── */}
            {step === 1 && (
              <div>
                <h2 className="text-xl font-bold text-gray-800 mb-1">Provider Setup</h2>
                <p className="text-gray-500 text-sm mb-6">Choose which AI providers you want to use. The default is free cloud inference — no local GPU needed.</p>
                <div className="space-y-4">

                  {/* Nvidia NIM — first priority */}
                  <label className={`flex items-center gap-3 p-4 border-2 rounded-xl cursor-pointer transition-colors ${useNvidiaNim ? 'border-green-400 bg-green-50' : 'border-gray-200 hover:border-green-300'}`}>
                    <input type="checkbox" checked={useNvidiaNim} onChange={e => {
                      setUseNvidiaNim(e.target.checked);
                      if (e.target.checked) {
                        setDefaultModel(NVIDIA_MODELS.default);
                        setReviewerModel(NVIDIA_MODELS.verifier);
                        setAgentModel(NVIDIA_MODELS.default);
                        setCostPolicy('free_only');
                      }
                    }} className="w-4 h-4" />
                    <div className="flex-1">
                      <div className="font-medium flex items-center gap-2">
                        🟢 Nvidia NIM
                        <span className="inline-block px-2 py-0.5 rounded text-xs font-semibold bg-green-100 text-green-800">Free</span>
                        <span className="inline-block px-2 py-0.5 rounded text-xs font-semibold bg-indigo-100 text-indigo-800">Recommended</span>
                      </div>
                      <div className="text-sm text-gray-500">Free cloud inference — no local GPU or Ollama required</div>
                      {nvidiaKeyConfigured
                        ? <div className="text-xs text-green-600 mt-1">✓ API key already configured on server — ready to use</div>
                        : <div className="text-xs text-amber-600 mt-1">Set NVIDIA_API_KEY on your Render/server environment to activate</div>
                      }
                    </div>
                  </label>

                  {/* Ollama */}
                  <label className="flex items-center gap-3 p-4 border rounded-xl cursor-pointer hover:border-indigo-400 transition-colors">
                    <input type="checkbox" checked={useOllama} onChange={e => setUseOllama(e.target.checked)} className="w-4 h-4" />
                    <div className="flex-1">
                      <div className="font-medium">🦙 Ollama (Local)</div>
                      <div className="text-sm text-gray-500">Run models locally on this machine (optional fallback)</div>
                    </div>
                  </label>
                  {useOllama && (
                    <div className="ml-8 space-y-3">
                      <div>
                        <label className="text-sm font-medium text-gray-700">Ollama URL</label>
                        <input
                          className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                          value={ollamaUrl}
                          onChange={e => setOllamaUrl(e.target.value)}
                          placeholder="http://localhost:11434"
                        />
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700">Repository Folder</label>
                        <input
                          className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                          value={repoPath}
                          onChange={e => setRepoPath(e.target.value)}
                          placeholder="/path/to/local-llm-server"
                        />
                        <p className="text-xs text-gray-400 mt-0.5">Folder where local-llm-server is cloned</p>
                      </div>
                      <div>
                        <label className="text-sm font-medium text-gray-700">Models Folder</label>
                        <input
                          className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                          value={modelsPath}
                          onChange={e => setModelsPath(e.target.value)}
                          placeholder="/path/to/models"
                        />
                        <p className="text-xs text-gray-400 mt-0.5">Folder where Ollama model weights are stored</p>
                      </div>
                    </div>
                  )}

                  {/* OpenAI */}
                  <label className="flex items-center gap-3 p-4 border rounded-xl cursor-pointer hover:border-indigo-400 transition-colors">
                    <input type="checkbox" checked={useOpenAI} onChange={e => setUseOpenAI(e.target.checked)} className="w-4 h-4" />
                    <div className="flex-1">
                      <div className="font-medium">🌐 OpenAI</div>
                      <div className="text-sm text-gray-500">GPT-4o, GPT-4o-mini (requires API key)</div>
                    </div>
                  </label>
                  {useOpenAI && (
                    <div className="ml-8 mb-3">
                      <label className="text-sm font-medium text-gray-700">OpenAI API Key</label>
                      <input
                        className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                        type="password"
                        value={openaiKey}
                        onChange={e => setOpenaiKey(e.target.value)}
                        placeholder={openaiSecretId ? '(key already saved — enter to replace)' : 'sk-...'}
                      />
                      {openaiSecretId && <div className="text-xs text-green-600 mt-1">✓ API key saved securely</div>}
                    </div>
                  )}

                  {/* Anthropic */}
                  <label className="flex items-center gap-3 p-4 border rounded-xl cursor-pointer hover:border-indigo-400 transition-colors">
                    <input type="checkbox" checked={useAnthropic} onChange={e => setUseAnthropic(e.target.checked)} className="w-4 h-4" />
                    <div className="flex-1">
                      <div className="font-medium">🔮 Anthropic</div>
                      <div className="text-sm text-gray-500">Claude 3.5 / 4 (requires API key)</div>
                    </div>
                  </label>
                  {useAnthropic && (
                    <div className="ml-8">
                      <label className="text-sm font-medium text-gray-700">Anthropic API Key</label>
                      <input
                        className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                        type="password"
                        value={anthropicKey}
                        onChange={e => setAnthropicKey(e.target.value)}
                        placeholder={anthropicSecretId ? '(key already saved — enter to replace)' : 'sk-ant-...'}
                      />
                      {anthropicSecretId && <div className="text-xs text-green-600 mt-1">✓ API key saved securely</div>}
                    </div>
                  )}

                  {/* Google */}
                  <label className="flex items-center gap-3 p-4 border rounded-xl cursor-pointer hover:border-indigo-400 transition-colors">
                    <input type="checkbox" checked={useGoogle} onChange={e => setUseGoogle(e.target.checked)} className="w-4 h-4" />
                    <div className="flex-1">
                      <div className="font-medium">🔵 Google Gemini</div>
                      <div className="text-sm text-gray-500">Gemini Pro / Flash (requires API key)</div>
                    </div>
                  </label>
                  {useGoogle && (
                    <div className="ml-8">
                      <label className="text-sm font-medium text-gray-700">Google AI API Key</label>
                      <input
                        className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                        type="password"
                        value={googleKey}
                        onChange={e => setGoogleKey(e.target.value)}
                        placeholder={googleSecretId ? '(key already saved — enter to replace)' : 'AIza...'}
                      />
                      {googleSecretId && <div className="text-xs text-green-600 mt-1">✓ API key saved securely</div>}
                    </div>
                  )}

                  {/* Azure */}
                  <label className="flex items-center gap-3 p-4 border rounded-xl cursor-pointer hover:border-indigo-400 transition-colors">
                    <input type="checkbox" checked={useAzure} onChange={e => setUseAzure(e.target.checked)} className="w-4 h-4" />
                    <div className="flex-1">
                      <div className="font-medium">🟦 Azure OpenAI</div>
                      <div className="text-sm text-gray-500">GPT-4o via Azure (requires API key)</div>
                    </div>
                  </label>
                  {useAzure && (
                    <div className="ml-8">
                      <label className="text-sm font-medium text-gray-700">Azure OpenAI API Key</label>
                      <input
                        className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                        type="password"
                        value={azureKey}
                        onChange={e => setAzureKey(e.target.value)}
                        placeholder={azureSecretId ? '(key already saved — enter to replace)' : 'your-azure-api-key'}
                      />
                      {azureSecretId && <div className="text-xs text-green-600 mt-1">✓ API key saved securely</div>}
                    </div>
                  )}

                  {/* GitHub Copilot */}
                  <label className="flex items-center gap-3 p-4 border rounded-xl cursor-pointer hover:border-indigo-400 transition-colors">
                    <input type="checkbox" checked={useCopilot} onChange={e => setUseCopilot(e.target.checked)} className="w-4 h-4" />
                    <div className="flex-1">
                      <div className="font-medium">🤖 GitHub Copilot</div>
                      <div className="text-sm text-gray-500">GPT-4o via GitHub Copilot (requires token)</div>
                    </div>
                  </label>
                  {useCopilot && (
                    <div className="ml-8">
                      <label className="text-sm font-medium text-gray-700">GitHub Copilot Token</label>
                      <input
                        className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                        type="password"
                        value={copilotKey}
                        onChange={e => setCopilotKey(e.target.value)}
                        placeholder={copilotSecretId ? '(token already saved — enter to replace)' : 'ghu_...'}
                      />
                      {copilotSecretId && <div className="text-xs text-green-600 mt-1">✓ Token saved securely</div>}
                    </div>
                  )}
                </div>
                <p className="text-xs text-gray-400 mt-4">
                  💡 API keys are stored securely in Settings → Secrets. They are never exposed in the UI or committed to source control.
                </p>
              </div>
            )}

            {/* ── Step 2: Model Selection ────────────────────────────────── */}
            {step === 2 && (
              <div>
                <h2 className="text-xl font-bold text-gray-800 mb-1">Model Selection</h2>
                <p className="text-gray-500 text-sm mb-4">
                  {useNvidiaNim
                    ? 'Using Nvidia NIM free cloud models. Change or override below if needed.'
                    : 'Configure local setup and choose the best models for your machine.'}
                </p>
                {useNvidiaNim && (
                  <div className="bg-green-50 border border-green-200 rounded-xl p-4 mb-5">
                    <div className="font-semibold text-green-800 mb-2">🟢 Nvidia NIM Free Models</div>
                    <div className="grid grid-cols-1 gap-1 text-sm text-green-700">
                      <div><span className="font-medium">Coder:</span> {NVIDIA_MODELS.executor}</div>
                      <div><span className="font-medium">Planner:</span> {NVIDIA_MODELS.planner}</div>
                      <div><span className="font-medium">Verifier:</span> {NVIDIA_MODELS.verifier}</div>
                    </div>
                    <p className="text-xs text-green-600 mt-2">All inference routed through integrate.api.nvidia.com — no local GPU needed.</p>
                  </div>
                )}

                {/* Local daemon control (local-only) */}
                {useOllama && (
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-6">
                    <div className="font-semibold text-gray-800 mb-3">⚙️ Local Services</div>
                    {isDeployed ? (
                      <div className="p-3 bg-white rounded-lg border border-gray-200 text-sm text-gray-500">
                        🌐 Running on a deployed instance — local daemon control is only available when running locally.
                        Services are managed by your backend at <code className="bg-gray-100 px-1 rounded">{backendUrl}</code>.
                      </div>
                    ) : (
                      <>
                        <div className="mb-4 p-3 bg-white rounded-lg border border-gray-200">
                          <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                              <span>{daemonConnected ? '🟢' : '🔴'}</span>
                              <span className="text-sm font-medium">
                                {daemonChecking ? 'Checking…' : daemonConnected ? 'Daemon Connected' : 'Daemon Not Connected'}
                              </span>
                            </div>
                            <button onClick={checkDaemonConnection} className="text-xs text-indigo-600 hover:underline">
                              Refresh
                            </button>
                          </div>
                          {!daemonConnected && (
                            <p className="text-xs text-gray-500 mt-1">
                              Start with: <code className="bg-gray-100 px-1 rounded">python service_daemon.py</code>
                            </p>
                          )}
                        </div>

                        {daemonConnected && (
                          <div className="space-y-2">
                            <div className="text-xs font-medium text-gray-700 mb-1">Services</div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
                              <button
                                onClick={() => proxyRunning ? stopService('proxy') : startService('proxy')}
                                className={`px-2 py-1.5 rounded text-xs font-medium ${proxyRunning ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-green-100 text-green-700 hover:bg-green-200'}`}
                              >
                                {proxyRunning ? '⏹️ Stop Proxy' : '▶️ Start Proxy'}
                              </button>
                              <button
                                onClick={() => tunnelRunning ? stopService('tunnel') : startService('tunnel')}
                                className={`px-2 py-1.5 rounded text-xs font-medium ${tunnelRunning ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-green-100 text-green-700 hover:bg-green-200'}`}
                              >
                                {tunnelRunning ? '⏹️ Stop Tunnel' : '▶️ Start Tunnel'}
                              </button>
                            </div>
                          </div>
                        )}
                      </>
                    )}
                  </div>
                )}

                {hardware && (
                  <div className="bg-gray-50 rounded-xl p-4 mb-5 text-sm">
                    <div className="font-semibold text-gray-700 mb-2">🖥️ Detected Hardware</div>
                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-gray-600">
                      <span>CPU: {hardware.cpu_model?.split(' ').slice(0,4).join(' ')}</span>
                      <span>RAM: {hardware.ram_total_gb?.toFixed(0)} GB</span>
                      <span>VRAM: {hardware.total_vram_gb?.toFixed(0)} GB {hardware.has_gpu ? '🟢' : '⚠️ No GPU'}</span>
                      <span>{hardware.gpus?.[0]?.name || 'CPU-only inference'}</span>
                    </div>
                  </div>
                )}
                {models.length > 0 && (
                  <div className="mb-5">
                    <div className="text-sm font-semibold text-gray-700 mb-2">Available Models ({models.length})</div>
                    <div className="max-h-36 overflow-y-auto space-y-1">
                      {models.map(m => (
                        <div key={m.name} className="flex items-center justify-between text-sm px-3 py-1.5 bg-gray-50 rounded-lg">
                          <span className="font-mono">{m.name}</span>
                          <span className="text-gray-400">{m.size_gb} GB</span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-700">Default / Coder Model</label>
                    <input className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                      value={defaultModel} onChange={e => setDefaultModel(e.target.value)}
                      placeholder="qwen3-coder:30b" />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Reviewer Model</label>
                    <input className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                      value={reviewerModel} onChange={e => setReviewerModel(e.target.value)}
                      placeholder="deepseek-r1:32b" />
                  </div>
                </div>
              </div>
            )}

            {/* ── Step 3: Runtime Config ─────────────────────────────────── */}
            {step === 3 && (
              <div>
                <h2 className="text-xl font-bold text-gray-800 mb-1">Runtime Configuration</h2>
                <p className="text-gray-500 text-sm mb-5">Enable the coding runtimes you have installed on this machine.</p>
                <div className="space-y-3">
                  {[
                    { key: 'hermes',   label: 'Hermes',   desc: 'Local LLM relay (built-in) — First Class', val: enableHermes,   set: setEnableHermes,   badge: 'Recommended' },
                    { key: 'opencode', label: 'OpenCode', desc: 'VS Code-style agent runtime',              val: enableOpenCode, set: setEnableOpenCode },
                    { key: 'task-harness', label: 'Task Harness', desc: 'Compatible external harness for long-running, multi-file agent work', val: enableTaskHarness, set: setEnableTaskHarness },
                    { key: 'aider',    label: 'Aider',    desc: 'Git-native coding agent',                  val: enableAider,    set: setEnableAider },
                  ].map(r => (
                    <label key={r.key} className="flex items-center gap-3 p-4 border rounded-xl cursor-pointer hover:border-indigo-300 transition-colors">
                      <input type="checkbox" checked={r.val} onChange={e => r.set(e.target.checked)} className="w-4 h-4" />
                      <div className="flex-1">
                        <div className="font-medium">{r.label} {r.badge && <span className={pill('rec', 'indigo')}>{r.badge}</span>}</div>
                        <div className="text-sm text-gray-500">{r.desc}</div>
                      </div>
                    </label>
                  ))}
                </div>
                <p className="text-xs text-gray-400 mt-4">You can add more runtimes later in Infrastructure → Runtimes.</p>
              </div>
            )}

            {/* ── Step 4: Default Agent ──────────────────────────────────── */}
            {step === 4 && (
              <div>
                <h2 className="text-xl font-bold text-gray-800 mb-1">Default Agent</h2>
                <p className="text-gray-500 text-sm mb-5">Configure your default agent. You can create more in Operations → Agents.</p>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-700">Agent Name</label>
                    <input className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                      value={agentName} onChange={e => setAgentName(e.target.value)} />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Model</label>
                    <input className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                      value={agentModel} onChange={e => setAgentModel(e.target.value)} />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Cost Policy</label>
                    <select className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                      value={costPolicy} onChange={e => setCostPolicy(e.target.value)}>
                      <option value="free_only">Free only (Nvidia NIM + local — no paid cloud)</option>
                      <option value="local_only">Local only (no cloud costs)</option>
                      <option value="allow_paid">Allow paid escalation</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* ── Step 5: Policy & Privacy ───────────────────────────────── */}
            {step === 5 && (
              <div>
                <h2 className="text-xl font-bold text-gray-800 mb-1">Policy & Privacy</h2>
                <p className="text-gray-500 text-sm mb-5">Set your cost control and observability preferences.</p>
                <div className="space-y-4">
                  <label className="flex items-center gap-3 cursor-pointer">
                    <input type="checkbox" checked={neverPaid} onChange={e => setNeverPaid(e.target.checked)} className="w-4 h-4" />
                    <div>
                      <div className="font-medium">Never use paid providers</div>
                      <div className="text-sm text-gray-500">All inference stays local (strongly recommended)</div>
                    </div>
                  </label>
                  {!neverPaid && (
                    <label className="flex items-center gap-3 cursor-pointer ml-6">
                      <input type="checkbox" checked={requireApproval} onChange={e => setRequireApproval(e.target.checked)} className="w-4 h-4" />
                      <div>
                        <div className="font-medium">Require approval before paid escalation</div>
                        <div className="text-sm text-gray-500">Ask before sending any task to a cloud API</div>
                      </div>
                    </label>
                  )}
                  <div className="border-t pt-4">
                    <label className="flex items-center gap-3 cursor-pointer">
                      <input type="checkbox" checked={enableLangfuse} onChange={e => setEnableLangfuse(e.target.checked)} className="w-4 h-4" />
                      <div>
                        <div className="font-medium">Enable Langfuse observability</div>
                        <div className="text-sm text-gray-500">Track token usage and cost savings</div>
                      </div>
                    </label>
                    {enableLangfuse && (
                      <div className="ml-6 mt-2">
                        <label className="text-sm font-medium text-gray-700">Langfuse Host</label>
                        <input className="w-full mt-1 border border-gray-300 rounded-lg px-3 py-2 text-base text-gray-900 focus:border-indigo-500 focus:ring-2 focus:ring-indigo-200 focus:outline-none"
                          value={langfuseHost} onChange={e => setLangfuseHost(e.target.value)} />
                        <p className="text-xs text-gray-400 mt-1">Add your Langfuse API keys in Settings → Secrets after setup.</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* ── Navigation ─────────────────────────────────────────────── */}
            <div className="flex flex-col-reverse gap-3 sm:flex-row sm:items-center sm:justify-between mt-8 pt-6 border-t">
              <button
                onClick={() => setStep(s => s - 1)}
                disabled={step === 1}
                className="w-full sm:w-auto px-4 py-2 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-40"
              >
                ← Back
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="w-full sm:w-auto px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
              >
                {saving ? 'Saving...' : step === 5 ? '🚀 Complete Setup' : 'Next →'}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
