import React, { useState, useEffect, useCallback } from 'react';
import {
  Github, FolderOpen, FileText, GitBranch, GitPullRequest,
  ChevronRight, ChevronDown, Loader2, Plus, RefreshCw,
  Check, X, ExternalLink, ArrowLeft, Save, GitCommit,
} from 'lucide-react';
import {
  githubStatus, listGithubRepos, listGithubBranches,
  getGithubTree, readGithubFile, writeGithubFile,
  listGithubPulls, createGithubPR, fmtErr,
} from '../api';

// ─── RepoSelector ──────────────────────────────────────────────────────────────
function RepoSelector({ onSelect }) {
  const [repos, setRepos] = useState([]);
  const [loading, setLoading] = useState(true);
  const [q, setQ] = useState('');
  const [searching, setSearching] = useState(false);
  const [loadErr, setLoadErr] = useState('');

  const load = useCallback(async (query = '') => {
    query ? setSearching(true) : setLoading(true);
    setLoadErr('');
    try {
      const { data } = await listGithubRepos(query);
      setRepos(data.repos || []);
    } catch (e) {
      setLoadErr(fmtErr(e?.response?.data?.detail) || e.message || 'Failed to load repositories');
    } finally { setLoading(false); setSearching(false); }
  }, []);

  useEffect(() => { load(); }, [load]);

  const handleSearch = (e) => {
    e.preventDefault();
    load(q);
  };

  return (
    <div className="space-y-4">
      <form onSubmit={handleSearch} className="flex gap-2">
        <input
          value={q}
          onChange={e => setQ(e.target.value)}
          placeholder="Search repositories…"
          className="flex-1 bg-[#0A0A0A] border border-white/10 px-3 py-2 text-xs text-white font-mono outline-none focus:border-[#002FA7]"
        />
        <button type="submit" disabled={searching}
          className="flex items-center gap-1.5 bg-[#002FA7] hover:bg-[#002585] text-white px-4 py-2 text-[10px] tracking-wider uppercase font-mono disabled:opacity-50">
          {searching ? <Loader2 size={11} className="animate-spin" /> : <RefreshCw size={11} />} Search
        </button>
      </form>

      {loadErr && <div className="text-[10px] text-[#FF3333] font-mono py-2">{loadErr}</div>}
      {loading ? (
        <div className="flex items-center gap-2 text-xs text-[#737373] py-4"><Loader2 size={14} className="animate-spin" /> Loading repos…</div>
      ) : (
        <div className="space-y-1.5 max-h-[60vh] overflow-y-auto">
          {repos.map(r => (
            <button key={r.full_name} onClick={() => onSelect(r)}
              className="w-full text-left border border-white/10 bg-[#141414] hover:border-[#002FA7] p-3 transition-all group">
              <div className="flex items-center gap-2">
                <Github size={13} className="text-[#737373] shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="text-xs text-white font-mono truncate">{r.full_name}</span>
                    {r.private && <span className="text-[8px] bg-white/10 text-[#737373] px-1 py-0.5 rounded font-mono">PRIVATE</span>}
                    {r.language && <span className="text-[8px] text-[#737373] font-mono">{r.language}</span>}
                  </div>
                  {r.description && <div className="text-[10px] text-[#737373] truncate mt-0.5">{r.description}</div>}
                </div>
                <ChevronRight size={12} className="text-[#737373] group-hover:text-white transition-colors shrink-0" />
              </div>
            </button>
          ))}
          {repos.length === 0 && <div className="text-xs text-[#737373] py-4 text-center">No repositories found</div>}
        </div>
      )}
    </div>
  );
}

