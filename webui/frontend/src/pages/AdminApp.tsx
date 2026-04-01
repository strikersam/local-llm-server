import { useEffect, useMemo, useState } from "react";
import {
  adminCreateProvider,
  adminCreateWorkspace,
  adminDeleteProvider,
  adminDeleteWorkspace,
  adminListProviders,
  adminListWorkspaces,
  adminLogin,
  adminRunCommand,
  adminSyncWorkspace,
} from "../api";
import { getLocal, removeLocal, setLocal } from "../storage";

const LS_ADMIN_TOKEN = "lls_admin_token";

function splitCmd(raw: string): string[] {
  return raw
    .trim()
    .split(/\s+/g)
    .filter(Boolean);
}

export default function AdminApp() {
  const [token, setToken] = useState(getLocal(LS_ADMIN_TOKEN) ?? "");
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [err, setErr] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const [providers, setProviders] = useState<any[]>([]);
  const [workspaces, setWorkspaces] = useState<any[]>([]);

  const [newProv, setNewProv] = useState({
    name: "",
    base_url: "",
    api_key: "",
    default_model: "",
    default_temperature: "0.2",
  });
  const [newWs, setNewWs] = useState({
    name: "",
    kind: "local",
    path: "",
    git_url: "",
    git_ref: "",
  });

  const [cmdWorkspace, setCmdWorkspace] = useState("ws_current");
  const [cmdRaw, setCmdRaw] = useState("git status");
  const [cmdOut, setCmdOut] = useState<any>(null);

  const authed = token.trim().length > 0;

  useEffect(() => {
    if (authed) setLocal(LS_ADMIN_TOKEN, token);
  }, [authed, token]);

  async function refresh() {
    if (!authed) return;
    setErr(null);
    try {
      const [p, w] = await Promise.all([adminListProviders(token), adminListWorkspaces(token)]);
      setProviders(p.providers ?? []);
      setWorkspaces(w.workspaces ?? []);
      if (w.workspaces?.[0]?.workspace_id) setCmdWorkspace(w.workspaces[0].workspace_id);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    }
  }

  useEffect(() => {
    refresh();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [authed]);

  async function doLogin() {
    setBusy(true);
    setErr(null);
    try {
      const out = await adminLogin(username, password);
      setToken(out.token);
      setLocal(LS_ADMIN_TOKEN, out.token);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    setToken("");
    removeLocal(LS_ADMIN_TOKEN);
  }

  async function createProvider() {
    setBusy(true);
    setErr(null);
    try {
      await adminCreateProvider(token, {
        name: newProv.name,
        base_url: newProv.base_url,
        api_key: newProv.api_key || null,
        default_model: newProv.default_model || null,
        default_temperature: Number(newProv.default_temperature || "0.2"),
        kind: "openai_compat",
      });
      setNewProv({ name: "", base_url: "", api_key: "", default_model: "", default_temperature: "0.2" });
      await refresh();
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  async function createWorkspace() {
    setBusy(true);
    setErr(null);
    try {
      const body: any = { name: newWs.name, kind: newWs.kind };
      if (newWs.kind === "local") body.path = newWs.path;
      if (newWs.kind === "git") {
        body.git_url = newWs.git_url;
        if (newWs.git_ref) body.git_ref = newWs.git_ref;
      }
      await adminCreateWorkspace(token, body);
      setNewWs({ name: "", kind: "local", path: "", git_url: "", git_ref: "" });
      await refresh();
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  async function runCmd() {
    setBusy(true);
    setErr(null);
    setCmdOut(null);
    try {
      const out = await adminRunCommand(token, cmdWorkspace, splitCmd(cmdRaw));
      setCmdOut(out.result);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  const workspaceOptions = useMemo(
    () =>
      workspaces.map((w: any) => (
        <option key={w.workspace_id} value={w.workspace_id}>
          {w.name}
        </option>
      )),
    [workspaces]
  );

  return (
    <div style={{ height: "100vh", display: "flex", flexDirection: "column" }}>
      <div className="topbar">
        <div className="brand">local-llm-server • Admin</div>
        <div className="muted">/admin/app</div>
        <a href="/app" className="pill">
          Back to app
        </a>
        <a href="/admin/ui/login" className="pill">
          Legacy admin UI
        </a>
        {authed ? (
          <button className="danger" onClick={logout}>
            Logout
          </button>
        ) : null}
        {busy ? <div className="pill">Working…</div> : null}
        {err ? <div className="pill" style={{ borderColor: "rgba(255,107,107,0.45)" }}>{err}</div> : null}
      </div>

      {!authed ? (
        <div className="stack" style={{ maxWidth: 720 }}>
          <div className="sectionTitle">Admin login</div>
          <div className="muted">
            Uses the server’s configured admin auth (`ADMIN_SECRET` or Windows auth when enabled).
          </div>
          <div className="row wrap">
            <input placeholder="Username (optional)" value={username} onChange={(e) => setUsername(e.target.value)} />
            <input
              placeholder="Password"
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
            <button className="primary" onClick={doLogin} disabled={busy || password.trim().length === 0}>
              Login
            </button>
          </div>
        </div>
      ) : (
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 14, padding: 14, overflow: "auto" }}>
          <div className="panel" style={{ borderRadius: 14, border: "1px solid var(--border)" }}>
            <div className="stack">
              <div className="sectionTitle">Providers</div>
              <div className="muted">OpenAI-compatible endpoints (secrets stay server-side).</div>
              <div className="list">
                {providers.map((p: any) => (
                  <div className="item" key={p.provider_id}>
                    <div className="row wrap">
                      <div className="grow">
                        <div style={{ fontWeight: 600 }}>{p.name}</div>
                        <div className="muted mono">{p.base_url}</div>
                        <div className="muted mono">id: {p.provider_id}</div>
                      </div>
                      <button
                        className="danger"
                        onClick={async () => {
                          await adminDeleteProvider(token, p.provider_id);
                          await refresh();
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="sectionTitle">Add provider</div>
              <div className="row wrap">
                <input
                  placeholder="Name"
                  value={newProv.name}
                  onChange={(e) => setNewProv({ ...newProv, name: e.target.value })}
                />
                <input
                  placeholder="Base URL (e.g. https://api.openai.com)"
                  value={newProv.base_url}
                  onChange={(e) => setNewProv({ ...newProv, base_url: e.target.value })}
                  style={{ width: 320 }}
                />
              </div>
              <div className="row wrap">
                <input
                  placeholder="API key (stored server-side)"
                  value={newProv.api_key}
                  onChange={(e) => setNewProv({ ...newProv, api_key: e.target.value })}
                  style={{ width: 320 }}
                />
                <input
                  placeholder="Default model (optional)"
                  value={newProv.default_model}
                  onChange={(e) => setNewProv({ ...newProv, default_model: e.target.value })}
                />
                <input
                  className="mono"
                  placeholder="Temp"
                  value={newProv.default_temperature}
                  onChange={(e) => setNewProv({ ...newProv, default_temperature: e.target.value })}
                  style={{ width: 90 }}
                />
                <button
                  className="primary"
                  onClick={createProvider}
                  disabled={busy || !newProv.name.trim() || !newProv.base_url.trim()}
                >
                  Create
                </button>
              </div>
            </div>
          </div>

          <div className="panel" style={{ borderRadius: 14, border: "1px solid var(--border)" }}>
            <div className="stack">
              <div className="sectionTitle">Workspaces</div>
              <div className="muted">
                The agent can read/search/apply diffs within the selected workspace root.
              </div>
              <div className="list">
                {workspaces.map((w: any) => (
                  <div className="item" key={w.workspace_id}>
                    <div className="row wrap">
                      <div className="grow">
                        <div style={{ fontWeight: 600 }}>
                          {w.name} <span className="muted">({w.kind})</span>
                        </div>
                        <div className="muted mono">{w.path}</div>
                        {w.git_url ? <div className="muted mono">{w.git_url}</div> : null}
                        <div className="muted mono">id: {w.workspace_id}</div>
                      </div>
                      {w.kind === "git" ? (
                        <button
                          onClick={async () => {
                            await adminSyncWorkspace(token, w.workspace_id);
                            await refresh();
                          }}
                        >
                          Sync
                        </button>
                      ) : null}
                      <button
                        className="danger"
                        onClick={async () => {
                          await adminDeleteWorkspace(token, w.workspace_id);
                          await refresh();
                        }}
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>

              <div className="sectionTitle">Add workspace</div>
              <div className="row wrap">
                <input
                  placeholder="Name"
                  value={newWs.name}
                  onChange={(e) => setNewWs({ ...newWs, name: e.target.value })}
                />
                <select value={newWs.kind} onChange={(e) => setNewWs({ ...newWs, kind: e.target.value })}>
                  <option value="local">local path</option>
                  <option value="git">git clone</option>
                </select>
              </div>
              {newWs.kind === "local" ? (
                <div className="row wrap">
                  <input
                    placeholder="Absolute path on server"
                    value={newWs.path}
                    onChange={(e) => setNewWs({ ...newWs, path: e.target.value })}
                    style={{ width: 420 }}
                  />
                </div>
              ) : (
                <div className="row wrap">
                  <input
                    placeholder="Git URL (https://...)"
                    value={newWs.git_url}
                    onChange={(e) => setNewWs({ ...newWs, git_url: e.target.value })}
                    style={{ width: 420 }}
                  />
                  <input
                    placeholder="Branch/ref (optional)"
                    value={newWs.git_ref}
                    onChange={(e) => setNewWs({ ...newWs, git_ref: e.target.value })}
                  />
                </div>
              )}
              <div className="row wrap">
                <button
                  className="primary"
                  onClick={createWorkspace}
                  disabled={
                    busy ||
                    !newWs.name.trim() ||
                    (newWs.kind === "local" ? !newWs.path.trim() : !newWs.git_url.trim())
                  }
                >
                  Create
                </button>
              </div>

              <div className="sectionTitle">Command runner</div>
              <div className="muted mono">Allowlist: `pytest`, `rg`, `git status|diff|log|show|rev-parse`, `ls`, `cat`.</div>
              <div className="row wrap">
                <select value={cmdWorkspace} onChange={(e) => setCmdWorkspace(e.target.value)}>
                  {workspaceOptions}
                </select>
                <input
                  className="mono grow"
                  placeholder="git status"
                  value={cmdRaw}
                  onChange={(e) => setCmdRaw(e.target.value)}
                />
                <button className="primary" onClick={runCmd} disabled={busy || splitCmd(cmdRaw).length === 0}>
                  Run
                </button>
              </div>
              {cmdOut ? (
                <div className="codebox mono">
                  exit={cmdOut.exit_code}
                  {"\n"}
                  {cmdOut.stdout}
                  {cmdOut.stderr ? `\n[stderr]\n${cmdOut.stderr}` : ""}
                </div>
              ) : null}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
