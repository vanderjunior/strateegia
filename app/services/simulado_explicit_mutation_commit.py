from __future__ import annotations

import hashlib
import json

from app.domain.models import (
    ControlledCommitDeltaDecision,
    ControlledCommitSurfaceDecision,
    SimuladoControlledRuntimeMutationCommitShell,
    ExplicitCommitAuditEntry,
    ExplicitCommitBlocker,
    ExplicitCommitConfirmationSummary,
    ExplicitCommitDecisionSummary,
    ExplicitCommitDeltaApproval,
    ExplicitCommitSurfaceApproval,
    ExplicitCommitValidationFinding,
    ExplicitCommitWarning,
    SimuladoExplicitRuntimeMutationCommit,
)
from app.repositories.json_store import JsonStudyRepository


EXPLICIT_MUTATION_COMMIT_BUILD_METHOD = "heuristic_simulado_explicit_runtime_mutation_commit_builder"
ALLOWED_DECISION_TYPES = {
    "approve_for_future_mutation_commit_review",
    "deny_commit",
    "request_revision",
    "block_commit",
    "mark_not_reviewed",
}


class SimuladoExplicitRuntimeMutationCommitService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_explicit_commit(
        self,
        source_commit_shell_id: str,
        *,
        decision_payload: dict[str, object] | None = None,
        user_id: str | None,
    ) -> SimuladoExplicitRuntimeMutationCommit | None:
        if user_id is None:
            return None

        shell = self.repository.get_simulado_controlled_mutation_commit_shell_by_id(
            source_commit_shell_id,
            user_id=user_id,
        )
        if shell is None:
            return None

        normalized_payload = self._normalize_payload(decision_payload)
        fingerprint = self._fingerprint(normalized_payload)
        existing = self.repository.get_simulado_explicit_mutation_commit(
            source_commit_shell_id,
            user_id=user_id,
        )
        if existing is not None and existing.metadata.get("decision_fingerprint") == fingerprint:
            return existing

        decision_summary = self._decision_summary(shell, normalized_payload, actor_user_id=user_id)
        confirmation_summary = self._confirmation_summary(shell, normalized_payload)
        blocker_codes = self._blocker_codes(shell, decision_summary, confirmation_summary)
        decision_status, readiness_state = self._state(
            decision_summary=decision_summary,
            blocker_codes=blocker_codes,
        )
        explicit_commit_recorded = bool(decision_summary.decision_recorded)
        explicit_commit_approved = (
            decision_summary.approved_for_future_mutation_commit_review is True
            and confirmation_summary.all_confirmations_satisfied is True
            and "blocked_by_public_answer_key_exposure_forbidden" not in blocker_codes
        )
        approved_for_future_review = explicit_commit_approved
        delta_approvals = self._delta_approvals(
            shell=shell,
            decision_summary=decision_summary,
            explicit_commit_approved=explicit_commit_approved,
        )
        surface_approvals = self._surface_approvals(
            shell=shell,
            decision_summary=decision_summary,
            explicit_commit_approved=explicit_commit_approved,
        )
        blockers = self._blockers(shell, blocker_codes)
        audit_trail = self._audit_trail(
            shell=shell,
            decision_summary=decision_summary,
            confirmation_summary=confirmation_summary,
            explicit_commit_approved=explicit_commit_approved,
            actor_user_id=user_id,
        )

        result = SimuladoExplicitRuntimeMutationCommit(
            explicit_commit_id=f"simulado-explicit-commit:{shell.commit_shell_id}:{fingerprint}",
            user_id=user_id,
            source_commit_shell_id=shell.commit_shell_id,
            source_mutation_transaction_id=shell.source_mutation_transaction_id,
            source_explicit_apply_id=shell.source_explicit_apply_id,
            source_apply_shell_id=shell.source_apply_shell_id,
            source_application_id=shell.source_application_id,
            source_runtime_guardrail_id=shell.source_runtime_guardrail_id,
            source_integrated_result_id=shell.source_integrated_result_id,
            source_score_result_id=shell.source_score_result_id,
            source_progress_guardrail_id=shell.source_progress_guardrail_id,
            source_attempt_session_id=shell.source_attempt_session_id,
            source_simulado_blueprint_id=shell.source_simulado_blueprint_id,
            decision_status=decision_status,
            readiness_state=readiness_state,
            decision_summary=decision_summary,
            confirmation_summary=confirmation_summary,
            delta_approvals=delta_approvals,
            surface_approvals=surface_approvals,
            audit_trail=audit_trail,
            blockers=blockers,
            validation_findings=self._findings(shell),
            warnings=self._warnings(shell),
            explicit_commit_recorded=explicit_commit_recorded,
            explicit_commit_approved=explicit_commit_approved,
            approved_for_future_mutation_commit_review=approved_for_future_review,
            approved_for_commit_now=False,
            commit_request_accepted=False,
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
            no_mutation_commit=True,
            no_mutation_commit_event_created=True,
            no_final_pedagogical_update_event=True,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            metadata={
                "build_method": EXPLICIT_MUTATION_COMMIT_BUILD_METHOD,
                "decision_fingerprint": fingerprint,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_explicit_mutation_commit(result, user_id=user_id)
        return result

    def get_explicit_commit(
        self,
        source_commit_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoExplicitRuntimeMutationCommit | None:
        return self.repository.get_simulado_explicit_mutation_commit(
            source_commit_shell_id,
            user_id=user_id,
        )

    def get_explicit_commit_by_id(
        self,
        explicit_commit_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoExplicitRuntimeMutationCommit | None:
        return self.repository.get_simulado_explicit_mutation_commit_by_id(
            explicit_commit_id,
            user_id=user_id,
        )

    def _normalize_payload(self, payload: dict[str, object] | None) -> dict[str, object]:
        if not isinstance(payload, dict):
            return {
                "decision_type": "mark_not_reviewed",
                "reviewer_id": None,
                "reason": "",
                "confirmations": {
                    "commit_policy_confirmed": False,
                    "explicit_commit_approval_confirmed": False,
                    "audit_confirmed": False,
                    "rollback_verified_confirmed": False,
                    "human_review_confirmed": False,
                    "public_answer_key_absence_confirmed": False,
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
            "commit_policy_confirmed": bool(confirmations.get("commit_policy_confirmed", False)),
            "explicit_commit_approval_confirmed": bool(
                confirmations.get("explicit_commit_approval_confirmed", False)
            ),
            "audit_confirmed": bool(confirmations.get("audit_confirmed", False)),
            "rollback_verified_confirmed": bool(confirmations.get("rollback_verified_confirmed", False)),
            "human_review_confirmed": bool(confirmations.get("human_review_confirmed", False)),
            "public_answer_key_absence_confirmed": bool(
                confirmations.get("public_answer_key_absence_confirmed", False)
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
        shell: SimuladoControlledRuntimeMutationCommitShell,
        payload: dict[str, object],
        *,
        actor_user_id: str,
    ) -> ExplicitCommitDecisionSummary:
        decision_type = str(payload["decision_type"])
        recorded = bool(payload["decision_recorded"])
        reviewer_id = payload["reviewer_id"] or actor_user_id
        reason = str(payload["reason"])
        confirmations = payload["confirmations"]
        all_confirmed = all(bool(value) for value in confirmations.values()) if isinstance(confirmations, dict) else False
        unsafe_exposure = self._unsafe_public_answer_key_exposure_detected(shell)

        decision_state = "decision_not_reviewed"
        approved = False
        denied = False
        revision_requested = False
        blocked = False
        if decision_type == "approve_for_future_mutation_commit_review":
            approved = recorded and all_confirmed and not unsafe_exposure
            decision_state = "decision_recorded" if approved or recorded else "decision_not_reviewed"
            blocked = recorded and not approved
        elif decision_type == "deny_commit":
            denied = recorded
            blocked = recorded
            decision_state = "decision_recorded" if recorded else "decision_not_reviewed"
        elif decision_type == "request_revision":
            revision_requested = recorded
            decision_state = "decision_needs_revision" if recorded else "decision_not_reviewed"
        elif decision_type == "block_commit":
            blocked = recorded
            decision_state = "decision_blocked" if recorded else "decision_not_reviewed"
        elif decision_type == "mark_not_reviewed":
            decision_state = "decision_not_reviewed"

        return ExplicitCommitDecisionSummary(
            summary_id=f"explicit-commit-decision:{shell.commit_shell_id}",
            decision_type=decision_type,
            decision_state=decision_state,
            reviewer_id=reviewer_id,
            reason=reason,
            decision_recorded=recorded,
            approved_for_future_mutation_commit_review=approved,
            approved_for_commit_now=False,
            denied=denied,
            revision_requested=revision_requested,
            blocked=blocked,
            metadata={},
        )

    def _confirmation_summary(
        self,
        shell: SimuladoControlledRuntimeMutationCommitShell,
        payload: dict[str, object],
    ) -> ExplicitCommitConfirmationSummary:
        confirmations = payload["confirmations"]
        values = [
            bool(confirmations["commit_policy_confirmed"]),
            bool(confirmations["explicit_commit_approval_confirmed"]),
            bool(confirmations["audit_confirmed"]),
            bool(confirmations["rollback_verified_confirmed"]),
            bool(confirmations["human_review_confirmed"]),
            bool(confirmations["public_answer_key_absence_confirmed"]),
        ]
        return ExplicitCommitConfirmationSummary(
            summary_id=f"explicit-commit-confirmations:{shell.commit_shell_id}",
            commit_policy_confirmed=bool(confirmations["commit_policy_confirmed"]),
            explicit_commit_approval_confirmed=bool(confirmations["explicit_commit_approval_confirmed"]),
            audit_confirmed=bool(confirmations["audit_confirmed"]),
            rollback_verified_confirmed=bool(confirmations["rollback_verified_confirmed"]),
            human_review_confirmed=bool(confirmations["human_review_confirmed"]),
            public_answer_key_absence_confirmed=bool(confirmations["public_answer_key_absence_confirmed"]),
            all_confirmations_satisfied=all(values),
            metadata={},
        )

    def _delta_approvals(
        self,
        *,
        shell: SimuladoControlledRuntimeMutationCommitShell,
        decision_summary: ExplicitCommitDecisionSummary,
        explicit_commit_approved: bool,
    ) -> list[ExplicitCommitDeltaApproval]:
        approvals: list[ExplicitCommitDeltaApproval] = []
        for source in shell.delta_commit_decisions:
            blockers = list(source.blockers)
            warnings = list(source.warnings)
            if explicit_commit_approved:
                state = "delta_approved_for_future_mutation_commit_review"
                explicitly_approved = True
                future_approved = True
            elif decision_summary.denied:
                state = "delta_denied"
                explicitly_approved = False
                future_approved = False
            elif decision_summary.revision_requested:
                state = "delta_needs_revision"
                explicitly_approved = False
                future_approved = False
            elif decision_summary.blocked or source.commit_decision == "delta_rejected_pre_commit":
                state = "delta_blocked"
                explicitly_approved = False
                future_approved = False
            else:
                state = "delta_not_reviewed"
                explicitly_approved = False
                future_approved = False
            approvals.append(
                ExplicitCommitDeltaApproval(
                    approval_id=f"explicit-commit-delta:{source.decision_id}",
                    source_delta_decision_id=source.decision_id,
                    source_delta_id=source.source_delta_id,
                    target_type=source.target_type,
                    delta_kind=source.delta_kind,
                    source_commit_decision=source.commit_decision,
                    source_committed=source.committed,
                    explicitly_approved=explicitly_approved,
                    approved_for_future_mutation_commit_review=future_approved,
                    approved_for_commit_now=False,
                    committed=False,
                    approval_state=state,
                    blockers=blockers,
                    warnings=warnings,
                    metadata={"source_commit_shell_id": shell.commit_shell_id},
                )
            )
        return approvals

    def _surface_approvals(
        self,
        *,
        shell: SimuladoControlledRuntimeMutationCommitShell,
        decision_summary: ExplicitCommitDecisionSummary,
        explicit_commit_approved: bool,
    ) -> list[ExplicitCommitSurfaceApproval]:
        approvals: list[ExplicitCommitSurfaceApproval] = []
        for source in shell.surface_commit_decisions:
            blockers = list(source.blockers)
            warnings = list(source.warnings)
            if explicit_commit_approved:
                state = "surface_approved_for_future_mutation_commit_review"
                explicitly_approved = True
                future_approved = True
            elif decision_summary.denied:
                state = "surface_denied"
                explicitly_approved = False
                future_approved = False
            elif decision_summary.revision_requested:
                state = "surface_needs_revision"
                explicitly_approved = False
                future_approved = False
            elif decision_summary.blocked or source.commit_decision == "surface_rejected_pre_commit":
                state = "surface_blocked"
                explicitly_approved = False
                future_approved = False
            else:
                state = "surface_not_reviewed"
                explicitly_approved = False
                future_approved = False
            approvals.append(
                ExplicitCommitSurfaceApproval(
                    approval_id=f"explicit-commit-surface:{source.decision_id}",
                    source_surface_decision_id=source.decision_id,
                    source_update_id=source.source_update_id,
                    surface_type=source.surface_type,
                    update_kind=source.update_kind,
                    source_commit_decision=source.commit_decision,
                    source_committed=source.committed,
                    explicitly_approved=explicitly_approved,
                    approved_for_future_mutation_commit_review=future_approved,
                    approved_for_commit_now=False,
                    committed=False,
                    approval_state=state,
                    blockers=blockers,
                    warnings=warnings,
                    metadata={"source_commit_shell_id": shell.commit_shell_id},
                )
            )
        return approvals

    def _audit_trail(
        self,
        *,
        shell: SimuladoControlledRuntimeMutationCommitShell,
        decision_summary: ExplicitCommitDecisionSummary,
        confirmation_summary: ExplicitCommitConfirmationSummary,
        explicit_commit_approved: bool,
        actor_user_id: str,
    ) -> list[ExplicitCommitAuditEntry]:
        events = [
            ("explicit_commit_created", "Explicit runtime mutation commit artifact was created."),
            ("no_mutation_commit", "Mutation commit remains disabled in this foundation."),
            ("no_runtime_application", "Runtime application remains disabled in this foundation."),
            ("no_progress_mutation", "Progress mutation remains disabled in this foundation."),
            (
                "no_final_pedagogical_update_event",
                "Final pedagogical update events remain disabled in this foundation.",
            ),
        ]
        if decision_summary.decision_recorded:
            events.append(("explicit_commit_decision_recorded", "Explicit mutation commit decision was recorded."))
        if (
            decision_summary.decision_type == "approve_for_future_mutation_commit_review"
            and decision_summary.decision_recorded
            and not confirmation_summary.all_confirmations_satisfied
        ):
            events.append(("confirmations_missing", "Required commit confirmations remain missing."))
        if explicit_commit_approved:
            events.append(
                (
                    "explicit_commit_approved_for_future_mutation_commit_review",
                    "Explicit commit was approved for future mutation commit review only.",
                )
            )
        elif decision_summary.denied:
            events.append(("explicit_commit_denied", "Explicit mutation commit was denied."))
        elif decision_summary.revision_requested:
            events.append(("explicit_commit_revision_requested", "Explicit mutation commit revision was requested."))
        elif decision_summary.blocked:
            events.append(("explicit_commit_blocked", "Explicit mutation commit remains blocked."))
        else:
            events.append(("explicit_commit_not_reviewed", "Explicit mutation commit remains not reviewed."))
        return [
            ExplicitCommitAuditEntry(
                audit_id=f"explicit-commit-audit:{event_type}:{shell.commit_shell_id}",
                event_type=event_type,
                actor_user_id=actor_user_id,
                message=message,
                metadata={},
            )
            for event_type, message in events
        ]

    def _blocker_codes(
        self,
        shell: SimuladoControlledRuntimeMutationCommitShell,
        decision_summary: ExplicitCommitDecisionSummary,
        confirmation_summary: ExplicitCommitConfirmationSummary,
    ) -> list[str]:
        blocker_codes: list[str] = []
        if self._unsafe_public_answer_key_exposure_detected(shell):
            blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        approve_attempt = (
            decision_summary.decision_type == "approve_for_future_mutation_commit_review"
            and decision_summary.decision_recorded
        )
        if approve_attempt:
            if not confirmation_summary.commit_policy_confirmed:
                blocker_codes.append("blocked_by_commit_policy_not_confirmed")
            if not confirmation_summary.explicit_commit_approval_confirmed:
                blocker_codes.append("blocked_by_explicit_commit_approval_not_confirmed")
            if not confirmation_summary.audit_confirmed:
                blocker_codes.append("blocked_by_audit_not_confirmed")
            if not confirmation_summary.rollback_verified_confirmed:
                blocker_codes.append("blocked_by_rollback_not_verified")
            if not confirmation_summary.human_review_confirmed:
                blocker_codes.append("blocked_by_human_review_not_confirmed")
            if not confirmation_summary.public_answer_key_absence_confirmed:
                blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        return blocker_codes

    def _state(
        self,
        *,
        decision_summary: ExplicitCommitDecisionSummary,
        blocker_codes: list[str],
    ) -> tuple[str, str]:
        if decision_summary.revision_requested:
            return "explicit_commit_needs_revision", "explicit_commit_needs_review"
        if decision_summary.denied:
            return "explicit_commit_blocked", "blocked_by_commit_preconditions_not_satisfied"
        if decision_summary.blocked and decision_summary.decision_type == "block_commit":
            return "explicit_commit_blocked", "blocked_by_commit_preconditions_not_satisfied"
        if "blocked_by_public_answer_key_exposure_forbidden" in blocker_codes:
            return "explicit_commit_blocked", "blocked_by_public_answer_key_exposure_forbidden"
        if "blocked_by_commit_policy_not_confirmed" in blocker_codes:
            return "explicit_commit_blocked", "blocked_by_commit_policy_not_confirmed"
        if "blocked_by_explicit_commit_approval_not_confirmed" in blocker_codes:
            return "explicit_commit_blocked", "blocked_by_explicit_commit_approval_not_confirmed"
        if "blocked_by_audit_not_confirmed" in blocker_codes:
            return "explicit_commit_blocked", "blocked_by_audit_not_confirmed"
        if "blocked_by_rollback_not_verified" in blocker_codes:
            return "explicit_commit_blocked", "blocked_by_rollback_not_verified"
        if "blocked_by_human_review_not_confirmed" in blocker_codes:
            return "explicit_commit_blocked", "blocked_by_human_review_not_confirmed"
        if "blocked_by_deltas_not_ready" in blocker_codes:
            return "explicit_commit_blocked", "blocked_by_deltas_not_ready"
        if "blocked_by_surfaces_not_ready" in blocker_codes:
            return "explicit_commit_blocked", "blocked_by_surfaces_not_ready"
        if decision_summary.approved_for_future_mutation_commit_review:
            return (
                "explicit_commit_approved_for_future_mutation_commit_review",
                "ready_for_future_mutation_commit_review",
            )
        if decision_summary.decision_recorded and decision_summary.decision_type == "mark_not_reviewed":
            return "explicit_commit_not_reviewed", "explicit_commit_needs_review"
        if decision_summary.decision_recorded:
            return "explicit_commit_blocked", "blocked_by_commit_preconditions_not_satisfied"
        return "explicit_commit_not_reviewed", "explicit_commit_needs_review"

    def _blockers(
        self,
        shell: SimuladoControlledRuntimeMutationCommitShell,
        blocker_codes: list[str],
    ) -> list[ExplicitCommitBlocker]:
        messages = {
            "blocked_by_commit_policy_not_confirmed": "Commit policy confirmation remains missing.",
            "blocked_by_explicit_commit_approval_not_confirmed": "Explicit commit approval confirmation remains missing.",
            "blocked_by_audit_not_confirmed": "Audit confirmation remains missing.",
            "blocked_by_rollback_not_verified": "Rollback verification confirmation remains missing.",
            "blocked_by_human_review_not_confirmed": "Human review confirmation remains missing.",
            "blocked_by_deltas_not_ready": "One or more delta commit decisions remain not ready for future commit review.",
            "blocked_by_surfaces_not_ready": "One or more surface commit decisions remain not ready for future commit review.",
            "blocked_by_commit_preconditions_not_satisfied": "Controlled commit shell preconditions remain unsatisfied.",
            "blocked_by_public_answer_key_exposure_forbidden": "Potential public answer key exposure forbids explicit commit approval.",
        }
        return [
            ExplicitCommitBlocker(
                blocker_id=f"explicit-commit-blocker:{code}:{shell.commit_shell_id}",
                code=code,
                severity="blocked",
                message=messages[code],
                related_artifact_type="simulado_controlled_runtime_mutation_commit_shell",
                related_artifact_id=shell.commit_shell_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        shell: SimuladoControlledRuntimeMutationCommitShell,
    ) -> list[ExplicitCommitValidationFinding]:
        items = [
            ExplicitCommitValidationFinding(
                finding_id=f"explicit-commit-finding:decision-only:{shell.commit_shell_id}",
                code="explicit_runtime_mutation_commit_decision_only",
                severity="info",
                message="Explicit runtime mutation commit remains a decision artifact in this foundation.",
                related_artifact_type="simulado_controlled_runtime_mutation_commit_shell",
                related_artifact_id=shell.commit_shell_id,
                metadata={},
            )
        ]
        for source in shell.validation_findings:
            items.append(
                ExplicitCommitValidationFinding(
                    finding_id=f"explicit-commit-finding:{source.code}:{shell.commit_shell_id}",
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
        shell: SimuladoControlledRuntimeMutationCommitShell,
    ) -> list[ExplicitCommitWarning]:
        items = [
            ExplicitCommitWarning(
                code="explicit_runtime_mutation_commit_no_commit",
                message="Explicit runtime mutation commit remains non-committing in this foundation.",
                severity="warning",
                related_artifact_type="simulado_controlled_runtime_mutation_commit_shell",
                related_artifact_id=shell.commit_shell_id,
                metadata={},
            )
        ]
        for source in shell.warnings:
            items.append(
                ExplicitCommitWarning(
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
        shell: SimuladoControlledRuntimeMutationCommitShell,
    ) -> bool:
        return (
            shell.answer_key_publicly_exposed
            or shell.gabarito_publicly_exposed
            or shell.precondition_summary.unsafe_public_answer_key_exposure_detected
            or shell.precondition_summary.unsafe_gabarito_exposure_detected
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
