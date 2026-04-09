import React, { useState } from 'react';
import { Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import {
  LayoutDashboard, MessageSquare, BookOpen, Upload, Activity,
  Settings, LogOut, Menu, X, Cpu, ChevronRight
} from 'lucide-react';

import DashboardHome from './DashboardHome';
import ChatPage from './ChatPage';
import WikiPage from './WikiPage';
import SourcesPage from './SourcesPage';
import ActivityPage from './ActivityPage';
import SettingsPage from './SettingsPage';

const navItems = [
  { to: '/', icon: LayoutDashboard, label: 'DASHBOARD', end: true },
  { to: '/chat', icon: MessageSquare, label: 'AGENT CHAT' },
  { to: '/wiki', icon: BookOpen, label: 'WIKI' },
  { to: '/sources', icon: Upload, label: 'SOURCES' },
  { to: '/activity', icon: Activity, label: 'ACTIVITY' },
  { to: '/settings', icon: Settings, label: 'SETTINGS' },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = async () => {
    await logout();
    navigate('/login');
  };

  const SidebarContent = () => (
    <div className="flex flex-col h-full" data-testid="sidebar">
      {/* Logo */}
      <div className="px-5 py-5 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Cpu size={18} className="text-[#002FA7]" />
          <span className="text-sm font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>
            LLM WIKI
          </span>
        </div>
        <div className="text-[10px] tracking-[0.2em] uppercase text-[#737373] mt-1 font-mono">
          AGENT DASHBOARD
        </div>
      </div>

      {/* Nav */}
      <nav className="flex-1 py-3 overflow-y-auto">
        {navItems.map(({ to, icon: Icon, label, end }) => (
          <NavLink
            key={to}
            to={to}
            end={end}
            onClick={() => setSidebarOpen(false)}
            className={({ isActive }) =>
              `flex items-center gap-3 px-5 py-2.5 text-xs tracking-wider font-mono transition-all group
              ${isActive
                ? 'text-white bg-white/5 border-l-2 border-[#002FA7]'
                : 'text-[#737373] hover:text-[#A0A0A0] hover:bg-white/[0.02] border-l-2 border-transparent'
              }`
            }
            data-testid={`nav-${label.toLowerCase().replace(/\s/g, '-')}`}
          >
            <Icon size={15} />
            <span>{label}</span>
            <ChevronRight size={12} className="ml-auto opacity-0 group-hover:opacity-50 transition-opacity" />
          </NavLink>
        ))}
      </nav>

      {/* User */}
      <div className="border-t border-white/10 p-4">
        <div className="flex items-center gap-3 mb-3">
          <div className="w-7 h-7 bg-[#002FA7] flex items-center justify-center text-xs font-bold">
            {(user?.name || 'A')[0].toUpperCase()}
          </div>
          <div className="flex-1 min-w-0">
            <div className="text-xs text-white truncate">{user?.name || 'Admin'}</div>
            <div className="text-[10px] text-[#737373] truncate">{user?.email}</div>
          </div>
        </div>
        <button
          onClick={handleLogout}
          className="w-full flex items-center gap-2 text-[10px] tracking-wider uppercase text-[#737373] hover:text-[#FF3333] transition-colors font-mono py-1"
          data-testid="logout-button"
        >
          <LogOut size={12} />
          SIGN OUT
        </button>
      </div>
    </div>
  );

  return (
    <div className="h-screen flex bg-[#0A0A0A]" data-testid="dashboard-layout">
      {/* Mobile menu toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="lg:hidden fixed top-3 left-3 z-50 p-2 bg-[#141414] border border-white/10 text-white"
        data-testid="mobile-menu-toggle"
      >
        {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
      </button>

      {/* Sidebar overlay (mobile) */}
      {sidebarOpen && (
        <div className="lg:hidden fixed inset-0 bg-black/60 z-30" onClick={() => setSidebarOpen(false)} />
      )}

      {/* Sidebar */}
      <aside className={`
        fixed lg:static inset-y-0 left-0 z-40
        w-56 bg-[#141414] border-r border-white/10
        transform transition-transform duration-200
        ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}
      `}>
        <SidebarContent />
      </aside>

      {/* Main content */}
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<DashboardHome />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:sessionId" element={<ChatPage />} />
          <Route path="/wiki" element={<WikiPage />} />
          <Route path="/wiki/:slug" element={<WikiPage />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/activity" element={<ActivityPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
