import React, { useState } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import { fmtErr, getBackendUrl } from '../api';
import { Lock, AlertCircle, GitFork as Github, CheckCircle, Bot, Database } from 'lucide-react';

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
      className="app-input w-full px-4 py-3 text-[0.95rem] text-[var(--text-primary)] placeholder-[var(--text-muted)] min-h-[3.25rem]"
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
    <main className="app-shell min-h-[100dvh] w-full flex flex-col lg:flex-row relative overflow-hidden" data-testid="login-page">
      {/* Background gradient */}
      <div className="absolute inset-0 pointer-events-none">
        <div className="absolute top-[-20%] left-[-10%] h-[32rem] w-[32rem] rounded-full blur-[130px]" style={{ background: 'rgba(93,162,255,0.16)' }} />
        <div className="absolute bottom-[-10%] right-[-5%] h-[24rem] w-[24rem] rounded-full blur-[120px]" style={{ background: 'rgba(93,162,255,0.1)' }} />
        <div className="absolute inset-0 bg-[radial-gradient(ellipse_at_top_left,rgba(93,162,255,0.08),transparent_56%)]" />
        <div
          className="absolute inset-0 opacity-[0.02]"
          style={{
            backgroundImage: `url("data:image/svg+xml,%3Csvg width='32' height='32' viewBox='0 0 32 32' xmlns='http://www.w3.org/2000/svg'%3E%3Cpath d='M0 0h1v1H0V0zm16 16h1v1h-1v-1z' fill='%23ffffff' fill-opacity='1'/%3E%3C/svg%3E")`,
            backgroundSize: '32px 32px',
          }}
        />
      </div>

      {/* Left — branding panel (desktop only) */}
      <section className="hidden lg:flex flex-col justify-between w-5/12 xl:w-1/2 p-8 xl:p-10 relative z-10">
        <div className="animate-fade-in">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-11 h-11 rounded-2xl flex items-center justify-center"
              style={{ background: 'linear-gradient(180deg, #6CB0FF 0%, #4F93FF 100%)', boxShadow: '0 12px 28px rgba(93,162,255,0.22)' }}>
              <Lock size={20} className="text-white" />
            </div>
            <div>
              <div className="text-[1.35rem] font-extrabold text-[var(--text-primary)] tracking-[-0.04em]"
                style={{ fontFamily: 'var(--font-main)' }}>LLM Relay v4.0</div>
              <div className="text-[0.8rem] text-[var(--text-muted)] font-mono leading-none mt-1 tracking-[0.16em] uppercase">native black control plane</div>
            </div>
          </div>

          {/* Features */}
          <div className="app-panel-elevated p-8 space-y-5">
            <div className="app-kicker">Private by default</div>
            <div className="space-y-4">
            <div className="flex items-center gap-3">
              <CheckCircle size={16} className="flex-shrink-0 text-[var(--success)]" />
              <div className="flex-1">
                <h3 className="text-[1rem] font-semibold text-[var(--text-primary)] mb-1">Enterprise security</h3>
                <p className="text-[0.92rem] text-[var(--text-tertiary)]">Local-first architecture keeps your data private and your control plane close at hand.</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Bot size={16} className="flex-shrink-0 text-[var(--accent)]" />
              <div className="flex-1">
                <h3 className="text-[1rem] font-semibold text-[var(--text-primary)] mb-1">Multi-agent orchestration</h3>
                <p className="text-[0.92rem] text-[var(--text-tertiary)]">Coordinate planning, execution, and review flows from one streamlined workspace.</p>
              </div>
            </div>
            <div className="flex items-center gap-3">
              <Database size={16} className="flex-shrink-0 text-[var(--role-power-user)]" />
              <div className="flex-1">
                <h3 className="text-[1rem] font-semibold text-[var(--text-primary)] mb-1">Knowledge integration</h3>
                <p className="text-[0.92rem] text-[var(--text-tertiary)]">Connect agents to documents, runtime context, and the repositories they need to operate on.</p>
              </div>
            </div>
            </div>
          </div>
        </div>

        {/* Footer hint */}
        <div className="app-panel px-6 py-4">
          <p className="text-[0.8rem] text-[var(--text-muted)] font-mono">
            Default: <span className="text-[var(--text-tertiary)]">admin@llmrelay.local</span>
          </p>
        </div>
      </section>

      {/* Right — form panel */}
      <section className="flex-1 w-full lg:w-7/12 xl:w-1/2 px-4 sm:px-6 xl:px-8 py-[max(env(safe-area-inset-top,0px),1rem)] sm:py-10 lg:py-12 relative z-10 flex items-center">
        <div className="w-full max-w-md mx-auto space-y-6">
          <div className="lg:hidden flex items-center gap-3 pb-2">
            <div className="w-10 h-10 rounded-2xl flex items-center justify-center"
              style={{ background: 'linear-gradient(180deg, #6CB0FF 0%, #4F93FF 100%)', boxShadow: '0 12px 28px rgba(93,162,255,0.22)' }}>
              <Lock size={18} className="text-white" />
            </div>
            <div>
              <div className="text-[1.1rem] font-extrabold tracking-[-0.04em] text-[var(--text-primary)]">LLM Relay v4.0</div>
              <div className="text-[0.72rem] font-mono uppercase tracking-[0.16em] text-[var(--text-muted)]">Secure mobile control plane</div>
            </div>
          </div>

          <div className="app-panel-elevated p-5 sm:p-7 space-y-6">
            <div className="space-y-3">
              <div className="app-kicker">Sign in</div>
              <h1 className="app-title text-[var(--text-primary)]">Sign in to Control Plane</h1>
              <p className="app-subtitle">
                Control your local AI stack from anywhere with a polished dark workspace designed for mobile and desktop.
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
                <div className="rounded-[18px] border p-4" style={{ background: 'rgba(255,107,125,0.1)', borderColor: 'rgba(255,107,125,0.22)' }}>
                  <AlertCircle size={16} className="mb-2 text-[var(--danger)]" />
                  <p className="text-[0.92rem] text-[var(--text-primary)]">{error}</p>
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="app-button-primary w-full rounded-[18px] text-[0.82rem]"
              >
                {loading ? (
                  <>
                    <div className="w-4 h-4 border-2 border-t-transparent rounded-full animate-spin"
                      style={{ borderColor: '#06111f' }} />
                    <span>Signing in…</span>
                  </>
                ) : (
                  <>
                    <Lock size={18} />
                    <span>Sign in</span>
                  </>
                )}
              </button>
            </form>

            <div className="space-y-4">
              <div className="relative">
                <div className="absolute inset-0 flex items-center">
                  <div className="w-full border-t border-[var(--border)]" />
                </div>
                <div className="relative flex justify-center">
                  <span className="bg-[var(--bg-surface)] px-3 text-[0.7rem] font-mono uppercase tracking-[0.18em] text-[var(--text-muted)]">or continue with</span>
                </div>
              </div>

              <div className="grid grid-cols-1 xs:grid-cols-2 gap-3">
                <a
                  href={hasBackendConfig ? `${backendUrl}/api/auth/github/login` : undefined}
                  aria-disabled={!hasBackendConfig}
                  onClick={(event) => {
                    if (!hasBackendConfig) event.preventDefault();
                  }}
                  className="app-button-secondary rounded-[18px] normal-case tracking-normal text-[0.92rem]"
                  style={{
                    opacity: hasBackendConfig ? 1 : 0.6,
                  }}
                >
                  <Github size={16} />
                  <span>GitHub</span>
                </a>
                <a
                  href={hasBackendConfig ? `${backendUrl}/api/auth/google/login` : undefined}
                  aria-disabled={!hasBackendConfig}
                  onClick={(event) => {
                    if (!hasBackendConfig) event.preventDefault();
                  }}
                  className="app-button-secondary rounded-[18px] normal-case tracking-normal text-[0.92rem]"
                  style={{
                    opacity: hasBackendConfig ? 1 : 0.6,
                  }}
                >
                  <GoogleIcon />
                  <span>Google</span>
                </a>
              </div>
            </div>
          </div>

          {!hasBackendConfig && (
            <p className="text-[0.9rem] text-[var(--text-tertiary)] leading-relaxed text-center">
              Need to connect a backend first?{' '}
              <Link to="/bootstrap" className="text-[var(--accent)] hover:text-[var(--accent-hover)] underline underline-offset-2 transition-colors duration-200">
                Open the setup wizard
              </Link>
              .
            </p>
          )}
        </div>
      </section>
    </main>
  );
}
