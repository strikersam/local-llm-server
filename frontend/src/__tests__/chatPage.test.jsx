import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

const mockNavigate = jest.fn();
let mockParams = {};

jest.mock('react-markdown', () => ({
  __esModule: true,
  default: ({ children }) => <div>{children}</div>,
}));

jest.mock('remark-gfm', () => ({
  __esModule: true,
  default: () => null,
}));

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useParams: () => mockParams,
}));

jest.mock('../api', () => ({
  chatSend: jest.fn(),
  createSchedule: jest.fn(),
  createTask: jest.fn(),
  deleteSession: jest.fn(),
  fmtErr: (value) => value?.message || String(value),
  getBackendUrl: jest.fn(() => ''),
  getGithubStatus: jest.fn(),
  getSession: jest.fn(),
  listProviderModels: jest.fn(),
  listProviders: jest.fn(),
  listSessions: jest.fn(),
}));

import ChatPage from '../pages/ChatPage';

const {
  chatSend,
  createSchedule,
  createTask,
  getGithubStatus,
  getSession,
  listProviderModels,
  listProviders,
  listSessions,
} = require('../api');

beforeEach(() => {
  jest.clearAllMocks();
  mockParams = {};
  localStorage.clear();
  window.HTMLElement.prototype.scrollIntoView = jest.fn();
  global.fetch = jest.fn().mockResolvedValue({
    ok: true,
    json: async () => ({ has_events: false, agents: [], tool_calls: [], latest_summary: '', latest_error: '' }),
  });
  global.EventSource = class MockEventSource {
    constructor() {
      this.close = jest.fn();
    }
  };
  listSessions.mockResolvedValue({ data: { sessions: [] } });
  getGithubStatus.mockResolvedValue({ data: { connected: false, login: null, github_login: null } });
  getSession.mockResolvedValue({ data: { messages: [] } });
  listProviders.mockResolvedValue({
    data: {
      providers: [
        { provider_id: 'nvidia-nim', name: 'Nvidia NIM', is_default: true },
      ],
    },
  });
  listProviderModels.mockResolvedValue({ data: { models: ['nvidia/nemotron-3-super-120b-a12b'] } });
});

test('shows an Agent Mode retry action for direct-chat handoff responses', async () => {
  chatSend
    .mockResolvedValueOnce({
      data: {
        session_id: 'session-123',
        response: 'This request needs Agent Mode because it involves repository / file changes.',
        assistant_meta: {
          recommended_mode: 'agent',
          retryable_prompt: 'Open a PR for this fix',
        },
      },
    })
    .mockResolvedValueOnce({
      data: {
        session_id: 'session-123',
        response: 'Agent answer',
      },
    });

  render(<ChatPage />);

  const user = userEvent.setup();
  await user.type(screen.getByTestId('chat-input'), 'Open a PR for this fix');
  await user.click(screen.getByTestId('chat-send-button'));

  expect(await screen.findByText(/needs Agent Mode/i)).toBeInTheDocument();
  await user.click(screen.getByTestId('retry-with-agent-mode-button'));

  await waitFor(() => expect(chatSend).toHaveBeenCalledTimes(2));
  expect(chatSend.mock.calls[1][0]).toBe('Open a PR for this fix');
  expect(chatSend.mock.calls[1][1]).toBe('session-123');
  expect(chatSend.mock.calls[1][5]).toBe(true);
  expect(await screen.findByText('Agent answer')).toBeInTheDocument();
});

test('shows a preflight banner before send for repo tasks in direct chat', async () => {
  render(<ChatPage />);

  const user = userEvent.setup();
  await user.type(screen.getByTestId('chat-input'), 'Clone my GitHub repo, run tests, and open a pull request.');

  expect(await screen.findByTestId('agent-mode-preflight-banner')).toBeInTheDocument();
  expect(screen.getByText(/Agent Mode recommended before send/i)).toBeInTheDocument();
  expect(screen.getByTestId('preflight-open-settings-button')).toBeInTheDocument();
  expect(screen.getByTestId('preflight-create-task-button')).toBeInTheDocument();
});

test('preflight banner can create a tracked task for follow-up work', async () => {
  createTask.mockResolvedValueOnce({
    data: {
      task: {
        task_id: 'task_123',
        title: 'Clone my GitHub repo, run tests, and open a pull request',
      },
    },
  });

  render(<ChatPage />);

  const user = userEvent.setup();
  await user.type(screen.getByTestId('chat-input'), 'Clone my GitHub repo, run tests, and open a pull request.');
  await user.click(await screen.findByTestId('preflight-create-task-button'));

  await waitFor(() => expect(createTask).toHaveBeenCalledTimes(1));
  expect(createTask.mock.calls[0][0]).toMatchObject({
    title: expect.stringContaining('Clone my GitHub repo'),
    prompt: 'Clone my GitHub repo, run tests, and open a pull request.',
    task_type: 'repository_change',
  });
  expect(mockNavigate).toHaveBeenCalledWith('/tasks');
});

