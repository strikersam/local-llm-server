import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from '../pages/LoginPage';

const mockLogin = jest.fn();
const mockGetBackendUrl = jest.fn();

jest.mock('../AuthContext', () => ({
  useAuth: () => ({ login: mockLogin }),
}));

jest.mock('../api', () => ({
  fmtErr: (value) => value?.message || String(value),
  getBackendUrl: () => mockGetBackendUrl(),
}));

function renderPage() {
  return render(
    <MemoryRouter>
      <LoginPage />
    </MemoryRouter>
  );
}

afterEach(() => {
  jest.clearAllMocks();
});

test('keeps GitHub and Google social login buttons wired to the configured backend', () => {
  mockGetBackendUrl.mockReturnValue('https://relay.example.com');

  renderPage();

  const githubLink = screen.getByText('GitHub').closest('a');
  const googleLink = screen.getByText('Google').closest('a');

  expect(githubLink).toHaveAttribute('href', 'https://relay.example.com/api/auth/github/login');
  expect(googleLink).toHaveAttribute('href', 'https://relay.example.com/api/auth/google/login');
  expect(githubLink).toHaveAttribute('aria-disabled', 'false');
  expect(googleLink).toHaveAttribute('aria-disabled', 'false');
});

test('shows disabled social login actions when no backend is configured', () => {
  mockGetBackendUrl.mockReturnValue('');

  renderPage();

  const githubLink = screen.getByText('GitHub').closest('a');
  const googleLink = screen.getByText('Google').closest('a');

  expect(githubLink).not.toHaveAttribute('href');
  expect(googleLink).not.toHaveAttribute('href');
  expect(githubLink).toHaveAttribute('aria-disabled', 'true');
  expect(googleLink).toHaveAttribute('aria-disabled', 'true');
});
