# Local Runtime Guide

This guide describes the verified local path for running Mentorium privately.

## Requirements

- Docker Desktop or Docker Engine with Docker Compose v2.
- Ports `3000` and `8000` available.
- Enough disk for uploaded source files plus JSON-derived artifacts. Start with at least 5-10 GB free for realistic experimentation.
- Optional: Python 3.12 and Node 22 for direct development outside Docker.

## Recommended Local Command Sequence

```bash
cp .env.example .env
docker compose build
docker compose up -d
docker compose ps
curl http://localhost:8000/api/exam-profiles
open http://localhost:3000
```

If `open` is not available, visit `http://localhost:3000` manually.

## Ports

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`

## Data Persistence

Compose stores backend data in the named volume `studyflow_data`, mounted at `/app/data`.

Files:

- `/app/data/study_data.json`
- `/app/data/uploads`

The backend also supports:

- `STUDYFLOW_DATA_FILE`
- `STUDYFLOW_UPLOAD_ROOT`

Use those only if you deliberately want a different data location.

## User Creation

Use the `/login` page if registration is available in the current UI. For API creation:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"student","password":"change-me-123","display_name":"Student"}'
```

Then log in at `/login`.

## Supported Uploads

- `.md`
- `.txt`
- textual `.pdf`

Limit: 5 MB per uploaded file.

Scanned PDFs usually produce an OCR-required state. OCR is disabled by default.

## Personal Full-Corpus Study Guidance

Personal-Study-MVP-A adds a real bounded textual study core:

- eligible textual study blocks show deterministic extractive summaries from source text;
- validated objective questions have backend-internal evidence-backed answer keys;
- answer review persists selected-answer attempts and derives correct/incorrect only when validation is supported;
- exact network retries reuse one idempotency key without duplicating the attempt;
- bounded owner-scoped attempt history survives repository reload and backend restart.

Attempts do not yet create weak-topic signals, suppress correct questions, prioritize errors, or alter future question order. No 24h/7d/30d SRS or other adaptive scheduler is active.

Each explicit answer submission requires a unique idempotency key. A network retry must reuse that key; after a confirmed response, a later attempt must use a new one. Attempt records are immutable and stored in the same owner-scoped JSON repository as other alpha state. Keep the backend at one replica and include the data volume in backups.

Current safe path:

1. Upload edital as `edital`.
2. Analyze edital.
3. Upload study materials as `study_material`.
4. Prepare each material.
5. Open `/study`.
6. Study blocks.
7. Use fixation questions as validated practice when the backend can derive correctness; otherwise treat them as ungraded prompts.
8. Mark blocks studied explicitly.
9. Check progress/review candidate.

Do not treat feedback as official exam correction. There is no public score, no gabarito reveal, no permanent mastery claim, and no executable cumulative review detail page yet.

## Backup

```bash
docker compose exec backend tar -czf /tmp/mentorium-data-backup.tgz /app/data
docker compose cp backend:/tmp/mentorium-data-backup.tgz ./mentorium-data-backup.tgz
```

## Restore

```bash
docker compose cp ./mentorium-data-backup.tgz backend:/tmp/mentorium-data-backup.tgz
docker compose exec backend tar -xzf /tmp/mentorium-data-backup.tgz -C /
docker compose restart backend frontend
```

## Restart

```bash
docker compose restart backend frontend
```

Cookie sessions are in memory, so users may need to log in again after backend restart. Data persists if the volume remains.

## Update/Rebuild

```bash
git pull
docker compose build
docker compose up -d
```

Before rebuilding for real study data, run a backup.

## Logs

```bash
docker compose logs -f backend
docker compose logs -f frontend
```

## Disk Usage

```bash
docker system df
docker volume ls
docker run --rm -v studyflow_data:/data alpine du -sh /data
```

## Development Without Docker

Backend:

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Frontend:

```bash
cd frontend
npm install
npm run dev
```

## QA Fixture

Development-only fixture for studied-material review QA:

```bash
docker compose exec backend python -m app.services.review_progress_qa_fixture
```

The fixture is explicit, idempotent, and disabled in production.

## Local Safety Notes

- Keep the instance private.
- Keep backups before uploading a real corpus.
- Avoid concurrent heavy writes with multiple testers.
- Do not expose `/inspection` publicly.
- Do not assume OCR, official correction, full adaptive scheduling, or simulado execution exists.
