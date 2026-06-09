# Study Progress Semantics Contract Plan

## Purpose

Define future study progress semantics before adding buttons such as `Concluir`, `Marcar como estudado`, `Revisado`, or `Progresso`.

This is a planning contract only. It does not add endpoints, UI behavior, progress mutation, studied/completed state, persisted attempts, scores, answer keys, gabarito, official correction, simulado execution, OCR, LLM calls, scheduler behavior, PostgreSQL, auth provider work, or signup.

## Product Objective

Progress should eventually help the student:

- know what was studied
- know what is pending
- know what needs review
- track weak topics
- unlock cumulative review based on real study activity
- later support simulados and performance analysis

The first progress contract must be precise because the current product already has safe study and review surfaces, but intentionally does not persist activity or claim completion.

## Current State

Available today:

- study materials can be uploaded and prepared
- material summaries appear for prepared `study_material` files
- `/study` shows read-only study blocks
- `/study/blocks/[blockId]` shows read-only block detail
- block detail shows bounded summaries and key points
- block detail shows objective fixation question candidates
- the user can select A-E or Certo/Errado and click `Revisar escolha`
- answer review returns conservative stateless feedback
- answer review can show advisory reinforcement
- `/study` shows a read-only cumulative review candidate after 3 prepared materials or available blocks

Not available today:

- no progress mutation
- no persisted answer attempts
- no studied state
- no completed state
- no reviewed state
- no official correction
- no score
- no exposed answer key or gabarito
- no simulado execution

## Core Vocabulary

### `prepared_material`

A material that has been processed or prepared for study.

Rules:

- means the material is available as bounded study input
- does not mean the material was studied
- does not mean the material was completed
- may count toward current read-only review candidates

### `available_block`

A study block generated from prepared material and, when available, study scope.

Rules:

- means the user can open the block
- does not mean the user opened it
- does not mean the user studied it
- does not mean the user completed it

### `opened_block`

A user opened a block detail page.

Future rules:

- may be tracked later as a low-confidence engagement event
- should not by itself count as studied
- should not by itself complete material progress

### `studied_block`

A block the user explicitly marks as studied in a future Progress phase.

Rules:

- requires an explicit user action
- requires a progress write contract
- should be user-scoped and idempotent
- can later count toward material progress

### `reviewed_question`

A question for which the user submitted an answer review.

Current rules:

- answer review is stateless
- no attempt is persisted
- no correctness is official
- no score is stored

Future rules:

- may create a `question_reviewed` progress event
- should remain separate from official correction unless a correction/scoring contract exists

### `weak_topic`

A topic or subtopic that needs reinforcement.

Current rules:

- reinforcement is advisory and stateless
- weak topics are not persisted
- no official error classification exists

Future rules:

- can be derived only after persisted review signals or a separate deterministic correction/error contract exists
- should remain conservative unless the backend has strong bounded evidence

### `completed_material`

A material whose required study blocks are completed.

Future-only rules:

- requires progress semantics for required blocks
- requires explicit completion criteria
- should not be inferred from upload, preparation, opening, or answer review alone

### `reviewed_material`

A material included in a cumulative review.

Future-only rules:

- requires a review state or event contract
- should not imply the material was mastered
- should not imply official scoring

## Current Wording Boundary

Until progress exists, normal user UI must not claim:

- `estudado`
- `concluído`
- `progresso atualizado`
- `você concluiu`
- `revisão concluída`
- official `acertos/erros`
- `pontuação`

Allowed current wording:

- `material preparado`
- `bloco disponível`
- `revisão sugerida`
- `escolha revisada sem pontuação`
- `orientação de estudo`
- `reforço sugerido`

The product can say that a review is based on prepared materials or available blocks, but not that the student has studied or completed those materials.

## Proposed Staged Approach

### Stage 1: Planning Only

Define vocabulary, event semantics, endpoint options, read summaries, safety boundaries, and review-after-3 implications.

### Stage 2: Progress Events Contract, No UI

Define event types and decide which events are automatic versus explicit user actions.

Candidate event types:

- `block_opened`
- `block_marked_studied`
- `question_reviewed`
- `review_opened`
- `review_completed`

### Stage 3: Backend Progress Endpoint

Add backend progress write endpoint(s) only after the event contract is approved.

Requirements:

- authenticated
- user-scoped
- explicit mutation
- idempotent where needed
- no score or gabarito
- no automatic completion
- bounded response only

### Stage 4: Frontend Progress UI

Add minimal explicit actions only after backend semantics exist.

Possible UI:

- `Marcar bloco como estudado`
- `Continuar depois`
- `Ver pendências`

### Stage 5: Progress-aware Review-after-3

Update cumulative review eligibility to use 3 studied materials, not merely 3 prepared materials, after studied/completed semantics are implemented.

### Stage 6: Correction, Scoring, And Simulado Later

Scoring, official correction, answer-key handling, and simulado readiness require separate future contracts.

## Proposed Endpoint Strategy

### Option A: Block-specific Endpoint

```http
POST /api/study/blocks/{block_id}/progress
```

Example request:

```json
{
  "event": "opened"
}
```

Pros:

- simple for block-only progress
- easy to route from block detail

Cons:

- does not generalize well to questions, reviews, or material-level events
- can lead to many narrowly scoped endpoints
- makes progress feel tied only to blocks

### Option B: Event-based Endpoint

```http
POST /api/study/progress/events
```

Example request:

```json
{
  "event_type": "block_marked_studied",
  "target_type": "block",
  "target_id": "study-block:material:doc-1:0"
}
```

