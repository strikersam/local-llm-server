import React, { useState, useEffect } from 'react';
import { getObservabilityStatus, getPlatformInfo, getObservabilityMetrics } from '../api';
import { BarChart3, ExternalLink, CheckCircle, XCircle, Activity, Zap, TrendingUp, History } from 'lucide-react';

export default function ObservabilityPage() {
  const [status, setStatus] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [platform, setPlatform] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      getObservabilityStatus().then(r => setStatus(r.data)),
      getPlatformInfo().then(r => setPlatform(r.data)),
      getObservabilityMetrics().then(r => setMetrics(r.data)),
    ]).catch(() => {}).finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-8 text-xs text-[#737373] font-mono animate-pulse-slow">Loading observability data...</div>;

  const summary = metrics?.summary_24h || { total_requests: 0, total_tokens: 0, total_savings_usd: 0 };

  return (
    <div className="p-5 lg:p-7 max-w-5xl" data-testid="observability-page">
      <div className="mb-6 animate-fade-in">
        <h1 className="text-2xl font-bold tracking-tighter" style={{ fontFamily: 'Outfit, sans-serif' }}>Observability</h1>
        <p className="text-xs text-[#737373] mt-0.5">Langfuse integration for LLM usage tracking, cost analysis, and trace inspection</p>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
        {/* Connection Status */}
        <div className="border border-white/10 bg-[#141414] animate-fade-in" data-testid="langfuse-status">
          <div className="px-5 py-3 border-b border-white/10 flex justify-between items-center">
            <span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">LANGFUSE CONNECTION</span>
            {status?.connected && <span className="bg-green-500/10 text-green-500 text-[9px] px-1.5 py-0.5 font-mono">LIVE</span>}
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
                <span className="text-[#A0A0A0] font-mono truncate block">{status?.base_url || '—'}</span>
              </div>
              <div>
                <span className="text-[#737373]">Public Key: </span>
                <span className="text-[#A0A0A0] font-mono">{status?.public_key_prefix || '—'}</span>
              </div>
            </div>
          </div>
        </div>

        {/* Local Metrics Summary */}
        <div className="border border-white/10 bg-[#141414] animate-fade-in">
          <div className="px-5 py-3 border-b border-white/10">
            <span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">LOCAL USAGE (24H)</span>
          </div>
          <div className="p-5 grid grid-cols-3 gap-2">
            <div className="bg-white/5 p-3 border border-white/5 hover:border-white/10 transition-colors">
              <Activity size={12} className="text-[#002FA7] mb-1" />
              <div className="text-lg font-bold text-white tracking-tighter leading-none">{summary.total_requests}</div>
              <div className="text-[9px] text-[#737373] uppercase font-mono mt-1">Requests</div>
            </div>
            <div className="bg-white/5 p-3 border border-white/5 hover:border-white/10 transition-colors">
              <Zap size={12} className="text-[#002FA7] mb-1" />
              <div className="text-lg font-bold text-white tracking-tighter leading-none">{(summary.total_tokens / 1000).toFixed(1)}k</div>
              <div className="text-[9px] text-[#737373] uppercase font-mono mt-1">Tokens</div>
            </div>
            <div className="bg-white/5 p-3 border border-white/5 hover:border-white/10 transition-colors">
              <TrendingUp size={12} className="text-green-500 mb-1" />
              <div className="text-lg font-bold text-white tracking-tighter leading-none">${summary.total_savings_usd.toFixed(2)}</div>
              <div className="text-[9px] text-[#737373] uppercase font-mono mt-1">Savings</div>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Activity Table */}
      {metrics?.recent_traces?.length > 0 && (
        <div className="border border-white/10 bg-[#141414] mb-4 animate-fade-in">
          <div className="px-5 py-3 border-b border-white/10 flex items-center gap-2">
            <History size={14} className="text-[#A0A0A0]" />
            <span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">RECENT SYSTEM TRACES</span>
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-left text-[10px] border-collapse font-mono">
              <thead>
                <tr className="border-b border-white/5 text-[#737373]">
                  <th className="px-5 py-2 font-medium uppercase">Time</th>
                  <th className="px-5 py-2 font-medium uppercase">Task / Model</th>
                  <th className="px-5 py-2 font-medium uppercase">Tokens</th>
                  <th className="px-5 py-2 font-medium uppercase">Latency</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-white/5">
                {metrics.recent_traces.map((t) => (
                  <tr key={t._id} className="hover:bg-white/[0.02]">
                    <td className="px-5 py-2.5 text-[#A0A0A0]">{new Date(t.timestamp).toLocaleTimeString([], { hour12: false })}</td>
                    <td className="px-5 py-2.5">
                      <div className="text-white font-bold">{t.task_name}</div>
                      <div className="text-[#737373] opacity-70 italic">{t.model}</div>
                    </td>
                    <td className="px-5 py-2.5 text-[#A0A0A0]">{t.prompt_tokens + t.completion_tokens}</td>
                    <td className="px-5 py-2.5 text-[#A0A0A0]">{t.latency_ms}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Open Dashboard */}
      {status?.configured && (
        <a href={status.base_url} target="_blank" rel="noopener noreferrer"
          className="border border-[#002FA7]/30 bg-[#002FA7]/10 p-5 flex items-center gap-4 mb-4 hover:bg-[#002FA7]/15 transition-colors animate-fade-in"
          data-testid="open-langfuse-button">
          <BarChart3 size={24} className="text-[#002FA7]" />
          <div className="flex-1">
            <div className="text-sm text-white font-bold">Open Langfuse Cloud Dashboard</div>
            <div className="text-[10px] text-[#737373] font-mono mt-0.5">{status.base_url}</div>
          </div>
          <ExternalLink size={16} className="text-[#002FA7]" />
        </a>
      )}

      {/* What Langfuse tracks */}
      <div className="border border-white/10 bg-[#141414] animate-fade-in">
        <div className="px-5 py-3 border-b border-white/10">
          <span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">SYSTEM OBSERVABILITY CAPABILITIES</span>
        </div>
        <div className="p-5 grid grid-cols-2 lg:grid-cols-4 gap-4">
          {[
            { label: 'Token Usage', desc: 'Input/output tokens per request', icon: Activity },
            { label: 'Cost Tracking', desc: 'Commercial-equivalent USD savings', icon: BarChart3 },
            { label: 'Latency', desc: 'Response time + TTFT per call', icon: Zap },
            { label: 'User Attribution', desc: 'Per-user, per-department breakdowns', icon: TrendingUp },
          ].map(item => (
            <div key={item.label} className="border border-white/10 p-3 hover:bg-white/5 transition-colors">
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
