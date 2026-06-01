# Prepared Material Study Summary Contract Plan

## Purpose

Define the future contract for study summaries created from prepared `material_type=study_material` uploads.

This began as a planning document. StudySummary-B implemented the backend read-only endpoint, StudySummary-C added the frontend same-origin proxy/API wrapper, and StudySummary-D added a minimal read-only material-detail card. LLM calls, generated summaries, fixation questions, study sessions, progress mutation, simulado execution, OCR, PostgreSQL, auth provider work, and signup remain out of scope.

## Current Implementation Status

Implemented in StudySummary-B:

- backend `GET /api/materials/{document_id}/study/summary`
- authenticated and user-scoped
- restricted to `material_type=study_material`
- returns `not_ready` without mutation when the material has not been prepared
- returns bounded section-level items from prepared section metadata
- uses conservative placeholder text: `Resumo em preparação para esta seção.`
- derives key points from section titles/headings only

Implemented in StudySummary-C:

- frontend same-origin `GET /api/materials/[materialId]/study/summary`
- frontend `fetchStudyMaterialSummary(materialId)` API helper
- defensive proxy sanitization of top-level and item fields
- product-safe API result mapping for `not_ready`, auth, not found, invalid material type, offline, unsupported, and invalid response states

Implemented in StudySummary-D:

- minimal material-detail `Resumo do material` card for real `material_type=study_material`
- loading, ready, needs-review, not-ready, auth, not-found, offline, and invalid-type states
- compact rendering of section title, placeholder summary, key points, estimated minutes, and review status
- no visible UI for non-study materials

Pending:

- generated/review-only summary candidates
- fixation questions
- study session/cycle integration

## Product Objective

A prepared study material should become a safe study unit for the user.

The user-facing goal is to help the user answer:

- what should I read now?
- what is the concise summary of this material?
- what are the main points I need to retain?
- which fixation questions should I answer later?
- what should be reinforced if I miss a question?

The material summary layer should sit between raw preparation and later study sessions. It should transform prepared material structure into bounded, reviewable study guidance without exposing raw extraction artifacts.

## Prerequisites

A study summary can exist only when all of these are true:

- the user is authenticated
- the material belongs to the authenticated user
- the material has `material_type=study_material`
- the study preparation status is `ready_for_study` or `needs_review`
- safe extraction/preparation artifacts exist
- OCR is not required for the current material
- the response can be produced without exposing raw text, chunks, sections, storage paths, cookies, tokens, password hashes, answer keys, or gabarito

If the material is missing, non-owned, not a study material, OCR-required, or not prepared, the future summary surface should return a conservative unavailable/not-ready state.

## Proposed Future Endpoint

Implemented initial endpoint:

```http
GET /api/materials/{document_id}/study/summary
```

Why `GET` first:

- the first contract should be read-only and bounded
- it can return `not_ready` or `needs_review` without mutating progress
- it keeps summary display separate from generation or drafting
- it matches the existing protected read pattern for material, edital, and pipeline summaries

If a later generation step is needed, add a separate draft/review-only action:

```http
POST /api/materials/{document_id}/study/summary/draft
```

That future `POST` should be explicitly framed as candidate creation, not final truth. It should not mutate progress, unlock simulado, or expose raw source artifacts.

## Proposed Response Shape

Bounded response only:

```json
{
  "document_id": "doc-123",
  "summary_status": "ready",
  "material_type": "study_material",
  "title": "Noções de navegação",
  "sections_count": 2,
  "items": [
    {
      "section_id": "section-1",
      "title": "Conceitos principais",
      "summary": "Resumo curto e revisável da seção.",
      "key_points": ["Ponto principal 1", "Ponto principal 2"],
      "estimated_minutes": 8,
      "status": "ready"
    }
  ],
  "warnings_count": 0,
  "source": "user_scope"
}
```

Allowed top-level fields:

- `document_id`
- `summary_status`
- `material_type`
- `title`
- `sections_count`
- `items`
- `warnings_count`
- `source`

Allowed item fields:

- `section_id`
- `title`
- `summary`
- `key_points`
- `estimated_minutes`
- `status`

Recommended status values:

- `ready`
- `needs_review`
- `not_ready`
- `failed`

Forbidden fields:

