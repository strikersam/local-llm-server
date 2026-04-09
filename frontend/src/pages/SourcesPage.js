import React, { useState, useEffect } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { listSources, getSource, deleteSource, ingestSource } from '../api';
import { Upload, Link, FileText, Trash2, Eye, X, Loader2, CheckCircle, AlertCircle, Globe } from 'lucide-react';

export default function SourcesPage() {
  const [sources, setSources] = useState([]);
  const [viewing, setViewing] = useState(null);
  const [tab, setTab] = useState('file'); // file | url | text
  const [uploading, setUploading] = useState(false);
  const [urlInput, setUrlInput] = useState('');
  const [textInput, setTextInput] = useState('');
  const [titleInput, setTitleInput] = useState('');

  useEffect(() => { loadSources(); }, []);

  const loadSources = async () => {
    try {
      const { data } = await listSources();
      setSources(data.sources || []);
    } catch {}
  };

  const handleFileUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('file', file);
      if (titleInput) fd.append('title', titleInput);
      await ingestSource(fd);
      loadSources();
      setTitleInput('');
    } catch {} finally { setUploading(false); }
  };

  const handleUrlIngest = async () => {
    if (!urlInput.trim()) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('url', urlInput);
      if (titleInput) fd.append('title', titleInput);
      await ingestSource(fd);
      loadSources();
      setUrlInput('');
      setTitleInput('');
    } catch {} finally { setUploading(false); }
  };

  const handleTextIngest = async () => {
    if (!textInput.trim()) return;
    setUploading(true);
    try {
      const fd = new FormData();
      fd.append('content_text', textInput);
      if (titleInput) fd.append('title', titleInput || 'Text Input');
      await ingestSource(fd);
      loadSources();
      setTextInput('');
      setTitleInput('');
    } catch {} finally { setUploading(false); }
  };

  const handleView = async (id) => {
    try {
      const { data } = await getSource(id);
      setViewing(data);
    } catch {}
  };

  const handleDelete = async (id) => {
    await deleteSource(id);
    if (viewing?._id === id) setViewing(null);
    loadSources();
  };

  const statusColor = (s) => s === 'processed' ? 'text-green-500' : s === 'failed' ? 'text-[#FF3333]' : 'text-[#F59E0B]';
  const StatusIcon = ({ status }) => status === 'processed' ? <CheckCircle size={12} className="text-green-500" /> :
    status === 'failed' ? <AlertCircle size={12} className="text-[#FF3333]" /> : <Loader2 size={12} className="text-[#F59E0B] animate-spin" />;

  return (
    <div className="h-full flex" data-testid="sources-page">
      {/* Left: Ingest + List */}
      <div className="w-80 border-r border-white/10 bg-[#141414] flex flex-col shrink-0 hidden md:flex">
        {/* Ingest panel */}
        <div className="p-4 border-b border-white/10 space-y-3">
          <div className="text-[10px] tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold mb-2">INGEST SOURCE</div>

          <input
            value={titleInput}
            onChange={(e) => setTitleInput(e.target.value)}
            placeholder="Source title (optional)"
            className="w-full bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]"
            data-testid="source-title-input"
          />

          {/* Tab buttons */}
          <div className="flex border border-white/10">
            {[
              { id: 'file', icon: FileText, label: 'FILE' },
              { id: 'url', icon: Globe, label: 'URL' },
              { id: 'text', icon: FileText, label: 'TEXT' },
            ].map(t => (
              <button key={t.id} onClick={() => setTab(t.id)}
                className={`flex-1 flex items-center justify-center gap-1 py-2 text-[10px] tracking-wider uppercase font-mono transition-colors
                  ${tab === t.id ? 'bg-[#002FA7] text-white' : 'text-[#737373] hover:text-[#A0A0A0]'}`}
                data-testid={`source-tab-${t.id}`}>
                <t.icon size={11} /> {t.label}
              </button>
            ))}
          </div>

          {tab === 'file' && (
            <label className={`block border-2 border-dashed border-white/10 hover:border-[#002FA7]/50 p-6 text-center cursor-pointer transition-colors ${uploading ? 'opacity-50' : ''}`}
              data-testid="source-file-drop">
              <Upload size={20} className="mx-auto mb-2 text-[#737373]" />
              <span className="text-[10px] text-[#737373] font-mono">{uploading ? 'UPLOADING...' : 'DROP FILE OR CLICK'}</span>
              <input type="file" className="hidden" onChange={handleFileUpload} disabled={uploading} data-testid="source-file-input" />
            </label>
          )}

          {tab === 'url' && (
            <div className="space-y-2">
              <input value={urlInput} onChange={(e) => setUrlInput(e.target.value)}
                placeholder="https://example.com/article"
                className="w-full bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]"
                data-testid="source-url-input" />
              <button onClick={handleUrlIngest} disabled={uploading || !urlInput.trim()}
                className="w-full bg-[#002FA7] hover:bg-[#002585] text-white py-2 text-[10px] tracking-wider uppercase font-mono disabled:opacity-50"
                data-testid="source-url-submit">
                {uploading ? 'INGESTING...' : 'INGEST URL'}
              </button>
            </div>
          )}

          {tab === 'text' && (
            <div className="space-y-2">
              <textarea value={textInput} onChange={(e) => setTextInput(e.target.value)}
                placeholder="Paste text content..."
                rows={4}
                className="w-full bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7] resize-y"
                data-testid="source-text-input" />
              <button onClick={handleTextIngest} disabled={uploading || !textInput.trim()}
                className="w-full bg-[#002FA7] hover:bg-[#002585] text-white py-2 text-[10px] tracking-wider uppercase font-mono disabled:opacity-50"
                data-testid="source-text-submit">
                {uploading ? 'INGESTING...' : 'INGEST TEXT'}
              </button>
            </div>
          )}
        </div>

        {/* Source list */}
        <div className="flex-1 overflow-y-auto divide-y divide-white/5">
          {sources.map(s => (
            <div key={s._id} className={`flex items-center gap-2 px-4 py-3 hover:bg-white/[0.03] transition-colors cursor-pointer group
              ${viewing?._id === s._id ? 'bg-white/5 border-l-2 border-[#002FA7]' : 'border-l-2 border-transparent'}`}
              onClick={() => handleView(s._id)} data-testid={`source-item-${s._id}`}>
              <StatusIcon status={s.status} />
              <div className="flex-1 min-w-0">
                <div className="text-xs text-[#A0A0A0] truncate">{s.title}</div>
                <div className="text-[10px] text-[#737373] flex items-center gap-2">
                  <span className="uppercase">{s.type}</span>
                  <span>{s.created_at?.split('T')[0]}</span>
                </div>
              </div>
              <button onClick={(e) => { e.stopPropagation(); handleDelete(s._id); }}
                className="opacity-0 group-hover:opacity-100 p-1 text-[#737373] hover:text-[#FF3333] transition-all"
                data-testid={`source-delete-${s._id}`}>
                <Trash2 size={12} />
              </button>
            </div>
          ))}
          {sources.length === 0 && (
            <div className="p-6 text-center text-xs text-[#737373]">No sources ingested yet</div>
          )}
        </div>
      </div>

      {/* Right: Detail view */}
      <div className="flex-1 overflow-y-auto">
        {viewing ? (
          <div className="animate-fade-in" data-testid="source-detail">
            <div className="px-6 py-4 border-b border-white/10 flex items-center gap-3">
              <StatusIcon status={viewing.status} />
              <div className="flex-1">
                <h2 className="text-sm font-bold text-white">{viewing.title}</h2>
                <div className="text-[10px] text-[#737373] font-mono mt-1">
                  {viewing.type.toUpperCase()} &middot; {viewing.status.toUpperCase()} &middot; {viewing.created_at?.replace('T', ' ').split('.')[0]}
                </div>
              </div>
              <button onClick={() => setViewing(null)} className="p-1 text-[#737373] hover:text-white"><X size={16} /></button>
            </div>
            {viewing.url && (
              <div className="px-6 py-2 border-b border-white/5 text-xs text-[#002FA7] font-mono truncate">
                <a href={viewing.url} target="_blank" rel="noopener noreferrer">{viewing.url}</a>
              </div>
            )}
            {viewing.summary && (
              <div className="p-6 border-b border-white/10">
                <div className="text-[10px] tracking-[0.15em] uppercase text-[#737373] mb-3 font-mono font-bold">AI SUMMARY</div>
                <div className="wiki-content text-xs">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>{viewing.summary}</ReactMarkdown>
                </div>
              </div>
            )}
            {viewing.raw_content && (
              <div className="p-6">
                <div className="text-[10px] tracking-[0.15em] uppercase text-[#737373] mb-3 font-mono font-bold">RAW CONTENT</div>
                <pre className="text-xs text-[#A0A0A0] bg-[#0A0A0A] border border-white/10 p-4 overflow-auto max-h-96 whitespace-pre-wrap font-mono">
                  {viewing.raw_content?.substring(0, 5000)}
                  {viewing.raw_content?.length > 5000 && '\n\n... (truncated)'}
                </pre>
              </div>
            )}
          </div>
        ) : (
          <div className="h-full flex flex-col items-center justify-center text-center p-8 animate-fade-in">
            <Upload size={40} className="text-[#002FA7] mb-4" />
            <h3 className="text-lg font-bold tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>Source Ingestion</h3>
            <p className="text-xs text-[#737373] max-w-md">
              Upload files, paste URLs, or input text. The AI agent will process and summarize each source for your wiki.
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
