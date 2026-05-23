from __future__ import annotations

from app.domain.models import (
    RuntimeApplyAuditRequirement,
    RuntimeApplyEnvironmentSafetyRequirement,
    RuntimeApplyFeatureFlagSnapshot,
    RuntimeApplyHumanReviewRequirement,
    RuntimeApplyIdempotencyRequirement,
    RuntimeApplyPolicyAuditEntry,
    RuntimeApplyPolicyBlocker,
    RuntimeApplyPolicySummary,
    RuntimeApplyPolicyValidationFinding,
    RuntimeApplyPolicyWarning,
    RuntimeApplyRollbackRequirement,
    RuntimeApplyScopePolicy,
    SimuladoFinalPedagogicalUpdateEvent,
    SimuladoRuntimeApplyPolicy,
)
from app.repositories.json_store import JsonStudyRepository


RUNTIME_APPLY_POLICY_BUILD_METHOD = "heuristic_simulado_runtime_apply_policy_builder"
RUNTIME_APPLY_FEATURE_FLAG_NAME = "simulado_runtime_apply_enabled"
RUNTIME_APPLY_POLICY_INPUTS_KEY = "runtime_apply_policy_inputs"
RUNTIME_APPLY_ALLOWED_MODES = {"event_proposal_only", "dry_run_final_event"}
RUNTIME_APPLY_SURFACES = [
    "minimal_progress_ledger",
    "ranking",
    "retention",
    "scheduler",
    "study_cycle",
    "curriculum_graph",
    "adaptive_tuning",
]


