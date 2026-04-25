import React, { useState, useEffect } from 'react';
import { Routes, Route, Navigate, useNavigate } from 'react-router-dom';
import { AuthProvider, useAuth } from './AuthContext';
import LoginPage from './pages/LoginPage';
import AuthCallback from './pages/AuthCallback';
import DashboardLayout from './pages/DashboardLayout';
import SetupWizardPage from './pages/SetupWizardPage';
import { getSetupState, getBackendUrl } from './api';

function LoadingScreen({ message }) {
  return (
    <div className="min-h-[100dvh] flex items-center justify-center bg-[#0A0A0A]">
      <div className="flex flex-col items-center gap-3">
        <div className="w-8 h-8 border-2 border-[#002FA7] border-t-transparent rounded-full animate-spin" />
        <p className="text-[#555555] text-xs font-mono tracking-widest uppercase">{message}</p>
      </div>
    </div>
  );
}

function ProtectedRoute({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen message="Authenticating" />;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

/**
 * SetupGuard — wraps the dashboard and redirects to /setup if setup is incomplete.
 * Only checks when a backend URL is configured; skips silently if no backend.
 */
function SetupGuard({ children }) {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    if (!user || !getBackendUrl()) {
      setChecked(true);
      return;
    }
    getSetupState()
      .then(r => {
        if (!r.data.completed) navigate('/setup', { replace: true });
      })
      .catch(() => {}) // don't block the dashboard if the call fails
      .finally(() => setChecked(true));
  }, [user, navigate]);

  if (!checked) return <LoadingScreen message="Checking setup" />;
  return children;
}

function AppRoutes() {
  const { user, loading } = useAuth();
  if (loading) return <LoadingScreen message="Initializing" />;
  return (
    <Routes>
      <Route path="/login" element={user ? <Navigate to="/" replace /> : <LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallback />} />

      {/* Pre-auth setup wizard — configure backend URL before logging in */}
      <Route path="/bootstrap" element={<SetupWizardPage />} />

      {/* Protected dashboard (includes /setup as a nested route) */}
      <Route
        path="/*"
        element={
          <ProtectedRoute>
            <SetupGuard>
              <DashboardLayout />
            </SetupGuard>
          </ProtectedRoute>
        }
      />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <AppRoutes />
    </AuthProvider>
  );
}
