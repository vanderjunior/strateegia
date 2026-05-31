# Coverage Contract Plan

## Purpose

Define the next read-only contract for comparing an analyzed edital against user materials without exposing raw content or adding study execution behavior.

Backend Coverage-B and frontend Coverage-C proxy/API wrapper are implemented. Visible UI migration is still pending.

## Current Prerequisites

- The user must be authenticated.
- The edital must exist in the current user scope.
- Coverage should require at least one bounded edital analysis with `analysis_status` of `analyzed` or `needs_review` and nonzero `topics_count` or `subtopics_count`.
- `analysis_status: "not_ready"` means the edital was not safely analyzed and must not produce real coverage.
- User materials are already classified by bounded `material_type`.
- Candidate source materials may include `study_material`, `bibliography`, and later `previous_exam`, but the edital itself remains the source of scope.
- Existing bounded material reads expose metadata, counts, and status only. They do not expose raw text, chunks, OCR, or storage paths.

## Implemented Endpoint

Implemented backend endpoint:

```http
GET /api/editais/{edital_id}/coverage
```

Rationale:

- Coverage is anchored to the edital scope, so the edital id should be the primary route key.
- The endpoint can enforce owner scope through the existing user-scoped edital repository lookup.
- Multiple materials may be considered for one edital, so a material-scoped route would make the contract feel narrower than the product concept.
- `GET /api/materials/{document_id}/edital/coverage` can remain an alternative only if a future flow needs coverage from an uploaded edital material before an edital extraction id exists.

## Read-Only Behavior

The endpoint must:

- require authentication
- use `JsonStudyRepository.for_user(user_id)` or the established user-scoped repository pattern
- return `401` for unauthenticated requests
- return `404` for missing or non-owner editais without revealing ownership
- return bounded `not_ready` coverage for `analysis_status: "not_ready"`
- return deterministic, idempotent results for the same persisted data
- never mutate progress, sessions, scheduling, materials, edital analysis, or alignment state
- never generate questions, simulados, study sessions, or answer keys
- never run OCR, LLM calls, or background processing

## Implemented Response Shape

```json
{
  "edital_id": "edital:doc-123",
  "analysis_status": "analyzed",
  "coverage_status": "partial",
  "topics_count": 3,
  "subtopics_count": 9,
  "covered_subtopics_count": 4,
  "partial_subtopics_count": 2,
  "uncovered_subtopics_count": 3,
  "out_of_scope_materials_count": 1,
  "materials_considered_count": 5,
  "items": [
    {
      "topic_id": "topic-1",
      "label": "Lingua Portuguesa",
      "subtopics_count": 3,
      "covered_count": 1,
      "partial_count": 1,
      "uncovered_count": 1,
      "status": "partial"
    }
  ],
  "source": "user_scope"
}
```

Allowed top-level fields:

- `edital_id`
- `analysis_status`
- `coverage_status`
- `topics_count`
- `subtopics_count`
- `covered_subtopics_count`
- `partial_subtopics_count`
- `uncovered_subtopics_count`
- `out_of_scope_materials_count`
- `materials_considered_count`
- `items`
- `source`

Allowed item fields:

- `topic_id`
- `label`
- `subtopics_count`
- `covered_count`
- `partial_count`
- `uncovered_count`
- `status`

Allowed statuses:

- `analysis_status`: `analyzed`, `needs_review`, `not_ready`, `failed`, `unknown`
- `coverage_status`: `not_ready`, `partial`, `ready_for_review`, `needs_review`, `unknown`
- item `status`: `covered`, `partial`, `uncovered`, `needs_review`

Forbidden response fields:

- raw edital text
- raw material text
- `extracted_text`
- raw chunks or sections
- OCR dumps
- bibliography evidence snippets
- raw bibliography bodies
- matched excerpt bodies
- base64 payloads
- `storage_path` or private paths
- token, cookie, session, or password fields
- answer key, gabarito, correctness, or correction fields
- worker/job/internal traces

