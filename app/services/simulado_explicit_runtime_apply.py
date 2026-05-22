from __future__ import annotations

import hashlib
import json

from app.domain.models import (
    ExplicitApplyAuditEntry,
    ExplicitApplyBlocker,
    ExplicitApplyConfirmationSummary,
    ExplicitApplyDecisionSummary,
    ExplicitApplyIntentApproval,
    ExplicitApplySurfaceApproval,
    ExplicitApplyValidationFinding,
    ExplicitApplyWarning,
    SimuladoControlledRuntimeApplyShell,
    SimuladoExplicitRuntimeProgressApply,
)
from app.repositories.json_store import JsonStudyRepository


EXPLICIT_RUNTIME_APPLY_BUILD_METHOD = "heuristic_simulado_explicit_runtime_apply_builder"
ALLOWED_DECISION_TYPES = {
    "approve_for_future_runtime_mutation_review",
    "deny_apply",
    "request_revision",
    "block_apply",
    "mark_not_reviewed",
}


class SimuladoExplicitRuntimeProgressApplyService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_explicit_apply(
        self,
        source_apply_shell_id: str,
        *,
        decision_payload: dict[str, object] | None = None,
        user_id: str | None,
    ) -> SimuladoExplicitRuntimeProgressApply | None:
        if user_id is None:
            return None

        shell = self.repository.get_simulado_controlled_apply_shell_by_id(
            source_apply_shell_id,
            user_id=user_id,
        )
        if shell is None:
            return None

        normalized_payload = self._normalize_payload(decision_payload)
        fingerprint = self._fingerprint(normalized_payload)
        existing = self.repository.get_simulado_explicit_runtime_apply(
            source_apply_shell_id,
            user_id=user_id,
        )
        if existing is not None and existing.metadata.get("decision_fingerprint") == fingerprint:
            return existing

        decision_summary = self._decision_summary(shell, normalized_payload, actor_user_id=user_id)
        confirmation_summary = self._confirmation_summary(shell, normalized_payload)
        blocker_codes = self._blocker_codes(shell, decision_summary, confirmation_summary)
        decision_status, readiness_state = self._state(
            shell=shell,
            decision_summary=decision_summary,
            blocker_codes=blocker_codes,
        )
        explicit_apply_recorded = bool(decision_summary.decision_recorded)
        explicit_apply_approved = (
            decision_summary.approved_for_future_runtime_mutation_review is True
            and confirmation_summary.all_confirmations_satisfied is True
            and "blocked_by_public_answer_key_exposure_forbidden" not in blocker_codes
        )
        intent_approvals = self._intent_approvals(
            shell=shell,
            decision_summary=decision_summary,
            confirmation_summary=confirmation_summary,
            explicit_apply_approved=explicit_apply_approved,
        )
        surface_approvals = self._surface_approvals(
            shell=shell,
            decision_summary=decision_summary,
            confirmation_summary=confirmation_summary,
            explicit_apply_approved=explicit_apply_approved,
        )
        blockers = self._blockers(shell, blocker_codes)
        audit_trail = self._audit_trail(
            shell=shell,
            decision_summary=decision_summary,
            confirmation_summary=confirmation_summary,
            explicit_apply_approved=explicit_apply_approved,
            actor_user_id=user_id,
        )

        result = SimuladoExplicitRuntimeProgressApply(
            explicit_apply_id=f"simulado-explicit-apply:{shell.apply_shell_id}:{fingerprint}",
            user_id=user_id,
            source_apply_shell_id=shell.apply_shell_id,
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
            intent_approvals=intent_approvals,
            surface_approvals=surface_approvals,
            audit_trail=audit_trail,
            blockers=blockers,
            validation_findings=self._findings(shell),
            warnings=self._warnings(shell),
            explicit_apply_recorded=explicit_apply_recorded,
            explicit_apply_approved=explicit_apply_approved,
            apply_request_accepted=False,
            apply_ready_for_runtime_mutation=False,
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
                "build_method": EXPLICIT_RUNTIME_APPLY_BUILD_METHOD,
                "decision_fingerprint": fingerprint,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_explicit_runtime_apply(result, user_id=user_id)
        return result

    def get_explicit_apply(
        self,
        source_apply_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoExplicitRuntimeProgressApply | None:
        return self.repository.get_simulado_explicit_runtime_apply(
            source_apply_shell_id,
            user_id=user_id,
        )

    def get_explicit_apply_by_id(
        self,
        explicit_apply_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoExplicitRuntimeProgressApply | None:
        return self.repository.get_simulado_explicit_runtime_apply_by_id(
            explicit_apply_id,
            user_id=user_id,
        )

    def _normalize_payload(self, payload: dict[str, object] | None) -> dict[str, object]:
        if not isinstance(payload, dict):
            return {
                "decision_type": "mark_not_reviewed",
                "reviewer_id": None,
                "reason": "",
                "confirmations": {
                    "runtime_policy_confirmed": False,
                    "explicit_apply_approval_confirmed": False,
                    "audit_confirmed": False,
                    "rollback_plan_confirmed": False,
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
            "runtime_policy_confirmed": bool(confirmations.get("runtime_policy_confirmed", False)),
            "explicit_apply_approval_confirmed": bool(
                confirmations.get("explicit_apply_approval_confirmed", False)
            ),
            "audit_confirmed": bool(confirmations.get("audit_confirmed", False)),
            "rollback_plan_confirmed": bool(confirmations.get("rollback_plan_confirmed", False)),
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
        shell: SimuladoControlledRuntimeApplyShell,
        payload: dict[str, object],
        *,
        actor_user_id: str,
    ) -> ExplicitApplyDecisionSummary:
        decision_type = str(payload["decision_type"])
        recorded = bool(payload["decision_recorded"])
        reviewer_id = payload["reviewer_id"] or actor_user_id
        reason = str(payload["reason"])
        confirmations = payload["confirmations"]
        all_confirmed = all(bool(value) for value in confirmations.values()) if isinstance(confirmations, dict) else False
        unsafe_exposure = shell.answer_key_publicly_exposed or shell.gabarito_publicly_exposed

        decision_state = "decision_not_reviewed"
        approved = False
        denied = False
        revision_requested = False
        blocked = False
        if decision_type == "approve_for_future_runtime_mutation_review":
            approved = recorded and all_confirmed and not unsafe_exposure
            decision_state = "decision_recorded" if approved or recorded else "decision_not_reviewed"
            blocked = recorded and not approved
        elif decision_type == "deny_apply":
            denied = recorded
            blocked = recorded
            decision_state = "decision_recorded" if recorded else "decision_not_reviewed"
        elif decision_type == "request_revision":
            revision_requested = recorded
            decision_state = "decision_needs_revision" if recorded else "decision_not_reviewed"
        elif decision_type == "block_apply":
            blocked = recorded
            decision_state = "decision_blocked" if recorded else "decision_not_reviewed"
        elif decision_type == "mark_not_reviewed":
            decision_state = "decision_not_reviewed"

        return ExplicitApplyDecisionSummary(
            summary_id=f"explicit-apply-decision:{shell.apply_shell_id}",
            decision_type=decision_type,
            decision_state=decision_state,
            reviewer_id=reviewer_id,
            reason=reason,
            decision_recorded=recorded,
            approved_for_future_runtime_mutation_review=approved,
            denied=denied,
            revision_requested=revision_requested,
            blocked=blocked,
            metadata={},
        )

    def _confirmation_summary(
        self,
        shell: SimuladoControlledRuntimeApplyShell,
        payload: dict[str, object],
    ) -> ExplicitApplyConfirmationSummary:
        confirmations = payload["confirmations"]
        assert isinstance(confirmations, dict)
        return ExplicitApplyConfirmationSummary(
            summary_id=f"explicit-apply-confirmations:{shell.apply_shell_id}",
            runtime_policy_confirmed=bool(confirmations["runtime_policy_confirmed"]),
            explicit_apply_approval_confirmed=bool(confirmations["explicit_apply_approval_confirmed"]),
            audit_confirmed=bool(confirmations["audit_confirmed"]),
            rollback_plan_confirmed=bool(confirmations["rollback_plan_confirmed"]),
            human_review_confirmed=bool(confirmations["human_review_confirmed"]),
            public_answer_key_absence_confirmed=bool(confirmations["public_answer_key_absence_confirmed"]),
            all_confirmations_satisfied=all(bool(value) for value in confirmations.values()),
            metadata={},
        )

    def _blocker_codes(
        self,
        shell: SimuladoControlledRuntimeApplyShell,
        decision_summary: ExplicitApplyDecisionSummary,
        confirmation_summary: ExplicitApplyConfirmationSummary,
    ) -> list[str]:
        blocker_codes: list[str] = []
        if shell.apply_shell_created is not True or shell.runtime_application_applied is True:
            blocker_codes.append("blocked_by_apply_shell_not_ready")
        if shell.answer_key_publicly_exposed or shell.gabarito_publicly_exposed:
            blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        if decision_summary.decision_recorded is False:
            blocker_codes.append("blocked_by_preconditions_not_satisfied")
        if (
            decision_summary.decision_type == "approve_for_future_runtime_mutation_review"
            and confirmation_summary.runtime_policy_confirmed is False
        ):
            blocker_codes.append("blocked_by_runtime_policy_not_confirmed")
        if (
            decision_summary.decision_type == "approve_for_future_runtime_mutation_review"
            and confirmation_summary.explicit_apply_approval_confirmed is False
        ):
            blocker_codes.append("blocked_by_explicit_apply_approval_not_confirmed")
        if (
            decision_summary.decision_type == "approve_for_future_runtime_mutation_review"
            and confirmation_summary.audit_confirmed is False
        ):
            blocker_codes.append("blocked_by_audit_not_confirmed")
        if (
            decision_summary.decision_type == "approve_for_future_runtime_mutation_review"
            and confirmation_summary.rollback_plan_confirmed is False
        ):
            blocker_codes.append("blocked_by_rollback_plan_not_confirmed")
        if (
            decision_summary.decision_type == "approve_for_future_runtime_mutation_review"
            and confirmation_summary.human_review_confirmed is False
        ):
            blocker_codes.append("blocked_by_human_review_not_confirmed")
        if (
            decision_summary.decision_type == "approve_for_future_runtime_mutation_review"
            and confirmation_summary.public_answer_key_absence_confirmed is False
        ):
            blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        if any(item.apply_decision != "intent_ready_for_future_apply_review" for item in shell.intent_decisions):
            blocker_codes.append("blocked_by_intents_not_ready")
        if any(item.apply_decision != "surface_ready_for_future_apply_review" for item in shell.surface_decisions):
            blocker_codes.append("blocked_by_surfaces_not_ready")
        return blocker_codes

    def _state(
        self,
        *,
        shell: SimuladoControlledRuntimeApplyShell,
        decision_summary: ExplicitApplyDecisionSummary,
        blocker_codes: list[str],
    ) -> tuple[str, str]:
        if "blocked_by_apply_shell_not_ready" in blocker_codes:
            return "explicit_apply_blocked", "blocked_by_apply_shell_not_ready"
        if "blocked_by_public_answer_key_exposure_forbidden" in blocker_codes:
            return "explicit_apply_blocked", "blocked_by_public_answer_key_exposure_forbidden"
        if decision_summary.decision_type == "approve_for_future_runtime_mutation_review":
            missing_confirmation_blockers = [
                code
                for code in blocker_codes
                if code
                in {
                    "blocked_by_runtime_policy_not_confirmed",
                    "blocked_by_explicit_apply_approval_not_confirmed",
                    "blocked_by_audit_not_confirmed",
                    "blocked_by_rollback_plan_not_confirmed",
                    "blocked_by_human_review_not_confirmed",
                }
            ]
            if missing_confirmation_blockers:
                return "explicit_apply_blocked", missing_confirmation_blockers[0]
            if decision_summary.approved_for_future_runtime_mutation_review:
                return (
                    "explicit_apply_approved_for_future_runtime_mutation_review",
                    "ready_for_future_runtime_mutation_review",
                )
            return "explicit_apply_blocked", "blocked_by_preconditions_not_satisfied"
        if decision_summary.decision_type == "deny_apply":
            return "explicit_apply_blocked", "explicit_apply_needs_review"
        if decision_summary.decision_type == "request_revision":
            return "explicit_apply_needs_revision", "explicit_apply_needs_review"
        if decision_summary.decision_type == "block_apply":
            return "explicit_apply_blocked", "explicit_apply_needs_review"
        if decision_summary.decision_recorded:
            return "explicit_apply_not_reviewed", "explicit_apply_needs_review"
        return "explicit_apply_not_reviewed", "blocked_by_preconditions_not_satisfied"

    def _intent_approvals(
        self,
        *,
        shell: SimuladoControlledRuntimeApplyShell,
        decision_summary: ExplicitApplyDecisionSummary,
        confirmation_summary: ExplicitApplyConfirmationSummary,
        explicit_apply_approved: bool,
    ) -> list[ExplicitApplyIntentApproval]:
        approvals: list[ExplicitApplyIntentApproval] = []
        for source in shell.intent_decisions:
            blockers = list(source.blockers)
            if decision_summary.decision_type == "approve_for_future_runtime_mutation_review":
                if explicit_apply_approved:
                    approval_state = "intent_approved_for_future_runtime_mutation_review"
                    approved_future = True
                else:
                    approval_state = "intent_blocked"
                    approved_future = False
                    blockers.extend(self._missing_confirmation_intent_blockers(confirmation_summary))
            elif decision_summary.decision_type == "deny_apply":
                approval_state = "intent_denied"
                approved_future = False
            elif decision_summary.decision_type == "request_revision":
                approval_state = "intent_needs_revision"
                approved_future = False
            elif decision_summary.decision_type == "block_apply":
                approval_state = "intent_blocked"
                approved_future = False
            else:
                approval_state = "intent_not_reviewed"
                approved_future = False
            approvals.append(
                ExplicitApplyIntentApproval(
                    approval_id=f"explicit-intent-approval:{source.decision_id}:{shell.apply_shell_id}",
                    source_intent_decision_id=source.decision_id,
                    source_intent_id=source.source_intent_id,
                    intent_type=source.intent_type,
                    proposed_surface=source.proposed_surface,
                    source_apply_decision=source.apply_decision,
                    source_applied=source.applied,
                    explicitly_approved=decision_summary.decision_type
                    == "approve_for_future_runtime_mutation_review",
                    approved_for_future_runtime_mutation_review=approved_future,
                    approved_for_apply_now=False,
                    applied=False,
                    approval_state=approval_state,
                    blockers=blockers,
                    warnings=list(source.warnings),
                    metadata={"source_apply_shell_id": shell.apply_shell_id},
                )
            )
        return approvals

    def _surface_approvals(
        self,
        *,
        shell: SimuladoControlledRuntimeApplyShell,
        decision_summary: ExplicitApplyDecisionSummary,
        confirmation_summary: ExplicitApplyConfirmationSummary,
        explicit_apply_approved: bool,
    ) -> list[ExplicitApplySurfaceApproval]:
        approvals: list[ExplicitApplySurfaceApproval] = []
        for source in shell.surface_decisions:
            blockers = list(source.blockers)
            if decision_summary.decision_type == "approve_for_future_runtime_mutation_review":
                if explicit_apply_approved:
                    approval_state = "surface_approved_for_future_runtime_mutation_review"
                    approved_future = True
                else:
                    approval_state = "surface_blocked"
                    approved_future = False
                    blockers.extend(self._missing_confirmation_surface_blockers(confirmation_summary))
            elif decision_summary.decision_type == "deny_apply":
                approval_state = "surface_denied"
                approved_future = False
            elif decision_summary.decision_type == "request_revision":
                approval_state = "surface_needs_revision"
                approved_future = False
            elif decision_summary.decision_type == "block_apply":
                approval_state = "surface_blocked"
                approved_future = False
            else:
                approval_state = "surface_not_reviewed"
                approved_future = False
            approvals.append(
                ExplicitApplySurfaceApproval(
                    approval_id=f"explicit-surface-approval:{source.decision_id}:{shell.apply_shell_id}",
                    source_surface_decision_id=source.decision_id,
                    source_diff_id=source.source_diff_id,
                    surface_type=source.surface_type,
                    source_apply_decision=source.apply_decision,
                    source_applied=source.applied,
                    explicitly_approved=decision_summary.decision_type
                    == "approve_for_future_runtime_mutation_review",
                    approved_for_future_runtime_mutation_review=approved_future,
                    approved_for_apply_now=False,
                    applied=False,
                    approval_state=approval_state,
                    blockers=blockers,
                    warnings=list(source.warnings),
                    metadata={"source_apply_shell_id": shell.apply_shell_id},
                )
            )
        return approvals

    def _audit_trail(
        self,
        *,
        shell: SimuladoControlledRuntimeApplyShell,
        decision_summary: ExplicitApplyDecisionSummary,
        confirmation_summary: ExplicitApplyConfirmationSummary,
        explicit_apply_approved: bool,
        actor_user_id: str,
    ) -> list[ExplicitApplyAuditEntry]:
        events = [
            ("explicit_apply_created", "Explicit runtime progress apply artifact was created."),
            ("no_runtime_application", "Runtime progress application remains non-applying in this foundation."),
            (
                "no_final_pedagogical_update_event",
                "Final pedagogical update events remain disabled in this foundation.",
            ),
        ]
        if decision_summary.decision_recorded:
            events.append(("explicit_apply_decision_recorded", "Explicit apply decision payload was recorded."))
        if decision_summary.decision_type == "approve_for_future_runtime_mutation_review":
            if explicit_apply_approved:
                events.append(
                    (
                        "explicit_apply_approved_for_future_runtime_mutation_review",
                        "Explicit apply was approved for future runtime mutation review only.",
                    )
                )
            else:
                events.append(("explicit_apply_blocked", "Explicit apply remains blocked in this foundation."))
                if not confirmation_summary.all_confirmations_satisfied:
                    events.append(("confirmations_missing", "Required confirmations remain incomplete."))
        elif decision_summary.decision_type == "deny_apply":
            events.append(("explicit_apply_denied", "Explicit apply was denied."))
        elif decision_summary.decision_type == "request_revision":
            events.append(("explicit_apply_revision_requested", "Explicit apply revision was requested."))
        elif decision_summary.decision_type == "block_apply":
            events.append(("explicit_apply_blocked", "Explicit apply was explicitly blocked."))
        else:
            events.append(("explicit_apply_not_reviewed", "Explicit apply remains not reviewed."))
        return [
            ExplicitApplyAuditEntry(
                audit_id=f"explicit-runtime-apply-audit:{event_type}:{shell.apply_shell_id}",
                event_type=event_type,
                actor_user_id=actor_user_id,
                message=message,
                metadata={},
            )
            for event_type, message in events
        ]

    def _blockers(
        self,
        shell: SimuladoControlledRuntimeApplyShell,
        blocker_codes: list[str],
    ) -> list[ExplicitApplyBlocker]:
        messages = {
            "blocked_by_apply_shell_not_ready": "Controlled apply shell is not ready for explicit review recording.",
            "blocked_by_preconditions_not_satisfied": "Explicit review preconditions remain unsatisfied.",
            "blocked_by_runtime_policy_not_confirmed": "Runtime policy confirmation remains missing.",
            "blocked_by_explicit_apply_approval_not_confirmed": "Explicit apply approval confirmation remains missing.",
            "blocked_by_audit_not_confirmed": "Audit confirmation remains missing.",
            "blocked_by_rollback_plan_not_confirmed": "Rollback plan confirmation remains missing.",
            "blocked_by_human_review_not_confirmed": "Human review confirmation remains missing.",
            "blocked_by_intents_not_ready": "One or more source intent decisions remain not ready.",
            "blocked_by_surfaces_not_ready": "One or more source surface decisions remain not ready.",
            "blocked_by_public_answer_key_exposure_forbidden": "Potential public answer key exposure forbids explicit review approval.",
        }
        return [
            ExplicitApplyBlocker(
                blocker_id=f"explicit-runtime-apply-blocker:{code}:{shell.apply_shell_id}",
                code=code,
                severity="blocked",
                message=messages[code],
                related_artifact_type="simulado_controlled_apply_shell",
                related_artifact_id=shell.apply_shell_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        shell: SimuladoControlledRuntimeApplyShell,
    ) -> list[ExplicitApplyValidationFinding]:
        items = [
            ExplicitApplyValidationFinding(
                finding_id=f"explicit-runtime-apply-finding:explicit-only:{shell.apply_shell_id}",
                code="explicit_runtime_apply_decision_only",
                severity="info",
                message="Explicit runtime apply remains a decision-only artifact in this foundation.",
                related_artifact_type="simulado_controlled_apply_shell",
                related_artifact_id=shell.apply_shell_id,
                metadata={},
            )
        ]
        for source in shell.validation_findings:
            items.append(
                ExplicitApplyValidationFinding(
                    finding_id=f"explicit-runtime-apply-finding:{source.code}:{shell.apply_shell_id}",
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
        shell: SimuladoControlledRuntimeApplyShell,
    ) -> list[ExplicitApplyWarning]:
        items = [
            ExplicitApplyWarning(
                code="explicit_runtime_apply_not_applied",
                message="Explicit runtime apply remains non-applying in this foundation.",
                severity="warning",
                related_artifact_type="simulado_controlled_apply_shell",
                related_artifact_id=shell.apply_shell_id,
                metadata={},
            )
        ]
        for source in shell.warnings:
            items.append(
                ExplicitApplyWarning(
                    code=source.code,
                    message=source.message,
                    severity=source.severity,
                    related_artifact_type=source.related_artifact_type,
                    related_artifact_id=source.related_artifact_id,
                    metadata={},
                )
            )
        return items

    def _fingerprint(self, payload: dict[str, object]) -> str:
        encoded = json.dumps(payload, sort_keys=True, ensure_ascii=True, separators=(",", ":"))
        return hashlib.sha1(encoded.encode("utf-8")).hexdigest()[:12]

    def _bounded_text(self, value: object, *, limit: int) -> str | None:
        if value is None:
            return None
        text = str(value).strip()
        return text[:limit]

    def _missing_confirmation_intent_blockers(
        self,
        confirmation_summary: ExplicitApplyConfirmationSummary,
    ) -> list[str]:
        blockers: list[str] = []
        if confirmation_summary.runtime_policy_confirmed is False:
            blockers.append("blocked_by_runtime_policy_not_confirmed")
        if confirmation_summary.explicit_apply_approval_confirmed is False:
            blockers.append("blocked_by_explicit_apply_approval_not_confirmed")
        if confirmation_summary.audit_confirmed is False:
            blockers.append("blocked_by_audit_not_confirmed")
        if confirmation_summary.rollback_plan_confirmed is False:
            blockers.append("blocked_by_rollback_plan_not_confirmed")
        if confirmation_summary.human_review_confirmed is False:
            blockers.append("blocked_by_human_review_not_confirmed")
        return blockers

    def _missing_confirmation_surface_blockers(
        self,
        confirmation_summary: ExplicitApplyConfirmationSummary,
    ) -> list[str]:
        return self._missing_confirmation_intent_blockers(confirmation_summary)
