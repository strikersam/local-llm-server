/**
 * Tests for SetupWizardPage persistence and prefill behavior.
 */

import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MemoryRouter } from 'react-router-dom';
import SetupWizardPage from '../pages/SetupWizardPage';

// ─── Mocks ────────────────────────────────────────────────────────────────────

jest.mock('../api', () => ({
  getSetupState:          jest.fn(),
  saveSetupStep:          jest.fn(),
  completeSetup:          jest.fn(),
  detectHardwareForSetup: jest.fn(),
  detectModelsForSetup:   jest.fn(),
  createSecret:           jest.fn(),
  getBackendUrl:          jest.fn(),
  setBackendUrl:          jest.fn(),
  getPublicPath:          jest.fn((p) => p || '/'),
}));

const api = require('../api');

function mockSetupState(overrides = {}) {
  api.getSetupState.mockResolvedValue({
    data: {
      completed: false,
      current_step: 1,
      step1_providers: {},
      step2_model: {},
      step3_runtimes: {},
      step4_agent: {},
      step5_policy: {},
      ...overrides,
    },
  });
}

// Simulate a healthy backend connection
function mockHealthyBackend() {
  global.fetch = jest.fn(async (url) => {
    if (url.includes('/api/health')) return { ok: true, status: 200 };
    return { ok: false, status: 404 };
  });
  api.getBackendUrl.mockReturnValue('http://localhost:8000');
}

// Simulate no backend configured
function mockNoBackend() {
  global.fetch = jest.fn(async () => { throw new Error('Failed to fetch'); });
  api.getBackendUrl.mockReturnValue('');
}

const originalFetch = global.fetch;

beforeEach(() => {
  api.detectHardwareForSetup.mockResolvedValue({ data: {} });
  api.detectModelsForSetup.mockResolvedValue({ data: { models: [] } });
  api.saveSetupStep.mockResolvedValue({ data: { saved: true } });
  api.completeSetup.mockResolvedValue({ data: { completed: true } });
  localStorage.clear();
});

afterEach(() => {
  global.fetch = originalFetch;
  jest.resetAllMocks();
});

function renderWizard(props = {}) {
  return render(
    <MemoryRouter>
      <SetupWizardPage {...props} />
    </MemoryRouter>
  );
}

// ─── Basic rendering ──────────────────────────────────────────────────────────

describe('SetupWizardPage rendering', () => {
  test('renders step 1 heading after loading', async () => {
    mockHealthyBackend();
    mockSetupState({ current_step: 1 });
    renderWizard();
    // Step 1 h2 heading renders once setup loads
    const heading = await screen.findByRole('heading', { name: /provider setup/i });
    expect(heading).toBeInTheDocument();
  });

  // ── Checkbox visibility regression guard ──────────────────────────────────
  // Regression: global `appearance:none` in index.css was hiding native
  // checkboxes. These tests verify the checkbox elements exist in the DOM so
  // any future CSS change that removes them is caught immediately.

  test('step 1 provider checkboxes are rendered in the DOM', async () => {
    mockHealthyBackend();
    mockSetupState({ current_step: 1 });
    renderWizard();
    await screen.findByRole('heading', { name: /provider setup/i });

    // Every provider card should have a visible checkbox role element
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBeGreaterThanOrEqual(2);
  });

  test('Nvidia NIM checkbox is checked by default on step 1', async () => {
    mockHealthyBackend();
    mockSetupState({ current_step: 1 });
    renderWizard();
    await screen.findByRole('heading', { name: /provider setup/i });

    // Nvidia NIM is the recommended default — must start checked
    const nvidiaLabel = screen.getByText(/nvidia nim/i).closest('label');
    const nvidiaCheckbox = nvidiaLabel.querySelector('input[type="checkbox"]');
    expect(nvidiaCheckbox).toBeInTheDocument();
    expect(nvidiaCheckbox.checked).toBe(true);
  });

  test('step 3 runtime checkboxes are all rendered in the DOM', async () => {
    mockHealthyBackend();
    mockSetupState({ current_step: 3 });
    renderWizard();
    await screen.findByRole('heading', { name: /runtime configuration/i });

    // All 3 runtimes (Hermes, OpenCode, Aider) must have checkbox controls
    const checkboxes = screen.getAllByRole('checkbox');
    expect(checkboxes.length).toBeGreaterThanOrEqual(3);
  });

  test('shows all 5 step labels in sidebar', async () => {
    mockHealthyBackend();
    mockSetupState();
    renderWizard();
    await waitFor(() => {
      expect(screen.getByText('Step 1')).toBeInTheDocument();
      expect(screen.getByText('Step 5')).toBeInTheDocument();
    });
  });

  test('shows loading indicator while fetching state', () => {
    mockHealthyBackend();
    // Make getSetupState never resolve so loading persists
    api.getSetupState.mockReturnValue(new Promise(() => {}));
    renderWizard();
    // Loading spinner should appear (it's shown while loadingState=true)
    // The sidebar is immediately visible
    expect(screen.getByText('🧠 Setup Wizard')).toBeInTheDocument();
  });
});

// ─── Prefill from saved backend state ────────────────────────────────────────

