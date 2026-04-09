import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { fmtErr } from '../api';
import { Lock, ArrowRight, AlertCircle } from 'lucide-react';

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
      {/* Background image */}
      <div
        className="absolute inset-0 opacity-20"
        style={{
          backgroundImage: `url(https://static.prod-images.emergentagent.com/jobs/6bf7aa0e-927a-4851-95e4-78f9c580e21a/images/37ee5765c3fcd28b5e7cefcd7091eb0b55fcc87a2bfd97123b3f7c4d496fd4db.png)`,
          backgroundSize: 'cover',
          backgroundPosition: 'center',
        }}
      />
      <div className="absolute inset-0 bg-black/70" />

      {/* Left branding panel */}
      <div className="hidden lg:flex flex-col justify-between w-1/2 p-12 relative z-10">
        <div>
          <div className="flex items-center gap-3 mb-2">
            <div className="w-2 h-2 bg-[#002FA7]" />
            <span className="text-xs tracking-[0.25em] uppercase text-[#737373] font-mono">System v1.0</span>
          </div>
          <h1 className="font-heading text-6xl font-bold tracking-tighter leading-none mt-8" style={{ fontFamily: 'Chivo, sans-serif' }}>
            LLM<br />WIKI
          </h1>
          <p className="text-[#737373] mt-6 text-sm leading-relaxed max-w-md font-mono">
            Persistent, compounding knowledge base maintained by AI agents.
            Self-hosted. Open source. No paid infrastructure required.
          </p>
        </div>
        <div className="text-[#737373] text-xs font-mono border-t border-white/10 pt-4">
          <span className="text-[#A0A0A0]">ARCHITECTURE</span> &mdash; Karpathy's LLM Wiki Pattern<br />
          <span className="text-[#A0A0A0]">RUNTIME</span> &mdash; Ollama + OpenAI Compatible<br />
          <span className="text-[#A0A0A0]">STORAGE</span> &mdash; MongoDB
        </div>
      </div>

      {/* Right login panel */}
      <div className="flex-1 flex items-center justify-center relative z-10 p-8">
        <div className="w-full max-w-sm animate-fade-in">
          <div className="border border-white/10 bg-[#141414]/90 backdrop-blur-sm">
            {/* Header */}
            <div className="border-b border-white/10 px-6 py-4 flex items-center gap-3">
              <Lock size={14} className="text-[#002FA7]" />
              <span className="text-xs tracking-[0.2em] uppercase text-[#A0A0A0] font-mono font-bold">
                Authentication Required
              </span>
            </div>

            <form onSubmit={handleSubmit} className="p-6 space-y-5" data-testid="login-form">
              {/* Visible only on mobile */}
              <div className="lg:hidden mb-4">
                <h2 className="text-2xl font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>LLM WIKI</h2>
                <p className="text-xs text-[#737373] mt-1">Agent Dashboard</p>
              </div>

              {error && (
                <div className="flex items-center gap-2 text-[#FF3333] text-xs bg-[#FF3333]/10 border border-[#FF3333]/20 p-3" data-testid="login-error">
                  <AlertCircle size={14} />
                  <span>{error}</span>
                </div>
              )}

              <div>
                <label className="block text-xs tracking-[0.15em] uppercase text-[#737373] mb-2 font-mono">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  className="w-full bg-[#0A0A0A] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7] transition-colors"
                  placeholder="admin@llmwiki.local"
                  required
                  data-testid="login-email-input"
                />
              </div>

              <div>
                <label className="block text-xs tracking-[0.15em] uppercase text-[#737373] mb-2 font-mono">Password</label>
                <input
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  className="w-full bg-[#0A0A0A] border border-white/10 px-4 py-3 text-sm text-white font-mono outline-none focus:border-[#002FA7] transition-colors"
                  placeholder="Enter password"
                  required
                  data-testid="login-password-input"
                />
              </div>

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-[#002FA7] hover:bg-[#002585] text-white py-3 text-sm font-mono tracking-wider uppercase flex items-center justify-center gap-2 transition-colors disabled:opacity-50"
                data-testid="login-submit-button"
              >
                {loading ? (
                  <span className="animate-pulse-slow">AUTHENTICATING...</span>
                ) : (
                  <>ACCESS DASHBOARD <ArrowRight size={14} /></>
                )}
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
