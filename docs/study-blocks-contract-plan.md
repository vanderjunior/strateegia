# Edital-aware Study Blocks Contract Plan

## Purpose

Define the backend-owned contract for edital-aware study blocks implemented in `StudyBlocks-A`.

This document records the first backend read-only contract. It does not add frontend UI, progress mutation, generated summaries, generated questions, simulados, OCR, LLM calls, scheduler behavior, PostgreSQL, auth provider work, or signup.

## Product Objective

Study blocks should transform the user's real study context into a simple sequence of what to study next.

Inputs:

- analyzed edital taxonomy
- prepared `study_material` files
- bounded material summary sections
- bounded coverage/matching data

Outputs:

- a clear sequence of study blocks
- each block tied to an edital topic/subtopic when possible
- each block tied to a prepared material and section when possible
- safe next actions for reading, without progress mutation

The edital remains the official scope source. Prepared study materials remain the learning source.

The first contract should make the study path understandable without pretending that progress tracking,
question generation, cumulative review, or simulado execution already exists.

## Implemented Endpoint

```http
GET /api/study/blocks
```

Why this should be backend-owned:

- The backend has access to user-scoped edital extraction, material preparation, coverage, and alignment data.
- Ordering and matching must be deterministic and consistent across clients.
- The frontend should not infer topic-material relationships from list/detail metadata.
- A dedicated endpoint can later support review grouping, question candidates, and progress semantics without changing the user-facing concept of a study block.

Why not extend `GET /api/study/session/next` immediately:

- `GET /api/study/session/next` is intentionally simple: one prepared material to study now.
- Study blocks require multi-material ordering, edital scope, section matches, and block statuses.
- Keeping the endpoints separate avoids mixing a simple fallback session with future edital-aware planning.

`GET /api/study/blocks` is read-only, authenticated, user-scoped, idempotent, and safe to call
from the same-origin frontend proxy.

## Prerequisites

The endpoint requires:

- authenticated user
- user-scoped repository access
- at least one prepared `study_material`

Ideal state:

- at least one analyzed or needs-review edital exists
- edital topics/subtopics are available
- prepared study materials have bounded summary sections
- coverage/matching can relate topic/subtopic labels to prepared material sections

Fallback state:

- if prepared materials exist but no analyzed edital exists, the endpoint may return material-only blocks with a warning such as `Ainda não conectado ao edital`
- if no prepared study material exists, return `not_ready`

## Proposed Response Shape

Implemented bounded top-level response:

```json
{
  "blocks_status": "ready",
  "scope_status": "connected_to_edital",
  "blocks_count": 1,
  "estimated_minutes": 8,
  "items": [
    {
      "block_id": "study-block:topic-1:subtopic-1:doc-456:section-0",
      "title": "Atos administrativos",
      "topic_id": "topic-1",
      "topic_label": "Direito Administrativo",
      "subtopic_id": "subtopic-1",
      "subtopic_label": "Atos administrativos",
      "material_id": "doc-456",
      "material_title": "aula-direito.md",
      "sections_count": 1,
      "summary_status": "ready",
      "estimated_minutes": 8,
      "status": "ready",
      "actions": [
        {
          "label": "Estudar bloco",
          "href": "/study/blocks/study-block%3Atopic-1%3Asubtopic-1%3Adoc-456%3Asection-0"
        },
        {
          "label": "Abrir material",
          "href": "/materials/doc-456"
        }
      ]
    }
  ],
  "source": "user_scope"
}
```

Implemented not-ready response:

```json
{
  "blocks_status": "not_ready",
  "scope_status": "not_ready",
  "blocks_count": 0,
  "estimated_minutes": 0,
  "items": [],
  "message": "Envie e prepare um material de estudo para montar seus blocos.",
  "source": "user_scope"
}
```

Allowed top-level fields:

- `blocks_status`
- `scope_status`
- `blocks_count`
- `estimated_minutes`
- `items`
- `message`
- `source`

Allowed item fields:

- `block_id`
- `title`
- `topic_id`
- `topic_label`
- `subtopic_id`
- `subtopic_label`
- `material_id`
- `material_title`
- `sections_count`
- `summary_status`
- `estimated_minutes`
- `status`
- `actions`

Allowed action fields:

- `label`
- `href`

Forbidden fields:

- raw edital text
- raw material text
- `extracted_text`
- chunk body
- section body
- raw OCR output
- base64
- `storage_path`
- local/private paths
- evidence excerpts
- raw bibliography bodies
- tokens/cookies/session values
- password hashes
- answer keys
- gabarito
- correctness/correction fields
- worker/job/runtime traces

## Review Grouping Strategy

The core product flow calls for a cumulative review after every 3 studied materials. That rule should be
planned now but not implemented in the first study-block read contract.

Recommended first-contract behavior:

- expose only ordinary study blocks
- do not create review blocks
- do not mutate completion/progress
- keep review-related fields out of the response unless they are static policy metadata

Recommended later behavior:

