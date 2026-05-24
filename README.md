# StudyFlow AI / Mentorium

Backend-first study platform with deterministic artifacts, user-scoped JSON persistence, bounded document processing, candidate/review-oriented edital and simulado planning, and a heavily tested no-leakage simulado runtime chain.

## Current Implementation Status

| Area | Status | Evidence / Notes | Next Step |
| --- | --- | --- | --- |
| Backend test health | `implemented_and_tested` | The full suite passed during this audit (`1372 passed, 5 warnings`), and the focused document/OCR/question/simulado audit slice also passed (`91 passed, 5 warnings`). | Keep full regression green before frontend integration work. |
| Document/PDF ingestion | `implemented_and_tested` | `app/services/document_pipeline.py` and `app/services/pdf_text_extraction.py` support TXT, Markdown, and text-based PDF extraction with chunk/section persistence and owner-only APIs. | Add richer parsing only if product needs it. |
| OCR/scanned PDF | `implemented_but_needs_manual_validation` | `app/services/ocr_adapter.py` provides an optional Tesseract-based OCR fallback. It is disabled by default, requires an external binary, and current tests prove safe fallback behavior plus mocked OCR success paths. | Validate with real scanned PDFs and a real OCR runtime before claiming production-ready scanned PDF support. |
| Edital ingestion | `partially_implemented` | `app/services/edital_ingestion.py` builds heuristic candidate sections, topics, bibliography items, exclusions, and weight hints. Tests prove deterministic `ready_for_review` and safe `insufficient_text` behavior. | Improve extraction quality and manual review surfaces. |
| Bibliography/material alignment | `partially_implemented` | `app/services/bibliography_alignment.py` computes candidate bibliography matches, topic coverage, gaps, and redundancy. It is tested, but still heuristic and candidate-based. | Tighten alignment quality and review tooling. |
| Question generation | `foundation_only` | The repo has tested blueprint and draft layers: `simulado_blueprint_builder.py`, `question_generation_blueprint.py`, `question_draft_generation.py`, answer/explanation guardrails, and question assembly. Drafts remain provisional and review-required. | Decide and implement the reviewed final-question workflow, if approved. |
| PSCPP question style profile | `metadata_only` | `app/services/question_style_profiles.py` exposes the canonical `marinha_dpc_pscpp_praticagem` profile with tested source-grounding, archetypes, scoring hints, and safety rules. | Reuse in any future final authoring/review tooling. |
| PSCPP question generation integration | `metadata_only` | PSCPP metadata enrichment and validation are tested across simulado, fixation, review, and summary-reading blueprint/draft flows. | Connect this metadata to any future final reviewed question production flow. |
| PSCPP study cycle profile | `metadata_only` | `app/services/study_cycle_profiles.py` exposes a tested PSCPP guidance profile, proportional weekly scaling, a 12-session rotation, and a question-style bridge. It does not create schedules. | Surface it in UI as editable guidance only. |
| Simulado generation | `foundation_only` | Upstream simulado generation is candidate/review-only. The code can build a simulado blueprint, question-generation blueprint, draft set, and non-executable question assembly, but not a verified complete executable prova with final new questions. | Verify or implement the reviewed final assembly/release path before claiming automatic simulado generation. |
| Simulado attempt/correction/score | `partially_implemented` | Attempt session, answer submission, correction shell/result, and score result artifacts are implemented and tested. The chain is bounded and deterministic, but execution shell and attempt session remain non-active/non-executable by design. | Decide whether a real executable simulado delivery flow should exist, then implement the minimal missing activation layer. |
| Runtime/apply/ledger chain | `implemented_and_tested` | The backend includes tested runtime guardrails and bounded artifacts for score -> progress guardrail -> runtime apply policy -> final event -> minimal ledger -> applied event ledger -> propagation guardrail -> controlled propagation apply. | Preserve invariants while deciding whether any broader runtime application is ever desired. |
| Minimal progress ledger | `implemented_and_tested` | `app/services/simulado_minimal_progress_ledger_apply.py` records minimal progress ledger entries with idempotency, rollback metadata, and no broader runtime mutation. | Keep as the narrowest runtime-safe apply surface. |
| Applied event ledger/idempotency | `implemented_and_tested` | `app/services/simulado_applied_event_ledger.py` records replay-safe, deduplicated applied-event entries from the minimal progress ledger apply. | Preserve as the auditable idempotency layer for downstream review. |
| Propagation guardrail | `implemented_and_tested` | `app/services/simulado_propagation_guardrail.py` creates user-scoped readiness artifacts and candidate propagation targets without mutating ranking, retention, scheduler, study cycle, curriculum graph, or adaptive tuning. | Keep as readiness-only unless propagation is explicitly approved in the future. |
| Controlled propagation apply | `implemented_and_tested` | `app/services/simulado_controlled_propagation_apply.py` records isolated controlled propagation ledger entries only. It is tested for idempotency, owner scope, no leakage, and no direct runtime mutation. | Keep ledger-only unless surface-specific propagation is explicitly approved later. |
| Frontend | `partially_implemented` | The repo contains a static app shell under `app/static/` with an inspection page and a read-only dashboard. There is no Next.js/React frontend, no integrated TSX prototype, and no evidence of a production API client layer. | Build the frontend app shell and API client on top of the already-tested backend surfaces. |
| Persistence | `partially_implemented` | Persistence is currently JSON-store based through `app/repositories/json_store.py`. User scoping and many artifact types are well covered by tests, but services still depend directly on the JSON store implementation. | Introduce cleaner repository boundaries before attempting PostgreSQL. |
| Deployment | `not_implemented` | The repo has no Docker image, staging config, cloud deployment config, or production packaging. Product/server readiness tests exist, but deploy infrastructure does not. | Add staging/deploy packaging after persistence and auth decisions are settled. |

