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

// API Keys
export const listApiKeys = () => API.get('/api/keys');
export const createApiKey = (data) => API.post('/api/keys', data);
export const deleteApiKey = (keyId) => API.delete(`/api/keys/${keyId}`);

// Observability
export const getObservabilityStatus = () => API.get('/api/observability/status');
export const getObservabilityDashboard = () => API.get('/api/observability/dashboard-url');

// Platform
export const getPlatformInfo = () => API.get('/api/platform');
export const healthCheck = () => API.get('/api/health');

export default API;
