# Study Blocks Inventory

## Purpose

Audit the existing backend and frontend capabilities that can support future edital-aware study blocks, before implementing `StudyBlocks-A`.

This is an inventory document only. It does not add endpoints, UI behavior, progress mutation, generated questions, simulados, OCR, LLM, scheduler, PostgreSQL, provider, or signup behavior.

## Existing Backend Endpoints

### `POST /api/materials/{document_id}/study/prepare`

- Read/write preparation endpoint for owned `material_type=study_material` files.
- Uses deterministic document preparation for `.txt`, `.md`, and textual `.pdf`.
- Can create safe extraction, chunk, section, and pipeline artifacts through `DocumentPipelineService.prepare_document_without_ocr`.
- Does not trigger OCR when preparation is explicitly no-OCR.
- Reusable for study blocks as the prerequisite that makes a study material eligible.
- Not a study-block endpoint and does not decide ordering or progress.

### `GET /api/materials/{document_id}/study/summary`

- Authenticated, user-scoped, read-only endpoint.
- Returns bounded prepared-material summary fields:
  - `document_id`
  - `summary_status`
  - `material_type`
  - `title`
  - `sections_count`
  - bounded section `items`
  - `warnings_count`
  - `source`
- Section items include only `section_id`, `title`, placeholder `summary`, `key_points`, `estimated_minutes`, and `status`.
- Reusable as the safe content source for study blocks.
- Does not expose raw text, chunk bodies, section bodies, OCR output, storage paths, answer keys, or correction/progress fields.

### `GET /api/study/session/next`

- Authenticated, user-scoped, read-only endpoint.
- Selects one prepared `study_material`.
- Ignores editais, bibliography, previous exams, notes, other, and unknown materials as primary study-session sources.
- Returns either:
  - `session_status=not_ready` with safe next actions, or
  - `ready` / `needs_review` with one material's bounded study-summary items.
- Selection is intentionally simple:
  - prefer `ready` over `needs_review`
  - choose the oldest deterministic candidate within the preferred status group
- Reusable as the first simple session surface.
- Too narrow for true edital-aware multi-material blocks because it does not map edital topics/subtopics to material sections.

### `GET /api/editais`

- Authenticated, user-scoped, read-only endpoint.
- Returns bounded edital extraction/alignment summary metadata.
- Includes `analysis_status`, `topics_count`, `subtopics_count`, `bibliography_count`, `gaps_count`, `review_state`, `coverage_status`, `alignment_status`, and `warnings_count`.
- Reusable to determine whether a real analyzed edital exists.
- Not enough by itself to build study blocks because it does not expose topic/subtopic ordering details or material-section matches.

### `GET /api/editais/{edital_id}/summary`

- Authenticated, user-scoped, read-only endpoint.
- Returns bounded metadata and summary flags for one edital.
- Reusable for gating and user-facing state.
- Not sufficient for study block construction because it does not expose topic/subtopic details or matched material sections.

### `GET /api/editais/{edital_id}/coverage`

- Authenticated, user-scoped, read-only endpoint.
- Returns bounded coverage counts and topic-level coverage items:
  - `topics_count`
  - `subtopics_count`
  - covered/partial/uncovered subtopic counts
  - materials considered count
  - per-topic coverage status
- Reusable as a conservative coverage summary.
- Current bounded response does not include document ids, section ids, or subtopic-level mappings.
- This is close to study-block needs but intentionally does not expose enough detail to render ordered blocks.

### Existing broader/internal reads

- `GET /api/materials/{document_id}/sections` and `GET /api/materials/{document_id}/chunks` exist but should not become the browser-facing study-block contract.
- They expose operational document structure and can include raw chunk text.
- Future study blocks should use a new bounded backend endpoint, not direct sections/chunks reads.

## Existing Backend Data and Services

### Edital extraction data

`EditalIngestionService` persists:

- `EditalExtractionResult`
- edital `sections`
- `topics`
- `subtopics`
- bibliography candidates
- exclusions
- weight hints
- warnings
- ingestion state

This is the strongest source for official study scope. A future block contract should use this backend data for topic/subtopic ordering and labels.

Important caveat:
- The extraction is heuristic and candidate/review-oriented.
- `analysis_status=not_ready`, `failed`, or unknown should not create concrete blocks.

### Material preparation data

`DocumentPipelineService` can persist:

- `DocumentExtractionResult`
- `DocumentSection`
- `DocumentChunk`
- `DocumentPipelineState`

Study material summary already converts prepared `DocumentSection` data into a bounded section list.

Important caveat:
- Raw extraction text and chunk bodies must stay server-side.
- Browser-facing study blocks should expose only bounded section references, titles, status, and placeholder/guidance copy.

### Bibliography and topic alignment data

`BibliographyAlignmentService` already computes richer internal matching artifacts:

- `TopicCoverageCandidate`
- `SectionCoverageCandidate`
- `DocumentCoverageCandidate`
- `BibliographyItemAlignment`
- `CoverageGap`
- `CoverageRedundancy`
- alignment evidence and matched terms

This is the most reusable backend capability for true edital-aware study blocks.

Important caveat:
- The current bounded coverage endpoint does not expose section-level matches.
- Internal evidence can include excerpts and matched terms; future study-block responses must whitelist carefully and avoid raw evidence snippets unless separately approved.

### JSON repository support

`JsonStudyRepository` already supports user-scoped access to:

