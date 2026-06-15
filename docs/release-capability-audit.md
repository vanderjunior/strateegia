# Release Capability Audit

Audit date: 2026-06-14

## Executive Verdict

Mentorium is a useful local/private alpha for organizing textual study materials and walking a student through a safe study workspace. It is not yet a complete adaptive exam-preparation environment.

## Personal-Study-MVP-A Update

Personal-Study-MVP-A moved the current textual study path beyond the Release-Capability-Audit-A placeholder state:

- Milestone 0 fixed the noisy mixed-format edital extraction regression so `Meteorologia` is detected conservatively.
- Eligible textual study blocks now use deterministic extractive summaries from source chunk text instead of the placeholder `Resumo em preparação para esta seção.`.
- Study-block objective questions now have backend-internal evidence-backed answer keys when one unambiguous source-supported answer can be derived.
- Answer review now persists bounded selected-answer attempts and derives `correct`, `incorrect`, or `ungraded` server-side.
- Incorrect validated attempts create weak-topic signals that feed reinforcement copy and cumulative-review candidate priority.
- Correct validated attempts are temporarily suppressed by a deterministic selection-round policy; there is no permanent mastery and no generic 24h/7d/30d SRS.
- The frontend still never receives answer keys, correctness inputs, mastery state, score, gabarito, raw chunks, or storage paths.

Updated verdicts after this sprint:

| Scenario | Verdict | Conditions |
| --- | --- | --- |
| A. Local personal alpha | `CONDITIONAL_GO` | Stronger than before for textual materials: grounded summaries, validated objective questions, persisted attempts, and bounded adaptation now exist. Backups and user review are still required. |
| B. Private 1-2 user staging | `CONDITIONAL_GO` | Still requires single replica, private access, persistent disk, and backup drill. |
| C. Full-corpus textual personal study | `CONDITIONAL_GO` | Conditional on textual sources, small corpus size, accepted extractive-question limitations, and manual review of outputs. |
| D. Adaptive question memory | `CONDITIONAL_GO` | Minimal deterministic memory exists for study-block questions; it is not a full scheduler. |
| E. Primary exam preparation environment | `NO_GO` | Still blocked by OCR/corpus coverage, limited deterministic question strategies, no executable cumulative review session, and no official correction/scoring. |
| F. Public production | `NO_GO` | Still blocked by JSON/file persistence, auth/session hardening, object storage, concurrency, observability, and security review. |

The current product can ingest an edital, prepare textual materials, show an ordered study path, expose extractive source-grounded summaries/key points, show objective questions with internal correctness when validated, persist selected-answer attempts, record explicit block-study progress, and show a cumulative review candidate with weak-topic signals. It still cannot prove syllabus sufficiency, execute a full cumulative review session, handle OCR-required corpora by default, or support public production.

## GO / NO-GO Verdicts

| Scenario | Verdict | Conditions |
| --- | --- | --- |
| A. Local personal alpha | `CONDITIONAL_GO` | Good for experimenting with textual `.md`, `.txt`, and textual `.pdf` content, as long as the user understands summaries/questions are candidates/placeholders and keeps backups. |
| B. Private 1-2 user staging | `CONDITIONAL_GO` | Use single replica, persistent volume, private access, backup/restore routine, and no public claims of adaptive grading. |
| C. Full-corpus personal study | `NO_GO` | Blocked by placeholder summaries, no reliable correctness model, no attempt memory, OCR gaps, and JSON concurrency/storage risk. |
| D. Adaptive question memory | `NO_GO` | Selected answers and correctness are not persisted for the current study-block review UI. |
| E. Primary exam preparation environment | `NO_GO` | The system cannot yet prove syllabus coverage, generate reliable questions, grade attempts, or schedule weak topics. |
| F. Public production | `NO_GO` | Needs transactional persistence, production auth/session design, upload storage, backup/restore, rate limits, monitoring, and security review. |

## Runtime Evidence

Synthetic API smoke with an isolated JSON store produced:

