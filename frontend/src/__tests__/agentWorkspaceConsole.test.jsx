import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';

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

jest.mock('../utils/agentWorkspaceTransport', () => ({
  createAgentWorkspaceEventSource: jest.fn(() => ({ close: jest.fn() })),
  fetchAgentWorkspaceSnapshot: jest.fn(),
}));

jest.mock('react-markdown', () => ({ __esModule: true, default: ({ children }) => <div>{children}</div> }));
jest.mock('remark-gfm', () => ({ __esModule: true, default: () => null }));
jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => jest.fn(),
  useParams: () => ({ sessionId: 'session-live' }),
}));

import ChatPage from '../pages/ChatPage';

const api = require('../api');
const transport = require('../utils/agentWorkspaceTransport');

describe('ChatPage live workspace console', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    window.HTMLElement.prototype.scrollIntoView = jest.fn();
    global.fetch = jest.fn().mockResolvedValue({ ok: true, json: async () => ({}) });
    api.listSessions.mockResolvedValue({ data: { sessions: [] } });
    api.getGithubStatus.mockResolvedValue({ data: { connected: false, login: null, github_login: null } });
    api.getSession.mockResolvedValue({ data: { _id: 'session-live', title: 'Live', messages: [{ role: 'assistant', content: 'Done.' }] } });
    api.listProviders.mockResolvedValue({ data: { providers: [{ provider_id: 'nvidia-nim', name: 'Nvidia NIM', is_default: true }] } });
    api.listProviderModels.mockResolvedValue({ data: { models: ['model-a'] } });
  });

  test('shows the CompanyHelm-style reconnect banner while live updates are offline', async () => {
    transport.fetchAgentWorkspaceSnapshot.mockRejectedValueOnce(Object.assign(new Error('HTTP 503'), { code: 'network' }));

    render(<ChatPage />);

    expect(await screen.findByTestId('agent-workspace-reconnect-banner')).toBeInTheDocument();
  });

  test('shows an auth-expired banner when the workspace snapshot returns 401', async () => {
    transport.fetchAgentWorkspaceSnapshot.mockRejectedValueOnce(Object.assign(new Error('expired'), { code: 'auth' }));

    render(<ChatPage />);

    await waitFor(() => expect(screen.getByTestId('agent-workspace-auth-banner')).toBeInTheDocument());
  });
});
