import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { fmtErr } from '../api';
import { Lock, ArrowRight, AlertCircle } from 'lucide-react';

const HERO_IMG = 'https://static.prod-images.emergentagent.com/jobs/6bf7aa0e-927a-4851-95e4-78f9c580e21a/images/6d1e1a17e7631bc5783700099b8bd99b3256c85b7d78807597ae8cea63ae6ad4.png';

export default function LoginPage() {
  const { login } = useAuth();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e) => {
    e.preventDefault();
    setError('');
    setLoading(true);
    try {
      await login(email, password);
    } catch (err) {
      setError(fmtErr(err?.response?.data?.detail));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="h-screen w-screen flex bg-[#0A0A0A] relative overflow-hidden" data-testid="login-page">
      <div className="absolute inset-0 opacity-25" style={{ backgroundImage: `url(${HERO_IMG})`, backgroundSize: 'cover', backgroundPosition: 'center' }} />
      <div className="absolute inset-0 bg-black/70" />

      {/* Left branding */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 p-12 relative z-10">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-2 h-2 bg-[#002FA7]" />
            <span className="text-xs tracking-[0.25em] uppercase text-[#737373] font-mono">Platform v2.0</span>
          </div>
          <h1 className="text-6xl font-bold tracking-tighter leading-none mt-8" style={{ fontFamily: 'Chivo, sans-serif' }}>
            LLM<br />RELAY
          </h1>
          <p className="text-[#A0A0A0] mt-4 text-base leading-relaxed max-w-lg" style={{ fontFamily: 'Chivo, sans-serif', fontWeight: 300 }}>
            Route, run, and control LLMs on your own hardware, not someone else's meter.
          </p>
          <p className="text-[#737373] mt-3 text-sm leading-relaxed max-w-md font-mono">
            Self-hosted. Open source. Fully autonomous.
            No paid infrastructure required.
          </p>
        </div>
        <div className="text-[#737373] text-xs font-mono border-t border-white/10 pt-4">
          <span className="text-[#A0A0A0]">RUNTIME</span> &mdash; Ollama + OpenAI Compatible + HuggingFace<br />
          <span className="text-[#A0A0A0]">STORAGE</span> &mdash; MongoDB &bull; <span className="text-[#A0A0A0]">OBSERVABILITY</span> &mdash; Langfuse<br />
          <span className="text-[#A0A0A0]">ACCESS</span> &mdash; ngrok / Cloudflare Tunnel
        </div>
      </div>

      {/* Right login */}
      <div className="flex-1 flex items-center justify-center relative z-10 p-8">
        <div className="w-full max-w-sm animate-fade-in">
          <div className="border border-white/10 bg-[#141414]/90 backdrop-blur-sm">
            <div className="border-b border-white/10 px-6 py-4 flex items-center gap-3">
              <Lock size={14} className="text-[#002FA7]" />
              <span className="text-xs tracking-[0.2em] uppercase text-[#A0A0A0] font-mono font-bold">Authentication Required</span>
            </div>
            <form onSubmit={handleSubmit} className="p-6 space-y-5" data-testid="login-form">
              <div className="lg:hidden mb-4">
                <h2 className="text-2xl font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>LLM RELAY</h2>
                <p className="text-xs text-[#737373] mt-1">Route, run, and control LLMs.</p>
              </div>
              {error && (
                <div className="flex items-center gap-2 text-[#FF3333] text-xs bg-[#FF3333]/10 border border-[#FF3333]/20 p-3" data-testid="login-error">
                  <AlertCircle size={14} /><span>{error}</span>
                </div>
              )}
              <div>
                <label className="block text-xs tracking-[0.15em] uppercase text-[#737373] mb-2 font-mono">Email</label>
                <input type="email" value={email} onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-[#0A0A0A] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7] transition-colors"
                  placeholder="admin@llmrelay.local" required data-testid="login-email-input" />
              </div>
              <div>
                <label className="block text-xs tracking-[0.15em] uppercase text-[#737373] mb-2 font-mono">Password</label>
                <input type="password" value={password} onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#0A0A0A] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7] transition-colors"
                  placeholder="Enter password" required data-testid="login-password-input" />
              </div>
              <button type="submit" disabled={loading}
                className="w-full bg-[#002FA7] hover:bg-[#002585] text-white py-3 text-sm font-mono tracking-wider uppercase flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                data-testid="login-submit-button">
                {loading ? <span className="animate-pulse-slow">AUTHENTICATING...</span> : <><span>ACCESS RELAY</span> <ArrowRight size={14} /></>}
              </button>
            </form>
            <div className="border-t border-white/10 px-6 py-3 text-xs text-[#737373] font-mono">
              Default: admin@llmwiki.local
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