## What is Safe to Claim Now

- The backend runtime chain is deterministic, user-scoped, and heavily tested.
- TXT, Markdown, and text-based PDF ingestion work today.
- OCR exists as an optional bounded fallback, not as a production-ready scanned-PDF promise.
- Edital ingestion, bibliography alignment, curriculum graph, study cycle, and simulado planning all exist as candidate/review artifacts.
- PSCPP question-style and PSCPP study-cycle profiles exist and are reusable as metadata layers.
- Minimal progress ledger apply, applied event ledger, propagation guardrail, and controlled propagation apply are implemented with explicit no-leakage and no-broad-mutation safeguards.
- Public answer key/gabarito exposure remains blocked across the tested simulado chain.
- The repo includes local cookie-based auth plus a static read-only dashboard/inspection shell.

## What Still Needs Verification

- Real scanned PDF support with a real OCR binary and representative documents.
- Full automatic simulado generation from edital + bibliography/material into a complete executable prova with new questions.
- Final question finalization and release behavior beyond blueprint/draft/assembly artifacts.
- Frontend app shell integration beyond the static dashboard.
- Backend API client integration for a modern frontend.
- Production-grade auth provider needs, if local auth is not enough for the intended product.
- PostgreSQL migration readiness.
- Deployment and staging readiness.

## Intentionally Deferred

- Broad runtime propagation into ranking, retention, scheduler, study cycle, curriculum graph, or adaptive tuning.
- RAG/vector retrieval.
- OCR provider expansion beyond the current optional adapter.
- PostgreSQL migration until the JSON-backed backend surfaces are stable enough to extract cleaner repository boundaries.
- Automatic scheduling, calendar mutation, or forced study plans.
- Public SaaS packaging, pricing, and payment flows.

## Key Docs

- [PSCPP question style profile](docs/exam-profiles/pscpp-question-style.md)
- [PSCPP study cycle profile](docs/exam-profiles/pscpp-study-cycle-profile.md)
