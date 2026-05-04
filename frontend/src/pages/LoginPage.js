import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { fmtErr, getBackendUrl } from '../api';
import { Lock, ArrowRight, AlertCircle, Github, CheckCircle, Bot, Database } from 'lucide-react';

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
      <label className="block text-[0.85rem] font-semibold tracking-widest uppercase text-[var(--text-muted)] mb-2">{label}</label>
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
      className="w-full bg-[var(--bg-surface)]/50 border border-[var(--border)] rounded-xl px-4 py-3 text-[0.9rem] text-[var(--text-primary)] placeholder-[var(--text-muted)] outline-none focus:border-[var(--accent)] focus:ring-2 focus:ring-[var(--accent)]/20 transition-all duration-200 min-h-[12px]"
    />
  );
}

export default function LoginPage() {
  const { login } = useAuth();
  const backendUrl = getBackendUrl();
  const hasBackendConfig = Boolean(backendUrl);
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
    <div className="min-h-[100dvh] w-full flex bg-[var(--bg-base)] relative overflow-hidden" data-testid="login-page">
      {/* Background gradient */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] w-[600px] h-[600px] rounded-full bg-[var(--accent)]/8 blur-[120px]" />
        <div className="absolute bottom-[-10%] right-[-5%] w-[400px] h-[400px] rounded-full bg-[var(--accent)]/5 blur-[100px]" />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(0,102,255,0.04),transparent_60%)]" />
        <div
          className="absolute inset-0 opacity-[0.015]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='32' height='32' viewBox='0 0 32 32' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 0h1v1H0V0zm16 16h1v1h-1v-1z' fill='%23ffffff' fill-opacity='1'/%3E%3C/svg%3E")`,
            backgroundSize: '32px 32px',
          }}
        />
      </div>

      {/* Left — branding panel (desktop only) */}
      <div className="hidden lg:flex flex-col justify-between w-5/12 xl:w-1/2 p-6 xl:p-8 relative z-10">
        <div className="animate-fade-in">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-9 h-9 rounded-xl flex items-center justify-center"
              style={{ background: 'var(--accent)', boxShadow: '0 2px 12px rgba(0,102,255,0.3)' }}>
              <Lock size={20} className="text-white" />
            </div>
            <div>
              <div className="text-[1.25rem] font-bold text-[var(--text-primary)] tracking-tight"
                style={{ fontFamily: 'var(--font-main)' }}>LLM Relay</div>
              <div className="text-[0.85rem] text-[var(--text-muted)] font-mono leading-none mt-0.5">v3.1 · control plane</div>
            </div>
          </div>

          {/* Features */}
          <div className="space-y-4">
            <div className="flex items-center gap-3">
              <CheckCircle size={16} className="flex-shrink-0 text-[var(--success)]" />
              <div className="flex-1">
                <h3 className="text-[1rem] font-semibold text-[var(--text-primary)] mb-1">Enterprise Security</h3>
                <p className="text-[0.85rem] text-[var(--text-tertiary)]">Local-first architecture keeps your data private</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Bot size={16} className="flex-shrink-0 text-[var(--accent)]" />
              <div className="flex-1">
                <h3 className="text-[1rem] font-semibold text-[var(--text-primary)] mb-1">Multi-Agent Orchestration</h3>
                <p className="text-[0.85rem] text-[var(--text-tertiary)]">Coordinate teams of AI agents for complex tasks</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Database size={16} className="flex-shrink-0 text-[var(--role-power-user)]" />
              <div className="flex-1">
                <h3 className="text-[1rem] font-semibold text-[var(--text-primary)] mb-1">Knowledge Integration</h3>
                <p className="text-[0.85rem] text-[var(--text-tertiary)]">Connect agents to your documents and data sources</p>
              </div>
            </div>
          </div>
        </div>

        {/* Footer hint */}
        <div className="border-t border-[var(--border)]/8 px-6 py-4 bg-[var(--bg-base)]/5">
          <p className="text-[0.8rem] text-[var(--text-muted)] font-mono">
            Default: <span className="text-[var(--text-tertiary)]">admin@llmrelay.local</span>
          </p>
        </div>
      </div>

      {/* Right — form panel */}
      <div className="flex-1 w-full lg:w-7/12 xl:w-1/2 px-6 xl:px-8 py-12 relative z-10">
        <div className="w-full max-w-xs mx-auto space-y-6">
          <div className="space-y-4">
            <h2 className="text-[1.5rem] font-bold tracking-tight text-[var(--text-primary)]"
              style={{ fontFamily: 'var(--font-main)' }}>Sign in to Control Plane</h2>
            <p className="text-[0.9rem] text-[var(--text-tertiary)]">
              Access your AI agent orchestration system
            </p>
          </div>

          <form onSubmit={handleSubmit} className="space-y-4">
            <FieldGroup label="Email">
              <TextInput
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                placeholder="admin@llmrelay.local"
                required
                testId="email-input"
              />
            </FieldGroup>
            <FieldGroup label="Password">
              <TextInput
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                placeholder="••••••••"
                required
                testId="password-input"
              />
            </FieldGroup>

            {error && (
              <div className="bg-[var(--danger)]/10 border border-[var(--danger)]/20 rounded-xl p-4">
                <AlertCircle size={16} className="mb-2 text-[var(--danger)]" />
                <p className="text-[0.9rem] text-[var(--text-primary)]">{error}</p>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full flex items-center justify-center gap-3 px-5 py-3 text-[0.95rem] font-medium bg-[var(--accent)] text-[var(--text-primary)] hover:bg-[var(--accent-hover)] transition-all duration-200 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? (
                <>
                  <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin"
                    style={{ borderColor: 'var(--text-primary)' }} />
                  <span className="ml-2">Signing in...</span>
                </>
              ) : (
                <>
                  <Lock size={18} />
                  <span>Sign in</span>
                </>
              )}
            </button>
          </form>

          {!hasBackendConfig && (
            <p className="text-[0.85rem] text-[var(--text-tertiary)] leading-relaxed text-center">
              Need to connect a backend first?{' '}
              <Link to="/bootstrap" className="text-[var(--accent)] hover:text-[var(--accent-hover)] underline underline-offset-2 transition-colors duration-200">
                Open the setup wizard
              </Link>
              .
            </p>
          )}
        </div>
      </div>
    </div>
  );
}
