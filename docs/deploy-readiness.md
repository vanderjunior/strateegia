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

Authenticated smoke result summary:

- `docker compose up -d` started backend and frontend successfully.
- Backend `GET /api/exam-profiles` returned `200`.
- Frontend `GET /` returned `200`.
- Backend login through existing `POST /api/auth/login` returned `200`.
- Upload through frontend `POST /api/materials/upload` returned `201`.
- Upload intent/material type is persisted as bounded `material_type` metadata when supplied by the frontend.
- Upload response sanitization passed:
  - no `extracted_text`
  - no `storage_path`
  - no base64 payload
  - no chunks or sections
- Frontend `GET /api/materials` returned real persisted materials.
- Smoke document id: `9b6cf52e-1e74-4e2d-b1f7-7093500c22c0`.
- Frontend `GET /api/materials/{document_id}/summary` returned `200`.
- Frontend `GET /api/materials/{document_id}/pipeline/summary` returned `200`.
- `docker compose down` without `-v` removed containers/network but preserved the Docker volume.
- `docker compose up -d` recreated containers.
- Login again returned `200`.
- Frontend `GET /api/materials` still returned `6` persisted materials.
- The same document summary and pipeline summary still returned `200` after recreate.

This confirms:

- authenticated Compose smoke passed
- upload response sanitization passed
- bounded material list/detail/pipeline reads passed
- persistence after `down`/`up` without `-v` passed

Do not use `docker compose down -v` when preserving staging data. The `-v` flag deletes the persistent volume. Sessions remain in-memory, so login is required again after backend restart/recreate even when JSON/upload data persists.

Manual authenticated smoke checklist:

- Establish a valid login/session using the existing local auth endpoints.
- Upload a small `.txt` material through the frontend controlled upload proxy.
- Confirm `/materials` shows real session data.
- Restart with `docker compose restart`, not `docker compose down -v`.
- Confirm JSON metadata and uploaded file data persist after restart.
- Open the uploaded material pipeline detail and confirm the bounded pipeline summary route works.

Authenticated smoke path:

The backend already exposes local auth endpoints:

- `POST /api/auth/register`
- `POST /api/auth/login`
- `POST /api/auth/logout`
- `GET /api/auth/me`

The frontend now exposes a minimal internal-staging login/logout UX:

- `/login` provides username/password login.
- AppShell shows `Entrar` while unauthenticated.
- AppShell shows `Sair` while authenticated.
- No signup/register UI is exposed in this phase.
- Sessions remain in-memory; after backend restart/recreate, enter again.

Use a local-only cookie jar. Do not commit credentials, cookies, or generated smoke files.

```bash
COOKIE_JAR=/tmp/studyflow.compose.cookies
SMOKE_USER="compose-smoke-$(date +%s)"
SMOKE_PASSWORD="<local-only-password-with-8-or-more-chars>"
SMOKE_FILE=/tmp/studyflow-compose-smoke.txt

printf 'Resumo de smoke autenticado\nLinha 2\n' > "$SMOKE_FILE"

curl -i -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -H 'content-type: application/json' \
  -d "{\"username\":\"$SMOKE_USER\",\"password\":\"$SMOKE_PASSWORD\",\"display_name\":\"Compose Smoke\",\"email\":\"$SMOKE_USER@example.com\"}" \
  http://localhost:8000/api/auth/register

curl -i -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -H 'content-type: application/json' \
  -d "{\"username\":\"$SMOKE_USER\",\"password\":\"$SMOKE_PASSWORD\"}" \
  http://localhost:8000/api/auth/login

curl -i -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  http://localhost:3000/api/auth/me

curl -i -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  -F "file=@$SMOKE_FILE;type=text/plain" \
  http://localhost:3000/api/materials/upload

curl -i -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  http://localhost:3000/api/materials
```

Expected authenticated smoke behavior:

- Register returns `201`.
- Login returns `200` and sets `studyflow_session`.
- Frontend `/api/auth/me` returns `200` with `authenticated: true`.
- Frontend `/api/materials/upload` returns a created/uploaded material response.
- Frontend `/api/materials` returns `200` with the uploaded material in the real session-backed list.

After upload, capture the uploaded `document_id` from the upload or materials response and verify bounded detail reads:

```bash
DOCUMENT_ID="<uploaded-document-id>"

curl -i -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  "http://localhost:3000/api/materials/$DOCUMENT_ID/summary"

curl -i -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  "http://localhost:3000/api/materials/$DOCUMENT_ID/pipeline/summary"
```

