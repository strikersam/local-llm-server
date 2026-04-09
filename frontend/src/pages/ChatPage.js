import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { chatSend, listSessions, getSession, deleteSession } from '../api';
import { Send, Plus, Trash2, MessageSquare, Bot, User, Loader2 } from 'lucide-react';

export default function ChatPage() {
  const { sessionId: paramSid } = useParams();
  const navigate = useNavigate();
  const [sessions, setSessions] = useState([]);
  const [currentSession, setCurrentSession] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const [sessionId, setSessionId] = useState(paramSid || null);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  useEffect(() => {
    loadSessions();
  }, []);

  useEffect(() => {
    if (paramSid) {
      loadSession(paramSid);
    }
  }, [paramSid]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const loadSessions = async () => {
    try {
      const { data } = await listSessions();
      setSessions(data.sessions || []);
    } catch {}
  };

  const loadSession = async (sid) => {
    try {
      const { data } = await getSession(sid);
      setSessionId(sid);
      setCurrentSession(data);
      setMessages(data.messages || []);
    } catch {}
  };

  const startNew = () => {
    setSessionId(null);
    setCurrentSession(null);
    setMessages([]);
    navigate('/chat');
    inputRef.current?.focus();
  };

  const handleSend = async () => {
    if (!input.trim() || sending) return;
    const content = input.trim();
    setInput('');
    setSending(true);
    setMessages(prev => [...prev, { role: 'user', content }]);

    try {
      const { data } = await chatSend(content, sessionId);
      setSessionId(data.session_id);
      setMessages(prev => [...prev, { role: 'assistant', content: data.response }]);
      if (!sessionId) {
        navigate(`/chat/${data.session_id}`, { replace: true });
      }
      loadSessions();
    } catch (err) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: `Error: ${err?.response?.data?.detail || 'Failed to get response. Check LLM provider.'}`
      }]);
    } finally {
      setSending(false);
    }
  };

  const handleDelete = async (sid, e) => {
    e.stopPropagation();
    await deleteSession(sid);
    if (sessionId === sid) startNew();
    loadSessions();
  };

  const handleKeyDown = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="h-full flex" data-testid="chat-page">
      {/* Sessions sidebar */}
      <div className="w-64 border-r border-white/10 bg-[#141414] flex flex-col shrink-0 hidden md:flex">
        <div className="p-4 border-b border-white/10">
          <button
            onClick={startNew}
            className="w-full flex items-center justify-center gap-2 bg-[#002FA7] hover:bg-[#002585] text-white py-2.5 text-xs tracking-wider uppercase font-mono transition-colors"
            data-testid="new-chat-button"
          >
            <Plus size={14} /> NEW SESSION
          </button>
        </div>
        <div className="flex-1 overflow-y-auto divide-y divide-white/5">
          {sessions.map(s => (
            <button
              key={s._id}
              onClick={() => { navigate(`/chat/${s._id}`); loadSession(s._id); }}
              className={`w-full flex items-center gap-2 px-4 py-3 text-left hover:bg-white/[0.03] transition-colors group
                ${sessionId === s._id ? 'bg-white/5 border-l-2 border-[#002FA7]' : 'border-l-2 border-transparent'}`}
              data-testid={`session-${s._id}`}
            >
              <MessageSquare size={13} className="text-[#737373] shrink-0" />
              <div className="flex-1 min-w-0">
                <div className="text-xs text-[#A0A0A0] truncate">{s.title || 'Untitled'}</div>
                <div className="text-[10px] text-[#737373]">{s.updated_at?.split('T')[0]}</div>
              </div>
              <button
                onClick={(e) => handleDelete(s._id, e)}
                className="opacity-0 group-hover:opacity-100 p-1 hover:text-[#FF3333] text-[#737373] transition-all"
                data-testid={`delete-session-${s._id}`}
              >
                <Trash2 size={12} />
              </button>
            </button>
          ))}
          {sessions.length === 0 && (
            <div className="p-4 text-center text-xs text-[#737373]">No sessions yet</div>
          )}
        </div>
      </div>

      {/* Chat area */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="px-6 py-3 border-b border-white/10 flex items-center gap-3">
          <Bot size={16} className="text-[#002FA7]" />
          <span className="text-xs tracking-[0.15em] uppercase text-[#A0A0A0] font-mono font-bold">
            {currentSession ? currentSession.title?.slice(0, 40) : 'New Agent Session'}
          </span>
          <div className="ml-auto flex items-center gap-2">
            <div className="w-1.5 h-1.5 bg-green-500 rounded-full" />
            <span className="text-[10px] text-[#737373] font-mono">WIKI AGENT ACTIVE</span>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="h-full flex flex-col items-center justify-center text-center animate-fade-in">
              <Bot size={40} className="text-[#002FA7] mb-4" />
              <h3 className="text-lg font-bold tracking-tight mb-2" style={{ fontFamily: 'Chivo, sans-serif' }}>
                Wiki Agent Ready
              </h3>
              <p className="text-xs text-[#737373] max-w-md leading-relaxed">
                Ask questions, request wiki page creation, analyze sources, or run wiki health checks.
                The agent has context of your entire wiki knowledge base.
              </p>
              <div className="mt-6 grid grid-cols-2 gap-2">
                {['What\'s in my wiki?', 'Create a new page about...', 'Analyze this source...', 'Run wiki lint'].map((prompt, i) => (
                  <button
                    key={i}
                    onClick={() => { setInput(prompt); inputRef.current?.focus(); }}
                    className="text-[10px] text-[#A0A0A0] border border-white/10 px-3 py-2 hover:border-[#002FA7] hover:text-white transition-all font-mono"
                    data-testid={`quick-prompt-${i}`}
                  >
                    {prompt}
                  </button>
                ))}
              </div>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className={`flex gap-3 ${m.role === 'user' ? 'justify-end' : ''} animate-fade-in`}>
              {m.role === 'assistant' && (
                <div className="w-7 h-7 bg-[#002FA7] flex items-center justify-center shrink-0 mt-1">
                  <Bot size={14} />
                </div>
              )}
              <div className={`max-w-[70%] ${
                m.role === 'user'
                  ? 'bg-[#002FA7]/20 border border-[#002FA7]/30'
                  : 'bg-[#1A1A1A] border border-white/10'
              } px-4 py-3`}>
                {m.role === 'assistant' ? (
                  <div className="wiki-content text-xs text-[#A0A0A0]">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>{m.content}</ReactMarkdown>
                  </div>
                ) : (
                  <p className="text-xs text-white whitespace-pre-wrap">{m.content}</p>
                )}
              </div>
              {m.role === 'user' && (
                <div className="w-7 h-7 bg-white/10 flex items-center justify-center shrink-0 mt-1">
                  <User size={14} className="text-[#A0A0A0]" />
                </div>
              )}
            </div>
          ))}

          {sending && (
            <div className="flex gap-3 animate-fade-in">
              <div className="w-7 h-7 bg-[#002FA7] flex items-center justify-center shrink-0">
                <Bot size={14} />
              </div>
              <div className="bg-[#1A1A1A] border border-white/10 px-4 py-3">
                <Loader2 size={14} className="animate-spin text-[#002FA7]" />
              </div>
            </div>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* Input */}
        <div className="border-t border-white/10 p-4">
          <div className="flex gap-3 items-end">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Message the Wiki Agent..."
              rows={1}
              className="flex-1 bg-[#141414] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7] resize-none transition-colors"
              data-testid="chat-input"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || sending}
              className="bg-[#002FA7] hover:bg-[#002585] text-white p-3 transition-colors disabled:opacity-30 disabled:cursor-not-allowed shrink-0"
              data-testid="chat-send-button"
            >
              <Send size={16} />
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
