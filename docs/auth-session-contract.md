# Auth / Session Contract Audit

## Current State

- The backend already has a local auth mechanism.
- It is not connected to a real auth provider yet.
- The current frontend does not implement login/logout or route protection UX.
- The frontend already classifies auth-required upload failures and shows session-aware copy.

## Current Backend Auth Mechanism

- Auth is cookie-based.
- Cookie name: `studyflow_session`.
- Login is handled by `POST /api/auth/login`.
- Logout is handled by `POST /api/auth/logout`.
- Current user status is exposed by `GET /api/auth/me`.
- Session state is stored in memory under `app.state.auth_sessions`.
- The login route currently creates a simple token from `user_id + "." + username` and stores the mapping in memory.
- Cookie flags today:
  - `httponly=True`
  - `samesite="lax"`
- There is no real provider, no signed session framework, no durable session store, no expiry policy, and no frontend auth UX yet.

## Protected Route Inventory

### Auth-required today

- Dashboard:
  - `GET /api/dashboard/overview`
  - `GET /dashboard`
- Materials / upload / processing:
  - `POST /api/materials/upload`
  - `POST /api/materials/{document_id}/process`
  - `GET /api/materials/{document_id}/pipeline`
  - `GET /api/materials/{document_id}/chunks`
  - `GET /api/materials/{document_id}/sections`
  - `POST /api/materials/{document_id}/edital/ingest`
  - `GET /api/materials/{document_id}/edital`
- Edital / alignment / graph / cycle:
  - `GET /api/edital/{edital_id}`
  - `POST /api/edital/{edital_id}/align-bibliography`
  - `GET /api/edital/{edital_id}/alignment`
  - `GET /api/alignment/{alignment_id}`
  - `POST /api/edital/{edital_id}/curriculum-graph/build`
  - `GET /api/edital/{edital_id}/curriculum-graph`
  - `GET /api/curriculum-graph/{graph_id}`
  - `POST /api/curriculum-graph/{graph_id}/study-cycle/build`
  - `GET /api/curriculum-graph/{graph_id}/study-cycle`
  - `GET /api/study-cycle/{cycle_id}`
- PSCPP suggestion from user-owned edital:
  - `POST /api/edital/{edital_id}/exam-profile/suggest`
  - `GET /api/edital/{edital_id}/exam-profile/suggestion`
- Simulado/runtime artifact chain:
  - The simulado, correction, scoring, runtime apply, propagation, and related GET/POST artifact routes are owner-scoped and auth-required.

### Public or effectively anonymous today

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`
- `GET /api/exam-profiles`
- `GET /api/exam-profiles/{profile_id}`

### Mixed / legacy optional-scope routes

- `POST /api/documents/upload`
- `GET /api/documents`
- `GET /api/documents/{document_id}`
- `POST /api/questions/{question_id}/answer`
- `POST /api/answers/submit`
- `POST /api/session/start`
- `GET /api/session/{session_id}/current`
- `POST /api/session/{session_id}/answer`
- `GET /api/progress`
- `GET /api/reviews/daily`
- `GET /api/reviews/blocks/latest`

These routes use `_scoped_repository(request)` or `_current_user_id(request)` and can operate anonymously or with optional session context. They are not aligned with the stricter auth-required contract used by the newer materials/editais/dashboard/simulado surfaces.

## Owner-only Enforcement

- Owner scope is enforced primarily by `user_id`.
- Request auth lookup:
  - `_current_user_id(request)` reads the `studyflow_session` cookie.
  - `_require_authenticated_user_id(request)` raises `401` when absent.
- Repository scoping:
  - `JsonStudyRepository.for_user(user_id)` returns `UserScopedStudyRepository`.
  - Newer artifact/material/edital/simulado reads and writes are persisted under user-specific containers.
- Cross-user access generally resolves to:
  - `401` when unauthenticated
  - `404` when authenticated as a different user and the artifact does not exist inside that user scope
- This owner-only behavior is backed by tests across materials, edital, dashboard, inspection, and simulado/runtime artifacts.

## Frontend Behavior Today

- No real login/logout UX exists yet.
- No route guards or session banner exist yet.
- Frontend API config:
  - `NEXT_PUBLIC_API_BASE_URL`
  - `NEXT_PUBLIC_USE_MOCK_API`
- GET API client:
  - `frontend/lib/api/client.ts`
  - uses `credentials: "include"`
  - classifies `401` as unauthorized/auth-required failure
  - falls back to mock/offline behavior in many adapters
- Upload path:
  - browser sends to same-origin `POST /api/materials/upload` in Next
  - Next route forwards the incoming `cookie` header to backend
  - frontend classifies `401/403` as `Sessão necessária para enviar material.`
- Current UX outcome:
  - read-only surfaces mostly degrade to mock/audited fallback
  - upload is the only frontend write path that explicitly surfaces auth-required messaging today

## Critical Gaps Before Real Auth UX

1. No frontend login/logout/session-status UX.
2. No explicit current-user bootstrap in the Next app shell.
3. No route-level decision on when to show:
   - mock fallback
   - `Requer sessão`
   - backend offline
4. Mixed backend contract:
   - newer routes require auth
   - older session/progress/document routes still allow anonymous/optional scope
5. No cross-origin auth contract is formalized:
   - frontend GET client calls `NEXT_PUBLIC_API_BASE_URL` directly with cookies
   - backend app currently does not expose a documented CORS/session contract for that browser flow
   - same-origin proxy is only implemented for upload, not for general authenticated GETs
6. No durable session strategy:
   - in-memory `auth_sessions` will reset on process restart
7. No CSRF strategy has been formalized for future authenticated mutation surfaces.
8. No explicit token storage policy exists because the current model is cookie-only and local.

## Recommended Auth-B Scope

- Keep backend behavior unchanged at first.
- Add frontend session-awareness, not a full provider yet.
- Recommended Auth-B scope:
  - define one canonical session source for the Next frontend
  - wire a lightweight current-user/session-status call around `GET /api/auth/me`
  - decide how authenticated frontend reads should reach backend:
    - same-origin proxy for authenticated GETs, or
    - explicit CORS/cookie contract if cross-origin is intended
  - add app-shell session states:
    - authenticated
    - unauthenticated
    - backend offline
    - mock/demo
  - add safe UX around protected views:
    - `Requer sessão`
    - fallback to audited demo only where product-approved
  - keep upload behavior unchanged except for clearer shared session-state UX

## Explicit Non-goals

- No auth provider integration yet.
- No login/signup screens yet.
- No cookie/session redesign yet.
- No backend auth rewrite yet.
- No PostgreSQL or durable session store yet.
- No deploy/staging work yet.

## Security Notes

- The current in-memory session map is acceptable for local/internal development, not for production-ready auth.
- The current token shape is simplistic and should not be treated as a final session design.
- Do not expand authenticated frontend behavior before choosing the browser-origin/cookie strategy.
- Do not bypass backend owner checks in frontend code.
- Do not expose password hashes, cookies, session tokens, raw OCR content, or raw document content.

## Test Strategy For Auth-B

- Backend:
  - keep targeted auth/upload/owner-only tests green
  - add tests only for any new session-status contract if introduced
- Frontend:
  - add tests for session-state rendering and `Requer sessão` UX
  - add tests for authenticated proxy/error classification if new proxies are introduced
