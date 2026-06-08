# Weak Point Reinforcement Contract Plan

## Purpose

Define the future contract for reinforcing weak points after a student reviews an answer on a study block.

This began as a planning document. ErrorReinforcement-D refined the existing block-detail answer-review UI to render the current answer-review `reinforcement` object more clearly as `Reforço sugerido`. It does not add endpoints, error classification, attempt persistence, progress mutation, answer-key exposure, scoring, simulado behavior, OCR, LLM calls, scheduler behavior, PostgreSQL, auth provider work, or signup.

## Product Objective

Weak point reinforcement should help the student know what to review after a weak answer, uncertain review, or needs-review response.

It should help the student:

- return to the relevant block summary
- focus on the related key points
- understand the topic or subtopic when available
- receive a concrete next study action
- later feed cumulative review blocks
- later support progress-aware adaptation

The first implementation must remain conservative:

- review-only or stateless
- no official error judgment
- no answer-key reveal
- no score
- no progress mutation

## Current State

Available today:

- `/study` renders bounded study blocks.
- `/study/blocks/[blockId]` renders bounded block detail, summary sections, key points, and fixation-question candidates.
- Fixation candidates prefer objective/selectable formats when safe: A-E/A-D multiple choice or C/E true/false.
- The user can select an objective alternative and click `Revisar escolha`.
- Backend `POST /api/study/blocks/{block_id}/questions/{question_id}/answer/review` returns bounded stateless feedback.
- Frontend same-origin answer-review proxy/API helper and minimal selectable UI exist.
- Block detail now separates the post-review hierarchy into `Feedback`, `Reforço sugerido`, and caution copy.
- ErrorReinforcement-QA-A closed this refined UI through Compose/API QA: authenticated answer review returned bounded conservative feedback plus reinforcement, browser unauthenticated access showed the expected auth-required state, and no answer key, gabarito, score, progress, raw content, or internal trace was exposed.
- Answer review may return `review_status=reviewed` or `needs_review`.
- Answer review may return `result=ungraded` or `needs_review`.
- Answer review may return a minimal `reinforcement` object:
  - `topic_label`
  - `subtopic_label`
  - `message`
  - `suggested_action`

Current boundaries:

- no official correctness
- no gabarito
- no correct alternative
- no answer key
- no score
- no persisted attempt history
- no progress mutation
- no formal weakness classification

## Proposed Staged Approach

### Stage 1: Use Existing Answer-Review Reinforcement

Use the existing answer-review response only.

Behavior:

- display the returned reinforcement message near the reviewed question
- map `suggested_action` to a product-safe label
- point the user back to the summary, question retry, or block revisit
- keep everything stateless
- do not persist attempts
- do not classify real errors
- do not mutate progress

This stage is represented by the current block-detail feedback panel. The UI renders the reinforcement message, topic/subtopic labels when present, a safe suggested-action label, and fallback guidance if the reinforcement message is empty.

### Stage 2: Optional Read-only Reinforcement Draft Contract

Add a backend-owned reinforcement read/draft only if the existing answer-review response becomes too small for the UI.

Possible endpoint options:

```http
GET /api/study/blocks/{block_id}/reinforcement?question_id=...
```

or:

```http
POST /api/study/blocks/{block_id}/questions/{question_id}/reinforcement/draft
```

Rules:

- user-scoped
- bounded response only
- no attempt persistence
- no progress mutation
- no answer-key reveal
- no official correction
- no score

Use `POST .../draft` only if the future request needs a selected answer or review context. Use `GET` only if the reinforcement can be derived from existing backend-owned block/question/review state without accepting answer input.

### Stage 3: Conservative Weakness Categories

Add bounded weakness categories only when a deterministic signal exists.

Rules:

- default to `not_classified` or `needs_review`
- avoid claiming the student definitively got something wrong
- avoid official correction language
- keep category labels product-oriented and non-shaming

### Stage 4: Connect To Review Blocks

Use reinforcement history as input to cumulative review after every 3 studied/prepared materials.

Inputs may include:

- studied blocks
- reviewed answers
- weak topics
- reinforcement history

This remains planning only. Do not implement review-after-3 behavior in this phase.

### Stage 5: Explicit Future Progress Phase

Only a later Progress phase may persist attempts or mutate progress.

That future phase must define:

- idempotency
- rollback
- auditability
- user scope
- privacy/no-leakage rules
- what counts as progress
- whether review feedback can affect progress

## Reinforcement Categories

Future weakness categories:

- `content_gap`
- `interpretation`
- `attention`
- `confusion`
- `memorization`
- `not_classified`

Product meanings:

- `content_gap`: the student likely did not know the concept yet.
- `interpretation`: the student may have misunderstood the wording or command.
- `attention`: the student may have missed a relevant detail.
- `confusion`: the student may have mixed similar concepts.
- `memorization`: the student likely needs recall practice for a definition, list, formula, or rule.
- `not_classified`: there is not enough safe signal to classify the weakness.

