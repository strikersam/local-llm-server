// When the frontend is deployed separately (e.g. GitHub Pages), set the
// VITE_API_BASE build-time env var to the backend URL (e.g. https://your-app.onrender.com).
// When served by the proxy itself (Render single-container, local dev), leave it
// empty — relative paths work automatically.
const API_BASE: string = (import.meta as any).env?.VITE_API_BASE ?? "";

export type Provider = {
  provider_id: string;
  name: string;
  base_url: string;
  default_model?: string | null;
  default_temperature?: number;
  has_api_key?: boolean;
};

export type Workspace = {
  workspace_id: string;
  name: string;
  kind: "local" | "git";
  path: string;
  git_url?: string | null;
  git_ref?: string | null;
};

export type AgentSession = {
  session_id: string;
  title: string;
  provider_id?: string | null;
  workspace_id?: string | null;
  created_at: string;
  updated_at: string;
  history: { role: "user" | "assistant" | "system"; content: string }[];
  last_plan?: any;
  last_result?: any;
};

function authHeaders(apiKey: string | null): Record<string, string> {
  if (!apiKey) return {};
  return { Authorization: `Bearer ${apiKey}` };
}

export class ApiError extends Error {
  readonly status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
    this.name = "ApiError";
  }
}

async function apiError(r: Response): Promise<never> {
  const text = await r.text();
  let message = text || `HTTP ${r.status}`;
  try {
    const data = JSON.parse(text);
    if (typeof data.detail === "string") {
      message = data.detail;
    } else if (Array.isArray(data.detail)) {
      message = data.detail
        .map((e: any) => (typeof e === "string" ? e : e.msg ?? JSON.stringify(e)))
        .join("; ") || text;
    }
  } catch {
    // Non-JSON body — fall through to status-based message.
  }
  throw new ApiError(r.status, message);
}

export async function getBootstrap(): Promise<any> {
  const r = await fetch(`${API_BASE}/ui/api/bootstrap`);
  if (!r.ok) return apiError(r);
  return r.json();
}

export async function listProviders(apiKey: string): Promise<Provider[]> {
  const r = await fetch(`${API_BASE}/ui/api/providers`, { headers: authHeaders(apiKey) });
  if (!r.ok) return apiError(r);
  const data = await r.json();
  return data.providers;
}

export async function listProviderModels(apiKey: string, providerId: string): Promise<string[]> {
  const r = await fetch(`${API_BASE}/ui/api/providers/${encodeURIComponent(providerId)}/models`, {
    headers: authHeaders(apiKey),
  });
  if (!r.ok) return apiError(r);
  const data = await r.json();
  return data.models ?? [];
}

export async function listWorkspaces(apiKey: string): Promise<Workspace[]> {
  const r = await fetch(`${API_BASE}/ui/api/workspaces`, { headers: authHeaders(apiKey) });
  if (!r.ok) return apiError(r);
  const data = await r.json();
  return data.workspaces;
}

export async function listFiles(apiKey: string, workspaceId: string, path: string, limit = 200): Promise<string[]> {
  const base = API_BASE || window.location.origin;
  const u = new URL(`${API_BASE}/ui/api/workspaces/${encodeURIComponent(workspaceId)}/files`, base);
  u.searchParams.set("path", path);
  u.searchParams.set("limit", String(limit));
  const r = await fetch(u.toString(), { headers: authHeaders(apiKey) });
  if (!r.ok) return apiError(r);
  const data = await r.json();
  return data.files ?? [];
}

export async function readFile(apiKey: string, workspaceId: string, path: string): Promise<string> {
  const base = API_BASE || window.location.origin;
  const u = new URL(`${API_BASE}/ui/api/workspaces/${encodeURIComponent(workspaceId)}/file`, base);
  u.searchParams.set("path", path);
  const r = await fetch(u.toString(), { headers: authHeaders(apiKey) });
  if (!r.ok) return apiError(r);
  const data = await r.json();
  return data.content ?? "";
}

