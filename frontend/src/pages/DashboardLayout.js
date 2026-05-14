import React, { useState, useCallback, useMemo } from 'react';
import { Routes, Route, NavLink, Navigate, useLocation, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import {
  LayoutDashboard, MessageSquare, BookOpen, Upload, Activity,
  Settings, LogOut, Menu, X, Cpu, Layers, BarChart3,
  Github, Shield, Bot, CheckSquare, Radio,
  Zap, Lock, Calendar, TrendingUp, MoreHorizontal,
} from 'lucide-react';
import ControlPlanePage from './ControlPlanePage';
import ChatPage from './ChatPage';
import WikiPage from './WikiPage';
import SourcesPage from './SourcesPage';
import ActivityPage from './ActivityPage';
import ProvidersPage from './ProvidersPage';
import ModelsPage from './ModelsPage';
import ObservabilityPage from './ObservabilityPage';
import SettingsPage from './SettingsPage';
import GitHubPage from './GitHubPage';
import AdminPortalPage from './AdminPortalPage';
import AgentsPage from './AgentsPage';
import TasksPage from './TasksPage';
import RuntimesPage from './RuntimesPage';
import SetupWizardPage from './SetupWizardPage';
import SchedulesPage from './SchedulesPage';
import RoutingPolicyPage from './RoutingPolicyPage';
import KnowledgePage from './KnowledgePage';
import LogsPage from './LogsPage';

/**
 * navSections — LLM Relay v4.0 navigation matching the Control Plane design system.
 *
 * Sections mirror the design bundle layout:
 *  WORKSPACE   — Control Plane, Tasks
 *  AGENTS      — Agent Roster, Schedules (Activity), Chat
 *  KNOWLEDGE   — Wiki & Sources
 *  INFRASTRUCTURE — Runtimes, Setup, Routing (Providers/Models/Obs)
 *  SYSTEM      — Logs, Settings (Admin Portal for admin)
 */
function buildNavSections(isAdmin, isPowerUser) {
  return [
    {
      label: 'WORKSPACE',
      items: [
        { to: '/', icon: LayoutDashboard, label: 'Dashboard', end: true },
        { to: '/tasks', icon: CheckSquare, label: 'Tasks' },
      ],
    },
    {
      label: 'AGENTS',
      items: [
        { to: '/agents', icon: Bot, label: 'Agent Roster' },
        { to: '/schedules', icon: Calendar, label: 'Schedules' },
        { to: '/chat', icon: MessageSquare, label: 'Direct Chat' },
      ],
    },
    {
      label: 'KNOWLEDGE',
      items: [
        { to: '/knowledge', icon: BookOpen, label: 'Wiki & Sources' },
      ],
    },
    {
      label: 'INFRASTRUCTURE',
      items: [
        { to: '/runtimes', icon: Radio, label: 'Agent Runtimes' },
        { to: '/routing', icon: TrendingUp, label: 'Routing Policy' },
        { to: '/providers', icon: Layers, label: 'Providers' },
      ],
    },
    {
      label: 'SYSTEM',
      items: [
        { to: '/logs', icon: BarChart3, label: 'Logs' },
        { to: '/setup', icon: Zap, label: 'Setup Wizard' },
        ...(isAdmin || isPowerUser ? [
          { to: '/admin', icon: Shield, label: 'Admin Portal', adminOnly: true },
        ] : []),
        { to: '/settings', icon: Settings, label: 'Settings' },
      ],
    },
  ];
}

const MOBILE_PRIMARY_NAV = [
  { to: '/', icon: LayoutDashboard, label: 'Home', end: true },
  { to: '/tasks', icon: CheckSquare, label: 'Tasks' },
  { to: '/agents', icon: Bot, label: 'Agents' },
  { to: '/knowledge', icon: BookOpen, label: 'Knowledge' },
  { to: '/settings', icon: Settings, label: 'Settings' },
];

function NavItem({ to, icon: Icon, label, end, onClick, adminOnly }) {
  return (
    <NavLink
      to={to}
      end={end}
      onClick={onClick}
      data-testid={`nav-${label.toLowerCase().replace(/\s/g, '-')}`}
      className={({ isActive }) =>
        `group relative flex items-center gap-2.5 px-3 py-2 mx-2 text-sm font-medium rounded-lg transition-all duration-150
        ${isActive
          ? `bg-[var(--accent)]/10 text-[var(--text-primary)]`
          : `text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-[var(--text-secondary)]/5`
        }`
      }
      style={{ width: 'calc(100% - 16px)' }}
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-[2px] h-4 rounded-full bg-[var(--accent)]" />
          )}
          <Icon size={14} className={isActive ? 'text-[var(--accent)]' : 'text-[var(--text-icon-inactive)] group-hover:text-[var(--text-icon-hover)]'} />
          <span className="flex-1 leading-none">{label}</span>
          {adminOnly && (
            <Lock size={9} className="text-[var(--text-muted)]" title="Admin only" />
          )}
        </>
      )}
    </NavLink>
  );
}

