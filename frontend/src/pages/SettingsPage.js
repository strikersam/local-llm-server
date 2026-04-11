import React, { useState, useEffect, useRef, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { healthCheck, getPlatformInfo, githubStatus, getGithubStatus, startGithubOAuth, setGithubToken, deleteGithubToken, listGithubRepos, authorizeGithubRepos } from '../api';
import { Settings, CheckCircle, XCircle, ExternalLink, Github, Globe, Server, Cpu, Key, Loader2, Trash2, Lock, ChevronDown, ChevronUp } from 'lucide-react';

export default function SettingsPage() {
  const [health, setHealth] = useState(null);
  const [platform, setPlatform] = useState(null);
  const [ghStatus, setGhStatus] = useState(null);

  // PAT fallback state
  const [showPat, setShowPat] = useState(false);
  const [ghToken, setGhToken] = useState('');
  const [ghSaving, setGhSaving] = useState(false);
  const [ghErr, setGhErr] = useState('');
  const [ghOk, setGhOk] = useState('');

  // OAuth state
  const [oauthLoading, setOauthLoading] = useState(false);
  const popupRef = useRef(null);
  const messageListenerRef = useRef(null);

  const refreshGhStatus = useCallback(() => {
    githubStatus().then(r => setGhStatus(r.data)).catch(() => setGhStatus({ connected: false, oauth_enabled: false }));
  }, []);

  useEffect(() => {
    healthCheck().then(r => setHealth(r.data)).catch(() => {});
    getPlatformInfo().then(r => setPlatform(r.data)).catch(() => {});
    refreshGhStatus();
  }, [refreshGhStatus]);

  // Clean up any open popup + message listener when the component unmounts
  useEffect(() => {
    return () => {
      if (messageListenerRef.current) window.removeEventListener('message', messageListenerRef.current);
      if (popupRef.current && !popupRef.current.closed) popupRef.current.close();
    };
  }, []);

  const handleOAuthConnect = async () => {
    setGhErr('');
    setOauthLoading(true);
    try {
      const { data } = await startGithubOAuth();
      const w = 600, h = 720;
      const left = Math.max(0, (window.screen.width - w) / 2);
      const top = Math.max(0, (window.screen.height - h) / 2);
      const popup = window.open(
        data.url,
        'github-oauth',
        `width=${w},height=${h},top=${top},left=${left},toolbar=no,menubar=no,scrollbars=yes`,
      );
      popupRef.current = popup;

      if (!popup) {
        setGhErr('Popup was blocked. Allow popups for this site and try again.');
        setOauthLoading(false);
        return;
      }

      // Listen for the postMessage fired by the backend callback page.
      // Validate origin so forged messages from other windows are ignored.
      const backendOrigin = process.env.REACT_APP_BACKEND_URL
        ? new URL(process.env.REACT_APP_BACKEND_URL).origin
        : window.location.origin;
      const handler = (event) => {
        if (event.origin !== backendOrigin) return;
        if (!event.data || event.data.type !== 'github_oauth') return;
        window.removeEventListener('message', handler);
        messageListenerRef.current = null;
        setOauthLoading(false);
        if (event.data.success) {
          setGhStatus(prev => ({ ...prev, connected: true, login: event.data.login }));
          setGhOk(`Connected as @${event.data.login}`);
        } else {
          setGhErr(event.data.error || 'Authorization failed');
        }
      };
      messageListenerRef.current = handler;
      window.addEventListener('message', handler);

      // Fallback: poll until popup closes in case postMessage is blocked
      const poll = setInterval(() => {
        if (popup.closed) {
          clearInterval(poll);
          if (messageListenerRef.current) {
            window.removeEventListener('message', messageListenerRef.current);
            messageListenerRef.current = null;
          }
          setOauthLoading(false);
          // Re-fetch status to see if connection succeeded
          refreshGhStatus();
        }
      }, 500);
    } catch (e) {
      setGhErr(e?.response?.data?.detail || e.message || 'Failed to start OAuth flow');
      setOauthLoading(false);
    }
  };

  const handleSaveToken = async () => {
    if (!ghToken.trim()) return;
    setGhSaving(true);
    setGhErr('');
    setGhOk('');
    try {
      const { data } = await setGithubToken(ghToken.trim());
      setGhStatus(prev => ({ ...prev, connected: true, login: data.login }));
      setGhToken('');
      setGhOk(`Connected as @${data.login}`);
      setShowPat(false);
    } catch (e) {
      setGhErr(e?.response?.data?.detail || e.message || 'Invalid token');
    } finally {
      setGhSaving(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await deleteGithubToken();
      setGhStatus(prev => ({ ...prev, connected: false, login: undefined }));
      setGhOk('');
    } catch { }
  };

  const S = ({ ok, label }) => (
    <div className="flex items-center gap-2">
      {ok ? <CheckCircle size={14} className="text-green-500" /> : <XCircle size={14} className="text-[#FF3333]" />}
      <div><div className="text-[11px] text-white">{label}</div><div className="text-[9px] text-[#737373] font-mono uppercase">{ok ? 'CONNECTED' : 'OFFLINE'}</div></div>
    </div>
  );

  return (
    <div className="p-5 lg:p-7 max-w-4xl" data-testid="settings-page">
      <div className="mb-6 animate-fade-in">
        <h1 className="text-2xl font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>Settings</h1>
        <p className="text-xs text-[#737373] mt-0.5">System configuration, health status, and deployment info</p>
      </div>

      <div className="grid gap-3">
        {/* Health */}
        <div className="border border-white/10 bg-[#141414] stagger-1">
          <div className="px-4 py-2.5 border-b border-white/10"><span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">System Health</span></div>
          <div className="p-4 grid grid-cols-3 gap-4">
            <S ok={health?.status === 'ok'} label="System" />
            <S ok={health?.mongo} label="MongoDB" />
            <S ok={health?.ollama} label="Ollama" />
          </div>
        </div>

        {/* Public Access / ngrok */}
        <div className="border border-white/10 bg-[#141414] stagger-2">
          <div className="px-4 py-2.5 border-b border-white/10"><span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">Public Access (ngrok)</span></div>
          <div className="p-4">
            {platform?.ngrok_configured ? (
              <div className="flex items-center gap-3">
                <Globe size={16} className="text-green-500" />
                <div>
                  <div className="text-[11px] text-white font-bold">ngrok Configured</div>
                  <a href={`https://${platform.ngrok_domain}`} target="_blank" rel="noopener noreferrer" className="text-[10px] text-[#002FA7] font-mono flex items-center gap-1 mt-0.5">
                    {platform.ngrok_domain} <ExternalLink size={10} />
                  </a>
                </div>
              </div>
            ) : (
              <div className="text-[11px] text-[#737373]">ngrok not configured. Set NGROK_AUTHTOKEN and NGROK_DOMAIN in .env</div>
            )}
          </div>
        </div>

        {/* Architecture */}
        <div className="border border-white/10 bg-[#141414] stagger-3">
          <div className="px-4 py-2.5 border-b border-white/10"><span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">Architecture — Karpathy LLM Wiki Pattern</span></div>
          <div className="p-4 grid grid-cols-3 gap-3">
            {[
              { n: '01', label: 'RAW SOURCES', desc: 'Files, URLs, text — ingested and AI-processed' },
              { n: '02', label: 'WIKI', desc: 'LLM-maintained markdown knowledge base' },
              { n: '03', label: 'AGENT', desc: 'Query, lint, cross-reference, expand' },
            ].map(l => (
              <div key={l.n} className="border border-white/10 p-3">
                <div className="text-xl font-bold text-[#002FA7] mb-1" style={{ fontFamily: 'Chivo, sans-serif' }}>{l.n}</div>
                <div className="text-[9px] tracking-[0.15em] uppercase text-white font-mono font-bold mb-0.5">{l.label}</div>
                <p className="text-[10px] text-[#737373] leading-relaxed">{l.desc}</p>
              </div>
            ))}
          </div>
        </div>

        {/* GitHub Integration */}
        <div className="border border-white/10 bg-[#141414] stagger-4">
          <div className="px-4 py-2.5 border-b border-white/10 flex items-center gap-2">
            <Github size={13} className="text-[#A0A0A0]" />
            <span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">GitHub Integration</span>
          </div>
          <div className="p-4 space-y-4">

            {/* ── Connected state ── */}
            {ghStatus?.connected ? (
              <div className="space-y-3">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-8 h-8 bg-[#002FA7]/20 border border-[#002FA7]/40 flex items-center justify-center">
                      <Github size={15} className="text-[#002FA7]" />
                    </div>
                    <div>
                      <div className="flex items-center gap-1.5">
                        <CheckCircle size={11} className="text-green-500" />
                        <span className="text-[11px] text-white font-bold">GitHub connected</span>
                      </div>
                      <div className="text-[10px] text-[#737373] font-mono mt-0.5">@{ghStatus.login}</div>
                    </div>
                  </div>
                  <button onClick={handleDisconnect}
                    className="flex items-center gap-1 text-[9px] text-[#737373] hover:text-[#FF3333] transition-colors font-mono uppercase tracking-wider border border-white/10 hover:border-[#FF3333]/30 px-2 py-1">
                    <Trash2 size={10} /> Disconnect
                  </button>
                </div>
                <Link to="/github"
                  className="inline-flex items-center gap-1.5 bg-[#002FA7] hover:bg-[#002585] text-white px-4 py-2 text-[10px] tracking-wider uppercase font-mono transition-colors">
                  <Github size={11} /> Open GitHub Repos
                </Link>
              </div>
            ) : (
              /* ── Not connected state ── */
              <div className="space-y-3">
                <p className="text-[11px] text-[#737373] leading-relaxed">
                  Connect your GitHub account to browse repos, edit files, and create pull requests directly from this dashboard.
                </p>

                {/* OAuth button — shown when the server has GITHUB_CLIENT_ID configured */}
                {ghStatus?.oauth_enabled ? (
                  <button
                    onClick={handleOAuthConnect}
                    disabled={oauthLoading}
                    className="w-full flex items-center justify-center gap-2 border border-white/20 hover:border-[#002FA7] bg-[#141414] hover:bg-[#002FA7]/10 text-white py-2.5 text-[11px] tracking-wider uppercase font-mono transition-all disabled:opacity-50 group"
                  >
                    {oauthLoading
                      ? <Loader2 size={14} className="animate-spin" />
                      : <Github size={14} className="group-hover:text-[#002FA7] transition-colors" />}
                    {oauthLoading ? 'Waiting for GitHub…' : 'Connect with GitHub'}
                  </button>
                ) : (
                  /* Server not configured for OAuth — show PAT directly */
                  <div className="border border-yellow-500/20 bg-yellow-500/5 p-3 text-[10px] text-yellow-400/80 font-mono leading-relaxed">
                    OAuth not configured on this server. Set <code>GITHUB_CLIENT_ID</code> &amp; <code>GITHUB_CLIENT_SECRET</code> to enable one-click connect, or use a token below.
                  </div>
                )}

                {ghErr && <div className="text-[10px] text-[#FF3333] font-mono">{ghErr}</div>}
                {ghOk && <div className="text-[10px] text-green-400 font-mono">{ghOk}</div>}

                {/* PAT fallback — always available as an alternative */}
                <div>
                  <button
                    onClick={() => setShowPat(v => !v)}
                    className="flex items-center gap-1.5 text-[9px] text-[#737373] hover:text-[#A0A0A0] transition-colors font-mono uppercase tracking-wider"
                  >
                    <Lock size={10} />
                    {ghStatus?.oauth_enabled ? 'Use a Personal Access Token instead' : 'Enter Personal Access Token'}
                    {showPat ? <ChevronUp size={10} /> : <ChevronDown size={10} />}
                  </button>

                  {showPat && (
                    <div className="mt-2 space-y-2 animate-fade-in">
                      <p className="text-[10px] text-[#737373]">
                        Generate a classic token with <code className="text-[#002FA7]">repo</code> scope at{' '}
                        <a href="https://github.com/settings/tokens/new?scopes=repo&description=local-llm-server"
                          target="_blank" rel="noopener noreferrer"
                          className="text-[#002FA7] hover:underline inline-flex items-center gap-0.5">
                          github.com/settings/tokens <ExternalLink size={9} />
                        </a>
                      </p>
                      <div className="flex gap-2">
                        <input
                          type="password"
                          value={ghToken}
                          onChange={e => setGhToken(e.target.value)}
                          placeholder="ghp_…"
                          className="flex-1 bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]"
                          onKeyDown={e => e.key === 'Enter' && handleSaveToken()}
                          autoComplete="off"
                        />
                        <button onClick={handleSaveToken} disabled={ghSaving || !ghToken.trim()}
                          className="flex items-center gap-1.5 bg-[#002FA7] hover:bg-[#002585] text-white px-4 py-2 text-[10px] tracking-wider uppercase font-mono disabled:opacity-40 shrink-0">
                          {ghSaving ? <Loader2 size={11} className="animate-spin" /> : <Key size={11} />} Save
                        </button>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        </div>

        {/* Quick Start */}
        <div className="border border-white/10 bg-[#141414] stagger-5">
          <div className="px-4 py-2.5 border-b border-white/10"><span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">Self-Hosting Guide</span></div>
          <div className="p-4 space-y-3">
            <div className="bg-[#0A0A0A] border border-white/10 p-3 text-[10px] font-mono text-[#A0A0A0]">
              <div className="text-[#737373]"># Clone & run</div>
              <div>git clone https://github.com/strikersam/local-llm-server</div>
              <div>docker compose up -d</div>
              <div className="text-[#737373] mt-2"># Default credentials</div>
              <div>Email: admin@llmrelay.local</div>
              <div>Password: WikiAdmin2026!</div>
            </div>
            <a href="https://github.com/strikersam/local-llm-server" target="_blank" rel="noopener noreferrer"
              className="flex items-center gap-2 text-[11px] text-[#002FA7] hover:underline">
              <Github size={13} /> View on GitHub <ExternalLink size={10} />
            </a>
          </div>
        </div>

        {/* Platform Info */}
        <div className="border border-white/10 bg-[#141414] stagger-5">
          <div className="px-4 py-2.5 border-b border-white/10"><span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">Platform Info</span></div>
          <div className="p-4 grid grid-cols-2 gap-3 text-[11px]">
            <div><span className="text-[#737373]">Version: </span><span className="text-white font-mono">{platform?.version || '—'}</span></div>
            <div><span className="text-[#737373]">Ollama Base: </span><span className="text-white font-mono">{platform?.ollama_base || '—'}</span></div>
            <div><span className="text-[#737373]">Langfuse: </span><span className={platform?.langfuse_configured ? 'text-green-500' : 'text-[#737373]'}>{platform?.langfuse_configured ? 'Configured' : 'Not configured'}</span></div>
            <div><span className={platform?.ngrok_configured ? 'text-green-500' : 'text-[#737373]'}>{platform?.ngrok_configured ? 'ngrok Configured' : 'ngrok Not configured'}</span></div>
          </div>
        </div>

        {/* GitHub Repository Access */}
        <GitHubAccessSection />
      </div>
    </div>
  );
}

function GitHubAccessSection() {
  const [status, setStatus] = useState(null);
  const [repos, setRepos] = useState([]);
  const [selectedRepos, setSelectedRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [connecting, setConnecting] = useState(false);
  const [connErr, setConnErr] = useState('');
  const popupRef = useRef(null);

  const refresh = useCallback(() => {
    setLoading(true);
    Promise.all([getGithubStatus(), listGithubRepos()])
      .then(([s, r]) => {
        setStatus(s.data);
        setRepos(r.data.repos || []);
        setSelectedRepos(s.data.authorized_repos || []);
      })
      .catch(err => console.error('Failed to fetch GH status', err))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    refresh();
  }, []);

  const handleToggleRepo = (fullName) => {
    setSelectedRepos(prev => 
      prev.includes(fullName) ? prev.filter(r => r !== fullName) : [...prev, fullName]
    );
  };

  const handleConnect = useCallback(async () => {
    setConnErr('');
    if (!status?.oauth_enabled) {
      setConnErr('OAuth not configured on this server. Set GITHUB_CLIENT_ID and GITHUB_CLIENT_SECRET in your .env file.');
      return;
    }
    setConnecting(true);
    try {
      const { data } = await startGithubOAuth();
      const popup = window.open(data.url, 'github_oauth', 'width=600,height=700,scrollbars=yes');
      if (!popup) {
        setConnErr('Popup was blocked. Allow popups for this site and try again.');
        setConnecting(false);
        return;
      }
      popupRef.current = popup;
      const backendOrigin = process.env.REACT_APP_BACKEND_URL
        ? new URL(process.env.REACT_APP_BACKEND_URL).origin
        : window.location.origin;
      const handler = (event) => {
        if (event.origin !== backendOrigin) return;
        if (!event.data || event.data.type !== 'github_oauth') return;
        window.removeEventListener('message', handler);
        setConnecting(false);
        if (event.data.success) {
          refresh();
        } else {
          setConnErr(event.data.error || 'Authorization failed');
        }
      };
      window.addEventListener('message', handler);
      const poll = setInterval(() => {
        if (popup.closed) {
          clearInterval(poll);
          window.removeEventListener('message', handler);
          setConnecting(false);
          refresh();
        }
      }, 500);
    } catch (e) {
      setConnErr(e?.response?.data?.detail || e.message || 'Failed to start OAuth flow');
      setConnecting(false);
    }
  }, [refresh, status]);

  const handleSave = async () => {
    setSaving(true);
    try {
      await authorizeGithubRepos(selectedRepos);
      refresh();
    } catch (err) {
      alert('Failed to save repository settings');
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="border border-white/10 bg-[#141414] stagger-6 overflow-hidden">
      <div className="px-4 py-2.5 border-b border-white/10 flex items-center justify-between bg-white/[0.02]">
        <div className="flex items-center gap-2">
          <Github size={14} className="text-[#002FA7]" />
          <span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">GitHub Repository Access</span>
        </div>
        {status?.connected && (
          <div className="flex items-center gap-1.5">
            <div className="w-1 h-1 bg-green-500 rounded-full animate-pulse" />
            <span className="text-[9px] text-green-500 font-mono uppercase font-bold tracking-widest">{status.github_login}</span>
          </div>
        )}
      </div>
      <div className="p-5">
        {!status?.connected ? (
          <div className="space-y-4">
            <p className="text-[11px] text-[#A0A0A0] leading-relaxed">
              Connect your GitHub account with <code className="text-[#002FA7] bg-[#002FA7]/10 px-1">repo</code> scope to allow the agent to manage your repositories directly.
            </p>
            {status?.oauth_enabled ? (
              <button onClick={handleConnect} disabled={connecting}
                 className="inline-flex items-center gap-2 bg-[#002FA7] hover:bg-[#002585] text-white px-4 py-2 text-[10px] font-mono font-bold tracking-widest uppercase transition-all disabled:opacity-50">
                {connecting ? <Loader2 size={14} className="animate-spin" /> : <Github size={14} />}
                {connecting ? 'Connecting…' : 'Connect GitHub'}
              </button>
            ) : (
              <div className="border border-yellow-500/20 bg-yellow-500/5 p-3 text-[10px] text-yellow-400/80 font-mono leading-relaxed">
                OAuth not configured. Set <code>GITHUB_CLIENT_ID</code> &amp; <code>GITHUB_CLIENT_SECRET</code> in your .env file to enable GitHub connection.
              </div>
            )}
            {connErr && <div className="text-[10px] text-[#FF3333] font-mono">{connErr}</div>}
          </div>
        ) : (
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <h3 className="text-[11px] text-white font-bold tracking-tight">Select Authorized Repositories</h3>
              <div className="flex gap-2">
                <button onClick={refresh} className="text-[9px] text-[#A0A0A0] hover:text-white transition-colors font-mono uppercase">Refresh List</button>
                {status?.oauth_enabled && (
                  <button onClick={handleConnect} disabled={connecting} className="text-[9px] text-[#002FA7] hover:underline font-mono uppercase disabled:opacity-50">
                    {connecting ? 'Re-Authing…' : 'Re-Auth'}
                  </button>
                )}
              </div>
            </div>
            {connErr && <div className="text-[10px] text-[#FF3333] font-mono">{connErr}</div>}

            <div className="max-h-60 overflow-y-auto border border-white/5 bg-black/20 divide-y divide-white/5 custom-scrollbar">
              {loading ? (
                <div className="p-8 text-center text-[10px] text-[#737373] animate-pulse font-mono uppercase">Loading repositories...</div>
              ) : repos.length > 0 ? (
                repos.map(repo => (
                  <label key={repo.id} className="flex items-center gap-3 px-3 py-2.5 cursor-pointer hover:bg-white/[0.03] transition-colors group">
                    <input 
                      type="checkbox" 
                      className="hidden"
                      checked={selectedRepos.includes(repo.full_name)}
                      onChange={() => handleToggleRepo(repo.full_name)}
                    />
                    <div className={`w-3.5 h-3.5 border flex items-center justify-center transition-all ${
                        selectedRepos.includes(repo.full_name) ? 'bg-[#002FA7] border-[#002FA7]' : 'border-white/20 group-hover:border-white/40'
                      }`}>
                      {selectedRepos.includes(repo.full_name) && <div className="w-1.5 h-1.5 bg-white" />}
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-[11px] text-white font-mono truncate">{repo.full_name}</span>
                        {repo.private && <span className="text-[8px] bg-white/10 px-1 text-[#737373] font-mono">PRIVATE</span>}
                      </div>
                      {repo.description && <div className="text-[9px] text-[#737373] truncate">{repo.description}</div>}
                    </div>
                  </label>
                ))
              ) : (
                <div className="p-8 text-center text-[10px] text-[#737373] font-mono whitespace-pre-wrap">
                  No repositories found or access denied.{"\n"}Try re-authenticating with full scopes.
                </div>
              )}
            </div>

            <div className="flex items-center justify-between pt-2">
              <span className="text-[9px] text-[#737373] font-mono">
                {selectedRepos.length} repository granted access
              </span>
              <button 
                onClick={handleSave}
                disabled={saving || loading}
                className="bg-white/5 hover:bg-white/10 border border-white/10 px-4 py-2 text-[10px] text-white font-mono font-bold tracking-widest uppercase transition-all disabled:opacity-30">
                {saving ? 'Saving...' : 'Save Permissions'}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
