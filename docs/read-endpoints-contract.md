# Bounded User-Scoped Read Endpoints Contract

## Purpose

Define the dedicated bounded read endpoints needed after the initial `/api/dashboard/overview` interim strategy.

This document records the bounded read contracts that are implemented or planned for protected read surfaces.

## Current Interim State

- `GET /api/dashboard/overview` remains an authenticated, user-scoped summary surface.
- The frontend same-origin Next proxies now target dedicated bounded endpoints for:
  - `GET /api/materials`
  - `GET /api/editais`
  - `GET /api/materials/{document_id}/summary`
  - `GET /api/editais/{edital_id}/summary`
- The dashboard overview is no longer the source for materials/editais list proxies.
- Backend `GET /api/materials/{document_id}/pipeline/summary` now provides the bounded pipeline detail contract.
- Frontend pipeline detail uses the same-origin bounded pipeline summary proxy.
- Backend `GET /api/editais/{edital_id}/coverage` now provides a read-only bounded edital x materials coverage contract; frontend proxy/UI migration is pending.

## Why Dedicated Endpoints Are Needed

- `GET /api/dashboard/overview` is a summary surface, not a list contract.
- `GET /api/documents` is too broad for direct frontend use because `Document` can carry fields like `source_excerpt`, generated summaries, and question artifacts.
- Material, pipeline, edital, and alignment repository data already exist in user scope, but the browser should receive only bounded metadata.

## Proposed Endpoint Inventory

### Phase 1: first dedicated list endpoints

- `GET /api/materials`
- `GET /api/editais`

### Phase 2: bounded summary/detail endpoints

- `GET /api/materials/{document_id}/summary`
- `GET /api/editais/{edital_id}/summary`

### Phase 3: recent operational surfaces

- `GET /api/materials/{document_id}/pipeline/summary`
- `GET /api/pipeline/recent`

### Phase 4: coverage reads

- `GET /api/editais/{edital_id}/coverage`

### Later

- `GET /api/study/today`

## Recommended Implementation Order

1. `GET /api/materials`
2. `GET /api/editais`
3. `GET /api/materials/{document_id}/summary`
4. `GET /api/editais/{edital_id}/summary`
5. `GET /api/materials/{document_id}/pipeline/summary`
6. `GET /api/editais/{edital_id}/coverage`
7. `GET /api/pipeline/recent`
8. `GET /api/study/today`

## Proposed Response Shapes

### `GET /api/materials`

Purpose:
- return a bounded user-scoped list of uploaded materials and their safe processing state
- implemented in ReadEndpoints-B as an authenticated, user-scoped, metadata-only endpoint

Implemented shape:

```json
{
  "items": [
    {
      "document_id": "doc-123",
      "display_filename": "roteiro-praticagem.pdf",
      "content_type": "pdf",
      "material_type": "study_material",
      "created_at": "2026-05-27T00:00:00Z",
      "updated_at": "2026-05-27T00:05:00Z",
      "processing_status": "ready_for_review",
      "extraction_status": "textual_pdf",
      "chunk_count": 12,
      "section_count": 4,
      "review_state": "ready_for_review",
      "warnings_count": 0,
      "latest_pipeline_status": "metadata_ready"
    }
  ],
  "count": 1,
  "source": "user_scope"
}
```

Allowed fields:
- `document_id`
- `display_filename`
- `content_type`
- `material_type`
- `created_at`
- `updated_at`
- `processing_status`
- `extraction_status`
- `chunk_count`
- `section_count`
- `review_state`
- `warnings_count`
- `latest_pipeline_status`

Forbidden fields:
- `extracted_text`
- `text`
- chunk bodies
- section bodies
- OCR dump
- base64 payload
- `storage_path`
- owner internals
- answer key or correction payloads

### `GET /api/materials/{document_id}/summary`

Purpose:
- return a bounded safe summary for one owned material without raw content
- implemented in SummaryRead-A as an authenticated, user-scoped, metadata-only endpoint