// ─── FileTree ──────────────────────────────────────────────────────────────────
function FileTree({ owner, repo, ref, onFileSelect }) {
  const [tree, setTree] = useState([]);
  const [expanded, setExpanded] = useState({});
  const [subtrees, setSubtrees] = useState({});
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    getGithubTree(owner, repo, ref, '')
      .then(({ data }) => setTree(data.items || []))
      .catch(() => { })
      .finally(() => setLoading(false));
  }, [owner, repo, ref]);

  const toggleDir = async (path) => {
    const open = !expanded[path];
    setExpanded(prev => ({ ...prev, [path]: open }));
    if (open && !subtrees[path]) {
      try {
        const { data } = await getGithubTree(owner, repo, ref, path);
        setSubtrees(prev => ({ ...prev, [path]: data.items || [] }));
      } catch { }
    }
  };

  const renderItems = (items, depth = 0) =>
    items.map(item => (
      <div key={item.path}>
        <button
          onClick={() => item.type === 'dir' ? toggleDir(item.path) : onFileSelect(item.path)}
          className="w-full flex items-center gap-1.5 px-2 py-1 text-left hover:bg-white/[0.04] transition-colors group"
          style={{ paddingLeft: `${8 + depth * 14}px` }}
        >
          {item.type === 'dir'
            ? (expanded[item.path] ? <ChevronDown size={11} className="text-[#737373] shrink-0" /> : <ChevronRight size={11} className="text-[#737373] shrink-0" />)
            : <FileText size={11} className="text-[#737373] shrink-0" />}
          <span className="text-[11px] font-mono truncate"
            style={{ color: item.type === 'dir' ? '#A0A0A0' : '#737373' }}>
            {item.name}
          </span>
        </button>
        {item.type === 'dir' && expanded[item.path] && subtrees[item.path] &&
          renderItems(subtrees[item.path], depth + 1)}
      </div>
    ));

  if (loading) return <div className="flex items-center gap-2 text-xs text-[#737373] p-3"><Loader2 size={12} className="animate-spin" /> Loading…</div>;
  return <div className="overflow-y-auto max-h-[calc(100vh-300px)]">{renderItems(tree)}</div>;
}

// ─── FileEditor ────────────────────────────────────────────────────────────────
function FileEditor({ owner, repo, branch, filePath, onCommitted }) {
  const [content, setContent] = useState('');
  const [originalContent, setOriginalContent] = useState('');
  const [sha, setSha] = useState('');
  const [loading, setLoading] = useState(true);
  const [commitMsg, setCommitMsg] = useState('');
  const [saving, setSaving] = useState(false);
  const [err, setErr] = useState('');
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    setLoading(true);
    setErr('');
    setSaved(false);
    readGithubFile(owner, repo, filePath, branch)
      .then(({ data }) => {
        setContent(data.content);
        setOriginalContent(data.content);
        setSha(data.sha);
        setCommitMsg(`Update ${filePath}`);
      })
      .catch(e => setErr(fmtErr(e?.response?.data?.detail) || e.message))
      .finally(() => setLoading(false));
  }, [owner, repo, filePath, branch]);

  const handleSave = async () => {
    if (!commitMsg.trim()) return;
    setSaving(true);
    setErr('');
    try {
      const { data } = await writeGithubFile(owner, repo, { path: filePath, content, message: commitMsg, sha, branch });
      setSaved(true);
      setOriginalContent(content);
      // Update SHA so the next save doesn't fail with a stale SHA conflict
      if (data.file_sha) setSha(data.file_sha);
      onCommitted && onCommitted(filePath, commitMsg);
      setTimeout(() => setSaved(false), 3000);
    } catch (e) {
      setErr(fmtErr(e?.response?.data?.detail) || e.message);
    } finally {
      setSaving(false);
    }
  };

  const isDirty = content !== originalContent;

  if (loading) return <div className="flex items-center gap-2 text-xs text-[#737373] p-4"><Loader2 size={14} className="animate-spin" /> Loading file…</div>;

  return (
    <div className="flex flex-col h-full">
      <div className="px-4 py-2.5 border-b border-white/10 flex items-center gap-2">
        <FileText size={13} className="text-[#737373]" />
        <span className="text-xs font-mono text-[#A0A0A0] truncate flex-1">{filePath}</span>
        {isDirty && <span className="text-[9px] bg-yellow-500/20 text-yellow-400 px-1.5 py-0.5 font-mono">MODIFIED</span>}
      </div>

      <textarea
        value={content}
        onChange={e => setContent(e.target.value)}
        className="flex-1 bg-[#0A0A0A] text-[11px] font-mono text-[#A0A0A0] p-4 outline-none resize-none border-none"
        spellCheck={false}
      />

      <div className="border-t border-white/10 p-3 space-y-2">
        {err && <div className="text-[10px] text-[#FF3333] font-mono">{err}</div>}
        <div className="flex gap-2">
          <input
            value={commitMsg}
            onChange={e => setCommitMsg(e.target.value)}
            placeholder="Commit message…"
            className="flex-1 bg-[#0A0A0A] border border-white/10 px-3 py-1.5 text-[11px] text-white font-mono outline-none focus:border-[#002FA7]"
          />
          <button
            onClick={handleSave}
            disabled={saving || !isDirty || !commitMsg.trim()}
            className="flex items-center gap-1.5 bg-[#002FA7] hover:bg-[#002585] text-white px-3 py-1.5 text-[10px] tracking-wider uppercase font-mono disabled:opacity-40 shrink-0"
          >
            {saving ? <Loader2 size={11} className="animate-spin" /> : saved ? <Check size={11} /> : <Save size={11} />}
            {saved ? 'Saved' : 'Commit'}
          </button>
        </div>
      </div>
    </div>
  );
}

