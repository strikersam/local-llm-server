/**
 * Tests for the serviceDetection utility.
 *
 * We mock `fetch` and the api module to control what each probe returns,
 * then verify that detectAllServices / detectCloudProvidersFromSetupState
 * return the expected ServiceStatus objects.
 */

import {
  detectOllama,
  detectBackend,
  detectCloudProvidersFromSetupState,
  detectAllServices,
  summarizeServices,
} from '../utils/serviceDetection';

// ─── Mocks ────────────────────────────────────────────────────────────────────

// Mock the api module so getBackendUrl returns a controllable value
jest.mock('../api', () => ({
  getBackendUrl: jest.fn(() => ''),
}));

const { getBackendUrl } = require('../api');

// Save original fetch
const originalFetch = global.fetch;

function mockFetch(responses) {
  // responses: Map of url-substring → { ok, status } | Error
  global.fetch = jest.fn(async (url) => {
    for (const [key, val] of Object.entries(responses)) {
      if (url.includes(key)) {
        if (val instanceof Error) throw val;
        return { ok: val.ok, status: val.status ?? (val.ok ? 200 : 500) };
      }
    }
    throw new Error(`Unexpected fetch: ${url}`);
  });
}

afterEach(() => {
  global.fetch = originalFetch;
  jest.clearAllMocks();
});

// ─── detectBackend ─────────────────────────────────────────────────────────────

describe('detectBackend', () => {
  test('returns available=true when health endpoint responds 200', async () => {
    mockFetch({ '/api/health': { ok: true } });
    const result = await detectBackend('http://localhost:8000');
    expect(result.available).toBe(true);
    expect(result.id).toBe('backend');
    expect(result.tier).toBe('remote');
  });

  test('returns available=false when health endpoint errors', async () => {
    mockFetch({ '/api/health': new Error('ECONNREFUSED') });
    const result = await detectBackend('http://localhost:8000');
    expect(result.available).toBe(false);
    expect(result.reason).toMatch(/not reachable/i);
  });

  test('returns available=false with explanation when no URL configured', async () => {
    getBackendUrl.mockReturnValue('');
    const result = await detectBackend('');
    expect(result.available).toBe(false);
    expect(result.reason).toMatch(/no backend url/i);
  });

  test('uses getBackendUrl fallback when no argument passed', async () => {
    getBackendUrl.mockReturnValue('http://my-server:8000');
    mockFetch({ '/api/health': { ok: true } });
    const result = await detectBackend();
    expect(result.available).toBe(true);
  });
});

// ─── detectOllama ─────────────────────────────────────────────────────────────

describe('detectOllama', () => {
  beforeAll(() => {
    // Simulate local environment
    Object.defineProperty(window, 'location', {
      value: { hostname: 'localhost' },
      writable: true,
    });
  });

  test('returns available=true when Ollama /api/tags responds 200', async () => {
    mockFetch({ '/api/tags': { ok: true } });
    const result = await detectOllama('http://localhost:11434');
    expect(result.available).toBe(true);
    expect(result.id).toBe('ollama');
    expect(result.tier).toBe('local');
  });

  test('returns available=false when Ollama is not running', async () => {
    mockFetch({ '/api/tags': new Error('Failed to fetch') });
    const result = await detectOllama('http://localhost:11434');
    expect(result.available).toBe(false);
    expect(result.reason).toMatch(/cannot reach ollama/i);
  });
});

// ─── detectCloudProvidersFromSetupState ───────────────────────────────────────

describe('detectCloudProvidersFromSetupState', () => {
  test('returns empty list when no providers enabled', () => {
    const result = detectCloudProvidersFromSetupState({});
    expect(result).toHaveLength(0);
  });

  test('marks anthropic as available when use_anthropic=true and secret saved', () => {
    const step1 = { use_anthropic: true, anthropic_secret_id: 'sec_abc123' };
    const result = detectCloudProvidersFromSetupState(step1);
    const anthropic = result.find(p => p.id === 'anthropic');
    expect(anthropic).toBeDefined();
    expect(anthropic.available).toBe(true);
    expect(anthropic.hasKey).toBe(true);
  });

  test('marks openai as unavailable when use_openai=true but no key saved', () => {
    const step1 = { use_openai: true };
    const result = detectCloudProvidersFromSetupState(step1);
    const openai = result.find(p => p.id === 'openai');
    expect(openai).toBeDefined();
    expect(openai.available).toBe(false);
    expect(openai.hasKey).toBe(false);
    expect(openai.reason).toMatch(/api key not yet saved/i);
  });

  test('detects multiple providers', () => {
    const step1 = {
      use_anthropic: true, anthropic_secret_id: 's1',
      use_openai: true,    openai_secret_id: 's2',
      use_google: true,    // no key
    };
    const result = detectCloudProvidersFromSetupState(step1);
    expect(result).toHaveLength(3);
    expect(result.filter(p => p.available)).toHaveLength(2);
  });

  test('ignores providers with flag=false', () => {
    const step1 = { use_anthropic: false, use_openai: false };
    const result = detectCloudProvidersFromSetupState(step1);
    expect(result).toHaveLength(0);
  });
});

// ─── detectAllServices ────────────────────────────────────────────────────────

describe('detectAllServices', () => {
  beforeEach(() => {
    Object.defineProperty(window, 'location', {
      value: { hostname: 'localhost' },
      writable: true,
    });
    getBackendUrl.mockReturnValue('http://localhost:8000');
  });

  test('combines backend + ollama + cloud results', async () => {
    mockFetch({
      '/api/health': { ok: true },
      '/api/tags':   { ok: true },
    });
    const state = {
      step1_providers: {
        use_ollama: true,
        ollama_base_url: 'http://localhost:11434',
        use_anthropic: true,
        anthropic_secret_id: 'sec123',
      },
    };
    const services = await detectAllServices(state);
    expect(services.find(s => s.id === 'backend')).toBeDefined();
    expect(services.find(s => s.id === 'ollama')).toBeDefined();
    expect(services.find(s => s.id === 'anthropic')).toBeDefined();
  });

  test('omits ollama entry when use_ollama is false', async () => {
    mockFetch({ '/api/health': { ok: true } });
    const state = { step1_providers: { use_ollama: false } };
    const services = await detectAllServices(state);
    expect(services.find(s => s.id === 'ollama')).toBeUndefined();
  });

  test('handles empty setup state gracefully', async () => {
    mockFetch({
      '/api/health': new Error('offline'),
      '/api/tags':   new Error('offline'),
    });
    const services = await detectAllServices({});
    expect(services).toBeInstanceOf(Array);
    expect(services.find(s => s.id === 'backend')?.available).toBe(false);
  });
});

// ─── summarizeServices ────────────────────────────────────────────────────────

describe('summarizeServices', () => {
  test('groups by tier with counts', () => {
    const services = [
      { id: 'backend', tier: 'remote', available: true },
      { id: 'ollama',  tier: 'local',  available: false },
      { id: 'anthropic', tier: 'cloud', available: true },
      { id: 'openai',    tier: 'cloud', available: true },
    ];
    const summary = summarizeServices(services);
    expect(summary.remote.total).toBe(1);
    expect(summary.remote.available).toBe(1);
    expect(summary.local.available).toBe(0);
    expect(summary.cloud.total).toBe(2);
    expect(summary.cloud.available).toBe(2);
  });

  test('returns empty object for empty services', () => {
    expect(summarizeServices([])).toEqual({});
  });
});