test('preflight banner can create a recurring schedule for automation prompts', async () => {
  createSchedule.mockResolvedValueOnce({
    data: {
      id: 'job_123',
      name: 'Daily: Every day clone my GitHub repo and open a pull request…',
    },
  });

  render(<ChatPage />);

  const user = userEvent.setup();
  await user.type(screen.getByTestId('chat-input'), 'Every day clone my GitHub repo, run tests, and open a pull request.');
  await user.click(await screen.findByTestId('preflight-create-schedule-button'));

  await waitFor(() => expect(createSchedule).toHaveBeenCalledTimes(1));
  expect(createSchedule.mock.calls[0][0]).toMatchObject({
    cron: '0 9 * * *',
    instruction: 'Every day clone my GitHub repo, run tests, and open a pull request.',
  });
  expect(mockNavigate).toHaveBeenCalledWith('/schedules');
});

test('preflight banner can enable Agent Mode before sending', async () => {
  chatSend.mockResolvedValueOnce({
    data: {
      session_id: 'session-999',
      response: 'Agent answer',
    },
  });

  render(<ChatPage />);

  const user = userEvent.setup();
  await user.type(screen.getByTestId('chat-input'), 'Fix the Dockerfile, run tests, and open a PR.');
  await user.click(await screen.findByTestId('preflight-enable-agent-mode-button'));
  await user.click(screen.getByTestId('chat-send-button'));

  await waitFor(() => expect(chatSend).toHaveBeenCalledTimes(1));
  expect(chatSend.mock.calls[0][5]).toBe(true);
});

test('restores persisted Agent Mode handoff actions when reopening a session', async () => {
  mockParams = { sessionId: 'session-789' };
  getSession.mockResolvedValueOnce({
    data: {
      _id: 'session-789',
      title: 'Saved handoff',
      messages: [
        {
          role: 'assistant',
          content: 'This request needs Agent Mode because it involves GitHub branch / PR actions.',
          assistant_meta: {
            recommended_mode: 'agent',
            retryable_prompt: 'Clone my repo and open a PR',
            workflow_suggestions: [
              {
                kind: 'task',
                payload: { title: 'Clone my repo and open a PR', prompt: 'Clone my repo and open a PR' },
              },
            ],
            settings_route: '/settings',
          },
        },
      ],
    },
  });

  render(<ChatPage />);

  expect(await screen.findByTestId('agent-handoff-actions')).toBeInTheDocument();
  expect(screen.getByTestId('retry-with-agent-mode-button')).toBeInTheDocument();
  expect(screen.getByTestId('agent-handoff-create-task-button')).toBeInTheDocument();
  expect(screen.getByTestId('agent-handoff-settings-button')).toBeInTheDocument();
});

test('offers a settings shortcut when GitHub access is required', async () => {
  chatSend.mockResolvedValueOnce({
    data: {
      session_id: 'session-456',
      response: 'This request needs Agent Mode because it involves GitHub branch / PR actions.',
      assistant_meta: {
        recommended_mode: 'agent',
        retryable_prompt: 'Clone my repo and open a PR',
        settings_route: '/settings',
      },
    },
  });

  render(<ChatPage />);

  const user = userEvent.setup();
  await user.type(screen.getByTestId('chat-input'), 'Clone my repo and open a PR');
  await user.click(screen.getByTestId('chat-send-button'));

  expect(await screen.findByTestId('agent-handoff-settings-button')).toBeInTheDocument();
  await user.click(screen.getByTestId('agent-handoff-settings-button'));

  expect(mockNavigate).toHaveBeenCalledWith('/settings');
});

test('renders the live agent workspace when session telemetry exists', async () => {
  mockParams = { sessionId: 'session-live' };
  getSession.mockResolvedValueOnce({
    data: {
      _id: 'session-live',
      title: 'Agent run',
      messages: [
        { role: 'user', content: 'Fix the failing tests' },
        { role: 'assistant', content: 'Done.' },
      ],
    },
  });
  global.fetch.mockResolvedValue({
    ok: true,
    json: async () => ({
      has_events: true,
      latest_summary: 'Tracked the full agent run.',
      latest_error: '',
      agents: [
        { id: 'planner', name: 'Planner', role: 'planner', status: 'done' },
      ],
      tool_calls: [
        { id: 'tool-1', tool_name: 'read_file', agent: 'implementer', status: 'success', output: 'ok' },
      ],
    }),
  });

  render(<ChatPage />);

  expect(await screen.findByTestId('agent-console')).toBeInTheDocument();
  expect(screen.getByText(/live agent workspace/i)).toBeInTheDocument();
  expect(screen.getByText(/tracked the full agent run/i)).toBeInTheDocument();
});