```text
register 201
login 200
upload_edital 201
analyze_edital 200 {'analysis_status': 'analyzed', 'topics_count': 2, 'subtopics_count': 3, 'bibliography_count': 2, 'warnings_count': 0}
prepare_material ... ready_for_study
summary_item {'status': 'ready', 'summary': 'O poder de policia consiste na atividade administrativa que limita direitos em favor do interesse publico. A atuacao deve observar competencia, finalidade e proporcionalidade. Exceto quando a lei autoriza medida imediata, a administracao deve respeitar o procedimento previsto.', 'key_points_count': 3, 'source_anchors_count': 3, 'generator_version': 'grounded-summary-v1', 'repeat_is_identical': true}
title_only_summary {'status': 'needs_review', 'key_points': [], 'source_anchors': []}
coverage {'coverage_status': 'partial', 'covered_subtopics_count': 2, 'partial_subtopics_count': 1, 'uncovered_subtopics_count': 0}
blocks {'blocks_status': 'ready', 'scope_status': 'connected_to_edital', 'blocks_count': 3}
questions {'question_status': 'ready', 'mode': 'review_only'} type multiple_choice with A-E alternatives
answer_review {'review_status': 'needs_review', 'result': 'needs_review'}
progress_before review_basis prepared_materials
progress_after studied_blocks_count 3, studied_materials_count 3, review_basis studied_materials
review_next basis studied_materials, materials_count 3, blocks_count 3
restart_summary preserved studied_materials_count 3
```

This proves the local path and restart persistence for synthetic textual content. It does not prove pedagogical quality.

Docker Compose smoke produced:

```text
docker compose build: backend and frontend images built
docker compose up -d: backend and frontend started
GET http://localhost:8000/api/exam-profiles -> 200
GET http://localhost:3000/ -> 200
review_progress_qa_fixture run twice -> same progress_event_ids, studied_materials_count 3, review_basis studied_materials
POST /api/auth/login through frontend proxy -> authenticated true
GET /api/study/progress/summary -> studied_blocks_count 7, prepared_materials_count 6, studied_materials_count 5, review_basis studied_materials
GET /api/study/review/next -> review_status needs_review, basis studied_materials, materials_count 5, blocks_count 5
GET /api/study/blocks -> blocks_count 6
```

Counts exceeded 3 because the local Compose QA volume already contained older fixture/user data. The deterministic fixture guarantee is therefore "at least 3" studied materials, not exactly 3, unless the QA volume is reset.

## Capability Matrix

