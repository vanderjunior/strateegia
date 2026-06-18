# Railway Staging Launch Runbook

Status: `READY_FOR_MANUAL_DEPLOY`

This runbook prepares the current textual personal-study alpha for a private Railway staging deployment. It does not mark public production ready and does not add product functionality.

## Architecture

Use one Railway project with two repository services:

| Service | Root | Dockerfile | Start | Health |
| --- | --- | --- | --- | --- |
| Backend | repository root | `Dockerfile` | `./scripts/start_backend.sh` | `GET /api/health` |
| Frontend | `frontend/` | `frontend/Dockerfile` | `npm run start -- -H 0.0.0.0 -p ${PORT:-3000}` | `GET /` |

Backend requirements:

- One replica only.
- Persistent Railway volume mounted at `/data`.
- Runtime env `DATA_DIR=/data`.
- No public domain after validation if the frontend can reach it through Railway private networking.
- No automatic QA fixture execution.

Frontend requirements:

- Public Railway HTTPS domain.
- Server-only `BACKEND_INTERNAL_URL` pointing to the backend private-network URL.
- Do not put the private backend URL in `NEXT_PUBLIC_*`.
- Build must not require backend private networking.

## Required Environment Variables

Backend:

```env
APP_ENV=staging
DATA_DIR=/data
ENABLE_PUBLIC_REGISTRATION=false
SESSION_COOKIE_SECURE=true
ENABLE_INSPECTION=false
INSPECTION_ALLOWED_IN_PRODUCTION=false
REQUIRE_AUTH_FOR_INSPECTION=true
ENABLE_OCR=false
```

Optional explicit path overrides, normally unnecessary when `DATA_DIR=/data`:

```env
STUDYFLOW_DATA_FILE=/data/study_data.json
STUDYFLOW_UPLOAD_ROOT=/data/uploads
```

Frontend:

```env
BACKEND_INTERNAL_URL=http://<backend-private-hostname>:<port>
NEXT_PUBLIC_USE_MOCK_API=false
NEXT_PUBLIC_API_BASE_URL=
```

Use `NEXT_PUBLIC_API_BASE_URL` only for browser-safe public configuration. For this staging topology, same-origin proxy routes should use `BACKEND_INTERNAL_URL`.

## Railway Setup

1. Create or select a private Railway project.
2. Add backend service from this repository.
3. Set backend root directory to repository root.
4. Use the root `Dockerfile`.
5. Attach a volume mounted at `/data`.
6. Set backend variables from this runbook.
7. Keep backend replicas at `1`.
8. Configure backend healthcheck path as `/api/health`.
9. Deploy backend.
10. Temporarily enable or use the backend service URL only long enough to validate `/api/health`, then remove public exposure if private networking works.
11. Add frontend service from this repository.
12. Set frontend root directory to `frontend`.
13. Use `frontend/Dockerfile`.
14. Set frontend variables from this runbook.
15. Configure frontend healthcheck path as `/`.
16. Generate the frontend public domain.
17. Deploy frontend.

## Tester User Creation

Create tester accounts explicitly. Do not enable public registration for staging.

Preferred Railway shell command:

```bash
MENTORIUM_TESTER_PASSWORD='<set-in-shell-only>' \
python scripts/create_staging_user.py \
  --username tester-one \
  --display-name 'Tester One' \
  --email tester-one@example.com
```

If the platform supports masked variables, set `MENTORIUM_TESTER_PASSWORD` as a one-off secret for the command and remove it afterward. Do not commit or paste tester passwords into docs.

The command is idempotent by username/email. It refuses `APP_ENV=production`, requires `APP_ENV=staging` unless `--allow-non-staging` is passed for local rehearsal, and never runs during normal app startup.

## Smoke Checklist

Run through the public frontend URL:

1. `GET /` returns `200`.
2. Login succeeds for tester one.
3. `/api/auth/me` through the frontend returns authenticated.
4. Upload a textual edital and analyze it.
5. Upload and prepare at least one textual study material.
6. Open `/study`.
7. Open a block detail.
8. Confirm grounded summary/key points render.
9. Confirm adaptive queue questions render without answer key, score, or mastery copy.
10. Submit one incorrect and one correct explicit attempt.
11. Confirm feedback is backend-derived.
12. Mark blocks studied explicitly.
13. Confirm progress summary and review basis remain bounded.
14. Logout/login again.
15. Login as tester two and confirm tester one data is not visible.

## Local Validation Snapshot

Last verified for this staging-prep pass:

- Backend tests: `1560 passed`, with existing PyMuPDF/SWIG deprecation warnings only.
- Frontend tests: `523 passed`, with existing React `act(...)` warnings in unrelated tests only.
- Frontend production build and typecheck passed.
- Docker Compose clean rebuild passed for backend and frontend images.
- Local Compose smoke passed: backend `GET /api/health` returned `200 {"status":"ok"}` and frontend `GET /` returned `200`.
- Railway deployment, public frontend URL smoke, Railway restart persistence, and Railway volume backup creation remain manual because Railway credentials/project access were not available in this environment.

## Restart And Redeploy Persistence

Before restart, record bounded IDs/counts:

- username;
- edital count;
- material count;
- block count;
- one question ID;
- attempt count;
- studied block count;
- review basis.

Then:

1. Restart backend service.
2. Login again.
3. Confirm data, attempts, progress, and queue behavior persist.
4. Perform a no-op redeploy.
5. Confirm the same persistence signals again.

Expected: sessions may be lost because sessions are in memory, but persisted user/material/progress/attempt data remains on `/data`.

## Backup

Create an initial backup before tester use.

If Railway shell access is available:

```bash
tar -czf /tmp/mentorium-staging-data.tgz /data
```

Download/store the tarball outside Railway. Restore only into a stopped or isolated backend because restoring replaces the current JSON/upload state.

Restore rehearsal:

1. Deploy a temporary backend service with a separate volume.
2. Upload the backup tarball.
3. Extract it so `/data/study_data.json` and `/data/uploads` exist.
4. Start the temporary backend.
5. Confirm login, materials, attempts, progress, and queue state.

Do not claim restore has been tested unless this rehearsal is completed.

## Deploy And Rollback

- Deploy from a staging branch, not an unreviewed local worktree.
- Deploy backend first for backend-compatible changes, then frontend.
- For frontend-only changes, deploy frontend only.
- Before schema-affecting backend changes, create a fresh volume backup.
- If healthcheck fails, inspect Railway build/runtime logs and roll back to the previous successful deployment.
- Code rollback does not roll back JSON/upload data. Use a backup only when data rollback is intended.
- To disable tester access quickly, pause the frontend service or rotate tester passwords by editing/removing users in a maintenance window.

## Current Limitations

- JSON/file persistence requires one backend replica.
- Sessions are in memory; backend restart logs users out.
- OCR is disabled by default.
- No public signup UI or public registration should be enabled.
- No score, official correction, gabarito reveal, simulado execution, or review-detail execution.
- Public production remains `NO_GO`.

## NPM Audit Triage

Run before deployment:

```bash
cd frontend
npm audit --omit=dev
npm audit
```

Current triage after non-forced `npm audit fix`:

- Production/runtime: `postcss <8.5.10` reported through Next's nested dependency as moderate severity. npm currently offers only `npm audit fix --force`, which would perform a breaking framework change. Do not use `--force` for staging; track the Next patch line and retest when a non-breaking remediation is available.
- Development-only: previous Vite/Vitest high/critical findings were removed by the non-forced audit fix. A remaining low esbuild advisory affects a Windows development-server path and is not part of the Railway production runtime.

Any future high or critical production-runtime advisory must be resolved before tester access.
