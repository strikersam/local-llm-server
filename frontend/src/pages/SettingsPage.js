import React, { useState, useEffect } from 'react';
import { healthCheck, getPlatformInfo, githubStatus, setGithubToken, deleteGithubToken } from '../api';
import { Settings, CheckCircle, XCircle, ExternalLink, Github, Globe, Server, Cpu, Key, Loader2, Trash2 } from 'lucide-react';

export default function SettingsPage() {
  const [health, setHealth] = useState(null);
  const [platform, setPlatform] = useState(null);
  const [ghStatus, setGhStatus] = useState(null);
  const [ghToken, setGhToken] = useState('');
  const [ghSaving, setGhSaving] = useState(false);
  const [ghErr, setGhErr] = useState('');
  const [ghOk, setGhOk] = useState('');

  useEffect(() => {
    healthCheck().then(r => setHealth(r.data)).catch(() => {});
    getPlatformInfo().then(r => setPlatform(r.data)).catch(() => {});
    githubStatus().then(r => setGhStatus(r.data)).catch(() => setGhStatus({ connected: false }));
  }, []);

  const handleSaveToken = async () => {
    if (!ghToken.trim()) return;
    setGhSaving(true);
    setGhErr('');
    setGhOk('');
    try {
      const { data } = await setGithubToken(ghToken.trim());
      setGhStatus({ connected: true, login: data.login });
      setGhToken('');
      setGhOk(`Connected as @${data.login}`);
    } catch (e) {
      setGhErr(e?.response?.data?.detail || e.message || 'Failed to save token');
    } finally {
      setGhSaving(false);
    }
  };

  const handleDisconnect = async () => {
    try {
      await deleteGithubToken();
      setGhStatus({ connected: false });
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
          <div className="p-4 space-y-3">
            {ghStatus?.connected ? (
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <CheckCircle size={14} className="text-green-500" />
                  <div>
                    <div className="text-[11px] text-white font-bold">Connected</div>
                    <div className="text-[10px] text-[#737373] font-mono">@{ghStatus.login}</div>
                  </div>
                </div>
                <button onClick={handleDisconnect}
                  className="flex items-center gap-1 text-[9px] text-[#737373] hover:text-[#FF3333] transition-colors font-mono uppercase tracking-wider">
                  <Trash2 size={11} /> Disconnect
                </button>
              </div>
            ) : (
              <div className="flex items-center gap-2">
                <XCircle size={14} className="text-[#737373]" />
                <div className="text-[11px] text-[#737373]">Not connected</div>
              </div>
            )}

            {!ghStatus?.connected && (
              <div className="space-y-2">
                <p className="text-[10px] text-[#737373] leading-relaxed">
                  Paste a GitHub Personal Access Token (classic) with <code className="text-[#002FA7]">repo</code> scope.
                  <a href="https://github.com/settings/tokens/new?scopes=repo&description=local-llm-server"
                    target="_blank" rel="noopener noreferrer"
                    className="ml-1 text-[#002FA7] hover:underline inline-flex items-center gap-0.5">
                    Create token <ExternalLink size={9} />
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
                  />
                  <button onClick={handleSaveToken} disabled={ghSaving || !ghToken.trim()}
                    className="flex items-center gap-1.5 bg-[#002FA7] hover:bg-[#002585] text-white px-4 py-2 text-[10px] tracking-wider uppercase font-mono disabled:opacity-40 shrink-0">
                    {ghSaving ? <Loader2 size={11} className="animate-spin" /> : <Key size={11} />} Connect
                  </button>
                </div>
                {ghErr && <div className="text-[10px] text-[#FF3333] font-mono">{ghErr}</div>}
                {ghOk && <div className="text-[10px] text-green-400 font-mono">{ghOk}</div>}
              </div>
            )}

            {ghStatus?.connected && (
              <a href="/github"
                className="inline-flex items-center gap-1.5 text-[10px] text-[#002FA7] hover:underline font-mono">
                <Github size={11} /> Open GitHub Repos
              </a>
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
            <div><span className="text-[#737373]">ngrok: </span><span className={platform?.ngrok_configured ? 'text-green-500' : 'text-[#737373]'}>{platform?.ngrok_configured ? 'Configured' : 'Not configured'}</span></div>
          </div>
        </div>
      </div>
    </div>
  );
}