| Capability | Status | Implementation files | API routes | Frontend surfaces | Persistence | Tests | Runtime evidence | Limitations | Next required implementation |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| Local auth | `USABLE_ALPHA` | `app/services/user_service.py`, `app/api/routes.py` | `/api/auth/register`, `/api/auth/login`, `/api/auth/me`, `/api/auth/logout` | `/login`, AppShell session | Users in JSON; sessions in memory | `test_user_persistence.py`, frontend auth tests | Register/login succeeded in smoke | Session lost on backend restart | Durable sessions or provider for staging |
| Edital upload | `USABLE_ALPHA` | `document_ingestion.py`, `material_service.py` | `POST /api/materials/upload` | `/materials/upload` | Upload file + metadata JSON | `test_material_upload.py` | `.md` edital uploaded | 5 MB limit | File-size policy and better upload UX |
| Textual PDF/TXT/MD | `USABLE_ALPHA` | `document_pipeline.py`, `pdf_text_extraction.py` | `POST /api/materials/{id}/process`, prepare/analyze routes | Material detail | Extracted text, chunks, sections persisted | Pipeline/PDF tests | MD/TXT path verified; tests cover PDF extraction | Large/complex PDFs not benchmarked | Corpus-size load testing |
| Scanned PDF OCR | `BLOCKED_BY_OCR` | `ocr_adapter.py` | Pipeline OCR path | Material/pipeline warnings | OCR metadata only unless enabled | OCR adapter tests | Not enabled in audit | Tesseract not required dependency; disabled by default | Real OCR runtime validation |
| Edital analysis | `PARTIAL` | `edital_ingestion.py` | `POST /api/materials/{id}/edital/analyze` | Material detail, `/editais` | Candidate result/state persisted | Edital tests; one full-suite fixture currently failing | Synthetic edital returned topics/subtopics/bibliography | Heuristic extraction; noisy fixture missed Meteorologia | Harden parser and manual review |
| Bibliography/reference matching | `PARTIAL` | `bibliography_alignment.py` | `/api/edital/{id}/align-bibliography`, `/alignment` | Limited/read surfaces | Alignment persisted | Bibliography tests | Source inspection | Token overlap, not proof of source adequacy | Product UI and semantic matching |
| Coverage estimation | `PARTIAL` | `routes.py`, `bibliography_alignment.py` | `GET /api/editais/{id}/coverage` | Edital detail | Computed from material contexts | Coverage tests | Synthetic coverage partial | Lexical estimate only | Coverage confidence model and review UI |
| Study blocks | `USABLE_ALPHA` | `routes.py` helpers | `GET /api/study/blocks`, `/study/session/next` | `/study` | Computed from prepared summaries | Study block/session tests | 3 blocks generated | Ordered list, not scheduler | Real cycle/scheduler contract |
| Block detail | `USABLE_ALPHA` | `routes.py` | `GET /api/study/blocks/{block_id}` | `/study/blocks/[blockId]` | Computed from material summary | Block detail tests | Detail returns bounded extractive summary/key points when source evidence is sufficient | Summary quality still requires validation with real corpora | Grounded question quality remains separate |
| Summaries/key points | `USABLE_ALPHA` | `_extractive_study_summary`, `_bounded_study_summary_item` in `routes.py` | `/api/materials/{id}/study/summary`, block detail | Material and block detail | Deterministically computed on read; no summary artifact writes | Summary, block-detail, session, and extraction regression tests | Source sentences, key points, bounded anchors, fingerprint, and generator version are returned deterministically | No LLM synthesis; insufficient/title-only/noisy source remains `needs_review`; pedagogical quality requires real-material validation | Validate extractive quality across representative exam corpora |
| Fixation questions | `PLACEHOLDER` | `_bounded_fixation_questions_response` | `GET /api/study/blocks/{id}/questions` | Block detail | Computed; not persisted | Fixation tests | A-E candidate alternatives returned | No answer key; candidates orient review | Reviewed question authoring and answer keys |
| Answer review | `READ_ONLY` | `_bounded_answer_review_response` | `POST /api/study/blocks/{id}/questions/{id}/answer/review` | Block detail feedback | Stateless response; no selected answer persisted | Answer review tests | Result `needs_review` for choice | No official correctness | Attempt/correction contract |
| Attempt memory | `MISSING` | Legacy `record_answer` exists but not current study UI path | Legacy `/questions/{id}/answer`, not study review | Not connected | Current selected answer not persisted | No current adaptive attempt tests | `reviewed_questions_count` remained 0 after answer review smoke | Cannot suppress/prioritize questions | Persist attempts from review UI after correction model |
| Reinforcement | `READ_ONLY` | Answer review helper | Included in answer-review response | `Reforço sugerido` panel | Stateless | Reinforcement UI tests | Message returned | Does not alter schedule | Persist weak-topic signals |
| Explicit progress | `USABLE_ALPHA` | `record_study_progress_event`, summary helpers | `/api/study/progress/events`, `/api/study/progress/summary` | Block detail button, `/study` card | JSON event metadata | Progress tests | Marking blocks studied persisted | Explicit only; no material completion | Progress UI/summary hardening |
| Studied-material derivation | `USABLE_ALPHA` | `_studied_material_ids_from_blocks` | Progress summary/review next | `/study` renders backend basis | Computed from explicit events | Review progress tests | 3 studied materials after all blocks marked | Requires safe block-material mapping | QA with larger material structures |
| Cumulative review candidate | `READ_ONLY` | `_bounded_next_review_block_response` | `GET /api/study/review/next` | Compact `/study` card | Computed; no review record | Review block tests | basis `studied_materials` after progress | No detail page or completion | Review detail and completion semantics |
| Curriculum graph/study cycle routes | `PARTIAL` | `curriculum_graph_builder.py`, `study_cycle_orchestrator.py` | `/curriculum-graph/...`, `/study-cycle/...` | Not main `/study` UX | Candidate artifacts persisted | Backend tests | Source/test evidence only | Candidate/review artifacts; not main scheduler | Decide product integration |
| Simulado scaffold | `PLACEHOLDER` | Many `simulado_*` services | `/simulado-*` routes | No executable student UI | Candidate artifacts persisted | Many backend tests | Full suite passes most scaffold tests | No final executable simulado for students | Separate simulado planning/implementation |
| Persistence | `USABLE_ALPHA` local, `PARTIAL` staging | `json_store.py`, Docker volume | All routes | All surfaces | JSON + uploaded files | User/material/progress tests | Restart smoke preserved JSON state | No transaction locks; single-replica only | PostgreSQL/object storage |
| Deployment | `PARTIAL` | Dockerfiles, Compose, env examples | N/A | N/A | Named Compose volume | Build/test evidence | Frontend build passed; Compose not fully rebuilt in audit yet | Needs private persistent volume and runbook | Deploy dry run |

