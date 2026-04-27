import React, { useState, useEffect, useCallback } from 'react';
import { Zap, Plus, X, AlertTriangle, Check } from 'lucide-react';
import { getRoutingPolicy, updateRoutingPolicy, fmtErr } from '../api';

const C = {
  bg: '#0F0F13', surface: '#141418', border: 'rgba(255,255,255,0.06)',
  primary: '#F2F2F6', secondary: '#B2B2C4', tertiary: '#808094', muted: '#565666',
  accent: '#002FA7',
};

const POOL_META = [
  {
    id: 'onDevice', label: 'On-Device', sub: 'Same machine as browser',
    desc: 'Fastest, fully private. Models running locally via Ollama on your current machine. No network hop.',
    color: '#10B981', badge: 'local', cost: '$0.00', privacy: 'Maximum', latency: '~80ms',
  },
  {
    id: 'selfHosted', label: 'Self-Hosted Server', sub: 'Your server / home lab / VPS',
    desc: 'Models on a server you control — accessed over LAN or internet. Private, no vendor dependency.',
    color: '#3B82F6', badge: 'server', cost: '$0.00', privacy: 'High', latency: '~150–400ms',
  },
  {
    id: 'freeCloud', label: 'Free Cloud', sub: 'Rate-limited, no cost',
    desc: 'Ollama Cloud, Groq (free tier), Google Gemini Free, Together AI free, Mistral Le Platforme free.',
    color: '#A78BFA', badge: 'free', cost: '$0.00', privacy: 'Low', latency: '~300–800ms',
  },
  {
    id: 'commercialCloud', label: 'Commercial Cloud', sub: 'Paid APIs — best capability',
    desc: 'OpenAI (GPT-4o, Codex), Anthropic (Claude 3.5 Sonnet/Opus), Cohere, Perplexity, Azure OpenAI.',
    color: '#F59E0B', badge: 'paid', cost: 'per token', privacy: 'Low', latency: '~300–1200ms',
  },
];

const DEFAULT_POOLS = {
  onDevice:        ['ollama/llama3.2:3b', 'ollama/codellama:7b', 'ollama/mistral:7b'],
  selfHosted:      ['server/llama3.2:8b', 'server/codellama:13b', 'server/qwen2.5:14b'],
  freeCloud:       ['groq/llama-3.1-70b-versatile', 'gemini/gemini-1.5-flash', 'together/mixtral-8x7b'],
  commercialCloud: ['anthropic/claude-3-haiku-20240307', 'openai/gpt-4o-mini', 'anthropic/claude-3-5-sonnet-20241022'],
};

const DEFAULT_POLICY = {
  complexityThreshold: 0.75,
  confidenceThreshold: 0.60,
  maxRetriesPerTier: 2,
  rateLimitCooldown: 60,
  circuitBreakerThreshold: 5,
  monthlyBudgetUSD: 10,
  neverUseCommercial: false,
  neverUseFreeCloud: false,
  askBeforeCommercial: true,
  skipOnDeviceIfRemote: false,
};

const ESCALATION_TRIGGERS_DEFAULTS = [
  { id: 'schema_fail',   label: 'Schema validation failure',      active: true,  desc: 'Output does not match expected JSON/typed schema' },
  { id: 'tool_fail',     label: 'Tool call failure (≥2 retries)', active: true,  desc: 'Agent tool returns error or timeout repeatedly' },
  { id: 'complexity',    label: 'High complexity score',          active: true,  desc: 'Task complexity exceeds configured threshold' },
  { id: 'low_conf',      label: 'Low confidence output',          active: true,  desc: 'Self-reported confidence below minimum threshold' },
  { id: 'context_limit', label: 'Context window exceeded',        active: true,  desc: 'Local model context exhausted mid-task' },
  { id: 'malformed',     label: 'Malformed / truncated response', active: true,  desc: 'Output ends abruptly or contains repeated tokens' },
  { id: 'rate_limit',    label: 'Tier rate-limited',              active: true,  desc: 'Current tier is throttled — skip to next available' },
  { id: 'user_request',  label: 'User requests best model',       active: true,  desc: '"best model", "high accuracy" detected in prompt' },
  { id: 'latency',       label: 'Latency SLA breach',             active: false, desc: 'Response time exceeds configured SLA threshold' },
];

function Toggle({ active, onClick }) {
  return (
    <button onClick={onClick}
      className="w-9 h-5 rounded-full border shrink-0 relative transition-all"
      style={{ background: active ? C.accent : '#1E1E26', borderColor: active ? 'rgba(0,47,167,0.4)' : 'rgba(255,255,255,0.1)' }}>
      <span className={`absolute top-0.5 w-3.5 h-3.5 rounded-full bg-white transition-all ${active ? 'left-[18px]' : 'left-0.5'}`} />
    </button>
  );
}

