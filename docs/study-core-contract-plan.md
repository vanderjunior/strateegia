# Core Study Flow Contract Plan

## Purpose

Define the core study flow before implementing study material summaries, questions, cycles, reviews, reinforcement, or simulations.

This is a planning contract only. It does not add endpoints, UI behavior, parser changes, OCR expansion, LLM calls, generated content, simulado execution, progress mutation, scheduler behavior, PostgreSQL, external auth, or signup.

## Product Objective

The product should help the user study from the official edital scope using their own learning materials.

Core principle:

- edital content/programmatic scope defines what must be studied
- bibliography is optional reference support when provided
- uploaded study materials are the learning source
- study sequence should follow edital scope and coverage gaps
- concise summaries and fixation questions should help the user retain material
- wrong answers should reinforce the specific theme/topic/subtopic that caused the error
- after every 3 studied materials, the app should run a cumulative review with summary and questions
- simulations/exams come later, after the learning and review loop is stable

## User-Facing Flow

1. Send edital:
   The user uploads an edital and classifies it as `Edital`.

2. Analyze edital:
   The user explicitly runs `Analisar edital`. The system creates bounded taxonomy/lifecycle metadata. An uploaded edital is not the same as an analyzed edital.

3. Send study materials:
   The user uploads materials classified as `Material de estudo`. Bibliography can be uploaded separately as `Bibliografia / referência`.

4. Prepare materials:
   The system prepares study materials into bounded readiness metadata and later safe study content surfaces. This should not expose raw storage paths or uncontrolled raw text.

5. Start study:
   The user opens a study sequence based on analyzed edital taxonomy and available prepared study materials.

6. Read summary:
   For each study block/material, the user sees a concise summary tied to edital topic/subtopic scope.

7. Answer fixation questions:
   The user answers small fixation question candidates for the current study block.

8. Reinforce errors:
   Wrong answers are classified back to the relevant area/topic/subtopic. The app reinforces that specific theme before moving forward.

9. Review after 3 materials:
   After every 3 studied materials, the app creates a cumulative review block with a short summary and questions across those materials and their edital topics.

10. Later simulation:
    Simulados/exams are introduced later, after the summary/question/review loop is safe and explicit.

## Domain Objects

### Edital Scope

The official source of what must be studied.

Expected bounded fields:

- `edital_id`
- `analysis_status`
- `areas_count` or `themes_count`
- `topics_count`
- `subtopics_count`
- `coverage_status`
- `source`

Rules:

- concrete study can start only from an analyzed usable edital taxonomy
- `not_ready`, uploaded-only, failed, unknown, or unavailable states must not create concrete study sessions
- the edital itself is not a learning material for coverage

### Topic / Subtopic

The study scope units extracted from the edital.

Recommended hierarchy:

```text
area/theme -> topic -> subtopic
```

Rules:

- topic/subtopic labels are bounded study targets
- ambiguous taxonomy should be marked for review
- source order should be preserved
- raw edital excerpts should not be exposed in normal study contracts

### Study Material

The content source the user studies from.

Expected bounded fields:

- `document_id`
- `material_type=study_material`
- `preparation_status`
- `extraction_status`
- `section_count`
- `topics_hint_count`
- `ready_for_study`
- `warnings_count`
- `source`

Rules:

- study material must be prepared before it can generate study blocks
- minimal controlled preparation now exists through `POST /api/materials/{document_id}/study/prepare`
- current preparation returns bounded readiness metadata only: status, section count, chunk count, warnings count, and `ready_for_study`
- OCR-required material remains not ready until a separate OCR-capable contract exists
- preparation does not imply summary/question generation
- later refinements still need topic mapping before concrete study blocks can be built

### Study Block

A bounded unit of study that links edital scope to one or more prepared study materials.

Possible fields:

- `study_block_id`
- `edital_id`
- `topic_id`
- `subtopic_ids`
- `material_ids`
- `sequence_index`
- `status`
- `summary_available`
- `questions_available`
- `review_due_after_block`

Rules:

- one block should be small enough to read and answer fixation questions
- blocks should be ordered by edital taxonomy and coverage priority
- blocks should not mutate progress until a later explicit phase

### Study Session

A read/view state for the user to open a study block.

Possible fields:

- `study_session_id`
- `study_block_id`
- `title`
- `scope_label`
- `materials_count`
- `summary_status`
- `question_status`
- `review_state`

Rules:

- initial sessions should be guidance/read-only until progress mutation is approved
- sessions should not look executable if questions/progress are not implemented

### Summary

A concise explanation of the study block.

Possible fields:

- `summary_id`
- `study_block_id`
- `topic_id`
- `subtopic_ids`
- `body`
- `source_material_ids`
- `status`
- `needs_review`

Rules:

- summary must be clearly tied to source materials and edital scope
- generated summary should be treated as candidate/reviewable unless a later quality contract approves stronger language
- do not expose storage paths, raw extraction artifacts, or uncontrolled chunks

### Fixation Question Candidate

A candidate question for retention after reading a summary/material.

Possible fields:

- `question_id`
- `study_block_id`
- `topic_id`
- `subtopic_id`
- `prompt`
- `options`
- `explanation`
- `status`
- `source`

Rules:

- answer keys must not be exposed prematurely in browser surfaces where the user is answering
- questions are candidates until quality/review rules are defined
- no simulado behavior should be implied by fixation questions

### Error Classification

The mapping from a missed answer to the study scope that needs reinforcement.

Possible fields:

- `error_id`
- `question_id`
- `topic_id`
- `subtopic_id`
- `error_type`
- `reinforcement_status`
- `source`

