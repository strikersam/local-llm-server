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

export async function getBootstrap(): Promise<any> {
  const r = await fetch("/ui/api/bootstrap");
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function listProviders(apiKey: string): Promise<Provider[]> {
  const r = await fetch("/ui/api/providers", { headers: authHeaders(apiKey) });
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  return data.providers;
}

export async function listProviderModels(apiKey: string, providerId: string): Promise<string[]> {
  const r = await fetch(`/ui/api/providers/${encodeURIComponent(providerId)}/models`, {
    headers: authHeaders(apiKey),
  });
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  return data.models ?? [];
}

export async function listWorkspaces(apiKey: string): Promise<Workspace[]> {
  const r = await fetch("/ui/api/workspaces", { headers: authHeaders(apiKey) });
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  return data.workspaces;
}

export async function listFiles(apiKey: string, workspaceId: string, path: string, limit = 200): Promise<string[]> {
  const u = new URL(`/ui/api/workspaces/${encodeURIComponent(workspaceId)}/files`, window.location.origin);
  u.searchParams.set("path", path);
  u.searchParams.set("limit", String(limit));
  const r = await fetch(u.toString(), { headers: authHeaders(apiKey) });
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  return data.files ?? [];
}

export async function readFile(apiKey: string, workspaceId: string, path: string): Promise<string> {
  const u = new URL(`/ui/api/workspaces/${encodeURIComponent(workspaceId)}/file`, window.location.origin);
  u.searchParams.set("path", path);
  const r = await fetch(u.toString(), { headers: authHeaders(apiKey) });
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  return data.content ?? "";
}

export async function searchCode(apiKey: string, workspaceId: string, query: string): Promise<any[]> {
  const r = await fetch(`/ui/api/workspaces/${encodeURIComponent(workspaceId)}/search`, {
    method: "POST",
    headers: { ...authHeaders(apiKey), "Content-Type": "application/json" },
    body: JSON.stringify({ query, limit: 50 }),
  });
  if (!r.ok) throw new Error(await r.text());
  const data = await r.json();
  return data.matches ?? [];
}

export async function createAgentSession(apiKey: string, title: string, providerId: string, workspaceId: string) {
  const r = await fetch("/agent/sessions", {
    method: "POST",
    headers: { ...authHeaders(apiKey), "Content-Type": "application/json" },
    body: JSON.stringify({ title, provider_id: providerId, workspace_id: workspaceId }),
  });
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as AgentSession;
}

export async function getAgentSession(apiKey: string, sessionId: string) {
  const r = await fetch(`/agent/sessions/${encodeURIComponent(sessionId)}`, { headers: authHeaders(apiKey) });
  if (!r.ok) throw new Error(await r.text());
  return (await r.json()) as AgentSession;
}

export async function runAgent(apiKey: string, sessionId: string, instruction: string, model: string | null) {
  const r = await fetch(`/agent/sessions/${encodeURIComponent(sessionId)}/run`, {
    method: "POST",
    headers: { ...authHeaders(apiKey), "Content-Type": "application/json" },
    body: JSON.stringify({ instruction, model: model ?? undefined, max_steps: 5 }),
  });
  if (!r.ok) throw new Error(await r.text());
  return await r.json();
}

// --- Admin API ---

export async function adminLogin(username: string, password: string) {
  const r = await fetch("/admin/api/login", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

function adminHeaders(adminToken: string): Record<string, string> {
  return { Authorization: `Bearer ${adminToken}` };
}

export async function adminListProviders(adminToken: string) {
  const r = await fetch("/admin/api/providers", { headers: adminHeaders(adminToken) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function adminCreateProvider(adminToken: string, body: any) {
  const r = await fetch("/admin/api/providers", {
    method: "POST",
    headers: { ...adminHeaders(adminToken), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function adminDeleteProvider(adminToken: string, providerId: string) {
  const r = await fetch(`/admin/api/providers/${encodeURIComponent(providerId)}`, {
    method: "DELETE",
    headers: adminHeaders(adminToken),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function adminListWorkspaces(adminToken: string) {
  const r = await fetch("/admin/api/workspaces", { headers: adminHeaders(adminToken) });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function adminCreateWorkspace(adminToken: string, body: any) {
  const r = await fetch("/admin/api/workspaces", {
    method: "POST",
    headers: { ...adminHeaders(adminToken), "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function adminDeleteWorkspace(adminToken: string, workspaceId: string) {
  const r = await fetch(`/admin/api/workspaces/${encodeURIComponent(workspaceId)}`, {
    method: "DELETE",
    headers: adminHeaders(adminToken),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function adminSyncWorkspace(adminToken: string, workspaceId: string) {
  const r = await fetch(`/admin/api/workspaces/${encodeURIComponent(workspaceId)}/sync`, {
    method: "POST",
    headers: adminHeaders(adminToken),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

export async function adminRunCommand(adminToken: string, workspaceId: string, command: string[]) {
  const r = await fetch("/admin/api/commands/run", {
    method: "POST",
    headers: { ...adminHeaders(adminToken), "Content-Type": "application/json" },
    body: JSON.stringify({ workspace_id: workspaceId, command, timeout_sec: 120 }),
  });
  if (!r.ok) throw new Error(await r.text());
  return r.json();
}

