import React, { useState, useEffect } from 'react';
import { getActivity } from '../api';
import { Activity, Clock, MessageSquare, BookOpen, Upload, Shield, Filter } from 'lucide-react';

const categoryConfig = {
  chat:   { icon: MessageSquare, dot: 'bg-purple-500',  label: 'Chat'   },
  wiki:   { icon: BookOpen,      dot: 'bg-[#002FA7]',   label: 'Wiki'   },
  ingest: { icon: Upload,        dot: 'bg-emerald-500', label: 'Ingest' },
  auth:   { icon: Shield,        dot: 'bg-amber-500',   label: 'Auth'   },
  lint:   { icon: Activity,      dot: 'bg-cyan-500',    label: 'Lint'   },
};

export default function ActivityPage() {
  const [logs, setLogs] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getActivity(200)
      .then(r => setLogs(r.data.logs || []))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = filter === 'all' ? logs : logs.filter(l => l.category === filter);

  return (
    <div className="p-5 sm:p-6 lg:p-8 max-w-5xl mx-auto" data-testid="activity-page">

      {/* Header */}
      <div className="mb-6 animate-fade-in">
        <h1 className="text-3xl font-bold tracking-[-0.03em] text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>Activity Log</h1>
        <p className="text-sm text-[#555555] mt-1">Full system event trail — all operations are recorded</p>
      </div>

      {/* Filter bar */}
      <div className="flex flex-wrap items-center gap-2 mb-6 stagger-1">
        <Filter size={13} className="text-[#555555]" />
        {['all', 'chat', 'wiki', 'ingest', 'auth', 'lint', 'provider', 'keys'].map(cat => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            data-testid={`filter-${cat}`}
            className={`text-[11px] font-medium px-3 py-1.5 rounded-full border transition-all capitalize ${
              filter === cat
                ? 'border-[#002FA7]/60 text-white bg-[#002FA7]/15'
                : 'border-white/8 text-[#555555] hover:text-[#A0A0A0] hover:border-white/14'
            }`}
          >
            {cat}
          </button>
        ))}
        <span className="text-[11px] text-[#444444] font-mono ml-auto">{filtered.length} entries</span>
      </div>

      {/* Log list */}
      <div className="bg-[#111111] border border-white/8 rounded-xl overflow-hidden">
        {/* Desktop column headers */}
        <div className="hidden sm:grid sm:grid-cols-[100px_1fr_180px] gap-4 px-5 py-3 border-b border-white/6 text-[11px] font-semibold tracking-widest uppercase text-[#444444]">
          <span>Type</span>
          <span>Event</span>
          <span>Timestamp</span>
        </div>

        <div className="divide-y divide-white/4 max-h-[calc(100dvh-280px)] overflow-y-auto">
          {loading ? (
            Array.from({ length: 8 }).map((_, i) => (
              <div key={i} className="flex items-center gap-3 px-5 py-3.5">
                <div className="skeleton w-2 h-2 rounded-full" />
                <div className="flex-1 skeleton h-3" />
                <div className="hidden sm:block skeleton h-3 w-36" />
              </div>
            ))
          ) : filtered.map(entry => {
            const cfg = categoryConfig[entry.category] || { icon: Activity, dot: 'bg-[#444444]', label: entry.category };
            const Icon = cfg.icon;
            return (
              <div
                key={entry._id}
                className="flex flex-col sm:grid sm:grid-cols-[100px_1fr_180px] gap-1 sm:gap-4 px-5 py-3.5 hover:bg-white/[0.02] transition-colors sm:items-center"
                data-testid={`activity-entry-${entry._id}`}
              >
                {/* Type badge */}
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full shrink-0 ${cfg.dot}`} />
                  <span className="text-[11px] font-medium text-[#666666] capitalize">{cfg.label}</span>
                </div>
                {/* Message */}
                <div className="text-[13px] text-[#A0A0A0] truncate">{entry.message}</div>
                {/* Timestamp */}
                <div className="text-[10px] text-[#444444] font-mono flex items-center gap-1.5">
                  <Clock size={9} />
                  {entry.created_at?.replace('T', ' ').split('.')[0]}
                </div>
              </div>
            );
          })}
          {!loading && filtered.length === 0 && (
            <div className="py-12 text-center">
              <Activity size={22} className="text-[#333333] mx-auto mb-2" />
              <p className="text-sm text-[#555555]">No activity entries {filter !== 'all' ? `for "${filter}"` : ''}</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
