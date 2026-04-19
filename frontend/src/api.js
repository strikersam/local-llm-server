import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_BACKEND_URL || '',
  headers: { 'Content-Type': 'application/json' },
});

// Attach Bearer token to every request
API.interceptors.request.use((config) => {
  const token = localStorage.getItem('access_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
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
export const login = (email, password) => API.post('/ui/api/auth/login', { email, password });
export const logout = () => {
  localStorage.removeItem('access_token');
  localStorage.removeItem('refresh_token');
  return Promise.resolve();
};
export const getMe = () => API.get('/ui/api/auth/me');

// Chat
export const chatSend = (content, sessionId, model, providerId, temperature, agentMode = false) =>
  API.post('/ui/api/chat/send', {
    content,
    session_id: sessionId,
    model: model || null,
    provider_id: providerId || null,
    temperature: temperature ?? null,
    agent_mode: agentMode,
  });
export const listSessions = () => API.get('/ui/api/chat/sessions');
export const getSession = (id) => API.get(`/ui/api/chat/sessions/${id}`);
export const deleteSession = (id) => API.delete(`/ui/api/chat/sessions/${id}`);

// Wiki
export const listWikiPages = (q) => API.get('/ui/api/wiki/pages', { params: q ? { q } : {} });
export const getWikiPage = (slug) => API.get(`/ui/api/wiki/pages/${slug}`);
export const createWikiPage = (data) => API.post('/ui/api/wiki/pages', data);
export const updateWikiPage = (slug, data) => API.put(`/ui/api/wiki/pages/${slug}`, data);
export const deleteWikiPage = (slug) => API.delete(`/ui/api/wiki/pages/${slug}`);
export const lintWiki = () => API.post('/ui/api/wiki/lint');

// Sources
export const ingestSource = (formData) => API.post('/ui/api/sources/ingest', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const listSources = () => API.get('/ui/api/sources');
export const getSource = (id) => API.get(`/ui/api/sources/${id}`);
export const deleteSource = (id) => API.delete(`/ui/api/sources/${id}`);

// Activity & Stats
export const getActivity = (limit = 50) => API.get('/ui/api/activity', { params: { limit } });
export const getStats = () => API.get('/ui/api/stats');

// Providers
export const listProviders = () => API.get('/ui/api/providers');
export const createProvider = (data) => API.post('/ui/api/providers', data);
export const updateProvider = (id, data) => API.put(`/ui/api/providers/${id}`, data);
export const deleteProvider = (id) => API.delete(`/ui/api/providers/${id}`);
export const testProvider = (id) => API.post(`/ui/api/providers/${id}/test`);
export const listProviderModels = (id) => API.get(`/ui/api/providers/${encodeURIComponent(id)}/models`);

// Models
export const listModels = () => API.get('/ui/api/models');
export const pullModel = (name) => API.post('/ui/api/models/pull', { name });
export const deleteModel = (name) => API.delete(`/ui/api/models/${encodeURIComponent(name)}`);

// API key management lives in the admin portal (AdminPortalPage) and talks
// to /admin/api/users/* directly. The legacy /api/keys helpers were removed
// when ApiKeysPage.js was consolidated into AdminPortalPage.

// Observability
export const getObservabilityStatus = () => API.get('/ui/api/observability/status');
export const getObservabilityMetrics = () => API.get('/ui/api/observability/metrics');
export const getObservabilityDashboard = () => API.get('/ui/api/observability/dashboard-url');

// Platform
export const getPlatformInfo = () => API.get('/ui/api/platform');
export const healthCheck = () => API.get('/ui/api/health');

// GitHub Integration
export const githubStatus = () => API.get('/ui/api/github/status');
export const getGithubStatus = githubStatus; // alias used by GitHubAccessSection
export const startGithubOAuth = (redirect = false) =>
  API.post('/ui/api/github/oauth/start', null, redirect ? { params: { redirect: 'true' } } : {});
export const setGithubToken = (token) => API.put('/ui/api/github/token', { token });
export const deleteGithubToken = () => API.delete('/ui/api/github/token');
export const listGithubRepos = (q = '', page = 1) => API.get('/ui/api/github/repos', { params: { q, page } });
export const listGithubBranches = (owner, repo) => API.get(`/ui/api/github/repos/${owner}/${repo}/branches`);
export const getGithubTree = (owner, repo, ref = 'HEAD', path = '') =>
  API.get(`/ui/api/github/repos/${owner}/${repo}/tree`, { params: { ref, path } });
export const readGithubFile = (owner, repo, path, ref = 'HEAD') =>
  API.get(`/ui/api/github/repos/${owner}/${repo}/file`, { params: { path, ref } });
export const writeGithubFile = (owner, repo, data) =>
  API.put(`/ui/api/github/repos/${owner}/${repo}/file`, data);
export const listGithubPulls = (owner, repo, state = 'open') =>
  API.get(`/ui/api/github/repos/${owner}/${repo}/pulls`, { params: { state } });
export const createGithubPR = (owner, repo, data) =>
  API.post(`/ui/api/github/repos/${owner}/${repo}/pulls`, data);
export const authorizeGithubRepos = (repoNames) => API.post('/ui/api/github/authorize-repos', { repo_names: repoNames });

export default API;
