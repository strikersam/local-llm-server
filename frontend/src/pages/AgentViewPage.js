import React, { useState, useRef, useEffect } from 'react';
import { ExternalLink, Maximize2, Minimize2, Settings2, RefreshCw, X, AlertTriangle, CheckCircle2 } from 'lucide-react';

const LS_AGENT_URL = 'llmrelay_agent_url';
const DEFAULT_URL  = 'http://localhost:8000';

function isHttpsPage() {
  return window.location.protocol === 'https:';
}

function isLocalUrl(url) {
  try {
    const { hostname } = new URL(url);
    return hostname === 'localhost' || hostname === '127.0.0.1' || hostname.endsWith('.local');
  } catch {
    return false;
  }
}

export default function AgentViewPage() {
  const [backendUrl, setBackendUrl] = useState(
    () => localStorage.getItem(LS_AGENT_URL) || DEFAULT_URL,
  );
  const [editUrl, setEditUrl]       = useState('');
  const [showUrlBar, setShowUrlBar] = useState(false);
  const [fullscreen, setFullscreen] = useState(false);
  const [iframeKey, setIframeKey]   = useState(0);  // bump to reload iframe
  const [iframeLoaded, setIframeLoaded] = useState(false);
  const iframeRef = useRef(null);

  const agentAppUrl = backendUrl.replace(/\/+$/, '') + '/app';
  const mixedContent = isHttpsPage() && isLocalUrl(backendUrl) && !backendUrl.startsWith('https://');

  useEffect(() => {
    localStorage.setItem(LS_AGENT_URL, backendUrl);
  }, [backendUrl]);

  function openUrlBar() {
    setEditUrl(backendUrl);
    setShowUrlBar(true);
  }

  function applyUrl() {
    const trimmed = editUrl.trim().replace(/\/+$/, '');
    if (trimmed) {
      setBackendUrl(trimmed);
      setIframeKey(k => k + 1);
      setIframeLoaded(false);
    }
    setShowUrlBar(false);
  }

  function reload() {
    setIframeLoaded(false);
    setIframeKey(k => k + 1);
  }

  return (
    <div className={`flex flex-col bg-[#0A0A0A] ${fullscreen ? 'fixed inset-0 z-[9999]' : 'h-full'}`}>

      {/* ── Toolbar ─────────────────────────────────────────────────────────── */}
      <div className="flex items-center gap-2 px-4 h-11 border-b border-white/10 bg-[#111111] shrink-0">

        {/* URL pill — click to edit */}
        <button
          onClick={openUrlBar}
          className="flex items-center gap-2 px-3 py-1.5 border border-white/10 hover:border-white/20 text-[10px] font-mono text-[#737373] hover:text-[#A0A0A0] transition-colors max-w-[260px] truncate"
          title="Click to change backend URL"
        >
          <Settings2 size={10} />
          <span className="truncate">{agentAppUrl}</span>
        </button>

        {/* Status dot */}
        <div
          className={`w-1.5 h-1.5 rounded-full shrink-0 ${iframeLoaded ? 'bg-green-500' : 'bg-[#444]'}`}
          title={iframeLoaded ? 'Connected' : 'Loading…'}
        />

        <div className="flex-1" />

        {/* Reload */}
        <button
          onClick={reload}
          className="p-1.5 text-[#555] hover:text-[#A0A0A0] transition-colors"
          title="Reload"
        >
          <RefreshCw size={13} />
        </button>

        {/* Open in new tab */}
        <a
          href={agentAppUrl}
          target="_blank"
          rel="noreferrer"
          className="p-1.5 text-[#555] hover:text-[#A0A0A0] transition-colors"
          title="Open in new tab"
        >
          <ExternalLink size={13} />
        </a>

        {/* Fullscreen toggle */}
        <button
          onClick={() => setFullscreen(f => !f)}
          className="p-1.5 text-[#555] hover:text-[#A0A0A0] transition-colors"
          title={fullscreen ? 'Exit fullscreen' : 'Fullscreen'}
        >
          {fullscreen ? <Minimize2 size={13} /> : <Maximize2 size={13} />}
        </button>
      </div>

      {/* ── URL edit bar ─────────────────────────────────────────────────────── */}
      {showUrlBar && (
        <div className="flex items-center gap-2 px-4 py-2.5 bg-[#0F0F0F] border-b border-white/10 shrink-0">
          <span className="text-[10px] font-mono text-[#737373] shrink-0">Backend URL</span>
          <input
            autoFocus
            value={editUrl}
            onChange={e => setEditUrl(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter') applyUrl(); if (e.key === 'Escape') setShowUrlBar(false); }}
            placeholder="http://localhost:8000 or https://your-tunnel.trycloudflare.com"
            className="flex-1 bg-[#1A1A1A] border border-white/10 focus:border-[#002FA7] px-3 py-1.5 text-[11px] font-mono text-white outline-none"
          />
          <button onClick={applyUrl} className="px-3 py-1.5 bg-[#002FA7] hover:bg-[#002585] text-[10px] font-mono text-white uppercase tracking-wider transition-colors">Apply</button>
          <button onClick={() => setShowUrlBar(false)} className="p-1.5 text-[#555] hover:text-[#A0A0A0]"><X size={13} /></button>
        </div>
      )}

      {/* ── Mixed-content warning (HTTPS page → HTTP iframe) ─────────────────── */}
      {mixedContent && (
        <div className="flex items-start gap-3 px-4 py-3 bg-yellow-500/5 border-b border-yellow-500/20 text-[11px] font-mono shrink-0">
          <AlertTriangle size={14} className="text-yellow-500 mt-0.5 shrink-0" />
          <div className="text-[#A0A0A0] space-y-1">
            <div className="text-yellow-400 font-semibold">Mixed content — iframe may be blocked</div>
            <div>
              This page is served over <strong>HTTPS</strong> but the agent backend is <strong>HTTP</strong>.
              Browsers block mixed content by default.
              To fix, use one of:
            </div>
            <ul className="list-disc list-inside space-y-0.5 text-[#737373]">
              <li><strong className="text-white">Cloudflare Tunnel</strong> (free, no signup): <code className="bg-white/5 px-1">cloudflared tunnel --url http://localhost:8000</code></li>
              <li><strong className="text-white">ngrok</strong>: <code className="bg-white/5 px-1">ngrok http 8000</code></li>
              <li><strong className="text-white">Render / public HTTPS URL</strong> — paste it via the URL bar above</li>
            </ul>
            <div className="flex items-center gap-2 mt-1">
              <CheckCircle2 size={11} className="text-green-500" />
              <span>Or use <a href={agentAppUrl} target="_blank" rel="noreferrer" className="text-[#002FA7] underline">Open in new tab</a> — works even without HTTPS.</span>
            </div>
          </div>
        </div>
      )}

      {/* ── iframe ────────────────────────────────────────────────────────────── */}
      <div className="flex-1 relative overflow-hidden">
        {/* Loading overlay */}
        {!iframeLoaded && !mixedContent && (
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-3 bg-[#0A0A0A] z-10">
            <div className="w-6 h-6 border-2 border-[#002FA7] border-t-transparent rounded-full animate-spin" />
            <p className="text-[10px] font-mono text-[#555] uppercase tracking-widest">Connecting to agent…</p>
            <p className="text-[9px] font-mono text-[#333]">{agentAppUrl}</p>
          </div>
        )}

        {!mixedContent && (
          <iframe
            key={iframeKey}
            ref={iframeRef}
            src={agentAppUrl}
            className="w-full h-full border-0"
            title="Local LLM Agent UI"
            allow="clipboard-read; clipboard-write"
            onLoad={() => setIframeLoaded(true)}
            onError={() => setIframeLoaded(false)}
          />
        )}

        {/* Fallback for blocked mixed content */}
        {mixedContent && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-center px-6">
            <AlertTriangle size={32} className="text-yellow-500" />
            <div>
              <p className="text-sm font-bold text-white mb-1">Iframe blocked by browser</p>
              <p className="text-[11px] text-[#737373] max-w-sm">
                Set up a tunnel (Cloudflare or ngrok) and paste the <strong>HTTPS</strong> URL in the bar above, or open the agent directly:
              </p>
            </div>
            <a
              href={agentAppUrl}
              target="_blank"
              rel="noreferrer"
              className="flex items-center gap-2 px-4 py-2 bg-[#002FA7] hover:bg-[#002585] text-white text-[11px] font-mono uppercase tracking-wider transition-colors"
            >
              <ExternalLink size={12} /> Open Agent in New Tab
            </a>
            <div className="text-[10px] font-mono text-[#444]">{agentAppUrl}</div>
          </div>
        )}
      </div>
    </div>
  );
}