- after progress mutation exists, the backend can insert a `review` block after each group of 3 completed
  materials
- review blocks should be backend-owned and should reference only bounded summaries/questions approved by
  later contracts
- the frontend should render the review block as another safe study item, not compute when it is due

## Status Semantics

### `blocks_status`

- `not_ready`: no prepared `study_material` exists.
- `partial`: prepared materials exist, but no analyzed edital is available; blocks are material-only.
- `ready`: analyzed edital plus prepared materials produce bounded block candidates.
- `needs_review`: mapping exists but is weak, incomplete, low confidence, or coverage is uncertain.

### `scope_status`

- `connected_to_edital`: blocks are tied to analyzed edital topic/subtopic scope.
- `material_only`: prepared material blocks exist, but they are not yet connected to analyzed edital scope.
- `not_ready`: not enough safe data exists to produce blocks.

### Item `status`

- `ready`: block has a usable prepared material/section and strong enough mapping.
- `needs_review`: block exists but mapping or source structure is weak.
- `not_ready`: block target exists, but no suitable prepared material/section is available.

## Matching And Ordering Strategy

Initial deterministic ordering:

1. Prefer blocks connected to edital subtopics with prepared `study_material` sections.
2. If no analyzed edital exists, return material-only blocks from prepared material summaries.
3. Sort edital-connected blocks by edital topic order and subtopic order.
4. Within the same topic/subtopic, prefer ready summary sections over needs-review sections.
5. Then sort by material `created_at`, then `document_id`, then section order.
6. Do not use previous exams as learning-source blocks in the first contract.
7. Do not let the frontend compute order or matching.

Matching inputs should be server-side only:

- edital topic/subtopic labels and ordering
- prepared material summary sections
- bounded section ids/titles
- coverage/alignment candidates
- material type and material metadata

Matching outputs should be bounded:

- topic/subtopic ids and labels
- material id/title
- section id/title if safe
- coverage/block status
- estimated minutes
- safe next actions

Do not return raw evidence, raw matched snippets, raw chunks, or full extracted text.

## Relationship With Existing Endpoints

### `GET /api/study/session/next`

Keep this endpoint as the simple "one material to study now" surface.

Future behavior may choose the first ready study block as its source, but that should happen after `GET /api/study/blocks` exists and is validated.

### `GET /api/materials/{document_id}/study/summary`

Reuse its bounded section items as material content for blocks.

This endpoint should remain material-scoped and should not learn edital ordering rules.

### `GET /api/editais/{edital_id}/coverage`

Reuse its coverage semantics for readiness, but do not overload it with study-block rendering concerns.

The current coverage endpoint is topic-count focused. Study blocks need a bounded topic/subtopic-to-section mapping contract.

### `BibliographyAlignmentService`

Reuse internal alignment candidates where safe:

- `TopicCoverageCandidate`
- `SectionCoverageCandidate`
- `DocumentCoverageCandidate`
- `CoverageGap`

Do not pass through alignment evidence or raw excerpts.

## Frontend Responsibilities

The frontend should:

- call the same-origin proxy for `GET /api/study/blocks`
- render block titles, statuses, estimates, and actions
- show not-ready, auth-required, offline, and unsupported states
- keep copy simple and user-facing
- preserve demo/reference content as secondary only

The frontend should not:

- compute block order
- match topics/subtopics to materials
- infer coverage from filenames or labels
- infer readiness to unlock questions
- group review blocks after every 3 materials
- mutate progress
- expose internal evidence or raw content

## Future Phases

1. `StudyBlocks-A`:
   Backend read-only `GET /api/study/blocks` is implemented.

2. `StudyBlocks-B`:
   Frontend same-origin proxy/API wrapper is implemented.

3. `StudyBlocks-C`:
   Add minimal `/study` blocks UI while keeping `/api/study/session/next` as the simple fallback.

4. `StudyBlockDetail-A`:
   Add read-only block detail page if needed.

5. `FixationQuestions-Planning-A`:
   Define bounded question candidate boundaries and answer-key handling.

6. `ReviewBlock-Planning-A`:
   Define review grouping after every 3 materials.

## Non-goals

- No progress mutation.
- No completion tracking.
- No generated questions.
- No generated simulados.
- No simulado execution.
- No LLM summary generation.
- No OCR expansion.
- No scheduler/calendar behavior.
- No PostgreSQL work.
- No external auth provider.
- No signup UI.
- No frontend-only matching/order logic.
- No raw content, storage paths, tokens, password hashes, answer keys, gabarito, or correction internals.

## Open Questions For `StudyBlocks-A`

- Should `needs_review` editais produce connected blocks, or only `analyzed` editais?
- Should first implementation include material-only blocks, or leave that responsibility to `GET /api/study/session/next`?
- Should bibliography matches influence ordering in the first contract, or only annotate readiness later?
- Should previous exams be completely ignored until question/practice phases, or shown as future support material?
- Should `StudyBlockDetail-A` wait until fixation questions exist, or should it show section summaries first?
