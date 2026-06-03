# Answer Submission and Review Contract Plan

## Purpose

Define the contract for answering fixation questions and receiving safe review feedback after studying one block.

This began as a planning document. AnswerReview-B implemented the backend stateless endpoint `POST /api/study/blocks/{block_id}/questions/{question_id}/answer/review`. AnswerReview-C added the frontend same-origin proxy/API helper. It does not add visible answer UI behavior, answer-key exposure, scoring, persistence, progress mutation, error reinforcement, review-after-3 behavior, simulado execution, OCR, LLM calls, scheduler behavior, PostgreSQL, auth provider work, or signup.

## Product Objective

Answer review should help the student:

- answer one fixation question after studying a block
- receive safe feedback about what to revisit
- understand the topic or subtopic that needs reinforcement
- later connect weak answers to targeted reinforcement
- later feed cumulative review after every 3 studied/prepared materials

The first answer-review surface should feel like a guided study checkpoint, not a scored exam, official gabarito, or progress-completion event.

## Current State

Implemented today:

- `/study` shows bounded study blocks.
- `/study/blocks/[blockId]` shows one bounded block detail.
- `GET /api/study/blocks/{block_id}/questions` returns deterministic review-only fixation question candidates.
- Frontend same-origin `GET /api/study/blocks/[blockId]/questions` and `fetchStudyBlockQuestions(blockId)` render the `Questões de fixação` card.
- Backend `POST /api/study/blocks/{block_id}/questions/{question_id}/answer/review` returns conservative bounded feedback for one submitted answer.
- Frontend same-origin `POST /api/study/blocks/[blockId]/questions/[questionId]/answer/review` and `reviewStudyBlockQuestionAnswer(blockId, questionId, payload)` exist.

Current boundaries:

- questions are candidates/review-only
- no frontend answer input exists
- no gabarito or answer key is shown
- short-answer review is conservative and ungraded
- no score is created
- no answer attempt is persisted
- no progress is mutated
- no simulado execution is enabled
- no OCR or LLM behavior is triggered

Existing older answer and simulado/correction/progress areas should not be reused directly for this user-facing block flow. They include recording, correction, answer-key, scoring, and progress concepts that are intentionally later-stage and must stay behind explicit contracts.

## Proposed Staged Approach

### Stage 1: Local Answer Draft UI Only

Future frontend-only phase:

- show an answer input for one candidate question
- allow the user to draft an answer locally
- do not persist the answer
- do not correct the answer
- do not show gabarito
- do not mutate progress

This can validate UX copy such as `Sua resposta` without adding backend semantics.

### Stage 2: Backend Answer Review, No Progress Mutation

Backend portion implemented in AnswerReview-B:

- add a scoped answer-review endpoint
- validate that the question belongs to the block
- accept a bounded text/choice answer
- return bounded feedback
- do not persist scores
- do not mutate progress
- do not reveal answer keys by default

Visible answer UI remains pending.

### Stage 3: Error Classification and Reinforcement Suggestion

Future pedagogical phase:

- classify weak answers into safe categories
- map the weakness back to topic/subtopic when available
- suggest revisiting the block summary or retrying a related question
- keep the output advisory until a stronger correction contract exists

### Stage 4: Explicit Progress Phase

Future mutation phase:

- persist answer attempts only after explicit approval
- update progress only after a separate progress contract
- define idempotency, rollback, audit, and no-leakage rules

## Implemented Backend Endpoint

```http
POST /api/study/blocks/{block_id}/questions/{question_id}/answer/review
```

Why this is preferred:

- the block owns the study scope
- the backend owns authenticated user scope
- the backend can resolve the block and validate material ownership
- the backend can validate that the question belongs to that block
- the endpoint name makes the first behavior review-only, not scoring or progress
- it avoids treating question ids as globally sufficient without block context

Alternative endpoint:

```http
POST /api/study/questions/{question_id}/answer/review
```

Why it is less suitable initially:

- it makes the question id carry too much scope
- it increases the risk of frontend-only block/question reconstruction
- it is less explicit about the block currently being studied

## Implemented Request Shape

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

Rules:

- require authentication
- enforce user scope through block ownership
- validate that `question_id` belongs to `block_id`
- require non-empty answer text/value
- bound answer length before processing
- do not accept file uploads
- do not accept raw hidden context
- do not accept client-submitted answer keys
- do not accept client-submitted correctness flags
- do not accept progress targets or score payloads

## Implemented Response Shape

```json
{
  "block_id": "study-block:material:doc-123:0",
  "question_id": "question:study-block:material:doc-123:0:0",
  "review_status": "reviewed",
  "result": "ungraded",
  "feedback": "Revise os pontos principais do bloco antes de avançar.",
  "reinforcement": {
    "topic_label": "Direito Administrativo",
    "subtopic_label": "Atos administrativos",
    "message": "Volte ao resumo deste bloco e destaque os atributos principais.",
    "suggested_action": "review_summary"
  },
  "source": "user_scope"
}
```

Allowed top-level fields:

- `block_id`
- `question_id`
- `review_status`
- `result`
- `feedback`
- `reinforcement`
- `source`

Allowed `review_status` values:

- `reviewed`
- `needs_review`
- `not_ready`
- `unsupported`

Allowed `result` values:

- `correct`
- `incorrect`
- `partial`
- `ungraded`
- `needs_review`

Allowed reinforcement fields:

- `topic_label`
- `subtopic_label`
- `message`
- `suggested_action`

Allowed `suggested_action` values:

- `review_summary`
- `retry_question`
- `revisit_block`

