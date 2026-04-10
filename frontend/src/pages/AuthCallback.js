import React, { useEffect } from 'react';
import { useNavigate, useLocation } from 'react-router-dom';
import { useAuth } from '../AuthContext';

export default function AuthCallback() {
  const navigate = useNavigate();
  const location = useLocation();
  const { checkAuth } = useAuth();

  useEffect(() => {
    const params = new URLSearchParams(location.search);
    const accessToken = params.get('access_token');
    const refreshToken = params.get('refresh_token');

    if (accessToken && refreshToken) {
      localStorage.setItem('access_token', accessToken);
      localStorage.setItem('refresh_token', refreshToken);
      
      // Sync auth state and redirect
      checkAuth().then(() => {
        navigate('/', { replace: true });
      });
    } else {
      console.error('Missing tokens in OAuth callback');
      navigate('/login', { replace: true });
    }
  }, [location, navigate, checkAuth]);

  return (
    <div className="h-screen flex items-center justify-center bg-[#0A0A0A]">
      <div className="text-[#737373] font-mono text-sm animate-pulse-slow uppercase tracking-widest">
        Finalizing session...
      </div>
    </div>
  );
}
