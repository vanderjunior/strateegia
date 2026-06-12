# Progress-aware Review Eligibility Contract Plan

## Purpose

Define how future cumulative review eligibility should move from prepared-material counts to studied-material counts without inventing completion semantics too early.

This is a planning contract only. It does not change `GET /api/study/review/next`, `GET /api/study/progress/summary`, frontend behavior, progress mutation, review eligibility, material completion, scoring, correction, gabarito handling, simulado behavior, OCR, LLM calls, scheduler behavior, PostgreSQL, provider work, or signup.

## Product Objective

Progress-aware review should eventually ensure that cumulative review is based on materials the student actually studied, not merely materials the system prepared.

Future target rule:

- after every 3 studied materials, offer a cumulative review

Current safe rule:

- cumulative review remains based on prepared materials or available study blocks
- progress-aware eligibility is not implemented yet
- `material_type=study_material` plus preparation means a material is ready for study, not that it has been studied

## Current State

Available today:

- prepared study materials exist
- study blocks exist
- block detail exists
- cumulative review candidate exists through `GET /api/study/review/next`
- explicit block progress exists through `POST /api/study/progress/events`
- progress summary exists through `GET /api/study/progress/summary`
- `block_marked_studied` is explicit and increments `studied_blocks_count`
- `/study/blocks/[blockId]` has a user-clicked `Marcar bloco como estudado` button
- `/study` shows a read-only progress summary card

Important current limits:

- `GET /api/study/review/next` still uses prepared materials or study blocks
- `review_basis` can be `prepared_materials`
- `studied_materials_count` remains `0`
- no material completion semantics exist
- no automatic progress writes exist
- no score, gabarito, official correction, persisted attempts, or simulado execution exists

## Key Distinction

### `prepared_material`

A material is prepared when it is ready for bounded study surfaces.

Rules:

- means the system can show summaries or blocks
- does not mean the student studied it
- does not mean the student completed it
- can support today's read-only review candidate

### `studied_block`

A block is studied when an explicit `block_marked_studied` event exists for that block.

Rules:

- requires explicit user action
- increments `studied_blocks_count`
- does not automatically mean the source material is studied
- does not imply mastery, score, or official correction

### `studied_material`

A future derived state indicating that a material has met approved study criteria.

Rules:

- must depend on a safe block-to-material relationship
- must not be derived from upload, preparation, page open, or answer review alone
- should remain `0` until the backend owns the derivation

### `review_eligible_material`

A future studied material that can count toward review-after-3.

Rules:

- should normally be a `study_material`
- should not include edital files, bibliography, previous exams, notes, unknown files, or other files by default
- should only count once per material for review eligibility

## Candidate Rules For Material Studied

### Option A: All Blocks Required

A material is studied only when all study blocks belonging to that material are marked studied.

Pros:

- conservative
- avoids false completion
- easy for users to understand once blocks are visible
- keeps review-after-3 aligned to actual block coverage

Cons:

- may be strict if a long material generates many blocks
- may delay review if one low-value block remains unmarked

### Option B: Minimum Threshold

A material is studied when at least N blocks or X percent of its blocks are marked studied.

Pros:

- practical for long materials
- avoids blocking review on every small block

Cons:

- introduces percentage and threshold complexity
- risks fake completion language
- needs careful UI copy to avoid `100%` or completion claims

### Option C: Explicit Material Action

A material is studied only when the user explicitly clicks a future `Marcar material como estudado` action.

Pros:

- clear user intent
- simple eligibility event
- avoids hidden derivation

Cons:

- adds another action
- may duplicate the block-level action
- needs a material detail or study path placement that feels natural

### Option D: Hybrid

A material can be considered studied when:

- all required blocks are marked studied, or
- the user explicitly marks the material as studied in a future approved phase

Pros:

- conservative by default
- allows explicit override later
- keeps backend-owned derivation while preserving user agency

Cons:

- needs clear conflict and idempotency rules
- requires careful copy so explicit material action does not imply mastery

Recommendation: start with Option A or Option D, but do not implement either until a dedicated backend phase defines the exact derivation and QA proves it safe.

## Recommended Initial Rule

For now:

- `studied_materials_count` should remain `0`
- `GET /api/study/review/next` should continue using prepared materials or study blocks
- `/study` should continue saying `Baseada em materiais preparados` when `review_basis=prepared_materials`
- the frontend must not infer `studied_materials` from `studied_blocks_count`
- answer review and reinforcement must not count as proof that a material was studied

