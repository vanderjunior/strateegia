# Deploy Readiness Plan

## Purpose

This document captures the local/staging readiness state before any real deployment work. It is planning-only: no deployment provider, PostgreSQL migration, auth provider, or product behavior change is introduced here.

## Current Local Architecture

- Backend: FastAPI app from `app.main:app`.
- Frontend: Next.js app under `frontend/`.
- Persistence: JSON repository at `data/study_data.json` by default.
- Upload files: stored under `data/uploads/` by default because `app.state.storage_root` is derived from the JSON repository parent.
- Session model: local in-memory cookie sessions stored in `app.state.auth_sessions`.
- Protected frontend reads: browser calls same-origin Next API routes, and those proxies forward cookies to the backend.

## Local Runbook

Backend:

```bash
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

If using the bundled project environment, run commands through the existing Python environment that provides `fastapi`, `uvicorn`, `pytest`, `httpx`, `pdfplumber`, `pymupdf`, and `python-multipart`.

Frontend:

```bash
cd frontend
npm run dev
```

Expected local ports:

- Backend: `http://127.0.0.1:8000`
- Frontend: `http://localhost:3000` unless Next selects another port

## Environment Variables

Backend currently reads:

- `APP_ENV`: `development`, `test`, or `production`; default is `development`.
- `ENABLE_INSPECTION`: enables inspection surfaces outside production by default.
- `REQUIRE_AUTH_FOR_INSPECTION`: defaults to `false` outside production and `true` in production.
- `INSPECTION_ALLOWED_IN_PRODUCTION`: must be enabled before inspection can be available in production.
- `STUDYFLOW_DATA_FILE`: JSON store path; default is `data/study_data.json`.
- `STUDYFLOW_UPLOAD_ROOT`: upload file root; default is `data/uploads`.

Backend gaps before staging:

- There is no durable session secret or session store setting.
- There is no explicit CORS configuration in the backend app.

Frontend currently reads:

- `NEXT_PUBLIC_API_BASE_URL`: browser/public backend base URL used by public API helpers and bundled client configuration.
- `BACKEND_INTERNAL_URL`: server-side backend base URL used by Next same-origin proxies; falls back to `NEXT_PUBLIC_API_BASE_URL` for local compatibility.
- `NEXT_PUBLIC_USE_MOCK_API`: `true` forces demo/mock mode.

Local frontend example:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
BACKEND_INTERNAL_URL=http://127.0.0.1:8000
NEXT_PUBLIC_USE_MOCK_API=false
```

Docker Compose frontend example:

```env
NEXT_PUBLIC_API_BASE_URL=http://localhost:8000
BACKEND_INTERNAL_URL=http://backend:8000
NEXT_PUBLIC_USE_MOCK_API=false
```

## Session And Cookie Notes

- Cookie name: `studyflow_session`.
- Cookie flags today:
  - `HttpOnly`
  - `SameSite=Lax`
  - no explicit `Secure` flag
- Session lookup is in-memory under `app.state.auth_sessions`.
- A backend restart clears active sessions.
- Same-origin Next proxies forward the browser cookie server-side to the backend.
- If frontend and backend are hosted on different origins, protected browser reads should keep using Next proxies unless CORS and cookie policy are deliberately configured.

## JSON Storage Notes

- Default path is `data/study_data.json`.
- Override with `STUDYFLOW_DATA_FILE`.
- The JSON store is created on app startup if missing.
- User-scoped materials, editais, pipeline state, and many artifacts live inside the JSON payload.
- Local data survives process restart when the `data/` directory remains intact.
- Data does not survive redeploy on ephemeral hosting unless `data/` is mounted or otherwise persisted.
- JSON persistence is acceptable for internal staging only if concurrent write/load expectations are modest and backups are clear.

## Upload Storage Notes

- Allowed upload extensions: `.pdf`, `.txt`, `.md`.
- Upload size limit: `5 MB`.
- Uploaded files are stored under `data/uploads/{user_id}/`.
- Override the upload root with `STUDYFLOW_UPLOAD_ROOT`.
- Metadata is stored in the JSON repository.
- TXT and Markdown can be text-extracted at upload time.
- PDFs are treated cautiously; scanned PDFs may require OCR validation.
- Upload files do not survive ephemeral redeploy unless the upload directory is persisted with the JSON store.

## CORS And Proxy Strategy

Protected browser reads currently use same-origin Next proxies for:

- `/api/auth/me`
- `/api/materials`
- `/api/editais`
- `/api/materials/[materialId]/summary`
- `/api/editais/[editalId]/summary`
- `/api/materials/[materialId]/pipeline/summary`
- `/api/materials/upload`

This is the safest staging pattern because cookies are forwarded server-side and cookie values are not exposed in UI state.

Next proxy routes use `BACKEND_INTERNAL_URL` when it is set. This lets Docker Compose route server-side calls to `http://backend:8000` while preserving `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` for browser-reachable/public configuration.

