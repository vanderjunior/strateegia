# Read-only Study Block Detail Contract Plan

## Purpose

Define the future read-only contract for studying one block from the `/study` path.

This began as a planning document. StudyBlockDetail-A implemented the backend read-only endpoint, StudyBlockDetail-B added the frontend same-origin proxy/API wrapper, and StudyBlockDetail-C added the minimal read-only `/study/blocks/[blockId]` page. It does not add progress mutation, generated questions, simulados, generated summaries, OCR, LLM calls, scheduler behavior, PostgreSQL, auth provider work, or signup.

## Product Objective

The block detail page should let the user study one block at a time.

The user should be able to:

- understand the edital topic/subtopic when available
- see the related study material
- read bounded summary sections and key points
- know what to study now
- return to the study path

The page should feel like a focused study surface, not a technical artifact viewer.

## Current Context

Implemented today:

- `GET /api/study/blocks` returns a bounded list/overview sequence of study blocks.
- `GET /api/study/blocks/{block_id}` resolves one current user block and returns bounded detail data.
- Frontend same-origin `GET /api/study/blocks/[blockId]`, `fetchStudyBlockDetail(blockId)`, and `/study/blocks/[blockId]` exist.
- `/study` renders those blocks first when available.
- Block list items may include actions pointing to `/study/blocks/{block_id}` URLs.
- `GET /api/materials/{document_id}/study/summary` returns bounded prepared-material section summaries.
- The one-material `GET /api/study/session/next` remains a fallback.

Current limitation:

- Browser/API QA for `/study/blocks/[blockId]` is still pending.
- The list item remains intentionally compact and should not become the source of truth for richer detail.

## Implemented Backend Endpoint

Implemented endpoint:

```http
GET /api/study/blocks/{block_id}
```

Why this should be backend-owned:

- The backend owns block resolution.
- The backend owns authenticated user scope.
- The backend owns topic/material/section mapping.
- The backend can validate whether the block still exists for the current user.
- The backend can safely derive detail from prepared material summaries without exposing raw sections or chunks.
- The frontend should not reconstruct block details from list data.

Why the existing list endpoint is not enough:

- `GET /api/study/blocks` is an overview and ordering contract.
- List items intentionally include only title, topic labels, material title, counts, estimates, status, and safe actions.
- A detail page needs bounded summary sections and key points.
- Future detail behavior may need to resolve changed material summaries, weak edital matches, or unavailable blocks at request time.
- Reusing only the list item would make the frontend responsible for reconstructing server-owned relationships.

## Implemented Bounded Response Shape

```json
{
  "block_id": "study-block:topic-1:doc-123:0",
  "detail_status": "ready",
  "title": "Atos administrativos",
  "topic_id": "topic-1",
  "topic_label": "Direito Administrativo",
  "subtopic_id": "subtopic-1",
  "subtopic_label": "Atos administrativos",
  "material_id": "doc-123",
  "material_title": "aula-direito-administrativo.md",
  "summary_status": "ready",
  "estimated_minutes": 8,
  "sections": [
    {
      "section_id": "doc-123:section:0",
      "title": "Atos administrativos",
      "summary": "Resumo curto e revisável da seção.",
      "key_points": ["Elemento principal", "Ponto de atenção"],
      "estimated_minutes": 8,
      "status": "ready"
    }
  ],
  "actions": [
    {
      "label": "Abrir material",
      "href": "/materials/doc-123"
    },
    {
      "label": "Voltar ao caminho de estudo",
      "href": "/study"
    }
  ],
  "source": "user_scope"
}
```

Allowed top-level fields:

- `block_id`
- `detail_status`
- `title`
- `topic_id`
- `topic_label`
- `subtopic_id`
- `subtopic_label`
- `material_id`
- `material_title`
- `summary_status`
- `estimated_minutes`
- `sections`
- `actions`
- `source`

Allowed section fields:

- `section_id`
- `title`
- `summary`
- `key_points`
- `estimated_minutes`
- `status`

Allowed action fields:

- `label`
- `href`

Forbidden fields:

- raw edital text
- raw material text
- `extracted_text`
- raw chunks
- raw section bodies
- OCR output
- base64 payloads
- storage paths
- local/private paths
- evidence snippets
- raw bibliography bodies
- cookies, tokens, session values, or password hashes
- answer keys
- gabarito
- correctness/correction payloads
- progress mutation payloads
- worker/job/internal traces

## Status Behavior

### `ready`

Use when the block resolves to the current user's prepared study material and has bounded summary sections ready for display.

### `needs_review`

Use when the block resolves, but the edital mapping, summary structure, or source preparation is weak enough to require conservative copy.

Examples:

- weak topic/subtopic match
- prepared section title exists but summary is limited
- analyzed edital exists but mapping is incomplete

### `not_ready`

Use when the `block_id` is syntactically valid for the route but cannot produce a study-ready detail from prepared material and bounded summary data.

Examples:

- material exists but is no longer prepared
- summary items are empty
- block references no longer match a safe section

### HTTP Statuses

- `401`: unauthenticated.
- `404`: missing block or block owned by another user.
- `200`: block detail can be returned as `ready`, `needs_review`, or `not_ready`.

The endpoint must never reveal whether another user owns a block.

## Relationship With Existing Endpoints

### `GET /api/study/blocks`

Purpose:

- list/overview
- sequence of blocks
- safe card rendering
- study path status

It should remain compact and suitable for `/study`.

### `GET /api/study/blocks/{block_id}`

Purpose:

- detailed read-only study surface for one block
- bounded summary sections
- key points
- material/topic context
- safe navigation actions

It resolves the block server-side instead of trusting the frontend list item.

### `GET /api/materials/{document_id}/study/summary`

Purpose:

- material-scoped prepared summary
- reusable source for detail sections

It should not learn block routing, edital ordering, or topic matching rules.

### `GET /api/study/session/next`

Purpose:

- simple fallback for one prepared material

It should not become the block-detail contract.

## Frontend Responsibilities

Implemented page:

```text
/study/blocks/[blockId]
```

Implemented frontend read support:

```text
GET /api/study/blocks/[blockId]
fetchStudyBlockDetail(blockId)
```

The page shows:

- block title
- edital topic/subtopic when available
- material title
- bounded summary sections
- key points
- estimated minutes
- safe actions

The page should not show:

- backend
- pipeline
- chunks
- metadata
- protected-read terminology
- confidence scores
- progress mutation controls
- questions
- simulado
- geração/generation language
- raw content
- internal diagnostics

The frontend should only render bounded backend output and safe fallback states. It should not compute block order, topic-material matching, section resolution, or study unlock rules.

## Backend Responsibilities

The backend endpoint:

- require authentication
- use current user scope
- resolve `block_id` against the user's current prepared materials and analyzed edital state
- derive sections from bounded study summary data
- return only whitelisted fields
- preserve `404` for missing/non-owner/unresolvable blocks
- keep raw extraction artifacts server-side

The backend should own block identity semantics because current block ids encode matching inputs that may change as the matching strategy improves.

## Future Phases

1. `StudyBlockDetail-A`: backend `GET /api/study/blocks/{block_id}` endpoint is implemented.
2. `StudyBlockDetail-B`: frontend same-origin proxy/API helper is implemented.
3. `StudyBlockDetail-C`: minimal `/study/blocks/[blockId]` page UI is implemented.
4. `StudyBlockDetail-QA-A`: browser/API QA and no-leakage validation.
5. `FixationQuestions-Planning-A`: bounded fixation-question and answer-key boundary planning.

## Non-goals

- No progress mutation.
- No completion tracking.
- No fixation questions.
- No answer keys.
- No gabarito.
- No simulado generation or execution.
- No generated summaries.
- No LLM behavior.
- No OCR expansion.
- No scheduler/calendar behavior.
- No PostgreSQL work.
- No external auth provider.
- No signup UI.
- No frontend-only matching/order/detail reconstruction.

## Open Questions For Implementation

- Should a stale but user-owned `block_id` return `404` or `200` with `detail_status=not_ready`?
- Should a detail endpoint support a material-only block id and an edital-connected block id with the same response shape?
- Should section ids be stable public identifiers or bounded opaque references?
- Should future review-after-3 blocks use the same endpoint shape or a separate detail subtype?
