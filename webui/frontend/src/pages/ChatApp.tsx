import { useEffect, useMemo, useState } from "react";
import {
  AgentSession,
  listFiles,
  listProviderModels,
  listProviders,
  listWorkspaces,
  readFile,
  runAgent,
  createAgentSession,
} from "../api";
import { getLocal, removeLocal, setLocal } from "../storage";

const LS_API_KEY = "lls_api_key";
const LS_PROVIDER = "lls_provider";
const LS_WORKSPACE = "lls_workspace";
const LS_MODEL = "lls_model";
const LS_SESSION = "lls_session";

function short(s: string, max = 28) {
  if (s.length <= max) return s;
  return s.slice(0, max - 1) + "…";
}

export default function ChatApp() {
  const [apiKey, setApiKey] = useState(getLocal(LS_API_KEY) ?? "");
  const [providers, setProviders] = useState<any[]>([]);
  const [workspaces, setWorkspaces] = useState<any[]>([]);
  const [providerId, setProviderId] = useState(getLocal(LS_PROVIDER) ?? "prov_local");
  const [workspaceId, setWorkspaceId] = useState(getLocal(LS_WORKSPACE) ?? "ws_current");
  const [models, setModels] = useState<string[]>([]);
  const [model, setModel] = useState(getLocal(LS_MODEL) ?? "");

  const [session, setSession] = useState<AgentSession | null>(null);
  const [busy, setBusy] = useState(false);
  const [err, setErr] = useState<string | null>(null);

  const [instruction, setInstruction] = useState("");

  const [fileList, setFileList] = useState<string[]>([]);
  const [filePath, setFilePath] = useState("");
  const [fileContent, setFileContent] = useState("");
  const [fileQuery, setFileQuery] = useState("");

  const ready = apiKey.trim().length > 0;

  useEffect(() => {
    setLocal(LS_API_KEY, apiKey);
  }, [apiKey]);
  useEffect(() => {
    setLocal(LS_PROVIDER, providerId);
  }, [providerId]);
  useEffect(() => {
    setLocal(LS_WORKSPACE, workspaceId);
  }, [workspaceId]);
  useEffect(() => {
    setLocal(LS_MODEL, model);
  }, [model]);

  useEffect(() => {
    if (!ready) return;
    (async () => {
      setErr(null);
      try {
        const [prov, ws] = await Promise.all([listProviders(apiKey), listWorkspaces(apiKey)]);
        setProviders(prov);
        setWorkspaces(ws);
      } catch (e: any) {
        setErr(e?.message ?? String(e));
      }
    })();
  }, [ready, apiKey]);

  useEffect(() => {
    if (!ready) return;
    (async () => {
      setErr(null);
      try {
        const ms = await listProviderModels(apiKey, providerId);
        setModels(ms);
        if (!model && ms.length) setModel(ms[0]);
      } catch (e: any) {
        setModels([]);
        // model listing is best-effort; don't block the whole app
        setErr(e?.message ?? String(e));
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [ready, apiKey, providerId]);

  useEffect(() => {
    if (!ready) return;
    (async () => {
      try {
        const files = await listFiles(apiKey, workspaceId, ".", 400);
        setFileList(files);
      } catch (e: any) {
        setErr(e?.message ?? String(e));
      }
    })();
  }, [ready, apiKey, workspaceId]);

  useEffect(() => {
    const sid = getLocal(LS_SESSION);
    if (!sid || !ready) return;
    // Sessions are in-memory server-side by default; ignore if gone.
    // Users can click "New session" to start over.
    // eslint-disable-next-line @typescript-eslint/no-unused-vars
  }, [ready]);

  const filteredFiles = useMemo(() => {
    if (!fileQuery.trim()) return fileList;
    const q = fileQuery.toLowerCase();
    return fileList.filter((p) => p.toLowerCase().includes(q)).slice(0, 400);
  }, [fileList, fileQuery]);

  async function openFile(path: string) {
    setFilePath(path);
    try {
      const c = await readFile(apiKey, workspaceId, path);
      setFileContent(c);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    }
  }

  async function newSession() {
    setBusy(true);
    setErr(null);
    try {
      const s = await createAgentSession(
        apiKey,
        `Session (${new Date().toISOString().slice(0, 16).replace("T", " ")})`,
        providerId,
        workspaceId
      );
      setSession(s);
      setLocal(LS_SESSION, s.session_id);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  async function send() {
    if (!session) {
      await newSession();
      // session state updates async; caller can hit send again
      return;
    }
    if (!instruction.trim()) return;
    setBusy(true);
    setErr(null);
    try {
      const out = await runAgent(apiKey, session.session_id, instruction.trim(), model || null);
      setSession(out.session);
      setInstruction("");
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  function logout() {
    setApiKey("");
    setProviders([]);
    setWorkspaces([]);
    setSession(null);
    removeLocal(LS_SESSION);
    removeLocal(LS_API_KEY);
  }

  const lastPlan = session?.last_plan;
  const lastResult = session?.last_result;

  return (
    <div className="layout">
      <div className="panel">
        <div className="stack">
          <div className="sectionTitle">Connection</div>
          <div className="row wrap">
            <span className="pill">
              <span className="muted">API key</span>
              <input
                className="mono"
                style={{ width: 170 }}
                placeholder="sk-qwen-..."
                value={apiKey}
                onChange={(e) => setApiKey(e.target.value)}
              />
            </span>
            <button onClick={logout} className="danger">
              Clear
            </button>
            <a href="/admin/app" className="pill">
              Admin
            </a>
          </div>
          <div className="row wrap">
            <span className="pill">
              <span className="muted">Provider</span>
              <select value={providerId} onChange={(e) => setProviderId(e.target.value)}>
                {providers.map((p) => (
                  <option key={p.provider_id} value={p.provider_id}>
                    {p.name}
                  </option>
                ))}
              </select>
            </span>
            <span className="pill">
              <span className="muted">Workspace</span>
              <select value={workspaceId} onChange={(e) => setWorkspaceId(e.target.value)}>
                {workspaces.map((w) => (
                  <option key={w.workspace_id} value={w.workspace_id}>
                    {w.name}
                  </option>
                ))}
              </select>
            </span>
          </div>
          <div className="row wrap">
            <span className="pill">
              <span className="muted">Model</span>
              <select value={model} onChange={(e) => setModel(e.target.value)}>
                {models.length === 0 ? <option value="">(unknown)</option> : null}
                {models.map((m) => (
                  <option key={m} value={m}>
                    {m}
                  </option>
                ))}
              </select>
            </span>
            <button className="primary" onClick={newSession} disabled={!ready || busy}>
              New session
            </button>
          </div>

          <div className="sectionTitle">Files</div>
          <input
            placeholder="Filter paths (e.g. proxy.py)"
            value={fileQuery}
            onChange={(e) => setFileQuery(e.target.value)}
          />
          <div className="list">
            {filteredFiles.slice(0, 120).map((p) => (
              <div
                key={p}
                className={`item ${p === filePath ? "active" : ""}`}
                onClick={() => openFile(p)}
                role="button"
                tabIndex={0}
              >
                <div className="mono">{short(p, 42)}</div>
              </div>
            ))}
          </div>
        </div>
      </div>

      <div className="main">
        <div className="topbar">
          <div className="brand">local-llm-server • Agent UI</div>
          <div className="muted">/app</div>
          {session ? <div className="pill mono">session: {session.session_id}</div> : null}
          {busy ? <div className="pill">Running…</div> : null}
          {err ? <div className="pill" style={{ borderColor: "rgba(255,107,107,0.45)" }}>{short(err, 80)}</div> : null}
        </div>

        <div className="chat">
          {!ready ? (
            <div className="msg system">
              Paste an API key (from `/admin/ui/login` → “Create user key”) to start.
            </div>
          ) : null}

          {!session ? (
            <div className="msg system">Click “New session”, then send an instruction.</div>
          ) : (
            session.history.map((m, idx) => (
              <div key={idx} className={`msg ${m.role}`}>
                <div className="muted" style={{ marginBottom: 6 }}>
                  {m.role.toUpperCase()}
                </div>
                {m.content}
              </div>
            ))
          )}

          {lastResult?.summary ? (
            <div className="msg system">
              <div className="muted" style={{ marginBottom: 6 }}>
                RESULT
              </div>
              {lastResult.summary}
            </div>
          ) : null}
        </div>

        <div className="composer">
          <div className="row">
            <textarea
              className="grow"
              rows={3}
              placeholder="Tell the agent what to do… (e.g. “Add a new endpoint and tests…”)"
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              disabled={!ready || busy}
            />
            <button className="primary" onClick={send} disabled={!ready || busy || instruction.trim().length === 0}>
              Send
            </button>
          </div>
        </div>
      </div>

      <div className="panel right">
        <div className="stack">
          <div className="sectionTitle">Workspace</div>
          <div className="muted mono">{filePath ? filePath : "Select a file to view"}</div>
          {filePath ? <div className="codebox mono">{fileContent || "(empty)"}</div> : null}

          <div className="sectionTitle">Plan</div>
          {lastPlan ? (
            <div className="codebox mono">{JSON.stringify(lastPlan, null, 2)}</div>
          ) : (
            <div className="muted">No plan yet.</div>
          )}

          <div className="sectionTitle">Steps</div>
          {lastResult?.steps ? (
            <div className="codebox mono">{JSON.stringify(lastResult.steps, null, 2)}</div>
          ) : (
            <div className="muted">No step results yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}

