import React, { useState, useEffect, useRef } from 'react';
import { BookOpen, Upload, Plus, ExternalLink, RefreshCw, AlertTriangle, Github, FileText, Globe, GitBranch, Loader } from 'lucide-react';
import {
  listWikiPages, createWikiPage, deleteWikiPage,
  listSources, ingestSource, deleteSource,
  githubStatus, listGithubRepos, fmtErr,
} from '../api';

const C = {
  bg: '#0F0F13', surface: '#141418', border: 'rgba(255,255,255,0.06)',
  primary: '#F2F2F6', secondary: '#B2B2C4', tertiary: '#808094', muted: '#565666',
  accent: '#002FA7',
};

function TabBar({ tabs, active, onChange }) {
  return (
    <div className="flex border rounded-lg overflow-hidden" style={{ borderColor: 'rgba(255,255,255,0.10)' }}>
      {tabs.map(([id, label]) => (
        <button key={id} onClick={() => onChange(id)}
          className="px-4 py-1.5 text-[10px] font-mono uppercase tracking-wider transition-colors"
          style={active === id
            ? { background: C.accent, color: '#fff' }
            : { color: C.tertiary, background: 'transparent' }}
          onMouseEnter={e => { if (active !== id) e.currentTarget.style.color = C.secondary; }}
          onMouseLeave={e => { if (active !== id) e.currentTarget.style.color = C.tertiary; }}>
          {label}
        </button>
      ))}
    </div>
  );
}

function StatusBadge({ status }) {
  const map = {
    ingested:   { color: '#10B981', label: 'ingested' },
    processing: { color: '#F59E0B', label: 'processing' },
    error:      { color: '#EF4444', label: 'error' },
    pending:    { color: '#6E6E80', label: 'pending' },
  };
  const { color, label } = map[status] || { color: C.muted, label: status };
  return (
    <span className="text-[9px] font-mono uppercase px-2 py-0.5 rounded border"
      style={{ color, borderColor: color + '30', background: color + '10' }}>
      {label}
    </span>
  );
}

