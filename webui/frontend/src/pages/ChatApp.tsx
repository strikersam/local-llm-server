import { useEffect, useMemo, useRef, useState } from "react";
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

// ── LocalStorage keys ──────────────────────────────────────────────────────────
const LS_API_KEY   = "lls_api_key";
const LS_PROVIDER  = "lls_provider";
const LS_WORKSPACE = "lls_workspace";
const LS_MODEL     = "lls_model";
const LS_SESSION   = "lls_session";
const LS_MODE      = "lls_mode";   // "auto" | "manual"

// ── Helpers ───────────────────────────────────────────────────────────────────
function short(s: string, max = 28) {
  return s.length <= max ? s : s.slice(0, max - 1) + "…";
}

/** Infer a human-readable model type from its name */
function modelType(name: string): string {
  if (/coder|code/i.test(name))                      return "coder";
  if (/r1|reasoner|thinking|deepseek/i.test(name))   return "reasoning";
  if (/gemma|llama|phi|mistral|qwen(?!.*coder)/i.test(name)) return "general";
  return "general";
}

function modelTypeBadge(name: string) {
  const t = modelType(name);
  const map: Record<string, string> = {
    coder:     "badge-coder",
    reasoning: "badge-reasoning",
    general:   "badge-general",
  };
  return map[t] ?? "badge-general";
}

