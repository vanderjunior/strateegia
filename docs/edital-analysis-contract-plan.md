# Controlled Edital Analysis Contract Plan

## Purpose

Track the controlled edital analysis execution contract.

The backend controlled endpoint, frontend proxy/API wrapper, and minimal material-detail UI action are implemented. This contract does not add dashboard-wide buttons, automatic analysis on upload, OCR, generation, simulado execution, progress mutation, scheduler behavior, PostgreSQL, or auth-provider behavior.

## Current State

- `material_type=edital` means an edital file was uploaded and classified by the user.
- An uploaded edital is not the same as an analyzed edital.
- Bounded protected reads already expose:
  - `GET /api/materials`
  - `GET /api/editais`
  - `GET /api/materials/{document_id}/summary`
  - `GET /api/editais/{edital_id}/summary`
  - `GET /api/materials/{document_id}/pipeline/summary`
- Frontend lifecycle state distinguishes:
  - `no_edital_uploaded`
  - `edital_uploaded_not_analyzed`
  - `edital_analyzed`
  - `analysis_needs_review`
  - `analysis_unavailable`
- Concrete study, PSCPP personalization, ciclo, questões, simulados, and execução remain gated until a real analyzed edital exists and later capability-specific contracts are added.
- Existing backend edital ingestion services can derive candidate topics, bibliography, exclusions, weights, and warnings from existing pipeline artifacts, but current broad ingestion reads are not the intended browser-facing product contract.

## Implemented Backend Endpoint

Implemented endpoint:

```http
POST /api/materials/{document_id}/edital/analyze
```

Rationale:

- The action starts from a user-owned uploaded material, not from an existing edital record.
- It aligns with the existing material-owned edital route family: `/api/materials/{document_id}/edital/...`.
- It can enforce `material_type=edital` before analysis.
- It avoids implying that an `edital_id` already exists before controlled analysis has created one.
- It gives the frontend a narrow, bounded product endpoint instead of using broad ingestion/extraction routes.

Alternative considered:

```http
POST /api/editais/{document_id}/analyze
```

This is less precise because `document_id` is a material identifier, not an edital identifier. Use it only if a later API naming pass intentionally moves all edital lifecycle actions under `/api/editais`.

## Preconditions

The implemented endpoint requires:

- Authenticated user; unauthenticated requests return `401`.
- `document_id` must exist inside the current user's `JsonStudyRepository.for_user(user_id)` scope.
- Missing or non-owner material returns `404` without revealing ownership.
- Uploaded material metadata must have `material_type=edital`.
- Non-edital material should return `422` with a bounded validation error, or `400` if the backend's existing validation style prefers it.
- The document must have extracted text or a safe text representation already available from existing pipeline artifacts.
- Scanned or OCR-required material should return a bounded `not_ready` status, not attempt OCR.
- The frontend must not send raw edital text in the request.
- The endpoint should be idempotent for a final analyzed/not-ready state unless a later explicit reanalysis contract is approved.

## Request Shape

The implemented backend endpoint requires no request body:

```http
POST /api/materials/{document_id}/edital/analyze
```

If a later client contract needs explicitness, it may add a minimal optional body:

```json
{
  "mode": "controlled"
}
```

Do not accept:

- raw edital text
- OCR payloads
- base64 content
- storage paths
- answer keys or correction artifacts
- options that trigger generation, simulado, scheduler, or progress mutation

## Implemented Bounded Response Shape

Return only bounded lifecycle metadata:

```json
{
  "edital_id": "edital:doc-123",
  "document_id": "doc-123",
  "analysis_status": "analyzed",
  "review_state": "ready_for_review",
  "topics_count": 12,
  "bibliography_count": 8,
  "gaps_count": 0,
  "warnings_count": 1,
  "source": "user_scope"
}
```

Allowed `analysis_status` values:

- `analyzed`
- `needs_review`
- `failed`
- `not_ready`

Allowed `review_state` values:

- `ready_for_review`
- `needs_review`
- `pending`
- `unknown`

Forbidden response fields:

- raw edital text
- raw document text
- `extracted_text`
- OCR dump
- raw chunks or sections
- bibliography evidence excerpts
- raw topic excerpts
- base64 payloads
- `storage_path`
- local absolute paths
- owner internals
- cookies, tokens, password hashes
- answer key, gabarito, correctness, correction fields
- worker, job, runtime, or internal trace payloads