When implemented later:

- the backend may derive `studied_materials_count` only after it can map blocks to source material and determine that approved required blocks are studied
- `review_basis` may become `studied_materials` only when at least 3 studied materials exist
- if fewer than 3 studied materials exist but 3 prepared materials exist, the product may still show a prepared-material review as `revisão sugerida`, not as progress-aware review

## Future Backend Strategy

Recommended future phase: `ReviewBlock-Progress-B`.

Scope:

- update backend summary and review logic only
- derive `studied_materials_count` conservatively
- keep review endpoint read-only
- do not mutate progress from `GET /api/study/review/next`
- do not create material completion records from review reads
- do not use frontend-only derivation

Potential backend rules:

- list prepared `study_material` documents owned by the user
- build or read backend-owned study blocks for each material
- map `block_marked_studied` events to block ids
- group studied blocks by `material_id`
- count a material as studied only when the approved material-studied rule is satisfied
- set `review_basis="studied_materials"` only when at least 3 eligible studied materials exist
- otherwise keep `review_basis="prepared_materials"` or `none`

## Future Response Considerations

`GET /api/study/progress/summary` may later include:

```json
{
  "studied_materials_count": 3,
  "review_due": true,
  "review_basis": "studied_materials"
}
```

`GET /api/study/review/next` may later include:

```json
{
  "basis": "studied_materials",
  "materials_count": 3
}
```

These fields should change only after the backend implements the derivation. The frontend should render the backend-provided basis and counts, not compute eligibility.

## Relationship With Review Card

Current `/study` review card should:

- keep saying `Baseada em materiais preparados` for `review_basis=prepared_materials`
- keep using `Revisão acumulada sugerida`
- avoid broken review-detail routes until a review detail page exists
- avoid claiming studied or completed material

Future `/study` review card may say:

- `Baseada em materiais estudados`

Only when the backend returns `review_basis=studied_materials`.

## Relationship With Progress Card

Current `/study` progress summary card should:

- show prepared materials
- show blocks marked as studied
- show reviewed questions without scoring
- optionally show opened blocks and reinforcement counts
- not show studied materials while `studied_materials_count=0`
- not show material completion
- not show percentages or progress bars

Future progress card may show studied materials only after backend derivation exists and copy is approved.

## Relationship With Answer Review And Reinforcement

Answer review and reinforcement are not proof that a material was studied.

Rules:

- `question_reviewed` may show engagement
- reviewed questions do not imply correctness
- reviewed questions do not imply material completion
- reinforcement does not imply official error classification
- weak-topic signals should not be used for review eligibility until persistence and semantics are explicit

## Relationship With Simulado

Progress-aware review may later feed simulado readiness, but no simulado work is included here.

Future simulado readiness should not consume `studied_materials_count` until:

- studied-material derivation is implemented
- review eligibility is QA-closed
- scoring/correction boundaries are separately approved

## Copy Rules

Allowed today:

- `materiais preparados`
- `blocos marcados como estudados`
- `revisão sugerida`
- `acompanhamento do estudo`
- `ações registradas por você`

Allowed only after implementation:

- `materiais estudados`
- `revisão baseada em materiais estudados`

Forbidden until implemented:

- `material concluído`
- `você concluiu`
- `progresso atualizado`
- `100%`
- `percentual concluído`
- official `acertos/erros`
- `pontuação`
- `gabarito`
- `resposta correta`
- `alternativa correta`

## Safety And Non-goals

No:

- material completion now
- automatic completion
- frontend-only studied-material derivation
- progress mutation from review endpoints
- answer-key or gabarito reveal
- score
- official correction
- persisted answer attempts
- simulado execution
- OCR or LLM expansion
- scheduler behavior
- PostgreSQL work
- provider or signup work

## Recommended Future Phases

1. `ReviewBlock-Progress-B`: backend conservative studied-material derivation planning/implementation.
2. `ReviewBlock-Progress-C`: frontend API/type adjustments if backend response shape changes.
3. `ReviewBlock-Progress-D`: UI copy update only if backend basis becomes `studied_materials`.
4. `ReviewBlock-Progress-QA-A`: browser/API QA for studied-material review eligibility.
5. `MaterialProgress-Planning-A`: plan explicit material-level action only if Option C or D is chosen.
