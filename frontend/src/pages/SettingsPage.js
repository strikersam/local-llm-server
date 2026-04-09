import React, { useState, useEffect } from 'react';
import { getProviders, healthCheck } from '../api';
import { Settings, Cpu, Globe, Server, CheckCircle, XCircle, ExternalLink } from 'lucide-react';

export default function SettingsPage() {
  const [providers, setProviders] = useState(null);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getProviders().then(r => setProviders(r.data)).catch(() => {});
    healthCheck().then(r => setHealth(r.data)).catch(() => {});
  }, []);

  return (
    <div className="p-6 lg:p-8 max-w-4xl" data-testid="settings-page">
      <div className="mb-8 animate-fade-in">
        <h1 className="text-2xl font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>Settings</h1>
        <p className="text-xs text-[#737373] mt-1">System configuration and provider management</p>
      </div>

      <div className="grid gap-4">
        {/* Health */}
        <div className="border border-white/10 bg-[#141414] stagger-1">
          <div className="px-5 py-3 border-b border-white/10">
            <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">System Health</span>
          </div>
          <div className="p-5">
            {health ? (
              <div className="grid grid-cols-2 gap-4">
                <div className="flex items-center gap-3">
                  {health.status === 'ok' ? <CheckCircle size={16} className="text-green-500" /> : <XCircle size={16} className="text-[#FF3333]" />}
                  <div>
                    <div className="text-xs text-white">System Status</div>
                    <div className="text-[10px] text-[#737373] font-mono uppercase">{health.status}</div>
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  {health.mongo ? <CheckCircle size={16} className="text-green-500" /> : <XCircle size={16} className="text-[#FF3333]" />}
                  <div>
                    <div className="text-xs text-white">MongoDB</div>
                    <div className="text-[10px] text-[#737373] font-mono">{health.mongo ? 'CONNECTED' : 'DISCONNECTED'}</div>
                  </div>
                </div>
              </div>
            ) : (
              <div className="text-xs text-[#737373]">Loading...</div>
            )}
          </div>
        </div>

        {/* Providers */}
        <div className="border border-white/10 bg-[#141414] stagger-2">
          <div className="px-5 py-3 border-b border-white/10">
            <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">LLM Providers</span>
          </div>
          <div className="divide-y divide-white/5">
            {providers?.providers?.map(p => (
              <div key={p.id} className="flex items-center gap-4 px-5 py-4" data-testid={`provider-${p.id}`}>
                <div className={`w-8 h-8 flex items-center justify-center ${p.status === 'active' ? 'bg-[#002FA7]' : 'bg-white/5'}`}>
                  {p.id === 'ollama' ? <Server size={16} /> : <Globe size={16} />}
                </div>
                <div className="flex-1">
                  <div className="text-xs text-white">{p.name}</div>
                  <div className="text-[10px] text-[#737373] font-mono uppercase">{p.status}</div>
                </div>
                {p.status === 'active' && (
                  <div className="w-2 h-2 bg-green-500 rounded-full" />
                )}
              </div>
            ))}
          </div>
        </div>

        {/* Docker info */}
        <div className="border border-white/10 bg-[#141414] stagger-3">
          <div className="px-5 py-3 border-b border-white/10">
            <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">Self-Hosting Guide</span>
          </div>
          <div className="p-5 space-y-3">
            <p className="text-xs text-[#A0A0A0]">
              This dashboard is designed to run fully self-hosted. Use the provided docker-compose.yml to deploy on your own server.
            </p>
            <div className="bg-[#0A0A0A] border border-white/10 p-4 text-xs font-mono text-[#A0A0A0]">
              <div className="text-[#737373] mb-2"># Quick start</div>
              <div>git clone &lt;repo&gt;</div>
              <div>docker compose up -d</div>
              <div className="text-[#737373] mt-2"># Default login</div>
              <div>Email: admin@llmwiki.local</div>
              <div>Password: WikiAdmin2026!</div>
            </div>
            <div className="flex items-center gap-2 text-xs text-[#002FA7]">
              <ExternalLink size={12} />
              <span>See README.md for full documentation</span>
            </div>
          </div>
        </div>

        {/* Architecture */}
        <div className="border border-white/10 bg-[#141414] stagger-4">
          <div className="px-5 py-3 border-b border-white/10">
            <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">Architecture</span>
          </div>
          <div className="p-5 grid grid-cols-3 gap-4">
            {[
              { label: 'RAW SOURCES', desc: 'Files, URLs, text inputs ingested and processed by AI', icon: '01' },
              { label: 'WIKI', desc: 'LLM-maintained markdown knowledge base with cross-references', icon: '02' },
              { label: 'SCHEMA', desc: 'Structured data extracted from wiki pages for queries', icon: '03' },
            ].map((layer, i) => (
              <div key={i} className="border border-white/10 p-4">
                <div className="text-2xl font-bold text-[#002FA7] mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>{layer.icon}</div>
                <div className="text-[10px] tracking-[0.15em] uppercase text-white font-mono font-bold mb-1">{layer.label}</div>
                <p className="text-[10px] text-[#737373] leading-relaxed">{layer.desc}</p>
              </div>
            ))}
          </div>
        </div>
      </div>
    </div>
  );
}
