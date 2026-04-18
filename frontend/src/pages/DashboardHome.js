import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStats, getActivity, healthCheck } from '../api';
import {
  BookOpen, MessageSquare, Upload, Activity, ArrowUpRight, Clock,
  Layers, Key, BarChart3, Box, CheckCircle, AlertCircle
} from 'lucide-react';

const categoryDot = {
  chat: 'bg-purple-500',
  wiki: 'bg-[#002FA7]',
  ingest: 'bg-emerald-500',
  provider: 'bg-amber-500',
  keys: 'bg-pink-500',
};

function StatCard({ icon: Icon, label, value, accent, onClick, delay }) {
  return (
    <button
      onClick={onClick}
      className={`group relative bg-[#111111] border border-white/8 rounded-xl p-5 text-left hover:border-white/16 hover:bg-[#141414] transition-all duration-200 hover:shadow-[0_8px_24px_rgba(0,0,0,0.4)] ${delay}`}
      data-testid={`stat-${label.toLowerCase().replace(/\s/g, '-')}`}
    >
      <div className="flex items-start justify-between mb-4">
        <div className="w-9 h-9 rounded-lg flex items-center justify-center" style={{ background: `${accent}15`, border: `1px solid ${accent}25` }}>
          <Icon size={16} style={{ color: accent }} />
        </div>
        <ArrowUpRight size={14} className="text-[#333333] opacity-0 group-hover:opacity-100 transition-opacity -translate-x-1 group-hover:translate-x-0 duration-200" />
      </div>
      <div
        className="text-[28px] font-bold tracking-tight text-white leading-none mb-1"
        style={{ fontFamily: 'Outfit, sans-serif' }}
      >
        {value}
      </div>
      <div className="text-[11px] text-[#555555] font-medium">{label}</div>
    </button>
  );
}

function HealthBadge({ label, ok }) {
  return (
    <div className={`inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] font-medium border transition-colors ${
      ok
        ? 'border-emerald-500/20 bg-emerald-500/8 text-emerald-400'
        : 'border-white/8 bg-white/4 text-[#555555]'
    }`}>
      {ok
        ? <CheckCircle size={11} />
        : <AlertCircle size={11} />
      }
      {label}
    </div>
  );
}

