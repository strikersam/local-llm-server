import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStats, getActivity, healthCheck } from '../api';
import {
  BookOpen, MessageSquare, Upload, Activity, ArrowUpRight, Clock,
  Layers, Key, BarChart3, Box, CheckCircle, AlertCircle
} from 'lucide-react';

const categoryDot = {
  chat: 'var(--role-power-user)',
  wiki: 'var(--accent)',
  ingest: 'var(--success)',
  provider: 'var(--warning)',
  keys: 'var(--info)',
};

function StatCard({ icon: Icon, label, value, accent, onClick, delay }) {
  return (
    <button
      onClick={onClick}
      className={`group relative flex flex-col items-start gap-3 transition-all duration-200 hover:-translate-y-[2px] hover:shadow-[0_8px_24px_rgba(0,0,0,0.4)] ${delay}`}
      data-testid={`stat-${label.toLowerCase().replace(/\s/g, '-')}`}
      style={{
        background: 'var(--bg-surface)',
        border: '1px solid var(--border)',
        borderRadius: 'var(--radius-lg)',
        padding: '1.5rem',
        transition: 'all 0.3s ease, border-color 0.3s ease, background-color 0.3s ease'
      }}
      onMouseEnter={e => { 
        e.currentTarget.style.borderColor = 'var(--border-strong)'; 
        e.currentTarget.style.background = 'var(--bg-elevated)'; 
      }}
      onMouseLeave={e => { 
        e.currentTarget.style.borderColor = 'var(--border)'; 
        e.currentTarget.style.background = 'var(--bg-surface)'; 
      }}
    >
      <div className="flex items-start justify-between mb-3">
        <div className="flex-shrink-0">
          <div className="w-9 h-9 rounded-xl flex items-center justify-center" 
            style={{ background: `${accent}10`, border: `1px solid ${accent}20` }}>
            <Icon size={16} style={{ color: accent }} />
          </div>
        </div>
        <div className="ml-auto">
          <ArrowUpRight size={12} className="text-[var(--text-tertiary)] opacity-0 group-hover:opacity-100 transition-opacity duration-200" />
        </div>
      </div>
      <div
        className="text-[1.75rem] font-bold tracking-tight text-white leading-none mb-1"
        style={{ fontFamily: 'var(--font-main)' }}
      >
        {value}
      </div>
      <div className="text-[0.95rem] font-medium" style={{ color: 'var(--text-secondary)' }}>{label}</div>
    </button>
  );
}

function HealthBadge({ label, ok }) {
  return (
    <div className={`inline-flex items-center gap-2 px-2.5 py-1 rounded-full text-[0.85rem] font-medium transition-colors ${
      ok
        ? 'border-[var(--success)]/20 bg-[var(--success)]/10 text-[var(--success)]'
        : 'border-[var(--border)]/20 bg-[var(--border)]/10 text-[var(--text-tertiary)]'
    }`}>
      {ok
        ? <CheckCircle size={10} />
        : <AlertCircle size={10} />
      }
      <span>{label}</span>
    </div>
  );
}