Implemented shape:

```json
{
  "document_id": "doc-123",
  "display_filename": "roteiro-praticagem.pdf",
  "content_type": "pdf",
  "material_type": "study_material",
  "created_at": "2026-05-27T00:00:00Z",
  "updated_at": "2026-05-27T00:05:00Z",
  "processing_status": "ready_for_review",
  "extraction_status": "textual_pdf",
  "chunk_count": 12,
  "section_count": 4,
  "review_state": "ready_for_review",
  "warnings_count": 0,
  "latest_pipeline_status": "metadata_ready",
  "pipeline": {
    "status": "metadata_ready",
    "steps_count": 5,
    "has_ocr_warning": false,
    "ready_for_review": true
  },
  "source": "user_scope"
}
```

### `GET /api/editais`

Purpose:
- return a bounded user-scoped list of edital extraction and alignment summaries
- implemented in ReadEndpoints-C as an authenticated, user-scoped, metadata-only endpoint

Implemented shape:

```json
{
  "items": [
    {
      "edital_id": "edital:doc-123",
      "document_id": "doc-123",
      "title": "Edital analisado da sessão",
      "created_at": "2026-05-27T00:00:00Z",
      "updated_at": "2026-05-27T00:05:00Z",
      "analysis_status": "analyzed",
      "review_state": "review_required",
      "topics_count": 12,
      "subtopics_count": 42,
      "bibliography_count": 8,
      "gaps_count": 3,
      "coverage_status": "partial",
      "warnings_count": 2,
      "alignment_status": "ready_for_review"
    }
  ],
  "count": 1,
  "source": "user_scope"
}
```

Allowed fields:
- `edital_id`
- `document_id`
- `title`
- `analysis_status`
- `created_at`
- `updated_at`
- `review_state`
- `topics_count`
- `subtopics_count`
- `bibliography_count`
- `gaps_count`
- `coverage_status`
- `warnings_count`
- `alignment_status`

Forbidden fields:
- raw edital text
- raw document text
- OCR dump
- full extracted sections
- bibliography evidence excerpts
- chunk text
- base64 payload
- `storage_path`

Lifecycle semantics:
- the implemented backend list shape includes bounded `analysis_status`
- an uploaded material with `material_type: "edital"` and no bounded edital item means `uploaded_not_analyzed` in the frontend state model
- a bounded edital item with ready review/coverage/alignment metadata means `analyzed`
- bounded edital metadata that is pending, partial, gap-bearing, not available, or needs review means `needs_review`
- offline, unsupported, failed, or unknown reads mean analysis is unavailable
- allowed backend `analysis_status` values are `analyzed`, `needs_review`, `failed`, and `not_ready`
- concrete study guidance may unlock only for analyzed edital metadata that is ready for review; uploaded-only, needs-review, failed, unknown, and unavailable states remain conservative
- these lifecycle fields are read-only metadata and do not imply edital ingestion, OCR, generation, or progress mutation
- `topics_count` counts bounded top-level edital subjects/topics; `subtopics_count` counts bounded child items detected under those subjects, such as numbered `1.1` lines, bullets, or safe inline semicolon/comma lists
- the deterministic parser remains conservative: bibliography/reference lines are not counted as topics or subtopics, and raw topic text/evidence excerpts are not exposed by bounded read endpoints

### `GET /api/editais/{edital_id}/summary`

Purpose:
- return one bounded owned edital summary without exposing ingestion body or alignment evidence excerpts
- implemented in SummaryRead-B as an authenticated, user-scoped, metadata-only endpoint

Implemented shape:

