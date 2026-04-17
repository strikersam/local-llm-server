/**
 * AdminPortalPage — native React admin UI.
 *
 * Calls /admin/api/* JSON endpoints directly via fetch(), so it works
 * from GitHub Pages (HTTPS) to any backend URL including ngrok tunnels.
 * No server-side session required — uses the Bearer token returned by
 * POST /admin/api/login.
 */
import React, { useCallback, useEffect, useRef, useState } from 'react';
import {
  Shield, LogIn, LogOut, RefreshCw, Settings2,
  Play, Square, RotateCcw, Key, Plus, Trash2, Copy,
  ChevronDown, ChevronUp, X, Loader2, Check, AlertTriangle,
} from 'lucide-react';

// ── localStorage keys ─────────────────────────────────────────────────────────
const LS_BACKEND  = 'agv_backend_url';       // shared with AgentViewPage
const LS_ADMIN_TK = 'adm_token';
const LS_ADMIN_UN = 'adm_username';

const DEFAULT_BACKEND = 'http://localhost:8000';

// ── API helpers ───────────────────────────────────────────────────────────────
function hdrs(token, backendUrl = '') {
  return {
    'Content-Type': 'application/json',
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...(backendUrl.includes('ngrok') ? { 'ngrok-skip-browser-warning': 'true' } : {}),
  };
}

async function apiFetch(backendUrl, path, token, opts = {}) {
  const base = backendUrl.replace(/\/+$/, '');
  const res = await fetch(`${base}${path}`, { headers: hdrs(token, backendUrl), ...opts });
  if (!res.ok) {
    let detail = `HTTP ${res.status}`;
    try {
      const d = await res.json();
      if (d.detail) {
        detail = typeof d.detail === 'string'
          ? d.detail
          : Array.isArray(d.detail)
            ? d.detail.map(e => e.msg || JSON.stringify(e)).join('; ')
            : JSON.stringify(d.detail);
      }
    } catch {}
    throw new Error(detail);
  }
  return res.json();
}

// ── Tiny helpers ──────────────────────────────────────────────────────────────
function Badge({ ok, label }) {
  return (
    <span className={`inline-flex items-center gap-1 px-2 py-0.5 text-[9px] font-mono uppercase tracking-wider border
      ${ok ? 'border-green-500/30 bg-green-500/10 text-green-400' : 'border-red-500/30 bg-red-500/10 text-red-400'}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${ok ? 'bg-green-500' : 'bg-red-500'}`} />
      {label}
    </span>
  );
}

function CopyButton({ text }) {
  const [copied, setCopied] = useState(false);
  function copy() {
    navigator.clipboard.writeText(text).then(() => { setCopied(true); setTimeout(() => setCopied(false), 1800); });
  }
  return (
    <button onClick={copy} title="Copy"
      className="p-1 text-[#555] hover:text-[#A0A0A0] transition-colors">
      {copied ? <Check size={12} className="text-green-400" /> : <Copy size={12} />}
    </button>
  );
}

// ── Service status card ───────────────────────────────────────────────────────
function ServiceCard({ name, running, onControl, loading }) {
  return (
    <div className="flex items-center justify-between px-4 py-3 bg-[#111] border border-white/8">
      <div className="flex items-center gap-3">
        <div className={`w-2 h-2 rounded-full shrink-0 ${running ? 'bg-green-500' : 'bg-red-500'}`} />
        <span className="text-[12px] font-mono text-[#C0C0C0] capitalize">{name}</span>
        <Badge ok={running} label={running ? 'Running' : 'Stopped'} />
      </div>
      <div className="flex gap-1.5">
        {!running ? (
          <button onClick={() => onControl('start', name)} disabled={loading}
            className="flex items-center gap-1 px-2.5 py-1.5 bg-green-500/15 border border-green-500/25 text-green-400 hover:bg-green-500/25 text-[10px] font-mono uppercase tracking-wider transition-colors disabled:opacity-40">
            <Play size={9} /> Start
          </button>
        ) : (
          <>
            <button onClick={() => onControl('restart', name)} disabled={loading}
              className="flex items-center gap-1 px-2.5 py-1.5 border border-white/10 hover:border-white/20 text-[#737373] hover:text-white text-[10px] font-mono uppercase tracking-wider transition-colors disabled:opacity-40">
              <RotateCcw size={9} /> Restart
            </button>
            <button onClick={() => onControl('stop', name)} disabled={loading}
              className="flex items-center gap-1 px-2.5 py-1.5 bg-red-500/10 border border-red-500/20 text-red-400 hover:bg-red-500/20 text-[10px] font-mono uppercase tracking-wider transition-colors disabled:opacity-40">
              <Square size={9} /> Stop
            </button>
          </>
        )}
      </div>
    </div>
  );
}

