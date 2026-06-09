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
- Backend `GET /api/study/blocks` now provides the first read-only bounded study-block sequence contract; frontend same-origin proxy/API wrapper and minimal `/study` UI exist.
- Backend `GET /api/study/blocks/{block_id}` now provides the first read-only bounded study-block detail contract; frontend same-origin proxy/API wrapper and minimal visible UI exist.
- Backend `GET /api/study/blocks/{block_id}/questions` now provides the first read-only bounded fixation-question candidate contract; frontend same-origin proxy/API helper and visible review-only card exist.
- Backend `POST /api/study/blocks/{block_id}/questions/{question_id}/answer/review` now provides a stateless bounded answer-review contract; frontend same-origin proxy/API helper and selectable review UI exist.
- Backend `GET /api/study/review/next` now provides the first read-only bounded cumulative-review candidate based on prepared materials/study blocks; frontend same-origin proxy/API helper and compact `/study` card exist.
- Backend `POST /api/study/progress/events` and `GET /api/study/progress/summary` now provide the first explicit backend-only study progress event contract; frontend proxy/UI remain pending.

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

- `GET /api/study/session/next`
- `GET /api/study/blocks`
- `GET /api/study/blocks/{block_id}`
- `GET /api/study/blocks/{block_id}/questions`
- `POST /api/study/blocks/{block_id}/questions/{question_id}/answer/review`
- `GET /api/study/review/next`
- `POST /api/study/progress/events`
- `GET /api/study/progress/summary`

## Recommended Implementation Order

1. `GET /api/materials`
2. `GET /api/editais`
3. `GET /api/materials/{document_id}/summary`
4. `GET /api/editais/{edital_id}/summary`
5. `GET /api/materials/{document_id}/pipeline/summary`
6. `GET /api/editais/{edital_id}/coverage`
7. `GET /api/pipeline/recent`
8. `GET /api/study/session/next`
9. `GET /api/study/blocks`
10. `GET /api/study/blocks/{block_id}`
11. `GET /api/study/blocks/{block_id}/questions`
12. `POST /api/study/blocks/{block_id}/questions/{question_id}/answer/review`
13. `GET /api/study/review/next`
14. `POST /api/study/progress/events`
15. `GET /api/study/progress/summary`

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

### Controlled action: `POST /api/materials/{document_id}/study/prepare`

Purpose:
- prepare one owned `material_type=study_material` for later study using the existing deterministic no-OCR document preparation path
- return bounded readiness metadata only
- not generate summaries, questions, simulados, study cycles, or progress updates

Implemented shape:

```json
{
  "document_id": "doc-123",
  "preparation_status": "ready_for_study",
  "material_type": "study_material",
  "section_count": 4,
  "chunk_count": 12,
  "warnings_count": 0,
  "ready_for_study": true,
  "source": "user_scope"
}
```

Status semantics:
- `ready_for_study`: safe text exists and bounded sections/chunks were created
- `needs_review`: safe text exists but structure is weak or incomplete
- `not_ready`: no safe text is available or OCR is required
- `failed`: controlled deterministic preparation failed

Rules:
- authenticated and user-scoped
- missing or non-owner material returns `404`
- non-`study_material` material returns `422`
- `.txt`, `.md`, and textual `.pdf` can be prepared deterministically
- OCR-required PDFs return `not_ready`; OCR is not triggered
- response must not expose raw text, chunks, sections, OCR output, storage paths, answer keys, gabarito, or progress/correction fields

### `GET /api/materials/{document_id}/study/summary`

Purpose:
- return a bounded read-only study summary structure for one owned prepared `material_type=study_material`
- provide conservative section-level placeholders from prepared section metadata only
- not generate final summaries, questions, simulados, study cycles, or progress updates
- implemented in StudySummary-B as a backend read-only contract
- frontend same-origin proxy/API wrapper implemented in StudySummary-C
- minimal material-detail read-only UI implemented in StudySummary-D

Implemented shape:

