# Runtime Architecture

## Runtime Philosophy

- deterministic-first runtime
- artifact-first architecture
- user-scoped artifacts
- owner-only access
- bounded JSON-safe payloads
- read-only `GET`
- deterministic and idempotent `POST` builds for the same source
- no implicit build on `GET`
- no raw runtime dumps
- no public answer key or gabarito exposure
- no LLM, RAG, or vector search unless a roadmap step explicitly requests it
- no autonomous mutation by default
- heuristics are allowed only when explicit, bounded, deterministic, and regression-tested
- proposal -> guardrail -> policy -> minimal apply -> propagation is the intended runtime safety sequence

## Runtime Mutation Philosophy

- runtime mutations are exceptional, not default behavior
- any future apply path must require explicit policy, feature flag, idempotency, rollback, audit, human review, and scoped surface allow-list
- ranking, retention, scheduler, study cycle, curriculum graph, and adaptive tuning must not update as side effects of correction or scoring
- there must be no hidden autonomous apply
- there must be no background mutation unless an explicit roadmap step introduces it
- there must be no automatic global recalculation from simulado results
- the first real apply must be isolated to a minimal progress ledger or snapshot only

## Hard Invariants

- `GET` must be read-only
- `POST build` must be deterministic and idempotent for the same source
- artifacts must be user-scoped
- APIs must be owner-only
- source artifacts must not be mutated by downstream build or read flows
- no answer key or gabarito public exposure
- no raw final content exposure
- no password, session, path, OCR, base64, or raw-runtime leaks
- no runtime mutation unless the roadmap step explicitly says apply
- no LLM, RAG, or vector search unless the roadmap step explicitly asks for it
- no broad refactor during roadmap steps
- the full test suite must remain green

## No-Apply Default

Until an explicit apply step says otherwise, these defaults must hold:

- `final_event_applied = false`
- `runtime_apply_allowed_now = false`
- `progress_mutation_applied = false`
- `ranking_update_applied = false`
- `retention_update_applied = false`
- `scheduler_update_applied = false`
- `study_cycle_update_applied = false`
- `curriculum_graph_update_applied = false`
- `adaptive_tuning_applied = false`
- `no_progress_mutation = true`
- `no_ranking_update = true`
- `no_retention_update = true`
- `no_scheduler_update = true`
- `no_study_cycle_update = true`
- `no_curriculum_graph_update = true`
- `no_adaptive_tuning_update = true`

## Apply Ladder

The intended runtime safety ladder is:

1. final event proposal
2. runtime apply policy / feature flag
3. minimal progress ledger apply
4. applied event ledger / idempotency
5. propagation guardrails
6. controlled propagation apply
7. only later: ranking, retention, scheduler, study cycle, curriculum graph, and adaptive tuning

Current ladder constraints:

- `47A` is policy gate only
- `47B` is stabilization only
- `48A` is the first possible real apply step, and only to an isolated minimal progress ledger or snapshot
- ranking, scheduler, retention, study cycle, curriculum graph, and adaptive tuning must not be part of the first real apply