// ── Main component ────────────────────────────────────────────────────────────
export default function AdminPortalPage() {
  const [backendUrl, setBackendUrl] = useState(
    () => localStorage.getItem(LS_BACKEND) || DEFAULT_BACKEND,
  );
  const [token,    setToken]    = useState(() => localStorage.getItem(LS_ADMIN_TK) || '');
  const [username, setUsername] = useState(() => localStorage.getItem(LS_ADMIN_UN) || '');

  // Login form
  const [loginUser, setLoginUser] = useState('');
  const [loginPass, setLoginPass] = useState('');
  const [loginErr,  setLoginErr]  = useState('');
  const [loginBusy, setLoginBusy] = useState(false);

  // Connection config panel
  const [cfgOpen,      setCfgOpen]      = useState(false);
  const [editBackend,  setEditBackend]  = useState(backendUrl);

  // Status
  const [status,       setStatus]       = useState(null);
  const [statusErr,    setStatusErr]    = useState('');
  const [statusBusy,   setStatusBusy]   = useState(false);
  const [controlBusy,  setControlBusy]  = useState(false);
  const [controlMsg,   setControlMsg]   = useState('');

  // Users / keys
  const [keys,        setKeys]        = useState([]);
  const [keysErr,     setKeysErr]     = useState('');
  const [keysBusy,    setKeysBusy]    = useState(false);
  const [newEmail,    setNewEmail]    = useState('');
  const [newDept,     setNewDept]     = useState('');
  const [createBusy,  setCreateBusy]  = useState(false);
  const [newKeyResult, setNewKeyResult] = useState(null);   // {api_key, record}
  const [showCreate,  setShowCreate]  = useState(false);

  // Persist
  useEffect(() => { localStorage.setItem(LS_BACKEND,  backendUrl); }, [backendUrl]);
  useEffect(() => { if (token)    localStorage.setItem(LS_ADMIN_TK, token); else localStorage.removeItem(LS_ADMIN_TK); }, [token]);
  useEffect(() => { if (username) localStorage.setItem(LS_ADMIN_UN, username); else localStorage.removeItem(LS_ADMIN_UN); }, [username]);

  const authenticated = Boolean(token);

  // ── Load status + keys after login ──────────────────────────────────────────
  const loadStatus = useCallback(async (tk = token, url = backendUrl) => {
    if (!tk) return;
    setStatusBusy(true); setStatusErr('');
    try { setStatus(await apiFetch(url, '/admin/api/status', tk)); }
    catch (e) {
      setStatusErr(e.message);
      if (e.message.includes('401') || e.message.includes('403')) { setToken(''); setUsername(''); }
    }
    finally { setStatusBusy(false); }
  }, [token, backendUrl]);

  const loadKeys = useCallback(async (tk = token, url = backendUrl) => {
    if (!tk) return;
    setKeysBusy(true); setKeysErr('');
    try { const d = await apiFetch(url, '/admin/api/users', tk); setKeys(d.records || []); }
    catch (e) { setKeysErr(e.message); }
    finally { setKeysBusy(false); }
  }, [token, backendUrl]);

  useEffect(() => {
    if (authenticated) { loadStatus(); loadKeys(); }
  }, [authenticated]); // eslint-disable-line

  // ── Login ────────────────────────────────────────────────────────────────────
  async function doLogin(e) {
    e.preventDefault();
    setLoginBusy(true); setLoginErr('');
    try {
      const d = await apiFetch(backendUrl, '/admin/api/login', null, {
        method: 'POST',
        body: JSON.stringify({ username: loginUser, password: loginPass }),
      });
      setToken(d.token);
      setUsername(d.username || loginUser);
      setLoginPass('');
      await Promise.all([loadStatus(d.token, backendUrl), loadKeys(d.token, backendUrl)]);
    } catch (e) {
      setLoginErr(e.message || 'Login failed');
    } finally {
      setLoginBusy(false);
    }
  }

  async function doLogout() {
    try { await apiFetch(backendUrl, '/admin/api/logout', token, { method: 'POST' }); } catch {}
    setToken(''); setUsername(''); setStatus(null); setKeys([]);
  }

  // ── Service control ──────────────────────────────────────────────────────────
  async function doControl(action, target) {
    setControlBusy(true); setControlMsg('');
    try {
      const d = await apiFetch(backendUrl, '/admin/api/control', token, {
        method: 'POST',
        body: JSON.stringify({ action, target }),
      });
      setControlMsg(d.message || `${action} sent to ${target}`);
      setTimeout(() => setControlMsg(''), 3000);
      await loadStatus();
    } catch (e) {
      setControlMsg(`Error: ${e.message}`);
    } finally {
      setControlBusy(false);
    }
  }

  // ── Create key ───────────────────────────────────────────────────────────────
  async function doCreateKey(e) {
    e.preventDefault();
    setCreateBusy(true);
    try {
      const d = await apiFetch(backendUrl, '/admin/api/users', token, {
        method: 'POST',
        body: JSON.stringify({ email: newEmail.trim(), department: newDept.trim() || 'default' }),
      });
      setNewKeyResult(d);
      setNewEmail(''); setNewDept('');
      await loadKeys();
    } catch (e) {
      setKeysErr(e.message);
    } finally {
      setCreateBusy(false);
    }
  }

  async function doDeleteKey(keyId) {
    if (!window.confirm('Delete this key? This cannot be undone.')) return;
    try {
      await apiFetch(backendUrl, `/admin/api/users/${encodeURIComponent(keyId)}`, token, { method: 'DELETE' });
      await loadKeys();
    } catch (e) {
      setKeysErr(e.message);
    }
  }

  async function doRotateKey(keyId) {
    try {
      const d = await apiFetch(backendUrl, `/admin/api/users/${encodeURIComponent(keyId)}/rotate`, token, { method: 'POST' });
      setNewKeyResult(d);
      await loadKeys();
    } catch (e) {
      setKeysErr(e.message);
    }
  }

  // ── Render ───────────────────────────────────────────────────────────────────
  return (
    <div className="flex flex-col h-full bg-[#0A0A0A] overflow-y-auto">

      {/* ── Top bar ── */}
      <div className="flex items-center gap-3 px-5 py-3 border-b border-white/10 bg-[#0D0D0D] shrink-0 flex-wrap">
        <Shield size={14} className="text-[#002FA7] shrink-0" />
        <span className="text-[11px] font-mono font-bold text-[#A0A0A0] tracking-wide uppercase flex-1">Admin Portal</span>

        {authenticated && (
          <span className="text-[10px] font-mono text-[#555]">
            signed in as <span className="text-[#A0A0A0]">{username}</span>
          </span>
        )}

        <button onClick={() => { setEditBackend(backendUrl); setCfgOpen(o => !o); }}
          className="flex items-center gap-1 text-[10px] font-mono text-[#555] hover:text-[#A0A0A0] px-2 py-1 border border-white/10 hover:border-white/20 transition-colors">
          <Settings2 size={10} /> {cfgOpen ? 'Close' : 'Config'}
        </button>

        {authenticated && (
          <button onClick={doLogout}
            className="flex items-center gap-1.5 px-2.5 py-1.5 border border-white/10 hover:border-red-500/30 text-[10px] font-mono text-[#555] hover:text-red-400 transition-colors">
            <LogOut size={10} /> Sign out
          </button>
        )}
      </div>

      {/* ── Config panel ── */}
      {cfgOpen && (
        <div className="px-5 py-3 border-b border-white/10 bg-[#0D0D0D] flex gap-3 items-end flex-wrap shrink-0">
          <div className="flex-1 min-w-48">
            <div className="text-[9px] font-mono text-[#555] uppercase tracking-wider mb-1">Backend URL</div>
            <input value={editBackend} onChange={e => setEditBackend(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter') { setBackendUrl(editBackend.replace(/\/+$/, '') || DEFAULT_BACKEND); setCfgOpen(false); }}}
              className="w-full bg-[#1A1A1A] border border-white/10 focus:border-[#002FA7] px-3 py-1.5 text-[11px] font-mono text-white outline-none" />
          </div>
          <button
            onClick={() => { setBackendUrl(editBackend.replace(/\/+$/, '') || DEFAULT_BACKEND); setCfgOpen(false); }}
            className="px-3 py-1.5 bg-[#002FA7] hover:bg-[#002585] text-[10px] font-mono text-white uppercase tracking-wider transition-colors">
            Apply
          </button>
        </div>
      )}

      {/* ── Login form (unauthenticated) ── */}
      {!authenticated && (
        <div className="flex flex-1 items-center justify-center p-6">
          <div className="w-full max-w-sm">
            <div className="flex flex-col items-center gap-2 mb-6">
              <div className="w-10 h-10 bg-[#002FA7] flex items-center justify-center shadow-[0_4px_16px_rgba(0,47,167,0.4)]">
                <Shield size={20} className="text-white" />
              </div>
              <p className="text-sm font-bold text-white">Admin login</p>
              <p className="text-[10px] text-[#555] font-mono text-center">{backendUrl}</p>
            </div>

            <form onSubmit={doLogin} className="space-y-3">
              <div>
                <div className="text-[9px] font-mono text-[#555] uppercase tracking-wider mb-1">Username</div>
                <input value={loginUser} onChange={e => setLoginUser(e.target.value)}
                  autoComplete="username" autoFocus
                  placeholder="admin"
                  className="w-full bg-[#141414] border border-white/10 focus:border-[#002FA7] px-3 py-2.5 text-sm font-mono text-white outline-none transition-colors" />
              </div>
              <div>
                <div className="text-[9px] font-mono text-[#555] uppercase tracking-wider mb-1">Password</div>
                <input type="password" value={loginPass} onChange={e => setLoginPass(e.target.value)}
                  autoComplete="current-password"
                  placeholder="••••••••"
                  className="w-full bg-[#141414] border border-white/10 focus:border-[#002FA7] px-3 py-2.5 text-sm font-mono text-white outline-none transition-colors" />
              </div>

              {loginErr && (
                <div className="flex items-center gap-2 px-3 py-2 bg-red-500/10 border border-red-500/20 text-[11px] font-mono text-red-400">
                  <AlertTriangle size={11} /> {loginErr}
                </div>
              )}

              <button type="submit" disabled={loginBusy || !loginPass}
                className="w-full flex items-center justify-center gap-2 py-2.5 bg-[#002FA7] hover:bg-[#002585] text-white text-[12px] font-mono uppercase tracking-wider transition-colors disabled:opacity-40 disabled:cursor-not-allowed">
                {loginBusy ? <Loader2 size={14} className="animate-spin" /> : <LogIn size={14} />}
                Sign in
              </button>
            </form>
          </div>
        </div>
      )}

      {/* ── Authenticated dashboard ── */}
      {authenticated && (
        <div className="flex-1 p-5 space-y-6 max-w-3xl w-full mx-auto">

          {/* ── Service status ── */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#444]">Services</h2>
              <button onClick={() => loadStatus()} disabled={statusBusy}
                className="flex items-center gap-1 text-[9px] font-mono text-[#555] hover:text-[#A0A0A0] transition-colors disabled:opacity-40">
                <RefreshCw size={9} className={statusBusy ? 'animate-spin' : ''} /> Refresh
              </button>
            </div>

            {statusErr && (
              <div className="px-3 py-2 mb-2 bg-red-500/10 border border-red-500/20 text-[11px] font-mono text-red-400">{statusErr}</div>
            )}

            {controlMsg && (
              <div className="px-3 py-2 mb-2 bg-[#002FA7]/10 border border-[#002FA7]/20 text-[11px] font-mono text-[#6699FF]">{controlMsg}</div>
            )}

            {statusBusy && !status ? (
              <div className="flex items-center gap-2 px-4 py-6 text-[#555]">
                <Loader2 size={14} className="animate-spin" />
                <span className="text-[11px] font-mono">Loading…</span>
              </div>
            ) : status ? (
              <div className="space-y-1.5">
                {Object.entries(status)
                  .filter(([k]) => k !== 'admin')
                  .map(([name, info]) => {
                    const running = typeof info === 'object'
                      ? (info.running ?? info.status === 'running')
                      : Boolean(info);
                    return (
                      <ServiceCard
                        key={name}
                        name={name}
                        running={running}
                        onControl={doControl}
                        loading={controlBusy}
                      />
                    );
                  })}
              </div>
            ) : (
              <div className="px-4 py-6 text-center text-[11px] font-mono text-[#555]">No status data</div>
            )}
          </section>

          {/* ── API Keys ── */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <h2 className="text-[10px] font-mono uppercase tracking-[0.18em] text-[#444]">API Keys</h2>
              <div className="flex items-center gap-2">
                <button onClick={() => loadKeys()} disabled={keysBusy}
                  className="flex items-center gap-1 text-[9px] font-mono text-[#555] hover:text-[#A0A0A0] transition-colors disabled:opacity-40">
                  <RefreshCw size={9} className={keysBusy ? 'animate-spin' : ''} /> Refresh
                </button>
                <button onClick={() => { setShowCreate(o => !o); setNewKeyResult(null); }}
                  className="flex items-center gap-1.5 px-2.5 py-1.5 bg-[#002FA7]/20 border border-[#002FA7]/30 hover:bg-[#002FA7]/30 text-[#6699FF] text-[10px] font-mono uppercase tracking-wider transition-colors">
                  <Plus size={10} /> New key
                </button>
              </div>
            </div>

            {/* Create form */}
            {showCreate && (
              <form onSubmit={doCreateKey}
                className="mb-3 px-4 py-3 bg-[#111] border border-white/8 flex flex-wrap gap-3 items-end">
                <div className="flex-1 min-w-40">
                  <div className="text-[9px] font-mono text-[#555] uppercase tracking-wider mb-1">Email / label</div>
                  <input value={newEmail} onChange={e => setNewEmail(e.target.value)} required
                    placeholder="user@example.com"
                    className="w-full bg-[#1A1A1A] border border-white/10 focus:border-[#002FA7] px-3 py-1.5 text-[11px] font-mono text-white outline-none" />
                </div>
                <div className="w-32">
                  <div className="text-[9px] font-mono text-[#555] uppercase tracking-wider mb-1">Department</div>
                  <input value={newDept} onChange={e => setNewDept(e.target.value)}
                    placeholder="default"
                    className="w-full bg-[#1A1A1A] border border-white/10 focus:border-[#002FA7] px-3 py-1.5 text-[11px] font-mono text-white outline-none" />
                </div>
                <button type="submit" disabled={createBusy || !newEmail}
                  className="flex items-center gap-1.5 px-3 py-1.5 bg-[#002FA7] hover:bg-[#002585] text-white text-[10px] font-mono uppercase tracking-wider transition-colors disabled:opacity-40">
                  {createBusy ? <Loader2 size={11} className="animate-spin" /> : <Plus size={11} />}
                  Create
                </button>
              </form>
            )}

            {/* New key result */}
            {newKeyResult && (
              <div className="mb-3 px-4 py-3 bg-green-500/5 border border-green-500/20 space-y-1">
                <div className="flex items-center gap-2 text-[10px] font-mono text-green-400">
                  <Check size={11} /> Key created — copy it now, it won't be shown again
                </div>
                <div className="flex items-center gap-2 bg-[#0A0A0A] border border-white/10 px-3 py-2 mt-2">
                  <code className="flex-1 text-[11px] font-mono text-white break-all">{newKeyResult.api_key}</code>
                  <CopyButton text={newKeyResult.api_key} />
                </div>
                <button onClick={() => setNewKeyResult(null)} className="text-[9px] font-mono text-[#555] hover:text-[#A0A0A0] mt-1 transition-colors">Dismiss</button>
              </div>
            )}

            {keysErr && (
              <div className="px-3 py-2 mb-2 bg-red-500/10 border border-red-500/20 text-[11px] font-mono text-red-400">{keysErr}</div>
            )}

            {keysBusy && keys.length === 0 ? (
              <div className="flex items-center gap-2 px-4 py-6 text-[#555]">
                <Loader2 size={14} className="animate-spin" />
                <span className="text-[11px] font-mono">Loading…</span>
              </div>
            ) : keys.length === 0 ? (
              <div className="px-4 py-6 text-center text-[11px] font-mono text-[#555]">No API keys found</div>
            ) : (
              <div className="space-y-1.5">
                {keys.map(k => (
                  <div key={k.key_id}
                    className="flex items-center gap-3 px-4 py-3 bg-[#111] border border-white/8 flex-wrap">
                    <Key size={12} className="text-[#444] shrink-0" />
                    <div className="flex-1 min-w-0">
                      <div className="text-[12px] font-mono text-[#C0C0C0] truncate">{k.email}</div>
                      <div className="text-[9px] font-mono text-[#444]">
                        {k.department} · {k.key_id} · {k.created ? new Date(k.created).toLocaleDateString() : ''}
                      </div>
                    </div>
                    <div className="flex gap-1.5 shrink-0">
                      <button onClick={() => doRotateKey(k.key_id)} title="Rotate key"
                        className="flex items-center gap-1 px-2 py-1.5 border border-white/10 hover:border-white/20 text-[9px] font-mono text-[#555] hover:text-[#A0A0A0] uppercase tracking-wider transition-colors">
                        <RotateCcw size={9} /> Rotate
                      </button>
                      <button onClick={() => doDeleteKey(k.key_id)} title="Delete key"
                        className="flex items-center gap-1 px-2 py-1.5 border border-red-500/20 hover:border-red-500/40 bg-red-500/5 hover:bg-red-500/10 text-[9px] font-mono text-red-500 hover:text-red-400 uppercase tracking-wider transition-colors">
                        <Trash2 size={9} /> Delete
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ── Quick link to full HTML admin ── */}
          <section className="pb-6">
            <div className="px-4 py-3 bg-[#111] border border-white/8 flex items-center justify-between flex-wrap gap-3">
              <div>
                <div className="text-[11px] font-mono text-[#A0A0A0]">Full admin portal</div>
                <div className="text-[9px] font-mono text-[#444] mt-0.5">
                  Server-side UI with advanced diagnostics and settings
                </div>
              </div>
              <a href={`${backendUrl.replace(/\/+$/, '')}/admin/ui/`} target="_blank" rel="noopener noreferrer"
                className="flex items-center gap-1.5 px-3 py-1.5 border border-white/10 hover:border-white/20 text-[10px] font-mono text-[#737373] hover:text-white uppercase tracking-wider transition-colors">
                Open ↗
              </a>
            </div>
          </section>

        </div>
      )}
    </div>
  );
}
