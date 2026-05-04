import React from 'react';
import { render, screen } from '@testing-library/react';
import { MemoryRouter } from 'react-router-dom';
import App from '../App';

jest.mock('../pages/AuthCallback', () => () => <div>Auth callback</div>);
jest.mock('../pages/DashboardLayout', () => () => <div>Dashboard</div>);
jest.mock('../pages/SetupWizardPage', () => () => <div>Setup wizard</div>);

jest.mock('../AuthContext', () => ({
  AuthProvider: ({ children }) => <>{children}</>,
  useAuth: () => ({
    user: false,
    loading: false,
    login: jest.fn(),
    logout: jest.fn(),
    checkAuth: jest.fn(),
  }),
}));

jest.mock('../api', () => {
  const actual = jest.requireActual('../api');
  return {
    ...actual,
    getBackendUrl: jest.fn(() => ''),
    getSetupState: jest.fn(() => Promise.resolve({ data: { completed: false } })),
  };
});

describe('GitHub Pages app routing', () => {
  test('companyhelm deep link falls back to the login page without crashing', async () => {
    render(
      <MemoryRouter basename="/local-llm-server" initialEntries={['/local-llm-server/companyhelm']}>
        <App />
      </MemoryRouter>
    );

    expect(await screen.findByText(/sign in to control plane/i)).toBeInTheDocument();
    expect(screen.getByText(/need to connect a backend first/i)).toBeInTheDocument();
  });
});
