from __future__ import annotations

from app.domain.models import (
    CommitExecutionAuditRequirement,
    CommitExecutionGuardrailAuditEntry,
    CommitExecutionGuardrailBlocker,
    CommitExecutionGuardrailValidationFinding,
    CommitExecutionGuardrailWarning,
    CommitExecutionReadinessSummary,
    CommitRollbackExecutionReadiness,
    CommitTransactionSafetyAssessment,
    PlannedProgressCommitExecutionCheck,
    PlannedSurfaceCommitExecutionCheck,
    RuntimeSurfaceRiskSummary,
    SimuladoControlledRuntimeCommitExecutionGuardrail,
    SimuladoRuntimeMutationCommitTransaction,
)
from app.repositories.json_store import JsonStudyRepository


CONTROLLED_COMMIT_EXECUTION_GUARDRAIL_BUILD_METHOD = (
    "heuristic_simulado_controlled_runtime_commit_execution_guardrail_builder"
)


class SimuladoControlledRuntimeCommitExecutionGuardrailService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_execution_guardrail(
        self,
        source_commit_transaction_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeCommitExecutionGuardrail | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_controlled_commit_execution_guardrail(
            source_commit_transaction_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        transaction = self.repository.get_simulado_runtime_mutation_commit_transaction_by_id(
            source_commit_transaction_id,
            user_id=user_id,
        )
        if transaction is None:
            return None

        progress_commit_checks = self._progress_commit_checks(transaction)
        surface_commit_checks = self._surface_commit_checks(transaction)
        rollback_readiness = self._rollback_readiness(transaction)
        audit_requirements = self._audit_requirements(transaction)
        readiness_summary = self._readiness_summary(
            transaction=transaction,
            progress_commit_checks=progress_commit_checks,
            surface_commit_checks=surface_commit_checks,
            rollback_readiness=rollback_readiness,
            audit_requirements=audit_requirements,
        )
        transaction_safety_assessment = self._transaction_safety_assessment(transaction)
        runtime_surface_risk_summary = self._runtime_surface_risk_summary(
            transaction=transaction,
            surface_commit_checks=surface_commit_checks,
        )
        blocker_codes = self._blocker_codes(
            transaction=transaction,
            readiness_summary=readiness_summary,
            rollback_readiness=rollback_readiness,
            progress_commit_checks=progress_commit_checks,
            surface_commit_checks=surface_commit_checks,
            audit_requirements=audit_requirements,
        )
        execution_guardrail_status, readiness_state = self._state(blocker_codes)

        result = SimuladoControlledRuntimeCommitExecutionGuardrail(
            execution_guardrail_id=(
                f"simulado-commit-execution-guardrail:{transaction.commit_transaction_id}"
            ),
            user_id=user_id,
            source_commit_transaction_id=transaction.commit_transaction_id,
            source_explicit_commit_id=transaction.source_explicit_commit_id,
            source_commit_shell_id=transaction.source_commit_shell_id,
            source_mutation_transaction_id=transaction.source_mutation_transaction_id,
            source_explicit_apply_id=transaction.source_explicit_apply_id,
            source_apply_shell_id=transaction.source_apply_shell_id,
            source_application_id=transaction.source_application_id,
            source_runtime_guardrail_id=transaction.source_runtime_guardrail_id,
            source_integrated_result_id=transaction.source_integrated_result_id,
            source_score_result_id=transaction.source_score_result_id,
            source_progress_guardrail_id=transaction.source_progress_guardrail_id,
            source_attempt_session_id=transaction.source_attempt_session_id,
            source_simulado_blueprint_id=transaction.source_simulado_blueprint_id,
            execution_guardrail_mode="execution_guardrail_only",
            execution_guardrail_status=execution_guardrail_status,
            readiness_state=readiness_state,
            readiness_summary=readiness_summary,
            transaction_safety_assessment=transaction_safety_assessment,
            rollback_readiness=rollback_readiness,
            progress_commit_checks=progress_commit_checks,
            surface_commit_checks=surface_commit_checks,
            runtime_surface_risk_summary=runtime_surface_risk_summary,
            audit_requirements=audit_requirements,
            audit_trail=self._audit_trail(
                transaction=transaction,
                blocker_codes=blocker_codes,
                actor_user_id=user_id,
            ),
            blockers=self._blockers(transaction, blocker_codes),
            validation_findings=self._findings(transaction),
            warnings=self._warnings(transaction),
            execution_guardrail_created=True,
            commit_execution_allowed=False,
            commit_execution_started=False,
            commit_executed=False,
            mutation_committed=False,
            commit_transaction_valid_for_execution=False,
            commit_execution_ready=False,
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
                "build_method": CONTROLLED_COMMIT_EXECUTION_GUARDRAIL_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_controlled_commit_execution_guardrail(result, user_id=user_id)
        return result

    def get_execution_guardrail(
        self,
        source_commit_transaction_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeCommitExecutionGuardrail | None:
        return self.repository.get_simulado_controlled_commit_execution_guardrail(
            source_commit_transaction_id,
            user_id=user_id,
        )

    def get_execution_guardrail_by_id(
        self,
        execution_guardrail_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeCommitExecutionGuardrail | None:
        return self.repository.get_simulado_controlled_commit_execution_guardrail_by_id(
            execution_guardrail_id,
            user_id=user_id,
        )

    def _readiness_summary(
        self,
        *,
        transaction: SimuladoRuntimeMutationCommitTransaction,
        progress_commit_checks: list[PlannedProgressCommitExecutionCheck],
        surface_commit_checks: list[PlannedSurfaceCommitExecutionCheck],
        rollback_readiness: CommitRollbackExecutionReadiness,
        audit_requirements: list[CommitExecutionAuditRequirement],
    ) -> CommitExecutionReadinessSummary:
        final_execution_approval_present = bool(
            transaction.metadata.get("execution_guardrail_final_execution_approval_present", False)
        )
        all_audit_requirements_satisfied = all(item.satisfied for item in audit_requirements if item.requirement_type != "final_execution_approval")
        executable_progress_count = sum(
            1 for item in progress_commit_checks if item.execution_check_state == "progress_commit_ready_for_future_execution_review"
        )
        executable_surface_count = sum(
            1 for item in surface_commit_checks if item.execution_check_state == "surface_commit_ready_for_future_execution_review"
        )
        return CommitExecutionReadinessSummary(
            summary_id=f"commit-execution-readiness:{transaction.commit_transaction_id}",
            source_commit_transaction_present=True,
            source_transaction_plan_only=transaction.commit_transaction_mode in {
                "commit_plan_only",
                "dry_run_commit_transaction",
            },
            source_transaction_not_executed=transaction.commit_executed is False,
            source_commit_transaction_valid_for_execution=transaction.commit_transaction_valid_for_execution,
            source_commit_execution_ready=transaction.commit_execution_ready,
            planned_progress_commit_count=len(progress_commit_checks),
            planned_surface_commit_count=len(surface_commit_checks),
            executable_progress_commit_count=executable_progress_count,
            executable_surface_commit_count=executable_surface_count,
            rollback_execution_ready=rollback_readiness.rollback_execution_ready,
            all_audit_requirements_satisfied=all_audit_requirements_satisfied,
            final_execution_approval_present=final_execution_approval_present,
            execution_preconditions_satisfied=False,
            metadata={},
        )

    def _transaction_safety_assessment(
        self,
        transaction: SimuladoRuntimeMutationCommitTransaction,
    ) -> CommitTransactionSafetyAssessment:
        no_answer_key_exposure = not self._unsafe_public_answer_key_exposure_detected(transaction)
        no_gabarito_exposure = not self._unsafe_gabarito_exposure_detected(transaction)
        return CommitTransactionSafetyAssessment(
            assessment_id=f"commit-transaction-safety:{transaction.commit_transaction_id}",
            transaction_status_safe=transaction.commit_transaction_status != "committed",
            no_prior_commit_execution_detected=transaction.commit_executed is False,
            no_prior_mutation_commit_detected=transaction.mutation_committed is False,
            no_runtime_application_detected=transaction.runtime_application_applied is False,
            no_progress_mutation_detected=transaction.progress_mutation_applied is False,
            no_ranking_update_detected=transaction.ranking_update_applied is False,
            no_retention_update_detected=transaction.retention_update_applied is False,
            no_scheduler_update_detected=transaction.scheduler_update_applied is False,
            no_study_cycle_update_detected=transaction.study_cycle_update_applied is False,
            no_curriculum_graph_update_detected=transaction.curriculum_graph_update_applied is False,
            no_adaptive_tuning_detected=transaction.adaptive_tuning_applied is False,
            no_public_answer_key_exposure_detected=no_answer_key_exposure,
            no_gabarito_exposure_detected=no_gabarito_exposure,
            safe_for_future_execution_review=bool(
                transaction.commit_executed is False
                and transaction.mutation_committed is False
                and no_answer_key_exposure
                and no_gabarito_exposure
            ),
            metadata={},
        )

    def _rollback_readiness(
        self,
        transaction: SimuladoRuntimeMutationCommitTransaction,
    ) -> CommitRollbackExecutionReadiness:
        blockers: list[str] = []
        if transaction.rollback_execution_plan.rollback_execution_ready is False:
            blockers.append("blocked_by_rollback_not_ready")
        return CommitRollbackExecutionReadiness(
            rollback_readiness_id=f"commit-rollback-readiness:{transaction.commit_transaction_id}",
            rollback_required=transaction.rollback_execution_plan.rollback_required,
            rollback_available=transaction.rollback_execution_plan.rollback_available,
            rollback_verified=transaction.rollback_execution_plan.rollback_verified,
            rollback_execution_ready=transaction.rollback_execution_plan.rollback_execution_ready,
            rollback_execution_performed=False,
            rollback_ready_for_future_execution_review=bool(
                transaction.rollback_execution_plan.rollback_available
                and transaction.rollback_execution_plan.rollback_verified
            ),
            blockers=blockers,
            warnings=[],
            metadata={},
        )

    def _progress_commit_checks(
        self,
        transaction: SimuladoRuntimeMutationCommitTransaction,
    ) -> list[PlannedProgressCommitExecutionCheck]:
        checks: list[PlannedProgressCommitExecutionCheck] = []
        for source in transaction.planned_progress_commits:
            blockers = list(source.blockers)
            if source.committed:
                blockers.append("progress_commit_blocked_by_source_already_committed")
                state = "progress_commit_execution_blocked"
            elif source.execution_allowed is False:
                blockers.append("progress_commit_blocked_by_execution_not_allowed")
                state = "progress_commit_execution_blocked"
            else:
                state = "progress_commit_ready_for_future_execution_review"
            checks.append(
                PlannedProgressCommitExecutionCheck(
                    check_id=f"progress-commit-check:{source.planned_commit_id}",
                    source_planned_commit_id=source.planned_commit_id,
                    target_type=source.target_type,
                    target_id=source.target_id,
                    delta_kind=source.delta_kind,
                    source_committed=source.committed,
                    source_execution_allowed=source.execution_allowed,
                    execution_check_state=state,
                    execution_allowed=False,
                    executed=False,
                    blockers=blockers,
                    warnings=list(source.warnings),
                    metadata={"source_commit_transaction_id": transaction.commit_transaction_id},
                )
            )
        return checks

    def _surface_commit_checks(
        self,
        transaction: SimuladoRuntimeMutationCommitTransaction,
    ) -> list[PlannedSurfaceCommitExecutionCheck]:
        checks: list[PlannedSurfaceCommitExecutionCheck] = []
        for source in transaction.planned_surface_commits:
            blockers = list(source.blockers)
            if source.committed:
                blockers.append("surface_commit_blocked_by_source_already_committed")
                state = "surface_commit_execution_blocked"
            elif source.execution_allowed is False:
                blockers.append("surface_commit_blocked_by_execution_not_allowed")
                state = "surface_commit_execution_blocked"
            else:
                state = "surface_commit_ready_for_future_execution_review"
            checks.append(
                PlannedSurfaceCommitExecutionCheck(
                    check_id=f"surface-commit-check:{source.planned_commit_id}",
                    source_planned_commit_id=source.planned_commit_id,
                    surface_type=source.surface_type,
                    update_kind=source.update_kind,
                    source_committed=source.committed,
                    source_execution_allowed=source.execution_allowed,
                    execution_check_state=state,
                    execution_allowed=False,
                    executed=False,
                    blockers=blockers,
                    warnings=list(source.warnings),
                    metadata={"source_commit_transaction_id": transaction.commit_transaction_id},
                )
            )
        return checks

    def _runtime_surface_risk_summary(
        self,
        *,
        transaction: SimuladoRuntimeMutationCommitTransaction,
        surface_commit_checks: list[PlannedSurfaceCommitExecutionCheck],
    ) -> RuntimeSurfaceRiskSummary:
        surface_types = {item.surface_type for item in transaction.planned_surface_commits}
        blocked_count = sum(1 for item in surface_commit_checks if item.execution_check_state == "surface_commit_execution_blocked")
        ready_count = sum(
            1 for item in surface_commit_checks if item.execution_check_state == "surface_commit_ready_for_future_execution_review"
        )
        return RuntimeSurfaceRiskSummary(
            summary_id=f"runtime-surface-risk:{transaction.commit_transaction_id}",
            progress_surface_present="progress" in surface_types,
            ranking_surface_present="ranking" in surface_types,
            retention_surface_present="retention" in surface_types,
            scheduler_surface_present="scheduler" in surface_types,
            study_cycle_surface_present="study_cycle" in surface_types,
            curriculum_graph_surface_present="curriculum_graph" in surface_types,
            adaptive_tuning_surface_present="adaptive_tuning" in surface_types,
            risky_surface_count=len(surface_commit_checks),
            blocked_surface_count=blocked_count,
            executable_surface_count=ready_count,
            metadata={},
        )

    def _audit_requirements(
        self,
        transaction: SimuladoRuntimeMutationCommitTransaction,
    ) -> list[CommitExecutionAuditRequirement]:
        metadata = transaction.metadata
        requirements = {
            "final_execution_approval": bool(
                metadata.get("execution_guardrail_final_execution_approval_present", False)
            ),
            "rollback_execution_confirmation": bool(
                metadata.get("execution_guardrail_rollback_execution_confirmation_present", False)
            ),
            "audit_confirmation": bool(
                metadata.get("execution_guardrail_audit_confirmation_present", False)
            ),
            "runtime_surface_confirmation": bool(
                metadata.get("execution_guardrail_runtime_surface_confirmation_present", False)
            ),
            "public_answer_key_absence_confirmation": bool(
                metadata.get("execution_guardrail_public_answer_key_absence_confirmation_present", False)
            ),
            "human_review_confirmation": bool(
                metadata.get("execution_guardrail_human_review_confirmation_present", False)
            ),
        }
        reasons = {
            "final_execution_approval": "Final execution approval remains required before any future commit execution.",
            "rollback_execution_confirmation": "Rollback execution confirmation remains required before any future commit execution.",
            "audit_confirmation": "Audit confirmation remains required before any future commit execution.",
            "runtime_surface_confirmation": "Runtime surface confirmation remains required before any future commit execution.",
            "public_answer_key_absence_confirmation": "Public answer key absence confirmation remains required before any future commit execution.",
            "human_review_confirmation": "Human review confirmation remains required before any future commit execution.",
        }
        return [
            CommitExecutionAuditRequirement(
                requirement_id=f"commit-execution-requirement:{key}:{transaction.commit_transaction_id}",
                requirement_type=key,
                required=True,
                satisfied=value,
                reason=reasons[key],
                metadata={},
            )
            for key, value in requirements.items()
        ]

    def _blocker_codes(
        self,
        *,
        transaction: SimuladoRuntimeMutationCommitTransaction,
        readiness_summary: CommitExecutionReadinessSummary,
        rollback_readiness: CommitRollbackExecutionReadiness,
        progress_commit_checks: list[PlannedProgressCommitExecutionCheck],
        surface_commit_checks: list[PlannedSurfaceCommitExecutionCheck],
        audit_requirements: list[CommitExecutionAuditRequirement],
    ) -> list[str]:
        blocker_codes: list[str] = []
        if self._unsafe_public_answer_key_exposure_detected(transaction) or self._unsafe_gabarito_exposure_detected(
            transaction
        ):
            blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        if readiness_summary.source_transaction_plan_only is False:
            blocker_codes.append("blocked_by_transaction_not_plan_only")
        if readiness_summary.source_transaction_not_executed is False:
            blocker_codes.append("blocked_by_transaction_already_executed")
        if transaction.commit_transaction_valid_for_execution is False:
            blocker_codes.append("blocked_by_commit_transaction_not_valid_for_execution")
        if transaction.commit_execution_ready is False:
            blocker_codes.append("blocked_by_commit_execution_not_ready")
        if rollback_readiness.rollback_execution_ready is False:
            blocker_codes.append("blocked_by_rollback_not_ready")
        if any(item.execution_check_state != "progress_commit_ready_for_future_execution_review" for item in progress_commit_checks):
            blocker_codes.append("blocked_by_progress_commits_not_executable")
        if any(item.execution_check_state != "surface_commit_ready_for_future_execution_review" for item in surface_commit_checks):
            blocker_codes.append("blocked_by_surface_commits_not_executable")
        if not all(
            item.satisfied for item in audit_requirements if item.requirement_type != "final_execution_approval"
        ):
            blocker_codes.append("blocked_by_audit_requirements_unsatisfied")
        if bool(transaction.metadata.get("force_commit_execution_disabled", False)):
            blocker_codes.append("blocked_by_commit_execution_disabled")
        if not readiness_summary.final_execution_approval_present:
            blocker_codes.append("blocked_by_final_execution_approval_missing")
        deduped: list[str] = []
        for code in blocker_codes:
            if code not in deduped:
                deduped.append(code)
        return deduped

    def _state(self, blocker_codes: list[str]) -> tuple[str, str]:
        ordered = [
            "blocked_by_public_answer_key_exposure_forbidden",
            "blocked_by_transaction_not_plan_only",
            "blocked_by_transaction_already_executed",
            "blocked_by_commit_transaction_not_valid_for_execution",
            "blocked_by_commit_execution_not_ready",
            "blocked_by_rollback_not_ready",
            "blocked_by_progress_commits_not_executable",
            "blocked_by_surface_commits_not_executable",
            "blocked_by_audit_requirements_unsatisfied",
            "blocked_by_commit_execution_disabled",
            "blocked_by_final_execution_approval_missing",
        ]
        for code in ordered:
            if code in blocker_codes:
                return "execution_blocked", code
        return "execution_guardrail_created", "execution_guardrail_needs_review"

    def _audit_trail(
        self,
        *,
        transaction: SimuladoRuntimeMutationCommitTransaction,
        blocker_codes: list[str],
        actor_user_id: str,
    ) -> list[CommitExecutionGuardrailAuditEntry]:
        events = [
            ("execution_guardrail_created", "Controlled runtime commit execution guardrail artifact was created."),
            ("no_commit_execution", "Commit execution remains disabled in this foundation."),
            ("no_mutation_commit", "Mutation commit remains disabled in this foundation."),
            ("no_runtime_application", "Runtime application remains disabled in this foundation."),
            ("no_progress_mutation", "Progress mutation remains disabled in this foundation."),
            (
                "no_final_pedagogical_update_event",
                "Final pedagogical update events remain disabled in this foundation.",
            ),
        ]
        if blocker_codes:
            events.append(("execution_blocked", "Controlled runtime commit execution remains blocked."))
        event_map = {
            "blocked_by_commit_transaction_not_valid_for_execution": (
                "commit_transaction_not_valid_for_execution",
                "Commit transaction is not valid for controlled execution.",
            ),
            "blocked_by_commit_execution_not_ready": (
                "commit_execution_not_ready",
                "Commit execution readiness remains false.",
            ),
            "blocked_by_rollback_not_ready": (
                "rollback_not_ready",
                "Rollback execution readiness remains false.",
            ),
            "blocked_by_progress_commits_not_executable": (
                "progress_commits_not_executable",
                "Planned progress commits remain non-executable.",
            ),
            "blocked_by_surface_commits_not_executable": (
                "surface_commits_not_executable",
                "Planned surface commits remain non-executable.",
            ),
            "blocked_by_audit_requirements_unsatisfied": (
                "audit_requirements_unsatisfied",
                "Audit requirements remain unsatisfied.",
            ),
            "blocked_by_final_execution_approval_missing": (
                "final_execution_approval_missing",
                "Final execution approval remains missing.",
            ),
        }
        for code, event in event_map.items():
            if code in blocker_codes:
                events.append(event)
        return [
            CommitExecutionGuardrailAuditEntry(
                audit_id=f"commit-execution-guardrail-audit:{event_type}:{transaction.commit_transaction_id}",
                event_type=event_type,
                actor_user_id=actor_user_id,
                message=message,
                metadata={},
            )
            for event_type, message in events
        ]

    def _blockers(
        self,
        transaction: SimuladoRuntimeMutationCommitTransaction,
        blocker_codes: list[str],
    ) -> list[CommitExecutionGuardrailBlocker]:
        messages = {
            "blocked_by_transaction_not_plan_only": "Source commit transaction is not plan-only.",
            "blocked_by_transaction_already_executed": "Source commit transaction appears already executed.",
            "blocked_by_commit_transaction_not_valid_for_execution": "Commit transaction is not valid for execution.",
            "blocked_by_commit_execution_not_ready": "Commit execution readiness remains false.",
            "blocked_by_rollback_not_ready": "Rollback execution readiness remains false.",
            "blocked_by_progress_commits_not_executable": "Planned progress commits remain non-executable.",
            "blocked_by_surface_commits_not_executable": "Planned surface commits remain non-executable.",
            "blocked_by_audit_requirements_unsatisfied": "Audit requirements remain unsatisfied.",
            "blocked_by_final_execution_approval_missing": "Final execution approval remains missing.",
            "blocked_by_commit_execution_disabled": "Commit execution remains disabled for this foundation.",
            "blocked_by_public_answer_key_exposure_forbidden": "Unsafe public answer key or gabarito exposure was detected.",
        }
        return [
            CommitExecutionGuardrailBlocker(
                blocker_id=f"commit-execution-guardrail-blocker:{code}:{transaction.commit_transaction_id}",
                code=code,
                message=messages[code],
                related_artifact_type="commit_transaction",
                related_artifact_id=transaction.commit_transaction_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        transaction: SimuladoRuntimeMutationCommitTransaction,
    ) -> list[CommitExecutionGuardrailValidationFinding]:
        return [
            CommitExecutionGuardrailValidationFinding(
                finding_id=f"commit-execution-guardrail-finding:{transaction.commit_transaction_id}",
                code="execution_guardrail_only",
                message="This artifact records controlled execution readiness metadata only.",
                related_artifact_type="commit_transaction",
                related_artifact_id=transaction.commit_transaction_id,
                metadata={},
            )
        ]

    def _warnings(
        self,
        transaction: SimuladoRuntimeMutationCommitTransaction,
    ) -> list[CommitExecutionGuardrailWarning]:
        return [
            CommitExecutionGuardrailWarning(
                code="no_commit_execution",
                message="Commit execution remains intentionally disabled in this foundation.",
                related_artifact_type="commit_transaction",
                related_artifact_id=transaction.commit_transaction_id,
                metadata={},
            )
        ]

    def _unsafe_public_answer_key_exposure_detected(
        self,
        transaction: SimuladoRuntimeMutationCommitTransaction,
    ) -> bool:
        return bool(transaction.answer_key_publicly_exposed) or (
            transaction.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
        ) or any(
            blocker.code == "blocked_by_public_answer_key_exposure_forbidden"
            for blocker in transaction.blockers
        )

    def _unsafe_gabarito_exposure_detected(
        self,
        transaction: SimuladoRuntimeMutationCommitTransaction,
    ) -> bool:
        return bool(transaction.gabarito_publicly_exposed) or (
            transaction.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
        )
