# Simulado Runtime Chain

## Current Simulado Runtime Chain

`SimuladoAttemptSession`
-> `SimuladoAnswerSubmission`
-> `SimuladoCorrectionShell`
-> `SimuladoAnswerKeyBoundary`
-> `SimuladoCorrectionResult`
-> `SimuladoScoreResult`
-> `SimuladoProgressMutationGuardrail`
-> `SimuladoIntegratedExecutionCorrection`
-> `SimuladoRuntimeApplicationGuardrail`
-> `SimuladoRuntimeProgressApplication`
-> `SimuladoControlledRuntimeApplyShell`
-> `SimuladoExplicitRuntimeProgressApply`
-> `SimuladoRuntimeProgressMutationTransaction`
-> `SimuladoControlledRuntimeMutationCommitShell`
-> `SimuladoExplicitRuntimeMutationCommit`
-> `SimuladoRuntimeMutationCommitTransaction`
-> `SimuladoControlledRuntimeCommitExecutionGuardrail`
-> `SimuladoExplicitRuntimeCommitExecutionApproval`
-> `SimuladoRuntimeCommitExecutionPlan`
-> `SimuladoControlledRuntimeCommitExecution`
-> `SimuladoFinalPedagogicalUpdateEvent`
-> `SimuladoRuntimeApplyPolicy`

## Current State

- full repo suite after `47A`: `1266 passed, 5 warnings`
- current layer: `SimuladoRuntimeApplyPolicy`
- current mode: `policy_gate_only`
- runtime apply feature flag disabled by default
- minimal progress ledger apply disabled
- no applied final event
- no applied progress ledger entry
- no runtime mutation

## Completed Recent Steps

- `33C` scoring foundation
- `33C-B` scoring stabilization
- `33D` progress mutation guardrails
- `33D-B` stabilization
- `33E` integrated execution/correction
- `33E-B` stabilization
- `34A` runtime application guardrail
- `34B` stabilization
- `35A` runtime progress application
- `35B` stabilization
- `36A` controlled runtime progress apply shell
- `36B` stabilization
- `37A` explicit runtime progress apply
- `37B` stabilization
- `38A` runtime progress mutation transaction
- `38B` stabilization
- `39A` controlled mutation commit shell
- `39B` stabilization
- `40A` explicit mutation commit
- `40B` stabilization
- `41A` runtime mutation commit transaction
- `41B` stabilization
- `42A` controlled commit execution guardrail
- `42B` stabilization
- `43A` explicit commit execution approval
- `43B` stabilization
- `44A` runtime commit execution plan
- `44B` stabilization
- `45A` controlled runtime commit execution dry-run
- `45B` stabilization
- `46A` final pedagogical update event proposal
- `46B` stabilization
- `47A` runtime apply policy / feature flag foundation

## Next Roadmap

- `47B` Runtime Apply Policy / Feature Flag Stabilization Fixtures
- `48A` Minimal Progress Ledger Apply Foundation
- `48B` Minimal Progress Ledger Apply Stabilization Fixtures
- `49A` Applied Event Ledger / Idempotency Foundation
- `49B` Applied Event Ledger / Idempotency Stabilization Fixtures
- `50A` Propagation Guardrails for Ranking/Retention/Scheduler/Study Cycle/Graph
- `50B` Stabilization Fixtures
- `51A` Controlled Propagation Apply Foundation
- `51B` Stabilization Fixtures

## First Real Apply Rule

- the first real apply should begin only at `48A`
- the first real apply must be limited to an isolated simulado progress ledger or snapshot
- no ranking update
- no retention update
- no scheduler update
- no study cycle update
- no curriculum graph update
- no adaptive tuning
- no global curriculum recalculation
- no hidden background mutation

## Prompt Compression Guidance

Future prompts should not paste the full historical chain.

Instead, instruct Codex to read these files first:

- `docs/architecture/runtime-architecture.md`
- `docs/architecture/project-direction.md`
- `docs/architecture/engineering-principles.md`
- `docs/architecture/simulado-runtime-chain.md`

Then specify only:

- current step
- allowed files
- forbidden future steps
- expected test targets
- final report requirements