```json
{
  "document_id": "doc-123",
  "summary_status": "ready",
  "material_type": "study_material",
  "title": "aula.md",
  "sections_count": 2,
  "items": [
    {
      "section_id": "doc-123:section:0",
      "title": "Atos administrativos",
      "summary": "Resumo em preparação para esta seção.",
      "key_points": ["Atos administrativos"],
      "estimated_minutes": 5,
      "status": "ready"
    }
  ],
  "warnings_count": 0,
  "source": "user_scope"
}
```

Status semantics:
- `ready`: prepared material has usable section titles and no warnings
- `needs_review`: prepared material exists but structure is weak, generic, or warning-bearing
- `not_ready`: material is not prepared, has no prepared sections, or has no safe extraction artifacts
- `failed`: deterministic preparation status failed

Rules:
- authenticated and user-scoped
- missing or non-owner material returns `404`
- non-`study_material` material returns `422`
- `GET` is idempotent and does not auto-prepare material
- frontend proxy path is `GET /api/materials/[materialId]/study/summary`
- section summaries are conservative placeholders, not generated final truth
- key points are derived from bounded section titles/headings only
- response must not expose raw text, chunks, sections, OCR output, storage paths, evidence snippets, answer keys, gabarito, progress, or correction fields

### `GET /api/study/session/next`

Purpose:
- return one minimal read-only study session from an owned prepared `material_type=study_material`
- use existing bounded study summary fields as the session content
- not require edital alignment yet, but preserve a safe note when the session is not fully connected to an analyzed edital
- implemented in StudySession-A as an idempotent backend read-only contract

Implemented ready shape:

```json
{
  "session_status": "ready",
  "session_id": "study-session:doc-123",
  "document_id": "doc-123",
  "material_title": "aula.md",
  "material_type": "study_material",
  "summary_status": "ready",
  "estimated_minutes": 10,
  "sections_count": 2,
  "items": [
    {
      "section_id": "doc-123:section:0",
      "title": "Atos administrativos",
      "summary": "Resumo em preparação para esta seção.",
      "key_points": ["Atos administrativos"],
      "estimated_minutes": 5,
      "status": "ready"
    }
  ],
  "next_actions": [
    {
      "label": "Abrir material",
      "href": "/materials/doc-123"
    },
    {
      "label": "Ver materiais",
      "href": "/materials"
    }
  ],
  "message": "Este estudo ainda não está conectado completamente ao edital.",
  "source": "user_scope"
}
```

Implemented not-ready shape:

```json
{
  "session_status": "not_ready",
  "message": "Envie e prepare um material de estudo para começar.",
  "next_actions": [
    {
      "label": "Enviar material",
      "href": "/materials/upload"
    },
    {
      "label": "Ver materiais",
      "href": "/materials"
    }
  ],
  "source": "user_scope"
}
```

Selection strategy:
- consider only owned materials with `material_type=study_material`
- ignore editais, bibliography, previous exams, notes, other, and unknown materials as primary session sources
- consider only prepared summaries with `summary_status=ready` or `needs_review` and at least one bounded summary item
- prefer `ready` over `needs_review`
- choose the oldest deterministic candidate within the preferred status group by `created_at`, then `document_id`

Rules:
- authenticated and user-scoped
- unauthenticated returns `401`
- no prepared study material returns `200` with `session_status=not_ready`
- `GET` is idempotent and does not prepare materials, mark completion, mutate progress, generate questions, generate simulados, call OCR, or call an LLM
- frontend proxy path is `GET /api/study/session/next`
- response must not expose raw text, chunks, sections, OCR output, storage paths, evidence snippets, answer keys, gabarito, progress, or correction fields

### `GET /api/study/blocks`

Purpose:
- return a backend-owned bounded sequence of study blocks from owned prepared `material_type=study_material` files
- connect blocks to analyzed edital topic/subtopic scope when a safe bounded label match exists
- return material-only blocks when prepared materials exist but no analyzed edital is available
- keep block ordering server-side so the frontend does not compute topic/material matching
- implemented in StudyBlocks-A as an idempotent backend read-only contract