function SidebarContent({ user, onLogout, onClose }) {
  const initial = (user?.name || user?.email || 'A')[0].toUpperCase();
  const isAdmin = user?.role === 'admin';
  const isPowerUser = user?.role === 'power_user';
  const navSections = buildNavSections(isAdmin, isPowerUser);

  const roleColor = isAdmin ? 'var(--accent)' : isPowerUser ? 'var(--role-power-user)' : 'var(--role-user)';
  const roleLabel = isAdmin ? 'admin' : isPowerUser ? 'power user' : 'user';

  return (
    <div className="flex flex-col h-full" data-testid="sidebar">
      {/* Logo */}
      <div className="px-4 pt-4 pb-3 border-b" style={{ borderColor: 'rgba(255,255,255,0.08)' }}>
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg flex items-center justify-center"
            style={{ background: 'var(--accent)', boxShadow: '0 2px 12px rgba(0,102,255,0.3)' }}>
            <Cpu size={16} className="text-white" />
          </div>
          <div>
            <div className="text-[14px] font-bold text-white tracking-tight"
              style={{ fontFamily: 'var(--font-main)' }}>LLM Relay v4.0</div>
            <div className="text-[10px] text-[var(--text-muted)] font-mono leading-none mt-0.5">native black control plane</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {navSections.map(section => (
          <div key={section.label} className="mb-1">
            <div className="px-5 pt-3 pb-1 text-[9px] tracking-[0.18em] uppercase font-mono font-bold"
              style={{ color: 'var(--text-muted)' }}>
              {section.label}
            </div>
            {section.items.map(item => (
              <NavItem key={item.to} {...item} onClick={onClose} />
            ))}
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="p-3 space-y-0.5" style={{ borderTop: '1px solid rgba(255,255,255,0.08)' }}>
        <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg">
          <div className="w-7 h-7 rounded-full flex items-center justify-center text-[11px] font-bold text-white shrink-0"
            style={{ background: 'var(--accent)' }}>
            {initial}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-[12px] font-medium truncate" style={{ color: 'var(--text-primary)' }}>
                {user?.name || 'User'}
              </span>
              <span className="text-[8px] font-mono uppercase tracking-wider px-1.5 py-[2px] rounded"
                style={{ background: `${roleColor}20`, color: roleColor }}>
                {roleLabel}
              </span>
            </div>
            <div className="text-[10px] font-mono truncate" style={{ color: 'var(--text-muted)' }}>
              {user?.email || 'local'}
            </div>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-[11px] transition-all duration-150"
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--danger)'; e.currentTarget.style.background = 'var(--danger-hover-bg)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--text-muted)'; e.currentTarget.style.background = 'transparent'; }}
          data-testid="logout-button"
        >
          <LogOut size={12} />
          <span>Sign out</span>
        </button>
      </div>
    </div>
  );
}

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate('/login');
  }, [logout, navigate]);

  const closeSidebar = useCallback(() => setSidebarOpen(false), []);
  const currentPath = location.pathname.startsWith('/chat/')
    ? '/chat'
    : location.pathname.startsWith('/wiki') || location.pathname.startsWith('/sources') || location.pathname.startsWith('/github')
      ? '/knowledge'
      : location.pathname;
  const mobileNavItems = useMemo(() => {
    const isKnown = MOBILE_PRIMARY_NAV.some((item) => item.to === currentPath || (item.end && currentPath === '/'));
    return isKnown
      ? MOBILE_PRIMARY_NAV
      : [...MOBILE_PRIMARY_NAV.slice(0, 4), { to: currentPath, icon: MoreHorizontal, label: 'More' }];
  }, [currentPath]);

  return (
    <div className="app-shell min-h-[100dvh] flex flex-col lg:flex-row overflow-hidden"
      style={{ fontFamily: 'var(--font-main)' }}
      data-testid="dashboard-layout">

      {/* Mobile top bar */}
      <div className="lg:hidden sticky top-0 z-40 flex items-center gap-3 px-4 h-[calc(env(safe-area-inset-top,0px)+4rem)] pt-[env(safe-area-inset-top,0px)] app-glass border-b"
        style={{ borderColor: 'var(--border)' }}>
        <button
          onClick={() => setSidebarOpen(s => !s)}
          className="w-11 h-11 flex items-center justify-center rounded-full border bg-white/[0.03]"
          style={{ borderColor: 'var(--border-soft)' }}
          data-testid="mobile-menu-toggle"
          aria-label="Toggle navigation"
        >
          {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
        </button>
        <div className="min-w-0 flex items-center gap-3">
          <div className="w-9 h-9 rounded-2xl flex items-center justify-center"
            style={{ background: 'linear-gradient(180deg, #6CB0FF 0%, #4F93FF 100%)', boxShadow: '0 10px 24px rgba(93,162,255,0.2)' }}>
            <Cpu size={14} className="text-white" />
          </div>
          <div className="min-w-0">
            <div className="text-[0.95rem] font-extrabold tracking-[-0.04em] text-white">LLM Relay v4.0</div>
            <div className="text-[0.65rem] font-mono uppercase tracking-[0.16em] text-[var(--text-muted)] truncate">
              {user?.name || user?.email || 'Control plane'}
            </div>
          </div>
        </div>
      </div>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 z-40 backdrop-blur-sm"
          style={{ background: 'rgba(0,0,0,0.6)' }}
          onClick={closeSidebar}
          aria-hidden
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-40
          w-[min(84vw,320px)] lg:w-[280px] flex flex-col
          transform transition-transform duration-200 ease-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
        style={{ background: 'rgba(5,6,8,0.98)', borderRight: '1px solid var(--border)' }}
      >
        <SidebarContent user={user} onLogout={handleLogout} onClose={closeSidebar} />
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden">
        <div className="flex-1 min-h-0 overflow-hidden">
          <Routes>
            {/* Dashboard home */}
            <Route path="/" element={<div className="h-full overflow-y-auto"><ControlPlanePage /></div>} />
            <Route path="/dashboard" element={<Navigate to="/" replace />} />
            <Route path="/control-plane" element={<Navigate to="/" replace />} />
            <Route path="/llmrelay" element={<Navigate to="/" replace />} />

            {/* Workspace */}
            <Route path="/tasks" element={<div className="h-full overflow-y-auto"><TasksPage /></div>} />

            {/* Agents */}
            <Route path="/agents" element={<div className="h-full overflow-y-auto"><AgentsPage /></div>} />
            <Route path="/schedules" element={<div className="h-full overflow-y-auto"><SchedulesPage /></div>} />
            <Route path="/chat" element={<ChatPage />} />
            <Route path="/chat/:sessionId" element={<ChatPage />} />

            {/* Knowledge — consolidated Wiki + Sources + GitHub */}
            <Route path="/knowledge" element={<div className="h-full overflow-hidden"><KnowledgePage /></div>} />
            {/* Legacy knowledge routes redirect */}
            <Route path="/wiki" element={<Navigate to="/knowledge" replace />} />
            <Route path="/wiki/:slug" element={<Navigate to="/knowledge" replace />} />
            <Route path="/sources" element={<Navigate to="/knowledge" replace />} />
            <Route path="/github" element={<Navigate to="/knowledge" replace />} />

            {/* Infrastructure */}
            <Route path="/runtimes" element={<div className="h-full overflow-y-auto"><RuntimesPage /></div>} />
            <Route path="/routing" element={<div className="h-full overflow-y-auto"><RoutingPolicyPage /></div>} />
            <Route path="/providers" element={<div className="h-full overflow-y-auto"><ProvidersPage /></div>} />
            <Route path="/models" element={<div className="h-full overflow-y-auto"><ModelsPage /></div>} />
            <Route path="/observability" element={<Navigate to="/logs" replace />} />

            {/* System — consolidated Logs */}
            <Route path="/logs" element={<div className="h-full overflow-hidden"><LogsPage /></div>} />
            <Route path="/activity" element={<Navigate to="/logs" replace />} />
            <Route path="/setup" element={<div className="h-full overflow-y-auto"><SetupWizardPage /></div>} />
            <Route path="/admin" element={<AdminPortalPage />} />
            <Route path="/settings" element={<div className="h-full overflow-y-auto"><SettingsPage /></div>} />

            {/* Legacy redirects */}
            <Route path="/keys" element={<Navigate to="/admin" replace />} />
            <Route path="/agentview" element={<Navigate to="/chat" replace />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </div>
      </main>

      <nav className="lg:hidden sticky bottom-0 z-30 app-glass border-t px-2 pb-[max(env(safe-area-inset-bottom,0px),0.5rem)] pt-2"
        style={{ borderColor: 'var(--border)' }}
        aria-label="Primary">
        <div className="grid grid-cols-5 gap-1 items-end">
          {mobileNavItems.slice(0, 2).map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={`${to}-${label}`}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex min-h-[3.5rem] flex-col items-center justify-center gap-1 rounded-2xl px-2 py-2 transition-all ${
                  isActive
                    ? 'bg-[var(--accent-soft)] text-white'
                    : 'text-[var(--text-muted)]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={18} className={isActive ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'} />
                  <span className="text-[0.62rem] font-mono uppercase tracking-[0.12em]">{label}</span>
                </>
              )}
            </NavLink>
          ))}

          {/* Center FAB — New Chat */}
          <NavLink
            to="/chat"
            className="flex flex-col items-center justify-center gap-1 -mt-3"
            aria-label="New chat"
            onClick={() => {}}
          >
            {({ isActive }) => (
              <>
                <div className={`w-12 h-12 rounded-full flex items-center justify-center shadow-[0_4px_16px_rgba(93,162,255,0.35)] transition-transform active:scale-95 ${isActive ? 'bg-[var(--accent-hover)]' : 'bg-[var(--accent)]'}`}>
                  <MessageSquare size={20} className="text-[#06111f]" />
                </div>
                <span className="text-[0.58rem] font-mono uppercase tracking-[0.12em] text-[var(--text-muted)]">Chat</span>
              </>
            )}
          </NavLink>

          {mobileNavItems.slice(2).map(({ to, icon: Icon, label, end }) => (
            <NavLink
              key={`${to}-${label}`}
              to={to}
              end={end}
              className={({ isActive }) =>
                `flex min-h-[3.5rem] flex-col items-center justify-center gap-1 rounded-2xl px-2 py-2 transition-all ${
                  isActive
                    ? 'bg-[var(--accent-soft)] text-white'
                    : 'text-[var(--text-muted)]'
                }`
              }
            >
              {({ isActive }) => (
                <>
                  <Icon size={18} className={isActive ? 'text-[var(--accent)]' : 'text-[var(--text-muted)]'} />
                  <span className="text-[0.62rem] font-mono uppercase tracking-[0.12em]">{label}</span>
                </>
              )}
            </NavLink>
          ))}
        </div>
      </nav>
    </div>
  );
}
