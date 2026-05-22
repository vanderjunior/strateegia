from __future__ import annotations

from app.domain.models import (
    PlannedProgressCommit,
    PlannedRuntimeSurfaceCommit,
    RuntimeCommitRollbackExecutionPlan,
    RuntimeCommitTransactionAuditEntry,
    RuntimeCommitTransactionBlocker,
    RuntimeCommitTransactionValidationFinding,
    RuntimeCommitTransactionValidationSummary,
    RuntimeCommitTransactionWarning,
    SimuladoControlledRuntimeMutationCommitShell,
    SimuladoExplicitRuntimeMutationCommit,
    SimuladoRuntimeMutationCommitTransaction,
    SimuladoRuntimeProgressMutationTransaction,
)
from app.repositories.json_store import JsonStudyRepository


RUNTIME_MUTATION_COMMIT_TRANSACTION_BUILD_METHOD = (
    "heuristic_simulado_runtime_mutation_commit_transaction_builder"
)
PROGRESS_COMMIT_KIND_BY_DELTA = {
    "mastery_delta": "progress_delta_commit",
    "completion_delta": "progress_delta_commit",
    "accuracy_delta": "progress_delta_commit",
    "review_signal_delta": "progress_signal_commit",
    "confidence_delta": "progress_signal_commit",
}
SURFACE_COMMIT_KIND_BY_SURFACE = {
    "progress": "progress_surface_commit",
    "ranking": "ranking_surface_commit",
    "retention": "retention_surface_commit",
    "scheduler": "scheduler_surface_commit",
    "study_cycle": "study_cycle_surface_commit",
    "curriculum_graph": "curriculum_graph_surface_commit",
    "adaptive_tuning": "adaptive_tuning_surface_commit",
}


