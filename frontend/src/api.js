import axios from 'axios';

const API = axios.create({
  baseURL: process.env.REACT_APP_BACKEND_URL || '',
  withCredentials: true,
  headers: { 'Content-Type': 'application/json' },
});

export function formatError(detail) {
  if (detail == null) return 'Something went wrong.';
  if (typeof detail === 'string') return detail;
  if (Array.isArray(detail)) return detail.map(e => e?.msg || JSON.stringify(e)).join(' ');
  if (detail?.msg) return detail.msg;
  return String(detail);
}

// Auth
export const login = (email, password) => API.post('/api/auth/login', { email, password });
export const logout = () => API.post('/api/auth/logout');
export const getMe = () => API.get('/api/auth/me');
export const refreshToken = () => API.post('/api/auth/refresh');

// Chat
export const chatSend = (content, sessionId, model) =>
  API.post('/api/chat/send', { content, session_id: sessionId, model });
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
export const ingestSource = (formData) =>
  API.post('/api/sources/ingest', formData, { headers: { 'Content-Type': 'multipart/form-data' } });
export const listSources = () => API.get('/api/sources');
export const getSource = (id) => API.get(`/api/sources/${id}`);
export const deleteSource = (id) => API.delete(`/api/sources/${id}`);

// Activity & Stats
export const getActivity = (limit = 50) => API.get('/api/activity', { params: { limit } });
export const getStats = () => API.get('/api/stats');
export const getProviders = () => API.get('/api/settings/providers');
export const healthCheck = () => API.get('/api/health');

export default API;
