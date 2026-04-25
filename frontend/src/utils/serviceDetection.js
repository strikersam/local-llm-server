/**
 * serviceDetection.js — Detect which LLM providers/services are available.
 *
 * Detection tiers:
 *   LOCAL   — Ollama or local LLM server reachable at a local port
 *   REMOTE  — User-hosted endpoint (configured via backend URL)
 *   CLOUD   — Commercial APIs (Anthropic, OpenAI, Google…) detected via saved secrets
 *   FREE    — HuggingFace and other open providers
 *
 * All functions return objects that are safe to render in UI.
 */

import { getBackendUrl } from '../api';

// ─── Types ────────────────────────────────────────────────────────────────────

/**
 * @typedef {Object} ServiceStatus
 * @property {string}  id        - unique identifier
 * @property {string}  name      - human-readable name
 * @property {string}  tier      - 'local' | 'remote' | 'cloud' | 'free'
 * @property {boolean} available - true if the service is reachable/configured
 * @property {string}  reason    - why not available (if applicable)
 * @property {boolean} hasKey    - true if an API key/secret is configured for this provider
 */

// ─── Constants ────────────────────────────────────────────────────────────────

const OLLAMA_DEFAULT_URL = 'http://localhost:11434';
const PROBE_TIMEOUT_MS   = 4000;

// ─── Helpers ──────────────────────────────────────────────────────────────────

async function probeFetch(url, options = {}) {
  const controller = new AbortController();
  const id = setTimeout(() => controller.abort(), PROBE_TIMEOUT_MS);
  try {
    const r = await fetch(url, { ...options, signal: controller.signal });
    return { ok: r.ok, status: r.status };
  } catch (e) {
    return { ok: false, error: e.message };
  } finally {
    clearTimeout(id);
  }
}

// ─── Detection functions ───────────────────────────────────────────────────────

/**
 * Check whether Ollama is reachable at the given URL (via backend proxy or directly).
 * On GitHub Pages the direct localhost probe will fail; use the backend proxy instead.
 */
export async function detectOllama(ollamaUrl = OLLAMA_DEFAULT_URL) {
  const backendUrl = getBackendUrl();
  const isDeployed = window.location.hostname !== 'localhost' &&
                     window.location.hostname !== '127.0.0.1';

  if (isDeployed && backendUrl) {
    // Ask the backend to check Ollama
    const r = await probeFetch(`${backendUrl}/api/setup/detect/models?ollama_url=${encodeURIComponent(ollamaUrl)}`);
    return {
      id: 'ollama',
      name: 'Ollama (Local)',
      tier: 'local',
      available: r.ok,
      reason: r.ok ? '' : 'Ollama not reachable via backend proxy',
      hasKey: false,
    };
  }

  // Local: probe directly
  const r = await probeFetch(`${ollamaUrl}/api/tags`);
  return {
    id: 'ollama',
    name: 'Ollama (Local)',
    tier: 'local',
    available: r.ok,
    reason: r.ok ? '' : `Cannot reach Ollama at ${ollamaUrl}. Is it running?`,
    hasKey: false,
  };
}

/**
 * Check whether the configured backend is reachable and return its health.
 */
export async function detectBackend(backendUrl) {
  const url = backendUrl || getBackendUrl();
  if (!url) {
    return {
      id: 'backend',
      name: 'LLM Relay Backend',
      tier: 'remote',
      available: false,
      reason: 'No backend URL configured. Open Setup Wizard to connect.',
      hasKey: false,
    };
  }
  const r = await probeFetch(`${url}/api/health`);
  return {
    id: 'backend',
    name: 'LLM Relay Backend',
    tier: 'remote',
    available: r.ok,
    reason: r.ok ? '' : `Backend not reachable at ${url}`,
    hasKey: false,
  };
}

/**
 * Detect cloud providers from the saved setup wizard state.
 * Returns one ServiceStatus entry per provider that was enabled in Step 1.
 */
export function detectCloudProvidersFromSetupState(step1Providers = {}) {
  const providers = [];

  const checks = [
    { id: 'anthropic', name: 'Anthropic (Claude)',      flag: 'use_anthropic', secretField: 'anthropic_secret_id', tier: 'cloud' },
    { id: 'openai',    name: 'OpenAI (GPT-4o)',         flag: 'use_openai',    secretField: 'openai_secret_id',    tier: 'cloud' },
    { id: 'google',    name: 'Google Gemini',           flag: 'use_google',    secretField: 'google_secret_id',    tier: 'cloud' },
    { id: 'azure',     name: 'Azure OpenAI',            flag: 'use_azure',     secretField: 'azure_secret_id',     tier: 'cloud' },
    { id: 'copilot',   name: 'GitHub Copilot',          flag: 'use_copilot',   secretField: 'copilot_secret_id',   tier: 'cloud' },
    { id: 'groq',      name: 'Groq',                    flag: 'use_groq',      secretField: 'groq_secret_id',      tier: 'free'  },
  ];

  for (const c of checks) {
    if (!step1Providers[c.flag]) continue;
    const hasKey = Boolean(step1Providers[c.secretField]);
    providers.push({
      id: c.id,
      name: c.name,
      tier: c.tier,
      available: hasKey,
      reason: hasKey ? '' : `API key not yet saved for ${c.name}. Open Setup → Provider Setup.`,
      hasKey,
    });
  }

  return providers;
}

/**
 * Run all detections and return a combined list of ServiceStatus objects.
 * Safe to call from any environment (gracefully handles probe failures).
 */
export async function detectAllServices(setupState = {}) {
  const backendUrl = getBackendUrl();
  const step1 = setupState.step1_providers || {};
  const ollamaUrl = step1.ollama_base_url || OLLAMA_DEFAULT_URL;

  const [backend, ollama] = await Promise.all([
    detectBackend(backendUrl),
    step1.use_ollama !== false ? detectOllama(ollamaUrl) : Promise.resolve(null),
  ]);

  const cloud = detectCloudProvidersFromSetupState(step1);

  return [
    backend,
    ...(ollama ? [ollama] : []),
    ...cloud,
  ].filter(Boolean);
}

/**
 * Returns a human-readable summary of detected services for the UI.
 * Groups by tier and counts available vs total.
 */
export function summarizeServices(services) {
  const byTier = {};
  for (const s of services) {
    if (!byTier[s.tier]) byTier[s.tier] = { available: 0, total: 0, items: [] };
    byTier[s.tier].total++;
    if (s.available) byTier[s.tier].available++;
    byTier[s.tier].items.push(s);
  }
  return byTier;
}
