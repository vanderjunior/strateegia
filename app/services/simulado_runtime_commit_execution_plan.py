from __future__ import annotations

from app.domain.models import (
    PlannedCommitExecutionPhase,
    PlannedProgressExecutionStep,
    PlannedSurfaceExecutionStep,
    RuntimeCommitAuditCheckpoint,
    RuntimeCommitExecutionPlanBlocker,
    RuntimeCommitExecutionPlanSummary,
    RuntimeCommitExecutionPlanValidationFinding,
    RuntimeCommitExecutionPlanWarning,
    RuntimeCommitRollbackCheckpoint,
    SimuladoControlledRuntimeCommitExecutionGuardrail,
    SimuladoExplicitRuntimeCommitExecutionApproval,
    SimuladoRuntimeCommitExecutionPlan,
)
from app.repositories.json_store import JsonStudyRepository


RUNTIME_COMMIT_EXECUTION_PLAN_BUILD_METHOD = (
    "heuristic_simulado_runtime_commit_execution_plan_builder"
)
PROGRESS_STEP_TYPE_BY_DELTA = {
    "mastery_delta": "progress_delta_step",
    "completion_delta": "progress_delta_step",
    "accuracy_delta": "progress_delta_step",
    "review_signal_delta": "progress_signal_step",
    "confidence_delta": "progress_signal_step",
}
SURFACE_STEP_TYPE_BY_SURFACE = {
    "progress": "progress_surface_step",
    "ranking": "ranking_surface_step",
    "retention": "retention_surface_step",
    "scheduler": "scheduler_surface_step",
    "study_cycle": "study_cycle_surface_step",
    "curriculum_graph": "curriculum_graph_surface_step",
    "adaptive_tuning": "adaptive_tuning_surface_step",
}
PHASE_TYPES = [
    "preflight_validation",
    "rollback_checkpoint_validation",
    "progress_step_review",
    "surface_step_review",
    "audit_checkpoint_review",
    "final_execution_review",
]