```json
{
  "edital_id": "edital:doc-123",
  "document_id": "doc-123",
  "title": "Edital analisado da sessão",
  "created_at": "2026-05-27T00:00:00Z",
  "updated_at": "2026-05-27T00:05:00Z",
  "analysis_status": "needs_review",
  "review_state": "review_required",
  "topics_count": 12,
  "subtopics_count": 42,
  "bibliography_count": 8,
  "gaps_count": 3,
  "coverage_status": "partial",
  "warnings_count": 2,
  "alignment_status": "ready_for_review",
  "summary": {
    "has_topics": true,
    "has_subtopics": true,
    "has_bibliography": true,
    "has_gaps": true,
    "needs_review": true
  },
  "source": "user_scope"
}
```

Summary lifecycle semantics:
- `analysis_status` is bounded metadata included in the summary response
- `topics_count` and `subtopics_count` keep top-level subjects separate from bounded child items
- `summary.needs_review: true` or non-ready status metadata keeps study guidance conservative
- summary responses must never expose raw edital text, raw bibliography bodies, source evidence snippets, OCR content, storage paths, or generated answer/correction fields

### `POST /api/materials/{document_id}/edital/analyze`

Purpose:
- run controlled backend edital analysis for one authenticated, user-owned uploaded material
- implemented in EditalAnalysis-B as a bounded lifecycle endpoint
- does not add OCR, question generation, simulado generation/execution, progress mutation, scheduler behavior, or automatic analysis on upload

Preconditions:
- unauthenticated requests return `401`
- missing or non-owner materials return `404`
- the uploaded material must have `material_type: "edital"`
- non-edital materials return `422`
- if extracted text artifacts are missing for `.txt`, `.md`, or textual `.pdf`, the endpoint may run safe deterministic no-OCR textual preparation internally before analysis
- textual PDFs use embedded-text extraction only; controlled analysis never triggers OCR
- the deterministic parser recognizes common edital headings such as `CONTEUDO PROGRAMATICO`, `CONHECIMENTOS`, `BIBLIOGRAFIA`, and `REFERÊNCIAS`, plus subject-colon headings, numbered top-level topics, numbered subitems like `1.1`, and child bullets under a current topic
- missing/insufficient safe text, OCR-required PDFs, and unsupported extraction states return a bounded `not_ready` response

Implemented shape:

```json
{
  "edital_id": "edital:doc-123",
  "document_id": "doc-123",
  "analysis_status": "analyzed",
  "review_state": "ready_for_review",
  "topics_count": 12,
  "subtopics_count": 42,
  "bibliography_count": 8,
  "gaps_count": 0,
  "warnings_count": 1,
  "source": "user_scope"
}
```

Allowed fields:
- `edital_id`
- `document_id`
- `analysis_status`
- `review_state`
- `topics_count`
- `subtopics_count`
- `bibliography_count`
- `gaps_count`
- `warnings_count`
- `source`

Allowed `analysis_status` values:
- `analyzed`
- `needs_review`
- `failed`
- `not_ready`

Forbidden fields:
- raw edital text
- raw document text
- `extracted_text`
- OCR dumps
- chunks or section bodies
- bibliography evidence excerpts
- base64 payloads
- `storage_path`
- private paths
- owner internals
- password/session fields
- answer key, gabarito, or correction payloads
- worker/job/internal traces

Frontend proxy/API status:
- same-origin Next proxy exists at `POST /api/materials/{materialId}/edital/analyze`
- the proxy forwards cookies server-side and whitelists the bounded response fields
- frontend API helper `analyzeMaterialAsEdital(materialId)` normalizes auth, not-found, invalid-material-type, not-ready, offline, and unsupported states
- the only frontend UI action is the minimal material-detail manual analysis button for real uploaded editais; no automatic upload-triggered analysis exists

### `GET /api/editais/{edital_id}/coverage`

Purpose:
- return a bounded, read-only coverage summary comparing one owned edital against current user materials
- implemented in Coverage-B as an authenticated, user-scoped, metadata-only endpoint
- Coverage-C adds the same-origin frontend proxy and API wrapper
- does not add visible coverage UI, study plan generation, question generation, simulado generation/execution, progress mutation, scheduler behavior, OCR, LLM calls, or frontend UI unlocks

