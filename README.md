# Mentorium

Mentorium is an alpha study workspace for organizing edital-driven study materials. It can upload and analyze an edital, upload and prepare textual study materials, create a visible study path, show bounded source-grounded summaries/key points, present objective fixation questions with internal evidence-backed correctness when validation is possible, persist selected-answer attempts, record explicit block-study progress, and show a cumulative review candidate informed by studied materials and weak-topic signals.

It is still not a full exam-preparation system. The new personal-study MVP is deterministic and source-grounded for eligible textual content, but it is not an official correction system, does not expose public scores/gabaritos, does not use OCR by default, does not provide a review detail session yet, and still relies on JSON/file persistence for local/private alpha use.

## Current Alpha Status

This repository is best described as a local/private alpha. It is now suitable for one student to experiment with textual materials using grounded summaries, validated objective questions when evidence is sufficient, persisted attempts, and a small deterministic adaptive queue. It is not yet safe to rely on as the primary preparation environment for a real exam until OCR/corpus coverage, question quality, review execution, backup procedures, and production persistence are hardened.

## What Works Today

- Local username/password authentication with a cookie session.
- Upload of `.txt`, `.md`, and textual `.pdf` files up to 5 MB per upload.
- Edital upload and heuristic candidate analysis of sections, topics, subtopics, bibliography, exclusions, and weights.
- Bibliography/material/topic alignment as candidate-based lexical/heuristic evidence.
- Study material preparation with text extraction, deterministic chunking, and Markdown-heading section detection.
- `/study` with `Continue seus estudos`, `Seu caminho de estudo`, compact `Revisao acumulada`, and compact `Acompanhamento do estudo`.
- Study block detail with extractive summary rows, key points, fixation questions, persisted answer review feedback, advisory reinforcement, and explicit `Marcar bloco como estudado`.
- Bounded attempt memory for study-block questions: selected answer, correctness state when validated, attempt count, weak-topic signals, and deterministic queue ordering.
- Progress events for explicit block study actions and conservative studied-material derivation when every block for a study material is marked studied.
- Read-only cumulative review candidate based on prepared materials or conservatively derived studied materials.
- Docker Compose local runtime with a named volume for `/app/data`.

## What Does Not Work Today

- No OCR by default. `ocr e desabilitado por padrao`; optional OCR requires Tesseract-compatible runtime validation and does not run during ordinary upload. OCR `nao roda no upload`.
- No answer-key/gabarito reveal. Correctness remains internal and source-evidence backed only for validated study-block questions.
- No official correction, score, percentage, ranking, or exam acertos/erros model.
- No permanent mastery claim. Correct answers are temporarily suppressed by a bounded selection-round policy only.
- No revised/generated summary after weak answers; reinforcement points back to source-grounded summaries and weak topics.
- No review detail page and no review-completed state.
- No public production deployment, PostgreSQL, object storage, provider/signup, payments, or SaaS hardening.
- Simulados exist only as backend scaffold/candidate artifacts; there is no final executable student simulado flow.

## Capability Matrix

| Capability | Status | Evidence | Limitation |
| --- | --- | --- | --- |
| Auth | `USABLE_ALPHA` | `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me` | Sessions are in memory; login is required after backend restart. |
| Edital upload/analyze | `USABLE_ALPHA` | `POST /api/materials/upload`, `POST /api/materials/{id}/edital/analyze` | Heuristic candidate extraction; complex edital structures need review. |
| Bibliography guidance | `PARTIAL` | `POST /api/edital/{id}/align-bibliography` | Candidate overlap only; not proof of sufficient source material. |
| Material ingestion | `USABLE_ALPHA` | TXT/MD/textual PDF pipeline tests and API smoke | 5 MB upload limit; scanned PDFs blocked without OCR. |
| Coverage estimation | `PARTIAL` | `GET /api/editais/{id}/coverage` | Lexical/topic-token estimate, not semantic sufficiency proof. |
| Study path | `USABLE_ALPHA` | `GET /api/study/blocks`, `/study` UI | Ordered blocks, not true cyclical scheduling. |
| Summaries | `USABLE_ALPHA` | Extractive source sentences in `GET /api/materials/{id}/study/summary` and block detail | Deterministic and bounded; insufficient evidence stays `needs_review`. |
| Questions | `USABLE_ALPHA` | `GET /api/study/blocks/{id}/questions` | Validated only when one evidence-backed answer can be derived; otherwise fallback stays ungraded. |
| Answer review | `USABLE_ALPHA` | `POST /api/study/blocks/{id}/questions/{id}/answer/review` | Persists attempts and derives correct/incorrect only for validated questions; no official correction. |
| Attempt memory/adaptation | `USABLE_ALPHA` | `study_question_attempts` JSON container and adaptive queue tests | Bounded deterministic policy; no permanent mastery or fixed 24/7/30-day SRS. |
| Reinforcement | `PARTIAL` | Incorrect validated attempts create weak-topic signals used by review candidate | Advisory only; does not create a review session or material completion. |
| Progress events | `USABLE_ALPHA` | `POST /api/study/progress/events`, `GET /api/study/progress/summary` | Explicit events only; no automatic completion. |
| Cumulative review | `READ_ONLY` | `GET /api/study/review/next` | Candidate only; no detail page or completion state. |
| Simulado | `PLACEHOLDER` | Simulado blueprint/shell routes and tests | Sem geracao final de questoes; sem execucao/correcao de simulados. |
| Persistence | `USABLE_ALPHA` for one local user | `JsonStudyRepository`, `data/study_data.json`, `data/uploads` | Single JSON file; not public-production safe. |
| Deployment | `PARTIAL` | Dockerfiles and Compose exist | Needs persistent volume, backups, single replica, secure env. |

