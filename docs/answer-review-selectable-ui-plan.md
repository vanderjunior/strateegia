# Selectable Answer Review UI Plan

## Purpose

Document the first visible answer-review UI for objective fixation-question candidates.

This began as a planning document. AnswerReview-D implemented the minimal selectable UI on `/study/blocks/[blockId]` for objective candidates. It does not add answer keys, gabarito, official correction, score, persistence, progress mutation, simulado behavior, OCR, LLM calls, scheduler behavior, PostgreSQL, auth provider work, or signup.

## Product Objective

Let the student answer objective fixation questions by selecting an option and receiving conservative study feedback.

Supported objective formats:

- PSCPP/default objective mode: `multiple_choice` with A-E alternatives
- future configured objective mode: `multiple_choice` with A-D alternatives
- CEBRASPE-style mode: `true_false` with `Certo` / `Errado`

The UI should ask for a selection and call the existing stateless answer-review helper. It must not present feedback as official correction.

## Current State

Implemented today:

- `GET /api/study/blocks/{block_id}/questions` returns review-only question candidates.
- Default/PSCPP-style candidates prefer `multiple_choice` A-E when bounded labels are available.
- A-D multiple choice is supported through the future profile hook.
- CEBRASPE-style candidates can use `true_false` C/E.
- `short_answer` remains fallback only.
- `/study/blocks/[blockId]` displays questions and alternatives.
- `multiple_choice` and `true_false` questions now support local radio selection and `Revisar escolha`.
- `short_answer` remains non-interactive in this UI phase.
- `POST /api/study/blocks/{block_id}/questions/{question_id}/answer/review` exists as a stateless backend review endpoint.
- Frontend same-origin answer-review proxy and `reviewStudyBlockQuestionAnswer(blockId, questionId, payload)` exist.

Current boundaries:

- visible answer review exists only for objective candidates
- no answer attempt is persisted
- no score is created
- no progress is mutated
- no answer key, gabarito, correct alternative, official correction, or correctness flag is exposed

## UI Model

### Multiple Choice

For `type="multiple_choice"`:

- render one radio group per question
- render options from `alternatives` exactly as returned by the backend
- support A-E or A-D by reading the returned alternative ids
- make option labels clickable
- allow one selected option per question
- button label: `Revisar escolha`

Example labels:

- `A. Revisar Atos administrativos.`
- `B. Relacionar Atos administrativos ao resumo do bloco.`

### True/False

For `type="true_false"`:

- render one radio group per question
- render `C. Certo`
- render `E. Errado`
- allow one selected option per question
- button label: `Revisar escolha`

### Short Answer Fallback

For `type="short_answer"` in the first selectable UI phase:

- keep the question display-only, or
- show `Revisão interativa ainda não disponível para este tipo de questão.`

Do not add a textarea in the first selectable UI phase unless a separate phase explicitly approves short-answer interaction.

## API Mapping

Use the existing helper:

```ts
reviewStudyBlockQuestionAnswer(blockId, questionId, payload)
```

For `multiple_choice`:

```json
{
  "answer": "A",
  "answer_format": "choice"
}
```

For `true_false`:

```json
{
  "answer": "C",
  "answer_format": "true_false"
}
```

Rules:

- `answer` is the selected alternative id, not the full option text
- do not send topic labels, hidden context, answer keys, correctness flags, score, or progress payloads
- do not reconstruct question ids or alternatives on the frontend
- call the helper only for question ids returned by the current bounded questions payload

## Feedback Model

After a successful review response, show:

- heading: `Feedback`
- backend `feedback`
- backend reinforcement `message`
- a product-safe label for `suggested_action`

Suggested action labels:

- `review_summary`: `Revisar resumo`
- `retry_question`: `Tentar novamente`
- `revisit_block`: `Revisitar bloco`

Result copy:

- `result="ungraded"`: `Escolha revisada sem pontuação.`
- `result="needs_review"` or `review_status="needs_review"`: `Esta escolha precisa de conferência.`

Always show this caution near the feedback:

```text
Este feedback é uma orientação de estudo, não uma correção oficial.
```

## No-Gabarito Policy

The selectable answer UI must not show:

- `gabarito`
- `resposta correta`
- `alternativa correta`
- `answer_key`
- `correct_answer`
- `correct_alternative`
- `is_correct`
- correctness flags
- score
- pontuação
- acertos/erros
- official correction

Even after review, the UI should not claim official correctness. Current answer review may say that a selection needs review or provide conservative guidance, but it must not reveal or imply an official answer.

## Validation States

User-facing states:

- no option selected: `Selecione uma alternativa antes de revisar.`
- auth required: `Entre para revisar sua escolha.`
- not found: `Questão ou bloco de estudo não encontrado.`
- validation error: `Revise sua escolha antes de enviar.`
- backend offline, missing config, or unsupported: `Não foi possível revisar sua escolha agora.`

State behavior:

- keep the selected option visible after submission
- keep feedback close to the question that was reviewed
- do not hide the study block summary
- do not block the user from returning to `/study`

## Accessibility And UX

Future UI should:

- use semantic radio groups
- associate each radio input with a visible label
- make labels clickable
- keep one selected option per question
- expose a clear disabled state while submitting
- keep feedback near the reviewed question
- avoid visual noise and repeated status cards
- keep questions secondary to the study block summary
- preserve keyboard navigation through options and the review button

## Safety And Non-goals

Do not add:

- official correction
- answer-key reveal
- gabarito
- correct alternative exposure
- score
- progress mutation
- answer attempt persistence
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

## Recommended Next Phase

`AnswerReview-QA-A`: browser/API QA for selectable answer review on block detail.

QA scope:

- login and open a prepared study block
- select A-E or C/E when available
- click `Revisar escolha`
- confirm conservative feedback and reinforcement render
- confirm no gabarito, correct alternative, score, official correction, persistence, or progress mutation appears