Behavior:
- unauthenticated requests return `401`
- missing or non-owner editais return `404`
- `analysis_status: "not_ready"` returns `coverage_status: "not_ready"` with empty coverage
- analyzed or needs-review editais are compared conservatively against bounded material metadata only
- the edital source document is excluded from material consideration
- materials with `material_type: "study_material"` are primary candidates
- materials with `material_type: "bibliography"` or `previous_exam` can provide supporting/partial signals
- `edital`, `unknown`, `other`, and `note` materials do not falsely cover edital subtopics in the initial contract

Implemented shape:

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

Forbidden fields:
- raw edital text
- raw material text
- `extracted_text`
- raw chunks or sections
- OCR dumps
- evidence snippets
- raw bibliography bodies
- base64 payloads
- `storage_path`
- private paths
- owner internals
- password/session fields
- answer key, gabarito, or correction payloads
- worker/job/internal traces

Frontend proxy/API status:
- same-origin Next proxy exists at `GET /api/editais/{editalId}/coverage`
- the proxy forwards cookies server-side and whitelists the bounded response fields
- frontend API helper `fetchEditalCoverage(editalId)` normalizes auth-required, not-found, not-ready, backend-offline, unsupported, and invalid-response states
- no visible coverage UI or study unlock exists in Coverage-C

## Pipeline Status Reads

### Current state

Existing backend reads:

- `GET /api/materials/{document_id}/pipeline`
- `GET /api/materials/{document_id}/sections`
- `GET /api/materials/{document_id}/chunks`

Findings:

- These routes are authenticated and user-scoped.
- Unauthenticated requests return `401`.
- Missing or non-owned materials resolve to `404` inside the current user's scope.
- `GET /api/materials/{document_id}/pipeline` returns bounded operational state, but includes implementation-oriented fields such as pipeline version, stages, errors, and stage details.
- `GET /api/materials/{document_id}/sections` is bounded enough for section metadata, but still exposes structural detail not needed for a compact pipeline status card.
- `GET /api/materials/{document_id}/chunks` returns chunk identifiers only today, but it remains semantically close to raw content surfaces and should not be the primary browser-facing detail contract.

### Implemented endpoint

Implemented in PipelineRead-B:

- `GET /api/materials/{document_id}/pipeline/summary`

Purpose:

- return bounded pipeline status for one owned material
- support the pipeline detail page without calling chunks/sections directly
- avoid raw pipeline events, worker/job traces, raw chunks, raw sections, OCR dumps, and storage paths

Suggested shape:

```json
{
  "document_id": "doc-123",
  "status": "ready_for_review",
  "steps": [
    {
      "key": "uploaded",
      "label": "Enviado",
      "state": "done",
      "warnings_count": 0
    },
    {
      "key": "text_extracted",
      "label": "Texto extraído",
      "state": "done",
      "warnings_count": 0
    },
    {
      "key": "segmented",
      "label": "Segmentado",
      "state": "done",
      "warnings_count": 0
    },
    {
      "key": "ready_for_review",
      "label": "Pronto para revisão",
      "state": "done",
      "warnings_count": 0
    }
  ],
  "steps_count": 4,
  "has_ocr_warning": false,
  "ready_for_review": true,
  "section_count": 4,
  "chunk_count": 12,
  "warnings_count": 0,
  "source": "user_scope"
}
```

Allowed fields:

- `document_id`
- `status`
- `steps`
- `steps_count`
- `has_ocr_warning`
- `ready_for_review`
- `section_count`
- `chunk_count`
- `warnings_count`
- `source`

Allowed step fields:

- `key`
- `label`
- `state`
- `warnings_count`

Forbidden fields:

- raw document text
- raw OCR output
- raw chunk bodies
- raw section bodies
- extraction payloads
- event metadata with implementation traces
- worker/job/runtime traces
- base64 payloads
- storage paths
- private paths
- answer key or correction payloads

