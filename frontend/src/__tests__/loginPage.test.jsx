import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import LoginPage from '../pages/LoginPage';

jest.mock('../AuthContext', () => ({
  useAuth: () => ({
    login: jest.fn(),
  }),
}));

jest.mock('../api', () => ({
  fmtErr: jest.fn((value) => value ?? 'Something went wrong.'),
  getBackendUrl: jest.fn(() => ''),
}));

describe('LoginPage', () => {
  test('renders the setup wizard guidance when no backend is configured', () => {
    render(
      <MemoryRouter>
        <LoginPage />
      </MemoryRouter>
    );

    expect(screen.getByText(/need to connect a backend first/i)).toBeInTheDocument();
    expect(screen.getByRole('link', { name: /open the setup wizard/i })).toHaveAttribute('href', '/bootstrap');
  });
});