class SimuladoRuntimeCommitExecutionPlanService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_execution_plan(
        self,
        source_execution_approval_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeCommitExecutionPlan | None:
        if user_id is None:
            return None

        approval = self.repository.get_simulado_explicit_commit_execution_approval_by_id(
            source_execution_approval_id,
            user_id=user_id,
        )
        if approval is None:
            return None

        existing = self.repository.get_simulado_runtime_commit_execution_plan(
            source_execution_approval_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        guardrail = self.repository.get_simulado_controlled_commit_execution_guardrail_by_id(
            approval.source_execution_guardrail_id,
            user_id=user_id,
        )
        planned_progress_steps = self._planned_progress_steps(approval)
        planned_surface_steps = self._planned_surface_steps(approval)
        rollback_checkpoints = self._rollback_checkpoints(approval, guardrail)
        audit_checkpoints = self._audit_checkpoints(approval)
        blocker_codes = self._blocker_codes(
            approval=approval,
            planned_progress_steps=planned_progress_steps,
            planned_surface_steps=planned_surface_steps,
            rollback_checkpoints=rollback_checkpoints,
            audit_checkpoints=audit_checkpoints,
        )
        ready_for_future = not blocker_codes and approval.explicit_execution_approved is True
        planned_execution_phases = self._planned_execution_phases(
            blocker_codes=blocker_codes,
            ready_for_future=ready_for_future,
        )
        plan_summary = self._plan_summary(
            approval=approval,
            planned_progress_steps=planned_progress_steps,
            planned_surface_steps=planned_surface_steps,
            planned_execution_phases=planned_execution_phases,
            rollback_checkpoints=rollback_checkpoints,
            audit_checkpoints=audit_checkpoints,
            ready_for_future=ready_for_future,
        )
        execution_plan_status, readiness_state = self._state(
            blocker_codes=blocker_codes,
            ready_for_future=ready_for_future,
        )

        result = SimuladoRuntimeCommitExecutionPlan(
            execution_plan_id=f"simulado-execution-plan:{approval.execution_approval_id}",
            user_id=user_id,
            source_execution_approval_id=approval.execution_approval_id,
            source_execution_guardrail_id=approval.source_execution_guardrail_id,
            source_commit_transaction_id=approval.source_commit_transaction_id,
            source_explicit_commit_id=approval.source_explicit_commit_id,
            source_commit_shell_id=approval.source_commit_shell_id,
            source_mutation_transaction_id=approval.source_mutation_transaction_id,
            source_explicit_apply_id=approval.source_explicit_apply_id,
            source_apply_shell_id=approval.source_apply_shell_id,
            source_application_id=approval.source_application_id,
            source_runtime_guardrail_id=approval.source_runtime_guardrail_id,
            source_integrated_result_id=approval.source_integrated_result_id,
            source_score_result_id=approval.source_score_result_id,
            source_progress_guardrail_id=approval.source_progress_guardrail_id,
            source_attempt_session_id=approval.source_attempt_session_id,
            source_simulado_blueprint_id=approval.source_simulado_blueprint_id,
            execution_plan_mode="execution_plan_only",
            execution_plan_status=execution_plan_status,
            readiness_state=readiness_state,
            plan_summary=plan_summary,
            planned_execution_phases=planned_execution_phases,
            planned_progress_steps=planned_progress_steps,
            planned_surface_steps=planned_surface_steps,
            rollback_checkpoints=rollback_checkpoints,
            audit_checkpoints=audit_checkpoints,
            blockers=self._blockers(approval, blocker_codes),
            validation_findings=self._findings(approval, ready_for_future=ready_for_future),
            warnings=self._warnings(approval, blocker_codes),
            execution_plan_created=True,
            execution_plan_ready_for_future_execution_review=ready_for_future,
            execution_allowed_now=False,
            execution_started=False,
            commit_execution_allowed=False,
            commit_execution_started=False,
            commit_executed=False,
            mutation_committed=False,
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
            no_final_pedagogical_update_event=True,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            metadata={
                "build_method": RUNTIME_COMMIT_EXECUTION_PLAN_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_runtime_commit_execution_plan(result, user_id=user_id)
        return result

    def get_execution_plan(
        self,
        source_execution_approval_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeCommitExecutionPlan | None:
        return self.repository.get_simulado_runtime_commit_execution_plan(
            source_execution_approval_id,
            user_id=user_id,
        )

    def get_execution_plan_by_id(
        self,
        execution_plan_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeCommitExecutionPlan | None:
        return self.repository.get_simulado_runtime_commit_execution_plan_by_id(
            execution_plan_id,
            user_id=user_id,
        )

    def _plan_summary(
        self,
        *,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
        planned_progress_steps: list[PlannedProgressExecutionStep],
        planned_surface_steps: list[PlannedSurfaceExecutionStep],
        planned_execution_phases: list[PlannedCommitExecutionPhase],
        rollback_checkpoints: list[RuntimeCommitRollbackCheckpoint],
        audit_checkpoints: list[RuntimeCommitAuditCheckpoint],
        ready_for_future: bool,
    ) -> RuntimeCommitExecutionPlanSummary:
        return RuntimeCommitExecutionPlanSummary(
            summary_id=f"runtime-commit-execution-plan-summary:{approval.execution_approval_id}",
            source_approval_present=True,
            source_approval_recorded=approval.explicit_execution_approval_recorded,
            source_approval_future_review_approved=approval.approved_for_future_commit_execution_review,
            source_approved_for_execution_now=approval.approved_for_execution_now,
            confirmations_satisfied=approval.confirmation_summary.all_confirmations_satisfied,
            progress_approval_count=len(approval.progress_execution_approvals),
            surface_approval_count=len(approval.surface_execution_approvals),
            approved_progress_step_count=sum(
                1 for item in planned_progress_steps if item.explicitly_approved_for_future_review
            ),
            approved_surface_step_count=sum(
                1 for item in planned_surface_steps if item.explicitly_approved_for_future_review
            ),
            planned_phase_count=len(planned_execution_phases),
            rollback_checkpoint_count=len(rollback_checkpoints),
            audit_checkpoint_count=len(audit_checkpoints),
            plan_ready_for_future_execution_review=ready_for_future,
            execution_allowed_now=False,
            unsafe_public_answer_key_exposure_detected=self._unsafe_public_answer_key_exposure_detected(
                approval
            ),
            unsafe_gabarito_exposure_detected=self._unsafe_gabarito_exposure_detected(approval),
            metadata={},
        )

    def _planned_progress_steps(
        self,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
    ) -> list[PlannedProgressExecutionStep]:
        steps: list[PlannedProgressExecutionStep] = []
        for item in approval.progress_execution_approvals:
            blockers = list(item.blockers)
            warnings = list(item.warnings)
            future_ready = bool(item.approved_for_future_commit_execution_review)
            if not future_ready:
                blockers.append("progress_step_blocked_by_approval_not_ready")
            blockers.append("progress_step_blocked_by_execution_now_not_allowed")
            steps.append(
                PlannedProgressExecutionStep(
                    step_id=f"planned-progress-step:{item.approval_id}",
                    source_progress_approval_id=item.approval_id,
                    source_check_id=item.source_check_id,
                    target_type=item.target_type,
                    delta_kind=item.delta_kind,
                    step_type=PROGRESS_STEP_TYPE_BY_DELTA.get(item.delta_kind, "unknown"),
                    step_status=(
                        "step_ready_for_future_execution_review"
                        if future_ready
                        else "step_blocked"
                    ),
                    explicitly_approved_for_future_review=future_ready,
                    execution_allowed=False,
                    executed=False,
                    blockers=self._dedupe(blockers),
                    warnings=self._dedupe(warnings),
                    metadata=dict(item.metadata),
                )
            )
        return steps

    def _planned_surface_steps(
        self,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
    ) -> list[PlannedSurfaceExecutionStep]:
        steps: list[PlannedSurfaceExecutionStep] = []
        for item in approval.surface_execution_approvals:
            blockers = list(item.blockers)
            warnings = list(item.warnings)
            future_ready = bool(item.approved_for_future_commit_execution_review)
            if not future_ready:
                blockers.append("surface_step_blocked_by_approval_not_ready")
            blockers.append("surface_step_blocked_by_execution_now_not_allowed")
            steps.append(
                PlannedSurfaceExecutionStep(
                    step_id=f"planned-surface-step:{item.approval_id}",
                    source_surface_approval_id=item.approval_id,
                    source_check_id=item.source_check_id,
                    surface_type=item.surface_type,
                    update_kind=item.update_kind,
                    step_type=SURFACE_STEP_TYPE_BY_SURFACE.get(item.surface_type, "unknown"),
                    step_status=(
                        "step_ready_for_future_execution_review"
                        if future_ready
                        else "step_blocked"
                    ),
                    explicitly_approved_for_future_review=future_ready,
                    execution_allowed=False,
                    executed=False,
                    blockers=self._dedupe(blockers),
                    warnings=self._dedupe(warnings),
                    metadata=dict(item.metadata),
                )
            )
        return steps

    def _rollback_checkpoints(
        self,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
        guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail | None,
    ) -> list[RuntimeCommitRollbackCheckpoint]:
        rollback_available = bool(guardrail and guardrail.rollback_readiness.rollback_available)
        rollback_verified = bool(guardrail and guardrail.rollback_readiness.rollback_verified)
        rollback_confirmed = bool(approval.confirmation_summary.rollback_execution_confirmed)
        return [
            RuntimeCommitRollbackCheckpoint(
                checkpoint_id=f"runtime-rollback-checkpoint:{approval.execution_approval_id}:plan",
                checkpoint_type="rollback_plan_available",
                required=True,
                available=rollback_available,
                verified=rollback_available,
                completed=False,
                execution_allowed=False,
                blockers=[] if rollback_available else ["rollback_checkpoint_missing_plan"],
                warnings=[],
                metadata={},
            ),
            RuntimeCommitRollbackCheckpoint(
                checkpoint_id=f"runtime-rollback-checkpoint:{approval.execution_approval_id}:verified",
                checkpoint_type="rollback_verified",
                required=True,
                available=rollback_available,
                verified=rollback_verified,
                completed=False,
                execution_allowed=False,
                blockers=[] if rollback_verified else ["rollback_checkpoint_not_verified"],
                warnings=[],
                metadata={},
            ),
            RuntimeCommitRollbackCheckpoint(
                checkpoint_id=f"runtime-rollback-checkpoint:{approval.execution_approval_id}:snapshot",
                checkpoint_type="rollback_snapshot_reference_safe",
                required=True,
                available=rollback_available,
                verified=rollback_verified,
                completed=False,
                execution_allowed=False,
                blockers=[] if rollback_available else ["rollback_snapshot_reference_unavailable"],
                warnings=[],
                metadata={},
            ),
            RuntimeCommitRollbackCheckpoint(
                checkpoint_id=f"runtime-rollback-checkpoint:{approval.execution_approval_id}:human",
                checkpoint_type="rollback_human_review",
                required=True,
                available=rollback_confirmed,
                verified=rollback_confirmed,
                completed=False,
                execution_allowed=False,
                blockers=[] if rollback_confirmed else ["rollback_human_review_not_confirmed"],
                warnings=[],
                metadata={},
            ),
        ]

    def _audit_checkpoints(
        self,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
    ) -> list[RuntimeCommitAuditCheckpoint]:
        return [
            self._audit_checkpoint(
                approval,
                checkpoint_type="final_execution_approval",
                satisfied=approval.confirmation_summary.final_execution_approval_confirmed,
            ),
            self._audit_checkpoint(
                approval,
                checkpoint_type="audit_confirmation",
                satisfied=approval.confirmation_summary.audit_confirmed,
            ),
            self._audit_checkpoint(
                approval,
                checkpoint_type="runtime_surface_confirmation",
                satisfied=approval.confirmation_summary.runtime_surface_confirmed,
            ),
            self._audit_checkpoint(
                approval,
                checkpoint_type="public_answer_key_absence_confirmation",
                satisfied=approval.confirmation_summary.public_answer_key_absence_confirmed,
            ),
            self._audit_checkpoint(
                approval,
                checkpoint_type="human_review_confirmation",
                satisfied=approval.confirmation_summary.human_review_confirmed,
            ),
            self._audit_checkpoint(
                approval,
                checkpoint_type="no_commit_execution_confirmation",
                satisfied=approval.no_commit_execution is True,
            ),
        ]

    def _audit_checkpoint(
        self,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
        *,
        checkpoint_type: str,
        satisfied: bool,
    ) -> RuntimeCommitAuditCheckpoint:
        return RuntimeCommitAuditCheckpoint(
            checkpoint_id=f"runtime-audit-checkpoint:{approval.execution_approval_id}:{checkpoint_type}",
            checkpoint_type=checkpoint_type,
            required=True,
            satisfied=satisfied,
            completed=False,
            execution_allowed=False,
            blockers=[] if satisfied else [f"{checkpoint_type}_not_satisfied"],
            warnings=[],
            metadata={},
        )

    def _planned_execution_phases(
        self,
        *,
        blocker_codes: list[str],
        ready_for_future: bool,
    ) -> list[PlannedCommitExecutionPhase]:
        phases: list[PlannedCommitExecutionPhase] = []
        for order, phase_type in enumerate(PHASE_TYPES, start=1):
            phase_blockers = self._phase_blockers(phase_type, blocker_codes)
            if ready_for_future:
                status = "phase_ready_for_future_execution_review"
            elif phase_blockers:
                status = "phase_blocked"
            else:
                status = "phase_needs_review"
            phases.append(
                PlannedCommitExecutionPhase(
                    phase_id=f"runtime-execution-phase:{phase_type}",
                    phase_order=order,
                    phase_type=phase_type,
                    phase_status=status,
                    description=phase_type.replace("_", " "),
                    required=True,
                    completed=False,
                    execution_allowed=False,
                    executed=False,
                    blockers=phase_blockers,
                    warnings=[],
                    metadata={},
                )
            )
        return phases

    def _phase_blockers(self, phase_type: str, blocker_codes: list[str]) -> list[str]:
        phase_to_codes = {
            "preflight_validation": {
                "blocked_by_execution_approval_not_approved",
                "blocked_by_confirmations_incomplete",
                "blocked_by_execution_disabled",
                "blocked_by_public_answer_key_exposure_forbidden",
            },
            "rollback_checkpoint_validation": {"blocked_by_rollback_checkpoints_incomplete"},
            "progress_step_review": {"blocked_by_progress_approvals_not_ready"},
            "surface_step_review": {"blocked_by_surface_approvals_not_ready"},
            "audit_checkpoint_review": {"blocked_by_audit_checkpoints_incomplete"},
            "final_execution_review": set(blocker_codes),
        }
        allowed = phase_to_codes.get(phase_type, set())
        return [code for code in blocker_codes if code in allowed]

    def _blocker_codes(
        self,
        *,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
        planned_progress_steps: list[PlannedProgressExecutionStep],
        planned_surface_steps: list[PlannedSurfaceExecutionStep],
        rollback_checkpoints: list[RuntimeCommitRollbackCheckpoint],
        audit_checkpoints: list[RuntimeCommitAuditCheckpoint],
    ) -> list[str]:
        blocker_codes: list[str] = []
        is_approve_path = (
            approval.decision_summary.decision_type
            == "approve_for_future_commit_execution_review"
        )
        if self._unsafe_public_answer_key_exposure_detected(approval):
            blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        if bool(approval.metadata.get("execution_disabled")):
            blocker_codes.append("blocked_by_execution_disabled")
        if is_approve_path and not approval.confirmation_summary.all_confirmations_satisfied:
            blocker_codes.append("blocked_by_confirmations_incomplete")
        if is_approve_path and any(
            not item.explicitly_approved_for_future_review for item in planned_progress_steps
        ):
            blocker_codes.append("blocked_by_progress_approvals_not_ready")
        if is_approve_path and any(
            not item.explicitly_approved_for_future_review for item in planned_surface_steps
        ):
            blocker_codes.append("blocked_by_surface_approvals_not_ready")
        if is_approve_path and any(
            checkpoint.required and not (checkpoint.available and checkpoint.verified)
            for checkpoint in rollback_checkpoints
        ):
            blocker_codes.append("blocked_by_rollback_checkpoints_incomplete")
        if is_approve_path and any(
            checkpoint.required and not checkpoint.satisfied for checkpoint in audit_checkpoints
        ):
            blocker_codes.append("blocked_by_audit_checkpoints_incomplete")
        if not approval.explicit_execution_approved:
            blocker_codes.append("blocked_by_execution_approval_not_approved")
        return self._dedupe(blocker_codes)

    def _state(
        self,
        *,
        blocker_codes: list[str],
        ready_for_future: bool,
    ) -> tuple[str, str]:
        if ready_for_future:
            return (
                "ready_for_future_controlled_execution_review",
                "ready_for_future_controlled_execution_review",
            )
        if blocker_codes:
            return ("execution_plan_blocked", blocker_codes[0])
        return ("execution_plan_needs_review", "execution_plan_needs_review")

    def _blockers(
        self,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
        blocker_codes: list[str],
    ) -> list[RuntimeCommitExecutionPlanBlocker]:
        messages = {
            "blocked_by_execution_approval_not_approved": "Source explicit execution approval is not approved for future review.",
            "blocked_by_confirmations_incomplete": "Source explicit execution approval confirmations are incomplete.",
            "blocked_by_progress_approvals_not_ready": "Progress execution approvals are not ready for future review.",
            "blocked_by_surface_approvals_not_ready": "Surface execution approvals are not ready for future review.",
            "blocked_by_rollback_checkpoints_incomplete": "Rollback checkpoints remain incomplete.",
            "blocked_by_audit_checkpoints_incomplete": "Audit checkpoints remain incomplete.",
            "blocked_by_execution_disabled": "Execution remains disabled for this plan artifact.",
            "blocked_by_public_answer_key_exposure_forbidden": "Unsafe public answer key exposure prevents plan readiness.",
        }
        return [
            RuntimeCommitExecutionPlanBlocker(
                blocker_id=f"runtime-execution-plan-blocker:{approval.execution_approval_id}:{code}",
                code=code,
                message=messages.get(code, code.replace("_", " ")),
                related_artifact_type="simulado_explicit_runtime_commit_execution_approval",
                related_artifact_id=approval.execution_approval_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
        *,
        ready_for_future: bool,
    ) -> list[RuntimeCommitExecutionPlanValidationFinding]:
        return [
            RuntimeCommitExecutionPlanValidationFinding(
                finding_id=f"runtime-execution-plan-finding:{approval.execution_approval_id}:future-review",
                code=(
                    "execution_plan_ready_for_future_review"
                    if ready_for_future
                    else "execution_plan_not_ready_for_future_review"
                ),
                message="Execution plan remains bounded to future controlled execution review only.",
                related_artifact_type="simulado_explicit_runtime_commit_execution_approval",
                related_artifact_id=approval.execution_approval_id,
                metadata={},
            )
        ]

    def _warnings(
        self,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
        blocker_codes: list[str],
    ) -> list[RuntimeCommitExecutionPlanWarning]:
        warnings = [
            RuntimeCommitExecutionPlanWarning(
                code="execution_plan_dry_run_only",
                message="This execution plan is a bounded non-executing dry-run artifact.",
                related_artifact_type="simulado_explicit_runtime_commit_execution_approval",
                related_artifact_id=approval.execution_approval_id,
                metadata={},
            )
        ]
        if blocker_codes:
            warnings.append(
                RuntimeCommitExecutionPlanWarning(
                    code="execution_plan_contains_blockers",
                    message="Future controlled execution review still depends on unresolved blockers.",
                    related_artifact_type="simulado_explicit_runtime_commit_execution_approval",
                    related_artifact_id=approval.execution_approval_id,
                    metadata={"blocker_count": len(blocker_codes)},
                )
            )
        return warnings

    def _unsafe_public_answer_key_exposure_detected(
        self,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
    ) -> bool:
        if approval.answer_key_publicly_exposed or approval.gabarito_publicly_exposed:
            return True
        if not approval.confirmation_summary.public_answer_key_absence_confirmed:
            return False
        if approval.readiness_state == "blocked_by_public_answer_key_exposure_forbidden":
            return True
        return any(
            blocker.code == "blocked_by_public_answer_key_exposure_forbidden"
            for blocker in approval.blockers
        )

    def _unsafe_gabarito_exposure_detected(
        self,
        approval: SimuladoExplicitRuntimeCommitExecutionApproval,
    ) -> bool:
        return approval.gabarito_publicly_exposed

    def _dedupe(self, items: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for item in items:
            if item in seen:
                continue
            ordered.append(item)
            seen.add(item)
        return ordered
