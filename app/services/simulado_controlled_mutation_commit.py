from __future__ import annotations

from app.domain.models import (
    ControlledCommitAuditEntry,
    ControlledCommitAuditRequirement,
    ControlledCommitBlocker,
    ControlledCommitDeltaDecision,
    ControlledCommitPreconditionSummary,
    ControlledCommitRollbackReadiness,
    ControlledCommitSurfaceDecision,
    ControlledCommitValidationFinding,
    ControlledCommitWarning,
    SimuladoControlledRuntimeMutationCommitShell,
    SimuladoRuntimeProgressMutationTransaction,
)
from app.repositories.json_store import JsonStudyRepository


CONTROLLED_MUTATION_COMMIT_SHELL_BUILD_METHOD = (
    "heuristic_simulado_controlled_runtime_mutation_commit_shell_builder"
)


class SimuladoControlledRuntimeMutationCommitService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_commit_shell(
        self,
        source_mutation_transaction_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeMutationCommitShell | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_controlled_mutation_commit_shell(
            source_mutation_transaction_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        transaction = self.repository.get_simulado_runtime_progress_mutation_transaction_by_id(
            source_mutation_transaction_id,
            user_id=user_id,
        )
        if transaction is None:
            return None

        precondition_summary = self._precondition_summary(transaction)
        rollback_readiness = self._rollback_readiness(transaction)
        blocker_codes = self._blocker_codes(
            transaction=transaction,
            precondition_summary=precondition_summary,
            rollback_readiness=rollback_readiness,
        )
        commit_status, readiness_state = self._state(blocker_codes)
        delta_commit_decisions = self._delta_commit_decisions(transaction)
        surface_commit_decisions = self._surface_commit_decisions(transaction)
        audit_requirements = self._audit_requirements(transaction)
        audit_trail = self._audit_trail(
            transaction=transaction,
            blocker_codes=blocker_codes,
            actor_user_id=user_id,
        )
        blockers = self._blockers(transaction, blocker_codes)

        result = SimuladoControlledRuntimeMutationCommitShell(
            commit_shell_id=f"simulado-mutation-commit-shell:{transaction.mutation_transaction_id}",
            user_id=user_id,
            source_mutation_transaction_id=transaction.mutation_transaction_id,
            source_explicit_apply_id=transaction.source_explicit_apply_id,
            source_apply_shell_id=transaction.source_apply_shell_id,
            source_application_id=transaction.source_application_id,
            source_runtime_guardrail_id=transaction.source_runtime_guardrail_id,
            source_integrated_result_id=transaction.source_integrated_result_id,
            source_score_result_id=transaction.source_score_result_id,
            source_progress_guardrail_id=transaction.source_progress_guardrail_id,
            source_attempt_session_id=transaction.source_attempt_session_id,
            source_simulado_blueprint_id=transaction.source_simulado_blueprint_id,
            commit_mode="pre_commit_shell",
            commit_status=commit_status,
            readiness_state=readiness_state,
            precondition_summary=precondition_summary,
            rollback_readiness=rollback_readiness,
            delta_commit_decisions=delta_commit_decisions,
            surface_commit_decisions=surface_commit_decisions,
            audit_requirements=audit_requirements,
            audit_trail=audit_trail,
            blockers=blockers,
            validation_findings=self._findings(transaction),
            warnings=self._warnings(transaction),
            commit_shell_created=True,
            commit_request_accepted=False,
            commit_preconditions_satisfied=False,
            commit_ready_for_execution=False,
            mutation_valid_for_commit=False,
            mutation_commit_ready=False,
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
                "build_method": CONTROLLED_MUTATION_COMMIT_SHELL_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_controlled_mutation_commit_shell(result, user_id=user_id)
        return result

    def get_commit_shell(
        self,
        source_mutation_transaction_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeMutationCommitShell | None:
        return self.repository.get_simulado_controlled_mutation_commit_shell(
            source_mutation_transaction_id,
            user_id=user_id,
        )

    def get_commit_shell_by_id(
        self,
        commit_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeMutationCommitShell | None:
        return self.repository.get_simulado_controlled_mutation_commit_shell_by_id(
            commit_shell_id,
            user_id=user_id,
        )

    def _precondition_summary(
        self,
        transaction: SimuladoRuntimeProgressMutationTransaction,
    ) -> ControlledCommitPreconditionSummary:
        metadata = transaction.metadata
        return ControlledCommitPreconditionSummary(
            summary_id=f"controlled-commit-preconditions:{transaction.mutation_transaction_id}",
            source_transaction_present=True,
            source_transaction_proposal_only=transaction.mutation_mode in {"proposal_only", "dry_run_transaction"},
            source_transaction_not_committed=(
                transaction.mutation_committed is False
                and transaction.mutation_status not in {"committed", "mutation_committed"}
            ),
            source_mutation_valid_for_commit=transaction.mutation_valid_for_commit,
            source_mutation_commit_ready=transaction.mutation_commit_ready,
            rollback_available=transaction.rollback_plan.rollback_available,
            rollback_verified=transaction.rollback_plan.rollback_verified,
            all_deltas_commit_allowed=bool(transaction.proposed_progress_deltas)
            and all(item.commit_allowed for item in transaction.proposed_progress_deltas),
            all_surfaces_commit_allowed=bool(transaction.proposed_surface_updates)
            and all(item.commit_allowed for item in transaction.proposed_surface_updates),
            commit_policy_present=bool(metadata.get("controlled_commit_policy_present", False)),
            explicit_commit_approval_present=bool(
                metadata.get("controlled_commit_explicit_commit_approval_present", False)
            ),
            audit_confirmation_present=bool(
                metadata.get("controlled_commit_audit_confirmation_present", False)
            ),
            unsafe_public_answer_key_exposure_detected=self._unsafe_public_answer_key_exposure_detected(
                transaction
            ),
            unsafe_gabarito_exposure_detected=self._unsafe_gabarito_exposure_detected(transaction),
            preconditions_satisfied=False,
            metadata={},
        )

    def _rollback_readiness(
        self,
        transaction: SimuladoRuntimeProgressMutationTransaction,
    ) -> ControlledCommitRollbackReadiness:
        blockers: list[str] = []
        if transaction.rollback_plan.rollback_available is False:
            blockers.append("blocked_by_rollback_not_available")
        if transaction.rollback_plan.rollback_verified is False:
            blockers.append("blocked_by_rollback_not_verified")
        return ControlledCommitRollbackReadiness(
            rollback_readiness_id=f"controlled-commit-rollback:{transaction.mutation_transaction_id}",
            rollback_required=transaction.rollback_plan.rollback_required,
            rollback_available=transaction.rollback_plan.rollback_available,
            rollback_verified=transaction.rollback_plan.rollback_verified,
            rollback_steps_count=transaction.rollback_plan.rollback_steps_count,
            rollback_ready_for_commit=bool(
                transaction.rollback_plan.rollback_available and transaction.rollback_plan.rollback_verified
            ),
            blockers=blockers,
            warnings=[],
            metadata={},
        )

    def _delta_commit_decisions(
        self,
        transaction: SimuladoRuntimeProgressMutationTransaction,
    ) -> list[ControlledCommitDeltaDecision]:
        decisions: list[ControlledCommitDeltaDecision] = []
        for source in transaction.proposed_progress_deltas:
            blockers = list(source.blockers)
            if source.applied:
                blockers.append("delta_blocked_by_source_already_applied")
                decision = "delta_rejected_pre_commit"
                reason = "source_delta_already_applied"
            elif source.commit_allowed is False:
                if "delta_blocked_by_commit_not_allowed" not in blockers:
                    blockers.append("delta_blocked_by_commit_not_allowed")
                decision = "delta_rejected_pre_commit"
                reason = "source_delta_commit_not_allowed"
            else:
                decision = "delta_ready_for_future_commit_review"
                reason = "future_explicit_commit_review_required"
            decisions.append(
                ControlledCommitDeltaDecision(
                    decision_id=f"controlled-commit-delta:{source.delta_id}",
                    source_delta_id=source.delta_id,
                    target_type=source.target_type,
                    target_id=source.target_id,
                    delta_kind=source.delta_kind,
                    source_applied=source.applied,
                    source_commit_allowed=source.commit_allowed,
                    commit_decision=decision,
                    commit_decision_reason=reason,
                    committed=False,
                    blockers=blockers,
                    warnings=list(source.warnings),
                    metadata={"source_mutation_transaction_id": transaction.mutation_transaction_id},
                )
            )
        return decisions

    def _surface_commit_decisions(
        self,
        transaction: SimuladoRuntimeProgressMutationTransaction,
    ) -> list[ControlledCommitSurfaceDecision]:
        decisions: list[ControlledCommitSurfaceDecision] = []
        for source in transaction.proposed_surface_updates:
            blockers = list(source.blockers)
            if source.applied:
                blockers.append("surface_blocked_by_source_already_applied")
                decision = "surface_rejected_pre_commit"
                reason = "source_surface_update_already_applied"
            elif source.commit_allowed is False:
                if "surface_blocked_by_commit_not_allowed" not in blockers:
                    blockers.append("surface_blocked_by_commit_not_allowed")
                decision = "surface_rejected_pre_commit"
                reason = "source_surface_commit_not_allowed"
            else:
                decision = "surface_ready_for_future_commit_review"
                reason = "future_explicit_commit_review_required"
            decisions.append(
                ControlledCommitSurfaceDecision(
                    decision_id=f"controlled-commit-surface:{source.update_id}",
                    source_update_id=source.update_id,
                    surface_type=source.surface_type,
                    update_kind=source.update_kind,
                    source_applied=source.applied,
                    source_commit_allowed=source.commit_allowed,
                    commit_decision=decision,
                    commit_decision_reason=reason,
                    committed=False,
                    blockers=blockers,
                    warnings=list(source.warnings),
                    metadata={"source_mutation_transaction_id": transaction.mutation_transaction_id},
                )
            )
        return decisions

    def _audit_requirements(
        self,
        transaction: SimuladoRuntimeProgressMutationTransaction,
    ) -> list[ControlledCommitAuditRequirement]:
        reasons = {
            "commit_policy_confirmation": (
                "Commit policy confirmation remains required before any explicit mutation commit review."
            ),
            "explicit_commit_approval": (
                "Explicit commit approval remains required before any explicit mutation commit review."
            ),
            "audit_confirmation": (
                "Audit confirmation remains required before any explicit mutation commit review."
            ),
            "rollback_verification_confirmation": (
                "Rollback verification remains required before any explicit mutation commit review."
            ),
            "public_answer_key_absence_confirmation": (
                "Public answer key absence confirmation remains required before any explicit mutation commit review."
            ),
            "human_review_confirmation": (
                "Human review confirmation remains required before any explicit mutation commit review."
            ),
        }
        return [
            ControlledCommitAuditRequirement(
                requirement_id=f"controlled-commit-requirement:{requirement_type}:{transaction.mutation_transaction_id}",
                requirement_type=requirement_type,
                required=True,
                satisfied=False,
                reason=reason,
                metadata={},
            )
            for requirement_type, reason in reasons.items()
        ]

    def _audit_trail(
        self,
        *,
        transaction: SimuladoRuntimeProgressMutationTransaction,
        blocker_codes: list[str],
        actor_user_id: str,
    ) -> list[ControlledCommitAuditEntry]:
        events = [
            ("commit_shell_created", "Controlled mutation commit shell artifact was created."),
            ("no_runtime_application", "Runtime application remains disabled in this foundation."),
            ("no_progress_mutation", "Progress mutation remains disabled in this foundation."),
            (
                "no_final_pedagogical_update_event",
                "Final pedagogical update events remain disabled in this foundation.",
            ),
        ]
        if blocker_codes:
            events.append(("commit_blocked", "Controlled mutation commit shell remains blocked in this foundation."))
        event_by_blocker = {
            "blocked_by_mutation_not_valid_for_commit": (
                "mutation_not_valid_for_commit",
                "Source mutation transaction is not valid for commit.",
            ),
            "blocked_by_mutation_commit_not_ready": (
                "mutation_commit_not_ready",
                "Source mutation transaction is not ready for commit.",
            ),
            "blocked_by_rollback_not_available": (
                "rollback_not_available",
                "Rollback remains unavailable for controlled commit review.",
            ),
            "blocked_by_rollback_not_verified": (
                "rollback_not_verified",
                "Rollback remains unverified for controlled commit review.",
            ),
            "blocked_by_commit_policy_missing": (
                "commit_policy_missing",
                "Commit policy confirmation remains missing.",
            ),
            "blocked_by_explicit_commit_approval_missing": (
                "explicit_commit_approval_missing",
                "Explicit commit approval remains missing.",
            ),
            "blocked_by_audit_confirmation_missing": (
                "audit_confirmation_missing",
                "Audit confirmation remains missing.",
            ),
        }
        for code in blocker_codes:
            if code in event_by_blocker:
                events.append(event_by_blocker[code])
        return [
            ControlledCommitAuditEntry(
                audit_id=f"controlled-commit-audit:{event_type}:{transaction.mutation_transaction_id}",
                event_type=event_type,
                actor_user_id=actor_user_id,
                message=message,
                metadata={},
            )
            for event_type, message in events
        ]

    def _blocker_codes(
        self,
        *,
        transaction: SimuladoRuntimeProgressMutationTransaction,
        precondition_summary: ControlledCommitPreconditionSummary,
        rollback_readiness: ControlledCommitRollbackReadiness,
    ) -> list[str]:
        blocker_codes: list[str] = []
        if not precondition_summary.source_transaction_proposal_only:
            blocker_codes.append("blocked_by_transaction_not_proposal_only")
        if not precondition_summary.source_transaction_not_committed:
            blocker_codes.append("blocked_by_transaction_already_committed")
        if (
            precondition_summary.unsafe_public_answer_key_exposure_detected
            or precondition_summary.unsafe_gabarito_exposure_detected
        ):
            blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        if transaction.metadata.get("force_runtime_mutation_disabled") is True or (
            transaction.readiness_state == "blocked_by_runtime_mutation_disabled"
        ):
            blocker_codes.append("blocked_by_runtime_mutation_disabled")
        if not precondition_summary.source_mutation_valid_for_commit:
            blocker_codes.append("blocked_by_mutation_not_valid_for_commit")
        if not precondition_summary.source_mutation_commit_ready:
            blocker_codes.append("blocked_by_mutation_commit_not_ready")
        if not rollback_readiness.rollback_available:
            blocker_codes.append("blocked_by_rollback_not_available")
        if not rollback_readiness.rollback_verified:
            blocker_codes.append("blocked_by_rollback_not_verified")
        if not precondition_summary.all_deltas_commit_allowed:
            blocker_codes.append("blocked_by_deltas_not_commit_allowed")
        if not precondition_summary.all_surfaces_commit_allowed:
            blocker_codes.append("blocked_by_surfaces_not_commit_allowed")
        if not precondition_summary.commit_policy_present:
            blocker_codes.append("blocked_by_commit_policy_missing")
        if not precondition_summary.explicit_commit_approval_present:
            blocker_codes.append("blocked_by_explicit_commit_approval_missing")
        if not precondition_summary.audit_confirmation_present:
            blocker_codes.append("blocked_by_audit_confirmation_missing")
        return blocker_codes

    def _state(self, blocker_codes: list[str]) -> tuple[str, str]:
        if "blocked_by_transaction_not_proposal_only" in blocker_codes:
            return "commit_blocked", "blocked_by_transaction_not_proposal_only"
        if "blocked_by_transaction_already_committed" in blocker_codes:
            return "commit_blocked", "blocked_by_transaction_already_committed"
        if "blocked_by_public_answer_key_exposure_forbidden" in blocker_codes:
            return "commit_blocked", "blocked_by_public_answer_key_exposure_forbidden"
        if "blocked_by_runtime_mutation_disabled" in blocker_codes:
            return "commit_blocked", "blocked_by_runtime_mutation_disabled"
        if "blocked_by_mutation_not_valid_for_commit" in blocker_codes:
            return "commit_blocked", "blocked_by_mutation_not_valid_for_commit"
        if "blocked_by_mutation_commit_not_ready" in blocker_codes:
            return "commit_blocked", "blocked_by_mutation_commit_not_ready"
        if "blocked_by_rollback_not_available" in blocker_codes:
            return "commit_blocked", "blocked_by_rollback_not_available"
        if "blocked_by_rollback_not_verified" in blocker_codes:
            return "commit_blocked", "blocked_by_rollback_not_verified"
        if "blocked_by_deltas_not_commit_allowed" in blocker_codes:
            return "commit_blocked", "blocked_by_deltas_not_commit_allowed"
        if "blocked_by_surfaces_not_commit_allowed" in blocker_codes:
            return "commit_blocked", "blocked_by_surfaces_not_commit_allowed"
        if "blocked_by_commit_policy_missing" in blocker_codes:
            return "commit_blocked", "blocked_by_commit_policy_missing"
        if "blocked_by_explicit_commit_approval_missing" in blocker_codes:
            return "commit_blocked", "blocked_by_explicit_commit_approval_missing"
        if "blocked_by_audit_confirmation_missing" in blocker_codes:
            return "commit_blocked", "blocked_by_audit_confirmation_missing"
        return "commit_shell_created_not_committed", "commit_shell_needs_review"

    def _blockers(
        self,
        transaction: SimuladoRuntimeProgressMutationTransaction,
        blocker_codes: list[str],
    ) -> list[ControlledCommitBlocker]:
        messages = {
            "blocked_by_transaction_not_proposal_only": "Source mutation transaction is not proposal-only.",
            "blocked_by_transaction_already_committed": "Source mutation transaction is already committed.",
            "blocked_by_mutation_not_valid_for_commit": "Source mutation transaction is not valid for commit.",
            "blocked_by_mutation_commit_not_ready": "Source mutation transaction is not ready for commit.",
            "blocked_by_rollback_not_available": "Rollback remains unavailable for controlled commit review.",
            "blocked_by_rollback_not_verified": "Rollback remains unverified for controlled commit review.",
            "blocked_by_deltas_not_commit_allowed": "One or more proposed deltas remain not commit-allowed.",
            "blocked_by_surfaces_not_commit_allowed": "One or more proposed surface updates remain not commit-allowed.",
            "blocked_by_commit_policy_missing": "Commit policy confirmation remains missing.",
            "blocked_by_explicit_commit_approval_missing": "Explicit commit approval remains missing.",
            "blocked_by_audit_confirmation_missing": "Audit confirmation remains missing.",
            "blocked_by_runtime_mutation_disabled": "Runtime mutation remains disabled in this foundation.",
            "blocked_by_public_answer_key_exposure_forbidden": "Potential public answer key exposure forbids controlled commit review.",
        }
        return [
            ControlledCommitBlocker(
                blocker_id=f"controlled-commit-blocker:{code}:{transaction.mutation_transaction_id}",
                code=code,
                severity="blocked",
                message=messages[code],
                related_artifact_type="simulado_runtime_progress_mutation_transaction",
                related_artifact_id=transaction.mutation_transaction_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        transaction: SimuladoRuntimeProgressMutationTransaction,
    ) -> list[ControlledCommitValidationFinding]:
        items = [
            ControlledCommitValidationFinding(
                finding_id=f"controlled-commit-finding:pre-commit-only:{transaction.mutation_transaction_id}",
                code="controlled_runtime_mutation_commit_pre_commit_only",
                severity="info",
                message="Controlled runtime mutation commit shell remains a pre-commit artifact in this foundation.",
                related_artifact_type="simulado_runtime_progress_mutation_transaction",
                related_artifact_id=transaction.mutation_transaction_id,
                metadata={},
            )
        ]
        for source in transaction.validation_findings:
            items.append(
                ControlledCommitValidationFinding(
                    finding_id=f"controlled-commit-finding:{source.code}:{transaction.mutation_transaction_id}",
                    code=source.code,
                    severity=source.severity,
                    message=source.message,
                    related_artifact_type=source.related_artifact_type,
                    related_artifact_id=source.related_artifact_id,
                    metadata={},
                )
            )
        return items

    def _warnings(
        self,
        transaction: SimuladoRuntimeProgressMutationTransaction,
    ) -> list[ControlledCommitWarning]:
        items = [
            ControlledCommitWarning(
                code="controlled_runtime_mutation_commit_not_committed",
                message="Controlled runtime mutation commit shell remains non-committing in this foundation.",
                severity="warning",
                related_artifact_type="simulado_runtime_progress_mutation_transaction",
                related_artifact_id=transaction.mutation_transaction_id,
                metadata={},
            )
        ]
        for source in transaction.warnings:
            items.append(
                ControlledCommitWarning(
                    code=source.code,
                    message=source.message,
                    severity=source.severity,
                    related_artifact_type=source.related_artifact_type,
                    related_artifact_id=source.related_artifact_id,
                    metadata={},
                )
            )
        return items

    def _unsafe_public_answer_key_exposure_detected(
        self,
        transaction: SimuladoRuntimeProgressMutationTransaction,
    ) -> bool:
        return transaction.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"

    def _unsafe_gabarito_exposure_detected(
        self,
        transaction: SimuladoRuntimeProgressMutationTransaction,
    ) -> bool:
        return transaction.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
