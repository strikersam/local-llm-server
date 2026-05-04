import React from 'react';
import { render, waitFor } from '@testing-library/react';
import AuthCallback from '../pages/AuthCallback';

const mockNavigate = jest.fn();
const mockCheckAuth = jest.fn(() => Promise.resolve());
let mockSearch = '?token=social-jwt&provider=github';

jest.mock('react-router-dom', () => ({
  ...jest.requireActual('react-router-dom'),
  useNavigate: () => mockNavigate,
  useLocation: () => ({ search: mockSearch }),
}));

jest.mock('../AuthContext', () => ({
  useAuth: () => ({ checkAuth: mockCheckAuth }),
}));

beforeEach(() => {
  localStorage.clear();
  sessionStorage.clear();
  mockNavigate.mockReset();
  mockCheckAuth.mockReset();
  mockCheckAuth.mockResolvedValue(undefined);
});

test('social login callback lands on the root dashboard after auth sync', async () => {
  mockSearch = '?token=social-jwt&provider=github';

  render(<AuthCallback />);

  await waitFor(() => expect(mockCheckAuth).toHaveBeenCalled());
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true }));
  expect(localStorage.getItem('access_token')).toBe('social-jwt');
  expect(sessionStorage.getItem('access_token')).toBe('social-jwt');
});

test('legacy callback flow also returns to the root dashboard', async () => {
  mockSearch = '?access_token=legacy-access&refresh_token=legacy-refresh';

  render(<AuthCallback />);

  await waitFor(() => expect(mockCheckAuth).toHaveBeenCalled());
  await waitFor(() => expect(mockNavigate).toHaveBeenCalledWith('/', { replace: true }));
  expect(localStorage.getItem('access_token')).toBe('legacy-access');
  expect(localStorage.getItem('refresh_token')).toBe('legacy-refresh');
});
