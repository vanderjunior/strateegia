# Engineering Principles

## Roadmap Implementation Pattern

- roadmap steps alternate foundation work and stabilization fixture work
- a foundation step may add models, services, repositories, APIs, docs, and tests
- a stabilization step should be fixture and regression work only
- do not mix the next foundation into a stabilization step
- do not implement future roadmap steps early

## TDD and Scope Control

- write tests first
- implement the minimal production code needed
- avoid broad refactors
- preserve the existing suite
- use synthetic deterministic fixtures
- avoid external services
- avoid real OCR, LLM, or vector calls
- add no new dependencies unless unavoidable

## Artifact Conventions

- artifact names must be explicit and source-aware
- source artifact ids must be stored
- `user_id` must be present
- `generated_at` is allowed
- `metadata` must stay bounded
- payloads must be JSON-safe
- no raw runtime dumps
- no absolute paths
- no full document body
- no OCR or base64 blobs
- no password, session, or token leaks

## API Conventions

- endpoints must be authenticated
- endpoints must be owner-only
- `POST /source/{id}/artifact/build` creates a deterministic artifact
- `GET /source/{id}/artifact` reads an existing artifact only
- `GET /artifact/{id}` reads by artifact id
- `GET` must not build
- `GET` must not mutate
- `POST` must be idempotent for the same source
- user-scope leakage must follow the existing safe API style, typically `401`, `403`, or `404` according to current project conventions

## Testing Conventions

- foundation tests
- API tests
- security and no-leakage tests
- stabilization fixture tests
- idempotency tests
- owner-scope tests
- `GET` read-only tests
- source immutability tests
- no runtime mutation assertions
- no answer key or gabarito leakage assertions

## Naming and Status Conventions

- use names like `proposal`, `plan`, `guardrail`, `policy`, `dry_run`, `preview`, and `not_applied` for non-mutating layers
- avoid names implying real apply unless that roadmap step explicitly applies
- avoid `completed`, `applied`, `executed`, or `committed` for dry-run artifacts unless explicitly false
- use explicit booleans for applied, enabled, and `no_*` safeguard states

## What Not To Do

- do not implement LLM, RAG, or vector features unless requested
- do not implement real apply before policy and feature flag steps
- do not update ranking, scheduler, or retention during scoring or correction
- do not expose answer key or gabarito
- do not mutate source artifacts
- do not add dashboard action buttons unless explicitly requested
- do not add background workers
- do not add SQL migrations unless explicitly requested
- do not change requirements without need
