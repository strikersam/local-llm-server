# V3 API Migration Plan — LLM Relay Platform

## Goal
Migrate from admin-based session auth (`/admin/api`) to v3 token-based auth (`/api/auth`) with comprehensive endpoint support for dashboard, chat, wiki, providers, and observability.

## Current State Analysis
- **Auth System**: Session-based tokens with admin_auth.py (AdminIdentity, AdminSession)
- **Data Persistence**: Keys stored in keys.json; no persistent user/session DB
- **API Structure**: `/admin/api/*` endpoints (login, status, control, users, keys)
- **Frontend Expectation**: `/api/auth/login` (email/password), JWT-like tokens (access_token, refresh_token)
- **Endpoints Needed**: ~40+ endpoints across auth, chat, wiki, sources, providers, models, stats, activity, observability

## Approach
Create a **parallel v3 API layer** that coexists with the existing `/admin/*` endpoints (backward compatibility).

1. **Phase 1 (Auth)**: Implement JWT-based token system with `/api/auth/login`, `/api/auth/me`, token refresh
2. **Phase 2 (Core Data)**: Add `/api/models`, `/api/providers`, `/api/stats` (read-only from Ollama/proxy internals)
3. **Phase 3 (Chat/Wiki)**: Implement `/api/chat/*` and `/api/wiki/*` (stub implementations initially)
4. **Phase 4 (Advanced)**: Add `/api/sources`, `/api/activity`, `/api/observability`

Keep existing `/admin/*` working for backward compatibility and internal use.

## Implementation Strategy

### Data Model Changes
```python
# New: v3 User model (for v3 dashboard auth)
class V3User(BaseModel):
    _id: str  # unique ID
    email: str  # from .env or ADMIN_SECRET email
    name: str
    role: str  # "admin", "user"
    created_at: datetime
    last_login: datetime

# New: JWT Token response
class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int
    _id: str
    email: str
    name: str
    role: str
```

### Files to Create/Modify

| File | Changes | Priority |
|------|---------|----------|
| `handlers/v3_auth.py` | New file: `/api/auth/login`, `/api/auth/me`, `/api/auth/refresh`, `/api/auth/logout` | P0 |
| `handlers/v3_models.py` | New file: `/api/models/*`, `/api/providers/*` endpoints | P1 |
| `handlers/v3_chat.py` | New file: `/api/chat/sessions/*` (can be stubs initially) | P2 |
| `handlers/v3_wiki.py` | New file: `/api/wiki/pages/*` (can be stubs initially) | P2 |
| `handlers/v3_stats.py` | New file: `/api/stats`, `/api/activity`, `/api/observability/*` | P2 |
| `proxy.py` | Import and register v3 handlers; add CORS headers | P0 |
| `tokens.py` | New file: JWT token generation/validation | P0 |
| `.env` | Add: V3_JWT_SECRET, V3_ADMIN_EMAIL, V3_ADMIN_NAME | P0 |
| `tests/test_v3_api.py` | New: comprehensive tests for all v3 endpoints | P0 |
| `docs/changelog.md` | Document the migration | P0 |

### Auth Flow (v3 JWT-based)
1. User hits `POST /api/auth/login` with `{email, password}`
2. Validate against ADMIN_SECRET (initially one hardcoded user)
3. Create JWT access_token (exp 1h) and refresh_token (exp 7d)
4. Return both tokens + user data
5. Frontend stores in localStorage and sends `Authorization: Bearer <access_token>` on subsequent requests
6. Middleware validates JWT before allowing access

### Database/Storage
- **Phase 1**: In-memory JWT validation + environment-based user (no persistent store needed yet)
- **Phase 2** (optional): Add SQLite for sessions/users if needed for scale

### Backward Compatibility
- Keep `/admin/*` endpoints fully functional
- Both auth systems can coexist
- Existing admin UI continues to work via session tokens
- v3 dashboard uses JWT tokens

## Implementation Checklist

### Phase 1: Auth (Required)
- [ ] Create `tokens.py` with JWT generation/validation
- [ ] Create `handlers/v3_auth.py` with login, me, refresh, logout
- [ ] Add JWT validation middleware
- [ ] Register v3 auth routes in `proxy.py`
- [ ] Add CORS headers for localhost:3000 in proxy
- [ ] Update .env with V3_JWT_SECRET (or auto-generate)
- [ ] Write tests for auth flow
- [ ] Verify frontend can log in

### Phase 2: Core Endpoints (For MVP)
- [ ] Create `handlers/v3_models.py` (list models, get model, pull, delete)
- [ ] Create `handlers/v3_stats.py` (stats, activity, observability)
- [ ] Wire up to Ollama API and proxy internals
- [ ] Write tests

### Phase 3: Chat/Wiki (Optional for MVP)
- [ ] Create `handlers/v3_chat.py` (list sessions, get, delete, send message)
- [ ] Create `handlers/v3_wiki.py` (CRUD for wiki pages)
- [ ] Implement using existing agent/chat infrastructure

### Phase 4: Full Feature Parity
- [ ] GitHub OAuth
- [ ] Sources/ingest
- [ ] Full observability metrics
- [ ] Rate limiting per user

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Breaking admin API | High | Keep `/admin/*` fully intact; only add `/api/*` |
| JWT secret exposure | High | Read from env var, warn if using default in .env |
| Token validation bugs | High | Extensive unit tests; compare against PyJWT library |
| CORS issues (localhost:3000) | Medium | Add `Access-Control-Allow-Origin: http://localhost:3000` |
| Test failures | Medium | Add `/api/*` tests before deploying; maintain 100% pass rate |
| User persistence | Low | Start with env-based user, add DB later if needed |

## Acceptance Checks
- [ ] `pytest -x` passes (including new v3 tests)
- [ ] Frontend login succeeds via `/api/auth/login`
- [ ] `/api/auth/me` returns user data
- [ ] `/api/models` lists available models
- [ ] Tokens expire correctly (test with expired JWT)
- [ ] `/admin/*` endpoints still work (backward compat)
- [ ] CORS headers correct for localhost:3000
- [ ] Changelog updated
- [ ] No secrets hardcoded

## Timeline
- **Phase 1 (Auth)**: ~2-3 hours
- **Phase 2 (Models/Stats)**: ~1-2 hours
- **Phase 3 (Chat/Wiki)**: ~2-3 hours (if building full features; stubs are ~30 min)
- **Phase 4 (Polish)**: ~1 hour

## Files to Read First (Understanding)
- `admin_auth.py` — current session/token system
- `proxy.py` — current route structure and middleware
- `router/model_router.py` — model querying logic
- `chat_handlers.py` — chat completions implementation

## Next Action After Approval
1. Run `pytest -x` to establish baseline (expect 1 failure in model_router, not related to auth)
2. Create `tokens.py` with JWT functions
3. Create `handlers/v3_auth.py` with complete auth flow
4. Update `proxy.py` to register v3 routes and add CORS
5. Test frontend login
6. Implement remaining endpoints per phases

---

**Estimated Total Effort**: 6-10 hours for full implementation, 2-3 hours for MVP (auth + models + stats)