## Architecture

- Backend: FastAPI app in `app/main.py` and `app/api/routes.py`.
- Storage: JSON repository in `app/repositories/json_store.py`, with uploads and derived artifacts under `data/uploads`.
- Frontend: Next.js app in `frontend/`, using same-origin proxy routes under `frontend/app/api`.
- Main product routes: `/`, `/login`, `/dashboard`, `/editais`, `/materials`, `/study`, `/study/blocks/[blockId]`.
- Internal/legacy diagnostics: `/inspection`, `/api/inspection/runtime`, `/api/dashboard/overview`.
- The public frontend nao chama, encapsula ou reaproveita `/api/inspection/runtime` for the study path.
- Candidate/future backend surfaces include curriculum graph, study cycle candidato, simulado blueprint, question drafts, correction shells, and runtime guardrails.

## Supported File Formats

- `.md`: supported, with headings used as section boundaries.
- `.txt`: supported as plain text.
- textual `.pdf`: supported through PyMuPDF first, with pdfplumber fallback.
- scanned/compressed image PDFs: `BLOCKED_BY_OCR` unless optional OCR is deliberately enabled and verified.
- unsupported upload types are rejected.

## OCR Status

OCR is optional and disabled by default. The code includes `app/services/ocr_adapter.py`, which can use Tesseract through `pytesseract` if configured, but `pytesseract` is intentionally not in `requirements.txt`. This keeps OCR optional for local/private alpha and avoids making heavy OCR dependencies mandatory.

## Local Docker Quick Start

Como instalar:

```bash
cp .env.example .env
docker compose build
docker compose up -d
```

Como executar:

- Frontend: `http://localhost:3000`
- Backend: `http://localhost:8000`
- Backend health smoke: `curl http://localhost:8000/api/exam-profiles`

Create a user from the UI at `/login`, or use `POST /api/auth/register` on the backend. The app does not require a production auth bypass.

## Environment Variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_ENV` | `development` | `development`, `test`, or `production`. |
| `STUDYFLOW_DATA_FILE` | `data/study_data.json` | JSON data file. |
| `STUDYFLOW_UPLOAD_ROOT` | `data/uploads` | Upload/artifact root. |
| `NEXT_PUBLIC_API_BASE_URL` | `http://127.0.0.1:8000` | Browser-visible backend base for local dev. |
| `BACKEND_INTERNAL_URL` | `http://127.0.0.1:8000` | Frontend server-to-backend proxy base. |
| `NEXT_PUBLIC_USE_MOCK_API` | `false` | Mock mode toggle. |
| `ENABLE_INSPECTION` | dev true | Internal inspection surface. |
| `REQUIRE_AUTH_FOR_INSPECTION` | production true | Protects inspection. |
| `INSPECTION_ALLOWED_IN_PRODUCTION` | `false` | Must stay false unless explicitly secured. |
| `ENABLE_OCR` | `false` | Optional OCR adapter toggle. |
| `OCR_ENGINE` | `tesseract` | Optional OCR engine setting. |
| `OCR_LANGUAGE` | `por+eng` | Optional OCR language. |
| `OCR_MAX_PAGES` | `5` | Optional OCR page cap. |

Inspection routes are for internal debug use only. In producao, keep `ENABLE_INSPECTION=false`, `REQUIRE_AUTH_FOR_INSPECTION=true`, and `INSPECTION_ALLOWED_IN_PRODUCTION=false` unless there is a deliberate private operations reason to expose them.