## Lifecycle Transitions

Recommended lifecycle mapping:

- `uploaded_not_analyzed` -> internal `analysis_pending` while controlled analysis starts.
- `analysis_pending` -> `not_ready` when text is missing, too short, OCR-required, or otherwise unsafe to analyze.
- `analysis_pending` -> `analyzed` when bounded candidate metadata is created and ready enough for review.
- `analysis_pending` -> `needs_review` when candidate metadata exists but warnings, partial extraction, or alignment uncertainty should keep the product conservative.
- `analysis_pending` -> `failed` when controlled analysis cannot complete due to a safe, product-facing failure.

Unlock rule:

- Concrete study guidance may unlock only after `analysis_status=analyzed` and `review_state=ready_for_review`.
- `needs_review`, `not_ready`, `failed`, `unknown`, and unavailable states must keep study, PSCPP personalization, ciclo, questões, simulados, and execução conservative or gated.

OCR rule:

- OCR-required material returns `not_ready`.
- This contract must not implement OCR or promise scanned PDF support.

## Current Readiness Criteria

Current controlled analysis can prepare safe textual artifacts internally when needed:

- Uploading `.txt` or `.md` stores text on the uploaded material record.
- When controlled analysis starts and no persisted `DocumentExtractionResult` exists, the backend runs a no-OCR deterministic preparation helper for `.txt`, `.md`, and textual `.pdf` materials.
- Textual PDFs use deterministic embedded-text extraction only. If useful text is present, the helper persists extraction, chunks, sections, and pipeline metadata through the existing bounded finalizer.
- Users do not need a separate visible `Processar` step before `Analisar edital` for textual materials.
- Scanned PDFs, OCR-required files, unsupported files, missing extraction, or text shorter than the ingestion threshold remain `not_ready`.
- Controlled analysis never triggers OCR. OCR-required PDFs are marked pending/not-ready for later explicit OCR-capable flows.
- Plain unstructured text such as `Conteúdo programático: Português, Informática...` can be prepared safely, but it returns `needs_review` when no top-level topic candidates are recognized.

The current deterministic analyzer recognizes topics when both conditions are true:

- Pipeline processing has created extraction, sections, and chunks.
- A section heading is recognizable as content program text, for example a Markdown heading such as `## 1. CONTEUDO PROGRAMATICO`, or a textual/PDF-extracted heading such as `1. CONTEUDO PROGRAMATICO`.
- Topic lines are numbered or bulleted top-level entries, for example `1. Lingua Portuguesa: Compreensao de textos; Ortografia oficial`.
- Subject headings ending in a colon, such as `Lingua Portuguesa:`, are recognized as topic candidates inside a content-program section.
- Numbered subitems such as `1.1 Compreensao e interpretacao de textos` are recognized as bounded subtopic candidates under the current topic.

The current deterministic analyzer recognizes bibliography when both conditions are true:

- A section heading is recognizable as bibliography, for example `## 2. BIBLIOGRAFIA`, `2. BIBLIOGRAFIA`, or `REFERÊNCIAS`.
- Reference-like lines are present. Years improve confidence but are not exposed through bounded reads.

Minimal structured Markdown fixture expected to reach `analysis_status=analyzed`:

```markdown
# EDITAL DE QA

## 1. CONTEUDO PROGRAMATICO

1. Lingua Portuguesa: Compreensao e interpretacao de textos; Ortografia oficial; Pontuacao.
2. Informatica: Redes de computadores; Seguranca da informacao; Banco de dados.
3. Direito Administrativo: Atos administrativos; Poderes administrativos; Responsabilidade civil do Estado.

## 2. BIBLIOGRAFIA

BRASIL. Constituicao da Republica Federativa do Brasil. 1988.
MANUAL DE QA. Referencia simulada para teste interno. 2026.
```

Status criteria for the current implementation:

- `not_ready`: no safe extraction can be prepared, OCR required, text too short, pending/started ingestion, or no safe source to inspect.
- `needs_review`: bounded extraction exists but has warnings, such as no topic candidates, partial structure, alignment warnings, or gaps.
- `analyzed`: bounded extraction exists, the ingestion state is ready for review, and no extraction/alignment warnings require conservative gating.