- raw document text
- full extracted text
- raw chunk body
- raw section body
- OCR dump
- base64 payload
- storage path or local/private path
- owner internals
- cookie, token, session, or password hash
- answer key, gabarito, correctness, or correction payload
- internal worker/job/runtime traces

## Summary Strategy

### Stage 1: Deterministic Outline

Use prepared material structure to show a bounded outline and safe not-ready states.

Possible behavior:

- derive section titles from existing prepared sections
- show section counts and estimated reading time
- return `summary_status=not_ready` or item-level `needs_review` if no safe summary exists
- show copy such as `Resumo em preparação` instead of pretending generated content exists

Stage 1 should not use LLMs and should not expose raw chunks or extracted text.

### Stage 2: Review-Only Summary Candidates

If generated summaries are introduced later, they should be candidates.

Rules:

- generated text is reviewable and not final truth by default
- the UI should say `Resumo sugerido` or `Precisa de conferência` when appropriate
- source material linkage should be bounded by section/material ids, not raw excerpts
- no progress mutation should happen when a summary is generated or viewed

### Stage 3: Connected Study Loop

After summary candidates are safe, connect them to:

- fixation question candidates
- missed-question reinforcement
- cumulative review blocks after every 3 studied materials
- later study sessions ordered by edital scope

This stage should still keep answer keys and correction internals out of premature browser-facing surfaces.

## UI Principles

The user should see:

- `Resumo do material`
- `Pontos principais`
- `Estudar agora`
- `Ainda precisa de conferência`
- `Material preparado, ainda não conectado ao edital`
- `Resumo em preparação`

Avoid normal-user UI language such as:

- pipeline
- chunks
- metadata
- backend
- runtime
- generation internals
- confidence score
- audit terminology
- storage path
- extracted text

The UI should feel like a study surface, not an engineering dashboard.

## Relationship With Edital

The edital remains the official scope source.

Study material summaries should eventually be filtered, ordered, or grouped by edital topic/subtopic coverage:

- one material can cover multiple edital topics
- one section can map to one or more edital subtopics
- alignment can be unknown without blocking basic reading
- if alignment is missing, show `Material preparado, ainda não conectado ao edital`
- concrete personalized study order should wait for analyzed edital taxonomy and alignment readiness

Do not treat an uploaded `material_type=edital` as analyzed scope. Upload classification remains metadata only until bounded edital analysis says otherwise.

## Relationship With Questions

Fixation questions come later.

Future `FixationQuestions-A` should use:

- prepared material structure
- bounded study summary items
- edital topic/subtopic scope when available

Rules:

- question candidates are review-only first
- answer keys must not be exposed prematurely in answering surfaces
- explanations should be bounded and source-aware
- fixation questions are not simulados
- no progress mutation should happen until a separate explicit phase

## Review Rule

Record the product rule:

- after every 3 prepared/studied materials, create a cumulative review block
- the review block should include a concise cumulative summary
- the review block should include questions across those materials and related edital topics
- implementation is deferred until `ReviewBlock-A`

This rule should not be implemented implicitly through summary generation.

## Safety And Non-Goals

Do not add in this contract:

- automatic final-truth generation
- raw text exposure
- raw chunk or section bodies
- storage paths
- OCR expansion
- LLM generation without a review-only contract
- fixation question generation
- simulado generation or execution
- progress mutation
- scheduler/calendar behavior
- PostgreSQL migration
- external auth provider or signup

All future summary endpoints must remain authenticated, user-scoped, bounded, deterministic in shape, and safe for browser consumption.

## Recommended Implementation Sequence

1. `StudySummary-B`: backend read-only/draft contract for `GET /api/materials/{document_id}/study/summary`.
2. `StudySummary-C`: frontend same-origin proxy and API helper.
3. `StudySummary-D`: minimal material-detail UI card for `Resumo do material`.
4. `StudySummary-QA-A`: browser/API QA for the minimal read-only summary card.
5. `StudySession-A`: organize the first study screen from analyzed edital taxonomy plus prepared materials.
6. `FixationQuestions-Planning-A`: define question candidate boundaries, answer-key handling, and review language.
7. `FixationQuestions-A`: add bounded fixation question candidates.
8. `ErrorReinforcement-A`: map missed questions back to topic/subtopic reinforcement.
9. `ReviewBlock-A`: add the cumulative review rule after every 3 studied materials.