Example error types:

- concept_gap
- detail_miss
- confusion_between_topics
- reading_attention
- unknown

Rules:

- wrong answers should reinforce the smallest reliable scope unit
- error tracking should not mutate durable progress until an explicit progress phase exists
- explanations should avoid shaming language

### Review Block

A cumulative review after every 3 studied materials.

Possible fields:

- `review_block_id`
- `trigger_material_count`
- `material_ids`
- `topic_ids`
- `summary_status`
- `question_count`
- `status`

Rules:

- first cadence: after every 3 prepared/studied materials
- review should include a short cumulative summary and fixation questions
- no calendar/scheduler behavior should be implied initially

## What Exists Today

- Auth/session and Docker Compose internal staging are working.
- Upload supports persisted `material_type`.
- Materials can be grouped by type in read-only UI.
- Study materials can be explicitly prepared through a controlled no-OCR action on material detail.
- Controlled edital analysis exists for uploaded `material_type=edital`.
- The deterministic edital parser can extract candidate sections/topics/subtopics/bibliography from structured textual sources.
- Bounded list/detail reads exist for materials, editais, material summary, edital summary, and pipeline summary.
- Bounded edital coverage endpoint/proxy/UI card exists and remains read-only.
- Study and PSCPP UI are gated until a real analyzed edital exists.
- Existing older backend services and routes for questions/simulados/progress exist in the codebase, but they are not the current real-user product flow and should not be exposed as final behavior without new bounded contracts.

## What Is Missing

- Reliable edital taxonomy with area/theme -> topic -> subtopic.
- Bounded bibliography material preparation.
- Topic-aware study material preparation/readiness beyond the current metadata-only preparation action.
- Coverage refinement based on prepared study materials.
- Study block sequencing from edital taxonomy and coverage.
- Safe study material summary contract.
- Fixation question candidate contract.
- Error classification and reinforcement loop.
- Review block contract after every 3 materials.
- Simulado/exam contract for later phases.
- Explicit progress mutation contract, if/when the product is ready.

## Recommended Implementation Sequence

1. `StudyMaterial-A`:
   Minimal controlled preparation/readiness for `material_type=study_material` is implemented. Later refinements can add topic mapping, but not summaries/questions/progress without separate contracts.

2. `StudySession-A`:
   Minimal read-only next session from one prepared `study_material` is implemented through `GET /api/study/session/next`. Later refinements can add edital-aware ordering across multiple materials, but not progress, questions, review blocks, or simulados without separate contracts.

3. `StudyBlocks-A/B/C`:
   Backend study blocks, frontend proxy/API, and minimal `/study` block rendering are implemented. Blocks remain read-only and do not mutate progress, create questions, create reviews, or execute simulados.

4. `StudySummary-A`:
   Define bounded candidate summaries for a study block. If generation is used, keep it behind an explicit review-only contract.

5. `FixationQuestions-A`:
   Define fixation question candidates for a study block without exposing answer keys prematurely.

6. `ErrorReinforcement-A`:
   Define how missed fixation questions map to topic/subtopic reinforcement.

7. `ReviewBlock-A`:
   Define the cumulative review block after every 3 studied materials.

8. `Simulado` later:
   Define exam/simulation generation and execution only after the study loop is stable.

Important dependency:

- `EditalTaxonomy-A` remains a prerequisite or parallel blocker because the study sequence depends on a reliable edital hierarchy.

## UI Simplification Rules

Normal user UI should show:

- next action
- edital state
- material readiness
- what to study now
- concise summary
- fixation questions when available
- reinforcement when needed
- review after 3 materials

Normal user UI should avoid:

- backend
- runtime
- pipeline
- chunk
- storage
- internal status/capability language
- raw parser diagnostics
- simulado/progress language before those phases are real

Preferred copy:

- `Preparar material para estudo`
- `Abrir estudo`
- `Resumo do conteúdo`
- `Questões de fixação`
- `Reforçar este tema`
- `Revisão acumulada`
- `Simulado em etapa futura`

## Safety Rules

- Do not expose raw storage paths.
- Do not expose raw document/OCR/chunk/section bodies in browser study contracts.
- Do not expose answer keys before the user has answered or before a specific review surface allows it.
- Do not present unsupported generated content as final truth.
- Treat generated summaries/questions as candidates until a quality/review contract exists.
- Keep all study reads user-scoped and authenticated where they use user materials.
- Keep `not_ready` edital/material states conservative.
- Do not mutate progress until an explicit progress phase is approved.
- Do not use previous exams as authoritative scope.

## Non-Goals

- no automatic simulado execution
- no progress mutation until an explicit phase
- no OCR expansion
- no LLM generation unless a review-only contract exists
- no PostgreSQL work
- no external auth provider or signup
- no scheduler/calendar behavior
- no new endpoints or UI behavior in this planning phase
- no exposure of raw content, storage paths, tokens, password hashes, answer keys, gabarito, or correction internals

## Recommended Next Implementation Phase

Recommended next phase: `StudyBlocks-QA-A`, followed by `StudyBlockDetail-A` or fixation-question planning after browser/API validation.

Reason:

- The product now has bounded preparation/readiness, one-material fallback, and a minimal read-only `/study` blocks surface.
- Browser/API QA should confirm the new `/study` blocks path before layering additional study structure on top.
- Summaries, fixation questions, reinforcement, and review blocks still depend on knowing which prepared material content maps to which edital topic/subtopic.
- The next product challenge is defining edital-aware ordering across prepared materials, without introducing questions, simulations, or progress mutation too early.