## Edital And Bibliography Answers

- Can a real edital with complex numbering and sections be processed? `PARTIAL`. Textual editais can be processed, but extraction is heuristic and one noisy stabilization fixture failed during the full suite because `Meteorologia` was not detected.
- Can bibliography guide material selection? `PARTIAL`. Bibliography alignment exists and uses overlap between references/material text, but it is candidate-based.
- Can the system prove every syllabus topic has sufficient source material? `MISSING`. It estimates coverage and gaps; it cannot prove sufficient taught content.
- Does coverage mean lexical mention or actual taught content? Mostly lexical/token overlap with section/chunk metadata and excerpts.

## Material Ingestion

Supported:

- `.txt`, `.md`, textual `.pdf`.
- Markdown headings become sections.
- Text is split into deterministic chunks with default max chunk size of 500 characters.
- Upload limit is 5 MB per file.

Unsupported or blocked:

- Scanned PDFs without OCR.
- Compressed/image PDFs that extract no text.
- Very large full corpus uploads beyond current upload limit and JSON storage assumptions.

Disk amplification:

- Original upload is stored under uploads.
- Extracted text, sections, chunks, pipeline state, edital extraction, and alignment/candidate artifacts are stored in JSON.
- For large text corpora, JSON can grow quickly because extracted text and chunk text are duplicated.

## Study Cycle Assessment

Current `/study` is an ordered block list with a continuation action. It is not a true cyclical scheduler.

What exists:

- Blocks are derived from prepared study material summaries.
- Blocks are sorted by edital connection, topic/subtopic order, readiness, created time, and material id.
- Cumulative review appears when enough prepared or studied materials exist.

What does not exist:

- No automatic resurfacing of older content.
- No performance-aware ordering.
- No historical weak-question sample after every 3-material review.
- No calendar/cycle engine connected to `/study`.

## Summaries Assessment

Classification: `USABLE_ALPHA`.

Eligible textual blocks now select bounded, non-duplicated source statements for the summary and key points. The response includes safe source anchors, a deterministic content fingerprint, generator version, and generation method. The implementation computes on read and does not persist duplicate summary artifacts.

Title-only, empty, formatting-noise, and otherwise insufficient source content remains `needs_review` with no fabricated summary. This is deterministic extractive study support, not LLM synthesis or proof of pedagogical completeness; representative real-material validation remains necessary.

## Questions Assessment

Runtime output shows multiple-choice alternatives such as:

```json
[
  {"id": "A", "text": "Revisar Atos administrativos."},
  {"id": "B", "text": "Relacionar Direito Administrativo ao resumo do bloco."}
]
```

Classification: `PLACEHOLDER`.

Questions are selectable review candidates/templates. They are not reliable exam questions because there is no correct alternative or official answer key. A student can use them as prompts for revisiting a block, not as a safe proof of learning.

## Attempt Memory And Adaptation

Current answer review does not persist:

- selected alternative;
- answer timestamp as an attempt;
- correct/incorrect state;
- attempt count per current question;
- last presentation;
- next eligible presentation;
- weakness category;
- reinforcement history.

The backend has legacy answer/progress models and simulado scaffold artifacts, but the current study-block answer review flow is stateless and not connected to adaptive scheduling. Therefore adaptive question memory is `MISSING`.

## Review And Reinforcement

Answer review returns conservative feedback and a reinforcement object. It does not alter future study order. Cumulative review is a read-only candidate assembled from blocks; it cannot be opened as a review detail page or completed.

