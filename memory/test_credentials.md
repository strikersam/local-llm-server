# Test Credentials

- **Email**: admin@llmwiki.local
- **Password**: WikiAdmin2026!
- **Role**: admin

## Auth Endpoints
- POST /api/auth/login
- POST /api/auth/logout
- GET /api/auth/me
- POST /api/auth/refresh

## Auth Type
JWT tokens stored in httpOnly cookies (access_token + refresh_token).
Access token valid for 24 hours, refresh token for 7 days.