class SimuladoRuntimeApplyPolicyService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_runtime_apply_policy(
        self,
        source_final_event_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeApplyPolicy | None:
        if user_id is None:
            return None

        final_event = self.repository.get_simulado_final_pedagogical_update_event_by_id(
            source_final_event_id,
            user_id=user_id,
        )
        if final_event is None:
            return None

        existing = self.repository.get_simulado_runtime_apply_policy(
            source_final_event_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        policy_inputs = self._policy_inputs(final_event)
        feature_flag_enabled = bool(policy_inputs.get("runtime_apply_feature_flag_enabled", False))
        apply_window_open = bool(policy_inputs.get("apply_window_open", False))

        feature_flag_snapshot = self._feature_flag_snapshot(
            final_event=final_event,
            feature_flag_enabled=feature_flag_enabled,
        )
        apply_scope_policy = self._apply_scope_policy(final_event)
        idempotency_requirement = self._idempotency_requirement(final_event, policy_inputs)
        rollback_requirement = self._rollback_requirement(final_event, policy_inputs)
        audit_requirement = self._audit_requirement(final_event, policy_inputs)
        human_review_requirement = self._human_review_requirement(final_event, policy_inputs)
        environment_safety_requirement = self._environment_safety_requirement(
            final_event,
            policy_inputs,
        )
        blocker_code = self._blocker_code(
            final_event=final_event,
            feature_flag_enabled=feature_flag_enabled,
            apply_window_open=apply_window_open,
            idempotency_requirement=idempotency_requirement,
            rollback_requirement=rollback_requirement,
            audit_requirement=audit_requirement,
            human_review_requirement=human_review_requirement,
            environment_safety_requirement=environment_safety_requirement,
            apply_scope_policy=apply_scope_policy,
        )
        runtime_apply_policy_status = self._status_for_blocker(blocker_code)

        result = SimuladoRuntimeApplyPolicy(
            runtime_apply_policy_id=f"simulado-runtime-apply-policy:{final_event.final_event_id}",
            user_id=user_id,
            source_final_event_id=final_event.final_event_id,
            source_controlled_execution_id=final_event.source_controlled_execution_id,
            source_execution_plan_id=final_event.source_execution_plan_id,
            source_execution_approval_id=final_event.source_execution_approval_id,
            source_execution_guardrail_id=final_event.source_execution_guardrail_id,
            source_commit_transaction_id=final_event.source_commit_transaction_id,
            source_explicit_commit_id=final_event.source_explicit_commit_id,
            source_commit_shell_id=final_event.source_commit_shell_id,
            source_mutation_transaction_id=final_event.source_mutation_transaction_id,
            source_explicit_apply_id=final_event.source_explicit_apply_id,
            source_apply_shell_id=final_event.source_apply_shell_id,
            source_application_id=final_event.source_application_id,
            source_runtime_guardrail_id=final_event.source_runtime_guardrail_id,
            source_integrated_result_id=final_event.source_integrated_result_id,
            source_score_result_id=final_event.source_score_result_id,
            source_progress_guardrail_id=final_event.source_progress_guardrail_id,
            source_attempt_session_id=final_event.source_attempt_session_id,
            source_simulado_blueprint_id=final_event.source_simulado_blueprint_id,
            runtime_apply_policy_mode="policy_gate_only",
            runtime_apply_policy_status=runtime_apply_policy_status,
            readiness_state=blocker_code,
            policy_summary=self._policy_summary(
                final_event=final_event,
                feature_flag_enabled=feature_flag_enabled,
                environment_safety_requirement=environment_safety_requirement,
                apply_scope_policy=apply_scope_policy,
            ),
            feature_flag_snapshot=feature_flag_snapshot,
            apply_scope_policy=apply_scope_policy,
            idempotency_requirement=idempotency_requirement,
            rollback_requirement=rollback_requirement,
            audit_requirement=audit_requirement,
            human_review_requirement=human_review_requirement,
            environment_safety_requirement=environment_safety_requirement,
            audit_trail=self._audit_trail(
                final_event=final_event,
                feature_flag_enabled=feature_flag_enabled,
                environment_safety_requirement=environment_safety_requirement,
            ),
            blockers=self._blockers(final_event, blocker_code),
            validation_findings=self._validation_findings(final_event, blocker_code),
            warnings=self._warnings(final_event, blocker_code),
            runtime_apply_policy_created=True,
            runtime_apply_feature_flag_enabled=feature_flag_enabled,
            runtime_apply_allowed_now=False,
            final_event_apply_allowed=False,
            final_event_applied=False,
            final_event_application_started=False,
            final_event_application_completed=False,
            minimal_progress_ledger_apply_allowed=False,
            ranking_apply_allowed=False,
            retention_apply_allowed=False,
            scheduler_apply_allowed=False,
            study_cycle_apply_allowed=False,
            curriculum_graph_apply_allowed=False,
            adaptive_tuning_apply_allowed=False,
            runtime_application_enabled=False,
            runtime_application_applied=False,
            progress_mutation_enabled=False,
            progress_mutation_applied=False,
            ranking_update_enabled=False,
            ranking_update_applied=False,
            retention_update_enabled=False,
            retention_update_applied=False,
            scheduler_update_enabled=False,
            scheduler_update_applied=False,
            study_cycle_update_enabled=False,
            study_cycle_update_applied=False,
            curriculum_graph_update_enabled=False,
            curriculum_graph_update_applied=False,
            adaptive_tuning_enabled=False,
            adaptive_tuning_applied=False,
            commit_executed=False,
            mutation_committed=False,
            no_commit_execution=True,
            no_commit_execution_event_created=True,
            no_mutation_commit=True,
            no_mutation_commit_event_created=True,
            no_runtime_application=True,
            no_progress_mutation=True,
            no_ranking_update=True,
            no_retention_update=True,
            no_scheduler_update=True,
            no_study_cycle_update=True,
            no_curriculum_graph_update=True,
            no_adaptive_tuning_update=True,
            no_applied_final_pedagogical_update_event=True,
            no_applied_progress_ledger_entry=True,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            metadata={
                "build_method": RUNTIME_APPLY_POLICY_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_runtime_apply_policy(result, user_id=user_id)
        return result

    def get_runtime_apply_policy(
        self,
        source_final_event_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeApplyPolicy | None:
        return self.repository.get_simulado_runtime_apply_policy(
            source_final_event_id,
            user_id=user_id,
        )

    def get_runtime_apply_policy_by_id(
        self,
        runtime_apply_policy_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeApplyPolicy | None:
        return self.repository.get_simulado_runtime_apply_policy_by_id(
            runtime_apply_policy_id,
            user_id=user_id,
        )

    def _policy_inputs(self, final_event: SimuladoFinalPedagogicalUpdateEvent) -> dict[str, object]:
        candidate = final_event.metadata.get(RUNTIME_APPLY_POLICY_INPUTS_KEY, {})
        if isinstance(candidate, dict):
            return dict(candidate)
        return {}

    def _feature_flag_snapshot(
        self,
        *,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        feature_flag_enabled: bool,
    ) -> RuntimeApplyFeatureFlagSnapshot:
        return RuntimeApplyFeatureFlagSnapshot(
            snapshot_id=f"runtime-apply-feature-flag:{final_event.final_event_id}",
            feature_flag_name=RUNTIME_APPLY_FEATURE_FLAG_NAME,
            feature_flag_enabled=feature_flag_enabled,
            default_enabled=False,
            source="foundation_default",
            environment="local_default",
            metadata={},
        )

    def _apply_scope_policy(
        self,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
    ) -> RuntimeApplyScopePolicy:
        return RuntimeApplyScopePolicy(
            scope_policy_id=f"runtime-apply-scope-policy:{final_event.final_event_id}",
            minimal_progress_ledger_apply_allowed=False,
            ranking_apply_allowed=False,
            retention_apply_allowed=False,
            scheduler_apply_allowed=False,
            study_cycle_apply_allowed=False,
            curriculum_graph_apply_allowed=False,
            adaptive_tuning_apply_allowed=False,
            allowed_surfaces=[],
            blocked_surfaces=list(RUNTIME_APPLY_SURFACES),
            metadata={},
        )

    def _idempotency_requirement(
        self,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        policy_inputs: dict[str, object],
    ) -> RuntimeApplyIdempotencyRequirement:
        present = bool(policy_inputs.get("idempotency_key_present", False))
        valid = bool(policy_inputs.get("idempotency_key_valid", False))
        satisfied = present and valid
        return RuntimeApplyIdempotencyRequirement(
            requirement_id=f"runtime-apply-idempotency:{final_event.final_event_id}",
            idempotency_key_required=True,
            idempotency_key_present=present,
            idempotency_key_valid=valid,
            satisfied=satisfied,
            blockers=[] if satisfied else ["blocked_by_idempotency_requirement_missing"],
            metadata={},
        )

    def _rollback_requirement(
        self,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        policy_inputs: dict[str, object],
    ) -> RuntimeApplyRollbackRequirement:
        present = bool(policy_inputs.get("rollback_plan_present", False))
        verified = bool(policy_inputs.get("rollback_verified", False))
        satisfied = present and verified
        return RuntimeApplyRollbackRequirement(
            requirement_id=f"runtime-apply-rollback:{final_event.final_event_id}",
            rollback_required=True,
            rollback_plan_required=True,
            rollback_plan_present=present,
            rollback_verified=verified,
            satisfied=satisfied,
            blockers=[] if satisfied else ["blocked_by_rollback_requirement_missing"],
            metadata={},
        )

    def _audit_requirement(
        self,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        policy_inputs: dict[str, object],
    ) -> RuntimeApplyAuditRequirement:
        present = bool(policy_inputs.get("audit_confirmation_present", False))
        return RuntimeApplyAuditRequirement(
            requirement_id=f"runtime-apply-audit:{final_event.final_event_id}",
            audit_required=True,
            audit_confirmation_required=True,
            audit_confirmation_present=present,
            satisfied=present,
            blockers=[] if present else ["blocked_by_audit_requirement_missing"],
            metadata={},
        )

    def _human_review_requirement(
        self,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        policy_inputs: dict[str, object],
    ) -> RuntimeApplyHumanReviewRequirement:
        present = bool(policy_inputs.get("human_review_present", False))
        return RuntimeApplyHumanReviewRequirement(
            requirement_id=f"runtime-apply-human-review:{final_event.final_event_id}",
            human_review_required=True,
            human_review_present=present,
            satisfied=present,
            blockers=[] if present else ["blocked_by_human_review_requirement_missing"],
            metadata={},
        )

    def _environment_safety_requirement(
        self,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        policy_inputs: dict[str, object],
    ) -> RuntimeApplyEnvironmentSafetyRequirement:
        environment_safe_for_apply = bool(policy_inputs.get("environment_safe_for_apply", False))
        write_mode_allowed = bool(policy_inputs.get("write_mode_allowed", False))
        dry_run_only = bool(policy_inputs.get("dry_run_only", True))
        external_services_disabled = bool(policy_inputs.get("external_services_disabled", True))
        satisfied = (
            environment_safe_for_apply and write_mode_allowed and external_services_disabled
        )
        return RuntimeApplyEnvironmentSafetyRequirement(
            requirement_id=f"runtime-apply-environment-safety:{final_event.final_event_id}",
            environment_safe_for_apply=environment_safe_for_apply,
            write_mode_allowed=write_mode_allowed,
            dry_run_only=dry_run_only,
            external_services_disabled=external_services_disabled,
            satisfied=satisfied,
            blockers=[] if satisfied else ["blocked_by_environment_not_safe_for_apply"],
            metadata={},
        )

    def _blocker_code(
        self,
        *,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        feature_flag_enabled: bool,
        apply_window_open: bool,
        idempotency_requirement: RuntimeApplyIdempotencyRequirement,
        rollback_requirement: RuntimeApplyRollbackRequirement,
        audit_requirement: RuntimeApplyAuditRequirement,
        human_review_requirement: RuntimeApplyHumanReviewRequirement,
        environment_safety_requirement: RuntimeApplyEnvironmentSafetyRequirement,
        apply_scope_policy: RuntimeApplyScopePolicy,
    ) -> str:
        if (
            final_event.event_summary.unsafe_public_answer_key_exposure_detected
            or final_event.event_summary.unsafe_gabarito_exposure_detected
        ):
            return "blocked_by_public_answer_key_exposure_forbidden"
        if final_event.final_event_mode not in RUNTIME_APPLY_ALLOWED_MODES:
            return "blocked_by_final_event_not_proposal_only"
        if final_event.final_pedagogical_update_event_applied or final_event.final_event_status == "applied":
            return "blocked_by_final_event_already_applied"
        if not feature_flag_enabled:
            return "blocked_by_runtime_apply_feature_flag_disabled"
        if not apply_window_open:
            return "blocked_by_runtime_apply_not_allowed_now"
        if not idempotency_requirement.satisfied:
            return "blocked_by_idempotency_requirement_missing"
        if not rollback_requirement.satisfied:
            return "blocked_by_rollback_requirement_missing"
        if not audit_requirement.satisfied:
            return "blocked_by_audit_requirement_missing"
        if not human_review_requirement.satisfied:
            return "blocked_by_human_review_requirement_missing"
        if not environment_safety_requirement.satisfied:
            return "blocked_by_environment_not_safe_for_apply"
        if apply_scope_policy.blocked_surfaces:
            return "blocked_by_apply_scope_not_allowed"
        return "ready_for_future_minimal_apply_review"

    def _status_for_blocker(self, blocker_code: str) -> str:
        if blocker_code == "ready_for_future_minimal_apply_review":
            return "ready_for_future_minimal_apply_review"
        if blocker_code == "blocked_by_runtime_apply_feature_flag_disabled":
            return "apply_not_enabled"
        if blocker_code in {
            "blocked_by_idempotency_requirement_missing",
            "blocked_by_rollback_requirement_missing",
            "blocked_by_audit_requirement_missing",
            "blocked_by_human_review_requirement_missing",
            "blocked_by_environment_not_safe_for_apply",
            "blocked_by_apply_scope_not_allowed",
        }:
            return "policy_needs_review"
        return "apply_blocked"

    def _policy_summary(
        self,
        *,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        feature_flag_enabled: bool,
        environment_safety_requirement: RuntimeApplyEnvironmentSafetyRequirement,
        apply_scope_policy: RuntimeApplyScopePolicy,
    ) -> RuntimeApplyPolicySummary:
        return RuntimeApplyPolicySummary(
            summary_id=f"runtime-apply-policy-summary:{final_event.final_event_id}",
            source_final_event_present=True,
            source_final_event_created=final_event.final_pedagogical_update_event_created,
            source_final_event_applied=final_event.final_pedagogical_update_event_applied,
            source_final_event_apply_allowed=final_event.final_pedagogical_update_event_apply_allowed,
            source_event_proposal_only=(final_event.final_event_mode in RUNTIME_APPLY_ALLOWED_MODES),
            apply_feature_flag_enabled=feature_flag_enabled,
            apply_allowed_now=False,
            minimal_progress_ledger_scope_allowed=False,
            ranking_scope_allowed=False,
            retention_scope_allowed=False,
            scheduler_scope_allowed=False,
            study_cycle_scope_allowed=False,
            curriculum_graph_scope_allowed=False,
            adaptive_tuning_scope_allowed=False,
            idempotency_required=True,
            rollback_required=True,
            audit_required=True,
            human_review_required=True,
            environment_safe_for_apply=environment_safety_requirement.environment_safe_for_apply,
            unsafe_public_answer_key_exposure_detected=(
                final_event.event_summary.unsafe_public_answer_key_exposure_detected
            ),
            unsafe_gabarito_exposure_detected=(
                final_event.event_summary.unsafe_gabarito_exposure_detected
            ),
            metadata={
                "blocked_surface_count": len(apply_scope_policy.blocked_surfaces),
            },
        )

    def _audit_trail(
        self,
        *,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        feature_flag_enabled: bool,
        environment_safety_requirement: RuntimeApplyEnvironmentSafetyRequirement,
    ) -> list[RuntimeApplyPolicyAuditEntry]:
        trail = [
            RuntimeApplyPolicyAuditEntry(
                audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:created",
                event_type="runtime_apply_policy_created",
                actor_user_id=final_event.user_id,
                message="Runtime apply policy artifact created.",
                metadata={},
            ),
            RuntimeApplyPolicyAuditEntry(
                audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:evaluated",
                event_type="runtime_apply_policy_evaluated",
                actor_user_id=final_event.user_id,
                message="Runtime apply policy was evaluated against the final event.",
                metadata={},
            ),
            RuntimeApplyPolicyAuditEntry(
                audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:idempotency",
                event_type="idempotency_required",
                actor_user_id=final_event.user_id,
                message="Idempotency protection remains required for any future apply path.",
                metadata={},
            ),
            RuntimeApplyPolicyAuditEntry(
                audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:rollback",
                event_type="rollback_required",
                actor_user_id=final_event.user_id,
                message="Rollback protection remains required for any future apply path.",
                metadata={},
            ),
            RuntimeApplyPolicyAuditEntry(
                audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:audit",
                event_type="audit_required",
                actor_user_id=final_event.user_id,
                message="Audit confirmation remains required for any future apply path.",
                metadata={},
            ),
            RuntimeApplyPolicyAuditEntry(
                audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:human-review",
                event_type="human_review_required",
                actor_user_id=final_event.user_id,
                message="Human review remains required for any future apply path.",
                metadata={},
            ),
        ]
        if not feature_flag_enabled:
            trail.append(
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:feature-flag-disabled",
                    event_type="runtime_apply_feature_flag_disabled",
                    actor_user_id=final_event.user_id,
                    message="Runtime apply feature flag remains disabled.",
                    metadata={},
                )
            )
        if not environment_safety_requirement.satisfied:
            trail.append(
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:environment-not-safe",
                    event_type="environment_not_safe_for_apply",
                    actor_user_id=final_event.user_id,
                    message="Environment remains unsafe for apply operations.",
                    metadata={},
                )
            )
        trail.extend(
            [
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:blocked",
                    event_type="runtime_apply_blocked",
                    actor_user_id=final_event.user_id,
                    message="Runtime apply remains blocked in this foundation.",
                    metadata={},
                ),
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:no-final-event-apply",
                    event_type="no_applied_final_pedagogical_update_event",
                    actor_user_id=final_event.user_id,
                    message="No applied final pedagogical update event was created.",
                    metadata={},
                ),
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:no-ledger-apply",
                    event_type="no_applied_progress_ledger_entry",
                    actor_user_id=final_event.user_id,
                    message="No applied progress ledger entry was created.",
                    metadata={},
                ),
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:no-runtime-application",
                    event_type="no_runtime_application",
                    actor_user_id=final_event.user_id,
                    message="No runtime application was performed.",
                    metadata={},
                ),
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:no-progress-mutation",
                    event_type="no_progress_mutation",
                    actor_user_id=final_event.user_id,
                    message="No progress mutation was performed.",
                    metadata={},
                ),
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:no-ranking-update",
                    event_type="no_ranking_update",
                    actor_user_id=final_event.user_id,
                    message="No ranking update was performed.",
                    metadata={},
                ),
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:no-retention-update",
                    event_type="no_retention_update",
                    actor_user_id=final_event.user_id,
                    message="No retention update was performed.",
                    metadata={},
                ),
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:no-scheduler-update",
                    event_type="no_scheduler_update",
                    actor_user_id=final_event.user_id,
                    message="No scheduler update was performed.",
                    metadata={},
                ),
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:no-study-cycle-update",
                    event_type="no_study_cycle_update",
                    actor_user_id=final_event.user_id,
                    message="No study cycle update was performed.",
                    metadata={},
                ),
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:no-graph-update",
                    event_type="no_curriculum_graph_update",
                    actor_user_id=final_event.user_id,
                    message="No curriculum graph update was performed.",
                    metadata={},
                ),
                RuntimeApplyPolicyAuditEntry(
                    audit_id=f"runtime-apply-policy-audit:{final_event.final_event_id}:no-tuning-update",
                    event_type="no_adaptive_tuning_update",
                    actor_user_id=final_event.user_id,
                    message="No adaptive tuning update was performed.",
                    metadata={},
                ),
            ]
        )
        return trail

    def _blockers(
        self,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        blocker_code: str,
    ) -> list[RuntimeApplyPolicyBlocker]:
        messages = {
            "blocked_by_final_event_not_proposal_only": "Final event is not proposal-only.",
            "blocked_by_final_event_already_applied": "Final event is already marked as applied.",
            "blocked_by_runtime_apply_feature_flag_disabled": "Runtime apply feature flag remains disabled.",
            "blocked_by_runtime_apply_not_allowed_now": "Runtime apply remains not allowed now.",
            "blocked_by_idempotency_requirement_missing": "Idempotency requirement remains unsatisfied.",
            "blocked_by_rollback_requirement_missing": "Rollback requirement remains unsatisfied.",
            "blocked_by_audit_requirement_missing": "Audit requirement remains unsatisfied.",
            "blocked_by_human_review_requirement_missing": "Human review requirement remains unsatisfied.",
            "blocked_by_environment_not_safe_for_apply": "Environment remains unsafe for apply operations.",
            "blocked_by_apply_scope_not_allowed": "Apply scopes remain disabled in this foundation.",
            "blocked_by_public_answer_key_exposure_forbidden": "Unsafe public answer key exposure prevents policy readiness.",
            "ready_for_future_minimal_apply_review": "Runtime apply policy is only ready for future review.",
        }
        return [
            RuntimeApplyPolicyBlocker(
                blocker_id=f"runtime-apply-policy-blocker:{final_event.final_event_id}:{blocker_code}",
                code=blocker_code,
                message=messages.get(blocker_code, blocker_code.replace("_", " ")),
                related_artifact_type="simulado_final_pedagogical_update_event",
                related_artifact_id=final_event.final_event_id,
                metadata={},
            )
        ]

    def _validation_findings(
        self,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        blocker_code: str,
    ) -> list[RuntimeApplyPolicyValidationFinding]:
        return [
            RuntimeApplyPolicyValidationFinding(
                finding_id=f"runtime-apply-policy-finding:{final_event.final_event_id}:policy",
                code=(
                    "runtime_apply_policy_ready_for_review"
                    if blocker_code == "ready_for_future_minimal_apply_review"
                    else "runtime_apply_policy_blocked"
                ),
                message="Runtime apply policy remains a gate-only artifact in this foundation.",
                related_artifact_type="simulado_final_pedagogical_update_event",
                related_artifact_id=final_event.final_event_id,
                metadata={"readiness_state": blocker_code},
            )
        ]

    def _warnings(
        self,
        final_event: SimuladoFinalPedagogicalUpdateEvent,
        blocker_code: str,
    ) -> list[RuntimeApplyPolicyWarning]:
        warnings = [
            RuntimeApplyPolicyWarning(
                code="runtime_apply_policy_gate_only",
                message="This runtime apply policy is a gate-only artifact and does not apply runtime changes.",
                related_artifact_type="simulado_final_pedagogical_update_event",
                related_artifact_id=final_event.final_event_id,
                metadata={},
            )
        ]
        if blocker_code != "ready_for_future_minimal_apply_review":
            warnings.append(
                RuntimeApplyPolicyWarning(
                    code="runtime_apply_policy_blocked",
                    message="Runtime apply remains blocked by feature flags, policy requirements, or source state.",
                    related_artifact_type="simulado_final_pedagogical_update_event",
                    related_artifact_id=final_event.final_event_id,
                    metadata={"readiness_state": blocker_code},
                )
            )
        return warnings