Initial behavior should prefer:

- `not_classified`
- `needs_review`

Only use a stronger category when the backend has a deterministic, bounded, review-safe signal.

## Proposed Future Response Shape

```json
{
  "block_id": "string",
  "question_id": "string|null",
  "reinforcement_status": "ready",
  "weakness_type": "not_classified",
  "topic_label": "string|null",
  "subtopic_label": "string|null",
  "title": "Revise este ponto",
  "message": "Volte ao resumo do bloco e revise os pontos principais.",
  "suggested_actions": [
    {
      "type": "review_summary",
      "label": "Revisar resumo",
      "href": "/study/blocks/<block_id>"
    }
  ],
  "source": "user_scope"
}
```

Allowed `reinforcement_status` values:

- `ready`
- `needs_review`
- `not_ready`

Allowed `weakness_type` values:

- `content_gap`
- `interpretation`
- `attention`
- `confusion`
- `memorization`
- `not_classified`

Allowed suggested action types:

- `review_summary`
- `retry_question`
- `revisit_block`
- `study_key_points`

Forbidden fields:

- raw material text
- raw edital text
- extracted text
- raw chunks
- raw section bodies
- evidence snippets
- hidden rationale
- storage paths
- local/private paths
- token, cookie, session, or password values
- answer key
- gabarito
- correct answer
- correct alternative
- correctness flag
- official correction result
- score
- progress mutation payload
- simulado execution payload
- worker/job/internal traces

## Relationship With Answer Review

Answer review already returns a minimal reinforcement object.

Current fields:

- `topic_label`
- `subtopic_label`
- `message`
- `suggested_action`

Future reinforcement should build from this instead of replacing it.

Rules:

- answer review remains the first source of immediate feedback
- reinforcement can enrich that feedback only with bounded, user-scoped guidance
- a future reinforcement endpoint should not reclassify answers as officially correct or incorrect unless a separate answer-key/correction policy is approved
- the frontend should not infer weakness categories from answer text or selected alternative ids

## Relationship With Study Blocks

Reinforcement belongs to the current study block.

It should point back to:

- block summary
- key points
- topic label
- subtopic label
- question candidate

It should not:

- jump to unrelated materials
- reconstruct block-topic matching on the frontend
- expose raw source evidence
- imply the material has been fully mastered or failed

The backend should own any future mapping from question review to topic/subtopic reinforcement.

## Relationship With Review After 3 Materials

Product rule:

After every 3 studied/prepared materials, the product should eventually produce a cumulative review block.

That review block should use:

- studied blocks
- reviewed answers
- weak topics
- reinforcement history
- bounded summaries and key points

This phase does not implement that behavior.

Review-after-3 remains a future contract because it needs explicit definitions for:

- what counts as a studied material
- whether viewing a block counts
- whether reviewing an answer counts
- how to handle material-only blocks not connected to edital
- whether progress must be persisted

## UI Principles

Future UI should use simple study language:

- `Reforço sugerido`
- `Revise este ponto`
- `Voltar ao resumo`
- `Revisar pontos principais`
- `Tentar questão parecida` later

Avoid:

- `Você errou` as an official judgment in early phases
- `gabarito`
- `resposta correta`
- `alternativa correta`
- `score`
- `pontuação`
- ranking language
- official correction language
- backend, pipeline, chunk, metadata, or internal terms

The reinforcement should stay near the reviewed question and remain secondary to the block summary.

## Safety And Non-goals

Do not add:

- official correction
- answer-key reveal
- gabarito
- correct alternative exposure
- scoring
- progress mutation
- persisted attempt history
- review-after-3 implementation
- simulado execution
- generated question expansion
- OCR or LLM behavior
- scheduler behavior
- PostgreSQL work
- external auth provider
- signup UI

Do not expose:

- raw material text
- raw edital text
- raw chunks or section bodies
- storage paths
- tokens, cookies, session values, or password hashes
- hidden rationale or internal traces

## Recommended Future Phases

Recommended sequence:

1. `ErrorReinforcement-B`: backend read-only or draft endpoint only if the existing answer-review reinforcement field is insufficient.
2. `ErrorReinforcement-C`: frontend same-origin proxy/API wrapper, if a new endpoint is introduced.
3. `ErrorReinforcement-D`: minimal reinforcement card after answer review.
4. `ErrorReinforcement-QA-A`: browser/API QA.
5. `ReviewBlock-Planning-A`: define cumulative review after every 3 materials.

Alternative if the current answer-review reinforcement field remains sufficient:

1. `ErrorReinforcement-D`: UI-only refinement using the existing answer-review response.
2. `ErrorReinforcement-QA-A`.
3. `ReviewBlock-Planning-A`.
