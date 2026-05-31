# Scope Model Contract Plan

## Purpose

Define the product and domain model for edital scope, bibliography, study materials, and later study organization before adding more parsing or coverage behavior.

This is a planning contract only. It does not add endpoints, UI actions, parser changes, OCR, LLM calls, generation, simulado execution, progress mutation, scheduler behavior, PostgreSQL, external auth, or signup.

## Product Objective

The product should organize preparation from distinct source roles:

- edital: official scope source that defines what must be studied
- bibliography: reference source that may support the scope, but may live inside the edital or in a separate file
- study material: learning content used to cover edital topics
- previous exams: later practice/style reference, not the first source of scope

Target long-term flow:

1. User uploads/classifies an edital.
2. User analyzes the edital into a bounded taxonomy.
3. User uploads bibliography and study materials.
4. The app prepares those materials into bounded metadata/readiness surfaces.
5. Coverage compares edital taxonomy against prepared references/materials.
6. Study organization uses coverage results later.
7. Summaries, reading guidance, questions, review, simulados, and progress come only after separate contracts.

## Current Findings

- Current `EditalIngestionService` detects edital sections and extracts flat `topics` plus `subtopics`; it does not model a deeper area/theme layer.
- Topic extraction relies on recognizable content-program headings plus numbered, bulleted, or colon-separated lines.
- Bibliography extraction only runs for sections classified as `bibliography`, but any meaningful line inside that section can become a bibliography candidate. This can inflate counts when the section boundary is too broad or non-reference lines are included.
- Current `BibliographyAlignmentService` has richer internal evidence structures, but those are not browser-facing and should remain bounded.
- Current coverage uses bounded edital topic/subtopic labels and material filename/type/section-title tokens. It deliberately avoids raw text and evidence snippets.
- Upload classification is persisted as `material_type`, but classification alone does not prepare, analyze, or compare content.

## Material Roles

### `edital`

Defines the official study scope.

Rules:

- An uploaded `edital` means "edital enviado", not "edital analisado".
- A controlled `Analisar edital` action can create bounded lifecycle metadata and taxonomy.
- The edital itself is not a study coverage source for its own scope.
- `analysis_status=not_ready` must not unlock study or PSCPP personalization.

### `bibliography`

Represents official/reference sources.

Rules:

- Bibliography may be found inside an explicit edital bibliography/reference section.
- Bibliography may also be uploaded as a separate `material_type=bibliography` file.
- A bibliography file needs its own bounded preparation/analysis flow before it can support coverage.
- Bibliography supports confidence/reference mapping; it should not define the full scope unless explicitly linked to edital taxonomy.

### `study_material`

Represents learning content.

Rules:

- Study material is the primary source for learning coverage.
- It needs bounded preparation: extraction/readiness, section detection, safe metadata, and later topic mapping.
- It should not generate summaries, questions, or progress changes until later contracts.

### `previous_exam`

Represents practice/style evidence for later phases.

Rules:

- Previous exams should not define edital scope.
- They can later support question style, recurrence, and practice planning after a dedicated contract.
- They should be ignored or treated as supporting only in the first coverage refinement.

### `note`

Represents user notes, summaries, or lightweight references.

Rules:

- Notes can support organization later.
- Notes should not be treated as authoritative scope or full coverage without explicit user/product rules.

### `other` / `unknown`

Represents unclassified or legacy uploads.

Rules:

- These require classification before reliable scope/coverage behavior.
- They should not silently unlock coverage or study planning.

## Edital Hierarchy Model

The edital taxonomy should support a deeper bounded hierarchy:

```text
area/theme -> topic -> subtopic
```

Example:

```text
Area/theme: Manobrabilidade
Topic: Rebocadores
Subtopic: Uso de rebocadores em atracação
```

Recommended semantics:

- `areas_count` or `themes_count`: number of top-level thematic buckets.
- `topics_count`: number of study topics inside those areas/themes.
- `subtopics_count`: number of concrete study items under topics.

Open naming decision:

- Prefer `areas_count` if the product copy uses "áreas".
- Prefer `themes_count` if parser/source data calls top-level groups "temas".
- Keep one canonical backend field once chosen; avoid exposing both unless there is a real distinction.

Initial recommendation:

- Use `areas_count` for bounded backend and frontend contracts because it reads naturally in product copy: "Áreas", "Tópicos", "Subtópicos".

Taxonomy rules:

- Preserve source order.
- Return bounded labels, ids, counts, and lifecycle status only.
- Do not expose raw excerpts, raw section bodies, chunk bodies, or storage paths.
- Treat ambiguous taxonomy as `needs_review`, not as ready.
- Do not force every edital to have all three levels; if an edital only has topic/subtopic, area may be `unknown` or omitted in bounded UI.

