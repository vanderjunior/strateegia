from __future__ import annotations

import hashlib
import json

from app.domain.models import (
    ExplicitExecutionApprovalAuditEntry,
    ExplicitExecutionApprovalBlocker,
    ExplicitExecutionApprovalConfirmationSummary,
    ExplicitExecutionApprovalDecisionSummary,
    ExplicitExecutionApprovalValidationFinding,
    ExplicitExecutionApprovalWarning,
    ExplicitProgressExecutionApproval,
    ExplicitSurfaceExecutionApproval,
    SimuladoControlledRuntimeCommitExecutionGuardrail,
    SimuladoExplicitRuntimeCommitExecutionApproval,
)
from app.repositories.json_store import JsonStudyRepository


EXPLICIT_COMMIT_EXECUTION_APPROVAL_BUILD_METHOD = (
    "heuristic_simulado_explicit_runtime_commit_execution_approval_builder"
)
ALLOWED_DECISION_TYPES = {
    "approve_for_future_commit_execution_review",
    "deny_execution",
    "request_revision",
    "block_execution",
    "mark_not_reviewed",
}


class SimuladoExplicitRuntimeCommitExecutionApprovalService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_execution_approval(
        self,
        source_execution_guardrail_id: str,
        *,
        decision_payload: dict[str, object] | None = None,
        user_id: str | None,
    ) -> SimuladoExplicitRuntimeCommitExecutionApproval | None:
        if user_id is None:
            return None

        guardrail = self.repository.get_simulado_controlled_commit_execution_guardrail_by_id(
            source_execution_guardrail_id,
            user_id=user_id,
        )
        if guardrail is None:
            return None

        normalized_payload = self._normalize_payload(decision_payload)
        fingerprint = self._fingerprint(normalized_payload)
        existing = self.repository.get_simulado_explicit_commit_execution_approval(
            source_execution_guardrail_id,
            user_id=user_id,
        )
        if existing is not None and existing.metadata.get("decision_fingerprint") == fingerprint:
            return existing

        decision_summary = self._decision_summary(guardrail, normalized_payload, actor_user_id=user_id)
        confirmation_summary = self._confirmation_summary(guardrail, normalized_payload)
        blocker_codes = self._blocker_codes(guardrail, decision_summary, confirmation_summary)
        explicit_execution_approved = (
            decision_summary.approved_for_future_commit_execution_review is True
            and confirmation_summary.all_confirmations_satisfied is True
            and not blocker_codes
        )
        approved_for_future_commit_execution_review = explicit_execution_approved
        progress_execution_approvals = self._progress_execution_approvals(
            guardrail=guardrail,
            decision_summary=decision_summary,
            explicit_execution_approved=explicit_execution_approved,
        )
        surface_execution_approvals = self._surface_execution_approvals(
            guardrail=guardrail,
            decision_summary=decision_summary,
            explicit_execution_approved=explicit_execution_approved,
        )
        blocker_codes = self._merge_readiness_blockers(
            blocker_codes,
            decision_summary=decision_summary,
            progress_execution_approvals=progress_execution_approvals,
            surface_execution_approvals=surface_execution_approvals,
        )
        decision_status, readiness_state = self._state(
            decision_summary=decision_summary,
            blocker_codes=blocker_codes,
            explicit_execution_approved=explicit_execution_approved,
        )
        result = SimuladoExplicitRuntimeCommitExecutionApproval(
            execution_approval_id=(
                f"simulado-explicit-execution-approval:{guardrail.execution_guardrail_id}:{fingerprint}"
            ),
            user_id=user_id,
            source_execution_guardrail_id=guardrail.execution_guardrail_id,
            source_commit_transaction_id=guardrail.source_commit_transaction_id,
            source_explicit_commit_id=guardrail.source_explicit_commit_id,
            source_commit_shell_id=guardrail.source_commit_shell_id,
            source_mutation_transaction_id=guardrail.source_mutation_transaction_id,
            source_explicit_apply_id=guardrail.source_explicit_apply_id,
            source_apply_shell_id=guardrail.source_apply_shell_id,
            source_application_id=guardrail.source_application_id,
            source_runtime_guardrail_id=guardrail.source_runtime_guardrail_id,
            source_integrated_result_id=guardrail.source_integrated_result_id,
            source_score_result_id=guardrail.source_score_result_id,
            source_progress_guardrail_id=guardrail.source_progress_guardrail_id,
            source_attempt_session_id=guardrail.source_attempt_session_id,
            source_simulado_blueprint_id=guardrail.source_simulado_blueprint_id,
            decision_status=decision_status,
            readiness_state=readiness_state,
            decision_summary=decision_summary,
            confirmation_summary=confirmation_summary,
            progress_execution_approvals=progress_execution_approvals,
            surface_execution_approvals=surface_execution_approvals,
            audit_trail=self._audit_trail(
                guardrail=guardrail,
                decision_summary=decision_summary,
                confirmation_summary=confirmation_summary,
                explicit_execution_approved=explicit_execution_approved,
                actor_user_id=user_id,
            ),
            blockers=self._blockers(guardrail, blocker_codes),
            validation_findings=self._findings(guardrail),
            warnings=self._warnings(guardrail),
            explicit_execution_approval_recorded=bool(decision_summary.decision_recorded),
            explicit_execution_approved=explicit_execution_approved,
            approved_for_future_commit_execution_review=approved_for_future_commit_execution_review,
            approved_for_execution_now=False,
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
                "build_method": EXPLICIT_COMMIT_EXECUTION_APPROVAL_BUILD_METHOD,
                "decision_fingerprint": fingerprint,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_explicit_commit_execution_approval(result, user_id=user_id)
        return result

    def get_execution_approval(
        self,
        source_execution_guardrail_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoExplicitRuntimeCommitExecutionApproval | None:
        return self.repository.get_simulado_explicit_commit_execution_approval(
            source_execution_guardrail_id,
            user_id=user_id,
        )

    def get_execution_approval_by_id(
        self,
        execution_approval_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoExplicitRuntimeCommitExecutionApproval | None:
        return self.repository.get_simulado_explicit_commit_execution_approval_by_id(
            execution_approval_id,
            user_id=user_id,
        )

    def _normalize_payload(self, payload: dict[str, object] | None) -> dict[str, object]:
        if not isinstance(payload, dict):
            return {
                "decision_type": "mark_not_reviewed",
                "reviewer_id": None,
                "reason": "",
                "confirmations": {
                    "final_execution_approval_confirmed": False,
                    "rollback_execution_confirmed": False,
                    "audit_confirmed": False,
                    "runtime_surface_confirmed": False,
                    "public_answer_key_absence_confirmed": False,
                    "human_review_confirmed": False,
                },
                "decision_recorded": False,
            }
        decision_type = payload.get("decision_type")
        if decision_type not in ALLOWED_DECISION_TYPES:
            decision_type = "mark_not_reviewed"
            recorded = False
        else:
            recorded = True
        reviewer_id = self._bounded_text(payload.get("reviewer_id"), limit=120)
        reason = self._bounded_text(payload.get("reason"), limit=280)
        confirmations = payload.get("confirmations")
        if not isinstance(confirmations, dict):
            confirmations = {}
        normalized_confirmations = {
            "final_execution_approval_confirmed": bool(
                confirmations.get("final_execution_approval_confirmed", False)
            ),
            "rollback_execution_confirmed": bool(
                confirmations.get("rollback_execution_confirmed", False)
            ),
            "audit_confirmed": bool(confirmations.get("audit_confirmed", False)),
            "runtime_surface_confirmed": bool(
                confirmations.get("runtime_surface_confirmed", False)
            ),
            "public_answer_key_absence_confirmed": bool(
                confirmations.get("public_answer_key_absence_confirmed", False)
            ),
            "human_review_confirmed": bool(
                confirmations.get("human_review_confirmed", False)
            ),
        }
        return {
            "decision_type": decision_type,
            "reviewer_id": reviewer_id,
            "reason": reason,
            "confirmations": normalized_confirmations,
            "decision_recorded": recorded,
        }

    def _decision_summary(
        self,
        guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail,
        payload: dict[str, object],
        *,
        actor_user_id: str,
    ) -> ExplicitExecutionApprovalDecisionSummary:
        decision_type = str(payload["decision_type"])
        recorded = bool(payload["decision_recorded"])
        reviewer_id = payload["reviewer_id"] or actor_user_id
        reason = str(payload["reason"])
        confirmations = payload["confirmations"]
        all_confirmed = (
            all(bool(value) for value in confirmations.values())
            if isinstance(confirmations, dict)
            else False
        )
        ready_for_future_review = guardrail.readiness_state == "ready_for_future_execution_approval_review"
        safe_source = not self._unsafe_public_answer_key_exposure_detected(guardrail)

        decision_state = "decision_not_reviewed"
        approved = False
        denied = False
        revision_requested = False
        blocked = False
        if decision_type == "approve_for_future_commit_execution_review":
            approved = recorded and all_confirmed and ready_for_future_review and safe_source
            decision_state = "decision_recorded" if (approved or recorded) else "decision_not_reviewed"
            blocked = recorded and not approved
        elif decision_type == "deny_execution":
            denied = recorded
            blocked = recorded
            decision_state = "decision_recorded" if recorded else "decision_not_reviewed"
        elif decision_type == "request_revision":
            revision_requested = recorded
            decision_state = "decision_needs_revision" if recorded else "decision_not_reviewed"
        elif decision_type == "block_execution":
            blocked = recorded
            decision_state = "decision_blocked" if recorded else "decision_not_reviewed"
        elif decision_type == "mark_not_reviewed":
            decision_state = "decision_not_reviewed"

        return ExplicitExecutionApprovalDecisionSummary(
            summary_id=f"explicit-execution-decision:{guardrail.execution_guardrail_id}",
            decision_type=decision_type,
            decision_state=decision_state,
            reviewer_id=reviewer_id,
            reason=reason,
            decision_recorded=recorded,
            approved_for_future_commit_execution_review=approved,
            approved_for_execution_now=False,
            denied=denied,
            revision_requested=revision_requested,
            blocked=blocked,
            metadata={},
        )

    def _confirmation_summary(
        self,
        guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail,
        payload: dict[str, object],
    ) -> ExplicitExecutionApprovalConfirmationSummary:
        confirmations = payload["confirmations"]
        values = [
            bool(confirmations["final_execution_approval_confirmed"]),
            bool(confirmations["rollback_execution_confirmed"]),
            bool(confirmations["audit_confirmed"]),
            bool(confirmations["runtime_surface_confirmed"]),
            bool(confirmations["public_answer_key_absence_confirmed"]),
            bool(confirmations["human_review_confirmed"]),
        ]
        return ExplicitExecutionApprovalConfirmationSummary(
            summary_id=f"explicit-execution-confirmations:{guardrail.execution_guardrail_id}",
            final_execution_approval_confirmed=bool(
                confirmations["final_execution_approval_confirmed"]
            ),
            rollback_execution_confirmed=bool(confirmations["rollback_execution_confirmed"]),
            audit_confirmed=bool(confirmations["audit_confirmed"]),
            runtime_surface_confirmed=bool(confirmations["runtime_surface_confirmed"]),
            public_answer_key_absence_confirmed=bool(
                confirmations["public_answer_key_absence_confirmed"]
            ),
            human_review_confirmed=bool(confirmations["human_review_confirmed"]),
            all_confirmations_satisfied=all(values),
            metadata={},
        )

    def _progress_execution_approvals(
        self,
        *,
        guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail,
        decision_summary: ExplicitExecutionApprovalDecisionSummary,
        explicit_execution_approved: bool,
    ) -> list[ExplicitProgressExecutionApproval]:
        approvals: list[ExplicitProgressExecutionApproval] = []
        for source in guardrail.progress_commit_checks:
            blockers = list(source.blockers)
            warnings = list(source.warnings)
            if explicit_execution_approved:
                state = "progress_execution_approved_for_future_commit_execution_review"
                explicitly_approved = True
                future_approved = True
            elif decision_summary.denied:
                state = "progress_execution_denied"
                explicitly_approved = False
                future_approved = False
            elif decision_summary.revision_requested:
                state = "progress_execution_needs_revision"
                explicitly_approved = False
                future_approved = False
            elif decision_summary.blocked or source.execution_check_state == "progress_commit_execution_blocked":
                state = "progress_execution_blocked"
                explicitly_approved = False
                future_approved = False
            else:
                state = "progress_execution_not_reviewed"
                explicitly_approved = False
                future_approved = False
            approvals.append(
                ExplicitProgressExecutionApproval(
                    approval_id=f"explicit-execution-progress:{source.check_id}",
                    source_check_id=source.check_id,
                    source_planned_commit_id=source.source_planned_commit_id,
                    target_type=source.target_type,
                    delta_kind=source.delta_kind,
                    source_execution_check_state=source.execution_check_state,
                    source_execution_allowed=source.source_execution_allowed,
                    source_executed=source.executed,
                    explicitly_approved=explicitly_approved,
                    approved_for_future_commit_execution_review=future_approved,
                    approved_for_execution_now=False,
                    executed=False,
                    approval_state=state,
                    blockers=blockers,
                    warnings=warnings,
                    metadata={"source_execution_guardrail_id": guardrail.execution_guardrail_id},
                )
            )
        return approvals

    def _surface_execution_approvals(
        self,
        *,
        guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail,
        decision_summary: ExplicitExecutionApprovalDecisionSummary,
        explicit_execution_approved: bool,
    ) -> list[ExplicitSurfaceExecutionApproval]:
        approvals: list[ExplicitSurfaceExecutionApproval] = []
        for source in guardrail.surface_commit_checks:
            blockers = list(source.blockers)
            warnings = list(source.warnings)
            if explicit_execution_approved:
                state = "surface_execution_approved_for_future_commit_execution_review"
                explicitly_approved = True
                future_approved = True
            elif decision_summary.denied:
                state = "surface_execution_denied"
                explicitly_approved = False
                future_approved = False
            elif decision_summary.revision_requested:
                state = "surface_execution_needs_revision"
                explicitly_approved = False
                future_approved = False
            elif decision_summary.blocked or source.execution_check_state == "surface_commit_execution_blocked":
                state = "surface_execution_blocked"
                explicitly_approved = False
                future_approved = False
            else:
                state = "surface_execution_not_reviewed"
                explicitly_approved = False
                future_approved = False
            approvals.append(
                ExplicitSurfaceExecutionApproval(
                    approval_id=f"explicit-execution-surface:{source.check_id}",
                    source_check_id=source.check_id,
                    source_planned_commit_id=source.source_planned_commit_id,
                    surface_type=source.surface_type,
                    update_kind=source.update_kind,
                    source_execution_check_state=source.execution_check_state,
                    source_execution_allowed=source.source_execution_allowed,
                    source_executed=source.executed,
                    explicitly_approved=explicitly_approved,
                    approved_for_future_commit_execution_review=future_approved,
                    approved_for_execution_now=False,
                    executed=False,
                    approval_state=state,
                    blockers=blockers,
                    warnings=warnings,
                    metadata={"source_execution_guardrail_id": guardrail.execution_guardrail_id},
                )
            )
        return approvals

    def _blocker_codes(
        self,
        guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail,
        decision_summary: ExplicitExecutionApprovalDecisionSummary,
        confirmation_summary: ExplicitExecutionApprovalConfirmationSummary,
    ) -> list[str]:
        blocker_codes: list[str] = []
        if self._unsafe_public_answer_key_exposure_detected(guardrail):
            blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        if not guardrail.execution_guardrail_created:
            blocker_codes.append("blocked_by_execution_guardrail_not_ready")
        approve_attempt = (
            decision_summary.decision_type == "approve_for_future_commit_execution_review"
            and decision_summary.decision_recorded
        )
        if approve_attempt:
            if guardrail.readiness_state != "ready_for_future_execution_approval_review":
                blocker_codes.append("blocked_by_execution_guardrail_not_ready")
            if not confirmation_summary.final_execution_approval_confirmed:
                blocker_codes.append("blocked_by_final_execution_approval_not_confirmed")
            if not confirmation_summary.rollback_execution_confirmed:
                blocker_codes.append("blocked_by_rollback_execution_not_confirmed")
            if not confirmation_summary.audit_confirmed:
                blocker_codes.append("blocked_by_audit_not_confirmed")
            if not confirmation_summary.runtime_surface_confirmed:
                blocker_codes.append("blocked_by_runtime_surface_not_confirmed")
            if not confirmation_summary.human_review_confirmed:
                blocker_codes.append("blocked_by_human_review_not_confirmed")
            if not confirmation_summary.public_answer_key_absence_confirmed:
                blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        deduped: list[str] = []
        for code in blocker_codes:
            if code not in deduped:
                deduped.append(code)
        return deduped

    def _merge_readiness_blockers(
        self,
        blocker_codes: list[str],
        *,
        decision_summary: ExplicitExecutionApprovalDecisionSummary,
        progress_execution_approvals: list[ExplicitProgressExecutionApproval],
        surface_execution_approvals: list[ExplicitSurfaceExecutionApproval],
    ) -> list[str]:
        merged = list(blocker_codes)
        approve_attempt = (
            decision_summary.decision_type == "approve_for_future_commit_execution_review"
            and decision_summary.decision_recorded
        )
        if approve_attempt:
            if any(
                item.approval_state in {"progress_execution_blocked", "progress_execution_needs_revision"}
                for item in progress_execution_approvals
            ):
                merged.append("blocked_by_progress_execution_checks_not_ready")
            if any(
                item.approval_state in {"surface_execution_blocked", "surface_execution_needs_revision"}
                for item in surface_execution_approvals
            ):
                merged.append("blocked_by_surface_execution_checks_not_ready")
        deduped: list[str] = []
        for code in merged:
            if code not in deduped:
                deduped.append(code)
        return deduped

    def _state(
        self,
        *,
        decision_summary: ExplicitExecutionApprovalDecisionSummary,
        blocker_codes: list[str],
        explicit_execution_approved: bool,
    ) -> tuple[str, str]:
        if decision_summary.revision_requested:
            return "explicit_execution_approval_needs_revision", "explicit_execution_approval_needs_review"
        if decision_summary.denied:
            return "explicit_execution_approval_blocked", "blocked_by_execution_guardrail_not_ready"
        if decision_summary.blocked and decision_summary.decision_type == "block_execution":
            return "explicit_execution_approval_blocked", "blocked_by_execution_guardrail_not_ready"
        ordered = [
            "blocked_by_public_answer_key_exposure_forbidden",
            "blocked_by_execution_guardrail_not_ready",
            "blocked_by_final_execution_approval_not_confirmed",
            "blocked_by_rollback_execution_not_confirmed",
            "blocked_by_audit_not_confirmed",
            "blocked_by_runtime_surface_not_confirmed",
            "blocked_by_human_review_not_confirmed",
            "blocked_by_progress_execution_checks_not_ready",
            "blocked_by_surface_execution_checks_not_ready",
        ]
        for code in ordered:
            if code in blocker_codes:
                return "explicit_execution_approval_blocked", code
        if explicit_execution_approved:
            return (
                "explicit_execution_approved_for_future_commit_execution_review",
                "ready_for_future_commit_execution_review",
            )
        if decision_summary.decision_recorded and decision_summary.decision_type == "mark_not_reviewed":
            return "explicit_execution_approval_not_reviewed", "explicit_execution_approval_needs_review"
        if decision_summary.decision_recorded:
            return "explicit_execution_approval_blocked", "explicit_execution_approval_needs_review"
        return "explicit_execution_approval_not_reviewed", "explicit_execution_approval_needs_review"

    def _audit_trail(
        self,
        *,
        guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail,
        decision_summary: ExplicitExecutionApprovalDecisionSummary,
        confirmation_summary: ExplicitExecutionApprovalConfirmationSummary,
        explicit_execution_approved: bool,
        actor_user_id: str,
    ) -> list[ExplicitExecutionApprovalAuditEntry]:
        events = [
            (
                "explicit_execution_approval_created",
                "Explicit runtime commit execution approval artifact was created.",
            ),
            ("no_commit_execution", "Commit execution remains disabled in this foundation."),
            ("no_mutation_commit", "Mutation commit remains disabled in this foundation."),
            ("no_runtime_application", "Runtime application remains disabled in this foundation."),
            ("no_progress_mutation", "Progress mutation remains disabled in this foundation."),
            (
                "no_final_pedagogical_update_event",
                "Final pedagogical update events remain disabled in this foundation.",
            ),
        ]
        if decision_summary.decision_recorded:
            events.append(
                (
                    "explicit_execution_decision_recorded",
                    "Explicit runtime commit execution decision was recorded.",
                )
            )
        if (
            decision_summary.decision_type == "approve_for_future_commit_execution_review"
            and decision_summary.decision_recorded
            and not confirmation_summary.all_confirmations_satisfied
        ):
            events.append(("confirmations_missing", "Required execution confirmations remain missing."))
        if explicit_execution_approved:
            events.append(
                (
                    "explicit_execution_approved_for_future_commit_execution_review",
                    "Explicit execution was approved for future controlled execution review only.",
                )
            )
        elif decision_summary.denied:
            events.append(("explicit_execution_denied", "Explicit execution was denied."))
        elif decision_summary.revision_requested:
            events.append(("explicit_execution_revision_requested", "Explicit execution revision was requested."))
        elif decision_summary.blocked:
            events.append(("explicit_execution_blocked", "Explicit execution remains blocked."))
        else:
            events.append(("explicit_execution_not_reviewed", "Explicit execution remains not reviewed."))
        return [
            ExplicitExecutionApprovalAuditEntry(
                audit_id=f"explicit-execution-audit:{event_type}:{guardrail.execution_guardrail_id}",
                event_type=event_type,
                actor_user_id=actor_user_id,
                message=message,
                metadata={},
            )
            for event_type, message in events
        ]

    def _blockers(
        self,
        guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail,
        blocker_codes: list[str],
    ) -> list[ExplicitExecutionApprovalBlocker]:
        messages = {
            "blocked_by_execution_guardrail_not_ready": "Controlled execution guardrail is not ready for future approval review.",
            "blocked_by_commit_execution_allowed_false": "Commit execution remains disabled in this foundation.",
            "blocked_by_commit_execution_not_ready": "Commit execution readiness remains false in this foundation.",
            "blocked_by_final_execution_approval_not_confirmed": "Final execution approval confirmation remains missing.",
            "blocked_by_rollback_execution_not_confirmed": "Rollback execution confirmation remains missing.",
            "blocked_by_audit_not_confirmed": "Audit confirmation remains missing.",
            "blocked_by_runtime_surface_not_confirmed": "Runtime surface confirmation remains missing.",
            "blocked_by_human_review_not_confirmed": "Human review confirmation remains missing.",
            "blocked_by_progress_execution_checks_not_ready": "One or more progress execution checks remain not ready for future review.",
            "blocked_by_surface_execution_checks_not_ready": "One or more surface execution checks remain not ready for future review.",
            "blocked_by_public_answer_key_exposure_forbidden": "Potential public answer key or gabarito exposure forbids explicit execution approval.",
        }
        return [
            ExplicitExecutionApprovalBlocker(
                blocker_id=f"explicit-execution-blocker:{code}:{guardrail.execution_guardrail_id}",
                code=code,
                severity="blocked",
                message=messages[code],
                related_artifact_type="simulado_controlled_runtime_commit_execution_guardrail",
                related_artifact_id=guardrail.execution_guardrail_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail,
    ) -> list[ExplicitExecutionApprovalValidationFinding]:
        return [
            ExplicitExecutionApprovalValidationFinding(
                finding_id=f"explicit-execution-finding:{guardrail.execution_guardrail_id}",
                code="explicit_runtime_commit_execution_approval_decision_only",
                message="This artifact records explicit runtime commit execution approval metadata only.",
                related_artifact_type="simulado_controlled_runtime_commit_execution_guardrail",
                related_artifact_id=guardrail.execution_guardrail_id,
                metadata={},
            )
        ]

    def _warnings(
        self,
        guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail,
    ) -> list[ExplicitExecutionApprovalWarning]:
        return [
            ExplicitExecutionApprovalWarning(
                code="no_commit_execution",
                message="Commit execution remains intentionally disabled in this foundation.",
                related_artifact_type="simulado_controlled_runtime_commit_execution_guardrail",
                related_artifact_id=guardrail.execution_guardrail_id,
                metadata={},
            )
        ]

    def _unsafe_public_answer_key_exposure_detected(
        self,
        guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail,
    ) -> bool:
        return bool(guardrail.answer_key_publicly_exposed) or (
            guardrail.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
        ) or any(
            blocker.code == "blocked_by_public_answer_key_exposure_forbidden"
            for blocker in guardrail.blockers
        )

    def _fingerprint(self, payload: dict[str, object]) -> str:
        serialized = json.dumps(payload, ensure_ascii=True, sort_keys=True)
        return hashlib.sha256(serialized.encode("utf-8")).hexdigest()[:16]

    def _bounded_text(self, value: object, *, limit: int) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        if len(text) > limit:
            return text[:limit]
        return text