export default function DashboardHome() {
  const nav = useNavigate();
  const [stats, setStats] = useState(null);
  const [activity, setActivity] = useState([]);
  const [health, setHealth] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      getStats().then(r => setStats(r.data)),
      getActivity(10).then(r => setActivity(r.data.logs || [])),
      healthCheck().then(r => setHealth(r.data)),
    ]).finally(() => setLoading(false));
  }, []);

  const isHealthy = health?.status === 'ok';

  return (
    <div className="p-5 sm:p-6 lg:p-8 max-w-7xl mx-auto" data-testid="dashboard-home">

      {/* Header */}
      <div className="mb-7 animate-fade-in">
        <div className="flex items-center gap-2 mb-2">
          <div className={`w-2 h-2 rounded-full transition-colors ${isHealthy ? 'bg-emerald-500' : 'bg-amber-500'} ${!loading ? 'animate-none' : 'animate-pulse-slow'}`} />
          <span className="text-[11px] font-mono tracking-[0.2em] uppercase text-[#444444]">
            {loading ? 'Checking status...' : isHealthy ? 'All systems operational' : 'Partial outage'}
          </span>
        </div>
        <h1
          className="text-3xl sm:text-4xl font-bold tracking-[-0.03em] text-white"
          style={{ fontFamily: 'Outfit, sans-serif' }}
        >
          Control Room
        </h1>
        <p className="text-sm text-[#555555] mt-1">LLM Relay — Unified AI Platform</p>
      </div>

      {/* Health badges */}
      <div className="flex flex-wrap gap-2 mb-7 stagger-1">
        <HealthBadge label="MongoDB" ok={health?.mongo} />
        <HealthBadge label="Ollama" ok={health?.ollama} />
        <HealthBadge label="Langfuse" ok={stats?.langfuse_configured} />
        {stats?.ngrok_domain && (
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-full text-[11px] font-mono border border-[#002FA7]/20 bg-[#002FA7]/8 text-[#4477FF]">
            {stats.ngrok_domain}
          </div>
        )}
      </div>

      {/* Stats grid */}
      <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-3 mb-7">
        <StatCard icon={BookOpen}    label="Wiki Pages" value={loading ? '—' : (stats?.wiki_pages ?? 0)}         accent="#3B82F6" onClick={() => nav('/wiki')}         delay="stagger-1" />
        <StatCard icon={MessageSquare} label="Sessions"  value={loading ? '—' : (stats?.chat_sessions ?? 0)}    accent="#A855F7" onClick={() => nav('/chat')}         delay="stagger-2" />
        <StatCard icon={Upload}      label="Sources"    value={loading ? '—' : (stats?.sources ?? 0)}            accent="#10B981" onClick={() => nav('/sources')}      delay="stagger-3" />
        <StatCard icon={Layers}      label="Providers"  value={loading ? '—' : (stats?.providers ?? 0)}          accent="#F59E0B" onClick={() => nav('/providers')}    delay="stagger-4" />
        <StatCard icon={Key}         label="API Keys"   value={loading ? '—' : (stats?.api_keys ?? 0)}           accent="#EC4899" onClick={() => nav('/admin')}        delay="stagger-5" />
        <StatCard icon={Activity}    label="Events"     value={loading ? '—' : (stats?.activity_entries ?? 0)}   accent="#06B6D4" onClick={() => nav('/activity')}     delay="stagger-6" />
      </div>

      {/* Content grid */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">

        {/* Recent Wiki Pages */}
        <div className="bg-[#111111] border border-white/8 rounded-xl overflow-hidden stagger-4">
          <div className="px-5 py-3.5 border-b border-white/6 flex items-center justify-between">
            <span className="text-[12px] font-semibold text-[#888888] tracking-wide">Recent Pages</span>
            <button onClick={() => nav('/wiki')} className="text-[11px] text-[#002FA7] hover:text-[#4477FF] transition-colors font-medium">
              View all
            </button>
          </div>
          <div className="divide-y divide-white/4">
            {loading ? (
              Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="px-5 py-3.5">
                  <div className="skeleton h-3 w-3/4 mb-2" />
                  <div className="skeleton h-2.5 w-1/3" />
                </div>
              ))
            ) : stats?.recent_pages?.length > 0 ? stats.recent_pages.map(p => (
              <button
                key={p.slug}
                onClick={() => nav(`/wiki/${p.slug}`)}
                className="w-full flex items-center gap-3 px-5 py-3.5 text-left hover:bg-white/[0.025] transition-colors group"
              >
                <div className="w-7 h-7 rounded-md bg-[#002FA7]/10 border border-[#002FA7]/15 flex items-center justify-center shrink-0">
                  <BookOpen size={12} className="text-[#4477FF]" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] text-[#CCCCCC] group-hover:text-white truncate transition-colors">{p.title}</div>
                  <div className="text-[10px] text-[#444444] mt-0.5">{p.updated_at?.split('T')[0]}</div>
                </div>
              </button>
            )) : (
              <div className="px-5 py-10 text-center">
                <BookOpen size={20} className="text-[#333333] mx-auto mb-2" />
                <p className="text-[12px] text-[#444444]">No wiki pages yet</p>
                <button onClick={() => nav('/wiki')} className="text-[11px] text-[#002FA7] hover:underline mt-1">Create one</button>
              </div>
            )}
          </div>
        </div>

        {/* Activity Feed */}
        <div className="lg:col-span-2 bg-[#111111] border border-white/8 rounded-xl overflow-hidden stagger-5">
          <div className="px-5 py-3.5 border-b border-white/6 flex items-center justify-between">
            <span className="text-[12px] font-semibold text-[#888888] tracking-wide">Recent Activity</span>
            <button onClick={() => nav('/activity')} className="text-[11px] text-[#002FA7] hover:text-[#4477FF] transition-colors font-medium">
              View all
            </button>
          </div>
          <div className="divide-y divide-white/4 max-h-80 overflow-y-auto">
            {loading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="flex items-center gap-3 px-5 py-3.5">
                  <div className="skeleton w-2 h-2 rounded-full shrink-0" />
                  <div className="flex-1">
                    <div className="skeleton h-3 w-4/5 mb-1.5" />
                    <div className="skeleton h-2.5 w-1/4" />
                  </div>
                </div>
              ))
            ) : activity.length > 0 ? activity.map(a => (
              <div key={a._id} className="flex items-start gap-3 px-5 py-3.5">
                <div className={`mt-1.5 w-2 h-2 rounded-full shrink-0 ${categoryDot[a.category] || 'bg-[#333333]'}`} />
                <div className="flex-1 min-w-0">
                  <div className="text-[13px] text-[#A0A0A0] truncate">{a.message}</div>
                  <div className="text-[10px] text-[#444444] mt-0.5 flex items-center gap-1.5 font-mono">
                    <Clock size={9} />
                    {a.created_at?.replace('T', ' ').split('.')[0]}
                  </div>
                </div>
                <span className="text-[10px] text-[#444444] font-mono uppercase tracking-wide shrink-0 mt-0.5">{a.category}</span>
              </div>
            )) : (
              <div className="px-5 py-10 text-center">
                <Activity size={20} className="text-[#333333] mx-auto mb-2" />
                <p className="text-[12px] text-[#444444]">No activity recorded yet</p>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Active provider bar */}
      <div className="mt-4 bg-[#111111] border border-white/8 rounded-xl px-5 py-3 flex flex-wrap items-center gap-3 stagger-6">
        <div className="w-7 h-7 rounded-md bg-amber-500/10 border border-amber-500/15 flex items-center justify-center">
          <Layers size={13} className="text-amber-400" />
        </div>
        <div className="flex-1 min-w-0">
          <span className="text-[12px] text-[#666666]">Active provider: </span>
          <span className="text-[12px] text-[#CCCCCC] font-medium">{stats?.llm_provider || '—'}</span>
        </div>
        <button onClick={() => nav('/providers')} className="text-[11px] text-[#002FA7] hover:text-[#4477FF] transition-colors font-medium flex items-center gap-1">
          Manage <ArrowUpRight size={11} />
        </button>
      </div>
    </div>
  );
}
