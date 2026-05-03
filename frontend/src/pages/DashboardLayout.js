import React, { useState, useCallback } from 'react';
import { Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import {
  LayoutDashboard, MessageSquare, BookOpen, Upload, Activity,
  Settings, LogOut, Menu, X, Cpu, Layers, BarChart3,
  Github, Shield, Bot, CheckSquare, Radio,
  Zap, Lock, Calendar, TrendingUp,
} from 'lucide-react';
import ControlPlanePage from './ControlPlanePage';
import DashboardHome from './DashboardHome';
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
 * navSections — v3.1 navigation matching the Control Plane design system.
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
        { to: '/', icon: LayoutDashboard, label: 'Control Plane', end: true },
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
              style={{ fontFamily: 'var(--font-main)' }}>LLM Relay</div>
            <div className="text-[10px] text-[var(--text-muted)] font-mono leading-none mt-0.5">v3.1 · control plane</div>
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
                style={{ background: `var(--role-color)20`, color: 'var(--role-color)' }}>
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
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = useCallback(async () => {
    await logout();
    navigate('/login');
  }, [logout, navigate]);

  const closeSidebar = useCallback(() => setSidebarOpen(false), []);

  return (
    <div className="min-h-[100dvh] flex" 
      style={{ background: 'var(--bg-base)', fontFamily: 'var(--font-main)' }}
      data-testid="dashboard-layout">

      {/* Mobile top bar */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center gap-2.5 px-3 h-14"
        style={{ background: 'var(--bg-sidebar)', borderBottom: '1px solid var(--border)' }}>
        <button
          onClick={() => setSidebarOpen(s => !s)}
          className="w-9 h-9 flex items-center justify-center rounded border"
          style={{ borderColor: 'var(--border-soft)' }}
          data-testid="mobile-menu-toggle"
          aria-label="Toggle navigation"
        >
          {sidebarOpen ? <X size={16} /> : <Menu size={16} />}
        </button>
        <div className="flex items-center gap-2">
          <div className="w-7 h-7 rounded-md flex items-center justify-center"
            style={{ background: 'var(--accent)' }}>
            <Cpu size={14} className="text-white" />
          </div>
          <span className="text-[13px] font-bold text-white tracking-tight"
            style={{ fontFamily: 'var(--font-main)' }}>LLM Relay</span>
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
          w-[260px] flex flex-col
          transform transition-transform duration-200 ease-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
        style={{ background: 'var(--bg-sidebar)', borderRight: '1px solid var(--border)' }}
      >
        <SidebarContent user={user} onLogout={handleLogout} onClose={closeSidebar} />
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden" style={{ paddingTop: '0' }}>
        <div className="flex-1 overflow-hidden pt-[16px] lg:pt-0">
          <Routes>
            {/* Control Plane home */}
            <Route path="/" element={<div className="h-full overflow-y-auto"><ControlPlanePage /></div>} />
            <Route path="/dashboard" element={<div className="h-full overflow-y-auto"><DashboardHome /></div>} />

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
    </div>
  );
}