Forbidden response fields:

- answer key
- gabarito
- correct answer
- correct alternative
- hidden rationale
- internal traces
- raw material text
- raw edital text
- extracted text
- raw chunks
- raw section bodies
- OCR output
- storage paths
- cookies, tokens, session values, or password hashes
- score records
- progress mutation payloads
- simulado execution payloads

## Answer Key Policy

Current fixation question display and stateless answer review continue not exposing answer keys or gabarito.

Conservative future policy:

- answer review may return feedback without revealing an official answer
- short-answer questions may return `ungraded` or `needs_review` until reliable correction exists
- multiple-choice and true/false gabarito reveal must be deliberate and bounded
- no answer key should be included in frontend payloads unless the endpoint explicitly returns reviewed feedback under a later answer-key reveal contract
- answer-key values must never be accepted from the client as correction evidence
- hidden rationale and internal support traces must not be browser-facing

## Correction Policy

Initial correction should be conservative.

Rules:

- short-answer responses should not be auto-graded unless a later reliable correction contract exists
- feedback can guide review without declaring correctness
- deterministic correction is allowed only where safe, such as strictly bounded `choice` or `true_false` questions with backend-owned review rules
- no LLM-based grading should be added without a later reviewed and guardrailed contract
- do not create score records in the first answer-review implementation
- do not mutate progress from answer review

Recommended early behavior:

- `short_answer`: usually `ungraded` or `needs_review`
- `choice`: may become `correct` / `incorrect` only after backend-owned answer-key policy is explicitly approved
- `true_false`: may become `correct` / `incorrect` only after backend-owned answer-key policy is explicitly approved

## Error Classification Future

Future error categories:

- `content_gap`
- `interpretation`
- `attention`
- `confusion`
- `memorization`

Rules:

- classification should be advisory before progress mutation exists
- classification should map back to topic/subtopic when available
- classification should not expose hidden answer keys or internal rationale
- classification should not create durable progress records until an explicit progress phase

## Reinforcement Future

Wrong, weak, or ungraded answers should later trigger:

- short focused explanation
- revisit block summary
- retry related question
- mark weak topic for a future review block

Initial reinforcement should be phrased as guidance:

- `Revise este ponto`
- `Volte ao resumo do bloco`
- `Tente uma pergunta parecida depois`

Do not implement automatic scheduling, progress updates, or review-block creation in the answer-review phase.

## Review After 3 Materials

Product rule:

- after every 3 studied/prepared materials, the app should later create a cumulative review

Future cumulative review should use:

- studied blocks
- answered questions
- weak topics
- error classifications
- prepared material summaries

This is not implemented in answer review. It should be planned in a separate `ReviewBlock` phase after answer attempts and error classifications have a safe contract.

## UI Principles

Future UI can show:

- `Sua resposta`
- `Revisar resposta`
- `Feedback`
- `Revisar este ponto`
- `Voltar ao resumo`
- `Tentar novamente`

Future UI should avoid:

- gabarito before review
- score-first presentation
- ranking
- exam/simulado framing
- internal/backend/pipeline terms
- hidden correction rationale
- progress mutation copy before an explicit progress phase
- `Concluir estudo` unless completion tracking exists

## Relationship With Existing Endpoints

### `GET /api/study/blocks/{block_id}/questions`

Purpose:

- display bounded review-only candidates
- no answer input
- no answer keys
- no correction
- no progress mutation

### `POST /api/study/blocks/{block_id}/questions/{question_id}/answer/review`

Purpose:

- review one submitted answer
- return bounded feedback
- optionally suggest reinforcement
- stateless and idempotent for the same input
- no progress mutation in the first implementation
- frontend proxy path is `POST /api/study/blocks/[blockId]/questions/[questionId]/answer/review`
- frontend API helper is `reviewStudyBlockQuestionAnswer(blockId, questionId, payload)`
- frontend proxy/API sanitize request and response fields by whitelist

### Existing legacy answer endpoints

Existing endpoints such as `/api/questions/{question_id}/answer` and `/api/answers/submit` should not become the browser-facing study-block answer contract without a separate audit. They record answers/correctness-like data and do not currently model the bounded block/question review policy described here.

### Existing simulado/correction/progress services

Existing simulado answer submission, correction, scoring, answer-key boundary, and progress guardrail areas are not the initial fixation answer-review surface. They may inform future safety patterns, but they are broader and more execution-oriented than the study-block review flow.

## Non-Goals

No:

- frontend answer input in this planning phase
- answer key exposure by default
- gabarito exposure
- correction implementation
- score persistence
- progress mutation
- error reinforcement implementation
- review-after-3 implementation
- generated questions
- LLM grading
- simulado execution
- OCR expansion
- scheduler
- PostgreSQL
- auth provider
- signup UI

## Recommended Future Phases

1. `AnswerReview-D`: minimal answer/review UI on block detail.
2. `AnswerReview-QA-A`: browser/API QA for answer review boundaries.
3. `ErrorReinforcement-Planning-A`: define weak-topic reinforcement contract.
4. `ReviewBlock-Planning-A`: define cumulative review after every 3 materials.

## Safety Checklist For Implementation

Before implementing answer review, confirm:

- `401` unauthenticated
- `404` missing/non-owner block or question
- question belongs to block
- answer input is bounded
- response shape is whitelisted
- no raw content or storage path exposure
- no answer key or gabarito exposure unless explicitly approved
- no correction result beyond bounded review
- no score record
- no progress mutation
- no simulado execution
- frontend copy stays study-oriented, not exam/scoring-oriented
