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
 * navSections — v3.1 navigation matching the Control Plane design.
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
        { to: '/providers', icon: Layers, label: 'Setup' },
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
        `group relative flex items-center gap-2.5 px-3 py-2 mx-2 text-[12.5px] font-medium rounded-lg transition-all duration-150
        ${isActive
          ? 'bg-accent/10 text-primary'
          : 'text-[#808094] hover:text-[#B2B2C4] hover:bg-white/[0.04]'
        }`
      }
      style={{ width: 'calc(100% - 16px)' }}
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 rounded-full bg-[#002FA7]" />
          )}
          <Icon size={14} className={isActive ? 'text-[#002FA7]' : 'text-[#6E6E80] group-hover:text-[#8E8EA2]'} />
          <span className="flex-1 leading-none">{label}</span>
          {adminOnly && (
            <Lock size={9} className="text-[#565666]" title="Admin only" />
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

  const roleColor = isAdmin ? '#002FA7' : isPowerUser ? '#3B82F6' : '#10B981';
  const roleLabel = isAdmin ? 'admin' : isPowerUser ? 'power user' : 'user';

  return (
    <div className="flex flex-col h-full" data-testid="sidebar">
      {/* Logo */}
      <div className="px-4 pt-4 pb-3 border-b" style={{ borderColor: 'rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg flex items-center justify-center"
            style={{ background: '#002FA7', boxShadow: '0 2px 12px rgba(0,47,167,0.5)' }}>
            <Cpu size={13} className="text-white" />
          </div>
          <div>
            <div className="text-[13px] font-bold text-white tracking-tight"
              style={{ fontFamily: 'var(--font-main)' }}>LLM Relay</div>
            <div className="text-[9px] text-[#565666] font-mono leading-none mt-0.5">v3.1 · control plane</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-2 overflow-y-auto">
        {navSections.map(section => (
          <div key={section.label} className="mb-1">
            <div className="px-5 pt-3 pb-1 text-[9px] tracking-[0.18em] uppercase font-mono font-bold"
              style={{ color: '#565666' }}>
              {section.label}
            </div>
            {section.items.map(item => (
              <NavItem key={item.to} {...item} onClick={onClose} />
            ))}
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="p-3 space-y-0.5" style={{ borderTop: '1px solid rgba(255,255,255,0.06)' }}>
        <div className="flex items-center gap-2.5 px-2 py-1.5 rounded-lg">
          <div className="w-6 h-6 rounded-full flex items-center justify-center text-[10px] font-bold text-white shrink-0"
            style={{ background: '#002FA7' }}>
            {initial}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-[11.5px] font-medium truncate" style={{ color: '#D2D2E2' }}>
                {user?.name || 'User'}
              </span>
              <span className="text-[7px] font-mono uppercase tracking-wider px-1 py-px rounded"
                style={{ background: roleColor + '20', color: roleColor }}>
                {roleLabel}
              </span>
            </div>
            <div className="text-[9px] font-mono truncate" style={{ color: '#565666' }}>
              {user?.email || 'local'}
            </div>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2 px-2 py-1.5 rounded-lg text-[11px] transition-all duration-150"
          style={{ color: '#6E6E80' }}
          onMouseEnter={e => { e.currentTarget.style.color = '#f87171'; e.currentTarget.style.background = 'rgba(239,68,68,0.05)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = '#6E6E80'; e.currentTarget.style.background = 'transparent'; }}
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
    <div className="min-h-[100dvh] flex" style={{ background: '#0F0F13', fontFamily: 'var(--font-main)' }}
      data-testid="dashboard-layout">

      {/* Mobile top bar */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center gap-3 px-4 h-12"
        style={{ background: '#0D0D11', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
        <button
          onClick={() => setSidebarOpen(s => !s)}
          className="w-7 h-7 flex items-center justify-center rounded border text-white"
          style={{ borderColor: 'rgba(255,255,255,0.1)' }}
          data-testid="mobile-menu-toggle"
          aria-label="Toggle navigation"
        >
          {sidebarOpen ? <X size={15} /> : <Menu size={15} />}
        </button>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md flex items-center justify-center"
            style={{ background: '#002FA7' }}>
            <Cpu size={11} className="text-white" />
          </div>
          <span className="text-[12px] font-bold text-white tracking-tight"
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
          w-52 flex flex-col
          transform transition-transform duration-200 ease-out
          ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
        `}
        style={{ background: '#0D0D11', borderRight: '1px solid rgba(255,255,255,0.06)' }}
      >
        <SidebarContent user={user} onLogout={handleLogout} onClose={closeSidebar} />
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 flex flex-col overflow-hidden" style={{ paddingTop: '0' }}>
        <div className="flex-1 overflow-hidden pt-12 lg:pt-0">
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
