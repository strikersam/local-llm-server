import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getStats, getActivity } from '../api';
import { BookOpen, MessageSquare, Upload, Activity, ArrowRight, Clock, Cpu } from 'lucide-react';

function StatCard({ icon: Icon, label, value, color, delay, onClick }) {
  return (
    <button
      onClick={onClick}
      className={`border border-white/10 bg-[#141414] p-5 text-left hover:border-white/20 transition-all group ${delay}`}
      data-testid={`stat-${label.toLowerCase().replace(/\s/g, '-')}`}
    >
      <div className="flex items-center justify-between mb-3">
        <Icon size={16} style={{ color }} />
        <ArrowRight size={12} className="text-[#737373] opacity-0 group-hover:opacity-100 transition-opacity" />
      </div>
      <div className="text-3xl font-bold tracking-tight" style={{ fontFamily: 'Chivo, sans-serif' }}>{value}</div>
      <div className="text-[10px] tracking-[0.2em] uppercase text-[#737373] mt-1 font-mono">{label}</div>
    </button>
  );
}

export default function DashboardHome() {
  const navigate = useNavigate();
  const [stats, setStats] = useState(null);
  const [activity, setActivity] = useState([]);

  useEffect(() => {
    getStats().then(r => setStats(r.data)).catch(() => {});
    getActivity(10).then(r => setActivity(r.data.logs || [])).catch(() => {});
  }, []);

  return (
    <div className="p-6 lg:p-8 max-w-7xl" data-testid="dashboard-home">
      {/* Header */}
      <div className="mb-8 animate-fade-in">
        <div className="flex items-center gap-2 text-[10px] tracking-[0.25em] uppercase text-[#737373] mb-2 font-mono">
          <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
          SYSTEM ONLINE
        </div>
        <h1 className="text-3xl font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>
          Control Room
        </h1>
        <p className="text-sm text-[#737373] mt-1">LLM Wiki Agent Dashboard — Overview</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        <StatCard icon={BookOpen} label="Wiki Pages" value={stats?.wiki_pages ?? '—'} color="#002FA7" delay="stagger-1" onClick={() => navigate('/wiki')} />
        <StatCard icon={MessageSquare} label="Chat Sessions" value={stats?.chat_sessions ?? '—'} color="#A855F7" delay="stagger-2" onClick={() => navigate('/chat')} />
        <StatCard icon={Upload} label="Sources" value={stats?.sources ?? '—'} color="#22C55E" delay="stagger-3" onClick={() => navigate('/sources')} />
        <StatCard icon={Activity} label="Activity Entries" value={stats?.activity_entries ?? '—'} color="#F59E0B" delay="stagger-4" onClick={() => navigate('/activity')} />
      </div>

      <div className="grid lg:grid-cols-3 gap-4">
        {/* Recent Wiki Pages */}
        <div className="lg:col-span-1 border border-white/10 bg-[#141414] stagger-4">
          <div className="px-5 py-3 border-b border-white/10 flex items-center justify-between">
            <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">Recent Pages</span>
            <button onClick={() => navigate('/wiki')} className="text-[10px] text-[#002FA7] hover:underline font-mono">VIEW ALL</button>
          </div>
          <div className="divide-y divide-white/5">
            {stats?.recent_pages?.length > 0 ? stats.recent_pages.map((p, i) => (
              <button
                key={p.slug}
                onClick={() => navigate(`/wiki/${p.slug}`)}
                className="w-full flex items-center gap-3 px-5 py-3 text-left hover:bg-white/[0.02] transition-colors"
              >
                <BookOpen size={13} className="text-[#002FA7] shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-white truncate">{p.title}</div>
                  <div className="text-[10px] text-[#737373]">{p.updated_at?.split('T')[0]}</div>
                </div>
              </button>
            )) : (
              <div className="px-5 py-8 text-center text-xs text-[#737373]">No wiki pages yet</div>
            )}
          </div>
        </div>

        {/* Activity Feed */}
        <div className="lg:col-span-2 border border-white/10 bg-[#141414] stagger-5">
          <div className="px-5 py-3 border-b border-white/10 flex items-center justify-between">
            <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">Activity Feed</span>
            <button onClick={() => navigate('/activity')} className="text-[10px] text-[#002FA7] hover:underline font-mono">VIEW ALL</button>
          </div>
          <div className="divide-y divide-white/5 max-h-80 overflow-y-auto">
            {activity.length > 0 ? activity.map((a, i) => (
              <div key={a._id} className="flex items-start gap-3 px-5 py-3">
                <div className={`mt-0.5 w-1.5 h-1.5 shrink-0 ${
                  a.category === 'chat' ? 'bg-purple-500' :
                  a.category === 'wiki' ? 'bg-[#002FA7]' :
                  a.category === 'ingest' ? 'bg-green-500' :
                  a.category === 'auth' ? 'bg-amber-500' : 'bg-[#737373]'
                }`} />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-[#A0A0A0] truncate">{a.message}</div>
                  <div className="text-[10px] text-[#737373] mt-0.5 flex items-center gap-2">
                    <Clock size={10} />
                    {a.created_at?.replace('T', ' ').split('.')[0]}
                  </div>
                </div>
                <span className="text-[10px] tracking-wider uppercase text-[#737373] font-mono shrink-0">{a.category}</span>
              </div>
            )) : (
              <div className="px-5 py-8 text-center text-xs text-[#737373]">No activity yet</div>
            )}
          </div>
        </div>
      </div>

      {/* Provider Info */}
      <div className="mt-4 border border-white/10 bg-[#141414] px-5 py-3 flex items-center gap-3 stagger-5">
        <Cpu size={14} className="text-[#002FA7]" />
        <span className="text-xs text-[#A0A0A0] font-mono">
          LLM Provider: <span className="text-white">{stats?.llm_provider?.toUpperCase() || '—'}</span>
        </span>
      </div>
    </div>
  );
}
