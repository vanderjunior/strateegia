# Bounded User-Scoped Read Endpoints Contract

## Purpose

Define the next dedicated read endpoints needed after the interim `/api/dashboard/overview` strategy now used by the frontend `/materials` and `/editais` proxies.

This document is a contract and test-planning artifact only. It does not introduce new backend behavior yet.

## Current Interim State

- `GET /api/dashboard/overview` is already authenticated and user-scoped.
- The frontend currently uses same-origin Next proxies:
  - `GET /api/materials`
  - `GET /api/editais`
- Those proxies sanitize dashboard overview data into bounded list payloads.
- This is safe enough for the first authenticated reads, but it is not a full listing contract.

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

- `GET /api/pipeline/recent`

### Later

- `GET /api/study/today`

## Recommended Implementation Order

1. `GET /api/materials`
2. `GET /api/editais`
3. `GET /api/materials/{document_id}/summary`
4. `GET /api/editais/{edital_id}/summary`
5. `GET /api/pipeline/recent`
6. `GET /api/study/today`

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

Suggested shape:

```json
{
  "document_id": "doc-123",
  "display_filename": "roteiro-praticagem.pdf",
  "content_type": "application/pdf",
  "uploaded_at": "2026-05-27T00:00:00Z",
  "status": "metadata_ready",
  "extraction_status": "extracted",
  "current_stage": "metadata_ready",
  "metadata_status": "ready",
  "chunk_count": 12,
  "section_count": 4,
  "review_state": "ready_for_review",
  "warnings": [
    "candidate_only",
    "review_required"
  ],
  "latest_pipeline_status": {
    "updated_at": "2026-05-27T00:05:00Z",
    "error_count": 0
  }
}
```

### `GET /api/editais`

Purpose:
- return a bounded user-scoped list of edital extraction and alignment summaries

Suggested shape:

```json
{
  "total_editais": 1,
  "total_topics": 12,
  "total_bibliography_items": 8,
  "total_gaps": 3,
  "items": [
    {
      "edital_id": "edital:doc-123",
      "document_id": "doc-123",
      "title": "Edital analisado da sessão",
      "created_at": "2026-05-27T00:00:00Z",
      "updated_at": "2026-05-27T00:05:00Z",
      "status": "ready_for_review",
      "review_state": "review_required",
      "topics_count": 12,
      "bibliography_count": 8,
      "gaps_count": 3,
      "coverage_status": "partial",
      "warnings_count": 2,
      "alignment_status": "ready_for_review"
    }
  ]
}
```

Allowed fields:
- `edital_id`
- `document_id`
- `title`
- `created_at`
- `updated_at`
- `status`
- `review_state`
- `topics_count`
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

### `GET /api/editais/{edital_id}/summary`

Purpose:
- return one bounded owned edital summary without exposing ingestion body or alignment evidence excerpts

Suggested shape:

```json
{
  "edital_id": "edital:doc-123",
  "document_id": "doc-123",
  "title": "Edital analisado da sessão",
  "status": "ready_for_review",
  "review_state": "review_required",
  "topics_count": 12,
  "subtopics_count": 20,
  "bibliography_count": 8,
  "gaps_count": 3,
  "coverage_status": "partial",
  "warnings": [
    "candidate_only",
    "review_required"
  ],
  "alignment_status": "ready_for_review"
}
```

### `GET /api/pipeline/recent`

Purpose:
- expose recent bounded pipeline state items without chunks, extraction text, or raw events

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
