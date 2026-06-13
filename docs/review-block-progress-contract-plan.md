# Progress-aware Review Eligibility Contract Plan

## Purpose

Define how future cumulative review eligibility should move from prepared-material counts to studied-material counts without inventing completion semantics too early.

This began as a planning contract. ReviewBlock-Progress-B implemented the first backend-only conservative derivation: a `study_material` counts as studied only when every backend-derived study block for that material has an explicit user-scoped `block_marked_studied` event. ReviewBlock-Progress-C aligned frontend proxy/API/types and existing `/study` copy so backend-provided `studied_materials` basis values are accepted and rendered safely. ReviewBlock-Progress-Fixture-A adds a deterministic development/test-only browser QA fixture that seeds analyzed edital access, three prepared study materials, and explicit studied-block events for the dedicated Compose QA user. This did not add progress mutation from review reads, material completion events, scoring, correction, gabarito handling, simulado behavior, OCR, LLM calls, scheduler behavior, PostgreSQL, provider work, or signup.

## Product Objective

Progress-aware review should eventually ensure that cumulative review is based on materials the student actually studied, not merely materials the system prepared.

Future target rule:

- after every 3 studied materials, offer a cumulative review

Current implemented safe rule:

- cumulative review remains based on prepared materials or available study blocks until at least 3 conservatively studied materials exist
- `review_basis=studied_materials` is backend-derived only when at least 3 materials satisfy the all-blocks rule
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

- `GET /api/study/review/next` uses `studied_materials` only when at least 3 materials satisfy the all-blocks rule; otherwise it falls back to prepared materials or study blocks
- `review_basis` can be `prepared_materials`
- `studied_materials_count` is conservatively derived in the backend
- the deterministic browser QA fixture is explicit development/test infrastructure and is not run by app startup
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

A backend-derived state indicating that a material has met the first approved study criteria.

Rules:

- depends on a safe block-to-material relationship
- requires every backend-derived block for the material to have an explicit `block_marked_studied` event
- must not be derived from upload, preparation, page open, or answer review alone
- does not mean the material is completed or mastered

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

Implemented starting point: Option A. Option D remains a possible future extension if an explicit material-level action is later approved.

## Recommended Initial Rule

Current implemented rule:

- `studied_materials_count` counts only prepared `study_material` files whose backend-derived blocks are all marked studied
- `GET /api/study/review/next` uses `basis=studied_materials` only when `studied_materials_count >= 3`
- `GET /api/study/review/next` continues using prepared materials or study blocks when fewer than 3 studied materials exist
- `/study` should continue saying `Baseada em materiais preparados` when `review_basis=prepared_materials`
- the frontend must not infer `studied_materials` from `studied_blocks_count`
- answer review and reinforcement must not count as proof that a material was studied

Future refinements:

- if fewer than 3 studied materials exist but 3 prepared materials exist, the product may still show a prepared-material review as `revisão sugerida`, not as progress-aware review
- material completion, explicit material action, percentages, and review completion remain separate future contracts

## Future Backend Strategy

Implemented in `ReviewBlock-Progress-B`.

Scope:

- update backend summary and review logic only
- derive `studied_materials_count` conservatively
- keep review endpoint read-only
- do not mutate progress from `GET /api/study/review/next`
- do not create material completion records from review reads
- do not use frontend-only derivation

Backend rules:

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

The backend now implements these fields when the all-blocks rule is satisfied. The frontend should render the backend-provided basis and counts, not compute eligibility.

## Deterministic Browser QA Fixture

ReviewBlock-Progress-Fixture-A provides a repeatable development/test seed for visual QA of the studied-material basis:

```bash
docker compose exec backend python -m app.services.review_progress_qa_fixture
```

Local non-Compose use can call:

```bash
python scripts/seed_review_progress_browser_qa.py
```

Fixture behavior:

- creates or reuses the dedicated Compose QA user
- upserts one bounded analyzed edital with `analysis_status=analyzed` and `review_state=ready_for_review`
- upserts three prepared `study_material` records with deterministic UUID-shaped ids and one backend-derived block each
- records explicit `block_marked_studied` events with stable idempotency keys
- converges on repeated runs without duplicating fixture materials or progress counts
- removes older records carrying this fixture tag for the dedicated QA user when they used a previous unsafe id format, without clearing unrelated user data
- refuses to run when `APP_ENV=production`

Expected QA state:

- `GET /api/study/progress/summary` returns `studied_materials_count>=3` and `review_basis=studied_materials`
- `GET /api/study/review/next` returns `basis=studied_materials`
- `/study` can render the existing studied-material review/progress copy because the fixture also satisfies the analyzed-edital gate

The fixture does not change production defaults, review eligibility rules, frontend UI, material completion semantics, percentages, scoring, gabarito, correction, simulado behavior, OCR, LLM calls, scheduler behavior, PostgreSQL, provider work, or signup.

ReviewBlock-Progress-C frontend alignment:

- accepts `basis=studied_materials` from `GET /api/study/review/next`
- accepts `review_basis=studied_materials` from `GET /api/study/progress/summary`
- preserves `studied_materials_count`
- renders `Baseada em materiais estudados` only when the review candidate basis is backend-provided as `studied_materials`
- renders `Revisão sugerida com base em materiais estudados.` only when progress summary `review_basis` is backend-provided as `studied_materials`
- does not derive studied materials from `studied_blocks_count`

## Relationship With Review Card

Current `/study` review card should:

- keep saying `Baseada em materiais preparados` for `review_basis=prepared_materials`
- keep using `Revisão acumulada sugerida`
- avoid broken review-detail routes until a review detail page exists
- avoid claiming studied or completed material

`/study` review card may say:

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

Future progress card may show studied materials only when backend derivation returns a positive count and copy is approved.

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

1. `ReviewBlock-Progress-QA-A`: browser/API QA for studied-material review eligibility and `/study` copy.
2. `MaterialProgress-Planning-A`: plan explicit material-level action only if Option C or D is chosen.
