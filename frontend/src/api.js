import axios from 'axios';

export function getBackendUrl() {
  return localStorage.getItem('backend_url') || process.env.REACT_APP_BACKEND_URL || '';
}

export function setBackendUrl(url) {
  const cleaned = url.replace(/\/$/, '');
  localStorage.setItem('backend_url', cleaned);
  API.defaults.baseURL = cleaned;
}

const API = axios.create({
  baseURL: getBackendUrl(),
  headers: { 'Content-Type': 'application/json' },
});

// Attach Bearer token and resolve dynamic backend URL on every request
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  // Always use the latest stored backend URL (user may change it in setup wizard)
  if (!config.baseURL || config.baseURL === '') {
    config.baseURL = getBackendUrl();
  }
  return config;
});

// On 401, try refreshing the token once
let isRefreshing = false;
API.interceptors.response.use(
  (res) => res,
  async (error) => {
    const orig = error.config;
    if (error.response?.status === 401 && !orig._retry && !orig.url?.includes('/auth/')) {
      orig._retry = true;
      const refresh = localStorage.getItem('refresh_token');
      if (refresh && !isRefreshing) {
        isRefreshing = true;
        try {
          const { data } = await axios.post(
            `${process.env.REACT_APP_BACKEND_URL || ''}/api/auth/refresh`,
            { refresh_token: refresh },
          );
          localStorage.setItem('access_token', data.access_token);
          orig.headers.Authorization = `Bearer ${data.access_token}`;
          return API(orig);
        } catch {
          localStorage.removeItem('access_token');
          localStorage.removeItem('refresh_token');
          window.location.href = '/login';
        } finally {
          isRefreshing = false;
        }
      }
    }
    return Promise.reject(error);
  }
);

export function fmtErr(detail) {
  if (detail == null) return 'Something went wrong.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(e => e?.msg || JSON.stringify(e)).join(' ');
  return detail?.msg || String(detail);
}

// Auth
export const login = (email, password) => API.post('/api/auth/login', { email, password });
export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  return Promise.resolve();
};
export const getMe = () => API.get('/api/auth/me');

// Chat
export const chatSend = (content, sessionId, model, providerId, temperature, agentMode = false) =>
  API.post('/api/chat/send', {
    content,
    session_id: sessionId,
    model: model || null,
    provider_id: providerId || null,
    temperature: temperature ?? null,
    agent_mode: agentMode,
  });
export const listSessions = () => API.get('/api/chat/sessions');
export const getSession = (id) => API.get(`/api/chat/sessions/${id}`);
export const deleteSession = (id) => API.delete(`/api/chat/sessions/${id}`);

// Wiki
export const listWikiPages = (q) => API.get('/api/wiki/pages', { params: q ? { q } : {} });
export const getWikiPage = (slug) => API.get(`/api/wiki/pages/${slug}`);
export const createWikiPage = (data) => API.post('/api/wiki/pages', data);
export const updateWikiPage = (slug, data) => API.put(`/api/wiki/pages/${slug}`, data);
export const deleteWikiPage = (slug) => API.delete(`/api/wiki/pages/${slug}`);
export const lintWiki = () => API.post('/api/wiki/lint');

