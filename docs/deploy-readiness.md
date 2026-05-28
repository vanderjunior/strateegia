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

- `NEXT_PUBLIC_API_BASE_URL`: backend base URL used by Next proxies and remaining API helpers.
- `NEXT_PUBLIC_USE_MOCK_API`: `true` forces demo/mock mode.

Local frontend example:

```env
NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000
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
- Do not add a Compose file until the frontend/backend URL split is explicit:
  - Next server-side proxies need an internal backend URL such as `http://backend:8000`.
  - Browser-facing direct API helpers need a browser-reachable URL such as `http://localhost:8000`, or those reads must also be proxied.
  - Today `NEXT_PUBLIC_API_BASE_URL` is a single value, so a naive Compose file could work for proxies while breaking direct browser reads.

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
   - an explicit frontend/backend URL strategy before creating the Compose file
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
- Confirm frontend proxies reach the backend through `NEXT_PUBLIC_API_BASE_URL`.
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