## Matching Strategy

Initial implementation should be deterministic and conservative:

- Use bounded edital topic and subtopic labels as the scope source.
- Consider material filenames, `material_type`, bounded material metadata, and bounded section titles if they are already available through user-scoped repository data.
- Do not return section bodies, chunk bodies, or evidence snippets.
- Prefer `needs_review` or `partial` when confidence is low.
- Avoid claiming `covered` unless there is strong label/metadata overlap.
- Treat a match against a filename or type alone as weak unless reinforced by additional bounded metadata.
- Keep matching idempotent and synchronous for the first read-only contract.

Implementation note:

- Existing bibliography alignment internals already compute richer evidence and topic coverage, but that shape is too operational for the browser-facing product contract. Coverage-B exposes a new bounded summary instead of passing through alignment evidence.

## Material Type Behavior

- `edital`: source of official scope; not a study coverage source.
- `study_material`: primary candidate for topic/subtopic coverage.
- `bibliography`: reference or support candidate; useful for confidence but not sufficient alone for full coverage.
- `previous_exam`: later style/question reference; not a default coverage source in the first contract.
- `note`: secondary support; likely `needs_review` unless clearly matched.
- `other`: secondary support; likely `needs_review` or ignored.
- `unknown`: ignored or `needs_review` depending on bounded metadata quality.

## Frontend Implications

Coverage-C adds:

- same-origin Next proxy at `GET /api/editais/{editalId}/coverage`
- frontend API helper `fetchEditalCoverage(editalId)`
- proxy-side whitelist sanitization for top-level and item fields
- product-safe mapping for auth-required, not-found, not-ready, offline, unsupported, and invalid-response states

Future UI should show simple read-only labels:

- `Cobertura do edital`
- `Topicos com material`
- `Topicos sem material`
- `Materiais fora do edital`
- `Precisa de conferencia`

Future UI must not show:

- raw excerpts
- chunk or section body text
- internal scoring
- backend, pipeline, worker, or job terminology
- automatic study plan language before a later StudyPlan contract exists

Coverage should not unlock concrete study by itself unless the future product rule explicitly requires both analyzed edital lifecycle and acceptable coverage state.

## Test Coverage

Backend tests:

- `401` unauthenticated
- `404` missing or non-owner edital
- `not_ready` edital returns bounded `coverage_status: "not_ready"`
- analyzed edital with no candidate materials returns all subtopics uncovered
- analyzed edital with matching bounded material metadata returns conservative `partial` or `covered` counts
- edital source material is excluded from material consideration
- `unknown` material does not falsely cover edital subtopics
- low-confidence matches remain `needs_review`
- response shape is deterministic and bounded
- repeated `GET` is idempotent
- no raw text, chunks, OCR, storage paths, token/session fields, answer keys, gabarito, or evidence snippets leak

Frontend tests:

- same-origin proxy preserves bounded coverage fields only
- API wrapper maps `401`, `404`, `502`, and `503`
- API wrapper maps `coverage_status: "not_ready"` to a product-safe not-ready result
- API wrapper maps invalid JSON or invalid bounded shape to `invalid_response`
- adapter maps coverage states to product labels
- `not_ready` coverage does not unlock study, PSCPP, Ciclo, Questões, Simulado, or progress UI
- UI does not show raw/internal copy or backend/pipeline terminology

## Explicit Non-Goals

- no visible coverage UI in Coverage-C
- no question generation
- no simulado generation or execution
- no progress mutation
- no scheduler
- no OCR
- no LLM
- no PostgreSQL
- no external auth provider or signup
- no automatic study plan
- no exposure of raw content or storage paths

## Recommended Implementation Sequence

1. Coverage-D: add minimal read-only card on edital detail.
2. Coverage-QA: validate browser, API, no-leakage, and conservative gating.
3. StudyPlan-Planning-A: define study-plan contract only after coverage is validated.
