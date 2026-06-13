# Cumulative Review Block Contract Plan

## Purpose

Define the future contract for cumulative review blocks after small batches of study materials.

This began as a planning document. ReviewBlock-B implemented the first backend read-only endpoint, `GET /api/study/review/next`, as a bounded cumulative-review candidate based on prepared materials or available study blocks. ReviewBlock-C added the frontend same-origin proxy and `fetchNextReviewBlock()` API helper. ReviewBlock-D added a compact read-only cumulative review card on `/study`. ReviewBlock-Progress-B added backend-only conservative support for `basis=studied_materials` when at least 3 prepared `study_material` files have all of their backend-derived blocks explicitly marked studied. ReviewBlock-Progress-C aligned the frontend to accept and render that backend-provided basis without deriving it locally. It does not add a review detail page, progress mutation from review reads, completed state, persisted answer attempts, answer-key exposure, scoring, official correction, simulado behavior, OCR, LLM calls, scheduler behavior, PostgreSQL, auth provider work, or signup.

## Product Objective

A review block should help the student consolidate learning after a small batch of study materials.

Core product rule:

- after every 3 studied materials, offer a cumulative review
- include a concise review summary
- include review/fixation questions
- emphasize weak topics or uncertain answers when available
- later feed simulado readiness

The first contract must be conservative because the current product has no progress mutation and no persisted attempts. Until a dedicated Progress phase exists, the product should speak about review candidates from prepared materials, not completed study history.

## Current State

Available today:

- study materials can be uploaded and prepared with deterministic no-OCR preparation
- prepared materials can expose bounded summary sections and key points
- `/study` renders bounded study blocks from prepared `study_material` files
- `/study/blocks/[blockId]` renders one bounded block detail
- block detail renders summary sections, key points, and objective fixation-question candidates
- objective candidates can use A-E/A-D multiple choice or C/E true/false when safe
- the user can select an option and click `Revisar escolha`
- answer review returns conservative stateless feedback and bounded reinforcement
- the reinforcement panel displays `Feedback`, `Reforço sugerido`, and caution copy

Not available today:

- no `material completed` state
- no persisted answer attempts
- no formal weakness history
- no progress mutation
- no official correction
- no score
- no answer key or gabarito
- no review detail page

## Prepared, Studied, And Completed Are Different

This distinction is the main safety rule for the first review-block contract.

Current product can safely say:

- `3 materiais preparados`
- `3 blocos disponíveis para revisão`
- `revisão sugerida`
- `revisão acumulada candidata`

Current product must not claim:

- `3 materiais estudados`
- `3 materiais concluídos`
- `progresso atualizado`
- `revisão concluída`

Backend responses may use the internal `studied_materials` basis after the conservative all-blocks rule is satisfied. User-facing `3 materiais estudados` copy still requires a frontend copy phase and must not imply material completion.

## Proposed Staged Approach

### Stage 1: Planning Only

Define review-block eligibility, response shape, safety boundaries, and future sequencing.

### Stage 2: Backend Read-only Review Candidate

Implemented in ReviewBlock-B as `GET /api/study/review/next`.

The endpoint returns the next cumulative review candidate from prepared materials or available study blocks.

Rules:

- authenticated
- user-scoped
- read-only
- idempotent
- no progress mutation
- no persisted review state
- no attempt persistence
- no marking materials as studied, reviewed, or completed

### Stage 3: Frontend Proxy And API Helper

Implemented in ReviewBlock-C.

Current frontend contract:

- same-origin proxy path: `GET /api/study/review/next`
- API helper: `fetchNextReviewBlock()`
- proxy forwards cookies server-side
- proxy uses the server/internal backend URL strategy
- proxy whitelists top-level, summary, questions, reinforcement, and action fields
- wrapper maps `review_status=not_ready` to a safe `not_ready` result
- the `/study` card can consume the bounded result without exposing backend action links to future routes

The frontend should not decide when a cumulative review is due, compute weakness history, or infer material completion.
It should also not infer `studied_materials`; it only renders that basis when the backend returns it.

### Stage 4: Minimal Review UI

Implemented in ReviewBlock-D as a compact `/study` card.

Initial copy should use:

- `Revisão acumulada`
- `Revise estes pontos`
- `Questões de revisão`
- `Reforço sugerido`

Current UI rules:

- show ready, needs-review, partial, and not-ready states with product-safe copy
- speak about `Materiais preparados` and `Blocos disponíveis`
- do not render backend action hrefs such as `/study/review/<review_id>` until a detail page exists
- do not claim materials were studied or completed
- do not expose gabarito, answer keys, score, official correction, simulado, or progress actions

### Stage 5: Progress-aware Review

Implemented in ReviewBlock-Progress-B for backend eligibility only: `basis=studied_materials` is used when at least 3 prepared `study_material` files have all backend-derived blocks marked studied. Frontend copy and detail UI remain unchanged.

### Stage 6: Simulado Readiness

Later, cumulative review signals may contribute to simulado readiness, but not before the review and progress contracts are stable.

## Implemented Backend Endpoint

Implemented endpoint:

```http
GET /api/study/review/next
```

Why this is preferred:

- the route describes the user task: get the next review candidate
- it avoids implying multiple persisted review resources already exist
- it leaves room for future `/api/study/review/blocks/{review_id}` detail endpoints if needed
- it keeps review sequencing backend-owned
- it is shorter and clearer than `/api/study/review/blocks/next`

The endpoint:

- require authentication
- use the current user's repository scope
- return `401` for unauthenticated requests
- never reveal another user's data
- return a bounded candidate cumulative review
- not mutate progress
- not mark materials as reviewed
- not mark blocks as completed
- not persist attempts or review history

