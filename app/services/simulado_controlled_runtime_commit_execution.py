from __future__ import annotations

from app.domain.models import (
    ControlledAuditVerificationRecord,
    ControlledCommitExecutionAuditEntry,
    ControlledCommitExecutionBlocker,
    ControlledCommitExecutionSummary,
    ControlledCommitExecutionValidationFinding,
    ControlledCommitExecutionWarning,
    ControlledPhaseExecutionRecord,
    ControlledProgressStepExecutionRecord,
    ControlledRollbackVerificationRecord,
    ControlledSurfaceStepExecutionRecord,
    SimuladoControlledRuntimeCommitExecution,
    SimuladoRuntimeCommitExecutionPlan,
)
from app.repositories.json_store import JsonStudyRepository


CONTROLLED_RUNTIME_COMMIT_EXECUTION_BUILD_METHOD = (
    "heuristic_simulado_controlled_runtime_commit_execution_builder"
)


class SimuladoControlledRuntimeCommitExecutionService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_controlled_execution(
        self,
        source_execution_plan_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeCommitExecution | None:
        if user_id is None:
            return None

        execution_plan = self.repository.get_simulado_runtime_commit_execution_plan_by_id(
            source_execution_plan_id,
            user_id=user_id,
        )
        if execution_plan is None:
            return None

        existing = self.repository.get_simulado_controlled_runtime_commit_execution(
            source_execution_plan_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        phase_records = self._phase_execution_records(execution_plan)
        progress_records = self._progress_step_execution_records(execution_plan)
        surface_records = self._surface_step_execution_records(execution_plan)
        rollback_records = self._rollback_verification_records(execution_plan)
        audit_records = self._audit_verification_records(execution_plan)
        blocker_codes = self._blocker_codes(
            execution_plan=execution_plan,
            phase_records=phase_records,
            progress_records=progress_records,
            surface_records=surface_records,
            rollback_records=rollback_records,
            audit_records=audit_records,
        )
        execution_status, readiness_state = self._state(
            execution_plan=execution_plan,
            blocker_codes=blocker_codes,
        )
        execution_summary = self._summary(
            execution_plan=execution_plan,
            phase_records=phase_records,
            progress_records=progress_records,
            surface_records=surface_records,
            rollback_records=rollback_records,
            audit_records=audit_records,
        )

        result = SimuladoControlledRuntimeCommitExecution(
            controlled_execution_id=(
                f"simulado-controlled-execution:{execution_plan.execution_plan_id}"
            ),
            user_id=user_id,
            source_execution_plan_id=execution_plan.execution_plan_id,
            source_execution_approval_id=execution_plan.source_execution_approval_id,
            source_execution_guardrail_id=execution_plan.source_execution_guardrail_id,
            source_commit_transaction_id=execution_plan.source_commit_transaction_id,
            source_explicit_commit_id=execution_plan.source_explicit_commit_id,
            source_commit_shell_id=execution_plan.source_commit_shell_id,
            source_mutation_transaction_id=execution_plan.source_mutation_transaction_id,
            source_explicit_apply_id=execution_plan.source_explicit_apply_id,
            source_apply_shell_id=execution_plan.source_apply_shell_id,
            source_application_id=execution_plan.source_application_id,
            source_runtime_guardrail_id=execution_plan.source_runtime_guardrail_id,
            source_integrated_result_id=execution_plan.source_integrated_result_id,
            source_score_result_id=execution_plan.source_score_result_id,
            source_progress_guardrail_id=execution_plan.source_progress_guardrail_id,
            source_attempt_session_id=execution_plan.source_attempt_session_id,
            source_simulado_blueprint_id=execution_plan.source_simulado_blueprint_id,
            execution_mode="controlled_execution_dry_run",
            execution_status=execution_status,
            readiness_state=readiness_state,
            execution_summary=execution_summary,
            phase_execution_records=phase_records,
            progress_step_execution_records=progress_records,
            surface_step_execution_records=surface_records,
            rollback_verification_records=rollback_records,
            audit_verification_records=audit_records,
            audit_trail=self._audit_trail(
                execution_plan=execution_plan,
                execution_status=execution_status,
            ),
            blockers=self._blockers(execution_plan, blocker_codes),
            validation_findings=self._findings(
                execution_plan=execution_plan,
                blocker_codes=blocker_codes,
            ),
            warnings=self._warnings(execution_plan, blocker_codes),
            controlled_execution_created=True,
            execution_started=False,
            execution_completed=False,
            execution_succeeded=False,
            execution_failed=False,
            execution_allowed_now=False,
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
            final_pedagogical_update_event_created=False,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            metadata={
                "build_method": CONTROLLED_RUNTIME_COMMIT_EXECUTION_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_controlled_runtime_commit_execution(
            result,
            user_id=user_id,
        )
        return result

    def get_controlled_execution(
        self,
        source_execution_plan_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeCommitExecution | None:
        return self.repository.get_simulado_controlled_runtime_commit_execution(
            source_execution_plan_id,
            user_id=user_id,
        )

    def get_controlled_execution_by_id(
        self,
        controlled_execution_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeCommitExecution | None:
        return self.repository.get_simulado_controlled_runtime_commit_execution_by_id(
            controlled_execution_id,
            user_id=user_id,
        )

    def _summary(
        self,
        *,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
        phase_records: list[ControlledPhaseExecutionRecord],
        progress_records: list[ControlledProgressStepExecutionRecord],
        surface_records: list[ControlledSurfaceStepExecutionRecord],
        rollback_records: list[ControlledRollbackVerificationRecord],
        audit_records: list[ControlledAuditVerificationRecord],
    ) -> ControlledCommitExecutionSummary:
        return ControlledCommitExecutionSummary(
            summary_id=(
                f"controlled-runtime-commit-execution-summary:{execution_plan.execution_plan_id}"
            ),
            source_plan_present=True,
            source_plan_created=execution_plan.execution_plan_created,
            source_plan_ready_for_future_execution_review=(
                execution_plan.execution_plan_ready_for_future_execution_review
            ),
            source_execution_allowed_now=execution_plan.execution_allowed_now,
            source_execution_started=execution_plan.execution_started,
            source_commit_executed=execution_plan.commit_executed,
            planned_phase_count=len(execution_plan.planned_execution_phases),
            evaluated_phase_count=len(phase_records),
            blocked_phase_count=sum(1 for item in phase_records if item.blocked),
            planned_progress_step_count=len(execution_plan.planned_progress_steps),
            evaluated_progress_step_count=len(progress_records),
            blocked_progress_step_count=sum(1 for item in progress_records if item.blocked),
            planned_surface_step_count=len(execution_plan.planned_surface_steps),
            evaluated_surface_step_count=len(surface_records),
            blocked_surface_step_count=sum(1 for item in surface_records if item.blocked),
            rollback_verification_count=len(rollback_records),
            rollback_blocked_count=sum(1 for item in rollback_records if item.blocked),
            audit_verification_count=len(audit_records),
            audit_blocked_count=sum(1 for item in audit_records if item.blocked),
            controlled_execution_dry_run_complete=True,
            real_execution_performed=False,
            mutation_commit_performed=False,
            runtime_application_performed=False,
            unsafe_public_answer_key_exposure_detected=(
                self._unsafe_public_answer_key_exposure_detected(execution_plan)
            ),
            unsafe_gabarito_exposure_detected=self._unsafe_gabarito_exposure_detected(
                execution_plan
            ),
            metadata={},
        )

    def _phase_execution_records(
        self,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
    ) -> list[ControlledPhaseExecutionRecord]:
        records: list[ControlledPhaseExecutionRecord] = []
        for item in execution_plan.planned_execution_phases:
            blocked = item.phase_status == "phase_blocked"
            if item.phase_status == "phase_ready_for_future_execution_review":
                status = "record_ready_for_future_execution_review"
            elif item.phase_status == "phase_needs_review":
                status = "record_needs_review"
                blocked = True
            elif blocked:
                status = "record_blocked"
            else:
                status = "record_evaluated"
            blockers = list(item.blockers)
            if blocked and "phase_execution_blocked_by_phase_not_ready" not in blockers:
                blockers.append("phase_execution_blocked_by_phase_not_ready")
            records.append(
                ControlledPhaseExecutionRecord(
                    record_id=f"controlled-phase-execution-record:{item.phase_id}",
                    source_phase_id=item.phase_id,
                    phase_type=item.phase_type,
                    phase_order=item.phase_order,
                    source_phase_status=item.phase_status,
                    execution_record_status=status,
                    evaluated=True,
                    execution_allowed=False,
                    executed=False,
                    blocked=blocked,
                    blockers=self._dedupe(blockers),
                    warnings=list(item.warnings),
                    metadata=dict(item.metadata),
                )
            )
        return records

    def _progress_step_execution_records(
        self,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
    ) -> list[ControlledProgressStepExecutionRecord]:
        records: list[ControlledProgressStepExecutionRecord] = []
        for item in execution_plan.planned_progress_steps:
            blocked = item.step_status == "step_blocked"
            if item.step_status == "step_ready_for_future_execution_review":
                status = "record_ready_for_future_execution_review"
            elif item.step_status == "step_needs_review":
                status = "record_needs_review"
                blocked = True
            elif blocked:
                status = "record_blocked"
            else:
                status = "record_evaluated"
            blockers = list(item.blockers)
            if blocked and "progress_execution_blocked_by_step_not_allowed" not in blockers:
                blockers.append("progress_execution_blocked_by_step_not_allowed")
            records.append(
                ControlledProgressStepExecutionRecord(
                    record_id=f"controlled-progress-step-execution-record:{item.step_id}",
                    source_step_id=item.step_id,
                    source_progress_approval_id=item.source_progress_approval_id,
                    target_type=item.target_type,
                    delta_kind=item.delta_kind,
                    source_step_status=item.step_status,
                    execution_record_status=status,
                    evaluated=True,
                    execution_allowed=False,
                    executed=False,
                    blocked=blocked,
                    proposed_delta_summary={
                        "target_type": item.target_type,
                        "delta_kind": item.delta_kind,
                        "explicitly_approved_for_future_review": (
                            item.explicitly_approved_for_future_review
                        ),
                    },
                    blockers=self._dedupe(blockers),
                    warnings=list(item.warnings),
                    metadata=dict(item.metadata),
                )
            )
        return records

    def _surface_step_execution_records(
        self,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
    ) -> list[ControlledSurfaceStepExecutionRecord]:
        records: list[ControlledSurfaceStepExecutionRecord] = []
        for item in execution_plan.planned_surface_steps:
            blocked = item.step_status == "step_blocked"
            if item.step_status == "step_ready_for_future_execution_review":
                status = "record_ready_for_future_execution_review"
            elif item.step_status == "step_needs_review":
                status = "record_needs_review"
                blocked = True
            elif blocked:
                status = "record_blocked"
            else:
                status = "record_evaluated"
            blockers = list(item.blockers)
            if blocked and "surface_execution_blocked_by_step_not_allowed" not in blockers:
                blockers.append("surface_execution_blocked_by_step_not_allowed")
            records.append(
                ControlledSurfaceStepExecutionRecord(
                    record_id=f"controlled-surface-step-execution-record:{item.step_id}",
                    source_step_id=item.step_id,
                    source_surface_approval_id=item.source_surface_approval_id,
                    surface_type=item.surface_type,
                    update_kind=item.update_kind,
                    source_step_status=item.step_status,
                    execution_record_status=status,
                    evaluated=True,
                    execution_allowed=False,
                    executed=False,
                    blocked=blocked,
                    proposed_surface_update_summary={
                        "surface_type": item.surface_type,
                        "update_kind": item.update_kind,
                        "explicitly_approved_for_future_review": (
                            item.explicitly_approved_for_future_review
                        ),
                    },
                    blockers=self._dedupe(blockers),
                    warnings=list(item.warnings),
                    metadata=dict(item.metadata),
                )
            )
        return records

    def _rollback_verification_records(
        self,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
    ) -> list[ControlledRollbackVerificationRecord]:
        records: list[ControlledRollbackVerificationRecord] = []
        for item in execution_plan.rollback_checkpoints:
            blocked = item.required and not (item.available and item.verified)
            blockers = list(item.blockers)
            if blocked and "rollback_verification_blocked_by_checkpoint_not_ready" not in blockers:
                blockers.append("rollback_verification_blocked_by_checkpoint_not_ready")
            records.append(
                ControlledRollbackVerificationRecord(
                    record_id=f"controlled-rollback-verification-record:{item.checkpoint_id}",
                    source_checkpoint_id=item.checkpoint_id,
                    checkpoint_type=item.checkpoint_type,
                    required=item.required,
                    available=item.available,
                    verified=item.verified,
                    evaluated=True,
                    execution_allowed=False,
                    executed=False,
                    blocked=blocked,
                    blockers=self._dedupe(blockers),
                    warnings=list(item.warnings),
                    metadata=dict(item.metadata),
                )
            )
        return records

    def _audit_verification_records(
        self,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
    ) -> list[ControlledAuditVerificationRecord]:
        records: list[ControlledAuditVerificationRecord] = []
        for item in execution_plan.audit_checkpoints:
            blocked = item.required and not item.satisfied
            blockers = list(item.blockers)
            if blocked and "audit_verification_blocked_by_checkpoint_not_ready" not in blockers:
                blockers.append("audit_verification_blocked_by_checkpoint_not_ready")
            records.append(
                ControlledAuditVerificationRecord(
                    record_id=f"controlled-audit-verification-record:{item.checkpoint_id}",
                    source_checkpoint_id=item.checkpoint_id,
                    checkpoint_type=item.checkpoint_type,
                    required=item.required,
                    satisfied=item.satisfied,
                    evaluated=True,
                    execution_allowed=False,
                    executed=False,
                    blocked=blocked,
                    blockers=self._dedupe(blockers),
                    warnings=list(item.warnings),
                    metadata=dict(item.metadata),
                )
            )
        return records

    def _audit_trail(
        self,
        *,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
        execution_status: str,
    ) -> list[ControlledCommitExecutionAuditEntry]:
        return [
            ControlledCommitExecutionAuditEntry(
                audit_id=f"controlled-commit-execution-audit:{execution_plan.execution_plan_id}:created",
                event_type="controlled_execution_created",
                actor_user_id=execution_plan.user_id,
                message="Controlled runtime commit execution dry-run artifact created.",
                metadata={},
            ),
            ControlledCommitExecutionAuditEntry(
                audit_id=f"controlled-commit-execution-audit:{execution_plan.execution_plan_id}:status",
                event_type=execution_status,
                actor_user_id=execution_plan.user_id,
                message="Controlled runtime commit execution remains non-executing.",
                metadata={},
            ),
            ControlledCommitExecutionAuditEntry(
                audit_id=f"controlled-commit-execution-audit:{execution_plan.execution_plan_id}:no-commit",
                event_type="no_commit_execution",
                actor_user_id=execution_plan.user_id,
                message="No commit execution was performed.",
                metadata={},
            ),
            ControlledCommitExecutionAuditEntry(
                audit_id=f"controlled-commit-execution-audit:{execution_plan.execution_plan_id}:no-mutation",
                event_type="no_mutation_commit",
                actor_user_id=execution_plan.user_id,
                message="No mutation commit was performed.",
                metadata={},
            ),
            ControlledCommitExecutionAuditEntry(
                audit_id=f"controlled-commit-execution-audit:{execution_plan.execution_plan_id}:no-runtime",
                event_type="no_runtime_application",
                actor_user_id=execution_plan.user_id,
                message="No runtime application was performed.",
                metadata={},
            ),
            ControlledCommitExecutionAuditEntry(
                audit_id=f"controlled-commit-execution-audit:{execution_plan.execution_plan_id}:no-progress",
                event_type="no_progress_mutation",
                actor_user_id=execution_plan.user_id,
                message="No progress mutation was performed.",
                metadata={},
            ),
            ControlledCommitExecutionAuditEntry(
                audit_id=f"controlled-commit-execution-audit:{execution_plan.execution_plan_id}:no-final",
                event_type="no_final_pedagogical_update_event",
                actor_user_id=execution_plan.user_id,
                message="No final pedagogical update event was created.",
                metadata={},
            ),
        ]

    def _blocker_codes(
        self,
        *,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
        phase_records: list[ControlledPhaseExecutionRecord],
        progress_records: list[ControlledProgressStepExecutionRecord],
        surface_records: list[ControlledSurfaceStepExecutionRecord],
        rollback_records: list[ControlledRollbackVerificationRecord],
        audit_records: list[ControlledAuditVerificationRecord],
    ) -> list[str]:
        if self._unsafe_public_answer_key_exposure_detected(execution_plan):
            return ["blocked_by_public_answer_key_exposure_forbidden"]
        if bool(execution_plan.metadata.get("execution_disabled")) or any(
            blocker.code == "blocked_by_execution_disabled"
            for blocker in execution_plan.blockers
        ):
            return ["blocked_by_execution_disabled"]
        if (
            not execution_plan.execution_plan_ready_for_future_execution_review
            and execution_plan.readiness_state
            in {
                "blocked_by_execution_approval_not_approved",
                "execution_plan_needs_review",
            }
        ):
            return ["blocked_by_execution_plan_not_ready"]
        if any(item.blocked for item in rollback_records):
            return ["blocked_by_rollback_verification_failed"]
        if any(item.blocked for item in audit_records):
            return ["blocked_by_audit_verification_failed"]
        if any(item.blocked for item in progress_records):
            return ["blocked_by_progress_steps_not_executable"]
        if any(item.blocked for item in surface_records):
            return ["blocked_by_surface_steps_not_executable"]
        if any(item.blocked for item in phase_records):
            return ["blocked_by_phases_not_executable"]
        if not execution_plan.execution_plan_ready_for_future_execution_review:
            return ["blocked_by_execution_plan_not_ready"]
        if not execution_plan.execution_allowed_now:
            return ["blocked_by_execution_allowed_now_false"]
        return []

    def _state(
        self,
        *,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
        blocker_codes: list[str],
    ) -> tuple[str, str]:
        if blocker_codes:
            return ("execution_blocked", blocker_codes[0])
        if execution_plan.execution_plan_ready_for_future_execution_review:
            return (
                "execution_needs_review",
                "dry_run_ready_for_future_execution_review",
            )
        return ("execution_not_started", "controlled_execution_needs_review")

    def _blockers(
        self,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
        blocker_codes: list[str],
    ) -> list[ControlledCommitExecutionBlocker]:
        messages = {
            "blocked_by_execution_plan_not_ready": "Source execution plan is not ready for controlled dry-run review.",
            "blocked_by_execution_allowed_now_false": "Source execution plan does not allow execution now.",
            "blocked_by_phases_not_executable": "Planned execution phases remain non-executable.",
            "blocked_by_progress_steps_not_executable": "Planned progress execution steps remain non-executable.",
            "blocked_by_surface_steps_not_executable": "Planned surface execution steps remain non-executable.",
            "blocked_by_rollback_verification_failed": "Rollback verification remains incomplete.",
            "blocked_by_audit_verification_failed": "Audit verification remains incomplete.",
            "blocked_by_execution_disabled": "Controlled execution remains disabled for this dry-run artifact.",
            "blocked_by_public_answer_key_exposure_forbidden": "Unsafe public answer key exposure prevents controlled execution review.",
        }
        return [
            ControlledCommitExecutionBlocker(
                blocker_id=(
                    f"controlled-commit-execution-blocker:{execution_plan.execution_plan_id}:{code}"
                ),
                code=code,
                message=messages.get(code, code.replace("_", " ")),
                related_artifact_type="simulado_runtime_commit_execution_plan",
                related_artifact_id=execution_plan.execution_plan_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        *,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
        blocker_codes: list[str],
    ) -> list[ControlledCommitExecutionValidationFinding]:
        return [
            ControlledCommitExecutionValidationFinding(
                finding_id=(
                    f"controlled-commit-execution-finding:{execution_plan.execution_plan_id}:dry-run"
                ),
                code=(
                    "controlled_execution_dry_run_blocked"
                    if blocker_codes
                    else "controlled_execution_dry_run_ready_for_review"
                ),
                message="Controlled runtime commit execution remains a dry-run preview only.",
                related_artifact_type="simulado_runtime_commit_execution_plan",
                related_artifact_id=execution_plan.execution_plan_id,
                metadata={"blocker_count": len(blocker_codes)},
            )
        ]

    def _warnings(
        self,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
        blocker_codes: list[str],
    ) -> list[ControlledCommitExecutionWarning]:
        warnings = [
            ControlledCommitExecutionWarning(
                code="controlled_execution_dry_run_only",
                message="This artifact previews controlled execution outcomes without executing commit.",
                related_artifact_type="simulado_runtime_commit_execution_plan",
                related_artifact_id=execution_plan.execution_plan_id,
                metadata={},
            )
        ]
        if blocker_codes:
            warnings.append(
                ControlledCommitExecutionWarning(
                    code="controlled_execution_contains_blockers",
                    message="Controlled execution preview remains bounded by unresolved blockers.",
                    related_artifact_type="simulado_runtime_commit_execution_plan",
                    related_artifact_id=execution_plan.execution_plan_id,
                    metadata={"blocker_count": len(blocker_codes)},
                )
            )
        return warnings

    def _unsafe_public_answer_key_exposure_detected(
        self,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
    ) -> bool:
        if execution_plan.answer_key_publicly_exposed or execution_plan.gabarito_publicly_exposed:
            return True
        if execution_plan.readiness_state == "blocked_by_public_answer_key_exposure_forbidden":
            return True
        return any(
            blocker.code == "blocked_by_public_answer_key_exposure_forbidden"
            for blocker in execution_plan.blockers
        )

    def _unsafe_gabarito_exposure_detected(
        self,
        execution_plan: SimuladoRuntimeCommitExecutionPlan,
    ) -> bool:
        return execution_plan.gabarito_publicly_exposed

    def _dedupe(self, items: list[str]) -> list[str]:
        ordered: list[str] = []
        seen: set[str] = set()
        for item in items:
            if item in seen:
                continue
            ordered.append(item)
            seen.add(item)
        return ordered
