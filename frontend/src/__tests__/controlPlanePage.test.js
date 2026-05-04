import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import ControlPlanePage from '../pages/ControlPlanePage';

jest.mock('../api', () => ({
  fmtErr: (value) => value?.message || String(value),
  getDecisionLog: jest.fn(),
  getDueSoonTasks: jest.fn(),
  getSavings: jest.fn(),
  getStats: jest.fn(),
  getUsage: jest.fn(),
  healthCheck: jest.fn(),
  listAgents: jest.fn(),
  listProviders: jest.fn(),
  listRuntimes: jest.fn(),
  listSchedules: jest.fn(),
  listTasks: jest.fn(),
}));

const {
  getDecisionLog,
  getDueSoonTasks,
  getSavings,
  getStats,
  getUsage,
  healthCheck,
  listAgents,
  listProviders,
  listRuntimes,
  listSchedules,
  listTasks,
} = require('../api');

function renderPage() {
  return render(
    <MemoryRouter>
      <ControlPlanePage />
    </MemoryRouter>
  );
}

beforeEach(() => {
  healthCheck.mockResolvedValue({ data: { status: 'ok', mongo: true, ollama: true, scheduler: true } });
  getStats.mockResolvedValue({
    data: {
      wiki_pages: 8,
      sources: 5,
      chat_sessions: 12,
      activity_entries: 41,
      recent_pages: [
        { title: 'Deployment Runbook', slug: 'deployment-runbook', updated_at: '2026-05-04T12:00:00Z' },
      ],
      llm_provider: 'Nvidia NIM (Free)',
      langfuse_configured: true,
    },
  });
  getUsage.mockResolvedValue({
    data: {
      total_requests: 24,
      total_tokens: 128400,
      local_ratio: 0.92,
    },
  });
  getSavings.mockResolvedValue({
    data: {
      summary: {
        total_savings_usd: 128.4,
        total_requests: 24,
        total_tokens: 128400,
      },
    },
  });
  listRuntimes.mockResolvedValue({
    data: {
      runtimes: [
        {
          runtime_id: 'hermes',
          display_name: 'Hermes',
          tier: 'first_class',
          circuit_open: false,
          health: { available: true, latency_ms: 132 },
          updated_at: '2026-05-04T12:10:00Z',
        },
      ],
    },
  });
  listTasks.mockResolvedValue({
    data: {
      tasks: [
        {
          task_id: 'task_1',
          title: 'Finish mobile nav polish',
          status: 'in_progress',
          priority: 'urgent',
          agent_id: 'engineer',
          updated_at: '2026-05-04T12:11:00Z',
        },
        {
          task_id: 'task_2',
          title: 'Review CompanyHelm parity gaps',
          status: 'blocked',
          priority: 'medium',
          updated_at: '2026-05-04T11:45:00Z',
        },
      ],
    },
  });
  getDueSoonTasks.mockResolvedValue({
    data: {
      tasks: [
        {
          task_id: 'task_due',
          title: 'Ship homepage refresh',
          due_date: Math.floor(Date.now() / 1000) + 3600,
        },
      ],
    },
  });
  getDecisionLog.mockResolvedValue({
    data: {
      decisions: [
        {
          id: 'decision_1',
          task_id: 'task_1',
          selected_runtime_id: 'internal_agent',
          model_used: 'nvidia/nemotron-3-super-120b-a12b',
          timestamp: new Date().toISOString(),
          escalated: false,
        },
      ],
    },
  });
  listAgents.mockResolvedValue({
    data: {
      agents: [
        {
          agent_id: 'agent_1',
          name: 'Engineer',
          role: 'Product engineer',
          preferred_runtime: 'hermes',
          status: 'running',
          updated_at: '2026-05-04T12:09:00Z',
        },
      ],
    },
  });
  listProviders.mockResolvedValue({
    data: {
      providers: [
        {
          provider_id: 'nvidia-nim',
          name: 'Nvidia NIM (Free)',
          default_model: 'nvidia/nemotron-3-super-120b-a12b',
          is_default: true,
          status: 'configured',
        },
        {
          provider_id: 'ollama-local',
          name: 'Ollama (Local)',
          default_model: 'qwen3-coder:30b',
          is_default: false,
          status: 'configured',
        },
      ],
    },
  });
  listSchedules.mockResolvedValue({
    data: {
      schedules: [
        {
          id: 'sched_1',
          name: 'Morning health check',
          cron: '0 8 * * *',
          status: 'active',
          updated_at: '2026-05-04T12:00:00Z',
        },
      ],
    },
  });
});

afterEach(() => {
  jest.clearAllMocks();
});

test('renders company-style dashboard summary with NVIDIA priority surfaced', async () => {
  renderPage();

  expect(await screen.findByRole('heading', { name: 'Dashboard' })).toBeInTheDocument();
  expect(screen.getByText(/CompanyHelm-style workspace command center/i)).toBeInTheDocument();

  await waitFor(() => expect(getUsage).toHaveBeenCalled());
  expect(screen.getByText('$128.40')).toBeInTheDocument();
  expect(screen.getByText('24')).toBeInTheDocument();
  expect(screen.getByText('128.4k')).toBeInTheDocument();
  expect(screen.getByText('92%')).toBeInTheDocument();
  expect(screen.getAllByText('Nvidia NIM (Free)').length).toBeGreaterThan(0);
  expect(screen.getAllByText('Priority').length).toBeGreaterThan(0);
  expect(screen.getByText('Deployment Runbook')).toBeInTheDocument();
  expect(screen.getByText('Finish mobile nav polish')).toBeInTheDocument();
  expect(screen.getByText('Morning health check')).toBeInTheDocument();
});

test('shows partial-load warning when one dashboard source fails', async () => {
  getSavings.mockRejectedValueOnce(new Error('savings offline'));

  renderPage();

  expect(await screen.findByText(/Some dashboard data could not be loaded/i)).toBeInTheDocument();
  expect(screen.getByText(/savings offline/i)).toBeInTheDocument();
});