Material type metadata:
- accepted upload values are `edital`, `study_material`, `previous_exam`, `bibliography`, `note`, `other`, and `unknown`
- missing upload intent is stored as `unknown`
- this field is bounded metadata only and must not trigger edital ingestion, OCR, processing, generation, or study/progress mutations

### Later endpoint: `GET /api/pipeline/recent`

Purpose:
- expose recent bounded pipeline state items without chunks, extraction text, or raw events
- useful later for dashboard or materials overview status cards
- not needed before the per-material pipeline summary is implemented

Suggested shape:

```json
{
  "total_documents": 2,
  "ocr_required_count": 1,
  "items": [
    {
      "document_id": "doc-123",
      "display_filename": "roteiro-praticagem.pdf",
      "current_stage": "metadata_ready",
      "extraction_status": "extracted",
      "metadata_status": "ready",
      "updated_at": "2026-05-27T00:05:00Z",
      "chunk_count": 12,
      "section_count": 4,
      "warnings_count": 0
    }
  ]
}
```

### `GET /api/study/today`

Purpose:
- later, expose bounded session guidance only after the list contracts stabilize

Suggested shape:

```json
{
  "session_available": true,
  "session_id": "sess-123",
  "title": "Sessão sugerida",
  "subject_label": "Navegação",
  "gap_count": 2,
  "materials_count": 3,
  "review_state": "guide_only"
}
```

## Auth and Owner-Scope Rules

- Require authenticated user for all dedicated user-scoped read endpoints.
- Resolve user scope through `JsonStudyRepository.for_user(user_id)` or equivalent repository methods already keyed by `user_id`.
- Return `401` when unauthenticated.
- Return `404` when the requested item is not found in the current user scope.
- Never reveal whether another user owns an item.
- List endpoints should return only the current user’s items or an empty list.

## No-Leakage Rules

Never expose in these read contracts:

- `password_hash`
- cookie values
- session token values
- `storage_path`
- local absolute paths like `/Users/` or `C:\\`
- `extracted_text`
- `text`
- raw OCR output
- base64 payloads
- raw chunk bodies
- raw section bodies
- raw edital body
- answer key or correction payloads
- private repository internals

## Backend Test Plan

For each dedicated endpoint:

### Auth and scope

- unauthenticated request returns `401`
- owner receives only own items
- another authenticated user does not receive other user data
- item summary returns `404` for non-owner or missing item

### Bounded payload

- response does not contain raw text fields
- response does not contain `storage_path`
- response does not contain cookie/session/user secret fields
- response does not contain absolute filesystem paths

### Shape stability

- empty list shape is stable
- counts are bounded and numeric
- recent lists remain deterministic where ordering is defined

## Frontend Test Plan

When the dedicated endpoints land:

- same-origin proxy continues mapping `401`, `502`, and `503`
- adapters prefer dedicated real list data over dashboard overview fallback
- product state mapping remains:
  - authenticated real data
  - requires session
  - demo
  - backend offline
  - unsupported
- view-model tests verify that raw fields never appear in browser-facing data

## Frontend Proxy Migration Plan

1. Keep the current same-origin Next proxies.
2. Switch proxy backend targets from `GET /api/dashboard/overview` to the dedicated bounded endpoints.
3. Keep sanitization in the Next proxy during the transition.
4. Only simplify proxy sanitization if the backend contract is proven bounded by tests.
5. Preserve current fallback UX:
   - `Dados reais da sessão`
   - `Requer sessão`
   - `Dados de demonstração`
   - `Backend offline`
   - `Consulta local`

## Non-Goals

- PostgreSQL migration
- external auth provider
- deploy/staging work
- OCR production validation
- question generation
- simulado execution
- progress mutation
- scheduler/calendar behavior
- replacing the current frontend fallback policy in this phase