Recommendation: prefer Option B later.

Reasons:

- extensible for block, question, review, and material events
- keeps progress mutation explicit
- supports append-only event storage later
- avoids creating many endpoints too early
- can support idempotency keys for repeated clicks
- gives the backend a single place to enforce owner scope and event semantics

## Proposed Read Endpoint

Future endpoint:

```http
GET /api/study/progress/summary
```

Bounded response shape:

```json
{
  "progress_status": "ready",
  "studied_blocks_count": 0,
  "prepared_materials_count": 0,
  "studied_materials_count": 0,
  "review_due": false,
  "review_basis": "prepared_materials",
  "weak_topics_count": 0,
  "source": "user_scope"
}
```

Allowed `progress_status` values:

- `ready`
- `not_ready`

Allowed `review_basis` values:

- `prepared_materials`
- `studied_materials`
- `none`

Rules:

- no raw content
- no answer keys or gabarito
- no score unless a future scoring contract explicitly approves it
- no raw attempts payload
- no storage paths
- no internal traces

## Event Semantics

### `block_opened`

Meaning:

- the user opened a block detail page

Rules:

- low-confidence engagement signal
- may help resume the last opened block
- must not mark the block as studied
- must not count toward completed material status

### `block_marked_studied`

Meaning:

- the user explicitly says the block was studied

Rules:

- high-confidence progress signal
- should be explicit and reversible or idempotent
- can count toward material progress
- should not imply mastery
- should not imply question correctness

### `question_reviewed`

Meaning:

- the user submitted an answer review for a fixation question

Rules:

- records review activity only if a future event endpoint exists
- does not imply official correctness
- does not create a score
- can later feed reinforcement signals

### `review_opened`

Meaning:

- the user opened a cumulative review surface

Rules:

- engagement signal only
- does not mean review was completed
- does not update progress by itself

### `review_completed`

Meaning:

- the user explicitly marks a review as completed in a future phase

Rules:

- future-only
- should require a review UI and progress contract
- should not be automatic
- should not imply official scoring

## What Counts Toward Review-after-3

Current behavior:

- `GET /api/study/review/next` can produce a read-only review candidate from 3 prepared study materials or available study blocks
- the current basis is `prepared_materials` or `study_blocks`
- this is a candidate review, not proof of completed study

Future progress-aware behavior:

- review-after-3 should use 3 studied materials only after a Progress phase exists
- a material should count as studied only when required study blocks are marked studied
- `study_material` is the default eligible material type
- `edital` is scope, not a primary review material
- `bibliography` is reference support, not a primary review material by default
- `previous_exam` supports practice/style later, not primary review material by default
- `unknown`, `other`, and `note` should not count by default

## Relationship With Answer Review

Current answer review:

- stateless
- conservative
- ungraded or needs-review
- no persisted attempt
- no score
- no progress mutation
- no answer key or gabarito

Future progress relationship:

- `question_reviewed` may be stored as an event
- the event should record that review happened, not that the answer was correct
- official correction requires a separate correction/scoring contract
- answer review should not automatically mark a block studied

## Relationship With Reinforcement

Current reinforcement:

- advisory
- stateless
- rendered from the existing answer-review response
- no formal weakness history

Future progress relationship:

- weak topics may be derived from persisted answer review or reinforcement events
- weak topics should remain conservative until a deterministic signal exists
- reinforcement should point back to block summary, key points, and topic/subtopic context
- reinforcement should not jump to unrelated materials

## Relationship With Simulado

Simulado remains future.

Progress may later inform:

- readiness
- weak areas
- topic distribution
- review coverage

No simulado execution, scoring, answer-key exposure, or progress mutation is part of this phase.

## Data Model Considerations

Future implementation should decide between:

- append-only event log
- mutable counters
- hybrid event log plus derived summary

Recommendation:

- prefer append-only progress events for the first write contract
- derive summary counters from events
- keep owner scope explicit
- use idempotency keys for repeated clicks
- keep events bounded and product-level
- do not store raw content, raw answer bodies beyond the approved contract, storage paths, answer keys, gabarito, or internal traces

Storage considerations:

- JSON store can support internal-staging validation
- PostgreSQL is better for production durability, querying, and concurrency later
- do not block progress planning on PostgreSQL, but do not pretend JSON is multi-instance production storage

## UI Principles

Future UI should show:

- `Marcar como estudado`
- `Continuar depois`
- `Pendente`
- `Revisão sugerida`

Avoid:

- automatic completion
- fake percentages
- score without correction
- ranking
- gabarito
- noisy status panels
- internal backend/pipeline/protected-read language

Progress actions must be explicit, understandable, and reversible or idempotent where practical.

## Safety And Non-goals

No:

- progress mutation now
- automatic completion
- studied/completed state now
- persisted attempts now
- official correction
- score
- answer-key or gabarito reveal
- simulado execution
- OCR or LLM expansion
- scheduler behavior
- PostgreSQL work
- auth provider or signup work

## Recommended Future Phases

1. `Progress-B`: backend event write contract.
2. `Progress-C`: frontend same-origin proxy/API wrapper.
3. `Progress-D`: minimal explicit `Marcar bloco como estudado` UI.
4. `Progress-QA-A`: browser/API QA for explicit progress events.
5. `ReviewBlock-Progress-A`: make review-after-3 use studied materials.
6. `Correction/Scoring-Planning-A`: plan official correction only after answer-key boundaries are approved.
7. `Simulado-Planning-A`: plan simulation readiness and execution later.
