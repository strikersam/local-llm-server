import React, { useState, useEffect } from 'react';
import { getActivity } from '../api';
import { Activity, Clock, MessageSquare, BookOpen, Upload, Shield, Filter } from 'lucide-react';

const categoryConfig = {
  chat: { icon: MessageSquare, color: 'bg-purple-500', label: 'CHAT' },
  wiki: { icon: BookOpen, color: 'bg-[#002FA7]', label: 'WIKI' },
  ingest: { icon: Upload, color: 'bg-green-500', label: 'INGEST' },
  auth: { icon: Shield, color: 'bg-amber-500', label: 'AUTH' },
  lint: { icon: Activity, color: 'bg-cyan-500', label: 'LINT' },
};

export default function ActivityPage() {
  const [logs, setLogs] = useState([]);
  const [filter, setFilter] = useState('all');

  useEffect(() => {
    getActivity(200).then(r => setLogs(r.data.logs || [])).catch(() => {});
  }, []);

  const filtered = filter === 'all' ? logs : logs.filter(l => l.category === filter);

  return (
    <div className="p-6 lg:p-8 max-w-5xl" data-testid="activity-page">
      <div className="mb-6 animate-fade-in">
        <h1 className="text-2xl font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>Activity Log</h1>
        <p className="text-xs text-[#737373] mt-1">System event trail — all operations are recorded</p>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-2 mb-6 flex-wrap">
        <Filter size={14} className="text-[#737373]" />
        {['all', 'chat', 'wiki', 'ingest', 'auth', 'lint'].map(cat => (
          <button
            key={cat}
            onClick={() => setFilter(cat)}
            className={`text-[10px] tracking-wider uppercase font-mono px-3 py-1.5 border transition-all
              ${filter === cat
                ? 'border-[#002FA7] text-white bg-[#002FA7]/20'
                : 'border-white/10 text-[#737373] hover:text-[#A0A0A0] hover:border-white/20'}`}
            data-testid={`filter-${cat}`}
          >
            {cat}
          </button>
        ))}
        <span className="text-[10px] text-[#737373] font-mono ml-auto">{filtered.length} entries</span>
      </div>

      {/* Log table */}
      <div className="border border-white/10 bg-[#141414]">
        {/* Header */}
        <div className="grid grid-cols-[80px_1fr_180px] gap-4 px-5 py-2.5 border-b border-white/10 text-[10px] tracking-[0.15em] uppercase text-[#737373] font-mono font-bold">
          <span>TYPE</span>
          <span>EVENT</span>
          <span>TIMESTAMP</span>
        </div>

        {/* Rows */}
        <div className="divide-y divide-white/5 max-h-[calc(100vh-250px)] overflow-y-auto">
          {filtered.map((entry, i) => {
            const cfg = categoryConfig[entry.category] || { icon: Activity, color: 'bg-[#737373]', label: entry.category?.toUpperCase() };
            const Icon = cfg.icon;
            return (
              <div key={entry._id} className="grid grid-cols-[80px_1fr_180px] gap-4 px-5 py-3 hover:bg-white/[0.02] transition-colors items-center"
                data-testid={`activity-entry-${entry._id}`}>
                <div className="flex items-center gap-2">
                  <div className={`w-1.5 h-1.5 ${cfg.color}`} />
                  <span className="text-[10px] tracking-wider uppercase text-[#737373] font-mono">{cfg.label}</span>
                </div>
                <div className="text-xs text-[#A0A0A0] truncate">{entry.message}</div>
                <div className="text-[10px] text-[#737373] font-mono flex items-center gap-1.5">
                  <Clock size={10} />
                  {entry.created_at?.replace('T', ' ').split('.')[0]}
                </div>
              </div>
            );
          })}
          {filtered.length === 0 && (
            <div className="py-12 text-center text-xs text-[#737373]">No activity entries</div>
          )}
        </div>
      </div>
    </div>
  );
}