## Bibliography Model

Bibliography can come from:

- an explicit bibliography/reference section inside the edital
- a separate uploaded `material_type=bibliography` file
- a manually classified bibliography/reference material

Counting rules:

- Only count bibliography from explicit bibliography/reference sections or prepared bibliography files.
- Do not infer hundreds of bibliography items from generic text, content-program lines, rules, schedules, or prose.
- Require reference-like signals before counting:
  - author/entity + title-like text
  - year
  - edition/publisher
  - legal norm identifier
  - line formatting consistent with references
- Low-confidence lines should become warnings or `needs_review`, not bibliography counts.

Separate bibliography uploads need their own bounded lifecycle:

```text
uploaded_not_prepared -> prepared -> needs_review -> failed/not_ready
```

Bounded bibliography read should expose only:

- material/document id
- status
- references_count
- warnings_count
- source
- optional reference category counts

It must not expose raw bibliography bodies or evidence snippets.

## Study Material Model

Study materials need their own preparation/readiness flow before they can support coverage.

Potential bounded preparation outputs:

- `material_id` / `document_id`
- `material_type`
- `preparation_status`
- `extraction_status`
- `sections_count`
- `topics_hint_count`
- `warnings_count`
- `ready_for_coverage`
- `source`

Preparation should:

- extract or confirm text availability
- detect sections/titles
- summarize bounded metadata
- mark OCR-required files as not ready without running OCR unless a later OCR contract exists
- later classify likely covered edital topics

Preparation should not:

- expose raw text
- generate summaries
- generate questions
- mutate progress
- create study sessions

## Proposed Future User Actions

Use product-facing labels:

- Edital: `Analisar edital`
- Bibliography: `Preparar bibliografia`
- Study material: `Preparar material para estudo`
- Previous exam: `Preparar prova anterior`

Avoid normal-user labels:

- process
- pipeline
- chunk
- runtime
- backend
- OCR, except as a caution when a scanned file cannot be read yet

## Proposed Backend Phases

Recommended sequence:

1. `EditalTaxonomy-A`: refine edital parser and bounded model for `area/topic/subtopic`.
2. `Bibliography-A`: add bounded bibliography material preparation/readiness.
3. `StudyMaterial-A`: add bounded study material preparation/readiness.
4. `Coverage-Refine-A`: compare edital taxonomy to prepared study materials and bibliography.
5. `StudyPlan-Planning-A`: define study organization contract after coverage semantics stabilize.

## Coverage Prerequisites

Real coverage should require:

- authenticated user scope
- analyzed edital with usable taxonomy
- `analysis_status=analyzed` or conservative `needs_review` semantics that do not overclaim readiness
- at least one prepared `study_material` or prepared `bibliography`
- bounded material readiness metadata

Rules:

- `analysis_status=not_ready` must return no real coverage.
- Uploaded-but-unanalyzed edital must not produce coverage.
- `previous_exam` should be ignored or supporting only in the first refined coverage contract.
- `unknown`, `other`, and unprepared materials should not count as reliable coverage.
- Coverage should remain read-only and must not unlock study planning by itself unless a future StudyPlan contract explicitly combines lifecycle and coverage thresholds.

## Safety and No-Leakage Rules

All future contracts must avoid:

- raw edital text
- raw material text
- `extracted_text`
- raw chunks or sections
- OCR dumps
- base64 payloads
- `storage_path` or local/private paths
- raw bibliography bodies
- evidence snippets
- confidence traces or internal worker/job details
- token, cookie, session, or password fields
- answer key, gabarito, correctness, or correction fields

## Non-Goals

- no parser changes in this planning phase
- no new endpoints
- no frontend buttons or UX behavior changes
- no automatic edital analysis on upload
- no bibliography preparation implementation yet
- no study material preparation implementation yet
- no OCR automation
- no LLM calls
- no summaries
- no questions
- no simulado generation or execution
- no progress mutation
- no scheduler
- no PostgreSQL
- no external auth provider or signup

## Recommended Next Implementation Phase

Recommended next phase: `EditalTaxonomy-A`.

Reason:

- A poor edital hierarchy breaks every downstream flow.
- Bibliography counts and coverage quality depend on knowing what is true scope versus reference material.
- Coverage refinement should wait until the source taxonomy distinguishes area/theme, topic, and subtopic.

`EditalTaxonomy-A` should be bounded and conservative:

- add or normalize taxonomy models for area/topic/subtopic
- keep existing lifecycle semantics
- add tests for PSCPP-style nested content
- reduce false bibliography counts by tightening section boundaries and reference-like line rules
- expose only bounded counts/statuses through existing or planned read surfaces
- do not add study unlock, OCR, generation, simulado, or progress behavior
