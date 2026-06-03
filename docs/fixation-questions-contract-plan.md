# Review-only Fixation Questions Contract Plan

## Purpose

Define the first safe contract for fixation questions after a user studies a bounded study block.

This began as a planning document. FixationQuestions-B implemented the backend read-only endpoint `GET /api/study/blocks/{block_id}/questions` for deterministic review-only question candidates. It does not add frontend UI, question generation, answer correction, answer-key exposure, progress mutation, review-after-3 behavior, simulado execution, OCR, LLM calls, scheduler behavior, PostgreSQL, auth provider work, or signup.

## Product Objective

Fixation questions should help the student test understanding after studying one block.

The questions should be:

- tied to a study block
- based on the current user's prepared study material
- linked to edital topic/subtopic when safe
- useful later for error reinforcement
- useful later for cumulative review blocks
- possible input to simulados only after separate contracts exist

The first product surface should feel like cautious study support, not an official exam, final answer key, or scored activity.

## Initial Principle

Questions must start as one of these user-facing concepts:

- `questoes candidatas`
- `questoes para revisao`

They are not final, not official, not guaranteed, and should be presented cautiously until validation rules exist.

Recommended UI copy:

- `Questoes de fixacao`
- `Estas questoes ainda estao em revisao`
- `Revise com calma antes de tratar como definitivo`

Avoid implying:

- final truth
- official exam status
- scoring
- progress completion
- simulado execution

## Existing Context To Reuse

Study flow available today:

- `GET /api/study/blocks`
- `GET /api/study/blocks/{block_id}`
- `GET /api/materials/{document_id}/study/summary`
- `/study`
- `/study/blocks/[blockId]`

Useful bounded data available today:

- block title
- material id/title
- topic/subtopic labels when available
- prepared summary sections
- key points
- estimated minutes
- status values: `ready`, `needs_review`, `not_ready`

Existing simulado/question/correction/progress areas should not be reused as browser-facing fixation-question behavior yet. They include answer-key, correction, submission, and progress guardrail concepts that are intentionally later-stage and must stay separate until a dedicated answer/review contract exists.

## Implemented Backend Endpoint Strategy

First read endpoint:

```http
GET /api/study/blocks/{block_id}/questions
```

Why this endpoint first:

- the block already owns the study scope
- the backend owns user scope and block resolution
- the backend can decide whether the block is ready for question candidates
- the frontend should not infer questions from summary text
- a `GET` can return bounded candidates or `not_ready` without mutation

If question drafting/generation is needed later, use a separate explicit draft action:

```http
POST /api/study/blocks/{block_id}/questions/draft
```

The staged approach is:

1. Planning completed.
2. Backend read-only candidate contract implemented.
3. Frontend same-origin proxy/API helper pending.
4. Frontend review-only display pending.
5. Answer/correction contract later.
6. Progress mutation much later.

Do not make `GET /api/study/blocks/{block_id}` responsible for question generation or answer-key policy.

## Proposed Bounded Response Shape