// Sources
export const ingestSource = (formData) => API.post('/api/sources/ingest', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const listSources = () => API.get('/api/sources');
export const getSource = (id) => API.get(`/api/sources/${id}`);
export const deleteSource = (id) => API.delete(`/api/sources/${id}`);

// Activity & Stats
export const getActivity = (limit = 50) => API.get('/api/activity', { params: { limit } });
export const getStats = () => API.get('/api/stats');

// Providers
export const listProviders = () => API.get('/api/providers');
export const createProvider = (data) => API.post('/api/providers', data);
export const updateProvider = (id, data) => API.put(`/api/providers/${id}`, data);
export const deleteProvider = (id) => API.delete(`/api/providers/${id}`);
export const testProvider = (id) => API.post(`/api/providers/${id}/test`);
export const listProviderModels = (id) => API.get(`/api/providers/${encodeURIComponent(id)}/models`);

// Models
export const listModels = () => API.get('/api/models');
export const pullModel = (name) => API.post('/api/models/pull', { name });
export const deleteModel = (name) => API.delete(`/api/models/${encodeURIComponent(name)}`);

// API key management lives in the admin portal (AdminPortalPage) and talks
// to /admin/api/users/* directly. The legacy /api/keys helpers were removed
// when ApiKeysPage.js was consolidated into AdminPortalPage.

// Observability
export const getObservabilityStatus = () => API.get('/api/observability/status');
export const getObservabilityMetrics = () => API.get('/api/observability/metrics');
export const getObservabilityDashboard = () => API.get('/api/observability/dashboard-url');

// Platform
export const getPlatformInfo = () => API.get('/api/platform');
export const healthCheck = () => API.get('/api/health');

// GitHub Integration
export const githubStatus = () => API.get('/api/github/status');
export const getGithubStatus = githubStatus; // alias used by GitHubAccessSection
export const startGithubOAuth = (redirect = false) =>
  API.post('/api/github/oauth/start', null, redirect ? { params: { redirect: 'true' } } : {});
export const setGithubToken = (token) => API.put('/api/github/token', { token });
export const deleteGithubToken = () => API.delete('/api/github/token');
export const listGithubRepos = (q = '', page = 1) => API.get('/api/github/repos', { params: { q, page } });
export const listGithubBranches = (owner, repo) => API.get(`/api/github/repos/${owner}/${repo}/branches`);
export const getGithubTree = (owner, repo, ref = 'HEAD', path = '') =>
  API.get(`/api/github/repos/${owner}/${repo}/tree`, { params: { ref, path } });
export const readGithubFile = (owner, repo, path, ref = 'HEAD') =>
  API.get(`/api/github/repos/${owner}/${repo}/file`, { params: { path, ref } });
export const writeGithubFile = (owner, repo, data) =>
  API.put(`/api/github/repos/${owner}/${repo}/file`, data);
export const listGithubPulls = (owner, repo, state = 'open') =>
  API.get(`/api/github/repos/${owner}/${repo}/pulls`, { params: { state } });
export const createGithubPR = (owner, repo, data) =>
  API.post(`/api/github/repos/${owner}/${repo}/pulls`, data);
export const authorizeGithubRepos = (repoNames) => API.post('/api/github/authorize-repos', { repo_names: repoNames });

// ── Runtimes (v3) ─────────────────────────────────────────────────────────────
export const listRuntimes = () => API.get('/runtimes/');
export const getRuntime = (id) => API.get(`/runtimes/${id}`);
export const getRuntimeHealth = () => API.get('/runtimes/health');
export const getRoutingPolicy = () => API.get('/runtimes/policy');
export const updateRoutingPolicy = (data) => API.put('/runtimes/policy', data);
export const getDecisionLog = (limit = 100) => API.get('/runtimes/decisions', { params: { limit } });
export const runTaskOnRuntime = (runtimeId, data) => API.post(`/runtimes/${runtimeId}/run`, data);

// ── Tasks (v3) ────────────────────────────────────────────────────────────────
export const listTasks = (params = {}) => API.get('/api/tasks/', { params });
export const createTask = (data) => API.post('/api/tasks/', data);
export const getTask = (id) => API.get(`/api/tasks/${id}`);
export const updateTask = (id, data) => API.patch(`/api/tasks/${id}`, data);
export const deleteTask = (id) => API.delete(`/api/tasks/${id}`);
export const retryTask = (id) => API.post(`/api/tasks/${id}/retry`);
export const escalateTask = (id) => API.post(`/api/tasks/${id}/escalate`);
export const addTaskComment = (id, data) => API.post(`/api/tasks/${id}/comments`, data);
export const approveTaskCheckpoint = (id, data) => API.post(`/api/tasks/${id}/approve`, data);
export const getTaskCounts = () => API.get('/api/tasks/counts');
export const getDueSoonTasks = (withinHours = 24) =>
  API.get('/api/tasks/due-soon', { params: { within_hours: withinHours } });

// ── Agents (v3) ───────────────────────────────────────────────────────────────
export const listAgents = () => API.get('/api/agents/');
export const createAgent = (data) => API.post('/api/agents/', data);
export const getAgent = (id) => API.get(`/api/agents/${id}`);
export const updateAgent = (id, data) => API.put(`/api/agents/${id}`, data);
export const deleteAgent = (id) => API.delete(`/api/agents/${id}`);

// ── Audit log (v3) ────────────────────────────────────────────────────────────
export const getAuditLog = (limit = 100) => API.get('/api/audit-log', { params: { limit } });

// ── Hardware (v3.1) ───────────────────────────────────────────────────────────
export const getHardwareProfile = () => API.get('/api/hardware/profile');
export const refreshHardwareProfile = () => API.get('/api/hardware/profile/refresh');
export const checkModelCompatibility = (modelName) =>
  API.get(`/api/hardware/compatibility/${encodeURIComponent(modelName)}`);
export const batchModelCompatibility = (models) =>
  API.post('/api/hardware/compatibility/batch', { models });

// ── Secrets (v3.1) ────────────────────────────────────────────────────────────
export const listSecrets = () => API.get('/api/secrets/');
export const createSecret = (data) => API.post('/api/secrets/', data);
export const getSecretMeta = (id) => API.get(`/api/secrets/${id}`);
export const updateSecret = (id, data) => API.put(`/api/secrets/${id}`, data);
export const deleteSecret = (id) => API.delete(`/api/secrets/${id}`);

// ── Social auth (v3.1) ────────────────────────────────────────────────────────
export const listUsers = () => API.get('/api/auth/users');
export const changeUserRole = (userId, role) =>
  API.post(`/api/auth/users/${userId}/role`, { role });

// ── Setup wizard (v3.1) ───────────────────────────────────────────────────────
export const getSetupState = () => API.get('/api/setup/state');
export const saveSetupStep = (step, data) => API.put(`/api/setup/step/${step}`, data);
export const completeSetup = () => API.post('/api/setup/complete');
export const detectHardwareForSetup = () => API.get('/api/setup/detect/hardware');
export const detectModelsForSetup = (ollamaUrl) =>
  API.get('/api/setup/detect/models', { params: { ollama_url: ollamaUrl } });

// ── Cost insights / observability (v3.1) ──────────────────────────────────────
export const getSavings = (period = 'month', bucket = 'day') =>
  API.get('/api/observability/savings', { params: { period, bucket } });
export const getUserSavings = (userId, period = 'month') =>
  API.get(`/api/observability/savings/${userId}`, { params: { period } });
export const getUsage = (period = 'month') =>
  API.get('/api/observability/usage', { params: { period } });

// ── GitHub workspace (v3.1) ───────────────────────────────────────────────────
export const listGithubReposV2 = () => API.get('/api/github/repos');
export const getGithubRepo = (owner, repo) => API.get(`/api/github/repos/${owner}/${repo}`);
export const listGithubBranchesV2 = (owner, repo) =>
  API.get(`/api/github/repos/${owner}/${repo}/branches`);
export const listGithubPRs = (owner, repo, state = 'open') =>
  API.get(`/api/github/repos/${owner}/${repo}/pulls`, { params: { state } });
export const initWorkspace = (owner, repo) =>
  API.post(`/api/github/repos/${owner}/${repo}/workspace/init`);
export const getWorkspaceStatus = (owner, repo) =>
  API.get(`/api/github/repos/${owner}/${repo}/workspace/status`);
export const getWorkspaceDiff = (owner, repo) =>
  API.get(`/api/github/repos/${owner}/${repo}/workspace/diff`);
export const commitWorkspace = (owner, repo, data) =>
  API.post(`/api/github/repos/${owner}/${repo}/workspace/commit`, data);

// ── Workspace sync (v3.1) ─────────────────────────────────────────────────────
export const getSyncStatus = () => API.get('/api/sync/status');
export const listSyncPeers = () => API.get('/api/sync/peers');
export const addSyncPeer = (data) => API.post('/api/sync/peers', data);
export const removeSyncPeer = (id) => API.delete(`/api/sync/peers/${id}`);
export const pushFolder = (folder) => API.post(`/api/sync/push/${folder}`);
export const pullFolder = (folder) => API.post(`/api/sync/pull/${folder}`);
export const listSyncConflicts = () => API.get('/api/sync/conflicts');
export const resolveConflict = (id) => API.post(`/api/sync/conflicts/${id}/resolve`);

export default API;
