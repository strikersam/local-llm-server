import React, { useState, useCallback } from 'react';
import { Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import {
  LayoutDashboard, MessageSquare, BookOpen, Upload, Activity,
  Settings, LogOut, Menu, X, Cpu, ChevronRight, Layers, BarChart3,
  Box, Github, Shield, Bot, CheckSquare, Radio, ClipboardList,
  FileText, Zap, Lock,
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

/**
 * navSections — v3 unified navigation.
 *
 * Sections:
 *  Operations  — Control Plane (home), Agent Chat, Agents, Tasks
 *  Engineering — GitHub, Wiki, Sources
 *  Infrastructure — Providers, Models, Runtimes, Observability
 *  System      — Activity, Admin Portal (admin only), Settings
 */
function buildNavSections(isAdmin) {
  return [
    {
      label: 'Operations',
      items: [
        { to: '/', icon: LayoutDashboard, label: 'Control Plane', end: true },
        { to: '/chat', icon: MessageSquare, label: 'Agent Chat' },
        { to: '/agents', icon: Bot, label: 'Agents' },
        { to: '/tasks', icon: CheckSquare, label: 'Tasks' },
      ],
    },
    {
      label: 'Engineering',
      items: [
        { to: '/github', icon: Github, label: 'GitHub' },
        { to: '/wiki', icon: BookOpen, label: 'Wiki' },
        { to: '/sources', icon: Upload, label: 'Sources' },
      ],
    },
    {
      label: 'Infrastructure',
      items: [
        { to: '/providers', icon: Layers, label: 'Providers' },
        { to: '/models', icon: Box, label: 'Models Hub' },
        { to: '/runtimes', icon: Radio, label: 'Runtimes' },
        { to: '/observability', icon: BarChart3, label: 'Observability' },
      ],
    },
    {
      label: 'System',
      items: [
        { to: '/activity', icon: Activity, label: 'Activity' },
        ...(isAdmin ? [
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
        `group relative flex items-center gap-3 px-4 py-2.5 text-[13px] font-medium rounded-lg mx-2 transition-all duration-150
        ${isActive
          ? 'bg-[#002FA7]/12 text-white'
          : 'text-[#666666] hover:text-[#A0A0A0] hover:bg-white/[0.03]'
        }`
      }
    >
      {({ isActive }) => (
        <>
          {isActive && (
            <div className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-4 bg-[#002FA7] rounded-full" />
          )}
          <Icon size={15} className={isActive ? 'text-[#002FA7]' : ''} />
          <span className="flex-1 leading-none">{label}</span>
          {adminOnly && (
            <Lock size={9} className="text-[#333] mr-1" title="Admin only" />
          )}
          <ChevronRight size={11} className="opacity-0 group-hover:opacity-40 transition-opacity -translate-x-1 group-hover:translate-x-0 duration-150" />
        </>
      )}
    </NavLink>
  );
}

function SidebarContent({ user, onLogout, onClose }) {
  const initial = (user?.name || user?.email || 'A')[0].toUpperCase();
  const isAdmin = user?.role === 'admin';
  const navSections = buildNavSections(isAdmin);

  return (
    <div className="flex flex-col h-full" data-testid="sidebar">
      {/* Logo */}
      <div className="px-5 pt-5 pb-4 border-b border-white/6">
        <div className="flex items-center gap-2.5">
          <div className="w-7 h-7 rounded-lg bg-[#002FA7] flex items-center justify-center shadow-[0_2px_8px_rgba(0,47,167,0.4)]">
            <Cpu size={14} className="text-white" />
          </div>
          <div>
            <div className="text-[13px] font-bold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>LLM Relay</div>
            <div className="text-[10px] text-[#444444] font-mono leading-none mt-0.5">v3.0</div>
          </div>
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {navSections.map(section => (
          <div key={section.label} className="mb-1">
            <div className="px-6 pt-3 pb-1 text-[10px] tracking-[0.18em] uppercase text-[#333333] font-mono font-bold">
              {section.label}
            </div>
            {section.items.map(item => (
              <NavItem key={item.to} {...item} onClick={onClose} />
            ))}
          </div>
        ))}
      </nav>

      {/* User footer */}
      <div className="border-t border-white/6 p-3 space-y-1">
        <div className="flex items-center gap-2.5 px-2 py-2 rounded-lg">
          <div className="w-7 h-7 rounded-full bg-[#002FA7] flex items-center justify-center text-[11px] font-bold text-white shrink-0 shadow-[0_2px_8px_rgba(0,47,167,0.3)]">
            {initial}
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-1.5">
              <span className="text-[12px] text-[#CCCCCC] font-medium truncate">{user?.name || 'User'}</span>
              {isAdmin && (
                <span className="text-[8px] font-mono uppercase px-1 py-0.5 rounded border border-amber-500/25 bg-amber-500/8 text-amber-400 flex-shrink-0">
                  Admin
                </span>
              )}
            </div>
            <div className="text-[10px] text-[#444444] truncate font-mono">{user?.email}</div>
          </div>
        </div>
        <button
          onClick={onLogout}
          className="w-full flex items-center gap-2 px-2 py-2 rounded-lg text-[12px] text-[#555555] hover:text-[#FF4444] hover:bg-[#FF4444]/5 transition-all duration-150 font-medium"
          data-testid="logout-button"
        >
          <LogOut size={13} />
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
    <div className="min-h-[100dvh] flex bg-[#0A0A0A]" data-testid="dashboard-layout">

      {/* Mobile top bar */}
      <div className="lg:hidden fixed top-0 left-0 right-0 z-50 flex items-center gap-3 px-4 h-14 bg-[#0A0A0A]/95 backdrop-blur-sm border-b border-white/6">
        <button
          onClick={() => setSidebarOpen(s => !s)}
          className="p-2 rounded-lg bg-white/4 border border-white/8 text-white hover:bg-white/8 transition-colors"
          data-testid="mobile-menu-toggle"
          aria-label="Toggle navigation"
        >
          {sidebarOpen ? <X size={17} /> : <Menu size={17} />}
        </button>
        <div className="flex items-center gap-2">
          <div className="w-6 h-6 rounded-md bg-[#002FA7] flex items-center justify-center">
            <Cpu size={12} className="text-white" />
          </div>
          <span className="text-[13px] font-bold text-white tracking-tight" style={{ fontFamily: 'Outfit, sans-serif' }}>LLM Relay</span>
          <span className="text-[9px] font-mono text-[#333] border border-white/8 px-1.5 py-0.5 rounded">v3</span>
        </div>
      </div>

      {/* Mobile overlay */}
      {sidebarOpen && (
        <div
          className="lg:hidden fixed inset-0 bg-black/60 z-40 backdrop-blur-[2px]"
          onClick={closeSidebar}
          aria-hidden
        />
      )}

      {/* Sidebar */}
      <aside
        className={`
          fixed lg:static inset-y-0 left-0 z-40
          w-56 bg-[#0D0D0D] border-r border-white/6
          transform transition-transform duration-200 ease-out
          ${sidebarOpen ? 'translate-x-0 shadow-[4px_0_32px_rgba(0,0,0,0.5)]' : '-translate-x-full lg:translate-x-0'}
          flex flex-col
        `}
      >
        <SidebarContent user={user} onLogout={handleLogout} onClose={closeSidebar} />
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 flex flex-col pt-14 lg:pt-0 overflow-hidden">
        <Routes>
          {/* v3 Control Plane home */}
          <Route path="/" element={<div className="overflow-y-auto flex-1"><ControlPlanePage /></div>} />
          {/* Legacy dashboard (accessible at /dashboard for backward compat) */}
          <Route path="/dashboard" element={<div className="overflow-y-auto flex-1"><DashboardHome /></div>} />

          {/* Operations */}
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:sessionId" element={<ChatPage />} />
          <Route path="/agents" element={<div className="overflow-y-auto flex-1"><AgentsPage /></div>} />
          <Route path="/tasks" element={<div className="overflow-y-auto flex-1"><TasksPage /></div>} />

          {/* Engineering */}
          <Route path="/github" element={<div className="overflow-y-auto flex-1"><GitHubPage /></div>} />
          <Route path="/wiki" element={<div className="overflow-y-auto flex-1"><WikiPage /></div>} />
          <Route path="/wiki/:slug" element={<div className="overflow-y-auto flex-1"><WikiPage /></div>} />
          <Route path="/sources" element={<div className="overflow-y-auto flex-1"><SourcesPage /></div>} />

          {/* Infrastructure */}
          <Route path="/providers" element={<div className="overflow-y-auto flex-1"><ProvidersPage /></div>} />
          <Route path="/models" element={<div className="overflow-y-auto flex-1"><ModelsPage /></div>} />
          <Route path="/runtimes" element={<div className="overflow-y-auto flex-1"><RuntimesPage /></div>} />
          <Route path="/observability" element={<div className="overflow-y-auto flex-1"><ObservabilityPage /></div>} />

          {/* System */}
          <Route path="/activity" element={<div className="overflow-y-auto flex-1"><ActivityPage /></div>} />
          <Route path="/admin" element={<AdminPortalPage />} />
          <Route path="/settings" element={<div className="overflow-y-auto flex-1"><SettingsPage /></div>} />

          {/* Redirects for old paths */}
          <Route path="/keys" element={<Navigate to="/admin" replace />} />
          <Route path="/agentview" element={<Navigate to="/chat" replace />} />

          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
