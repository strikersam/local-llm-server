/**
 * AuthCallback.js — Social login callback handler (v3.1)
 *
 * Handles two OAuth flows:
 *   1. Legacy flow: /auth/callback?access_token=...&refresh_token=...
 *   2. Social login flow (v3.1): /auth/callback?token=<jwt>&provider=github|google
 *
 * Security: JWT stored in localStorage (for axios interceptor) and
 * sessionStorage (soft fallback). Never logged or transmitted in URL
 * beyond the redirect param.
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';

export default function AuthCallback() {
  const navigate  = useNavigate();
  const location  = useLocation();
  const [status, setStatus]   = useState('processing');
  const [provider, setProvider] = useState('');

  useEffect(() => {
    const params = new URLSearchParams(location.search);

    // v3.1 social login flow
    const socialToken = params.get('token');
    const socialProv  = params.get('provider');

    // Legacy flow
    const accessToken  = params.get('access_token');
    const refreshToken = params.get('refresh_token');

    if (socialToken) {
      // Social login: store JWT
      localStorage.setItem('access_token', socialToken);
      sessionStorage.setItem('access_token', socialToken);
      setProvider(socialProv || 'oauth');
      setStatus('success');
      setTimeout(() => navigate('/control-plane', { replace: true }), 1200);
    } else if (accessToken && refreshToken) {
      // Legacy flow
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);
      setStatus('success');
      setTimeout(() => navigate('/', { replace: true }), 800);
    } else {
      setStatus('error');
    }
  }, [location, navigate]);

  return (
    <div className="min-h-screen flex items-center justify-center bg-gray-50">
      <div className="bg-white rounded-2xl shadow-lg p-10 text-center max-w-sm w-full">
        {status === 'processing' && (
          <>
            <div className="text-5xl mb-4 animate-bounce">🔐</div>
            <h2 className="text-lg font-semibold text-gray-700">Authenticating…</h2>
            <p className="text-gray-400 text-sm mt-1">Verifying your credentials</p>
          </>
        )}
        {status === 'success' && (
          <>
            <div className="text-5xl mb-4">✅</div>
            <h2 className="text-lg font-semibold text-gray-700">
              {provider ? `${provider.charAt(0).toUpperCase() + provider.slice(1)} login successful!` : 'Login successful!'}
            </h2>
            <p className="text-gray-400 text-sm mt-1">Redirecting…</p>
          </>
        )}
        {status === 'error' && (
          <>
            <div className="text-5xl mb-4">❌</div>
            <h2 className="text-lg font-semibold text-gray-700">Authentication failed</h2>
            <p className="text-red-500 text-sm mt-1">No token received. Please try again.</p>
            <button
              onClick={() => navigate('/login', { replace: true })}
              className="mt-4 text-indigo-600 text-sm hover:underline"
            >
              ← Back to login
            </button>
          </>
        )}
      </div>
    </div>
  );
}
