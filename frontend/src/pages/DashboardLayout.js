import React, { useState } from 'react';
import { Routes, Route, NavLink, Navigate, useNavigate } from 'react-router-dom';
import { useAuth } from '../AuthContext';
import {
  LayoutDashboard, MessageSquare, BookOpen, Upload, Activity,
  Settings, LogOut, Menu, X, Cpu, ChevronRight, Layers, Key, BarChart3, Box, Github
} from 'lucide-react';
import DashboardHome from './DashboardHome';
import ChatPage from './ChatPage';
import WikiPage from './WikiPage';
import SourcesPage from './SourcesPage';
import ActivityPage from './ActivityPage';
import ProvidersPage from './ProvidersPage';
import ModelsPage from './ModelsPage';
import ApiKeysPage from './ApiKeysPage';
import ObservabilityPage from './ObservabilityPage';
import SettingsPage from './SettingsPage';
import GitHubPage from './GitHubPage';

const navSections = [
  {
    label: 'CORE', items: [
      { to: '/', icon: LayoutDashboard, label: 'DASHBOARD', end: true },
      { to: '/chat', icon: MessageSquare, label: 'AGENT CHAT' },
      { to: '/wiki', icon: BookOpen, label: 'WIKI' },
      { to: '/sources', icon: Upload, label: 'SOURCES' },
      { to: '/github', icon: Github, label: 'GITHUB' },
    ]
  },
  {
    label: 'INFRASTRUCTURE', items: [
      { to: '/providers', icon: Layers, label: 'PROVIDERS' },
      { to: '/models', icon: Box, label: 'MODELS HUB' },
      { to: '/keys', icon: Key, label: 'API KEYS' },
    ]
  },
  {
    label: 'SYSTEM', items: [
      { to: '/observability', icon: BarChart3, label: 'OBSERVABILITY' },
      { to: '/activity', icon: Activity, label: 'ACTIVITY' },
      { to: '/settings', icon: Settings, label: 'SETTINGS' },
    ]
  },
];

export default function DashboardLayout() {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const handleLogout = async () => { await logout(); navigate('/login'); };

  const SidebarContent = () => (
    <div className="flex flex-col h-full" data-testid="sidebar">
      <div className="px-5 py-4 border-b border-white/10">
        <div className="flex items-center gap-2">
          <Cpu size={16} className="text-[#002FA7]" />
          <span className="text-sm font-bold tracking-tighter" style={{ fontFamily: 'Chivo, sans-serif' }}>LLM RELAY</span>
        </div>
        <div className="text-[9px] tracking-[0.2em] uppercase text-[#737373] mt-0.5 font-mono">UNIFIED PLATFORM v2.0</div>
      </div>
      <nav className="flex-1 py-2 overflow-y-auto">
        {navSections.map(section => (
          <div key={section.label}>
            <div className="px-5 pt-4 pb-1.5 text-[9px] tracking-[0.2em] uppercase text-[#737373]/60 font-mono font-bold">{section.label}</div>
            {section.items.map(({ to, icon: Icon, label, end }) => (
              <NavLink key={to} to={to} end={end} onClick={() => setSidebarOpen(false)}
                className={({ isActive }) => `flex items-center gap-2.5 px-5 py-2 text-[11px] tracking-wider font-mono transition-all group
                  ${isActive ? 'text-white bg-white/5 border-l-2 border-[#002FA7]' : 'text-[#737373] hover:text-[#A0A0A0] hover:bg-white/[0.02] border-l-2 border-transparent'}`}
                data-testid={`nav-${label.toLowerCase().replace(/\s/g, '-')}`}>
                <Icon size={14} />
                <span>{label}</span>
                <ChevronRight size={10} className="ml-auto opacity-0 group-hover:opacity-50 transition-opacity" />
              </NavLink>
            ))}
          </div>
        ))}
      </nav>
      <div className="border-t border-white/10 p-3">
        <div className="flex items-center gap-2 mb-2">
          <div className="w-6 h-6 bg-[#002FA7] flex items-center justify-center text-[10px] font-bold">{(user?.name || 'A')[0].toUpperCase()}</div>
          <div className="flex-1 min-w-0">
            <div className="text-[11px] text-white truncate">{user?.name || 'Admin'}</div>
            <div className="text-[9px] text-[#737373] truncate">{user?.email}</div>
          </div>
        </div>
        <button onClick={handleLogout} className="w-full flex items-center gap-1.5 text-[9px] tracking-wider uppercase text-[#737373] hover:text-[#FF3333] transition-colors font-mono py-1" data-testid="logout-button">
          <LogOut size={11} /> SIGN OUT
        </button>
      </div>
    </div>
  );

  return (
    <div className="h-screen flex bg-[#0A0A0A]" data-testid="dashboard-layout">
      <button onClick={() => setSidebarOpen(!sidebarOpen)} className="lg:hidden fixed top-3 left-3 z-50 p-2 bg-[#141414] border border-white/10 text-white" data-testid="mobile-menu-toggle">
        {sidebarOpen ? <X size={18} /> : <Menu size={18} />}
      </button>
      {sidebarOpen && <div className="lg:hidden fixed inset-0 bg-black/60 z-30" onClick={() => setSidebarOpen(false)} />}
      <aside className={`fixed lg:static inset-y-0 left-0 z-40 w-52 bg-[#141414] border-r border-white/10 transform transition-transform duration-200 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full lg:translate-x-0'}`}>
        <SidebarContent />
      </aside>
      <main className="flex-1 overflow-y-auto">
        <Routes>
          <Route path="/" element={<DashboardHome />} />
          <Route path="/chat" element={<ChatPage />} />
          <Route path="/chat/:sessionId" element={<ChatPage />} />
          <Route path="/wiki" element={<WikiPage />} />
          <Route path="/wiki/:slug" element={<WikiPage />} />
          <Route path="/sources" element={<SourcesPage />} />
          <Route path="/providers" element={<ProvidersPage />} />
          <Route path="/models" element={<ModelsPage />} />
          <Route path="/keys" element={<ApiKeysPage />} />
          <Route path="/github" element={<GitHubPage />} />
          <Route path="/observability" element={<ObservabilityPage />} />
          <Route path="/activity" element={<ActivityPage />} />
          <Route path="/settings" element={<SettingsPage />} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </main>
    </div>
  );
}
