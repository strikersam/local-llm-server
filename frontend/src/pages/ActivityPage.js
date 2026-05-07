import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { getActivity } from '../api';
import { Filter, Trash2, Activity } from 'lucide-react';

export default function ActivityPage() {
  const [entries, setEntries] = useState([]);
  const [filter, setFilter] = useState('all');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const nav = useNavigate();

  const categoryConfig = {
    chat:   { icon: MessageSquare, dot: 'var(--role-power-user)',  label: 'Chat'   },
    wiki:   { icon: BookOpen,      dot: 'var(--accent)',   label: 'Wiki'   },
    ingest: { icon: Upload,        dot: 'var(--success)', label: 'Ingest' },
    auth:   { icon: Shield,        dot: 'var(--warning)',   label: 'Auth'   },
    lint:   { icon: Activity,      dot: 'var(--info)',    label: 'Lint'   },
  };

  useEffect(() => {
    const loadActivity = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await getActivity();
        setEntries(res.data);
      } catch (err) {
        setError(err?.response?.data?.detail || 'Failed to load activity');
        console.error('Activity load error:', err);
      } finally {
        setLoading(false);
      }
    };

    loadActivity();
    const interval = setInterval(loadActivity, 10000); // Refresh every 10 seconds
    return () => clearInterval(interval);
  }, []);

  const filtered = filter === 'all' ? entries : entries.filter(e => e.category === filter);

  if (loading) {
    return (
      <div className="p-6">
        <div className="flex min-h-[20vh] items-center justify-center">
          <div className="text-center space-y-4">
            <div className="w-8 h-8 border-2 border-t-transparent rounded-full animate-spin"
              style={{ borderColor: 'var(--accent)' }} />
            <p className="text-[0.95rem] text-[var(--text-muted)]">Loading activity...</p>
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
    <div className="p-6 sm:p-8 lg:p-[2rem] max-w-[1400px] mx-auto" data-testid="activity-page">
      {/* Header */}
      <div className="flex items-center justify-between mb-6">
        <div>
          <h1 className="text-[1.75rem] font-bold tracking-[-0.03em] text-[var(--text-primary)]"
            style={{ fontFamily: 'var(--font-main)' }}>Activity Log</h1>
          <p className="text-sm text-[var(--text-tertiary)] mt-1">Full system event trail — all operations are recorded</p>
        </div>
        <div className="flex items-center gap-3">
          <Filter size={14} className="text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] transition-colors duration-200" />
          <select 
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
            className="ml-3 flex items-center gap-2 px-3 py-1.5 rounded-lg border border-[var(--border)]/20 bg-[var(--bg-surface)]/50 text-[var(--text-primary)] focus:outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/20 transition-colors duration-200"
          >
            <option value="all">All Categories</option>
            <option value="chat">Chat</option>
            <option value="wiki">Wiki</option>
            <option value="ingest">Ingest</option>
            <option value="auth">Auth</option>
            <option value="lint">Lint</option>
          </select>
        </div>
      </div>

      {/* Stats Bar */}
      <div className="flex flex-wrap items-center gap-2 mb-6 stagger-1">
        <div className="px-3 py-1.5 rounded-lg text-[0.85rem] font-medium border transition-all capitalize ${
          filter === 'all' 
            ? 'border-[var(--accent)]/60 text-[var(--text-primary)] bg-[var(--accent)]/15'
            : 'border-[var(--border)]/8 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:border-[var(--border)]/14'
        }">
          All ({entries.length})
        </div>
        {Object.keys(categoryConfig).map(cat => (
          <div 
            key={cat}
            className={`px-3 py-1.5 rounded-lg text-[0.85rem] font-medium border transition-all capitalize ${
              filter === cat
                ? `border-[${categoryConfig[cat].dot}]/60 text-[var(--text-primary)] bg-[${categoryConfig[cat].dot}]/15`
                : 'border-[var(--border)]/8 text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:border-[var(--border)]/14'
            }`}
            onClick={() => setFilter(cat)}
          >
            {categoryConfig[cat].label} ({entries.filter(e => e.category === cat).length})
          </div>
        ))}
        <span className="ml-auto text-[0.85rem] font-mono text-[var(--text-tertiary)]">{filtered.length} entries</span>
      </div>

      {/* Entries Container */}
      <div className="bg-[var(--bg-surface)] border border-[var(--border)] rounded-xl overflow-hidden">
        {/* Header */}
        <div className="hidden sm:grid sm:grid-cols-[60px_1fr_120px] gap-3 px-4 py=3 border-b border-[var(--border)]/8 text-[var(--text-muted)] font-medium uppercase tracking-wider text-[0.85rem]">
          <span className="sr-only">Type</span>
          <span className="sr-only">Message</span>
          <span className="sr-only">Time</span>
        </div>
        
        {/* Entries List */}
        <div className="divide-y divide-[var(--border)] max-h-[80vh] overflow-y-auto">
          {filtered.length === 0 ? (
            <div className="py-12 text-center">
              <Activity size={20} className="text-[var(--text-tertiary)] mx-auto mb-4" />
              <p className="text-sm text-[var(--text-tertiary)]">No activity entries {filter !== 'all' ? `for "${filter}"` : ''}</p>
              <p className="text-[0.85rem] font-mono text-[var(--text-muted)] mt-2">
                Activity will appear here as agents perform tasks
              </p>
            </div>
          ) : (
            filtered.map((entry, i) => {
              const cfg = categoryConfig[entry.category] || { icon: Activity, dot: 'var(--text-tertiary)', label: entry.category };
              
              return (
                <div 
                  key={entry._id} 
                  className="flex items-start gap-3 px-4 py-3 hover:bg-[var(--bg-surface)]/20 transition-colors duration-200 sm:items-center"
                >
                  <div className="flex-shrink-0">
                    <div className="w-3 h-3 rounded-full shrink-0" 
                      style={{ background: cfg.dot }} />
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-[0.9rem] text-[var(--text-secondary)] truncate">{entry.message}</div>
                    <div className="text-[0.8rem] font-mono mt-1 flex items-center gap-1">
                      <Clock size={8} className="text-[var(--text-muted)]" />
                      <span className="ml-1">{entry.created_at?.replace('T', ' ').split('.')[0] || ''}</span>
                    </div>
                  </div>
                  <span className="text-[0.8rem] font-mono text-[var(--text-tertiary)] uppercase tracking-wide shrink-0 mt-1 self-start sm:self-center">
                    {cfg.label}
                  </span>
                </div>
              );
            })
          )}
        </div>
      </div>
    </div>
  );
}