Persistence smoke:

```bash
docker compose restart

curl -i -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  http://localhost:3000/api/auth/me

curl -i -c "$COOKIE_JAR" -b "$COOKIE_JAR" \
  http://localhost:3000/api/materials
```

Because sessions are in-memory, `docker compose restart` may clear the login session. If `/api/auth/me` returns `authenticated: false` after restart, log in again with the same `SMOKE_USER` and `SMOKE_PASSWORD`, then re-check `/api/materials`. The persisted material should remain as long as the `studyflow_data` volume was not removed.

### UX-RealUser-D Compose Browser QA

Authenticated Compose browser QA passed after the user-facing copy cleanup:

- `docker compose up -d` started existing backend and frontend containers.
- Backend `GET http://localhost:8000/api/exam-profiles` returned `200`.
- Frontend `GET http://localhost:3000` returned `200`.
- Logged-out `/dashboard` showed the simplified sign-in panel instead of a personalized study plan.
- Logged-out `/materials/upload` blocked active upload controls and showed the login path.
- Login through `/login` worked with a local smoke user.
- After login, the session notice showed `Sessão ativa`, the user label, and `Sair`.
- Logged-in `/dashboard` focused on the next step, not developer/staging diagnostics.
- `/materials` used the simplified card surface without section/gap zero-noise.
- The current QA volume had no legacy unknown-file materials, so `Tipo não informado` was not observable in-browser during this run; automated frontend coverage verifies the unknown-type label.
- `/materials/upload` exposed upload controls only while logged in.
- `/editais` showed the edital state without confusing zero metric cards.
- `/study` remained gated until a real analyzed edital exists.
- `/pscpp` remained reference/demo framed rather than a personalized plan.
- Logout returned the UI to `Entrar`, and `/materials/upload` became unavailable again.
- Browser checks found no raw text, storage path, token, password hash, answer key, or gabarito copy in the inspected surfaces.

No backend behavior, edital analysis execution, OCR, processing, generation, progress, scheduler, PostgreSQL, provider, or signup behavior was added during this QA closeout.

### EditalAnalysis-F1 Compose/API QA

Controlled edital analysis QA passed for safe textual PDF preparation:

- Uploading a PDF with `material_type=edital` showed the material under the Editais grouping.
- Material detail exposed the existing manual `Analisar edital` action for the uploaded edital.
- Clicking analyze used the controlled endpoint: `POST /api/materials/{document_id}/edital/analyze`.
- Fresh textual PDFs no longer returned `not_ready` solely because extraction artifacts were missing.
- When deterministic embedded-text extraction succeeded, the bounded result returned `analyzed` or `needs_review` according to the current parser output.
- OCR-required PDFs remained bounded `not_ready`.
- Controlled analysis did not trigger OCR.
- Browser/API inspection found no raw PDF text, storage path, token, password hash, answer key, or gabarito exposure.
- `/study` and `/pscpp` remained gated unless the edital lifecycle truly allowed unlock.

Known limitation: textual PDF structure recognition is still conservative. A textual PDF may return `needs_review` until a later parser/coverage phase improves section/topic recognition. Scanned or OCR-required PDFs still require a separate explicit OCR-capable contract and are not analyzed automatically.

### StudyMaterial-A Compose/API QA

Minimal study material preparation QA passed for the controlled no-OCR path:

- Rebuilt the Compose backend/frontend images before QA so the running containers included `POST /api/materials/{document_id}/study/prepare` and the frontend proxy `/api/materials/[materialId]/study/prepare`.
- Login through the frontend auth proxy returned `200` with an authenticated local QA user.
- Uploading a small `.txt` file through `/api/materials/upload` with `material_type=study_material` returned `201` with sanitized bounded metadata.
- Calling `POST /api/materials/{document_id}/study/prepare` through the frontend proxy returned `200` with `preparation_status=ready_for_study`, `section_count=1`, `chunk_count=1`, `warnings_count=0`, and `ready_for_study=true`.
- `/api/materials` showed the uploaded file as `material_type=study_material` under the bounded materials list.
- Uploading the same file as `material_type=edital` and calling the study preparation endpoint returned `422`, confirming non-study materials are not prepared through this action.
- API inspection found no raw extracted text, chunk or section body, storage path, token, password hash, answer key, or gabarito exposure.
- The UI action remains limited to authenticated real materials classified as `study_material`; editais, bibliography, previous exams, notes, and other materials do not show the study preparation action.

