import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStats, getActivity, healthCheck } from '../api';
import { BookOpen, MessageSquare, Upload, Activity, ArrowRight, Clock, Layers, Key, BarChart3, Box, CheckCircle, XCircle } from 'lucide-react';

function StatCard({ icon: Icon, label, value, color, onClick, delay }) {
  return (
    <button onClick={onClick} className={`border border-white/10 bg-[#141414] p-4 text-left hover:border-white/20 transition-all group ${delay}`} data-testid={`stat-${label.toLowerCase().replace(/\s/g, '-')}`}>
      <div className="flex items-center justify-between mb-2">
        <Icon size={14} style={{ color }} />
        <ArrowRight size={10} className="text-[#737373] opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
      <div className="text-2xl font-bold tracking-tight" style={{ fontFamily: 'Chivo, sans-serif' }}>{value}</div>
      <div className="text-[9px] tracking-[0.2em] uppercase text-[#737373] mt-0.5 font-mono">{label}</div>
    </button>
  );
}

export default function DashboardHome() {
  const nav = useNavigate();
  const [stats, setStats] = useState(null);
  const [activity, setActivity] = useState([]);
  const [health, setHealth] = useState(null);

  useEffect(() => {
    getStats().then(r => setStats(r.data)).catch(() => {});
    getActivity(8).then(r => setActivity(r.data.logs || [])).catch(() => {});
    healthCheck().then(r => setHealth(r.data)).catch(() => {});
  }, []);

  return (
    <div className="p-5 lg:p-7 max-w-7xl" data-testid="dashboard-home">
      <div className="mb-6 animate-fade-in">
        <div className="flex items-center gap-2 text-[9px] tracking-[0.25em] uppercase text-[#737373] mb-1.5 font-mono">
          <div className={`w-1.5 h-1.5 rounded-full ${health?.status === 'ok' ? 'bg-green-500' : 'bg-amber-500'}`} />
          {health?.status === 'ok' ? 'ALL SYSTEMS OPERATIONAL' : 'CHECKING STATUS...'}
        </div>
        <h1 className="text-2xl font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>Control Room</h1>
        <p className="text-xs text-[#737373] mt-0.5">Unified AI Agent Platform — Self-Hosted</p>
      </div>

      {/* Health Badges */}
      <div className="flex flex-wrap gap-2 mb-5">
        {[
          { label: 'MongoDB', ok: health?.mongo },
          { label: 'Ollama', ok: health?.ollama },
          { label: 'Langfuse', ok: stats?.langfuse_configured },
        ].map(svc => (
          <div key={svc.label} className="flex items-center gap-1.5 border border-white/10 bg-[#141414] px-3 py-1.5 text-[10px] font-mono">
            {svc.ok ? <CheckCircle size={11} className="text-green-500" /> : <XCircle size={11} className="text-[#737373]" />}
            <span className="text-[#A0A0A0]">{svc.label}</span>
          </div>
        ))}
        {stats?.ngrok_domain && (
          <div className="flex items-center gap-1.5 border border-[#002FA7]/30 bg-[#002FA7]/10 px-3 py-1.5 text-[10px] font-mono">
            <span className="text-[#002FA7]">{stats.ngrok_domain}</span>
          </div>
        )}
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-3 mb-6">
        <StatCard icon={BookOpen} label="Wiki Pages" value={stats?.wiki_pages ?? '—'} color="#002FA7" onClick={() => nav('/wiki')} delay="stagger-1" />
        <StatCard icon={MessageSquare} label="Sessions" value={stats?.chat_sessions ?? '—'} color="#A855F7" onClick={() => nav('/chat')} delay="stagger-2" />
        <StatCard icon={Upload} label="Sources" value={stats?.sources ?? '—'} color="#22C55E" onClick={() => nav('/sources')} delay="stagger-3" />
        <StatCard icon={Layers} label="Providers" value={stats?.providers ?? '—'} color="#F59E0B" onClick={() => nav('/providers')} delay="stagger-4" />
        <StatCard icon={Key} label="API Keys" value={stats?.api_keys ?? '—'} color="#EC4899" onClick={() => nav('/keys')} delay="stagger-5" />
        <StatCard icon={Activity} label="Events" value={stats?.activity_entries ?? '—'} color="#06B6D4" onClick={() => nav('/activity')} delay="stagger-5" />
      </div>

      <div className="grid lg:grid-cols-3 gap-3">
        {/* Recent Pages */}
        <div className="border border-white/10 bg-[#141414]">
          <div className="px-4 py-2.5 border-b border-white/10 flex items-center justify-between">
            <span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">Recent Pages</span>
            <button onClick={() => nav('/wiki')} className="text-[9px] text-[#002FA7] hover:underline font-mono">ALL</button>
          </div>
          <div className="divide-y divide-white/5">
            {stats?.recent_pages?.length > 0 ? stats.recent_pages.map(p => (
              <button key={p.slug} onClick={() => nav(`/wiki/${p.slug}`)} className="w-full flex items-center gap-2 px-4 py-2.5 text-left hover:bg-white/[0.02] transition-colors">
                <BookOpen size={12} className="text-[#002FA7] shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] text-white truncate">{p.title}</div>
                  <div className="text-[9px] text-[#737373]">{p.updated_at?.split('T')[0]}</div>
                </div>
              </button>
            )) : <div className="px-4 py-6 text-center text-[11px] text-[#737373]">No wiki pages yet</div>}
          </div>
        </div>

        {/* Activity Feed */}
        <div className="lg:col-span-2 border border-white/10 bg-[#141414]">
          <div className="px-4 py-2.5 border-b border-white/10 flex items-center justify-between">
            <span className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">Activity Feed</span>
            <button onClick={() => nav('/activity')} className="text-[9px] text-[#002FA7] hover:underline font-mono">ALL</button>
          </div>
          <div className="divide-y divide-white/5 max-h-72 overflow-y-auto">
            {activity.length > 0 ? activity.map(a => (
              <div key={a._id} className="flex items-start gap-2 px-4 py-2.5">
                <div className={`mt-0.5 w-1.5 h-1.5 shrink-0 ${
                  a.category === 'chat' ? 'bg-purple-500' : a.category === 'wiki' ? 'bg-[#002FA7]' :
                  a.category === 'ingest' ? 'bg-green-500' : a.category === 'provider' ? 'bg-amber-500' :
                  a.category === 'keys' ? 'bg-pink-500' : 'bg-[#737373]'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="text-[11px] text-[#A0A0A0] truncate">{a.message}</div>
                  <div className="text-[9px] text-[#737373] mt-0.5 flex items-center gap-1.5"><Clock size={9} />{a.created_at?.replace('T', ' ').split('.')[0]}</div>
                </div>
                <span className="text-[9px] tracking-wider uppercase text-[#737373] font-mono shrink-0">{a.category}</span>
              </div>
            )) : <div className="px-4 py-6 text-center text-[11px] text-[#737373]">No activity yet</div>}
          </div>
        </div>
      </div>

      {/* Provider Info */}
      <div className="mt-3 border border-white/10 bg-[#141414] px-4 py-2.5 flex items-center gap-3">
        <Layers size={13} className="text-[#002FA7]" />
        <span className="text-[11px] text-[#A0A0A0] font-mono">Active Provider: <span className="text-white">{stats?.llm_provider || '—'}</span></span>
      </div>
    </div>
  );
}
