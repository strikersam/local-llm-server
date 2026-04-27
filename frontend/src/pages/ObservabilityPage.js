/**
 * ObservabilityPage.js — Cost Insights & Langfuse Integration (v3.1)
 *
 * Shows:
 *   - Total savings vs cloud APIs (this month / week / day)
 *   - Token usage breakdown by model
 *   - Time-series savings chart
 *   - Langfuse connection status
 *   - Per-user savings (admin/power user view)
 */

import React, { useState, useEffect } from 'react';
import { getSavings, getUsage } from '../api';

const fmt = (n) => (n == null ? '—' : typeof n === 'number' ? n.toFixed(4) : n);
const fmtBig = (n) => (n == null ? '—' : n >= 1000 ? `$${(n/1000).toFixed(2)}K` : `$${n.toFixed(4)}`);

function StatCard({ label, value, sub, color = 'indigo' }) {
  const colors = {
    indigo: 'border-indigo-100 bg-indigo-50 text-indigo-700',
    green:  'border-green-100  bg-green-50  text-green-700',
    purple: 'border-purple-100 bg-purple-50 text-purple-700',
    amber:  'border-amber-100  bg-amber-50  text-amber-700',
  };
  return (
    <div className={`border rounded-xl p-4 ${colors[color]}`}>
      <div className="text-xs font-semibold uppercase tracking-wide opacity-70 mb-1">{label}</div>
      <div className="text-2xl font-bold">{value}</div>
      {sub && <div className="text-xs opacity-60 mt-0.5">{sub}</div>}
    </div>
  );
}

function SavingsBar({ model, savings, maxSavings }) {
  const pct = maxSavings > 0 ? (savings / maxSavings) * 100 : 0;
  return (
    <div className="flex items-center gap-3 text-sm">
      <span className="font-mono w-44 truncate text-gray-700" title={model}>{model}</span>
      <div className="flex-1 bg-gray-100 rounded-full h-2">
        <div className="bg-indigo-500 h-2 rounded-full transition-all" style={{ width: `${pct}%` }} />
      </div>
      <span className="text-gray-600 w-20 text-right">{fmtBig(savings)}</span>
    </div>
  );
}

function TimeSeries({ data }) {
  if (!data || data.length === 0) return <div className="text-gray-400 text-sm py-4">No data yet</div>;
  const maxSav = Math.max(...data.map(d => d.savings_usd), 0.001);
  return (
    <div className="flex items-end gap-1 h-20 w-full">
      {data.slice(-30).map((d, i) => {
        const h = (d.savings_usd / maxSav) * 100;
        const dt = new Date(d.timestamp * 1000).toLocaleDateString('en', { month: 'short', day: 'numeric' });
        return (
          <div key={i} className="flex-1 flex flex-col items-center group relative">
            <div
              className="w-full bg-indigo-400 rounded-sm hover:bg-indigo-600 transition-colors cursor-pointer"
              style={{ height: `${Math.max(2, h)}%` }}
              title={`${dt}: $${d.savings_usd}`}
            />
          </div>
        );
      })}
    </div>
  );
}

export default function ObservabilityPage() {
  const [period, setPeriod] = useState('month');
  const [savings, setSavings] = useState(null);
  const [usage, setUsage]     = useState(null);
  const [loading, setLoading] = useState(true);

  const load = async (p) => {
    setLoading(true);
    try {
      const [sv, us] = await Promise.all([
        getSavings(p),
        getUsage(p),
      ]);
      setSavings(sv.data);
      setUsage(us.data);
    } catch (e) {
      console.error(e);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { load(period); }, [period]);

  const s = savings?.summary || {};
  const ts = savings?.time_series || [];
  const byModel = usage?.by_model || {};
  const topModels = Object.entries(byModel)
    .sort((a, b) => b[1].savings_usd - a[1].savings_usd);
  const maxSav = topModels.length > 0 ? topModels[0][1].savings_usd : 0;

  return (
    <div className="p-6 max-w-5xl">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">💰 Cost Insights</h1>
          <p className="text-sm text-gray-500 mt-0.5">Local inference savings vs cloud APIs</p>
        </div>
        <div className="flex gap-2">
          {['day', 'week', 'month'].map(p => (
            <button
              key={p}
              onClick={() => setPeriod(p)}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                period === p ? 'bg-indigo-600 text-white' : 'bg-gray-100 text-gray-600 hover:bg-gray-200'
              }`}
            >
              {p.charAt(0).toUpperCase() + p.slice(1)}
            </button>
          ))}
        </div>
      </div>

      {loading ? (
        <div className="text-center py-12 text-gray-400">Loading cost data…</div>
      ) : (
        <>
          {/* Stat cards */}
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
            <StatCard
              label="Savings vs Cloud"
              value={fmtBig(s.total_savings_usd)}
              sub={`${period}`}
              color="green"
            />
            <StatCard
              label="Infra Cost"
              value={fmtBig(s.total_infra_cost_usd)}
              sub="Electricity + hardware"
              color="amber"
            />
            <StatCard
              label="Total Requests"
              value={s.total_requests?.toLocaleString() || '0'}
              sub={`${period}`}
              color="indigo"
            />
            <StatCard
              label="Total Tokens"
              value={s.total_tokens ? (s.total_tokens / 1000).toFixed(1) + 'K' : '0'}
              sub="Input + output"
              color="purple"
            />
          </div>

          {/* Savings over time */}
          <div className="bg-white border rounded-xl p-5 mb-5">
            <div className="text-sm font-semibold text-gray-700 mb-3">
              📈 Savings Over Time ({period})
            </div>
            <TimeSeries data={ts} />
            <div className="flex justify-between text-xs text-gray-400 mt-1">
              <span>Older</span>
              <span>Today</span>
            </div>
          </div>

          {/* By model breakdown */}
          <div className="bg-white border rounded-xl p-5 mb-5">
            <div className="text-sm font-semibold text-gray-700 mb-3">
              🤖 Savings by Model ({period})
            </div>
            {topModels.length === 0 ? (
              <div className="text-gray-400 text-sm py-2">No usage data yet. Run some tasks to see savings here.</div>
            ) : (
              <div className="space-y-2">
                {topModels.map(([model, stats]) => (
                  <SavingsBar
                    key={model}
                    model={model}
                    savings={stats.savings_usd}
                    maxSavings={maxSav}
                  />
                ))}
              </div>
            )}
          </div>

          {/* Summary banner */}
          {s.total_savings_usd > 0 && (
            <div className="bg-green-50 border border-green-200 rounded-xl p-4 text-sm text-green-800">
              🎉 You've saved <strong>{fmtBig(s.total_savings_usd)}</strong> this {period} by running models locally
              instead of using cloud APIs. Commercial equivalent would have cost{' '}
              <strong>{fmtBig(s.total_commercial_eq_usd)}</strong> — you paid{' '}
              <strong>{fmtBig(s.total_infra_cost_usd)}</strong> in electricity and hardware amortisation.
            </div>
          )}

          {s.total_requests === 0 && (
            <div className="bg-blue-50 border border-blue-200 rounded-xl p-4 text-sm text-blue-700">
              ℹ️ No requests recorded yet for this period. Savings will appear here as you use the platform.
              Make sure <code className="font-mono">LANGFUSE_PUBLIC_KEY</code> and{' '}
              <code className="font-mono">LANGFUSE_SECRET_KEY</code> are configured for full observability.
            </div>
          )}
        </>
      )}
    </div>
  );
}