// ─── PRPanel ──────────────────────────────────────────────────────────────────
function PRPanel({ owner, repo, defaultBranch }) {
  const [pulls, setPulls] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState({ title: '', body: '', head: '', base: defaultBranch || 'main' });
  const [creating, setCreating] = useState(false);
  const [err, setErr] = useState('');

  const load = useCallback(() => {
    setLoading(true);
    listGithubPulls(owner, repo)
      .then(({ data }) => setPulls(data.pulls || []))
      .catch(() => { })
      .finally(() => setLoading(false));
  }, [owner, repo]);

  useEffect(() => { load(); }, [load]);

  const handleCreate = async () => {
    if (!form.title.trim() || !form.head.trim()) return;
    setCreating(true);
    setErr('');
    try {
      await createGithubPR(owner, repo, form);
      setShowCreate(false);
      setForm({ title: '', body: '', head: '', base: defaultBranch || 'main' });
      load();
    } catch (e) {
      setErr(fmtErr(e?.response?.data?.detail) || e.message);
    } finally {
      setCreating(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <span className="text-[10px] tracking-[0.15em] uppercase text-[#737373] font-mono font-bold">Pull Requests</span>
        <button onClick={() => setShowCreate(!showCreate)}
          className="flex items-center gap-1 text-[9px] tracking-wider uppercase font-mono text-[#002FA7] hover:text-white transition-colors">
          <Plus size={10} /> New PR
        </button>
      </div>

      {showCreate && (
        <div className="border border-[#002FA7]/30 bg-[#0A0A0A] p-3 space-y-2">
          {err && <div className="text-[10px] text-[#FF3333] font-mono">{err}</div>}
          <input value={form.title} onChange={e => setForm({ ...form, title: e.target.value })}
            placeholder="PR title" className="w-full bg-[#141414] border border-white/10 px-3 py-1.5 text-[11px] text-white font-mono outline-none focus:border-[#002FA7]" />
          <div className="flex gap-2">
            <input value={form.head} onChange={e => setForm({ ...form, head: e.target.value })}
              placeholder="head branch" className="flex-1 bg-[#141414] border border-white/10 px-3 py-1.5 text-[11px] text-white font-mono outline-none focus:border-[#002FA7]" />
            <span className="text-[#737373] text-xs self-center">→</span>
            <input value={form.base} onChange={e => setForm({ ...form, base: e.target.value })}
              placeholder="base branch" className="flex-1 bg-[#141414] border border-white/10 px-3 py-1.5 text-[11px] text-white font-mono outline-none focus:border-[#002FA7]" />
          </div>
          <textarea value={form.body} onChange={e => setForm({ ...form, body: e.target.value })}
            placeholder="Description (optional)" rows={3}
            className="w-full bg-[#141414] border border-white/10 px-3 py-1.5 text-[11px] text-white font-mono outline-none focus:border-[#002FA7] resize-none" />
          <div className="flex gap-2">
            <button onClick={handleCreate} disabled={creating || !form.title.trim() || !form.head.trim()}
              className="flex items-center gap-1.5 bg-[#002FA7] hover:bg-[#002585] text-white px-4 py-1.5 text-[10px] tracking-wider uppercase font-mono disabled:opacity-40">
              {creating ? <Loader2 size={11} className="animate-spin" /> : <GitPullRequest size={11} />} Create PR
            </button>
            <button onClick={() => setShowCreate(false)} className="text-[#737373] hover:text-white text-[10px] font-mono px-2">Cancel</button>
          </div>
        </div>
      )}

      {loading ? (
        <div className="flex items-center gap-2 text-xs text-[#737373]"><Loader2 size={12} className="animate-spin" /> Loading…</div>
      ) : pulls.length === 0 ? (
        <div className="text-[11px] text-[#737373]">No open pull requests.</div>
      ) : (
        <div className="space-y-1.5">
          {pulls.map(pr => (
            <a key={pr.number} href={pr.html_url} target="_blank" rel="noopener noreferrer"
              className="flex items-start gap-2 border border-white/10 bg-[#141414] hover:border-[#002FA7] p-2.5 transition-all">
              <GitPullRequest size={12} className="text-green-500 mt-0.5 shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-[11px] text-white truncate">{pr.title}</div>
                <div className="text-[9px] text-[#737373] font-mono mt-0.5">
                  #{pr.number} · {pr.user} · {pr.head} → {pr.base}
                </div>
              </div>
              <ExternalLink size={10} className="text-[#737373] shrink-0 mt-1" />
            </a>
          ))}
        </div>
      )}
    </div>
  );
}

// ─── Main GitHubPage ──────────────────────────────────────────────────────────
export default function GitHubPage() {
  const [ghStatus, setGhStatus] = useState(null);
  const [selectedRepo, setSelectedRepo] = useState(null);
  const [branch, setBranch] = useState('');
  const [branches, setBranches] = useState([]);
  const [selectedFile, setSelectedFile] = useState(null);
  const [activeTab, setActiveTab] = useState('files'); // 'files' | 'pulls'
  const [commits, setCommits] = useState([]);

  useEffect(() => {
    githubStatus()
      .then(({ data }) => setGhStatus(data))
      .catch(() => setGhStatus({ connected: false }));
  }, []);

  const handleSelectRepo = async (repo) => {
    setSelectedRepo(repo);
    setSelectedFile(null);
    setBranch(repo.default_branch);
    setCommits([]);
    try {
      const { data } = await listGithubBranches(repo.owner, repo.name);
      setBranches(data.branches || []);
    } catch { }
  };

  const handleCommitted = (filePath, msg) => {
    setCommits(prev => [
      { path: filePath, message: msg, time: new Date().toLocaleTimeString() },
      ...prev.slice(0, 9),
    ]);
  };

  if (!ghStatus) {
    return (
      <div className="flex items-center justify-center h-full">
        <Loader2 size={20} className="animate-spin text-[#737373]" />
      </div>
    );
  }

  if (!ghStatus.connected) {
    return (
      <div className="p-5 lg:p-7 max-w-2xl">
        <div className="mb-6">
          <h1 className="text-2xl font-bold tracking-tighter flex items-center gap-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
            <Github size={22} /> GitHub
          </h1>
          <p className="text-xs text-[#737373] mt-0.5">Connect a GitHub Personal Access Token to browse and edit repos</p>
        </div>
        <div className="border border-white/10 bg-[#141414] p-6 text-center space-y-3">
          <Github size={32} className="mx-auto text-[#737373]" />
          <div className="text-sm text-white">GitHub not connected</div>
          <p className="text-xs text-[#737373] max-w-sm mx-auto">
            Go to <strong className="text-white">Settings</strong> and paste a GitHub Personal Access Token with <code className="text-[#002FA7]">repo</code> scope to get started.
          </p>
          <a href="/settings" className="inline-flex items-center gap-1.5 bg-[#002FA7] hover:bg-[#002585] text-white px-5 py-2 text-[10px] tracking-wider uppercase font-mono transition-colors">
            Go to Settings
          </a>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header */}
      <div className="px-5 py-3 border-b border-white/10 flex items-center gap-3 shrink-0">
        {selectedRepo ? (
          <button onClick={() => { setSelectedRepo(null); setSelectedFile(null); }}
            className="flex items-center gap-1.5 text-[#737373] hover:text-white transition-colors">
            <ArrowLeft size={14} />
          </button>
        ) : null}
        <Github size={15} className="text-[#002FA7]" />
        <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">
          {selectedRepo ? selectedRepo.full_name : 'GitHub Repositories'}
        </span>
        {selectedRepo && (
          <>
            <div className="ml-3 flex items-center gap-1.5">
              <GitBranch size={12} className="text-[#737373]" />
              <select
                value={branch}
                onChange={e => { setBranch(e.target.value); setSelectedFile(null); }}
                className="bg-[#0A0A0A] border border-white/10 text-[10px] text-white font-mono px-2 py-1 outline-none focus:border-[#002FA7]"
              >
                {branches.map(b => <option key={b} value={b}>{b}</option>)}
              </select>
            </div>
            <a href={`https://github.com/${selectedRepo.full_name}`} target="_blank" rel="noopener noreferrer"
              className="ml-2 flex items-center gap-1 text-[10px] text-[#737373] hover:text-[#002FA7] font-mono transition-colors">
              <ExternalLink size={10} /> GitHub
            </a>
          </>
        )}
        <div className="ml-auto flex items-center gap-2">
          <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
          <span className="text-[10px] text-[#737373] font-mono">@{ghStatus.login}</span>
        </div>
      </div>

      {/* Body */}
      {!selectedRepo ? (
        <div className="flex-1 overflow-y-auto p-5">
          <RepoSelector onSelect={handleSelectRepo} />
        </div>
      ) : (
        <div className="flex-1 flex overflow-hidden">
          {/* Left: file tree + tabs */}
          <div className="w-56 border-r border-white/10 flex flex-col shrink-0">
            <div className="flex border-b border-white/10">
              <button
                onClick={() => setActiveTab('files')}
                className={`flex-1 flex items-center justify-center gap-1 py-2 text-[10px] font-mono tracking-wider uppercase transition-colors ${activeTab === 'files' ? 'text-white border-b-2 border-[#002FA7]' : 'text-[#737373] hover:text-[#A0A0A0]'}`}
              >
                <FolderOpen size={11} /> Files
              </button>
              <button
                onClick={() => setActiveTab('pulls')}
                className={`flex-1 flex items-center justify-center gap-1 py-2 text-[10px] font-mono tracking-wider uppercase transition-colors ${activeTab === 'pulls' ? 'text-white border-b-2 border-[#002FA7]' : 'text-[#737373] hover:text-[#A0A0A0]'}`}
              >
                <GitPullRequest size={11} /> PRs
              </button>
            </div>

            <div className="flex-1 overflow-hidden">
              {activeTab === 'files' ? (
                <FileTree
                  owner={selectedRepo.owner}
                  repo={selectedRepo.name}
                  ref={branch}
                  onFileSelect={setSelectedFile}
                />
              ) : (
                <div className="p-3 overflow-y-auto h-full">
                  <PRPanel
                    owner={selectedRepo.owner}
                    repo={selectedRepo.name}
                    defaultBranch={selectedRepo.default_branch}
                  />
                </div>
              )}
            </div>

            {/* Recent commits */}
            {commits.length > 0 && (
              <div className="border-t border-white/10 p-2 shrink-0">
                <div className="text-[9px] tracking-[0.15em] uppercase text-[#737373] font-mono mb-1.5">Recent Commits</div>
                {commits.slice(0, 3).map((c, i) => (
                  <div key={i} className="flex items-start gap-1.5 py-1">
                    <GitCommit size={9} className="text-green-500 mt-0.5 shrink-0" />
                    <div className="min-w-0">
                      <div className="text-[9px] text-white font-mono truncate">{c.message}</div>
                      <div className="text-[8px] text-[#737373] font-mono">{c.path} · {c.time}</div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* Right: editor */}
          <div className="flex-1 flex flex-col overflow-hidden bg-[#0A0A0A]">
            {selectedFile ? (
              <FileEditor
                owner={selectedRepo.owner}
                repo={selectedRepo.name}
                branch={branch}
                filePath={selectedFile}
                onCommitted={handleCommitted}
              />
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center p-8 animate-fade-in">
                <FolderOpen size={36} className="text-[#002FA7] mb-4" />
                <h3 className="text-base font-bold tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
                  {selectedRepo.name}
                </h3>
                <p className="text-xs text-[#737373] max-w-xs leading-relaxed">
                  {selectedRepo.description || 'Select a file from the tree to view and edit it.'}
                </p>
                <div className="mt-4 grid grid-cols-2 gap-2 text-[10px] font-mono text-[#737373]">
                  <div className="border border-white/10 p-2"><span className="text-[#A0A0A0]">Branch: </span>{branch}</div>
                  <div className="border border-white/10 p-2"><span className="text-[#A0A0A0]">Lang: </span>{selectedRepo.language || '—'}</div>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
