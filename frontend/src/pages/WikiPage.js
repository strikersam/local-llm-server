import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { listWikiPages, getWikiPage, createWikiPage, updateWikiPage, deleteWikiPage, lintWiki } from '../api';
import { BookOpen, Plus, Search, Save, Trash2, Edit3, X, FileText, CheckCircle, AlertTriangle, Loader2 } from 'lucide-react';

export default function WikiPage() {
  const { slug } = useParams();
  const navigate = useNavigate();
  const [pages, setPages] = useState([]);
  const [search, setSearch] = useState('');
  const [current, setCurrent] = useState(null);
  const [editing, setEditing] = useState(false);
  const [creating, setCreating] = useState(false);
  const [form, setForm] = useState({ title: '', content: '', tags: '' });
  const [lintResult, setLintResult] = useState(null);
  const [linting, setLinting] = useState(false);
  const [loading, setLoading] = useState(false);

  useEffect(() => { loadPages(); }, []);
  useEffect(() => { if (slug) loadPage(slug); else setCurrent(null); }, [slug]);

  const loadPages = async (q) => {
    try {
      const { data } = await listWikiPages(q);
      setPages(data.pages || []);
    } catch {}
  };

  const loadPage = async (s) => {
    try {
      const { data } = await getWikiPage(s);
      setCurrent(data);
      setForm({ title: data.title, content: data.content || '', tags: (data.tags || []).join(', ') });
    } catch { setCurrent(null); }
  };

  const handleSearch = (e) => {
    setSearch(e.target.value);
    loadPages(e.target.value || undefined);
  };

  const handleCreate = async () => {
    if (!form.title.trim()) return;
    setLoading(true);
    try {
      const { data } = await createWikiPage({
        title: form.title,
        content: form.content,
        tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
      });
      setCreating(false);
      navigate(`/wiki/${data.slug}`);
      loadPages();
    } catch (err) {
      alert(err?.response?.data?.detail || 'Failed to create page');
    } finally { setLoading(false); }
  };

  const handleUpdate = async () => {
    if (!current) return;
    setLoading(true);
    try {
      await updateWikiPage(current.slug, {
        title: form.title,
        content: form.content,
        tags: form.tags.split(',').map(t => t.trim()).filter(Boolean),
      });
      setEditing(false);
      loadPage(current.slug);
      loadPages();
    } catch {} finally { setLoading(false); }
  };

  const handleDelete = async () => {
    if (!current || !window.confirm('Delete this page?')) return;
    await deleteWikiPage(current.slug);
    navigate('/wiki');
    loadPages();
  };

  const handleLint = async () => {
    setLinting(true);
    try {
      const { data } = await lintWiki();
      setLintResult(data);
    } catch {} finally { setLinting(false); }
  };

  return (
    <div className="h-full flex" data-testid="wiki-page">
      {/* Page list sidebar */}
      <div className="w-72 border-r border-white/10 bg-[#141414] flex flex-col shrink-0 hidden md:flex">
        <div className="p-4 border-b border-white/10 space-y-3">
          <div className="relative">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-[#737373]" />
            <input
              value={search}
              onChange={handleSearch}
              placeholder="Search wiki..."
              className="w-full bg-[#0A0A0A] border border-white/10 pl-9 pr-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]"
              data-testid="wiki-search-input"
            />
          </div>
          <div className="flex gap-2">
            <button
              onClick={() => { setCreating(true); setCurrent(null); setEditing(false); setForm({ title: '', content: '', tags: '' }); navigate('/wiki'); }}
              className="flex-1 flex items-center justify-center gap-1.5 bg-[#002FA7] hover:bg-[#002585] text-white py-2 text-[10px] tracking-wider uppercase font-mono"
              data-testid="create-page-button"
            >
              <Plus size={12} /> NEW PAGE
            </button>
            <button
              onClick={handleLint}
              disabled={linting}
              className="flex items-center justify-center gap-1.5 border border-white/10 hover:border-white/20 text-[#A0A0A0] hover:text-white px-3 py-2 text-[10px] tracking-wider uppercase font-mono transition-all"
              data-testid="lint-wiki-button"
            >
              {linting ? <Loader2 size={12} className="animate-spin" /> : <CheckCircle size={12} />}
            </button>
          </div>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-white/5">
          {pages.map(p => (
            <button
              key={p.slug}
              onClick={() => { setCreating(false); setEditing(false); navigate(`/wiki/${p.slug}`); }}
              className={`w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-white/[0.03] transition-colors
                ${current?.slug === p.slug ? 'bg-white/5 border-l-2 border-[#002FA7]' : 'border-l-2 border-transparent'}`}
              data-testid={`wiki-page-${p.slug}`}
            >
              <FileText size={13} className="text-[#737373] shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-xs text-[#A0A0A0] truncate">{p.title}</div>
                <div className="flex items-center gap-2 mt-0.5">
                  {p.tags?.slice(0, 2).map(t => (
                    <span key={t} className="text-[9px] text-[#737373] bg-white/5 px-1.5 py-0.5">{t}</span>
                  ))}
                </div>
              </div>
            </button>
          ))}
          {pages.length === 0 && (
            <div className="p-6 text-center text-xs text-[#737373]">
              {search ? 'No matching pages' : 'No wiki pages yet. Create one!'}
            </div>
          )}
        </div>
      </div>

      {/* Content area */}
      <div className="flex-1 overflow-y-auto">
        {/* Creating new page */}
        {creating && (
          <div className="p-6 max-w-4xl animate-fade-in" data-testid="wiki-create-form">
            <div className="flex items-center gap-3 mb-6">
              <Plus size={16} className="text-[#002FA7]" />
              <h2 className="text-lg font-bold tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>Create New Page</h2>
              <button onClick={() => setCreating(false)} className="ml-auto p-1 text-[#737373] hover:text-white"><X size={16} /></button>
            </div>
            <div className="space-y-4">
              <div>
                <label className="block text-[10px] tracking-[0.15em] uppercase text-[#737373] mb-2 font-mono">Title</label>
                <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
                  className="w-full bg-[#0A0A0A] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7]"
                  placeholder="Page title" data-testid="wiki-title-input" />
              </div>
              <div>
                <label className="block text-[10px] tracking-[0.15em] uppercase text-[#737373] mb-2 font-mono">Content (Markdown)</label>
                <textarea value={form.content} onChange={e => setForm({ ...form, content: e.target.value })}
                  rows={16}
                  className="w-full bg-[#0A0A0A] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7] resize-y"
                  placeholder="Write markdown content..." data-testid="wiki-content-input" />
              </div>
              <div>
                <label className="block text-[10px] tracking-[0.15em] uppercase text-[#737373] mb-2 font-mono">Tags (comma separated)</label>
                <input value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })}
                  className="w-full bg-[#0A0A0A] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7]"
                  placeholder="llm, agents, architecture" data-testid="wiki-tags-input" />
              </div>
              <button onClick={handleCreate} disabled={loading}
                className="bg-[#002FA7] hover:bg-[#002585] text-white px-6 py-3 text-xs tracking-wider uppercase font-mono flex items-center gap-2 disabled:opacity-50"
                data-testid="wiki-save-button">
                {loading ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                CREATE PAGE
              </button>
            </div>
          </div>
        )}

        {/* Viewing page */}
        {current && !creating && (
          <div className="animate-fade-in" data-testid="wiki-viewer">
            {/* Page header */}
            <div className="px-6 py-4 border-b border-white/10 flex items-center gap-3">
              <BookOpen size={16} className="text-[#002FA7]" />
              <div className="flex-1">
                <h2 className="text-lg font-bold tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>
                  {current.title}
                </h2>
                <div className="flex items-center gap-3 mt-1">
                  <span className="text-[10px] text-[#737373] font-mono">/{current.slug}</span>
                  {current.tags?.map(t => (
                    <span key={t} className="text-[9px] bg-white/5 text-[#A0A0A0] px-2 py-0.5 border border-white/5">{t}</span>
                  ))}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <button onClick={() => setEditing(!editing)}
                  className="flex items-center gap-1.5 border border-white/10 hover:border-[#002FA7] text-[#A0A0A0] hover:text-white px-3 py-1.5 text-[10px] tracking-wider uppercase font-mono transition-all"
                  data-testid="wiki-edit-button">
                  <Edit3 size={12} /> {editing ? 'VIEW' : 'EDIT'}
                </button>
                <button onClick={handleDelete}
                  className="flex items-center gap-1.5 border border-white/10 hover:border-[#FF3333] text-[#737373] hover:text-[#FF3333] px-3 py-1.5 text-[10px] tracking-wider uppercase font-mono transition-all"
                  data-testid="wiki-delete-button">
                  <Trash2 size={12} />
                </button>
              </div>
            </div>

            {editing ? (
              <div className="p-6 space-y-4 max-w-4xl">
                <div>
                  <label className="block text-[10px] tracking-[0.15em] uppercase text-[#737373] mb-2 font-mono">Title</label>
                  <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
                    className="w-full bg-[#0A0A0A] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7]"
                    data-testid="wiki-edit-title" />
                </div>
                <div>
                  <label className="block text-[10px] tracking-[0.15em] uppercase text-[#737373] mb-2 font-mono">Content (Markdown)</label>
                  <textarea value={form.content} onChange={e => setForm({ ...form, content: e.target.value })} rows={20}
                    className="w-full bg-[#0A0A0A] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7] resize-y"
                    data-testid="wiki-edit-content" />
                </div>
                <div>
                  <label className="block text-[10px] tracking-[0.15em] uppercase text-[#737373] mb-2 font-mono">Tags</label>
                  <input value={form.tags} onChange={e => setForm({ ...form, tags: e.target.value })}
                    className="w-full bg-[#0A0A0A] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7]"
                    data-testid="wiki-edit-tags" />
                </div>
                <button onClick={handleUpdate} disabled={loading}
                  className="bg-[#002FA7] hover:bg-[#002585] text-white px-6 py-3 text-xs tracking-wider uppercase font-mono flex items-center gap-2 disabled:opacity-50"
                  data-testid="wiki-update-button">
                  {loading ? <Loader2 size={14} className="animate-spin" /> : <Save size={14} />}
                  SAVE CHANGES
                </button>
              </div>
            ) : (
              <div className="p-6 max-w-4xl wiki-content">
                <ReactMarkdown remarkPlugins={[remarkGfm]}>{current.content || '*No content yet.*'}</ReactMarkdown>
              </div>
            )}
          </div>
        )}

        {/* Empty state / Lint results */}
        {!current && !creating && (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 animate-fade-in">
            {lintResult ? (
              <div className="w-full max-w-2xl text-left" data-testid="lint-results">
                <h3 className="text-lg font-bold tracking-tight mb-4" style={{ fontFamily: 'Outfit, sans-serif' }}>Wiki Health Report</h3>
                {lintResult.summary && <p className="text-xs text-[#A0A0A0] mb-4">{lintResult.summary}</p>}
                {lintResult.issues?.length > 0 ? (
                  <div className="space-y-2">
                    {lintResult.issues.map((issue, i) => (
                      <div key={i} className="flex items-start gap-3 border border-white/10 bg-[#141414] p-3">
                        <AlertTriangle size={14} className={issue.severity === 'high' ? 'text-[#FF3333]' : 'text-[#F59E0B]'} />
                        <div>
                          <div className="text-xs text-white">{issue.description}</div>
                          <div className="text-[10px] text-[#737373] mt-1">
                            {issue.type} &middot; {issue.page || 'global'} &middot; {issue.severity}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="text-xs text-green-500 flex items-center gap-2"><CheckCircle size={14} /> Wiki is healthy!</div>
                )}
                <button onClick={() => setLintResult(null)} className="mt-4 text-[10px] text-[#737373] hover:text-white font-mono">DISMISS</button>
              </div>
            ) : (
              <>
                <BookOpen size={40} className="text-[#002FA7] mb-4" />
                <h3 className="text-lg font-bold tracking-tight mb-2" style={{ fontFamily: 'Outfit, sans-serif' }}>Wiki Browser</h3>
                <p className="text-xs text-[#737373] max-w-md">
                  Select a page from the sidebar or create a new one.
                  Use the lint button to check wiki health.
                </p>
              </>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