class SimuladoRuntimeMutationCommitTransactionService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_commit_transaction(
        self,
        source_explicit_commit_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeMutationCommitTransaction | None:
        if user_id is None:
            return None

        explicit_commit = self.repository.get_simulado_explicit_mutation_commit_by_id(
            source_explicit_commit_id,
            user_id=user_id,
        )
        if explicit_commit is None:
            return None

        existing = self.repository.get_simulado_runtime_mutation_commit_transaction(
            source_explicit_commit_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        shell = self.repository.get_simulado_controlled_mutation_commit_shell_by_id(
            explicit_commit.source_commit_shell_id,
            user_id=user_id,
        )
        mutation_transaction = self.repository.get_simulado_runtime_progress_mutation_transaction_by_id(
            explicit_commit.source_mutation_transaction_id,
            user_id=user_id,
        )
        rollback_execution_plan = self._rollback_execution_plan(
            explicit_commit=explicit_commit,
            mutation_transaction=mutation_transaction,
        )
        planned_progress_commits = self._planned_progress_commits(explicit_commit)
        planned_surface_commits = self._planned_surface_commits(explicit_commit)
        blocker_codes = self._blocker_codes(
            explicit_commit=explicit_commit,
            shell=shell,
            mutation_transaction=mutation_transaction,
            rollback_execution_plan=rollback_execution_plan,
            planned_progress_commits=planned_progress_commits,
            planned_surface_commits=planned_surface_commits,
        )
        commit_transaction_status, readiness_state = self._state(blocker_codes)
        validation_summary = self._validation_summary(
            explicit_commit=explicit_commit,
            shell=shell,
            mutation_transaction=mutation_transaction,
            planned_progress_commits=planned_progress_commits,
            planned_surface_commits=planned_surface_commits,
            rollback_execution_plan=rollback_execution_plan,
        )

        result = SimuladoRuntimeMutationCommitTransaction(
            commit_transaction_id=f"simulado-commit-transaction:{explicit_commit.explicit_commit_id}",
            user_id=user_id,
            source_explicit_commit_id=explicit_commit.explicit_commit_id,
            source_commit_shell_id=explicit_commit.source_commit_shell_id,
            source_mutation_transaction_id=explicit_commit.source_mutation_transaction_id,
            source_explicit_apply_id=explicit_commit.source_explicit_apply_id,
            source_apply_shell_id=explicit_commit.source_apply_shell_id,
            source_application_id=explicit_commit.source_application_id,
            source_runtime_guardrail_id=explicit_commit.source_runtime_guardrail_id,
            source_integrated_result_id=explicit_commit.source_integrated_result_id,
            source_score_result_id=explicit_commit.source_score_result_id,
            source_progress_guardrail_id=explicit_commit.source_progress_guardrail_id,
            source_attempt_session_id=explicit_commit.source_attempt_session_id,
            source_simulado_blueprint_id=explicit_commit.source_simulado_blueprint_id,
            commit_transaction_mode="commit_plan_only",
            commit_transaction_status=commit_transaction_status,
            readiness_state=readiness_state,
            validation_summary=validation_summary,
            planned_progress_commits=planned_progress_commits,
            planned_surface_commits=planned_surface_commits,
            rollback_execution_plan=rollback_execution_plan,
            audit_trail=self._audit_trail(
                explicit_commit=explicit_commit,
                blocker_codes=blocker_codes,
                actor_user_id=user_id,
            ),
            blockers=self._blockers(explicit_commit, blocker_codes),
            validation_findings=self._findings(explicit_commit),
            warnings=self._warnings(explicit_commit),
            commit_transaction_created=True,
            commit_transaction_valid_for_execution=False,
            commit_execution_ready=False,
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
                "build_method": RUNTIME_MUTATION_COMMIT_TRANSACTION_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_runtime_mutation_commit_transaction(result, user_id=user_id)
        return result

    def get_commit_transaction(
        self,
        source_explicit_commit_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeMutationCommitTransaction | None:
        return self.repository.get_simulado_runtime_mutation_commit_transaction(
            source_explicit_commit_id,
            user_id=user_id,
        )

    def get_commit_transaction_by_id(
        self,
        commit_transaction_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeMutationCommitTransaction | None:
        return self.repository.get_simulado_runtime_mutation_commit_transaction_by_id(
            commit_transaction_id,
            user_id=user_id,
        )

    def _validation_summary(
        self,
        *,
        explicit_commit: SimuladoExplicitRuntimeMutationCommit,
        shell: SimuladoControlledRuntimeMutationCommitShell | None,
        mutation_transaction: SimuladoRuntimeProgressMutationTransaction | None,
        planned_progress_commits: list[PlannedProgressCommit],
        planned_surface_commits: list[PlannedRuntimeSurfaceCommit],
        rollback_execution_plan: RuntimeCommitRollbackExecutionPlan,
    ) -> RuntimeCommitTransactionValidationSummary:
        return RuntimeCommitTransactionValidationSummary(
            summary_id=f"runtime-commit-transaction-validation:{explicit_commit.explicit_commit_id}",
            source_explicit_commit_present=True,
            explicit_commit_recorded=explicit_commit.explicit_commit_recorded,
            explicit_commit_approved=explicit_commit.explicit_commit_approved,
            approved_for_future_mutation_commit_review=(
                explicit_commit.approved_for_future_mutation_commit_review
            ),
            approved_for_commit_now=explicit_commit.approved_for_commit_now,
            confirmations_satisfied=explicit_commit.confirmation_summary.all_confirmations_satisfied,
            source_commit_shell_present=shell is not None,
            source_commit_shell_pre_commit_only=self._shell_pre_commit_only(shell),
            source_mutation_transaction_present=mutation_transaction is not None,
            planned_progress_commit_count=len(planned_progress_commits),
            planned_surface_commit_count=len(planned_surface_commits),
            rollback_execution_plan_available=rollback_execution_plan.rollback_available,
            rollback_execution_plan_verified=rollback_execution_plan.rollback_verified,
            transaction_valid_for_execution=False,
            transaction_execution_ready=False,
            unsafe_public_answer_key_exposure_detected=self._unsafe_public_answer_key_exposure_detected(
                explicit_commit
            ),
            unsafe_gabarito_exposure_detected=self._unsafe_gabarito_exposure_detected(explicit_commit),
            metadata={},
        )

    def _planned_progress_commits(
        self,
        explicit_commit: SimuladoExplicitRuntimeMutationCommit,
    ) -> list[PlannedProgressCommit]:
        planned: list[PlannedProgressCommit] = []
        for approval in explicit_commit.delta_approvals:
            blockers = list(approval.blockers)
            if not approval.approved_for_future_mutation_commit_review:
                blockers.append("planned_commit_blocked_by_unapproved_delta")
            if not approval.metadata.get("target_id"):
                blockers.append("planned_commit_blocked_by_missing_target")
            blockers.append("planned_commit_blocked_by_commit_now_not_allowed")
            blockers.append("planned_commit_blocked_by_execution_not_allowed")
            planned.append(
                PlannedProgressCommit(
                    planned_commit_id=f"planned-progress-commit:{approval.approval_id}",
                    source_delta_approval_id=approval.approval_id,
                    source_delta_decision_id=approval.source_delta_decision_id,
                    source_delta_id=approval.source_delta_id,
                    target_type=approval.target_type,
                    target_id=approval.metadata.get("target_id")
                    if isinstance(approval.metadata, dict)
                    else None,
                    delta_kind=approval.delta_kind,
                    planned_commit_kind=PROGRESS_COMMIT_KIND_BY_DELTA.get(approval.delta_kind, "unknown"),
                    proposed_before_summary={"available": False},
                    proposed_after_summary={"available": False},
                    planned_delta_value=None,
                    confidence=0.0,
                    committed=False,
                    execution_allowed=False,
                    blockers=blockers,
                    warnings=list(approval.warnings),
                    metadata={"source_explicit_commit_id": explicit_commit.explicit_commit_id},
                )
            )
        return planned

    def _planned_surface_commits(
        self,
        explicit_commit: SimuladoExplicitRuntimeMutationCommit,
    ) -> list[PlannedRuntimeSurfaceCommit]:
        planned: list[PlannedRuntimeSurfaceCommit] = []
        for approval in explicit_commit.surface_approvals:
            blockers = list(approval.blockers)
            if not approval.approved_for_future_mutation_commit_review:
                blockers.append("surface_commit_blocked_by_unapproved_surface")
            blockers.append("surface_commit_blocked_by_commit_now_not_allowed")
            blockers.append("surface_commit_blocked_by_execution_not_allowed")
            planned.append(
                PlannedRuntimeSurfaceCommit(
                    planned_commit_id=f"planned-surface-commit:{approval.approval_id}",
                    source_surface_approval_id=approval.approval_id,
                    source_surface_decision_id=approval.source_surface_decision_id,
                    source_update_id=approval.source_update_id,
                    surface_type=approval.surface_type,
                    update_kind=approval.update_kind,
                    planned_commit_kind=SURFACE_COMMIT_KIND_BY_SURFACE.get(
                        approval.surface_type,
                        "unknown",
                    ),
                    target_ref=approval.metadata.get("target_ref")
                    if isinstance(approval.metadata, dict)
                    else None,
                    proposed_before_summary={"available": False},
                    proposed_after_summary={"available": False},
                    committed=False,
                    execution_allowed=False,
                    blockers=blockers,
                    warnings=list(approval.warnings),
                    metadata={"source_explicit_commit_id": explicit_commit.explicit_commit_id},
                )
            )
        return planned

    def _rollback_execution_plan(
        self,
        *,
        explicit_commit: SimuladoExplicitRuntimeMutationCommit,
        mutation_transaction: SimuladoRuntimeProgressMutationTransaction | None,
    ) -> RuntimeCommitRollbackExecutionPlan:
        rollback_plan = mutation_transaction.rollback_plan if mutation_transaction is not None else None
        rollback_plan_id = ""
        rollback_available = False
        rollback_verified = False
        rollback_steps_count = 0
        if rollback_plan is not None:
            rollback_plan_id = rollback_plan.rollback_plan_id
            rollback_available = bool(rollback_plan.rollback_available)
            rollback_verified = bool(rollback_plan.rollback_verified)
            rollback_steps_count = int(rollback_plan.rollback_steps_count or 0)
        return RuntimeCommitRollbackExecutionPlan(
            rollback_execution_plan_id=(
                f"runtime-commit-rollback:{explicit_commit.explicit_commit_id}"
                if rollback_plan_id
                else ""
            ),
            rollback_required=True,
            rollback_available=rollback_available,
            rollback_verified=rollback_verified,
            rollback_execution_ready=False,
            rollback_execution_performed=False,
            rollback_steps_count=rollback_steps_count,
            rollback_summary="Rollback execution planning remains required before any future commit execution.",
            metadata={},
        )

    def _blocker_codes(
        self,
        *,
        explicit_commit: SimuladoExplicitRuntimeMutationCommit,
        shell: SimuladoControlledRuntimeMutationCommitShell | None,
        mutation_transaction: SimuladoRuntimeProgressMutationTransaction | None,
        rollback_execution_plan: RuntimeCommitRollbackExecutionPlan,
        planned_progress_commits: list[PlannedProgressCommit],
        planned_surface_commits: list[PlannedRuntimeSurfaceCommit],
    ) -> list[str]:
        blocker_codes: list[str] = []
        if self._unsafe_public_answer_key_exposure_detected(explicit_commit) or self._unsafe_gabarito_exposure_detected(
            explicit_commit
        ):
            blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        if not explicit_commit.explicit_commit_approved:
            blocker_codes.append("blocked_by_explicit_commit_not_approved")
        if explicit_commit.explicit_commit_approved and not explicit_commit.approved_for_commit_now:
            blocker_codes.append("blocked_by_commit_now_not_allowed")
        if not explicit_commit.confirmation_summary.all_confirmations_satisfied:
            blocker_codes.append("blocked_by_confirmations_incomplete")
        if not self._shell_pre_commit_only(shell):
            blocker_codes.append("blocked_by_commit_shell_not_pre_commit_only")
        if mutation_transaction is None:
            blocker_codes.append("blocked_by_missing_source_mutation_transaction")
        if not rollback_execution_plan.rollback_execution_plan_id:
            blocker_codes.append("blocked_by_missing_rollback_execution_plan")
        if rollback_execution_plan.rollback_available is False:
            blocker_codes.append("blocked_by_rollback_not_available")
        if rollback_execution_plan.rollback_verified is False:
            blocker_codes.append("blocked_by_rollback_not_verified")
        if any(not item.metadata.get("source_explicit_commit_id") for item in planned_progress_commits):
            blocker_codes.append("blocked_by_delta_approvals_not_ready")
        elif any(not item.blockers or "planned_commit_blocked_by_unapproved_delta" in item.blockers for item in planned_progress_commits):
            blocker_codes.append("blocked_by_delta_approvals_not_ready")
        if any(
            not item.blockers or "surface_commit_blocked_by_unapproved_surface" in item.blockers
            for item in planned_surface_commits
        ):
            blocker_codes.append("blocked_by_surface_approvals_not_ready")
        if bool(explicit_commit.metadata.get("force_commit_execution_disabled", False)):
            blocker_codes.append("blocked_by_commit_execution_disabled")
        deduped: list[str] = []
        for code in blocker_codes:
            if code not in deduped:
                deduped.append(code)
        return deduped

    def _state(self, blocker_codes: list[str]) -> tuple[str, str]:
        ordered = [
            "blocked_by_public_answer_key_exposure_forbidden",
            "blocked_by_explicit_commit_not_approved",
            "blocked_by_commit_shell_not_pre_commit_only",
            "blocked_by_missing_source_mutation_transaction",
            "blocked_by_commit_execution_disabled",
            "blocked_by_commit_now_not_allowed",
            "blocked_by_confirmations_incomplete",
            "blocked_by_missing_rollback_execution_plan",
            "blocked_by_rollback_not_available",
            "blocked_by_rollback_not_verified",
            "blocked_by_delta_approvals_not_ready",
            "blocked_by_surface_approvals_not_ready",
        ]
        for code in ordered:
            if code in blocker_codes:
                return "commit_blocked", code
        return "not_committed", "commit_transaction_needs_review"

    def _audit_trail(
        self,
        *,
        explicit_commit: SimuladoExplicitRuntimeMutationCommit,
        blocker_codes: list[str],
        actor_user_id: str,
    ) -> list[RuntimeCommitTransactionAuditEntry]:
        events = [
            ("commit_transaction_created", "Runtime mutation commit transaction artifact was created."),
            ("commit_plan_created", "Commit transaction plan was created as dry-run metadata only."),
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
            events.append(("commit_transaction_blocked", "Runtime mutation commit transaction remains blocked."))
        event_map = {
            "blocked_by_explicit_commit_not_approved": (
                "explicit_commit_not_approved",
                "Source explicit commit is not approved for future commit planning.",
            ),
            "blocked_by_commit_now_not_allowed": (
                "commit_now_not_allowed",
                "Commit now remains disallowed for this foundation.",
            ),
            "blocked_by_confirmations_incomplete": (
                "confirmations_incomplete",
                "Required explicit commit confirmations remain incomplete.",
            ),
            "blocked_by_missing_rollback_execution_plan": (
                "rollback_execution_plan_missing",
                "Rollback execution plan metadata remains missing.",
            ),
            "blocked_by_rollback_not_available": (
                "rollback_not_available",
                "Rollback execution plan remains unavailable.",
            ),
            "blocked_by_rollback_not_verified": (
                "rollback_not_verified",
                "Rollback execution plan remains unverified.",
            ),
        }
        for code, event in event_map.items():
            if code in blocker_codes:
                events.append(event)
        return [
            RuntimeCommitTransactionAuditEntry(
                audit_id=f"runtime-commit-transaction-audit:{event_type}:{explicit_commit.explicit_commit_id}",
                event_type=event_type,
                actor_user_id=actor_user_id,
                message=message,
                metadata={},
            )
            for event_type, message in events
        ]

    def _blockers(
        self,
        explicit_commit: SimuladoExplicitRuntimeMutationCommit,
        blocker_codes: list[str],
    ) -> list[RuntimeCommitTransactionBlocker]:
        messages = {
            "blocked_by_explicit_commit_not_approved": "Source explicit commit is not approved.",
            "blocked_by_commit_now_not_allowed": "Commit-now execution remains disabled for this foundation.",
            "blocked_by_confirmations_incomplete": "Required confirmations remain incomplete.",
            "blocked_by_commit_shell_not_pre_commit_only": "Source controlled commit shell is not pre-commit-only.",
            "blocked_by_missing_source_mutation_transaction": "Source mutation transaction is missing.",
            "blocked_by_missing_rollback_execution_plan": "Rollback execution plan metadata is missing.",
            "blocked_by_rollback_not_available": "Rollback execution metadata is unavailable.",
            "blocked_by_rollback_not_verified": "Rollback execution metadata is unverified.",
            "blocked_by_delta_approvals_not_ready": "Delta approvals are not ready for future execution review.",
            "blocked_by_surface_approvals_not_ready": "Surface approvals are not ready for future execution review.",
            "blocked_by_commit_execution_disabled": "Commit execution remains disabled for this foundation.",
            "blocked_by_public_answer_key_exposure_forbidden": "Unsafe answer key or gabarito exposure was detected.",
        }
        return [
            RuntimeCommitTransactionBlocker(
                blocker_id=f"runtime-commit-transaction-blocker:{code}:{explicit_commit.explicit_commit_id}",
                code=code,
                message=messages[code],
                related_artifact_type="explicit_commit",
                related_artifact_id=explicit_commit.explicit_commit_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        explicit_commit: SimuladoExplicitRuntimeMutationCommit,
    ) -> list[RuntimeCommitTransactionValidationFinding]:
        return [
            RuntimeCommitTransactionValidationFinding(
                finding_id=f"runtime-commit-transaction-finding:{explicit_commit.explicit_commit_id}",
                code="commit_plan_only",
                message="This artifact records a dry-run commit transaction only.",
                related_artifact_type="explicit_commit",
                related_artifact_id=explicit_commit.explicit_commit_id,
                metadata={},
            )
        ]

    def _warnings(
        self,
        explicit_commit: SimuladoExplicitRuntimeMutationCommit,
    ) -> list[RuntimeCommitTransactionWarning]:
        return [
            RuntimeCommitTransactionWarning(
                code="no_commit_execution",
                message="Commit execution remains intentionally disabled in this foundation.",
                related_artifact_type="explicit_commit",
                related_artifact_id=explicit_commit.explicit_commit_id,
                metadata={},
            )
        ]

    def _shell_pre_commit_only(
        self,
        shell: SimuladoControlledRuntimeMutationCommitShell | None,
    ) -> bool:
        if shell is None:
            return False
        return shell.commit_mode in {"pre_commit_shell", "controlled_commit_shell"} and shell.mutation_committed is False

    def _unsafe_public_answer_key_exposure_detected(
        self,
        explicit_commit: SimuladoExplicitRuntimeMutationCommit,
    ) -> bool:
        return bool(explicit_commit.answer_key_publicly_exposed) or (
            explicit_commit.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
        ) or any(
            blocker.code == "blocked_by_public_answer_key_exposure_forbidden"
            for blocker in explicit_commit.blockers
        )

    def _unsafe_gabarito_exposure_detected(
        self,
        explicit_commit: SimuladoExplicitRuntimeMutationCommit,
    ) -> bool:
        return bool(explicit_commit.gabarito_publicly_exposed) or (
            explicit_commit.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
        )