`needs_review` and `not_ready` remain conservative states. They do not unlock concrete study, PSCPP personalization, Ciclo, Questões, Simulados, or Execução.

Remaining parser limitations before Coverage-A:

- Inline prose such as `Conteúdo programático: Português, Informática...` remains conservative and may still return `needs_review` when there is no clear heading/topic structure.
- Keep OCR, generation, coverage planning, and progress mutation out of this transition.

## Frontend Implications

Future phases may add:

- A same-origin Next proxy for `POST /api/materials/{materialId}/edital/analyze`.
- An `Analisar edital` action only for authenticated users and uploaded materials with `material_type=edital`.
- Product copy that explains analysis is controlled and may return not-ready.
- A session refresh or materials/editais refetch after success.

Current gating must remain:

- `/editais` can show `Edital enviado` when a material was classified as edital but no analyzed edital exists.
- `/study` and `/pscpp` unlock concrete guidance only after analyzed/ready state.
- Ciclo remains gated until an analyzed edital exists.
- Questões, Simulados, and Execução remain unavailable until their own later contracts exist.

The frontend must not:

- send raw text
- show raw analysis artifacts
- show answer keys or gabarito
- imply question generation, simulado generation, progress mutation, or scheduling

## Backend Test Coverage

Implemented focused backend tests cover:

- `401` unauthenticated request.
- `404` missing material.
- `404` non-owner material.
- `422` or `400` for material whose `material_type` is not `edital`.
- Safe deterministic textual preparation for fresh `.txt`, `.md`, and textual `.pdf` edital uploads when extraction artifacts are missing.
- OCR-required PDFs return `not_ready` without calling OCR.
- `not_ready` response for OCR-required, unsupported, missing safe extraction, or insufficient text.
- `analyzed` or `needs_review` response for an owned edital material with safe extracted text.
- Idempotent repeated call for an already final controlled analysis state.
- Response shape contains only allowed keys.
- Serialization no-leakage assertions for:
  - raw edital text
  - raw document text
  - `extracted_text`
  - chunks/sections body
  - OCR dump
  - base64
  - storage paths
  - `/Users/`
  - `C:\`
  - `password_hash`
  - session token
  - answer key/gabarito/correctness fields
  - worker/job/runtime traces

Targeted pytest command:

```bash
./.python_packages/bin/pytest tests/test_edital_analysis_controlled_api.py tests/test_edital_ingestion_api.py tests/test_editais_read_api.py tests/test_edital_summary_read_api.py tests/test_material_upload.py tests/test_materials_read_api.py
```

## Frontend Test Plan

Add focused frontend tests when a UI/proxy phase is approved:

- Analyze button is hidden before the implementation phase.
- Analyze button appears only for authenticated uploaded edital materials.
- Non-edital materials do not show edital analysis action.
- Proxy forwards cookies server-side and does not expose tokens/cookies.
- Success maps to updated lifecycle state.
- `not_ready`, `needs_review`, `failed`, `401`, `404`, `422`, `502`, and `503` states show product-safe copy.
- View models do not include raw fields.
- `/study`, `/pscpp`, Ciclo, Questões, Simulados, and Execução remain gated unless analyzed/ready conditions are met.

## Explicit Non-goals

- No automatic analysis on upload.
- No dashboard-wide `Analisar edital` UI.
- No OCR implementation or production OCR guarantee.
- No process/reprocess action.
- No bibliography alignment action in the same endpoint.
- No question generation.
- No simulado generation or execution.
- No progress mutation.
- No scheduler/calendar behavior.
- No PostgreSQL migration.
- No auth provider or signup flow.
- No raw content, storage path, token, or gabarito exposure.

## Recommended Implementation Sequence

1. `EditalAnalysis-B`: backend controlled endpoint, bounded response, owner-scope tests. Implemented.
2. `EditalAnalysis-C`: frontend same-origin proxy, sanitizer, API helper tests. Implemented.
3. `EditalAnalysis-D`: minimal material-detail UI action gated to authenticated uploaded edital materials. Implemented.
4. `Coverage-A`: read-only edital x materials coverage contract.
5. `StudyPlan-A`: concrete study guidance only after analyzed edital and coverage contracts are stable.
