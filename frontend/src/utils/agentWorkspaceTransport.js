import { getAuthHeaders, getBackendUrl, getAccessToken } from '../api';

export function buildAgentStatusUrl(sessionId) {
  const base = (getBackendUrl() || '').replace(/\/$/, '');
  return sessionId
    ? `${base}/api/agent/status?session_id=${encodeURIComponent(sessionId)}`
    : `${base}/api/agent/status`;
}

export function buildAgentStreamUrl(sessionId) {
  const base = (getBackendUrl() || '').replace(/\/$/, '');
  const params = new URLSearchParams();
  if (sessionId) params.set('session_id', sessionId);
  const accessToken = getAccessToken();
  if (accessToken) params.set('access_token', accessToken);
  const query = params.toString();
  return query ? `${base}/api/agent/stream?${query}` : `${base}/api/agent/stream`;
}

export async function fetchAgentWorkspaceSnapshot(sessionId) {
  const response = await fetch(buildAgentStatusUrl(sessionId), {
    headers: getAuthHeaders(),
  });

  if (response.status === 401) {
    const error = new Error('Agent workspace session expired. Please sign in again.');
    error.code = 'auth';
    throw error;
  }

  if (!response.ok) {
    const error = new Error(`HTTP ${response.status}`);
    error.code = 'network';
    throw error;
  }

  const data = await response.json();
  return {
    has_events: Boolean(data.has_events),
    agents: Array.isArray(data.agents) ? data.agents : [],
    tool_calls: Array.isArray(data.tool_calls) ? data.tool_calls : [],
    latest_summary: data.latest_summary || '',
    latest_error: data.latest_error || '',
  };
}

export function createAgentWorkspaceEventSource(sessionId) {
  return new EventSource(buildAgentStreamUrl(sessionId));
}