export async function searchCode(apiKey: string, workspaceId: string, query: string): Promise<any[]> {
  const r = await fetch(`${API_BASE}/ui/api/workspaces/${encodeURIComponent(workspaceId)}/search`, {
    method: "POST",
    headers: { ...authHeaders(apiKey), "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit: 50 }),
  });
  if (!r.ok) return apiError(r);
  const data = await r.json();
  return data.matches ?? [];
}

export async function createAgentSession(apiKey: string, title: string, providerId: string, workspaceId: string) {
  const r = await fetch(`${API_BASE}/agent/sessions`, {
    method: "POST",
    headers: { ...authHeaders(apiKey), "Content-Type": "application/json" },
    body: JSON.stringify({ title, provider_id: providerId, workspace_id: workspaceId }),
  });
  if (!r.ok) return apiError(r);
  return (await r.json()) as AgentSession;
}

export async function getAgentSession(apiKey: string, sessionId: string) {
  const r = await fetch(`${API_BASE}/agent/sessions/${encodeURIComponent(sessionId)}`, { headers: authHeaders(apiKey) });
  if (!r.ok) return apiError(r);
  return (await r.json()) as AgentSession;
}

export async function runAgent(
  apiKey: string,
  sessionId: string,
  instruction: string,
  model: string | null,
  providerId?: string | null,
) {
  const body: Record<string, any> = { instruction, max_steps: 5 };
  if (model)      body.model       = model;
  if (providerId) body.provider_id = providerId;
  const r = await fetch(`${API_BASE}/agent/sessions/${encodeURIComponent(sessionId)}/run`, {
    method: "POST",
    headers: { ...authHeaders(apiKey), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) return apiError(r);
  return await r.json();
}

/**
 * Ask the proxy what model it would route a given message to in auto mode.
 * Returns { resolved_model, task_category, selection_source } — best-effort,
 * safe to ignore on error.
 */
export async function previewRoute(apiKey: string, text: string): Promise<{
  resolved_model: string;
  task_category: string;
  selection_source: string;
} | null> {
  try {
    const r = await fetch(`${API_BASE}/ui/api/route`, {
      method: "POST",
      headers: { ...authHeaders(apiKey), "Content-Type": "application/json" },
      body: JSON.stringify({ text }),
    });
    if (!r.ok) {
      if (r.status === 401 || r.status === 403) {
        throw new ApiError(r.status, `Route preview unauthorized (HTTP ${r.status})`);
      }
      return null;
    }
    return await r.json();
  } catch (err) {
    if (err instanceof ApiError) throw err;
    return null;
  }
}

// --- Admin API ---

export async function adminLogin(username: string, password: string) {
  const r = await fetch(`${API_BASE}/admin/api/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) return apiError(r);
  return r.json();
}

function adminHeaders(adminToken: string): Record<string, string> {
  return { Authorization: `Bearer ${adminToken}` };
}

export async function adminListProviders(adminToken: string) {
  const r = await fetch(`${API_BASE}/admin/api/providers`, { headers: adminHeaders(adminToken) });
  if (!r.ok) return apiError(r);
  return r.json();
}

export async function adminCreateProvider(adminToken: string, body: any) {
  const r = await fetch(`${API_BASE}/admin/api/providers`, {
    method: "POST",
    headers: { ...adminHeaders(adminToken), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) return apiError(r);
  return r.json();
}

export async function adminDeleteProvider(adminToken: string, providerId: string) {
  const r = await fetch(`${API_BASE}/admin/api/providers/${encodeURIComponent(providerId)}`, {
    method: "DELETE",
    headers: adminHeaders(adminToken),
  });
  if (!r.ok) return apiError(r);
  return r.json();
}

export async function adminListWorkspaces(adminToken: string) {
  const r = await fetch(`${API_BASE}/admin/api/workspaces`, { headers: adminHeaders(adminToken) });
  if (!r.ok) return apiError(r);
  return r.json();
}

export async function adminCreateWorkspace(adminToken: string, body: any) {
  const r = await fetch(`${API_BASE}/admin/api/workspaces`, {
    method: "POST",
    headers: { ...adminHeaders(adminToken), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) return apiError(r);
  return r.json();
}

export async function adminDeleteWorkspace(adminToken: string, workspaceId: string) {
  const r = await fetch(`${API_BASE}/admin/api/workspaces/${encodeURIComponent(workspaceId)}`, {
    method: "DELETE",
    headers: adminHeaders(adminToken),
  });
  if (!r.ok) return apiError(r);
  return r.json();
}

export async function adminSyncWorkspace(adminToken: string, workspaceId: string) {
  const r = await fetch(`${API_BASE}/admin/api/workspaces/${encodeURIComponent(workspaceId)}/sync`, {
    method: "POST",
    headers: adminHeaders(adminToken),
  });
  if (!r.ok) return apiError(r);
  return r.json();
}

export async function adminRunCommand(adminToken: string, workspaceId: string, command: string[]) {
  const r = await fetch(`${API_BASE}/admin/api/commands/run`, {
    method: "POST",
    headers: { ...adminHeaders(adminToken), "Content-Type": "application/json" },
    body: JSON.stringify({ workspace_id: workspaceId, command, timeout_sec: 120 }),
  });
  if (!r.ok) return apiError(r);
  return r.json();
}