Public backend GETs may remain direct only when they do not depend on protected session cookies. If a browser route needs authenticated user data, prefer a same-origin proxy first.

## Validation Commands

Backend targeted protected-read validation:

```bash
./.python_packages/bin/pytest tests/test_pipeline_summary_read_api.py tests/test_material_summary_read_api.py tests/test_materials_read_api.py tests/test_editais_read_api.py tests/test_edital_summary_read_api.py tests/test_material_upload.py tests/test_user_dashboard_api.py tests/test_user_dashboard_http_smoke.py
```

Backend full validation, when needed:

```bash
./.python_packages/bin/pytest
```

Frontend validation:

```bash
cd frontend
npm run test
npm run typecheck
npm run build
```

Frontend safety greps:

```bash
rg -n -i 'correct_answer|correct_option|answer_key|answer_key_value|final_answer_key|final_answer_key_content|gabarito|gabarito_final|correctness|is_correct|raw document body|raw OCR text dump|OCR/base64 payload|password_hash|session token|private path/storage root|/Users/|C:\\' app components lib/mock lib/adapters lib/api lib/product
rg -n -i 'pricing|plano gratuito|plano profissional|plano intensivo|assinatura|comprar|checkout' app components lib/mock lib/adapters lib/api lib/product
```

## Staging Options

### Local-only

- Lowest risk and already available.
- Good for continued product QA.
- Not enough for multi-user or external review.

### Docker Compose internal staging

- Recommended next staging option.
- Run backend and frontend together with a mounted persistent volume for `data/`.
- Keeps JSON/uploads explicit and reversible.
- Avoids premature PostgreSQL or cloud provider coupling.
- A conservative `docker-compose.yml` is available for internal staging readiness:
  - backend runs `uvicorn app.main:app --host 0.0.0.0 --port 8000`
  - backend mounts `studyflow_data` at `/app/data`
  - frontend uses `BACKEND_INTERNAL_URL=http://backend:8000`
  - frontend builds with `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000`

Compose command:

```bash
docker compose up --build
```

Smoke result summary:

- Backend container started, exposed port `8000`, and Uvicorn started successfully.
- Frontend container started, exposed port `3000`, and Next.js started successfully.
- `GET http://localhost:8000/api/exam-profiles` returned `200`.
- `GET http://localhost:3000` returned `200`.
- `GET http://localhost:3000/api/auth/me` returned `200` with `{"authenticated":false,"user":null}`.
- `GET http://localhost:3000/api/materials` returned `401 Authentication required`.
- `GET http://localhost:3000/api/editais` returned `401 Authentication required`.
- Backend logs confirmed proxied requests arriving from the frontend container IP, which validates `BACKEND_INTERNAL_URL=http://backend:8000`.
- `docker compose restart` succeeded, and frontend/backend returned `200` after restart.
- `docker volume ls` showed `newproject_studyflow_data`.
- `docker compose down -v` removed the volume. Do not use `-v` when preserving staging data.

Commands that passed:

```bash
docker compose config
docker compose up --build
docker compose restart
curl -i http://localhost:8000/api/exam-profiles
curl -i http://localhost:3000
curl -i http://localhost:3000/api/auth/me
curl -i http://localhost:3000/api/materials
curl -i http://localhost:3000/api/editais
docker volume ls
docker compose down -v
```

Expected unauthenticated proxy behavior:

- `/api/auth/me` returns `200` with `authenticated: false`.
- `/api/materials` returns `401`.
- `/api/editais` returns `401`.
- These responses confirm proxy connectivity. A `502` here would indicate backend connectivity failure from the frontend container.

Manual authenticated smoke checklist, still pending:

- Establish a valid login/session using the existing local auth path.
- Upload a small `.txt` material through the controlled upload page.
- Confirm `/materials` shows real session data.
- Restart with `docker compose restart`, not `docker compose down -v`.
- Confirm JSON metadata and uploaded file data persist after restart.
- Open the uploaded material pipeline detail and confirm the bounded pipeline summary route works.

### Single VM

- Good second option if the team wants a persistent internal URL.
- Requires process manager, HTTPS, backups, and mounted storage.

### Render/Railway/Fly backend plus Vercel frontend

- Reasonable later.
- Cross-origin cookies, HTTPS, persisted storage, and backend file volume support must be settled first.
- Next proxies can still protect browser reads, but backend session cookie domain/SameSite/Secure behavior needs deliberate testing.

## Recommended Staging Path

1. Keep local validation as the default development workflow.
2. Add an internal Docker Compose staging plan with:
   - backend service
   - frontend service
   - mounted `data/` volume shared only with backend
   - explicit `STUDYFLOW_DATA_FILE=/app/data/study_data.json`
   - explicit `STUDYFLOW_UPLOAD_ROOT=/app/data/uploads`
   - `BACKEND_INTERNAL_URL=http://backend:8000` for Next server-side proxies
   - `NEXT_PUBLIC_API_BASE_URL=http://localhost:8000` for browser/public configuration
   - no public auth provider yet
3. Validate one internal user flow:
   - login with local auth
   - upload controlled material
   - view materials/editais/detail/pipeline bounded reads
   - restart services and confirm JSON/uploads persist
4. Only then consider a cloud provider.

## PostgreSQL Timing

PostgreSQL should wait until:

- repository boundaries are clearer
- JSON storage limitations have been observed in staging
- real user-scoped upload/list/detail flows have been validated end-to-end
- the team knows which artifacts need relational querying versus file/object storage

Do not migrate persistence before staging proves the product flow and storage requirements.

## Risks And Limitations

- In-memory sessions are cleared on backend restart.
- Session cookies are local and not production-auth hardened.
- JSON store can be fragile under concurrent writes or ephemeral hosting.
- Upload files require persistent disk.
- Cross-origin cookie behavior can fail if frontend/backend are split without careful HTTPS/domain/SameSite/Secure policy.
- OCR is not a production guarantee for scanned PDFs.
- Simulado execution remains intentionally non-active.
- Progress mutation and scheduler/calendar UX remain deferred.
- No external auth provider, billing, pricing, or public SaaS packaging exists.

## Pre-Deploy Checklist

- Confirm target staging topology and ports.
- Make JSON path and upload storage root explicit before any cloud run.
- Use `STUDYFLOW_DATA_FILE` and `STUDYFLOW_UPLOAD_ROOT` instead of relying on implicit paths.
- Mount or back up `data/`.
- Confirm backend restart behavior for sessions and storage.
- Confirm frontend proxies reach the backend through `BACKEND_INTERNAL_URL`.
- Confirm browser/public API helpers use `NEXT_PUBLIC_API_BASE_URL`.
- Confirm no protected browser read depends on direct cross-origin cookies.
- Run backend targeted tests and frontend test/typecheck/build.
- Run no-leakage and pricing/marketing greps.
- Keep inspection disabled or auth-protected in production-like environments.

## Non-Goals

- No PostgreSQL migration.
- No external auth provider.
- No deployment provider configuration.
- No upload/process/OCR/generation/simulado/progress/scheduler behavior changes.
- No pricing, plans, checkout, or public SaaS packaging.