Textual PDF and OCR-required PDF behavior is covered by targeted backend tests: textual PDFs use deterministic embedded-text extraction without a separate visible process step, while OCR-required PDFs return bounded `not_ready` and do not trigger OCR. This flow still does not generate summaries, fixation questions, study sessions, simulados, progress updates, or LLM content.

### StudySummary-D1 Compose Browser/API QA

Prepare-then-summary QA passed for the bounded material summary flow:

- Compose was rebuilt and both services responded before QA.
- Login through `/login` worked with a local QA user.
- Uploading a small `.md` file through `/materials/upload` with `material_type=study_material` returned sanitized bounded metadata.
- Material detail showed `Preparação para estudo` and `Resumo do material` with the safe not-ready copy before preparation.
- Clicking `Preparar para estudo` showed the success state and refreshed the summary card in the same page session.
- The refreshed summary displayed bounded section count, section titles, placeholder summaries, key points, estimated minutes, and ready labels.
- The frontend summary API returned `summary_status=ready`, `sections_count=2`, bounded item titles, placeholder summaries, key points, and estimated minutes.
- A material uploaded as `material_type=edital` did not show the study preparation action or study summary card.
- Browser/API inspection found no raw extracted text, chunk or section body, storage path, token, password hash, answer key, gabarito, generated-question, simulado, or progress-mutation exposure.

Known limitation: study summaries remain conservative placeholders derived from prepared section metadata. This QA did not add generated summaries, fixation questions, study sessions, simulados, progress updates, OCR, or LLM behavior.

### StudyBlocks-QA-A Compose/API QA

Bounded `/study` blocks QA passed after rebuilding the Compose frontend/backend images:

- Backend `GET /api/exam-profiles`, frontend `GET /`, and frontend `GET /study` returned `200`.
- Unauthenticated frontend `GET /api/study/blocks` returned `401`, confirming protected proxy behavior.
- Authenticated `GET /api/study/blocks` with no prepared study material returned `blocks_status=not_ready`, `scope_status=not_ready`, `blocks_count=0`, and the safe next-step message.
- Uploading a small Markdown file as `material_type=study_material`, then calling `POST /api/materials/{document_id}/study/prepare`, returned a bounded ready-for-study result.
- After preparation, `GET /api/study/blocks` returned `blocks_status=partial`, `scope_status=material_only`, two bounded block items, material title, section counts, estimated minutes, and safe read-only actions.
- Uploading and analyzing a small textual edital, then re-checking blocks, returned `blocks_status=ready`, `scope_status=connected_to_edital`, bounded topic labels, material title, section counts, estimated minutes, and safe read-only actions.
- API inspection found no raw extracted text, chunk or section body, storage path, token, password hash, answer key, gabarito, generated-question, simulado, or progress-mutation exposure.

Known limitations: `/study` still has no block detail page, review-after-3 behavior, progress mutation, questions, generated summaries, simulado execution, OCR, LLM, scheduler, PostgreSQL, provider, or signup behavior. The older one-material `Estudo de agora` view remains only as a fallback if the blocks API is unavailable or unsupported.

### Representative QA Seed

Use the local seed script when the Compose volume needs representative browser QA data:

```bash
docker compose up -d
scripts/seed_compose_qa_materials.sh
```

The script:

- uses `FRONTEND_URL`, defaulting to `http://localhost:3000`
- uses `BACKEND_URL`, defaulting to `http://localhost:8000`
- registers or reuses `QA_SEED_USER`, defaulting to `compose-qa-seed`
- logs in through the frontend `/api/auth/login` proxy
- uploads small generated `.txt` files through frontend `/api/materials/upload`
- creates examples for `edital`, `study_material`, `previous_exam`, `bibliography`, and `note`
- omits `material_type` for one optional legacy item so `/materials` can show `Tipo não informado`
- prints the bounded `/api/materials` response

Override values only for local/internal QA:

```bash
QA_SEED_USER="compose-qa-seed-$(date +%s)" \
QA_SEED_PASSWORD="<local-only-password>" \
scripts/seed_compose_qa_materials.sh
```

After seeding, inspect these browser routes:

- `http://localhost:3000/materials`
- `http://localhost:3000/editais`
- `http://localhost:3000/study`
- `http://localhost:3000/pscpp`
- `http://localhost:3000/materials/upload`

The seed is not automatic and is not production data. Rerunning it creates additional QA materials for the same user. `docker compose down -v` deletes the persistent local volume and removes the seeded dataset.

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