## Persistence Assessment

| State | Persisted? | Store | Restart survival | Redeploy survival | Notes |
| --- | --- | --- | --- | --- | --- |
| Users | Yes | JSON | Yes | Yes if volume kept | Password hashes persisted. |
| Sessions | No | In-memory app state | No | No | Re-login required. |
| Materials metadata | Yes | JSON | Yes | Yes if volume kept | User-scoped. |
| Uploaded files | Yes | `data/uploads` | Yes | Yes if volume kept | Not object storage. |
| Extracted text | Yes | JSON | Yes | Yes if volume kept | Can grow quickly. |
| Sections/chunks | Yes | JSON | Yes | Yes if volume kept | Chunk text stored in JSON. |
| Edital analysis | Yes | JSON | Yes | Yes if volume kept | Candidate-only. |
| Study blocks | Computed | Routes | Recomputed | Recomputed | Derived from summaries/edital. |
| Question candidates | Computed | Routes | Recomputed | Recomputed | No stable question bank beyond deterministic IDs. |
| Answer review | No | Stateless | No | No | No selected answer persisted. |
| Progress events | Yes | JSON | Yes | Yes if volume kept | Explicit events only. |
| Review candidate | Computed | Routes | Recomputed | Recomputed | No review record. |
| Simulado scaffold | Yes if routes used | JSON | Yes | Yes if volume kept | Candidate artifacts, not student execution. |

Safety:

- One local user: acceptable alpha with backups.
- Two private users: possible but risky; avoid simultaneous writes and keep backups.
- Public production: not safe; JSON file writes and local uploads are not production-grade.

## Dependency Audit

- Backend runtime target: Python 3.12 in Docker.
- Backend dependencies: FastAPI, Uvicorn, pytest, httpx, pdfplumber, PyMuPDF, python-multipart.
- OCR dependencies are intentionally optional and absent from `requirements.txt`.
- Frontend: Next.js 15, React 19, Node 22 container.
- `package-lock.json` exists and frontend `npm run test` / `npm run build` passed.
- `pyproject.toml` is absent; backend packaging is requirements/Dockerfile based.

## Validation

Backend full suite:

- Command: `PYTHONPATH=./.python_packages /Users/vjr/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest`
- Result: `1518 passed`, `4 failed`, `5 warnings`.
- Failures:
  - Three README expectation failures, addressed by this README rewrite and confirmed fixed in a focused rerun.
  - One real existing extraction failure: `tests/test_edital_extraction_stabilization_fixtures.py::test_noisy_mixed_format_fixture_stays_conservative_and_does_not_crash` expected `Meteorologia`, but extraction did not detect it.
- Focused rerun after README rewrite: README readiness tests passed; the same noisy-edital extraction failure remained.

Frontend:

- `npm run test`: `57 passed`, `494 tests`.
- `npm run build`: passed.
- Initial parallel `npm run typecheck` failed from known `.next/types` race while build was running; sequential rerun passed.

## P0 / P1 / P2 / P3 Blockers

P0 required before full personal study:

- Validate source-grounded summary quality across representative real exam materials.
- Correctness model and reviewed answer keys.
- Persist selected answers/attempts.
- Adaptive question memory and scheduling.
- Better edital extraction for noisy/complex structures.
- Backup/restore command tested on real corpus.

P1 required before second external tester:

- Private staging with persistent disk and single replica.
- Disable/protect inspection in production.
- Upload size and storage budget policy.
- Error/recovery UX for OCR-required PDFs.

P2 required before broader production:

- PostgreSQL or transactional persistence.
- Object storage for uploads.
- Production auth/session provider.
- Concurrency controls and observability.

P3 later:

- Production OCR.
- Executable simulados with correction/scoring.
- Dashboards/charts and richer review UI.

## Recommended Next Sprint

Implement attempt persistence and correctness planning before expanding review UI:

1. `Correction-Planning-A`: answer-key/correction semantics.
2. `AttemptMemory-B`: persist selected answers as ungraded attempts first.
3. `QuestionQuality-B`: generate reviewed, answerable objective questions with reliable keys.
4. Validate the grounded-summary output against representative real exam materials without expanding it into generated or adaptive content.
