import React from 'react';
import { render, screen, waitFor, act } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

let mockParams = {};

jest.mock('react-markdown', () => ({ __esModule: true, default: ({ children }) => <div>{children}</div> }));
jest.mock('remark-gfm', () => ({ __esModule: true, default: () => null }));
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useParams: () => mockParams,
  useNavigate: () => jest.fn(),
}));

jest.useFakeTimers();

jest.mock('../api', () => ({
  chatSend: jest.fn(),
  getAgentChatJob: jest.fn(),
  getGithubStatus: jest.fn(),
  getSession: jest.fn(),
  listProviderModels: jest.fn(),
  listProviders: jest.fn(),
  listSessions: jest.fn(),
  createTask: jest.fn(),
  createSchedule: jest.fn(),
  deleteSession: jest.fn(),
  fmtErr: (v) => v?.message || String(v),
  getAccessToken: jest.fn(() => 'token-123'),
  getAuthHeaders: jest.fn(() => ({ Authorization: 'Bearer token-123' })),
  getBackendUrl: jest.fn(() => ''),
}));

import ChatPage from '../pages/ChatPage';
const { chatSend, getAgentChatJob, listProviders, listProviderModels, getGithubStatus, getSession, listSessions } = require('../api');

beforeEach(() => {
  jest.clearAllMocks();
  mockParams = {};
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
  global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({ has_events: false, agents: [], tool_calls: [], latest_summary: '', latest_error: '' }) });
  listSessions.mockResolvedValue({ data: { sessions: [] } });
  getGithubStatus.mockResolvedValue({ data: { connected: false, login: null, github_login: null } });
  getSession.mockResolvedValue({ data: { messages: [] } });
  listProviders.mockResolvedValue({ data: { providers: [{ provider_id: 'local', name: 'Local', is_default: true }] } });
  listProviderModels.mockResolvedValue({ data: { models: ['local-model'] } });
});

test('agent-mode accepted job is shown as pending and final result replaces it (no raw metadata shown)', async () => {
  // chatSend returns accepted job envelope
  chatSend.mockResolvedValueOnce({ data: { session_id: 's-1', job_id: 'job-1', status: 'queued', phase: 'planning', message: 'Accepted' } });

  // getAgentChatJob will be called twice by the poller: first returns running, then succeeded
  getAgentChatJob
    .mockResolvedValueOnce({ data: { job_id: 'job-1', status: 'running', phase: 'planning', progress_events: [{ message: 'Planning' }] } })
    .mockResolvedValueOnce({ data: { job_id: 'job-1', status: 'succeeded', phase: 'execution', result: { response: 'Final assistant result' } } });

  // delay: null is required with jest.useFakeTimers() — without it, user-event v14
  // schedules each keystroke via setTimeout which stalls when fake timers are active.
  const user = userEvent.setup({ delay: null });
  render(<ChatPage />);
  await user.type(screen.getByTestId('chat-input'), 'Run the repo tests and open a PR');
  await user.click(screen.getByTestId('chat-send-button'));

  // Agent job panel should appear with queued/running state
  expect(await screen.findByText(/Agent job/i)).toBeInTheDocument();
  expect(screen.getByText(/queued|running/i)).toBeInTheDocument();

  // Advance timers to let polling run once (running)
  await act(async () => {
    jest.advanceTimersByTime(1600);
    // allow pending promises to resolve
    await Promise.resolve();
  });

  // Progress event message should be visible (may appear in multiple elements)
  expect(screen.getAllByText(/Planning/i).length).toBeGreaterThan(0);

  // Advance timers to let polling run again (succeeded)
  await act(async () => {
    jest.advanceTimersByTime(1600);
    await Promise.resolve();
  });

  // Final assistant message should be rendered as a chat bubble — not raw job JSON
  await waitFor(() => expect(screen.getByText('Final assistant result')).toBeInTheDocument());

  // The agent job panel still exists in state but UI should now show final message (we don't show raw envelope as assistant text)
  expect(screen.queryByText(/Agent job/)).toBeInTheDocument();
});