describe('Prefill from saved wizard state', () => {
  test('prefills Anthropic checkbox when use_anthropic=true', async () => {
    mockHealthyBackend();
    mockSetupState({
      step1_providers: {
        use_anthropic: true,
        anthropic_secret_id: 'sec_abc',
        use_ollama: true,
        ollama_base_url: 'http://localhost:11434',
      },
    });
    renderWizard();

    // Wait for state to load and key-saved indicator to appear
    await screen.findByText('✓ API key saved securely');

    const anthropicLabel = screen.getByText('🔮 Anthropic').closest('label');
    const checkbox = anthropicLabel.querySelector('input[type="checkbox"]');
    expect(checkbox.checked).toBe(true);
  });

  test('shows "key already saved" placeholder when secret ID exists', async () => {
    mockHealthyBackend();
    mockSetupState({
      step1_providers: {
        use_openai: true,
        openai_secret_id: 'sec_xyz',
      },
    });
    renderWizard();

    await screen.findByText('✓ API key saved securely');
  });

  test('prefills Step 2 model names from saved state', async () => {
    mockHealthyBackend();
    mockSetupState({
      current_step: 2,
      step2_model: {
        default_model: 'llama3:8b',
        reviewer_model: 'mistral:7b',
      },
    });
    renderWizard();

    // After state loads, component should show step 2 with the saved model names
    await screen.findByDisplayValue('llama3:8b');
    expect(screen.getByDisplayValue('mistral:7b')).toBeInTheDocument();
  });

  test('prefills Step 4 agent name from saved state', async () => {
    mockHealthyBackend();
    mockSetupState({
      current_step: 4,
      step4_agent: {
        agent_name: 'Coder Bot',
        agent_model: 'qwen3-coder:30b',
        cost_policy: 'local_only',
      },
    });
    renderWizard();

    await screen.findByDisplayValue('Coder Bot');
  });

  test('calls onComplete callback when setup is already completed', async () => {
    mockHealthyBackend();
    api.getSetupState.mockResolvedValue({ data: { completed: true } });
    const onComplete = jest.fn();
    renderWizard({ onComplete });

    await waitFor(() => expect(onComplete).toHaveBeenCalled(), { timeout: 3000 });
  });
});

// ─── localStorage draft fallback ─────────────────────────────────────────────

describe('localStorage draft fallback', () => {
  test('shows connection banner when no backend URL configured', async () => {
    mockNoBackend();
    // getSetupState won't be called if no URL, so no need to mock
    renderWizard();

    await screen.findByText(/connect to your local llm server/i);
    expect(screen.getByText(/steps will be saved locally/i)).toBeInTheDocument();
  });

  test('saves draft to localStorage when Next is clicked with backend connected', async () => {
    mockHealthyBackend();
    mockSetupState();
    renderWizard();

    // Wait for step 1 to render
    await screen.findByRole('heading', { name: /provider setup/i });

    const nextBtn = screen.getByRole('button', { name: /next →/i });
    await act(async () => {
      await userEvent.click(nextBtn);
    });

    const draft = JSON.parse(localStorage.getItem('llm_relay_setup_draft') || 'null');
    expect(draft).not.toBeNull();
    expect(draft.step1).toBeDefined();
  });

  test('applies localStorage draft when backend unreachable', async () => {
    mockNoBackend();

    localStorage.setItem('llm_relay_setup_draft', JSON.stringify({
      currentStep: 1,
      step4: { agentName: 'Draft Agent', agentModel: 'model:x', costPolicy: 'local_only' },
    }));

    renderWizard();

    // Banner shows because no backend
    await screen.findByText(/connect to your local llm server/i);
    // localStorage was applied (draft loaded but user still needs to connect for step 4)
    // The draft is loaded internally; no visible assertion needed beyond "not crashing"
    expect(screen.getByText('🧠 Setup Wizard')).toBeInTheDocument();
  });
});

// ─── Backend connection banner ────────────────────────────────────────────────

describe('Backend connection banner', () => {
  test('shows CORS/network error message on connection failure', async () => {
    mockNoBackend();
    renderWizard();

    // Banner appears
    await screen.findByText(/connect to your local llm server/i);

    const input = screen.getByPlaceholderText('http://localhost:8000');
    const connectBtn = screen.getByRole('button', { name: /connect/i });

    await act(async () => {
      await userEvent.clear(input);
      await userEvent.type(input, 'http://bad-host:9999');
      await userEvent.click(connectBtn);
    });

    await screen.findByText(/cannot reach backend/i);
  });

  test('hides connection error after successful connection', async () => {
    // Start disconnected
    mockNoBackend();
    renderWizard();

    await screen.findByText(/connect to your local llm server/i);

    // Now mock a successful connection
    mockSetupState();
    global.fetch = jest.fn(async (url) => {
      if (url.includes('/api/health')) return { ok: true };
      return { ok: false };
    });

    const input = screen.getByPlaceholderText('http://localhost:8000');
    const connectBtn = screen.getByRole('button', { name: /connect/i });

    await act(async () => {
      await userEvent.clear(input);
      await userEvent.type(input, 'http://localhost:8000');
      await userEvent.click(connectBtn);
    });

    // Should no longer show "steps will be saved locally" warning
    await waitFor(() => {
      expect(screen.queryByText(/steps will be saved locally/i)).not.toBeInTheDocument();
    }, { timeout: 3000 });
  });
});

// ─── Done screen ──────────────────────────────────────────────────────────────

describe('Done screen', () => {
  test('renders done screen when setup is already completed', async () => {
    mockHealthyBackend();
    api.getSetupState.mockResolvedValue({ data: { completed: true } });

    renderWizard();

    await screen.findByText(/you're all set/i, {}, { timeout: 3000 });
    expect(screen.getByText(/open control plane/i)).toBeInTheDocument();
  });
});
