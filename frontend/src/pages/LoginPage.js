import React, { useState } from 'react';
import { useAuth } from '../AuthContext';
import { fmtErr } from '../api';
import { Lock, ArrowRight, AlertCircle, Github } from 'lucide-react';

const GoogleIcon = () => (
  <svg viewBox="0 0 24 24" width="15" height="15" fill="none">
    <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z" fill="#4285F4"/>
    <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
    <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z" fill="#FBBC05"/>
    <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
  </svg>
);

function FieldGroup({ label, children }) {
  return (
    <div>
      <label className="block text-[11px] font-semibold tracking-widest uppercase text-[#555555] mb-2">{label}</label>
      {children}
    </div>
  );
}

function TextInput({ type, value, onChange, placeholder, required, testId }) {
  return (
    <input
      type={type}
      value={value}
      onChange={onChange}
      placeholder={placeholder}
      required={required}
      data-testid={testId}
      className="w-full bg-black/40 border border-white/10 rounded-md px-4 py-3 text-sm text-white placeholder-[#444] outline-none focus:border-[#002FA7] focus:ring-1 focus:ring-[#002FA7]/30 transition-all min-h-[46px]"
    />
  );
}

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
    <div className="min-h-[100dvh] w-full flex bg-[#0F0F13] relative overflow-hidden" data-testid="login-page">
      {/* Background gradient */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-[#002FA7]/8 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-5%] w-[400px] h-[400px] rounded-full bg-[#002FA7]/5 blur-[100px]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(0,47,167,0.04),transparent_60%)]" />
        <div
          className="absolute inset-0 opacity-[0.015]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='32' height='32' viewBox='0 0 32 32' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 0h1v1H0V0zm16 16h1v1h-1v-1z' fill='%23ffffff' fill-opacity='1'/%3E%3C/svg%3E")`,
            backgroundSize: '32px 32px',
          }}
        />
      </div>

      {/* Left — branding panel (desktop only) */}
      <div className="hidden lg:flex flex-col justify-between w-5/12 xl:w-1/2 p-12 xl:p-16 relative z-10">
        <div className="animate-fade-in">
          <div className="flex items-center gap-2.5 mb-12">
            <div className="w-2 h-2 rounded-sm bg-[#002FA7]" />
            <span className="text-[11px] tracking-[0.3em] uppercase text-[#555555] font-mono font-medium">Platform v3.1</span>
          </div>
          <h1 className="text-[80px] xl:text-[96px] font-bold tracking-[-0.04em] leading-[0.9] text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>
            LLM<br />RELAY
          </h1>
          <p className="text-[#6A6A6A] mt-6 text-lg leading-relaxed max-w-sm font-light" style={{ fontFamily: 'Outfit, sans-serif' }}>
            Route, run, and control LLMs on your own hardware — not someone else's meter.
          </p>
          <div className="flex flex-wrap gap-2 mt-8">
            {['Self-hosted', 'Open source', 'OpenAI-compatible'].map(tag => (
              <span key={tag} className="px-3 py-1 border border-white/8 rounded-full text-[11px] text-[#555555] font-mono tracking-wide">
                {tag}
              </span>
            ))}
          </div>
        </div>

        <div className="text-[11px] text-[#333333] font-mono space-y-1 border-t border-white/5 pt-6 stagger-3">
          <div><span className="text-[#555555]">RUNTIME</span> — Ollama · OpenAI Compatible · HuggingFace</div>
          <div><span className="text-[#555555]">STORAGE</span> — MongoDB &nbsp;·&nbsp; <span className="text-[#555555]">OBS</span> — Langfuse</div>
          <div><span className="text-[#555555]">ACCESS</span> — ngrok / Cloudflare Tunnel</div>
        </div>
      </div>

      {/* Divider (desktop) */}
      <div className="hidden lg:block w-px bg-white/5 self-stretch my-12" />

      {/* Right — login card */}
      <div className="flex-1 flex items-center justify-center relative z-10 p-5 sm:p-8">
        <div className="w-full max-w-[400px] animate-fade-in">

          {/* Mobile header */}
          <div className="lg:hidden text-center mb-8">
            <div className="inline-flex items-center gap-2 mb-4">
              <div className="w-2 h-2 rounded-sm bg-[#002FA7]" />
              <span className="text-[10px] tracking-[0.3em] uppercase text-[#555555] font-mono">Platform v3.1</span>
            </div>
            <h1 className="text-4xl font-bold tracking-[-0.03em] text-white" style={{ fontFamily: 'Outfit, sans-serif' }}>LLM Relay</h1>
            <p className="text-sm text-[#555555] mt-2">Route, run, and control LLMs.</p>
          </div>

          {/* Card */}
          <div className="bg-[#141418] border border-white/8 rounded-xl overflow-hidden shadow-[0_24px_64px_rgba(0,0,0,0.6)]">

            {/* Card header */}
            <div className="px-6 py-4 border-b border-white/6 flex items-center gap-2.5">
              <div className="w-7 h-7 rounded-md bg-[#002FA7]/15 border border-[#002FA7]/20 flex items-center justify-center">
                <Lock size={13} className="text-[#002FA7]" />
              </div>
              <span className="text-xs font-semibold tracking-[0.15em] uppercase text-[#666666]">Authenticate</span>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="p-6 space-y-4" data-testid="login-form">
              {error && (
                <div className="flex items-start gap-2.5 text-[#FF3333] text-sm bg-[#FF3333]/8 border border-[#FF3333]/20 rounded-lg p-3.5 animate-scale-in" data-testid="login-error">
                  <AlertCircle size={15} className="shrink-0 mt-0.5" />
                  <span className="leading-snug">{error}</span>
                </div>
              )}

              <FieldGroup label="Email">
                <TextInput
                  type="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="admin@llmrelay.local"
                  required
                  testId="login-email-input"
                />
              </FieldGroup>

              <FieldGroup label="Password">
                <TextInput
                  type="password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  required
                  testId="login-password-input"
                />
              </FieldGroup>

              <button
                type="submit"
                disabled={loading}
                className="w-full mt-2 bg-[#002FA7] hover:bg-[#0038CC] active:scale-[0.98] text-white rounded-md py-3 px-4 text-sm font-semibold flex items-center justify-center gap-2 transition-all duration-150 disabled:opacity-50 disabled:cursor-not-allowed min-h-[46px] shadow-[0_4px_12px_rgba(0,47,167,0.4)]"
                data-testid="login-submit-button"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-white/40 border-t-white rounded-full animate-spin" />
                    <span>Authenticating…</span>
                  </>
                ) : (
                  <>
                    <span>Sign in to Relay</span>
                    <ArrowRight size={15} />
                  </>
                )}
              </button>
            </form>

            {/* Social login */}
            <div className="px-6 pb-6 space-y-4">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-white/6" />
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-[#111111] px-3 text-[11px] uppercase tracking-widest text-[#333333] font-mono">or</span>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-2.5">
                <a
                  href={`${process.env.REACT_APP_BACKEND_URL || ''}/api/auth/github/login`}
                  className="flex items-center justify-center gap-2 bg-white/4 hover:bg-white/8 border border-white/8 hover:border-white/14 rounded-md py-2.5 text-[12px] font-medium text-[#A0A0A0] hover:text-white transition-all min-h-[42px]"
                >
                  <Github size={14} /> GitHub
                </a>
                <a
                  href={`${process.env.REACT_APP_BACKEND_URL || ''}/api/auth/google/login`}
                  className="flex items-center justify-center gap-2 bg-white/4 hover:bg-white/8 border border-white/8 hover:border-white/14 rounded-md py-2.5 text-[12px] font-medium text-[#A0A0A0] hover:text-white transition-all min-h-[42px]"
                >
                  <GoogleIcon /> Google
                </a>
              </div>
            </div>

            {/* Footer hint */}
            <div className="border-t border-white/5 px-6 py-3 bg-white/[0.015]">
              <p className="text-[11px] text-[#444444] font-mono">
                Default: <span className="text-[#666666]">admin@llmrelay.local</span>
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
