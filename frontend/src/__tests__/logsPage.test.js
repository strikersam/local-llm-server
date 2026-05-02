import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import LogsPage from '../pages/LogsPage';

jest.mock('../api', () => ({
  getActivity: jest.fn(),
  getStats: jest.fn(),
  getDecisionLog: jest.fn(),
  getSavings: jest.fn(),
  getUsage: jest.fn(),
  fmtErr: (value) => value?.message || String(value),
}));

const { getActivity, getStats, getDecisionLog, getSavings, getUsage } = require('../api');

beforeEach(() => {
  getDecisionLog.mockResolvedValue({ data: { decisions: [] } });
  getActivity.mockResolvedValue({
    data: {
      logs: [
        {
          _id: 'log_1',
          category: 'wiki',
          message: 'Wiki page updated',
          created_at: '2026-05-02T20:00:00Z',
        },
      ],
    },
  });
  getStats.mockResolvedValue({ data: { total_tokens: 0, escalations: 0, requests_24h: 0, providers: [] } });
  getSavings.mockResolvedValue({
    data: {
      summary: {
        total_savings_usd: 12.5,
        total_tokens: 4200,
        total_requests: 7,
        total_infra_cost_usd: 0.21,
        total_commercial_eq_usd: 12.71,
      },
      time_series: [
        { timestamp: 1714608000, savings_usd: 5.25 },
      ],
    },
  });
  getUsage.mockResolvedValue({
    data: {
      total_requests: 7,
      total_tokens: 4200,
      local_ratio: 1,
      escalations: 0,
      by_model: {
        'qwen3-coder:30b': { requests: 7, tokens: 4200, savings_usd: 12.5 },
      },
    },
  });
});

afterEach(() => {
  jest.clearAllMocks();
});

test('activity tab renders backend activity logs payloads', async () => {
  const user = userEvent.setup();
  render(<LogsPage />);

  await user.click(screen.getByRole('button', { name: /activity/i }));

  expect(await screen.findByText('Wiki page updated')).toBeInTheDocument();
});

test('metrics tab renders summary data from savings and usage endpoints', async () => {
  const user = userEvent.setup();
  render(<LogsPage />);

  await user.click(screen.getByRole('button', { name: /metrics & savings/i }));

  await waitFor(() => expect(getSavings).toHaveBeenCalled());
  expect(await screen.findAllByText('$12.50')).toHaveLength(2);
  expect(screen.getByText('7')).toBeInTheDocument();
  expect(screen.getByText('4.2k')).toBeInTheDocument();
  expect(screen.getByText('100%')).toBeInTheDocument();
});
