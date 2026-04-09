import React, { useState, useEffect } from 'react';
import { getObservabilityStatus, getPlatformInfo } from '../api';
import { BarChart3, ExternalLink, CheckCircle, XCircle, Loader2, Activity } from 'lucide-react';

export default function ObservabilityPage() {
  const [status, setStatus] = useState(null);
  const [platform, setPlatform] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getObservabilityStatus().then(r => setStatus(r.data)),
      getPlatformInfo().then(r => setPlatform(r.data)),
    ]).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-xs text-[#737373] font-mono animate-pulse-slow">Loading observability data...</div>;

  return (
    <div className="p-5 lg:p-7 max-w-5xl" data-testid="observability-page">
      <div className="mb-6 animate-fade-in">
        <h1 className="text-2xl font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>Observability</h1>
        <p className="text-xs text-[#737373] mt-0.5">Langfuse integration for LLM usage tracking, cost analysis, and trace inspection</p>
      </div>

      {/* Connection Status */}
      <div className="border border-white/10 bg-[#141414] mb-4 animate-fade-in" data-testid="langfuse-status">
        <div className="px-5 py-3 border-b border-white/10">
          <span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">LANGFUSE CONNECTION</span>
        </div>
        <div className="p-5">
          <div className="flex items-center gap-3 mb-4">
            {status?.connected ? (
              <CheckCircle size={20} className="text-green-500" />
            ) : status?.configured ? (
              <XCircle size={20} className="text-[#FF3333]" />
            ) : (
              <XCircle size={20} className="text-[#737373]" />
            )}
            <div>
              <div className="text-sm text-white font-bold">
                {status?.connected ? 'Connected' : status?.configured ? 'Configuration Error' : 'Not Configured'}
              </div>
              <div className="text-[10px] text-[#737373] font-mono">{status?.message}</div>
            </div>
          </div>
          <div className="grid grid-cols-2 gap-4 text-[11px]">
            <div>
              <span className="text-[#737373]">Base URL: </span>
              <span className="text-[#A0A0A0] font-mono">{status?.base_url || '—'}</span>
            </div>
            <div>
              <span className="text-[#737373]">Public Key: </span>
              <span className="text-[#A0A0A0] font-mono">{status?.public_key_prefix || '—'}</span>
            </div>
          </div>
        </div>
      </div>

      {/* Open Dashboard */}
      {status?.configured && (
        <a href={status.base_url} target="_blank" rel="noopener noreferrer"
          className="border border-[#002FA7]/30 bg-[#002FA7]/10 p-5 flex items-center gap-4 mb-4 hover:bg-[#002FA7]/15 transition-colors animate-fade-in"
          data-testid="open-langfuse-button">
          <BarChart3 size={24} className="text-[#002FA7]" />
          <div className="flex-1">
            <div className="text-sm text-white font-bold">Open Langfuse Dashboard</div>
            <div className="text-[10px] text-[#737373] font-mono mt-0.5">{status.base_url}</div>
          </div>
          <ExternalLink size={16} className="text-[#002FA7]" />
        </a>
      )}

      {/* What Langfuse tracks */}
      <div className="border border-white/10 bg-[#141414] animate-fade-in">
        <div className="px-5 py-3 border-b border-white/10">
          <span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">WHAT LANGFUSE TRACKS</span>
        </div>
        <div className="p-5 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Token Usage', desc: 'Input/output tokens per request', icon: Activity },
            { label: 'Cost Tracking', desc: 'Commercial-equivalent USD savings', icon: BarChart3 },
            { label: 'Latency', desc: 'Response time + TTFT per call', icon: Activity },
            { label: 'User Attribution', desc: 'Per-user, per-department breakdowns', icon: Activity },
          ].map(item => (
            <div key={item.label} className="border border-white/10 p-3">
              <item.icon size={14} className="text-[#002FA7] mb-2" />
              <div className="text-[11px] text-white font-bold">{item.label}</div>
              <div className="text-[10px] text-[#737373] mt-0.5">{item.desc}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Setup guide if not configured */}
      {!status?.configured && (
        <div className="border border-white/10 bg-[#141414] mt-4 p-5 animate-fade-in">
          <div className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold mb-3">SETUP GUIDE</div>
          <div className="space-y-2 text-[11px] text-[#A0A0A0]">
            <p>1. Create a project at <a href="https://cloud.langfuse.com" target="_blank" rel="noopener noreferrer" className="text-[#002FA7]">cloud.langfuse.com</a></p>
            <p>2. Copy your Public Key and Secret Key</p>
            <p>3. Add to your <code className="bg-white/5 px-1.5 py-0.5 text-[10px]">.env</code> file:</p>
            <pre className="bg-[#0A0A0A] border border-white/10 p-3 text-[10px] font-mono text-[#737373]">
              LANGFUSE_PUBLIC_KEY=pk-lf-...{'\n'}LANGFUSE_SECRET_KEY=sk-lf-...{'\n'}LANGFUSE_BASE_URL=https://cloud.langfuse.com
            </pre>
          </div>
        </div>
      )}
    </div>
  );
}