function RangeField({ label, value, min, max, step, fmt, desc, onChange }) {
  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <span className="text-[10px] font-mono" style={{ color: '#9A9AAE' }}>{label}</span>
        <span className="text-[11px] font-mono font-bold" style={{ color: C.primary }}>{fmt(value)}</span>
      </div>
      <input type="range" min={min} max={max} step={step} value={value}
        onChange={e => onChange(Number(e.target.value))}
        className="w-full cursor-pointer" style={{ accentColor: C.accent }} />
      <div className="text-[8px] font-mono mt-1" style={{ color: C.muted }}>{desc}</div>
    </div>
  );
}

export default function RoutingPolicyPage() {
  const [pools, setPools]       = useState(DEFAULT_POOLS);
  const [policy, setPolicy]     = useState(DEFAULT_POLICY);
  const [triggers, setTriggers] = useState(ESCALATION_TRIGGERS_DEFAULTS);
  const [addingTo, setAddingTo] = useState(null);
  const [newModel, setNewModel] = useState('');
  const [saving, setSaving]     = useState(false);
  const [saved, setSaved]       = useState(false);
  const [loadError, setLoadError] = useState('');
  const [saveError, setSaveError] = useState('');

  const load = useCallback(async () => {
    try {
      const r = await getRoutingPolicy();
      const d = r.data || {};
      if (d.pools)    setPools({ ...DEFAULT_POOLS, ...d.pools });
      if (d.policy)   setPolicy({ ...DEFAULT_POLICY, ...d.policy });
      if (d.triggers) setTriggers(d.triggers);
    } catch {
      // Use defaults silently — backend may not have data yet
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  async function save() {
    setSaving(true);
    setSaveError('');
    try {
      await updateRoutingPolicy({ pools, policy, triggers });
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (e) {
      setSaveError(fmtErr(e));
    } finally {
      setSaving(false);
    }
  }

  function removeModel(poolId, model) {
    setPools(p => ({ ...p, [poolId]: p[poolId].filter(m => m !== model) }));
  }
  function addModel(poolId) {
    if (!newModel.trim()) return;
    setPools(p => ({ ...p, [poolId]: [...p[poolId], newModel.trim()] }));
    setNewModel(''); setAddingTo(null);
  }
  function toggleTrigger(id) {
    setTriggers(prev => prev.map(t => t.id === id ? { ...t, active: !t.active } : t));
  }
  function togglePolicy(key) {
    setPolicy(p => ({ ...p, [key]: !p[key] }));
  }

  return (
    <div className="h-full overflow-y-auto">
      <div className="p-5 max-w-5xl space-y-5">

        {/* Header */}
        <div className="flex items-start justify-between">
          <div>
            <h1 className="text-[15px] font-bold tracking-tight" style={{ color: C.primary, fontFamily: 'var(--font-main)' }}>Routing Policy</h1>
            <p className="text-[10px] font-mono mt-0.5" style={{ color: C.tertiary }}>4-tier escalation ladder · local-first by default</p>
          </div>
          <div className="flex flex-col items-end gap-1.5">
            <button onClick={save} disabled={saving}
              className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono uppercase tracking-wider text-white rounded-lg disabled:opacity-50 transition-all"
              style={{ background: saved ? '#10B981' : C.accent }}>
              {saved ? <><Check size={10} /> Saved</> : <><Zap size={10} /> Save Policy</>}
            </button>
            {saveError && <div className="text-[9px] font-mono text-red-400">{saveError}</div>}
          </div>
        </div>

        {/* Tier ladder diagram */}
        <div className="rounded-xl p-5" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          <div className="text-[9px] font-mono uppercase tracking-wider mb-4" style={{ color: C.tertiary }}>Escalation Ladder — lowest cost first</div>
          <div className="flex flex-col sm:flex-row items-stretch sm:items-start gap-2">
            {POOL_META.map((tier, i) => (
              <React.Fragment key={tier.id}>
                <div className="flex-1 min-w-0">
                  <div className="border rounded-xl p-3.5 h-full"
                    style={{ borderColor: tier.color + '30', background: tier.color + '08' }}>
                    <div className="flex items-center gap-2 mb-2">
                      <div className="w-5 h-5 rounded-md flex items-center justify-center text-[9px] font-bold text-white"
                        style={{ background: tier.color }}>
                        {i + 1}
                      </div>
                      <div>
                        <div className="text-[11px] font-semibold text-white leading-tight">{tier.label}</div>
                        <div className="text-[8px] font-mono leading-tight" style={{ color: tier.color }}>{tier.sub}</div>
                      </div>
                    </div>
                    <div className="grid grid-cols-2 gap-x-3 gap-y-1 mt-2">
                      {[
                        { k: 'Cost',    v: tier.cost },
                        { k: 'Privacy', v: tier.privacy },
                        { k: 'Latency', v: tier.latency },
                        { k: 'Models',  v: (pools[tier.id] || []).length },
                      ].map(r => (
                        <div key={r.k}>
                          <div className="text-[7px] font-mono uppercase tracking-wider" style={{ color: C.muted }}>{r.k}</div>
                          <div className="text-[9px] font-mono" style={{ color: C.secondary }}>{r.v}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
                {i < POOL_META.length - 1 && (
                  <div className="hidden sm:flex items-center self-center flex-col text-[10px] font-mono" style={{ color: C.muted }}>
                    <span>→</span>
                    <span className="text-[7px] mt-0.5">escalate</span>
                  </div>
                )}
              </React.Fragment>
            ))}
          </div>
        </div>

        {/* Pool configuration */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {POOL_META.map(tier => (
            <div key={tier.id} className="rounded-xl overflow-hidden"
              style={{ background: C.surface, border: `1px solid ${C.border}` }}>
              <div className="px-4 py-3 border-b flex items-center gap-2" style={{ borderColor: C.border }}>
                <div className="w-2 h-2 rounded-full" style={{ background: tier.color }} />
                <div className="flex-1 min-w-0">
                  <span className="text-[10px] font-mono font-bold uppercase tracking-wider" style={{ color: tier.color }}>{tier.label}</span>
                  <span className="ml-2 text-[8px] font-mono" style={{ color: C.muted }}>{tier.sub}</span>
                </div>
                <span className="text-[8px] font-mono" style={{ color: C.muted }}>priority order ↓</span>
              </div>
              <div className="px-4 pt-3 pb-0">
                <p className="text-[9px] font-mono leading-relaxed" style={{ color: '#6E6E80' }}>{tier.desc}</p>
              </div>
              <div className="p-3 space-y-1.5">
                {(pools[tier.id] || []).map((m, i) => (
                  <div key={m} className="flex items-center gap-2 px-3 py-2 rounded-lg group"
                    style={{ background: '#111116', border: '1px solid rgba(255,255,255,0.05)' }}>
                    <span className="text-[8px] font-mono w-3 shrink-0" style={{ color: C.muted }}>{i + 1}</span>
                    <span className="text-[10px] font-mono flex-1 truncate" style={{ color: tier.color }}>{m}</span>
                    <button onClick={() => removeModel(tier.id, m)}
                      className="opacity-0 group-hover:opacity-100 transition-all"
                      style={{ color: C.muted }}
                      onMouseEnter={e => e.currentTarget.style.color = '#EF4444'}
                      onMouseLeave={e => e.currentTarget.style.color = C.muted}>
                      <X size={9} />
                    </button>
                  </div>
                ))}
                {addingTo === tier.id ? (
                  <div className="flex gap-1.5">
                    <input autoFocus value={newModel} onChange={e => setNewModel(e.target.value)}
                      onKeyDown={e => { if (e.key === 'Enter') addModel(tier.id); if (e.key === 'Escape') { setAddingTo(null); setNewModel(''); } }}
                      placeholder="provider/model-name"
                      className="flex-1 px-2.5 py-1.5 text-[10px] font-mono rounded-lg outline-none placeholder:text-[#565666]"
                      style={{ background: '#111116', border: '1px solid rgba(0,47,167,0.4)', color: C.primary }} />
                    <button onClick={() => addModel(tier.id)}
                      className="px-2.5 py-1.5 text-[9px] font-mono text-white rounded-lg"
                      style={{ background: C.accent }}>Add</button>
                    <button onClick={() => { setAddingTo(null); setNewModel(''); }}
                      className="px-2 py-1.5 text-[9px] font-mono rounded-lg border transition-colors"
                      style={{ color: C.tertiary, borderColor: 'rgba(255,255,255,0.08)' }}>✕</button>
                  </div>
                ) : (
                  <button onClick={() => { setAddingTo(tier.id); setNewModel(''); }}
                    className="w-full flex items-center gap-1.5 px-3 py-2 border border-dashed rounded-lg text-[9px] font-mono transition-colors"
                    style={{ borderColor: 'rgba(255,255,255,0.08)', color: C.muted }}
                    onMouseEnter={e => { e.currentTarget.style.color = C.tertiary; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.16)'; }}
                    onMouseLeave={e => { e.currentTarget.style.color = C.muted; e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; }}>
                    <Plus size={9} /> Add model
                  </button>
                )}
              </div>
            </div>
          ))}
        </div>

        {/* Global overrides */}
        <div className="rounded-xl overflow-hidden" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          <div className="px-4 py-3 border-b" style={{ borderColor: C.border }}>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider" style={{ color: '#9A9AAE' }}>Global Overrides</span>
          </div>
          <div className="p-4 grid grid-cols-1 sm:grid-cols-2 gap-3">
            {[
              { key: 'neverUseCommercial',   label: 'Never use commercial cloud',     desc: 'Hard block paid APIs — all tasks stay on local/free tiers' },
              { key: 'neverUseFreeCloud',    label: 'Never use free cloud',            desc: 'Skip free-tier providers (privacy-sensitive environments)' },
              { key: 'askBeforeCommercial',  label: 'Approval before paid tier',       desc: 'Human gate required before any commercial API call' },
              { key: 'skipOnDeviceIfRemote', label: 'Skip on-device if remote access', desc: 'If portal is accessed over internet, skip on-device tier' },
            ].map(toggle => (
              <div key={toggle.key}
                className="flex items-start gap-3 p-3 rounded-xl border transition-colors cursor-pointer"
                style={{ borderColor: C.border }}
                onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.10)'}
                onMouseLeave={e => e.currentTarget.style.borderColor = C.border}>
                <div className="mt-0.5">
                  <Toggle active={policy[toggle.key]} onClick={() => togglePolicy(toggle.key)} />
                </div>
                <div>
                  <div className="text-[11px] font-medium" style={{ color: '#CACADA' }}>{toggle.label}</div>
                  <div className="text-[9px] font-mono mt-0.5" style={{ color: '#6E6E80' }}>{toggle.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Thresholds */}
        <div className="rounded-xl overflow-hidden" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          <div className="px-4 py-3 border-b" style={{ borderColor: C.border }}>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider" style={{ color: '#9A9AAE' }}>Thresholds & Limits</span>
          </div>
          <div className="p-4 grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-5">
            <RangeField label="Complexity trigger"  value={policy.complexityThreshold}    min={0}  max={1}   step={0.05} fmt={v => `${Math.round(v*100)}%`}              desc="Escalate if task complexity exceeds this score" onChange={v => setPolicy(p => ({ ...p, complexityThreshold: v }))} />
            <RangeField label="Confidence minimum"  value={policy.confidenceThreshold}    min={0}  max={1}   step={0.05} fmt={v => `${Math.round(v*100)}%`}              desc="Retry if output confidence is below this score" onChange={v => setPolicy(p => ({ ...p, confidenceThreshold: v }))} />
            <RangeField label="Retries per tier"    value={policy.maxRetriesPerTier}      min={0}  max={5}   step={1}    fmt={v => `${v}×`}                               desc="Attempts at each tier before escalating up" onChange={v => setPolicy(p => ({ ...p, maxRetriesPerTier: v }))} />
            <RangeField label="Rate-limit cooldown" value={policy.rateLimitCooldown}      min={10} max={300} step={10}   fmt={v => `${v}s`}                               desc="Wait before retrying a rate-limited provider" onChange={v => setPolicy(p => ({ ...p, rateLimitCooldown: v }))} />
            <RangeField label="Circuit breaker"     value={policy.circuitBreakerThreshold} min={1}  max={20}  step={1}    fmt={v => `${v} fails`}                         desc="Failures before a provider is marked offline" onChange={v => setPolicy(p => ({ ...p, circuitBreakerThreshold: v }))} />
            <RangeField label="Monthly paid budget" value={policy.monthlyBudgetUSD}       min={0}  max={100} step={1}    fmt={v => v === 0 ? 'Unlimited' : `$${v}`}       desc="Hard cap on commercial cloud spend per month" onChange={v => setPolicy(p => ({ ...p, monthlyBudgetUSD: v }))} />
          </div>
        </div>

        {/* Escalation triggers */}
        <div className="rounded-xl overflow-hidden" style={{ background: C.surface, border: `1px solid ${C.border}` }}>
          <div className="px-4 py-3 border-b flex items-center gap-2" style={{ borderColor: C.border }}>
            <span className="text-[10px] font-mono font-bold uppercase tracking-wider" style={{ color: '#9A9AAE' }}>Escalation Triggers</span>
            <span className="text-[8px] font-mono ml-1" style={{ color: C.muted }}>{triggers.filter(t => t.active).length} active</span>
          </div>
          <div className="divide-y" style={{ '--tw-divide-color': 'rgba(255,255,255,0.05)' }}>
            {triggers.map(t => (
              <div key={t.id} className="flex items-center gap-3 px-4 py-3 transition-colors"
                onMouseEnter={e => e.currentTarget.style.background = 'rgba(255,255,255,0.015)'}
                onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                <Toggle active={t.active} onClick={() => toggleTrigger(t.id)} />
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] font-medium" style={{ color: '#CACADA' }}>{t.label}</div>
                  <div className="text-[9px] font-mono" style={{ color: '#6E6E80' }}>{t.desc}</div>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
