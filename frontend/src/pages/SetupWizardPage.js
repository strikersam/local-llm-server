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
 */

import React, { useState, useEffect, useCallback } from 'react';
import {
  getSetupState,
  saveSetupStep,
  completeSetup,
  detectHardwareForSetup,
  detectModelsForSetup,
} from '../api';

const STEPS = [
  { num: 1, title: 'Provider Setup',     icon: '🔌' },
  { num: 2, title: 'Local Models',       icon: '🖥️' },
  { num: 3, title: 'Runtime Config',     icon: '⚙️' },
  { num: 4, title: 'Default Agent',      icon: '🤖' },
  { num: 5, title: 'Policy & Privacy',   icon: '🛡️' },
];

const pill = (label, color = 'green') =>
  `inline-block px-2 py-0.5 rounded text-xs font-semibold bg-${color}-100 text-${color}-800`;

export default function SetupWizardPage({ onComplete }) {
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [hardware, setHardware] = useState(null);
  const [models, setModels] = useState([]);
  const [done, setDone] = useState(false);

  // Step 1
  const [useOllama, setUseOllama] = useState(true);
  const [ollamaUrl, setOllamaUrl] = useState('http://localhost:11434');
  const [useOpenAI, setUseOpenAI] = useState(false);
  const [useAnthropic, setUseAnthropic] = useState(false);

  // Step 2
  const [defaultModel, setDefaultModel] = useState('qwen3-coder:30b');
  const [reviewerModel, setReviewerModel] = useState('deepseek-r1:32b');
  const [repoPath, setRepoPath] = useState('');
  const [modelsPath, setModelsPath] = useState('');
  const [daemonConnected, setDaemonConnected] = useState(false);
  const [daemonChecking, setDaemonChecking] = useState(false);
  const [proxyRunning, setProxyRunning] = useState(false);
  const [tunnelRunning, setTunnelRunning] = useState(false);

  // Step 3
  const [enableHermes, setEnableHermes] = useState(true);
  const [enableOpenCode, setEnableOpenCode] = useState(false);
  const [enableAider, setEnableAider] = useState(false);

  // Step 4
  const [agentName, setAgentName] = useState('My Agent');
  const [agentModel, setAgentModel] = useState('qwen3-coder:30b');
  const [costPolicy, setCostPolicy] = useState('local_only');

  // Step 5
  const [neverPaid, setNeverPaid] = useState(true);
  const [requireApproval, setRequireApproval] = useState(true);
  const [enableLangfuse, setEnableLangfuse] = useState(false);
  const [langfuseHost, setLangfuseHost] = useState('https://cloud.langfuse.com');

  useEffect(() => {
    getSetupState().then(r => {
      if (r.data.completed) {
        setDone(true);
        if (onComplete) onComplete();
      } else {
        setStep(r.data.current_step || 1);
      }
    }).catch(() => {});
  }, []);

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

  const checkDaemonConnection = useCallback(async () => {
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
  }, []);

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
        alert('Configuration saved!');
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
      alert('Error: ' + e.message);
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
      alert('Error: ' + e.message);
    }
  };

  useEffect(() => {
    if (step === 2) {
      loadHardware();
      if (useOllama) {
        checkDaemonConnection();
      }
    }
  }, [step, loadHardware, useOllama, checkDaemonConnection]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const payloads = {
        1: { use_ollama: useOllama, ollama_base_url: ollamaUrl, use_openai: useOpenAI, use_anthropic: useAnthropic },
        2: { default_model: defaultModel, coder_model: defaultModel, reviewer_model: reviewerModel, repo_path: repoPath, models_path: modelsPath },
        3: { enable_hermes: enableHermes, enable_opencode: enableOpenCode, enable_aider: enableAider },
        4: { agent_name: agentName, agent_model: agentModel, cost_policy: costPolicy },
        5: { never_use_paid_providers: neverPaid, require_approval_before_paid: requireApproval, enable_langfuse: enableLangfuse, langfuse_host: langfuseHost },
      };
      await saveSetupStep(step, payloads[step]);
      if (step < 5) {
        setStep(s => s + 1);
      } else {
        await completeSetup();
        setDone(true);
        if (onComplete) onComplete();
      }
    } finally {
      setSaving(false);
    }
  };

  const compatClass = (label) => {
    if (!hardware || !label) return '';
    const map = { compatible: 'text-green-600', degraded: 'text-yellow-600', incompatible: 'text-red-600' };
    return map[label] || '';
  };

  if (done) {
    return (
      <div className="flex flex-col items-center justify-center min-h-screen bg-gray-50 p-8">
        <div className="bg-white rounded-2xl shadow-lg p-10 text-center max-w-md">
          <div className="text-5xl mb-4">🎉</div>
          <h1 className="text-2xl font-bold text-gray-800 mb-2">You're all set!</h1>
          <p className="text-gray-500 mb-6">Your AI Agent Control Plane is ready to use.</p>
          <a href="/control-plane" className="bg-indigo-600 text-white px-6 py-2 rounded-lg hover:bg-indigo-700">
            Open Control Plane →
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 flex">
      {/* Sidebar */}
      <div className="w-64 bg-indigo-900 text-white p-6 flex flex-col">
        <div className="mb-8">
          <div className="text-lg font-bold">🧠 Setup Wizard</div>
          <div className="text-indigo-300 text-sm mt-1">Let's get you started</div>
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
      <div className="flex-1 p-8 overflow-auto">
        <div className="max-w-2xl mx-auto">
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

          <div className="bg-white rounded-2xl shadow p-8">
            {/* Step 1 */}
            {step === 1 && (
              <div>
                <h2 className="text-xl font-bold text-gray-800 mb-1">Provider Setup</h2>
                <p className="text-gray-500 text-sm mb-6">Choose which AI providers you want to use. Local-first is the default.</p>
                <div className="space-y-4">
                  <label className="flex items-center gap-3 p-4 border rounded-xl cursor-pointer hover:border-indigo-400 transition-colors">
                    <input type="checkbox" checked={useOllama} onChange={e => setUseOllama(e.target.checked)} className="w-4 h-4" />
                    <div>
                      <div className="font-medium">🦙 Ollama (Local)</div>
                      <div className="text-sm text-gray-500">Run models locally on this machine</div>
                    </div>
                    <span className={pill('Recommended')}>Recommended</span>
                  </label>
                  {useOllama && (
                    <div className="ml-8">
                      <label className="text-sm font-medium text-gray-700">Ollama URL</label>
                      <input
                        className="w-full mt-1 border rounded-lg px-3 py-2 text-sm"
                        value={ollamaUrl}
                        onChange={e => setOllamaUrl(e.target.value)}
                        placeholder="http://localhost:11434"
                      />
                    </div>
                  )}
                  <label className="flex items-center gap-3 p-4 border rounded-xl cursor-pointer hover:border-indigo-400 transition-colors">
                    <input type="checkbox" checked={useOpenAI} onChange={e => setUseOpenAI(e.target.checked)} className="w-4 h-4" />
                    <div>
                      <div className="font-medium">🌐 OpenAI</div>
                      <div className="text-sm text-gray-500">GPT-4o, GPT-4o-mini (requires API key)</div>
                    </div>
                  </label>
                  <label className="flex items-center gap-3 p-4 border rounded-xl cursor-pointer hover:border-indigo-400 transition-colors">
                    <input type="checkbox" checked={useAnthropic} onChange={e => setUseAnthropic(e.target.checked)} className="w-4 h-4" />
                    <div>
                      <div className="font-medium">🔮 Anthropic</div>
                      <div className="text-sm text-gray-500">Claude 3.5 / 4 (requires API key)</div>
                    </div>
                  </label>
                </div>
                <p className="text-xs text-gray-400 mt-4">
                  💡 API keys for cloud providers are stored securely in Settings → Secrets after setup.
                </p>
              </div>
            )}

            {/* Step 2 */}
            {step === 2 && (
              <div>
                <h2 className="text-xl font-bold text-gray-800 mb-1">Local Models</h2>
                <p className="text-gray-500 text-sm mb-4">We detected your hardware. Configure local setup and choose the best models for your machine.</p>

                {/* Local Setup Section */}
                {useOllama && (
                  <div className="bg-blue-50 border border-blue-200 rounded-xl p-5 mb-6">
                    <div className="font-semibold text-gray-800 mb-3">⚙️ Local Setup</div>

                    {/* Daemon Status */}
                    <div className="mb-4 p-3 bg-white rounded-lg border border-gray-200">
                      <div className="flex items-center gap-2 mb-2">
                        <span className={daemonConnected ? '🟢' : '🔴'}></span>
                        <span className="text-sm font-medium">
                          {daemonConnected ? 'Daemon Connected' : 'Daemon Not Connected'}
                        </span>
                      </div>
                      <p className="text-xs text-gray-500">
                        {daemonConnected ? 'Ready to configure services' : 'Start with: python service_daemon.py'}
                      </p>
                    </div>

                    {/* Paths Configuration */}
                    <div className="space-y-2 mb-4">
                      <div>
                        <label className="text-xs font-medium text-gray-700">Repository Path</label>
                        <input className="w-full mt-1 border rounded-lg px-2 py-1.5 text-xs font-mono bg-white"
                          value={repoPath} onChange={e => setRepoPath(e.target.value)}
                          placeholder="/path/to/local-llm-server" />
                      </div>
                      <div>
                        <label className="text-xs font-medium text-gray-700">Models Path</label>
                        <input className="w-full mt-1 border rounded-lg px-2 py-1.5 text-xs font-mono bg-white"
                          value={modelsPath} onChange={e => setModelsPath(e.target.value)}
                          placeholder="/path/to/models" />
                      </div>
                    </div>

                    {/* Configure Button */}
                    <button
                      onClick={configureDaemon}
                      className="w-full mb-3 px-3 py-1.5 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700 text-xs"
                    >
                      📁 Configure Paths
                    </button>

                    {/* Service Controls */}
                    {daemonConnected && (
                      <div className="space-y-2">
                        <div className="text-xs font-medium text-gray-700">Services</div>
                        <div className="grid grid-cols-2 gap-2">
                          <button
                            onClick={() => proxyRunning ? stopService('proxy') : startService('proxy')}
                            className={`px-2 py-1.5 rounded text-xs font-medium ${
                              proxyRunning ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-green-100 text-green-700 hover:bg-green-200'
                            }`}
                          >
                            {proxyRunning ? '⏹️ Stop Proxy' : '▶️ Start Proxy'}
                          </button>
                          <button
                            onClick={() => tunnelRunning ? stopService('tunnel') : startService('tunnel')}
                            className={`px-2 py-1.5 rounded text-xs font-medium ${
                              tunnelRunning ? 'bg-red-100 text-red-700 hover:bg-red-200' : 'bg-green-100 text-green-700 hover:bg-green-200'
                            }`}
                          >
                            {tunnelRunning ? '⏹️ Stop Tunnel' : '▶️ Start Tunnel'}
                          </button>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {hardware && (
                  <div className="bg-gray-50 rounded-xl p-4 mb-5 text-sm">
                    <div className="font-semibold text-gray-700 mb-2">🖥️ Detected Hardware</div>
                    <div className="grid grid-cols-2 gap-2 text-gray-600">
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
                    <input className="w-full mt-1 border rounded-lg px-3 py-2 text-sm font-mono"
                      value={defaultModel} onChange={e => setDefaultModel(e.target.value)}
                      placeholder="qwen3-coder:30b" />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Reviewer Model</label>
                    <input className="w-full mt-1 border rounded-lg px-3 py-2 text-sm font-mono"
                      value={reviewerModel} onChange={e => setReviewerModel(e.target.value)}
                      placeholder="deepseek-r1:32b" />
                  </div>
                </div>
              </div>
            )}

            {/* Step 3 */}
            {step === 3 && (
              <div>
                <h2 className="text-xl font-bold text-gray-800 mb-1">Runtime Configuration</h2>
                <p className="text-gray-500 text-sm mb-5">Enable the coding runtimes you have installed on this machine.</p>
                <div className="space-y-3">
                  {[
                    { key: 'hermes', label: 'Hermes', desc: 'Local LLM relay (built-in) — First Class', val: enableHermes, set: setEnableHermes, badge: 'Recommended' },
                    { key: 'opencode', label: 'OpenCode', desc: 'VS Code-style agent runtime', val: enableOpenCode, set: setEnableOpenCode },
                    { key: 'aider', label: 'Aider', desc: 'Git-native coding agent', val: enableAider, set: setEnableAider },
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

            {/* Step 4 */}
            {step === 4 && (
              <div>
                <h2 className="text-xl font-bold text-gray-800 mb-1">Default Agent</h2>
                <p className="text-gray-500 text-sm mb-5">Configure your default agent. You can create more in Operations → Agents.</p>
                <div className="space-y-3">
                  <div>
                    <label className="text-sm font-medium text-gray-700">Agent Name</label>
                    <input className="w-full mt-1 border rounded-lg px-3 py-2 text-sm"
                      value={agentName} onChange={e => setAgentName(e.target.value)} />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Model</label>
                    <input className="w-full mt-1 border rounded-lg px-3 py-2 text-sm font-mono"
                      value={agentModel} onChange={e => setAgentModel(e.target.value)} />
                  </div>
                  <div>
                    <label className="text-sm font-medium text-gray-700">Cost Policy</label>
                    <select className="w-full mt-1 border rounded-lg px-3 py-2 text-sm"
                      value={costPolicy} onChange={e => setCostPolicy(e.target.value)}>
                      <option value="local_only">Local only (no cloud costs)</option>
                      <option value="allow_paid">Allow paid escalation</option>
                    </select>
                  </div>
                </div>
              </div>
            )}

            {/* Step 5 */}
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
                        <input className="w-full mt-1 border rounded-lg px-3 py-2 text-sm"
                          value={langfuseHost} onChange={e => setLangfuseHost(e.target.value)} />
                        <p className="text-xs text-gray-400 mt-1">Add your Langfuse API keys in Settings → Secrets after setup.</p>
                      </div>
                    )}
                  </div>
                </div>
              </div>
            )}

            {/* Navigation */}
            <div className="flex items-center justify-between mt-8 pt-6 border-t">
              <button
                onClick={() => setStep(s => s - 1)}
                disabled={step === 1}
                className="px-4 py-2 text-sm text-gray-600 hover:text-gray-800 disabled:opacity-40"
              >
                ← Back
              </button>
              <button
                onClick={handleSave}
                disabled={saving}
                className="px-6 py-2 bg-indigo-600 text-white rounded-lg hover:bg-indigo-700 text-sm font-medium disabled:opacity-50"
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
