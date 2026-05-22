from __future__ import annotations

from app.domain.models import (
    ControlledApplyAuditEntry,
    ControlledApplyAuditRequirement,
    ControlledApplyBlocker,
    ControlledApplyIntentDecision,
    ControlledApplyPreconditionSummary,
    ControlledApplySurfaceDecision,
    ControlledApplyValidationFinding,
    ControlledApplyWarning,
    SimuladoControlledRuntimeApplyShell,
    SimuladoRuntimeProgressApplication,
)
from app.repositories.json_store import JsonStudyRepository


CONTROLLED_APPLY_SHELL_BUILD_METHOD = "heuristic_simulado_controlled_apply_shell_builder"


class SimuladoControlledRuntimeApplyShellService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_apply_shell(
        self,
        source_application_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeApplyShell | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_controlled_apply_shell(
            source_application_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        application = self.repository.get_simulado_runtime_progress_application_by_id(
            source_application_id,
            user_id=user_id,
        )
        if application is None:
            return None

        precondition_summary = self._precondition_summary(application)
        blocker_codes = self._blocker_codes(application, precondition_summary)
        apply_status, readiness_state = self._state(application, blocker_codes)
        intent_decisions = self._intent_decisions(application, precondition_summary)
        surface_decisions = self._surface_decisions(application, precondition_summary)
        audit_requirements = self._audit_requirements(application, precondition_summary)
        audit_trail = self._audit_trail(
            application=application,
            readiness_state=readiness_state,
            actor_user_id=user_id,
        )
        blockers = self._blockers(application, blocker_codes)

        result = SimuladoControlledRuntimeApplyShell(
            apply_shell_id=f"simulado-controlled-apply-shell:{application.application_id}",
            user_id=user_id,
            source_application_id=application.application_id,
            source_runtime_guardrail_id=application.source_runtime_guardrail_id,
            source_integrated_result_id=application.source_integrated_result_id,
            source_score_result_id=application.source_score_result_id,
            source_progress_guardrail_id=application.source_progress_guardrail_id,
            source_attempt_session_id=application.source_attempt_session_id,
            source_simulado_blueprint_id=application.source_simulado_blueprint_id,
            application_mode="pre_apply_shell",
            apply_status=apply_status,
            readiness_state=readiness_state,
            precondition_summary=precondition_summary,
            intent_decisions=intent_decisions,
            surface_decisions=surface_decisions,
            audit_requirements=audit_requirements,
            audit_trail=audit_trail,
            blockers=blockers,
            validation_findings=self._findings(application),
            warnings=self._warnings(application),
            apply_shell_created=True,
            apply_request_accepted=False,
            apply_preconditions_satisfied=False,
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
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            metadata={
                "build_method": CONTROLLED_APPLY_SHELL_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_controlled_apply_shell(result, user_id=user_id)
        return result

    def get_apply_shell(
        self,
        source_application_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeApplyShell | None:
        return self.repository.get_simulado_controlled_apply_shell(
            source_application_id,
            user_id=user_id,
        )

    def get_apply_shell_by_id(
        self,
        apply_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoControlledRuntimeApplyShell | None:
        return self.repository.get_simulado_controlled_apply_shell_by_id(
            apply_shell_id,
            user_id=user_id,
        )

    def _precondition_summary(
        self,
        application: SimuladoRuntimeProgressApplication,
    ) -> ControlledApplyPreconditionSummary:
        metadata = application.metadata
        runtime_policy_present = bool(
            metadata.get("controlled_apply_runtime_policy_present")
            if "controlled_apply_runtime_policy_present" in metadata
            else application.readiness_state != "blocked_by_runtime_policy_missing"
        )
        explicit_apply_approval_present = bool(
            metadata.get("controlled_apply_explicit_apply_approval_present")
            if "controlled_apply_explicit_apply_approval_present" in metadata
            else application.readiness_state != "blocked_by_explicit_apply_not_allowed"
        )
        audit_confirmation_present = bool(
            metadata.get("controlled_apply_audit_confirmation_present")
            if "controlled_apply_audit_confirmation_present" in metadata
            else application.readiness_state != "blocked_by_audit_confirmation_missing"
        )
        rollback_plan_present = bool(metadata.get("controlled_apply_rollback_plan_present", False))
        source_application_planned_only = application.application_mode in {"dry_run", "planned_only"}
        source_application_not_applied = (
            application.application_status not in {"applied", "application_applied"}
            and application.runtime_application_applied is False
            and application.progress_mutation_applied is False
        )
        all_intents_apply_allowed = bool(application.planned_mutation_intents) and all(
            item.apply_allowed for item in application.planned_mutation_intents
        )
        all_surfaces_apply_allowed = bool(application.proposed_surface_diffs) and all(
            item.apply_allowed for item in application.proposed_surface_diffs
        )
        unsafe_public_answer_key_exposure_detected = application.answer_key_publicly_exposed is True
        unsafe_gabarito_exposure_detected = application.gabarito_publicly_exposed is True

        return ControlledApplyPreconditionSummary(
            summary_id=f"controlled-apply-preconditions:{application.application_id}",
            source_application_present=True,
            source_application_planned_only=source_application_planned_only,
            source_application_not_applied=source_application_not_applied,
            runtime_policy_present=runtime_policy_present,
            explicit_apply_approval_present=explicit_apply_approval_present,
            audit_confirmation_present=audit_confirmation_present,
            rollback_plan_present=rollback_plan_present,
            all_intents_apply_allowed=all_intents_apply_allowed,
            all_surfaces_apply_allowed=all_surfaces_apply_allowed,
            unsafe_public_answer_key_exposure_detected=unsafe_public_answer_key_exposure_detected,
            unsafe_gabarito_exposure_detected=unsafe_gabarito_exposure_detected,
            preconditions_satisfied=False,
            metadata={},
        )

    def _blocker_codes(
        self,
        application: SimuladoRuntimeProgressApplication,
        precondition_summary: ControlledApplyPreconditionSummary,
    ) -> list[str]:
        blocker_codes: list[str] = []
        if not precondition_summary.source_application_planned_only:
            blocker_codes.append("blocked_by_application_not_planned_only")
        if not precondition_summary.source_application_not_applied:
            blocker_codes.append("blocked_by_application_already_applied")
        if (
            precondition_summary.unsafe_public_answer_key_exposure_detected
            or precondition_summary.unsafe_gabarito_exposure_detected
        ):
            blocker_codes.append("blocked_by_public_answer_key_exposure_forbidden")
        if (
            application.metadata.get("force_runtime_application_disabled") is True
            or application.readiness_state == "blocked_by_runtime_application_disabled"
        ):
            blocker_codes.append("blocked_by_runtime_application_disabled")
        if not precondition_summary.runtime_policy_present:
            blocker_codes.append("blocked_by_runtime_policy_missing")
        if not precondition_summary.explicit_apply_approval_present:
            blocker_codes.append("blocked_by_explicit_apply_approval_missing")
        if not precondition_summary.audit_confirmation_present:
            blocker_codes.append("blocked_by_audit_confirmation_missing")
        if not precondition_summary.all_intents_apply_allowed:
            blocker_codes.append("blocked_by_intents_not_apply_allowed")
        if not precondition_summary.all_surfaces_apply_allowed:
            blocker_codes.append("blocked_by_surfaces_not_apply_allowed")
        return blocker_codes

    def _state(
        self,
        application: SimuladoRuntimeProgressApplication,
        blocker_codes: list[str],
    ) -> tuple[str, str]:
        if "blocked_by_application_not_planned_only" in blocker_codes:
            return "apply_blocked", "blocked_by_application_not_planned_only"
        if "blocked_by_application_already_applied" in blocker_codes:
            return "apply_blocked", "blocked_by_application_already_applied"
        if "blocked_by_public_answer_key_exposure_forbidden" in blocker_codes:
            return "apply_blocked", "blocked_by_public_answer_key_exposure_forbidden"
        if "blocked_by_runtime_application_disabled" in blocker_codes:
            return "apply_blocked", "blocked_by_runtime_application_disabled"
        if "blocked_by_runtime_policy_missing" in blocker_codes:
            return "apply_blocked", "blocked_by_runtime_policy_missing"
        if "blocked_by_explicit_apply_approval_missing" in blocker_codes:
            return "apply_blocked", "blocked_by_explicit_apply_approval_missing"
        if "blocked_by_audit_confirmation_missing" in blocker_codes:
            return "apply_blocked", "blocked_by_audit_confirmation_missing"
        if "blocked_by_intents_not_apply_allowed" in blocker_codes:
            return "apply_blocked", "blocked_by_intents_not_apply_allowed"
        if "blocked_by_surfaces_not_apply_allowed" in blocker_codes:
            return "apply_blocked", "blocked_by_surfaces_not_apply_allowed"
        if application.plan.requires_complete_guardrail:
            return "apply_needs_review", "apply_shell_needs_review"
        return "apply_shell_created_not_applied", "apply_shell_needs_review"

    def _intent_decisions(
        self,
        application: SimuladoRuntimeProgressApplication,
        precondition_summary: ControlledApplyPreconditionSummary,
    ) -> list[ControlledApplyIntentDecision]:
        decisions: list[ControlledApplyIntentDecision] = []
        preconditions_missing = not (
            precondition_summary.runtime_policy_present
            and precondition_summary.explicit_apply_approval_present
            and precondition_summary.audit_confirmation_present
        )
        for source in application.planned_mutation_intents:
            blockers = list(source.blockers)
            apply_allowed = bool(source.apply_allowed and not preconditions_missing)
            if source.apply_allowed is False:
                blockers.append("intent_blocked_by_apply_not_allowed")
                decision = "intent_rejected_pre_apply"
                reason = "source_intent_apply_not_allowed"
            elif preconditions_missing:
                decision = "intent_rejected_pre_apply"
                reason = "controlled_apply_preconditions_missing"
            else:
                decision = "intent_ready_for_future_apply_review"
                reason = "future_explicit_apply_review_required"
            decisions.append(
                ControlledApplyIntentDecision(
                    decision_id=f"controlled-apply-intent:{source.intent_id}",
                    source_intent_id=source.source_intent_id or source.intent_id,
                    intent_type=source.intent_type,
                    proposed_surface=source.proposed_surface,
                    planned=source.planned,
                    source_applied=source.applied,
                    apply_allowed=apply_allowed,
                    apply_decision=decision,
                    apply_decision_reason=reason,
                    applied=False,
                    blockers=blockers,
                    warnings=list(source.warnings),
                    metadata={"source_application_id": application.application_id},
                )
            )
        return decisions

    def _surface_decisions(
        self,
        application: SimuladoRuntimeProgressApplication,
        precondition_summary: ControlledApplyPreconditionSummary,
    ) -> list[ControlledApplySurfaceDecision]:
        decisions: list[ControlledApplySurfaceDecision] = []
        preconditions_missing = not (
            precondition_summary.runtime_policy_present
            and precondition_summary.explicit_apply_approval_present
            and precondition_summary.audit_confirmation_present
        )
        for source in application.proposed_surface_diffs:
            blockers = list(source.blockers)
            apply_allowed = bool(source.apply_allowed and not preconditions_missing)
            if source.apply_allowed is False:
                blockers.append("surface_blocked_by_apply_not_allowed")
                decision = "surface_rejected_pre_apply"
                reason = "source_surface_apply_not_allowed"
            elif preconditions_missing:
                decision = "surface_rejected_pre_apply"
                reason = "controlled_apply_preconditions_missing"
            else:
                decision = "surface_ready_for_future_apply_review"
                reason = "future_explicit_apply_review_required"
            decisions.append(
                ControlledApplySurfaceDecision(
                    decision_id=f"controlled-apply-surface:{source.diff_id}",
                    source_diff_id=source.diff_id,
                    surface_type=source.surface_type,
                    diff_status=source.diff_status,
                    source_applied=source.applied,
                    apply_allowed=apply_allowed,
                    apply_decision=decision,
                    apply_decision_reason=reason,
                    applied=False,
                    blockers=blockers,
                    warnings=list(source.warnings),
                    metadata={"source_application_id": application.application_id},
                )
            )
        return decisions

    def _audit_requirements(
        self,
        application: SimuladoRuntimeProgressApplication,
        precondition_summary: ControlledApplyPreconditionSummary,
    ) -> list[ControlledApplyAuditRequirement]:
        reasons = {
            "runtime_policy_confirmation": (
                "Runtime policy confirmation remains required before any explicit apply review."
            ),
            "explicit_apply_approval": (
                "Explicit apply approval remains required before any explicit apply review."
            ),
            "audit_confirmation": (
                "Audit confirmation remains required before any explicit apply review."
            ),
            "public_answer_key_absence_confirmation": (
                "Public answer key absence confirmation remains required before any explicit apply review."
            ),
            "rollback_plan_confirmation": (
                "Rollback plan confirmation remains required before any explicit apply review."
            ),
            "human_review_confirmation": (
                "Human review confirmation remains required before any explicit apply review."
            ),
        }
        satisfied_map = {
            "runtime_policy_confirmation": False,
            "explicit_apply_approval": False,
            "audit_confirmation": False,
            "public_answer_key_absence_confirmation": False,
            "rollback_plan_confirmation": False,
            "human_review_confirmation": False,
        }
        return [
            ControlledApplyAuditRequirement(
                requirement_id=f"controlled-apply-requirement:{kind}:{application.application_id}",
                requirement_type=kind,
                required=True,
                satisfied=satisfied_map[kind],
                reason=reasons[kind],
                metadata={},
            )
            for kind in (
                "runtime_policy_confirmation",
                "explicit_apply_approval",
                "audit_confirmation",
                "public_answer_key_absence_confirmation",
                "rollback_plan_confirmation",
                "human_review_confirmation",
            )
        ]

    def _audit_trail(
        self,
        *,
        application: SimuladoRuntimeProgressApplication,
        readiness_state: str,
        actor_user_id: str,
    ) -> list[ControlledApplyAuditEntry]:
        events = [
            ("apply_shell_created", "Controlled runtime apply shell was created."),
            ("no_runtime_application", "Runtime progress application remains non-applying in this foundation."),
        ]
        if readiness_state.startswith("blocked_by_"):
            events.append(("apply_blocked", f"Controlled apply shell remains blocked by {readiness_state}."))
        if readiness_state == "blocked_by_runtime_policy_missing":
            events.append(("runtime_policy_missing", "Runtime policy remains unavailable for controlled apply."))
        if readiness_state == "blocked_by_explicit_apply_approval_missing":
            events.append(
                ("explicit_apply_approval_missing", "Explicit apply approval remains unavailable.")
            )
        if readiness_state == "blocked_by_audit_confirmation_missing":
            events.append(("audit_confirmation_missing", "Audit confirmation remains unavailable."))
        return [
            ControlledApplyAuditEntry(
                audit_id=f"controlled-apply-audit:{event_type}:{application.application_id}",
                event_type=event_type,
                actor_user_id=actor_user_id,
                message=message,
                metadata={},
            )
            for event_type, message in events
        ]

    def _blockers(
        self,
        application: SimuladoRuntimeProgressApplication,
        blocker_codes: list[str],
    ) -> list[ControlledApplyBlocker]:
        messages = {
            "blocked_by_application_not_planned_only": (
                "Source runtime progress application is no longer planned-only/dry-run."
            ),
            "blocked_by_application_already_applied": (
                "Source runtime progress application appears already applied."
            ),
            "blocked_by_runtime_policy_missing": (
                "Runtime policy remains unavailable for controlled apply validation."
            ),
            "blocked_by_explicit_apply_approval_missing": (
                "Explicit apply approval remains unavailable for controlled apply validation."
            ),
            "blocked_by_audit_confirmation_missing": (
                "Audit confirmation remains unavailable for controlled apply validation."
            ),
            "blocked_by_intents_not_apply_allowed": (
                "At least one planned mutation intent remains not apply-allowed."
            ),
            "blocked_by_surfaces_not_apply_allowed": (
                "At least one proposed surface diff remains not apply-allowed."
            ),
            "blocked_by_runtime_application_disabled": (
                "Runtime application remains disabled for this controlled apply foundation."
            ),
            "blocked_by_public_answer_key_exposure_forbidden": (
                "Potential public answer key or gabarito exposure forbids controlled apply validation."
            ),
        }
        return [
            ControlledApplyBlocker(
                blocker_id=f"controlled-apply-blocker:{code}:{application.application_id}",
                code=code,
                severity="blocked",
                message=messages[code],
                related_artifact_type="simulado_runtime_progress_application",
                related_artifact_id=application.application_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        application: SimuladoRuntimeProgressApplication,
    ) -> list[ControlledApplyValidationFinding]:
        items = [
            ControlledApplyValidationFinding(
                finding_id=f"controlled-apply-finding:pre-apply-shell:{application.application_id}",
                code="controlled_apply_shell_pre_apply_only",
                severity="info",
                message="Controlled apply shell remains a pre-apply validation artifact in this foundation.",
                related_artifact_type="simulado_runtime_progress_application",
                related_artifact_id=application.application_id,
                metadata={},
            )
        ]
        for source in application.validation_findings:
            items.append(
                ControlledApplyValidationFinding(
                    finding_id=f"controlled-apply-finding:{source.code}:{application.application_id}",
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
        application: SimuladoRuntimeProgressApplication,
    ) -> list[ControlledApplyWarning]:
        items = [
            ControlledApplyWarning(
                code="controlled_apply_shell_not_applied",
                message="Controlled apply shell remains non-applying in this foundation.",
                severity="warning",
                related_artifact_type="simulado_runtime_progress_application",
                related_artifact_id=application.application_id,
                metadata={},
            )
        ]
        for source in application.warnings:
            items.append(
                ControlledApplyWarning(
                    code=source.code,
                    message=source.message,
                    severity=source.severity,
                    related_artifact_type=source.related_artifact_type,
                    related_artifact_id=source.related_artifact_id,
                    metadata={},
                )
            )
        return items