Implemented ready/partial shape:

```json
{
  "blocks_status": "ready",
  "scope_status": "connected_to_edital",
  "blocks_count": 1,
  "estimated_minutes": 5,
  "items": [
    {
      "block_id": "study-block:subtopic-1:doc-123:0",
      "title": "Atos administrativos",
      "topic_id": "topic-1",
      "topic_label": "Direito Administrativo",
      "subtopic_id": "subtopic-1",
      "subtopic_label": "Atos administrativos",
      "material_id": "doc-123",
      "material_title": "aula.md",
      "sections_count": 1,
      "summary_status": "ready",
      "estimated_minutes": 5,
      "status": "ready",
      "actions": [
        {
          "label": "Estudar bloco",
          "href": "/study/blocks/study-block:subtopic-1:doc-123:0"
        }
      ]
    }
  ],
  "source": "user_scope"
}
```

Implemented not-ready shape:

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

Status semantics:
- `not_ready`: no prepared `study_material` with bounded summary items exists
- `partial`: prepared material blocks exist, but no analyzed edital is available
- `ready`: prepared blocks are connected to analyzed edital scope and have ready summary structure
- `needs_review`: edital exists but mapping is weak/incomplete, or one or more blocks need review

Ordering strategy:
- connected edital topic/subtopic blocks first
- then summary readiness
- then material `created_at`
- then `document_id`
- then section order

Rules:
- authenticated and user-scoped
- unauthenticated returns `401`
- `GET` is idempotent and does not prepare materials, mark completion, mutate progress, generate questions, generate simulados, call OCR, or call an LLM
- ignores editais, bibliography, previous exams, notes, other, and unknown materials as primary study-block sources
- frontend proxy path is `GET /api/study/blocks`
- frontend API helper is `fetchStudyBlocks()`
- visible `/study` list UI exists
- review-after-3 is not implemented yet
- response must not expose raw text, chunks, sections, OCR output, storage paths, evidence snippets, answer keys, gabarito, progress, or correction fields

### `GET /api/study/blocks/{block_id}`

Purpose:
- return a backend-owned bounded detail read for one current user study block
- resolve `block_id` against the same deterministic block ids produced by `GET /api/study/blocks`
- enrich the selected block with bounded prepared-material summary sections
- keep block resolution, user scope, topic/material/section mapping, and stale/missing handling server-side
- implemented in StudyBlockDetail-A as an idempotent backend read-only contract

Implemented shape:

