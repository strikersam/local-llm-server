import {
  buildAgentStatusUrl,
  buildAgentStreamUrl,
  fetchAgentWorkspaceSnapshot,
} from '../utils/agentWorkspaceTransport';

jest.mock('../api', () => ({
  getAccessToken: jest.fn(() => 'token-123'),
  getAuthHeaders: jest.fn(() => ({ Authorization: 'Bearer token-123' })),
  getBackendUrl: jest.fn(() => 'https://api.example.com'),
}));

const { getAccessToken, getAuthHeaders, getBackendUrl } = require('../api');

describe('agent workspace transport', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getAccessToken.mockReturnValue('token-123');
    getAuthHeaders.mockReturnValue({ Authorization: 'Bearer token-123' });
    getBackendUrl.mockReturnValue('https://api.example.com');
    global.fetch = jest.fn();
  });

  test('builds an authenticated stream URL for EventSource sessions', () => {
    expect(buildAgentStreamUrl('session-456')).toBe(
      'https://api.example.com/api/agent/stream?session_id=session-456&access_token=token-123',
    );
  });

  test('fetches workspace snapshots with bearer auth headers', async () => {
    global.fetch.mockResolvedValueOnce({
      ok: true,
      status: 200,
      json: async () => ({ has_events: true, agents: [{ id: 'planner' }], tool_calls: [] }),
    });

    const snapshot = await fetchAgentWorkspaceSnapshot('session-123');

    expect(global.fetch).toHaveBeenCalledWith(
      buildAgentStatusUrl('session-123'),
      { headers: { Authorization: 'Bearer token-123' } },
    );
    expect(snapshot.has_events).toBe(true);
    expect(snapshot.agents).toHaveLength(1);
  });

  test('maps 401 snapshot failures to a session-expired error', async () => {
    global.fetch.mockResolvedValueOnce({ ok: false, status: 401 });

    await expect(fetchAgentWorkspaceSnapshot('session-123')).rejects.toMatchObject({
      code: 'auth',
      message: 'Agent workspace session expired. Please sign in again.',
    });
  });
});
