/**
 * AuthCallback.js — Social login callback handler for LLM Relay v4.0
 *
 * Handles two OAuth flows:
 *   1. Legacy flow: /auth/callback?access_token=...&refresh_token=...
 *   2. Social login flow (v4.0): /auth/callback?token=<jwt>&provider=github|google
 *
 * Security: JWT stored in localStorage (for axios interceptor) and
 * sessionStorage (soft fallback). Never logged or transmitted in URL
 * beyond the redirect param.
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../AuthContext';

export default function AuthCallback() {
  const navigate  = useNavigate();
  const location  = useLocation();
  const { checkAuth } = useAuth();
  const [status, setStatus]   = useState('processing');
  const [provider, setProvider] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(location.search);

    // v4.0 social login flow
    const socialToken = params.get('token');
    const socialProv  = params.get('provider');

    // Legacy flow
    const accessToken  = params.get('access_token');
    const refreshToken = params.get('refresh_token');

    if (socialToken) {
      // Social login: store JWT then sync AuthContext before navigating so
      // ProtectedRoute sees the authenticated user and doesn't bounce to /login.
      localStorage.setItem('access_token', socialToken);
      sessionStorage.setItem('access_token', socialToken);
      setProvider(socialProv || 'oauth');
      setStatus('success');
      checkAuth().then(() => navigate('/', { replace: true }));
    } else if (accessToken && refreshToken) {
      // Legacy flow
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);
      setStatus('success');
      checkAuth().then(() => navigate('/', { replace: true }));
    } else {
      setStatus('error');
    }
  }, [location, navigate, checkAuth]);

  return (
    <main className="app-shell min-h-[100dvh] flex items-center justify-center px-4 py-[max(env(safe-area-inset-top,0px),1rem)]">
      <section className="app-panel-elevated p-8 sm:p-10 text-center max-w-sm w-full">
        {status === 'processing' && (
          <>
            <div className="text-5xl mb-4 animate-bounce">🔐</div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">Authenticating…</h2>
            <p className="text-[var(--text-tertiary)] text-sm mt-1">Verifying your credentials</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="text-5xl mb-4">✅</div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">
              {provider ? `${provider.charAt(0).toUpperCase() + provider.slice(1)} login successful!` : 'Login successful!'}
            </h2>
            <p className="text-[var(--text-tertiary)] text-sm mt-1">Redirecting…</p>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="text-5xl mb-4">❌</div>
            <h2 className="text-lg font-semibold text-[var(--text-primary)]">Authentication failed</h2>
            <p className="text-[var(--danger)] text-sm mt-1">No token received. Please try again.</p>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="app-button-secondary mt-5 w-full rounded-[18px] text-[0.74rem]"
            >
              Back to login
            </button>
          </>
        )}
      </section>
    </main>
  );
}