export default function DashboardHome() {
  const [stats, setStats] = useState(null);
  const [activity, setActivity] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  useEffect(() => {
    const loadData = async () => {
      setLoading(true);
      setError(null);
      try {
        const [statsRes, activityRes, healthRes] = await Promise.all([
          getStats(),
          getActivity(),
          healthCheck()
        ]);
        setStats(statsRes.data);
        setActivity(activityRes.data);
        // Health data could be used for a health indicator if needed
      } catch (err) {
        setError(err?.response?.data?.detail || 'Failed to load dashboard data');
        console.error('Dashboard load error:', err);
      } finally {
        setLoading(false);
      }
    };

    loadData();
    const interval = setInterval(loadData, 15000); // Refresh every 15 seconds
    return () => clearInterval(interval);
  }, []);

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex min-h-[20vh] items-center justify-center">
          <div className="text-center space-y-4">
            <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: 'var(--accent)' }} />
            <p className="text-[0.95rem] text-[var(--text-muted)]">Loading dashboard...</p>
          </div>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-6">
        <div className="bg-[var(--danger)]/10 border border-[var(--danger)]/20 rounded-xl p-5">
          <AlertCircle size={16} className="mb-3 text-[var(--danger)]" />
          <p className="text-[0.9rem] text-[var(--text-primary)]">Error: {error}</p>
          <button onClick={() => window.location.reload()} 
            className="mt-4 inline-flex items-center gap-2 px-4 py-2 bg-[var(--accent)]/10 text-[var(--accent)] hover:bg-[var(--accent)]/20 rounded-lg font-medium transition-colors">
            Refresh <ArrowUpRight size={12} />
          </button>
        </div>
      </div>
    );
  }

  return (
    <div className="p-6">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[1.5rem] font-bold tracking-tight text-[var(--text-primary)]"
            style={{ fontFamily: 'var(--font-main)' }}>Dashboard</h1>
          <p className="text-[0.9rem] text-[var(--text-tertiary)]">Overview of your LLM Relay system</p>
        </div>
        <div className="flex items-center gap-3">
          <HealthBadge label="API" ok={Boolean(stats?.llm_provider)} />
          <HealthBadge label="DB" ok={stats?.total_agents !== undefined} />
        </div>
      </div>

      {/* Stats Cards */}
      <div className="grid gap-4 mb-6"
        style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))' }}>
        <StatCard 
          icon={Activity} 
          label="Total Agents" 
          value={stats?.total_agents ?? 0} 
          accent="var(--accent)" 
          onClick={() => nav('/agents')} 
        />
        <StatCard 
          icon={MessageSquare} 
          label="Active Chats" 
          value={stats?.active_sessions ?? 0} 
          accent="var(--role-power-user)" 
          onClick={() => nav('/chat')} 
        />
        <StatCard 
          icon={Upload} 
          label="Knowledge Items" 
          value={stats?.wiki_pages ?? 0} 
          accent="var(--success)" 
          onClick={() => nav('/knowledge')} 
        />
        <StatCard 
          icon={Key} 
          label="API Keys" 
          value={stats?.api_keys ?? 0} 
          accent="var(--warning)" 
          onClick={() => nav('/admin')} 
        />
      </div>

      {/* Activity Feed */}
      <div className="space-y-4">
        <div className="flex items-center justify-between mb-3">
          <h2 className="text-[1.15rem] font-semibold text-[var(--text-primary)]">
            Recent Activity
          </h2>
          <button onClick={() => nav('/activity')} 
            className="text-[0.9rem] font-medium text-[var(--accent)] hover:text-[var(--accent-hover)]">
            View all <ArrowUpRight size={10} />
          </button>
        </div>
        <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl overflow-hidden">
          <div className="divide-y divide-[var(--border)] max-h-[80vh] overflow-y-auto">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 px-4 py-3">
                  <div className="skeleton w-3 h-3 rounded-full shrink-0" />
                  <div className="flex-1">
                    <div className="skeleton h-2 w-3/4 mb-1.5" />
                    <div className="skeleton h-1.5 w-1/3" />
                  </div>
                </div>
              ))
            ) : activity.length > 0 ? activity.map(a => (
              <div key={a._id} className="flex items-start gap-3 px-4 py-3">
                <div className={`mt-0.5 w-2.5 h-2.5 rounded-full shrink-0 ${categoryDot[a.category] || 'var(--text-tertiary)'}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-[0.9rem] text-[var(--text-secondary)] truncate">{a.message}</div>
                  <div className="text-[0.8rem] font-mono mt-0.5 flex items-center gap-1">
                    <Clock size={8} className="text-[var(--text-muted)]" />
                    <span className="ml-1">{a.created_at?.replace('T', ' ').split('.')[0] || ''}</span>
                  </div>
                </div>
                <span className="text-[0.8rem] font-mono text-[var(--text-tertiary)] uppercase tracking-wide shrink-0 mt-0.5">{a.category}</span>
              </div>
            )) : (
              <div className="px-6 py-10 text-center">
                <Activity size={18} className="text-[var(--text-tertiary)] mx-auto mb-3" />
                <p className="text-[0.9rem] text-[var(--text-tertiary)]">No activity recorded yet</p>
                <p className="text-[0.85rem] font-mono text-[var(--text-muted)] mt-2">
                  Activity will appear here as agents perform tasks
                </p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Quick Status */}
      <div className="mt-6 pt-5 border-t border-[var(--border)]">
        <div className="grid gap-3"
          style={{ gridTemplateColumns: 'repeat(auto-fit, minmax(160px, 1fr))' }}>
          <div className="flex flex-col items-center">
            <Layers size={18} className="mb-2 text-[var(--accent)]" />
            <div className="text-[0.85rem] font-medium text-[var(--text-primary)]">Active Provider</div>
            <div className="text-[0.8rem] font-mono text-[var(--text-secondary)]">{stats?.llm_provider || '—'}</div>
          </div>
          <div className="flex flex-col items-center">
            <BarChart3 size={18} className="mb-2 text-[var(--success)]" />
            <div className="text-[0.85rem] font-medium text-[var(--text-primary)]">Total Requests</div>
            <div className="text-[0.8rem] font-mono text-[var(--text-secondary)]">{stats?.total_requests ?? 0}</div>
          </div>
          <div className="flex flex-col items-center">
            <CheckCircle size={18} className="mb-2 text-[var(--warning)]" />
            <div className="text-[0.85rem] font-medium text-[var(--text-primary)]">Success Rate</div>
            <div className="text-[0.8rem] font-mono text-[var(--text-secondary)]">
              {stats?.success_rate !== undefined ? `${(stats?.success_rate * 100).toFixed(1)}%` : '—'}
            </div>
          </div>
          <div className="flex flex-col items-center">
            <Clock size={18} className="mb-2 text-[var(--info)]" />
            <div className="text-[0.85rem] font-medium text-[var(--text-primary)]">Avg Response Time</div>
            <div className="text-[0.8rem] font-mono text-[var(--text-secondary)]">
              {stats?.avg_response_time !== undefined ? `${stats?.avg_response_time.toFixed(1)}s` : '—'}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