- uploaded materials
- document extraction results
- document sections/chunks
- edital extraction results
- bibliography alignment states/results
- pipeline states

This is enough persistence for an internal-staging read contract. It is still not production/multi-instance storage.

## Existing Frontend Surfaces

### `/study`

- Consumes `fetchNextStudySession()`.
- Shows one real read-only session from a prepared study material when available.
- Shows not-ready/auth/offline states otherwise.
- Does not compute material order, topic matching, or progress.
- Should remain a renderer for bounded backend output.

### Material detail

- Shows manual `Preparar para estudo` for authenticated real `study_material` items.
- Shows `Resumo do material` from the bounded study-summary endpoint.
- Refreshes the summary after successful prepare.
- Does not show raw content, chunks, storage paths, generated questions, simulados, or progress controls.

### Edital detail

- Shows bounded edital metadata and coverage card.
- Coverage card uses `GET /api/editais/{edital_id}/coverage`.
- Renders topic-level coverage counts and statuses.
- Does not compute coverage or study order on the client.

### Materials list/grouping

- Groups by `material_type`.
- Helps users distinguish editais, study materials, bibliography, previous exams, notes, and unknown files.
- Does not trigger preparation, analysis, matching, or study planning.

## What Already Exists Enough To Reuse

- User-scoped material upload and `material_type`.
- Deterministic no-OCR preparation for study materials.
- Bounded prepared-material summary items.
- One simple read-only next study session from prepared materials.
- Edital analysis lifecycle metadata.
- Topic/subtopic counts from edital extraction.
- Bounded topic-level coverage counts.
- Internal alignment data that already knows about topic-to-document and section-to-topic candidates.
- Test patterns for auth, owner scope, idempotent reads, bounded shape, and no-leakage.

## What Is Missing For True Edital-aware Study Blocks

- A bounded topic/subtopic to material-section mapping contract.
- A backend-owned block ordering strategy.
- Block status fields such as `ready`, `needs_review`, `missing_material`, and `not_ready`.
- Multi-material sequencing.
- A safe distinction between:
  - official edital topic/subtopic
  - matched study material section
  - bibliography/reference support
  - previous exam/practice source
- A review grouping rule after every 3 materials.
- A future connection to fixation questions.
- A future error-reinforcement loop.
- Explicit progress mutation contract, intentionally deferred.
- QA for browser rendering of real edital-aware blocks.

## Recommended Backend Contract

Prefer a new read-only endpoint for `StudyBlocks-A`:

```http
GET /api/study/blocks
```

Why a new endpoint:

- `GET /api/study/session/next` is intentionally simple and material-based.
- Extending it directly risks mixing single-session selection with multi-block planning.
- Study blocks need edital scope, material-section matches, coverage status, review state, and ordering.
- The backend already has enough internal alignment data to own that logic.

Suggested bounded shape:

```json
{
  "blocks_status": "ready|needs_review|not_ready",
  "edital_id": "edital:doc-123",
  "blocks_count": 2,
  "blocks": [
    {
      "block_id": "study-block:topic-1:doc-456:section-0",
      "order_index": 0,
      "topic_id": "topic-1",
      "topic_label": "Atos administrativos",
      "subtopic_id": "subtopic-1",
      "subtopic_label": "Elementos do ato administrativo",
      "document_id": "doc-456",
      "material_title": "aula.md",
      "section_id": "doc-456:section:0",
      "section_title": "Atos administrativos",
      "coverage_status": "covered|partial|missing_material|needs_review",
      "estimated_minutes": 5,
      "summary_status": "ready|needs_review|not_ready",
      "next_actions": [
        {
          "label": "Abrir material",
          "href": "/materials/doc-456"
        }
      ]
    }
  ],
  "review_policy": {
    "review_after_materials": 3,
    "enabled": false
  },
  "source": "user_scope"
}
```

Initial implementation can be smaller than this, but it should preserve the principle:
- backend decides ordering and matching
- frontend renders only bounded backend output
- no raw excerpts or chunk bodies
- no progress mutation

## Frontend Responsibility

The frontend should not compute:

- block order
- edital topic/subtopic matching
- material-section matching
- coverage classification
- review grouping
- readiness to unlock questions or progress

The frontend should:

- call a same-origin proxy for the bounded study-block endpoint
- render blocks, statuses, and next actions
- show empty/auth/offline states
- keep demo/reference content secondary
- keep copy truthful when blocks are candidate/review-oriented
- avoid raw content, internal evidence, storage paths, tokens, answer keys, and correction fields

## Recommended Implementation Sequence

1. `StudyBlocks-A`:
   Implement backend `GET /api/study/blocks` with a conservative bounded shape.

2. `StudyBlocks-Proxy-A`:
   Add frontend same-origin proxy/API wrapper and render blocks on `/study`.

3. `StudyBlocks-QA-A`:
   Browser/API QA with a prepared study material and analyzed edital.

4. `ReviewBlock-A`:
   Add read-only review grouping after every 3 materials.

5. `FixationQuestions-A`:
   Add review-only fixation question candidates after the block contract is stable.

## Non-goals

- No progress mutation.
- No generated questions.
- No simulado generation or execution.
- No LLM summary generation.
- No OCR expansion.
- No scheduler/calendar behavior.
- No PostgreSQL migration.
- No auth provider or signup.
- No frontend-only matching/order logic.
- No raw document text, OCR output, chunk body, section body, storage path, token, password hash, answer key, gabarito, or correction field exposure.
