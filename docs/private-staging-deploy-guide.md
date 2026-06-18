# Private Staging Deploy Guide

This guide evaluates private deployment options for the current Mentorium architecture.

## Personal-Study-MVP-A Capability Note

Private staging can now demonstrate grounded textual study behavior: extractive summaries, internally validated objective questions, immutable owner-scoped selected-answer attempts, and block-detail question ordering from the deterministic attempt-aware backend queue. This does not make the app public-production ready. Keep staging private, single-replica, backed by persistent disk, and clearly labeled alpha.

Do not market staging as official correction, scoring, permanent mastery, OCR-complete, or simulado execution.

## Recommendation

Primary option after Personal-Study-E2E-A: Railway Hobby-style private staging with a persistent backend volume, or local Docker host plus Tailscale when cloud credentials are not available.

Fallback option: Railway Hobby or Render paid service with persistent disk/volume, single backend replica, and explicit backups.

Not recommended today: Heroku-style ephemeral dynos without external persistence.

## Why Persistence Drives The Decision

Mentorium currently stores:

- JSON application state.
- Uploaded source files.
- Extracted text, chunks, sections, analyses, and progress events.
- Question attempts and their idempotency index.

That means the backend service needs durable filesystem storage. Stateless platforms or ephemeral filesystems will lose data unless storage is moved to an external database/object store.

## Option A: Local Docker + Tailscale

Status: recommended for private alpha.

Pros:

- Best match for JSON/file persistence.
- Data stays on the owner machine.
- Easy backup by archiving the Compose volume.
- No public internet exposure required.

Cons:

- Owner machine must stay online.
- Manual backups and updates.
- Not production hosting.

Use:

```bash
docker compose up -d
tailscale up
```

Then expose access only to trusted tailnet users. Tailscale CLI docs describe connecting a device with `tailscale up` and managing tailnet access: https://tailscale.com/docs/reference/tailscale-cli

## Option B: Railway Hobby

Status: conditional fallback.

Railway volumes provide persistent data for services. Treat the backend as single-replica while JSON/file storage is in use.

Required setup:

- Backend service from root `Dockerfile`.
- Frontend service from `frontend/Dockerfile`.
- Volume mounted to backend at `/data`.
- `DATA_DIR=/data`.
- `APP_ENV=staging`.
- `ENABLE_PUBLIC_REGISTRATION=false`.
- `SESSION_COOKIE_SECURE=true`.
- `ENABLE_INSPECTION=false` or protect it explicitly.
- `BACKEND_INTERNAL_URL` on frontend pointing to backend private URL.
- One backend replica only.

Risks:

- 5 GB Hobby volume may be too small for a full corpus with extracted text/chunks.
- JSON writes are single-file and not concurrency-safe.
- Need manual or platform backups.

Verdict: `CONDITIONAL_GO` for 1-2 testers only after backup drill.

Before tester access, run the NPM audit triage in `docs/staging-launch-runbook.md`. Do not proceed if a high or critical production-runtime advisory is present.

## Option C: Render Paid Service With Disk

Status: conditional fallback.

Render persistent disks preserve filesystem changes across deploys/restarts for paid services. Their docs state services are ephemeral by default and only disk mount paths persist: https://render.com/docs/disks

Required setup:

- Backend Docker service with disk mounted at `/data` or the provider-specific persistent disk path.
- Frontend web service.
- Single backend instance.
- Same env as Railway, adjusted only for the provider-specific disk mount.
- Backup routine from disk snapshots plus exported tarball.

Risks:

- Free instances without disks are unsuitable for persistent study data.
- Disk restore can lose changes after snapshot.

Verdict: `CONDITIONAL_GO` for private staging if paid disk and backups are configured.

## Option D: Heroku

Status: not recommended with current storage.

Heroku dynos use an ephemeral filesystem. The official dyno isolation docs describe dyno isolation and ephemeral dyno behavior: https://devcenter.heroku.com/articles/dyno-isolation

Mentorium would need PostgreSQL plus object storage before Heroku is a reasonable fit.

Verdict: `NO_GO` for current file-backed architecture.

## Required Services

- Backend FastAPI web service.
- Frontend Next.js web service.
- Persistent backend volume/disk.
- No PostgreSQL yet.
- No object storage yet.

## Resource Estimate

Minimum private alpha:

- Backend: 512 MB RAM can run light workloads, 1 GB safer for PDF extraction.
- Frontend: 512 MB RAM usually enough.
- Storage: start with 5-10 GB for experiments; more for real corpora.
- CPU: one shared vCPU is acceptable for small textual materials.

Do not assume a free plan is sufficient. Railway Free volume is 0.5 GB per current docs, which is too small for realistic full-corpus uploads plus extracted artifacts.

## Environment Variables

Backend:

```text
APP_ENV=staging
DATA_DIR=/data
ENABLE_PUBLIC_REGISTRATION=false
SESSION_COOKIE_SECURE=true
ENABLE_INSPECTION=false
INSPECTION_ALLOWED_IN_PRODUCTION=false
REQUIRE_AUTH_FOR_INSPECTION=true
ENABLE_OCR=false
```

Frontend:

```text
BACKEND_INTERNAL_URL=<private backend URL>
NEXT_PUBLIC_API_BASE_URL=
NEXT_PUBLIC_USE_MOCK_API=false
```

## Cookies And Auth

Current staging cookies are HTTP-only, SameSite=Lax, and secure when `APP_ENV=staging` unless explicitly overridden.

Sessions are in memory; backend restart logs users out.

## Health Checks

Suggested checks:

- Backend: `GET /api/health`.
- Frontend: `GET /`.

## Backup Policy

Before every deploy:

1. Stop writes if possible.
2. Export `/data` to a tarball.
3. Store backup outside the hosting volume.
4. Verify restore on a separate environment.

## Upload Policy

- Keep 5 MB app upload limit unless explicitly changed.
- Prefer Markdown/TXT or textual PDFs.
- Reject scanned PDFs unless OCR runtime is configured and validated.
- Monitor volume usage after every full-corpus import.

## Deployment Branch And Rollback

- Deploy from a stable branch after backend and frontend tests pass.
- Keep a recent data backup before deploying.
- Roll back code and data separately: code rollback does not automatically restore JSON/upload state.

## Single-Replica Requirement

Run only one backend replica while storage is JSON/file based. Multiple writers can corrupt or overwrite state because writes are read-modify-write against one JSON file.

## Detailed Railway Runbook

Use `docs/staging-launch-runbook.md` for the exact two-service Railway setup, tester creation command, smoke checklist, restart-persistence checks, backup procedure, and rollback flow.