## Persistent Data Directories

Docker Compose mounts a named volume at `/app/data`. Inside it:

- `/app/data/study_data.json` stores users, material metadata, extracted text, sections, chunks, analyses, progress events, and candidate artifacts.
- `/app/data/uploads` stores uploaded source files.

Backup:

```bash
docker compose exec backend tar -czf /tmp/mentorium-data-backup.tgz /app/data
docker compose cp backend:/tmp/mentorium-data-backup.tgz ./mentorium-data-backup.tgz
```

Restore:

```bash
docker compose cp ./mentorium-data-backup.tgz backend:/tmp/mentorium-data-backup.tgz
docker compose exec backend tar -xzf /tmp/mentorium-data-backup.tgz -C /
docker compose restart backend frontend
```

## User Creation

Use `/login` in the frontend and choose the registration flow if available, or call:

```bash
curl -X POST http://localhost:8000/api/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"username":"student","password":"change-me-123","display_name":"Student"}'
```

Then log in through `/login`. Passwords are hashed with PBKDF2 in the JSON store, but the app is still alpha and should not be exposed publicly without additional controls.

## Running Tests

Como rodar os testes:

Backend:

```bash
PYTHONPATH=./.python_packages /Users/vjr/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest
```

Frontend:

```bash
cd frontend
npm run test
npm run build
npm run typecheck
```

Run `npm run build` and `npm run typecheck` sequentially to avoid `.next/types` races.

## Frontend Development

```bash
cd frontend
npm install
npm run dev
```

Set `BACKEND_INTERNAL_URL=http://127.0.0.1:8000` and `NEXT_PUBLIC_USE_MOCK_API=false` for real backend integration.

## Backend Development

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Python 3.12 is the Docker/runtime target. The local Codex audit used a bundled Python 3.12 runtime because the vendored `.python_packages` native wheels are CPython 3.12 wheels.

## Private Staging Deployment

Primary recommendation today: local Docker + Tailscale for one or two testers. This best matches the current JSON/file persistence and single-replica assumptions.

Fallback: Railway Hobby or Render paid service with a persistent volume/disk mounted at `/app/data`, one backend replica, separate frontend service, explicit backups, and private access controls.

Heroku-style ephemeral dynos are not a good fit unless data is moved out of the local filesystem.

## Seguranca, Security And Privacy Notes

- Uploaded material text and extracted chunks are persisted in the JSON data file and upload directory.
- Cookie sessions are in memory; backend restart requires login again.
- The repository has internal inspection and scaffold routes that should not be exposed in production.
- Em producao, keep inspection disabled unless it is explicitly authenticated and protected.
- No public SaaS security review has been completed.
- JSON/file storage is acceptable for local alpha, risky for two concurrent staging users, and not safe for public multi-user production.

## Known Limitations

- `limita`: 5 MB upload limit and local disk amplification from uploads plus extracted text/chunks.
- Heuristic edital parsing can miss topics in noisy mixed formatting.
- Coverage is lexical/candidate-based and cannot prove every syllabus topic has sufficient source content.
- Study blocks are still mostly ordered by backend-derived metadata; adaptive behavior currently applies to the bounded question queue and review weak-topic signals.
- Extractive summaries depend on eligible textual source evidence and are not full teacher-authored explanations.
- Fixation questions expose no gabarito; internal correctness exists only for validated evidence-backed questions.
- Reinforcement influences weak-topic signals and review candidate priority, but does not create a full review session.
- Cumulative review is read-only and cannot be completed.
- Inspection surfaces exist for internal development only.

## Roadmap To Full Adaptive Study

P0 before full personal study:

- Broader quality validation for extractive summaries and deterministic questions across real edital/material corpora.
- Review detail/session route that can execute cumulative review safely.
- OCR decision and validation for scanned PDFs, or explicit product limitation to textual files only.
- Backup/restore drill against a real personal corpus.
- Review detail page with completion semantics after progress contract.

P1 before second external tester:

- Backup/restore drill, disk quota guidance, and concurrency hardening.
- Better edital parsing for complex numbering/noisy formats.
- Private deployment checklist with persistent disk and secure inspection settings.

P2 before broader production:

- PostgreSQL or transactional storage.
- Object storage for uploads.
- Production auth/session provider.
- Observability, rate limiting, and operational runbooks.

P3 later:

- OCR production enablement.
- Simulados with final reviewed questions, execution, correction, and scoring.
- Rich progress charts and long-term analytics.