Frontend same-origin proxy/API helper and the compact `/study` card already exist. A dedicated review detail page remains pending.

## Implemented Bounded Response Shape

```json
{
  "review_status": "ready",
  "review_id": "review:prepared-materials:1",
  "basis": "prepared_materials",
  "materials_count": 3,
  "blocks_count": 3,
  "estimated_minutes": 18,
  "title": "Revisão acumulada",
  "summary": {
    "status": "ready",
    "items": [
      {
        "title": "Atos administrativos",
        "message": "Revise os conceitos centrais e compare os pontos principais dos blocos preparados.",
        "topic_label": "Direito Administrativo",
        "subtopic_label": "Atos administrativos"
      }
    ]
  },
  "questions": {
    "status": "ready",
    "items_count": 5
  },
  "reinforcement": {
    "status": "needs_review",
    "weak_topics_count": 0,
    "items": [
      {
        "topic_label": null,
        "subtopic_label": null,
        "message": "Ainda não há histórico suficiente de respostas para destacar pontos fracos reais."
      }
    ]
  },
  "actions": [
    {
      "label": "Abrir revisão",
      "href": "/study/review/review:prepared-materials:1"
    }
  ],
  "source": "user_scope"
}
```

Allowed top-level fields:

- `review_status`
- `review_id`
- `basis`
- `materials_count`
- `blocks_count`
- `estimated_minutes`
- `title`
- `summary`
- `questions`
- `reinforcement`
- `actions`
- `source`

Allowed `review_status` values:

- `ready`
- `partial`
- `not_ready`
- `needs_review`

Allowed `basis` values:

- `prepared_materials`
- `study_blocks`
- `studied_materials`

`studied_materials` is used only when the backend conservative all-blocks rule derives at least 3 studied materials.

Forbidden fields:

- raw material text
- raw edital text
- extracted text
- raw chunks
- section bodies
- OCR output
- base64 payloads
- storage paths
- local/private paths
- cookies, tokens, session values, or password hashes
- answer keys
- gabarito
- correct alternatives
- official correction payloads
- score or pontuação
- progress payloads
- attempt history
- worker/job/internal traces

## Review Eligibility Rules

Initial conservative eligibility:

- fewer than 3 prepared `study_material` files or fewer than 3 available study blocks:
  return `review_status="not_ready"` or `review_status="partial"`
- 3 or more prepared `study_material` files or study blocks:
  return `review_status="ready"` or `review_status="needs_review"`

Use `needs_review` when:

- material summaries are weak or generic
- block-to-edital matching is weak
- reinforcement data is absent or insufficient
- question candidates are limited

Future progress-aware eligibility:

- use 3 actually studied materials only after a Progress phase defines studied/completed events
- do not retrofit progress semantics into this read-only endpoint

## What Counts As A Material

Initial eligible material:

- `study_material`

Not eligible by default:

- `edital`: official scope, not a learning material for review count
- `bibliography`: reference support, not primary review material unless a later phase allows it
- `previous_exam`: practice/style support, not primary review material unless a later phase allows it
- `note`: optional support, not eligible by default
- `other`: not eligible by default
- `unknown`: not eligible by default

This keeps the first review rule tied to user-uploaded learning material rather than scope/reference files.

## Relationship With Answer Review And Reinforcement

Review blocks should later use:

- answer review results
- reinforcement suggestions
- weak topic labels
- question candidates
- block summary/key points

Until persistence exists:

- do not claim historical errors
- do not claim weak-topic trends
- do not say the user missed a topic
- do not count retries, successes, mistakes, or attempts

The first endpoint can still return a conservative reinforcement section that says there is not enough answer history yet.

## Relationship With Fixation Questions

Review block questions should be review-only initially.

Rules:

- no gabarito
- no answer-key reveal
- no official correction
- no score
- no progress mutation
- no persisted attempts

Later, the existing fixation-question candidate strategy may be reused with cumulative scope:

- multiple-choice A-E/A-D when safe
- true/false C/E for CEBRASPE-style contexts
- short-answer only as fallback

## Relationship With Progress

Progress mutation is future only.

Do not expose or imply:

- `completed`
- `studied`
- `review done`
- streaks
- percentages
- performance trends
- score
- ranking
- progress update

Those concepts require an explicit Progress phase that defines:

- what event is recorded
- who owns it
- idempotency
- rollback
- privacy boundaries
- how user-visible progress is phrased
- whether answer review affects progress

## UI Principles

Future UI should show:

- `Revisão acumulada`
- `Revise estes pontos`
- `Questões de revisão`
- `Reforço sugerido`
- `Baseada nos materiais preparados`
- `Ainda sem histórico de progresso`

Avoid:

- `você concluiu`
- `progresso atualizado`
- `3 materiais estudados`
- score
- ranking
- gabarito
- official correction language
- backend, pipeline, chunk, metadata, protected-read, runtime, or internal/developer language

## Safety And Non-goals

No:

- backend endpoint in this planning phase
- frontend UI in this planning phase
- progress mutation
- studied/completed state
- persisted attempts
- official correction
- answer-key or gabarito reveal
- score or pontuação
- simulado execution
- OCR or LLM work
- scheduler behavior
- PostgreSQL
- external auth provider
- signup UI

## Recommended Future Phases

1. `ReviewBlock-QA-A`: browser/API QA.
2. `Progress-Planning-A`: define studied/completed/progress semantics.
3. `ReviewBlockDetail-Planning-B` or equivalent if a cumulative review detail page becomes necessary.
4. `Simulado-Planning-A`: define how cumulative review informs later simulation readiness.