```json
{
  "block_id": "study-block:subtopic-1:doc-123:0",
  "detail_status": "ready",
  "title": "Atos administrativos",
  "topic_id": "topic-1",
  "topic_label": "Direito Administrativo",
  "subtopic_id": "subtopic-1",
  "subtopic_label": "Atos administrativos",
  "material_id": "doc-123",
  "material_title": "aula.md",
  "summary_status": "ready",
  "estimated_minutes": 5,
  "sections": [
    {
      "section_id": "doc-123:section:0",
      "title": "Atos administrativos",
      "summary": "Resumo em preparação para esta seção.",
      "key_points": ["Atos administrativos"],
      "estimated_minutes": 5,
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

Status semantics:
- `ready`: block resolves to prepared study material and ready bounded summary sections
- `needs_review`: block resolves, but mapping or summary structure is weak
- `not_ready`: block resolves structurally but has no usable bounded summary section

Rules:
- authenticated and user-scoped
- unauthenticated returns `401`
- missing, non-owner, or unresolvable blocks return `404`
- repeated `GET` is idempotent and does not prepare materials, mark completion, mutate progress, generate questions, generate simulados, call OCR, or call an LLM
- frontend proxy path is `GET /api/study/blocks/[blockId]`
- frontend API helper is `fetchStudyBlockDetail(blockId)`
- visible `/study/blocks/[blockId]` UI exists
- response must not expose raw text, chunks, section bodies, OCR output, storage paths, evidence snippets, answer keys, gabarito, progress, correction fields, or internal traces

### `GET /api/study/blocks/{block_id}/questions`

Purpose:
- return deterministic read-only fixation-question candidates for one current user study block
- reuse backend-owned block detail resolution and user scope
- derive candidates only from bounded block detail fields such as block title, topic/subtopic labels, section titles, and key points
- keep the surface review-only: no answer submission, answer key, correction, scoring, progress mutation, simulado execution, OCR, or LLM behavior
- implemented in FixationQuestions-B as an idempotent backend read-only contract

Implemented shape:

```json
{
  "block_id": "study-block:subtopic-1:doc-123:0",
  "question_status": "ready",
  "mode": "review_only",
  "items": [
    {
      "question_id": "question:study-block:subtopic-1:doc-123:0:0",
      "type": "multiple_choice",
      "prompt": "Considerando o tema Direito Administrativo, escolha uma alternativa para orientar sua revisão de Atos administrativos.",
      "alternatives": [
        { "id": "A", "text": "Revisar Atos administrativos." },
        { "id": "B", "text": "Relacionar Direito Administrativo ao resumo do bloco." },
        { "id": "C", "text": "Identificar pontos principais de Atos administrativos." },
        { "id": "D", "text": "Retomar Direito Administrativo no material estudado." },
        { "id": "E", "text": "Comparar Atos administrativos com os demais pontos do bloco." }
      ],
      "topic_label": "Direito Administrativo",
      "subtopic_label": "Atos administrativos",
      "difficulty": "basic",
      "status": "candidate"
    }
  ],
  "warnings_count": 0,
  "source": "user_scope"
}
```

Status semantics:
- `ready`: block detail is ready and at least one bounded candidate can be derived
- `needs_review`: block detail resolves but mapping or summary structure needs review; candidates are marked `needs_review`
- `not_ready`: block detail has no usable bounded study content for question candidates
- `unsupported`: reserved for future policy-disabled cases

Rules:
- authenticated and user-scoped
- unauthenticated returns `401`
- missing, non-owner, or unresolvable blocks return `404`
- repeated `GET` is idempotent and does not create attempts, mark completion, mutate progress, generate official questions, generate simulados, call OCR, or call an LLM
- candidates are limited and deduplicated deterministically
- PSCPP/default objective review prefers `multiple_choice` with display-only alternatives `A`, `B`, `C`, `D`, `E`
- CEBRASPE-style review can use `true_false` with `Certo` and `Errado`
- `short_answer` remains fallback only when no safe objective alternatives can be formed
- frontend proxy path is `GET /api/study/blocks/[blockId]/questions`
- frontend API helper is `fetchStudyBlockQuestions(blockId)`
- answer keys and gabarito are not returned
- response must not expose raw text, chunks, section bodies, OCR output, storage paths, evidence snippets, answer keys, gabarito, correctness flags, correction fields, progress payloads, or internal traces

### Controlled review action: `POST /api/study/blocks/{block_id}/questions/{question_id}/answer/review`

Purpose:
- accept one bounded answer for a generated fixation-question candidate
- validate authentication and user scope through the current study block
- validate that `question_id` belongs to the current bounded candidates for `block_id`
- return conservative review feedback and a reinforcement suggestion
- remain stateless: no answer persistence, score record, correction record, or progress mutation
- implemented in AnswerReview-B as a backend contract
- frontend same-origin proxy/API helper implemented in AnswerReview-C; selectable review UI implemented in AnswerReview-D

Implemented request shape:

```json
{
  "answer": "string",
  "answer_format": "text"
}
```

Allowed `answer_format` values:
- `text`
- `choice`
- `true_false`

Implemented response shape:

```json
{
  "block_id": "study-block:material:doc-123:0",
  "question_id": "question:study-block:material:doc-123:0:0",
  "review_status": "reviewed",
  "result": "ungraded",
  "feedback": "Compare sua resposta com o resumo do bloco e revise os pontos principais relacionados.",
  "reinforcement": {
    "topic_label": "Direito Administrativo",
    "subtopic_label": "Atos administrativos",
    "message": "Revise o resumo do bloco e compare sua resposta com os pontos principais de Atos administrativos.",
    "suggested_action": "review_summary"
  },
  "source": "user_scope"
}
```

Status semantics:
- `review_status=reviewed` with `result=ungraded`: current conservative short-answer review
- `review_status=needs_review`: no safe automatic review rule exists for the candidate/format
- `review_status=not_ready` and `unsupported`: reserved for future bounded states

Rules:
- unauthenticated returns `401`
- missing, non-owner, or unresolvable blocks return `404`
- question ids that are not generated for the current block return `404`
- invalid request bodies return `422`
- answer strings are trimmed, required, and length-bounded
- repeated `POST` with the same input is idempotent because no state is written
- short-answer candidates are not graded for correctness in this phase
- frontend proxy path is `POST /api/study/blocks/[blockId]/questions/[questionId]/answer/review`
- frontend API helper is `reviewStudyBlockQuestionAnswer(blockId, questionId, payload)`
- frontend proxy forwards cookies server-side, strips request fields outside `answer` and `answer_format`, and whitelists response fields
- answer keys, gabarito, correct answers, correct alternatives, authoritative correctness flags, solutions, hidden rationale, scores, correction records, progress payloads, raw content, storage paths, tokens, and internal traces are forbidden

### `GET /api/study/review/next`

Purpose:
- return the next bounded cumulative-review candidate from prepared study materials or available study blocks
- keep the first review-after-3 contract read-only until progress semantics exist
- not claim materials were studied, completed, or recorded as progress
- implemented in ReviewBlock-B as a backend contract; frontend same-origin proxy/API helper implemented in ReviewBlock-C; a compact read-only `/study` review card was added in ReviewBlock-D

Implemented ready/needs-review shape:

```json
{
  "review_status": "ready",
  "review_id": "review:prepared_materials:3:3",
  "basis": "prepared_materials",
  "materials_count": 3,
  "blocks_count": 3,
  "estimated_minutes": 15,
  "title": "Revisão acumulada",
  "summary": {
    "status": "ready",
    "items": [
      {
        "title": "Atos administrativos",
        "message": "Revise Atos administrativos no material aula.md.",
        "topic_label": "Direito Administrativo",
        "subtopic_label": "Atos administrativos"
      }
    ]
  },
  "questions": {
    "status": "ready",
    "items_count": 3
  },
  "reinforcement": {
    "status": "needs_review",
    "weak_topics_count": 0,
    "items": [
      {
        "topic_label": null,
        "subtopic_label": null,
        "message": "Ainda não há histórico de respostas para apontar pontos fracos reais."
      }
    ]
  },
  "actions": [
    {
      "label": "Abrir revisão",
      "href": "/study/review/review:prepared_materials:3:3"
    }
  ],
  "source": "user_scope"
}
```

Implemented not-ready shape:

```json
{
  "review_status": "not_ready",
  "review_id": null,
  "basis": "prepared_materials",
  "materials_count": 0,
  "blocks_count": 0,
  "estimated_minutes": 0,
  "title": "Revisão acumulada",
  "summary": {
    "status": "not_ready",
    "items": []
  },
  "questions": {
    "status": "not_ready",
    "items_count": 0
  },
  "reinforcement": {
    "status": "not_ready",
    "weak_topics_count": 0,
    "items": []
  },
  "actions": [],
  "message": "Prepare pelo menos 3 materiais de estudo para montar uma revisão acumulada.",
  "source": "user_scope"
}
```

Rules:
- unauthenticated returns `401`
- only prepared `material_type=study_material` items count as primary review materials
- `edital`, `bibliography`, `previous_exam`, `note`, `other`, and `unknown` do not count by default
- fewer than 3 prepared study materials and fewer than 3 available study blocks return `not_ready`
- 3 or more prepared study materials or study blocks can return `ready` or `needs_review`
- `basis=studied_materials` is reserved for a future Progress phase and is not used now
- repeated `GET` is idempotent and does not create review records, persist attempts, mark completion, mutate progress, generate simulados, call OCR, or call an LLM
- answer keys, gabarito, correct answers, correct alternatives, official correction fields, scores, progress payloads, attempt payloads, raw content, chunks, section bodies, storage paths, tokens, and internal traces are forbidden
- frontend proxy path is `GET /api/study/review/next`
- frontend API helper is `fetchNextReviewBlock()`
- frontend proxy forwards cookies server-side, uses the internal backend URL strategy, and whitelists response fields before returning data to the browser
- frontend wrapper treats `ready`, `needs_review`, and `partial` as successful bounded review candidates and maps `not_ready` to product-safe guidance

### `POST /api/study/progress/events`

Purpose:
- record explicit user-scoped study progress events
- keep progress mutation explicit and never automatic from page views
- persist only bounded event metadata
- not persist answer attempts as correction records
- not create studied/completed material state
- not expose answer keys, gabarito, scores, correction payloads, raw content, storage paths, or internal traces
- implemented in Progress-B as a backend-only contract; frontend proxy/UI remain pending

Request shape:

```json
{
  "event_type": "block_marked_studied",
  "target_type": "block",
  "target_id": "study-block:material:doc-1:0",
  "idempotency_key": "optional-stable-key"
}
```

Implemented response shape:

```json
{
  "event_id": "study-progress-event:...",
  "event_type": "block_marked_studied",
  "target_type": "block",
  "target_id": "study-block:material:doc-1:0",
  "created_at": "2026-06-09T12:00:00+00:00",
  "source": "user_scope"
}
```

Rules:
- unauthenticated returns `401`
- accepted event types are `block_opened`, `block_marked_studied`, `question_reviewed`, `review_opened`, and `review_completed`
- accepted target types are `block`, `question`, `review`, and `material`, but unsafe event/target combinations are rejected
- currently supported safe combinations are block events for `block`, question review events for `question`, and review events for `review`
- `block_opened` records low-confidence engagement and does not count as studied
- `block_marked_studied` increments studied block count only
- `question_reviewed` records review activity only; it does not store an answer, correctness, score, gabarito, or correction result
- `review_opened` and `review_completed` are explicit review events; they do not create score or official completion semantics
- repeated requests with the same `idempotency_key` for the same user return the original event and do not duplicate counts
- extra fields such as answer payloads, score, answer keys, or gabarito are rejected

### `GET /api/study/progress/summary`

Purpose:
- return a bounded user-scoped progress summary from explicit progress events plus existing prepared-material state
- keep material completion conservative until a future contract defines it
- keep review-after-3 prepared-material based until a frontend/progress phase explicitly moves it to studied materials

Implemented shape:

```json
{
  "progress_status": "ready",
  "opened_blocks_count": 1,
  "studied_blocks_count": 1,
  "prepared_materials_count": 3,
  "studied_materials_count": 0,
  "review_due": true,
  "review_basis": "prepared_materials",
  "reviewed_questions_count": 1,
  "weak_topics_count": 0,
  "source": "user_scope"
}
```

Rules:
- unauthenticated returns `401`
- `opened_blocks_count` comes only from explicit `block_opened` events
- `studied_blocks_count` comes only from explicit `block_marked_studied` events
- `reviewed_questions_count` comes only from explicit `question_reviewed` events
- `prepared_materials_count` is derived from owned prepared `material_type=study_material` files
- `studied_materials_count` remains `0` until material completion derivation is explicitly approved
- `review_due` may be based on prepared materials while studied-material semantics are still pending
- `weak_topics_count` remains `0` until persisted review/reinforcement signals are approved
- responses must not claim `progresso atualizado`, `você concluiu`, official `acertos/erros`, score, gabarito, or correction

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

### `GET /api/study/session/next`

Purpose:
- implemented minimal next-session guidance from prepared study materials
- later phases may extend this into edital-aware multi-material study blocks without progress mutation

See the implemented shape above.

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