```json
{
  "block_id": "study-block:topic-1:doc-123:0",
  "question_status": "ready",
  "mode": "review_only",
  "items": [
    {
      "question_id": "question:study-block:topic-1:doc-123:0:0",
      "type": "short_answer",
      "prompt": "Explique, com suas palavras, o ponto principal relacionado a Atos administrativos.",
      "alternatives": [],
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

Allowed top-level fields:

- `block_id`
- `question_status`
- `mode`
- `items`
- `warnings_count`
- `source`

Allowed item fields:

- `question_id`
- `type`
- `prompt`
- `alternatives`
- `topic_label`
- `subtopic_label`
- `difficulty`
- `status`

Allowed alternative fields:

- `id`
- `text`

Implemented and reserved status values:

- `question_status`: `ready`, `needs_review`, `not_ready`, `unsupported`
- `mode`: `review_only`
- `type`: `short_answer`; `true_false` and `multiple_choice` are reserved for later phases
- `difficulty`: `basic`, `medium`, `hard`
- item `status`: `candidate`, `needs_review`

Forbidden fields:

- answer key
- gabarito
- correct option
- correction result
- correctness flags
- hidden rationale
- final explanation
- raw edital text
- raw material text
- extracted text
- raw chunks
- section bodies
- OCR output
- base64 payload
- storage paths
- local/private paths
- cookies, tokens, session values, or password hashes
- progress mutation payloads
- worker/job/internal traces

## Answer Key Policy

Initial question display must not expose answer keys or gabarito by default.

Rules:

- answer keys stay server-side or absent until a correction/review contract exists
- browser-facing question candidates show prompt and alternatives only
- `correct_answer`, `answer_key`, `gabarito`, `is_correct`, and correction payloads are forbidden in the review-only response
- explanations that reveal the answer should wait until an answer/review phase
- progress must not be mutated when a question is viewed or answered in early phases

Possible future correction flow:

1. User answers a candidate question.
2. Backend compares only when a correction contract exists.
3. Answer key remains hidden until the correction/review phase.
4. Correction result can be shown only through a bounded response.
5. Progress mutation waits for an explicit progress phase.

## Question Source Policy

Questions may be derived from bounded study data:

- block title
- bounded section summary when a later phase makes that useful
- key points
- topic/subtopic labels
- material title when useful in a later phase
- exam profile style later

Questions must not be derived from frontend-visible raw data:

- raw hidden chunks exposed to frontend
- raw section bodies
- unsupported OCR output
- unrelated materials
- previous exams as content source unless a later phase allows it
- answer-key artifacts from simulado/correction services

The backend should own derivation. The frontend should render bounded question candidates only.

## Question Type Strategy

Start simple.

Implemented first option:

- `short_answer` prompt-only review candidates

Recommended future options:

- `true_false` for future CEBRASPE-style review
- `multiple_choice` for future FGV-style review

The current endpoint intentionally returns empty `alternatives` and no answer key.

The first implementation should likely choose one type or return a generic review-only model before attempting board-specific question behavior.

## Relationship With Study Block

A fixation question set belongs to one block.

Rules:

- block gives material/topic scope
- question candidates test that block only
- no questions if the block detail is `not_ready`
- `needs_review` blocks may produce only `needs_review` question candidates
- material-only blocks may produce material-only review questions, but copy must say they are not fully connected to edital scope
- connected edital blocks may include topic/subtopic labels when returned by the backend

The frontend should not compute question/block linkage from filenames, labels, or summary strings.

## Error Reinforcement Future

Future flow:

1. User answers a question.
2. Wrong answer is classified later.
3. The system suggests targeted reinforcement.

Possible error classifications:

- `content_gap`
- `interpretation`
- `attention`
- `confusion`
- `memorization`
- `unknown`

Possible reinforcement actions:

- short focused summary
- repeat a related question
- revisit the related block section
- review topic/subtopic explanation

No implementation exists in this phase. Error reinforcement must not mutate progress until a separate progress contract exists.

## Review After 3 Materials Future

Product rule:

- after every 3 studied or prepared materials, create a cumulative review
- review includes a short cumulative summary
- review includes fixation question candidates
- later, review should use wrong answers and weak topics

Implementation remains deferred.

Recommended later review object:

- `review_block_id`
- `material_ids`
- `topic_labels`
- `summary_status`
- `question_status`
- `items_count`
- `source`

The frontend should not calculate the "every 3 materials" rule. The backend should own review grouping once progress/completion semantics exist.

## UI Principles

Future UI should show:

- `Questoes de fixacao`
- `Responder`
- `Revisar ponto fraco`
- `Estas questoes ainda estao em revisao`
- `Voltar ao bloco`

Future UI should avoid:

- gabarito before answer/correction phase
- answer keys before review
- internal terms
- confidence scores
- backend/pipeline/chunk wording
- progress mutation copy
- final score language
- simulado language

The UI should present questions as study support, not as an official assessment.

## Relationship With Existing Simulado/Question Areas

Existing simulado services and tests include foundations for question assembly, answer-key boundaries, answer submission, correction shells, execution approval, and progress guardrails.

Those areas are useful as safety references, especially:

- answer-key public exposure must remain forbidden
- correction requires a separate contract
- progress mutation requires separate explicit approval
- simulado execution is not the same as fixation review

They should not be surfaced as fixation-question UI or reused directly for block questions until a dedicated bounded contract connects them safely.

## Non-goals

- No frontend UI in this phase.
- No generated questions.
- No official/final questions.
- No final answer keys.
- No gabarito.
- No correction result.
- No hidden rationale.
- No answer submission.
- No progress mutation.
- No error reinforcement implementation.
- No review-after-3 implementation.
- No simulado generation or execution.
- No LLM behavior.
- No OCR expansion.
- No scheduler/calendar behavior.
- No PostgreSQL work.
- No external auth provider.
- No signup UI.

## Recommended Future Phases

1. `FixationQuestions-C`: frontend same-origin proxy/API helper.
2. `FixationQuestions-D`: minimal review-only questions UI on block detail.
3. `FixationQuestions-QA-A`: browser/API QA and no-leakage validation.
4. `AnswerReview-Planning-A`: answer submission, correction, and answer-key reveal boundaries.
5. `ErrorReinforcement-Planning-A`: wrong-answer classification and reinforcement contract.
6. `ReviewBlock-Planning-A`: cumulative review after every 3 studied/prepared materials.

## Open Questions

- Should future generated fixation questions replace or complement the deterministic review-only prompts?
- Should `GET /api/study/blocks/{block_id}/questions` continue deriving candidates on demand, or read previously drafted candidates once a draft contract exists?
- Should material-only blocks allow questions before edital connection, or return `needs_review` until topic scope exists?
- Which first type is safest: `true_false`, `multiple_choice`, or a generic prompt-only review item?
- When answer review exists, should explanations reveal the answer immediately after a response or only after explicit review?