function WikiTab() {
  const [pages, setPages]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState('');
  const [creating, setCreating] = useState(false);
  const [newTitle, setNewTitle] = useState('');

  useEffect(() => {
    setLoading(true);
    listWikiPages()
      .then(r => setPages(r.data?.pages || r.data || []))
      .catch(e => setError(fmtErr(e)))
      .finally(() => setLoading(false));
  }, []);

  async function handleCreate() {
    if (!newTitle.trim()) return;
    try {
      const slug = newTitle.trim().toLowerCase().replace(/\s+/g, '-').replace(/[^a-z0-9-]/g, '');
      const r = await createWikiPage({ title: newTitle.trim(), slug, content: '' });
      setPages(prev => [r.data, ...prev]);
      setNewTitle('');
      setCreating(false);
    } catch (e) {
      setError(fmtErr(e));
    }
  }

  return (
    <div className="space-y-3">
      {creating && (
        <div className="flex gap-2">
          <input autoFocus value={newTitle} onChange={e => setNewTitle(e.target.value)}
            placeholder="Page title"
            onKeyDown={e => { if (e.key === 'Enter') handleCreate(); if (e.key === 'Escape') setCreating(false); }}
            className="flex-1 px-3 py-2 text-[12px] font-mono rounded-lg outline-none placeholder:text-[#565666]"
            style={{ background: '#18181D', border: '1px solid rgba(0,47,167,0.4)', color: C.primary }} />
          <button onClick={handleCreate}
            className="px-3 py-2 text-[10px] font-mono text-white rounded-lg" style={{ background: C.accent }}>
            Create
          </button>
          <button onClick={() => setCreating(false)}
            className="px-3 py-2 text-[10px] font-mono rounded-lg border transition-colors"
            style={{ color: C.tertiary, borderColor: 'rgba(255,255,255,0.1)' }}>
            Cancel
          </button>
        </div>
      )}

      {error && (
        <div className="text-[10px] text-amber-400 font-mono flex items-center gap-2">
          <AlertTriangle size={11} /> {error}
        </div>
      )}

      {loading ? (
        <div className="py-10 text-center text-[11px] font-mono" style={{ color: C.muted }}>Loading pages…</div>
      ) : pages.length === 0 ? (
        <div className="py-12 text-center">
          <BookOpen size={24} className="mx-auto mb-3" style={{ color: C.muted }} />
          <div className="text-[12px] font-medium mb-1" style={{ color: C.secondary }}>No wiki pages yet</div>
          <button onClick={() => setCreating(true)}
            className="mt-2 px-3 py-1.5 text-[10px] font-mono text-white rounded-lg" style={{ background: C.accent }}>
            Create first page
          </button>
        </div>
      ) : (
        pages.map(p => (
          <div key={p.slug || p.id} className="flex items-center gap-3 px-4 py-3 rounded-xl border cursor-pointer transition-all"
            style={{ background: C.surface, borderColor: C.border }}
            onMouseEnter={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'; e.currentTarget.style.background = '#18181D'; }}
            onMouseLeave={e => { e.currentTarget.style.borderColor = C.border; e.currentTarget.style.background = C.surface; }}>
            <FileText size={13} style={{ color: C.tertiary }} className="shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-[12.5px] font-medium truncate" style={{ color: '#D8D8E8' }}>{p.title}</div>
              <div className="text-[9px] font-mono" style={{ color: C.muted }}>
                {p.slug} {p.word_count ? `· ${p.word_count.toLocaleString()} words` : ''}
              </div>
            </div>
            {p.updated_at && (
              <span className="text-[9px] font-mono shrink-0" style={{ color: C.muted }}>
                {new Date(p.updated_at * 1000 || p.updated_at).toLocaleDateString()}
              </span>
            )}
          </div>
        ))
      )}
    </div>
  );
}

function SourcesTab() {
  const [sources, setSources] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState('');
  const fileRef = useRef(null);
  const [uploading, setUploading] = useState(false);

  useEffect(() => {
    setLoading(true);
    listSources()
      .then(r => setSources(r.data?.sources || r.data || []))
      .catch(e => setError(fmtErr(e)))
      .finally(() => setLoading(false));
  }, []);

  async function handleFileUpload(e) {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    setUploading(true);
    setError('');
    for (const file of files) {
      try {
        const fd = new FormData();
        fd.append('file', file);
        const r = await ingestSource(fd);
        setSources(prev => [r.data, ...prev]);
      } catch (err) {
        setError(fmtErr(err));
      }
    }
    setUploading(false);
    e.target.value = '';
  }

  function srcIcon(type) {
    if (type === 'git' || type === 'github') return Github;
    if (type === 'url') return Globe;
    return FileText;
  }

  return (
    <div className="space-y-2">
      {error && (
        <div className="text-[10px] text-amber-400 font-mono flex items-center gap-2 mb-2">
          <AlertTriangle size={11} /> {error}
        </div>
      )}

      {loading ? (
        <div className="py-10 text-center text-[11px] font-mono" style={{ color: C.muted }}>Loading sources…</div>
      ) : (
        sources.map(s => {
          const Icon = srcIcon(s.type);
          return (
            <div key={s.id || s.name} className="flex items-center gap-3 px-4 py-3 rounded-xl border transition-all"
              style={{ background: C.surface, borderColor: C.border }}
              onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'}
              onMouseLeave={e => e.currentTarget.style.borderColor = C.border}>
              <Icon size={13} style={{ color: C.tertiary }} className="shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-[12.5px] font-medium truncate" style={{ color: '#D8D8E8' }}>{s.name}</div>
                <div className="text-[9px] font-mono" style={{ color: C.muted }}>
                  {s.type} {s.size ? `· ${s.size}` : ''} {s.chunk_count ? `· ${s.chunk_count} chunks` : ''}
                </div>
              </div>
              <StatusBadge status={s.status || 'ingested'} />
            </div>
          );
        })
      )}

      {/* Drop zone */}
      <div
        className="mt-4 border-2 border-dashed rounded-xl p-8 text-center cursor-pointer transition-colors"
        style={{ borderColor: uploading ? C.accent : 'rgba(255,255,255,0.08)' }}
        onClick={() => fileRef.current?.click()}
        onDragOver={e => { e.preventDefault(); e.currentTarget.style.borderColor = C.accent; }}
        onDragLeave={e => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)'; }}
        onDrop={async e => {
          e.preventDefault();
          e.currentTarget.style.borderColor = 'rgba(255,255,255,0.08)';
          const dt = e.dataTransfer;
          if (dt.files?.length) {
            await handleFileUpload({ target: { files: dt.files, value: '' } });
          }
        }}>
        {uploading
          ? <Loader size={20} className="mx-auto mb-2 animate-spin" style={{ color: C.accent }} />
          : <Upload size={20} className="mx-auto mb-2" style={{ color: C.muted }} />
        }
        <div className="text-[11px] font-mono" style={{ color: C.tertiary }}>
          {uploading ? 'Uploading…' : 'Drop files here or click to upload'}
        </div>
        <div className="text-[9px] font-mono mt-1" style={{ color: C.muted }}>PDF, DOCX, TXT, URLs, Git repos</div>
      </div>
      <input ref={fileRef} type="file" multiple className="hidden" accept=".pdf,.docx,.doc,.txt,.md"
        onChange={handleFileUpload} />
    </div>
  );
}

function GitHubTab() {
  const [status, setStatus] = useState(null);
  const [repos, setRepos]   = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError]   = useState('');

  useEffect(() => {
    setLoading(true);
    Promise.allSettled([
      githubStatus().then(r => setStatus(r.data)),
      listGithubRepos().then(r => setRepos(r.data?.repos || r.data || [])),
    ])
      .catch(e => setError(fmtErr(e)))
      .finally(() => setLoading(false));
  }, []);

  const connected = status?.connected;

  if (!connected) {
    return (
      <div className="py-12 text-center">
        <Github size={28} className="mx-auto mb-3" style={{ color: C.muted }} />
        <div className="text-[13px] font-medium mb-1.5" style={{ color: C.secondary }}>GitHub not connected</div>
        <div className="text-[10px] font-mono mb-4" style={{ color: C.muted }}>Connect to browse repos, clone locally, and enable agent workspace</div>
        <button
          onClick={() => { import('../api').then(({ startGithubOAuth }) => startGithubOAuth(true)); }}
          className="px-4 py-2 text-[11px] font-mono text-white rounded-lg" style={{ background: C.accent }}>
          Connect GitHub
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {error && (
        <div className="text-[10px] text-amber-400 font-mono flex items-center gap-2 mb-2">
          <AlertTriangle size={11} /> {error}
        </div>
      )}
      {loading ? (
        <div className="py-10 text-center text-[11px] font-mono" style={{ color: C.muted }}>Loading repos…</div>
      ) : repos.length === 0 ? (
        <div className="py-10 text-center text-[11px] font-mono" style={{ color: C.muted }}>No repositories found</div>
      ) : (
        repos.map(r => (
          <div key={r.full_name || r.name} className="flex items-center gap-3 px-4 py-3 rounded-xl border transition-all"
            style={{ background: C.surface, borderColor: C.border }}
            onMouseEnter={e => e.currentTarget.style.borderColor = 'rgba(255,255,255,0.12)'}
            onMouseLeave={e => e.currentTarget.style.borderColor = C.border}>
            <GitBranch size={13} style={{ color: C.tertiary }} className="shrink-0" />
            <div className="flex-1 min-w-0">
              <div className="text-[12.5px] font-medium truncate" style={{ color: '#D8D8E8' }}>{r.full_name || r.name}</div>
              <div className="text-[9px] font-mono" style={{ color: C.muted }}>
                {r.language || 'unknown'} {r.default_branch ? `· ${r.default_branch}` : ''} {r.stargazers_count != null ? `· ★ ${r.stargazers_count}` : ''}
              </div>
            </div>
            {r.private && (
              <span className="text-[8px] font-mono px-1.5 py-0.5 rounded border" style={{ color: C.muted, borderColor: 'rgba(255,255,255,0.08)' }}>private</span>
            )}
            <a href={r.html_url} target="_blank" rel="noreferrer" onClick={e => e.stopPropagation()}
              style={{ color: C.muted }}
              onMouseEnter={e => e.currentTarget.style.color = C.secondary}
              onMouseLeave={e => e.currentTarget.style.color = C.muted}>
              <ExternalLink size={11} />
            </a>
          </div>
        ))
      )}
    </div>
  );
}

export default function KnowledgePage() {
  const [tab, setTab] = useState('wiki');

  const tabActions = {
    wiki:    <button onClick={() => {}} className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono uppercase text-white rounded-lg" style={{ background: C.accent }}><Plus size={11} /> New Page</button>,
    sources: <button onClick={() => {}} className="flex items-center gap-1.5 px-3 py-1.5 text-[10px] font-mono uppercase text-white rounded-lg" style={{ background: C.accent }}><Plus size={11} /> Add Source</button>,
    github:  null,
  };

  return (
    <div className="h-full flex flex-col overflow-hidden">
      {/* Header */}
      <div className="flex items-center gap-4 px-5 py-3.5 border-b shrink-0"
        style={{ borderColor: C.border }}>
        <h1 className="text-[15px] font-bold tracking-tight flex-1"
          style={{ color: C.primary, fontFamily: 'var(--font-main)' }}>Knowledge</h1>
        <TabBar tabs={[['wiki','Wiki'],['sources','Sources'],['github','GitHub']]} active={tab} onChange={setTab} />
        {tabActions[tab]}
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-5">
        {tab === 'wiki'    && <WikiTab />}
        {tab === 'sources' && <SourcesTab />}
        {tab === 'github'  && <GitHubTab />}
      </div>
    </div>
  );
}
