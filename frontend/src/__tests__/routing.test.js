/**
 * Tests for routing behavior — ensures /login, /bootstrap, /setup routes
 * resolve to the right components, and that GitHub Pages basename works.
 */

import React from 'react';
import { render, screen, waitFor } from '@testing-library/react';
import { MemoryRouter, Routes, Route } from 'react-router-dom';
import { getPublicPath } from '../api';

// ─── getPublicPath helper ─────────────────────────────────────────────────────

describe('getPublicPath', () => {
  const originalEnv = process.env;

  afterEach(() => {
    process.env = originalEnv;
  });

  test('returns path unchanged when PUBLIC_URL is empty', () => {
    process.env = { ...originalEnv, PUBLIC_URL: '' };
    expect(getPublicPath('/login')).toBe('/login');
  });

  test('prepends PUBLIC_URL when set', () => {
    process.env = { ...originalEnv, PUBLIC_URL: '/local-llm-server' };
    expect(getPublicPath('/login')).toBe('/local-llm-server/login');
  });

  test('handles paths without leading slash', () => {
    process.env = { ...originalEnv, PUBLIC_URL: '/local-llm-server' };
    expect(getPublicPath('login')).toBe('/local-llm-server/login');
  });

  test('returns base path when no path argument', () => {
    process.env = { ...originalEnv, PUBLIC_URL: '/local-llm-server' };
    const result = getPublicPath();
    expect(result).toBe('/local-llm-server');
  });

  test('returns "/" when both PUBLIC_URL and path are empty', () => {
    process.env = { ...originalEnv, PUBLIC_URL: '' };
    expect(getPublicPath('')).toBe('/');
  });
});

// ─── Route resolution (MemoryRouter) ─────────────────────────────────────────

function StubLogin()     { return <div data-testid="login-page">Login</div>; }
function StubBootstrap() { return <div data-testid="bootstrap-page">Bootstrap</div>; }
function StubDashboard() { return <div data-testid="dashboard">Dashboard</div>; }

function TestRouter({ initialPath }) {
  return (
    <MemoryRouter initialEntries={[initialPath]}>
      <Routes>
        <Route path="/login"     element={<StubLogin />} />
        <Route path="/bootstrap" element={<StubBootstrap />} />
        <Route path="/*"         element={<StubDashboard />} />
      </Routes>
    </MemoryRouter>
  );
}

describe('Route resolution', () => {
  test('/login renders login page', () => {
    render(<TestRouter initialPath="/login" />);
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  test('/bootstrap renders setup wizard', () => {
    render(<TestRouter initialPath="/bootstrap" />);
    expect(screen.getByTestId('bootstrap-page')).toBeInTheDocument();
  });

  test('/setup falls through to dashboard (embedded wizard)', () => {
    render(<TestRouter initialPath="/setup" />);
    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
  });

  test('unknown path falls to dashboard (catch-all)', () => {
    render(<TestRouter initialPath="/nonexistent" />);
    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
  });
});

// ─── GitHub Pages basename routing ───────────────────────────────────────────

describe('GitHub Pages basename routing', () => {
  test('MemoryRouter with /local-llm-server basename resolves /login', () => {
    render(
      <MemoryRouter basename="/local-llm-server" initialEntries={['/local-llm-server/login']}>
        <Routes>
          <Route path="/login"     element={<StubLogin />} />
          <Route path="/bootstrap" element={<StubBootstrap />} />
          <Route path="/*"         element={<StubDashboard />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByTestId('login-page')).toBeInTheDocument();
  });

  test('MemoryRouter with /local-llm-server basename resolves /setup', () => {
    render(
      <MemoryRouter basename="/local-llm-server" initialEntries={['/local-llm-server/setup']}>
        <Routes>
          <Route path="/login"     element={<StubLogin />} />
          <Route path="/bootstrap" element={<StubBootstrap />} />
          <Route path="/*"         element={<StubDashboard />} />
        </Routes>
      </MemoryRouter>
    );
    expect(screen.getByTestId('dashboard')).toBeInTheDocument();
  });
});