// ── Component ─────────────────────────────────────────────────────────────────
export default function ChatApp() {
  // ── Core state ──────────────────────────────────────────────────────────────
  const [apiKey,      setApiKey]      = useState(getLocal(LS_API_KEY)   ?? "");
  const [providers,   setProviders]   = useState<any[]>([]);
  const [workspaces,  setWorkspaces]  = useState<any[]>([]);
  const [providerId,  setProviderId]  = useState(getLocal(LS_PROVIDER)  ?? "prov_local");
  const [workspaceId, setWorkspaceId] = useState(getLocal(LS_WORKSPACE) ?? "ws_current");
  const [models,      setModels]      = useState<string[]>([]);
  const [model,       setModel]       = useState(getLocal(LS_MODEL)     ?? "");

  // ── Selection mode ───────────────────────────────────────────────────────────
  const [mode, setMode] = useState<"auto" | "manual">(
    (getLocal(LS_MODE) as "auto" | "manual") ?? "auto"
  );

  // ── Model picker modal ───────────────────────────────────────────────────────
  const [showPicker,      setShowPicker]      = useState(false);
  const [pickerProvider,  setPickerProvider]  = useState("");
  const [pickerModels,    setPickerModels]    = useState<string[]>([]);
  const [pickerModel,     setPickerModel]     = useState("");
  const [pickerLoading,   setPickerLoading]   = useState(false);

  // ── Session / chat ───────────────────────────────────────────────────────────
  const [session,     setSession]     = useState<AgentSession | null>(null);
  const [busy,        setBusy]        = useState(false);
  const [err,         setErr]         = useState<string | null>(null);
  const [instruction, setInstruction] = useState("");
  const [lastRouting, setLastRouting] = useState<string | null>(null);

  // ── Files ────────────────────────────────────────────────────────────────────
  const [fileList,    setFileList]    = useState<string[]>([]);
  const [filePath,    setFilePath]    = useState("");
  const [fileContent, setFileContent] = useState("");
  const [fileQuery,   setFileQuery]   = useState("");

  // ── Mobile tab navigation ────────────────────────────────────────────────────
  const [mobileTab, setMobileTab] = useState<"settings" | "chat" | "files">("chat");

  const chatEndRef = useRef<HTMLDivElement>(null);
  const ready = apiKey.trim().length > 0;

  // ── Persist to localStorage ──────────────────────────────────────────────────
  useEffect(() => setLocal(LS_API_KEY,   apiKey),      [apiKey]);
  useEffect(() => setLocal(LS_PROVIDER,  providerId),  [providerId]);
  useEffect(() => setLocal(LS_WORKSPACE, workspaceId), [workspaceId]);
  useEffect(() => setLocal(LS_MODEL,     model),       [model]);
  useEffect(() => setLocal(LS_MODE,      mode),        [mode]);

  // ── Load providers + workspaces when key changes ─────────────────────────────
  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    setErr(null);
    Promise.all([listProviders(apiKey), listWorkspaces(apiKey)])
      .then(([prov, ws]) => {
        if (cancelled) return;
        setProviders(prov);
        setWorkspaces(ws);
      })
      .catch((e: any) => { if (!cancelled) setErr(e?.message ?? String(e)); });
    return () => { cancelled = true; };
  }, [ready, apiKey]);

  // ── Load models when provider changes ────────────────────────────────────────
  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    listProviderModels(apiKey, providerId)
      .then((ms) => {
        if (cancelled) return;
        setModels(ms);
        // If the saved model is not in this provider's list, reset to the
        // first available one — prevents sending a stale/invalid model name
        // after switching providers.
        setModel((current) => {
          if (current && ms.includes(current)) return current;
          return ms[0] ?? "";
        });
      })
      .catch((e: any) => {
        if (cancelled) return;
        setModels([]);
        // Don't clobber a valid session with a transient provider-listing
        // failure — surface it in the error chip but keep the UI usable.
        setErr(`Could not list models: ${e?.message ?? String(e)}`);
      });
    return () => { cancelled = true; };
  }, [ready, apiKey, providerId]);

  // ── Load file list when workspace changes ────────────────────────────────────
  useEffect(() => {
    if (!ready) return;
    let cancelled = false;
    listFiles(apiKey, workspaceId, ".", 400)
      .then((files) => { if (!cancelled) setFileList(files); })
      .catch((e: any) => { if (!cancelled) setErr(e?.message ?? String(e)); });
    return () => { cancelled = true; };
  }, [ready, apiKey, workspaceId]);

  // ── Auto-scroll chat to bottom ───────────────────────────────────────────────
  useEffect(() => {
    // Respect the user's reduced-motion preference — smooth scroll can trigger
    // vestibular symptoms for some users.
    const reduced = typeof window !== "undefined"
      && typeof window.matchMedia === "function"
      && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
    chatEndRef.current?.scrollIntoView({ behavior: reduced ? "auto" : "smooth" });
  }, [session?.history.length, busy]);

  // ── Picker: load models for selected provider ────────────────────────────────
  useEffect(() => {
    if (!showPicker || !pickerProvider || !ready) return;
    let cancelled = false;
    setPickerLoading(true);
    listProviderModels(apiKey, pickerProvider)
      .then((ms) => {
        if (cancelled) return;
        setPickerModels(ms);
        setPickerModel((current) => (current && ms.includes(current) ? current : (ms[0] ?? "")));
      })
      .catch(() => { if (!cancelled) setPickerModels([]); })
      .finally(() => { if (!cancelled) setPickerLoading(false); });
    return () => { cancelled = true; };
    // pickerModel is deliberately excluded — we only refresh the list when the
    // provider changes, not every time the user selects a different row.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [showPicker, pickerProvider, apiKey, ready]);

  // ── Filtered file list ───────────────────────────────────────────────────────
  const filteredFiles = useMemo(() => {
    if (!fileQuery.trim()) return fileList;
    const q = fileQuery.toLowerCase();
    return fileList.filter((p) => p.toLowerCase().includes(q)).slice(0, 400);
  }, [fileList, fileQuery]);

  // ── Actions ──────────────────────────────────────────────────────────────────
  async function openFile(path: string) {
    setFilePath(path);
    setMobileTab("files");
    try {
      const c = await readFile(apiKey, workspaceId, path);
      setFileContent(c);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    }
  }

  async function openPicker() {
    const firstProvider = providers[0]?.provider_id ?? "";
    setPickerProvider(providerId || firstProvider);
    setPickerModel(model);
    setPickerModels([]);
    setShowPicker(true);
  }

  function confirmPicker() {
    setProviderId(pickerProvider);
    setModel(pickerModel);
    setShowPicker(false);
  }

  async function createNewSession(): Promise<AgentSession | null> {
    setBusy(true);
    setErr(null);
    try {
      const s = await createAgentSession(
        apiKey,
        `Session (${new Date().toISOString().slice(0, 16).replace("T", " ")})`,
        providerId,
        workspaceId,
      );
      setSession(s);
      setLocal(LS_SESSION, s.session_id);
      return s;
    } catch (e: any) {
      setErr(e?.message ?? String(e));
      return null;
    } finally {
      setBusy(false);
    }
  }

  async function send() {
    if (!instruction.trim()) return;

    // In auto mode pass null → the proxy router classifies the task and picks the model.
    // In manual mode pass the user-selected model name.
    const modelToSend = mode === "auto" ? null : (model || null);

    let currentSession = session;
    if (!currentSession) {
      currentSession = await createNewSession();
      if (!currentSession) return;
    }

    setBusy(true);
    setErr(null);
    const text = instruction.trim();
    setInstruction("");
    try {
      const out = await runAgent(apiKey, currentSession.session_id, text, modelToSend);
      setSession(out.session);
      // Surface routing info when in auto mode (if the backend returns it).
      if (mode === "auto" && out.routing_model) {
        setLastRouting(out.routing_model);
      } else {
        setLastRouting(null);
      }
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    // Ctrl+Enter or Cmd+Enter sends the message
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      if (!busy && instruction.trim()) send();
    }
  }

  function logout() {
    setApiKey("");
    setProviders([]);
    setWorkspaces([]);
    setSession(null);
    setLastRouting(null);
    removeLocal(LS_SESSION);
    removeLocal(LS_API_KEY);
  }

  const lastPlan   = session?.last_plan;
  const lastResult = session?.last_result;

  // ── Provider name lookup ──────────────────────────────────────────────────────
  const providerName = providers.find((p) => p.provider_id === providerId)?.name ?? providerId;

  // ── Render ────────────────────────────────────────────────────────────────────
  return (
    <>
      {/* ── Model picker modal ───────────────────────────────────────────────── */}
      {showPicker && (
        <div
          className="modal-overlay"
          onClick={() => setShowPicker(false)}
          onKeyDown={(e) => { if (e.key === "Escape") setShowPicker(false); }}
          role="presentation"
        >
          <div
            className="modal"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-labelledby="model-picker-title"
          >
            <div className="modal-header">
              <span className="modal-title" id="model-picker-title">Select Provider &amp; Model</span>
              <button
                className="modal-close"
                onClick={() => setShowPicker(false)}
                aria-label="Close model picker"
              >✕</button>
            </div>

            {/* Provider tabs */}
            <div className="picker-providers">
              {providers.map((p) => (
                <button
                  key={p.provider_id}
                  className={`picker-provider-tab ${pickerProvider === p.provider_id ? "active" : ""}`}
                  onClick={() => setPickerProvider(p.provider_id)}
                >
                  {p.name}
                </button>
              ))}
            </div>

            {/* Model list */}
            <div className="modal-body">
              {pickerLoading ? (
                <div className="muted" style={{ padding: "24px", textAlign: "center" }}>
                  Loading models…
                </div>
              ) : pickerModels.length === 0 ? (
                <div className="muted" style={{ padding: "24px", textAlign: "center" }}>
                  No models found for this provider.
                </div>
              ) : (
                <div className="model-list">
                  {pickerModels.map((m) => (
                    <div
                      key={m}
                      className={`model-card ${pickerModel === m ? "selected" : ""}`}
                      onClick={() => setPickerModel(m)}
                      role="button"
                      tabIndex={0}
                      onKeyDown={(e) => e.key === "Enter" && setPickerModel(m)}
                    >
                      <div className="model-card-name mono">{m}</div>
                      <span className={`model-badge ${modelTypeBadge(m)}`}>
                        {modelType(m)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <div className="modal-footer">
              <button onClick={() => setShowPicker(false)}>Cancel</button>
              <button
                className="primary"
                disabled={!pickerModel}
                onClick={confirmPicker}
              >
                Use {pickerModel ? short(pickerModel, 22) : "model"}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* ── Main layout ──────────────────────────────────────────────────────── */}
      <div className="layout">

        {/* ── LEFT: Settings panel ──────────────────────────────────────────── */}
        <div className={`panel ${mobileTab === "settings" ? "mobile-active" : ""}`}>
          <div className="stack">
            <div className="sectionTitle">Connection</div>

            {/* API key row */}
            <div className="field-row">
              <label className="muted field-label" htmlFor="lls-api-key">API key</label>
              <div className="field-row-inner">
                <input
                  id="lls-api-key"
                  className="mono field-input"
                  type="password"
                  placeholder="sk-qwen-…"
                  value={apiKey}
                  onChange={(e) => setApiKey(e.target.value)}
                  autoComplete="off"
                />
                <button onClick={logout} className="danger btn-sm">Clear</button>
                <a href="/admin/app" className="pill btn-sm">Admin</a>
              </div>
            </div>

            {/* Workspace */}
            <div className="field-row">
              <label className="muted field-label" htmlFor="lls-workspace">Workspace</label>
              <select
                id="lls-workspace"
                className="field-select"
                value={workspaceId}
                onChange={(e) => setWorkspaceId(e.target.value)}
              >
                {workspaces.map((w) => (
                  <option key={w.workspace_id} value={w.workspace_id}>{w.name}</option>
                ))}
              </select>
            </div>

            {/* ── Model selection mode ─────────────────────────────────────── */}
            <div className="sectionTitle" style={{ marginTop: 4 }}>Model Selection</div>
            <div className="mode-toggle">
              <button
                className={`mode-btn ${mode === "auto" ? "active" : ""}`}
                onClick={() => setMode("auto")}
              >
                ⚡ Auto
              </button>
              <button
                className={`mode-btn ${mode === "manual" ? "active" : ""}`}
                onClick={() => setMode("manual")}
              >
                ⚙ Manual
              </button>
            </div>

            {mode === "auto" ? (
              <div className="mode-description">
                <div className="mode-desc-title">Smart routing enabled</div>
                <div className="muted mode-desc-text">
                  Each message is classified (code, reasoning, chat…) and routed
                  to the best available local model automatically. Your API key
                  works with all models — just send a message.
                </div>
                {lastRouting && (
                  <div className="routing-chip">
                    Last routed to: <span className="mono">{lastRouting}</span>
                  </div>
                )}
              </div>
            ) : (
              <div className="mode-description">
                <div className="mode-desc-title">Manual selection</div>
                <div className="manual-selection-row">
                  <div className="selected-model-display">
                    <span className="muted">Provider:</span>
                    <span className="mono">{short(providerName, 16)}</span>
                    <span className="muted" style={{ marginLeft: 6 }}>Model:</span>
                    <span className="mono">{model ? short(model, 18) : "(none)"}</span>
                  </div>
                  <button className="primary btn-sm" onClick={openPicker} disabled={!ready}>
                    Change
                  </button>
                </div>
              </div>
            )}

            {/* New session button */}
            <button
              className="primary"
              onClick={createNewSession}
              disabled={!ready || busy}
              style={{ width: "100%" }}
            >
              New session
            </button>

            {/* ── Files ────────────────────────────────────────────────────── */}
            <div className="sectionTitle" style={{ marginTop: 4 }}>Files</div>
            <input
              placeholder="Filter paths…"
              value={fileQuery}
              onChange={(e) => setFileQuery(e.target.value)}
              style={{ width: "100%", boxSizing: "border-box" }}
            />
            <div className="list">
              {filteredFiles.slice(0, 120).map((p) => (
                <div
                  key={p}
                  className={`item ${p === filePath ? "active" : ""}`}
                  onClick={() => openFile(p)}
                  role="button"
                  tabIndex={0}
                  onKeyDown={(e) => e.key === "Enter" && openFile(p)}
                >
                  <div className="mono">{short(p, 40)}</div>
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* ── CENTRE: Chat ──────────────────────────────────────────────────── */}
        <div className={`main ${mobileTab === "chat" ? "mobile-active" : ""}`}>
          <div className="topbar">
            <div className="brand">local-llm-server</div>
            <div className="topbar-badges">
              {mode === "auto" ? (
                <span className="badge-auto pill">⚡ Auto</span>
              ) : (
                <span className="pill mono" style={{ fontSize: 11 }}>
                  {short(model || "(no model)", 20)}
                </span>
              )}
              {session ? (
                <span className="pill mono" style={{ fontSize: 11 }}>
                  {short(session.session_id, 20)}
                </span>
              ) : null}
              {busy ? (
                <span className="pill busy-pill" role="status" aria-live="polite">
                  ● Running…
                </span>
              ) : null}
              {err ? (
                <span
                  className="pill err-pill"
                  title={err}
                  role="alert"
                  aria-live="assertive"
                >{short(err, 60)}</span>
              ) : null}
            </div>
          </div>

          <div className="chat">
            {!ready && (
              <div className="msg system">
                Paste your API key in the <strong>Config</strong> panel to start.
                <br />
                The same token works for all models — Claude Code, Cursor, Aider,
                or this UI.
              </div>
            )}

            {ready && !session && (
              <div className="msg system">
                Choose <strong>Auto</strong> (smart routing) or{" "}
                <strong>Manual</strong> (pick provider + model), then send a
                message. A session is created automatically on first send.
              </div>
            )}

            {session &&
              session.history.map((m, idx) => (
                <div key={idx} className={`msg ${m.role}`}>
                  <div className="msg-role muted">{m.role.toUpperCase()}</div>
                  <div className="msg-content">{m.content}</div>
                </div>
              ))}

            {lastResult?.summary && (
              <div className="msg system">
                <div className="msg-role muted">RESULT</div>
                <div className="msg-content">{lastResult.summary}</div>
              </div>
            )}

            {busy && (
              <div className="msg system thinking">
                <div className="thinking-dots">
                  <span /><span /><span />
                </div>
                {mode === "auto"
                  ? "Router classifying task and running agent…"
                  : `Running agent with ${model || "selected model"}…`}
              </div>
            )}

            <div ref={chatEndRef} />
          </div>

          <div className="composer">
            <label htmlFor="lls-composer" className="sr-only">Message</label>
            <textarea
              id="lls-composer"
              className="composer-input"
              placeholder={
                mode === "auto"
                  ? "Describe what you need… the router picks the best model. (Ctrl+Enter to send)"
                  : `Sending to ${short(model || "selected model", 22)}… (Ctrl+Enter to send)`
              }
              value={instruction}
              onChange={(e) => setInstruction(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={!ready || busy}
              rows={3}
              aria-label="Message to agent"
            />
            <div className="composer-actions">
              {mode === "manual" && !model && (
                <button className="primary btn-sm" onClick={openPicker} disabled={!ready}>
                  Select model
                </button>
              )}
              <button
                className="primary send-btn"
                onClick={send}
                disabled={!ready || busy || !instruction.trim() || (mode === "manual" && !model)}
              >
                Send
              </button>
            </div>
          </div>
        </div>

        {/* ── RIGHT: Workspace / Plan / Steps ───────────────────────────────── */}
        <div className={`panel right ${mobileTab === "files" ? "mobile-active" : ""}`}>
          <div className="stack">
            <div className="sectionTitle">Workspace</div>
            <div className="muted mono" style={{ fontSize: 11 }}>
              {filePath || "Select a file to view"}
            </div>
            {filePath ? (
              <div className="codebox mono">{fileContent || "(empty)"}</div>
            ) : null}

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
              <div className="muted">No steps yet.</div>
            )}
          </div>
        </div>
      </div>

      {/* ── Mobile bottom navigation ─────────────────────────────────────────── */}
      <nav className="bottom-nav" aria-label="Mobile sections">
        <button
          className={`bottom-nav-btn ${mobileTab === "settings" ? "active" : ""}`}
          onClick={() => setMobileTab("settings")}
          aria-pressed={mobileTab === "settings"}
          aria-label="Configuration"
        >
          <span className="bottom-nav-icon" aria-hidden="true">⚙</span>
          <span className="bottom-nav-label">Config</span>
        </button>
        <button
          className={`bottom-nav-btn ${mobileTab === "chat" ? "active" : ""}`}
          onClick={() => setMobileTab("chat")}
          aria-pressed={mobileTab === "chat"}
          aria-label="Chat"
        >
          <span className="bottom-nav-icon" aria-hidden="true">💬</span>
          <span className="bottom-nav-label">Chat</span>
        </button>
        <button
          className={`bottom-nav-btn ${mobileTab === "files" ? "active" : ""}`}
          onClick={() => setMobileTab("files")}
          aria-pressed={mobileTab === "files"}
          aria-label="Files"
        >
          <span className="bottom-nav-icon" aria-hidden="true">📁</span>
          <span className="bottom-nav-label">Files</span>
        </button>
      </nav>
    </>
  );
}
