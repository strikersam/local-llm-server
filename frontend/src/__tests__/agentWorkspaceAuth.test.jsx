import React from 'react';
import { render, waitFor } from '@testing-library/react';

jest.mock('../api', () => ({
  getAccessToken: jest.fn(() => 'token-123'),
  getAuthHeaders: jest.fn(() => ({ Authorization: 'Bearer token-123' })),
  getBackendUrl: jest.fn(() => 'https://api.example.com'),
}));

import AgentActivityFeed from '../components/AgentActivityFeed.jsx';
import AgentStatusPanel from '../components/AgentStatusPanel.jsx';

const { getAccessToken, getAuthHeaders, getBackendUrl } = require('../api');

describe('agent workspace auth transport', () => {
  beforeEach(() => {
    jest.clearAllMocks();
    getAccessToken.mockReturnValue('token-123');
    getAuthHeaders.mockReturnValue({ Authorization: 'Bearer token-123' });
    getBackendUrl.mockReturnValue('https://api.example.com');
    global.fetch = jest.fn().mockResolvedValue({
      ok: true,
      json: async () => ({ agents: [] }),
    });
    window.HTMLElement.prototype.scrollIntoView = jest.fn();
    global.EventSource = class MockEventSource {
      static instances = [];

      constructor(url) {
        this.url = url;
        this.close = jest.fn();
        MockEventSource.instances.push(this);
      }
    };
  });

  test('AgentStatusPanel sends bearer auth when polling live status', async () => {
    render(<AgentStatusPanel sessionId="session-123" />);

    await waitFor(() => expect(global.fetch).toHaveBeenCalled());
    expect(global.fetch).toHaveBeenCalledWith(
      'https://api.example.com/api/agent/status?session_id=session-123',
      { headers: { Authorization: 'Bearer token-123' } },
    );
    expect(getAuthHeaders).toHaveBeenCalled();
  });

  test('AgentActivityFeed appends the access token for EventSource auth', () => {
    render(<AgentActivityFeed sessionId="session-456" />);

    expect(global.EventSource.instances[0].url).toBe(
      'https://api.example.com/api/agent/stream?session_id=session-456&access_token=token-123',
    );
  });
});
