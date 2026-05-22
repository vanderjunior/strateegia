from __future__ import annotations

from app.domain.models import (
    PlannedRuntimeMutationIntent,
    ProposedRuntimeSurfaceDiff,
    RuntimeApplicationAuditEntry,
    RuntimeProgressApplicationBlocker,
    RuntimeProgressApplicationPlan,
    RuntimeProgressApplicationValidationFinding,
    RuntimeProgressApplicationWarning,
    SimuladoRuntimeApplicationGuardrail,
    SimuladoRuntimeProgressApplication,
)
from app.repositories.json_store import JsonStudyRepository


RUNTIME_PROGRESS_APPLICATION_BUILD_METHOD = "heuristic_simulado_runtime_progress_application_builder"
INCOMPLETE_GUARDRAIL_STATES = {
    "blocked_by_incomplete_integrated_chain",
    "blocked_by_missing_score_result",
    "blocked_by_incomplete_score",
    "blocked_by_missing_progress_guardrail",
}


class SimuladoRuntimeProgressApplicationService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_application(
        self,
        source_runtime_guardrail_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeProgressApplication | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_runtime_progress_application(
            source_runtime_guardrail_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        runtime_guardrail = self.repository.get_simulado_runtime_guardrail_by_id(
            source_runtime_guardrail_id,
            user_id=user_id,
        )
        if runtime_guardrail is None:
            return None

        planned_mutation_intents = self._planned_mutation_intents(runtime_guardrail)
        proposed_surface_diffs = self._proposed_surface_diffs(runtime_guardrail)
        application_status, readiness_state, blocker_codes = self._state(runtime_guardrail)
        blockers = self._blockers(runtime_guardrail, blocker_codes)
        plan = self._plan(
            runtime_guardrail=runtime_guardrail,
            planned_mutation_intents=planned_mutation_intents,
            proposed_surface_diffs=proposed_surface_diffs,
            blockers=blockers,
            application_status=application_status,
            readiness_state=readiness_state,
        )
        audit_trail = self._audit_trail(
            runtime_guardrail=runtime_guardrail,
            readiness_state=readiness_state,
            actor_user_id=user_id,
        )

        result = SimuladoRuntimeProgressApplication(
            application_id=f"simulado-progress-application:{runtime_guardrail.runtime_guardrail_id}",
            user_id=user_id,
            source_runtime_guardrail_id=runtime_guardrail.runtime_guardrail_id,
            source_integrated_result_id=runtime_guardrail.source_integrated_result_id,
            source_score_result_id=runtime_guardrail.source_score_result_id,
            source_progress_guardrail_id=runtime_guardrail.source_progress_guardrail_id,
            source_attempt_session_id=runtime_guardrail.source_attempt_session_id,
            source_simulado_blueprint_id=runtime_guardrail.source_simulado_blueprint_id,
            application_mode="planned_only",
            application_status=application_status,
            readiness_state=readiness_state,
            plan=plan,
            planned_mutation_intents=planned_mutation_intents,
            proposed_surface_diffs=proposed_surface_diffs,
            audit_trail=audit_trail,
            blockers=blockers,
            validation_findings=self._findings(runtime_guardrail),
            warnings=self._warnings(runtime_guardrail),
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
                "build_method": RUNTIME_PROGRESS_APPLICATION_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_runtime_progress_application(result, user_id=user_id)
        return result

    def get_application(
        self,
        source_runtime_guardrail_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeProgressApplication | None:
        return self.repository.get_simulado_runtime_progress_application(
            source_runtime_guardrail_id,
            user_id=user_id,
        )

    def get_application_by_id(
        self,
        application_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeProgressApplication | None:
        return self.repository.get_simulado_runtime_progress_application_by_id(
            application_id,
            user_id=user_id,
        )

    def _state(
        self,
        runtime_guardrail: SimuladoRuntimeApplicationGuardrail,
    ) -> tuple[str, str, list[str]]:
        blocker_codes: list[str] = []
        source_codes = {item.code for item in runtime_guardrail.blockers}
        metadata = runtime_guardrail.metadata
        incomplete_guardrail = runtime_guardrail.readiness_state in INCOMPLETE_GUARDRAIL_STATES
        guardrail_not_eligible = runtime_guardrail.safety_assessment.progress_guardrail_eligible is False
        runtime_policy_missing = (
            metadata.get("force_runtime_policy_missing") is True
            or runtime_guardrail.safety_assessment.runtime_policy_available is False
        )
        runtime_application_disabled = metadata.get("force_runtime_application_disabled") is True
        explicit_apply_not_allowed = metadata.get("force_explicit_apply_not_allowed") is True

        if incomplete_guardrail:
            blocker_codes.append("blocked_by_incomplete_guardrail")
        if runtime_guardrail.readiness_state == "blocked_by_progress_guardrail_not_eligible" or guardrail_not_eligible:
            blocker_codes.append("blocked_by_guardrail_not_eligible")
        if runtime_policy_missing or "blocked_by_runtime_policy_missing" in source_codes:
            blocker_codes.append("blocked_by_runtime_policy_missing")
        if runtime_application_disabled:
            blocker_codes.append("blocked_by_runtime_application_disabled")
        if explicit_apply_not_allowed:
            blocker_codes.append("blocked_by_explicit_apply_not_allowed")
        else:
            blocker_codes.append("blocked_by_audit_confirmation_missing")

        if incomplete_guardrail:
            return "application_blocked", "blocked_by_incomplete_guardrail", blocker_codes
        if runtime_guardrail.readiness_state == "blocked_by_progress_guardrail_not_eligible":
            return "application_blocked", "blocked_by_guardrail_not_eligible", blocker_codes
        if runtime_policy_missing:
            return "application_blocked", "blocked_by_runtime_policy_missing", blocker_codes
        if runtime_application_disabled:
            return "application_blocked", "blocked_by_runtime_application_disabled", blocker_codes
        if explicit_apply_not_allowed:
            return "application_needs_review", "blocked_by_explicit_apply_not_allowed", blocker_codes
        return "application_needs_review", "blocked_by_audit_confirmation_missing", blocker_codes

    def _plan(
        self,
        *,
        runtime_guardrail: SimuladoRuntimeApplicationGuardrail,
        planned_mutation_intents: list[PlannedRuntimeMutationIntent],
        proposed_surface_diffs: list[ProposedRuntimeSurfaceDiff],
        blockers: list[RuntimeProgressApplicationBlocker],
        application_status: str,
        readiness_state: str,
    ) -> RuntimeProgressApplicationPlan:
        plan_status = "plan_blocked" if application_status == "application_blocked" else "plan_needs_review"
        return RuntimeProgressApplicationPlan(
            plan_id=f"runtime-progress-plan:{runtime_guardrail.runtime_guardrail_id}",
            plan_status=plan_status,
            planned_only=True,
            dry_run=True,
            can_apply_now=False,
            requires_runtime_policy=readiness_state == "blocked_by_runtime_policy_missing",
            requires_explicit_final_approval=True,
            requires_complete_guardrail=readiness_state == "blocked_by_incomplete_guardrail",
            requires_audit_confirmation=True,
            mutation_intent_count=len(planned_mutation_intents),
            proposed_surface_count=len(proposed_surface_diffs),
            blocker_count=len(blockers),
            metadata={},
        )

    def _planned_mutation_intents(
        self,
        runtime_guardrail: SimuladoRuntimeApplicationGuardrail,
    ) -> list[PlannedRuntimeMutationIntent]:
        items: list[PlannedRuntimeMutationIntent] = []
        source_codes = {item.code for item in runtime_guardrail.blockers}
        for source in runtime_guardrail.candidate_mutation_intents:
            blockers = list(source.blockers)
            if runtime_guardrail.safety_assessment.runtime_policy_available is False:
                blockers.append("intent_blocked_by_runtime_policy_missing")
            if "force_runtime_application_disabled" in runtime_guardrail.metadata:
                blockers.append("intent_blocked_by_apply_disabled")
            items.append(
                PlannedRuntimeMutationIntent(
                    intent_id=f"planned-runtime-intent:{source.intent_id}",
                    source_intent_id=source.intent_id,
                    intent_type=source.intent_type,
                    proposed_surface=source.proposed_surface,
                    proposed_update_kind="intent_planned_not_applied",
                    source_target_id=source.source_target_id,
                    topic_id=source.topic_id,
                    subtopic_id=source.subtopic_id,
                    microtopic_id=source.microtopic_id,
                    subject_id=source.subject_id,
                    planned=True,
                    applied=False,
                    apply_allowed=False,
                    requires_review=True,
                    blockers=blockers,
                    warnings=list(source.warnings),
                    metadata={"source_runtime_guardrail_id": runtime_guardrail.runtime_guardrail_id},
                )
            )
        if not items and source_codes:
            items.append(
                PlannedRuntimeMutationIntent(
                    intent_id=f"planned-runtime-intent:unknown:{runtime_guardrail.runtime_guardrail_id}",
                    source_intent_id=None,
                    intent_type="unknown",
                    proposed_surface="unknown",
                    proposed_update_kind="intent_planned_not_applied",
                    planned=True,
                    applied=False,
                    apply_allowed=False,
                    requires_review=True,
                    blockers=["intent_blocked_by_guardrail"],
                    warnings=[],
                    metadata={"source_runtime_guardrail_id": runtime_guardrail.runtime_guardrail_id},
                )
            )
        return items

    def _proposed_surface_diffs(
        self,
        runtime_guardrail: SimuladoRuntimeApplicationGuardrail,
    ) -> list[ProposedRuntimeSurfaceDiff]:
        diffs: list[ProposedRuntimeSurfaceDiff] = []
        for source in runtime_guardrail.affected_runtime_surfaces:
            diff_status = "diff_blocked" if source.future_update_allowed is False else "diff_needs_review"
            diffs.append(
                ProposedRuntimeSurfaceDiff(
                    diff_id=f"proposed-runtime-diff:{source.surface_id}:{runtime_guardrail.runtime_guardrail_id}",
                    surface_type=source.surface_type,
                    surface_name=source.surface_name,
                    target_ref=source.metadata.get("source_intent_id") if isinstance(source.metadata, dict) else None,
                    before_snapshot_available=False,
                    after_snapshot_available=False,
                    before_summary={"affected": source.affected, "planned_only": True},
                    proposed_after_summary={"planned_change": "none_applied", "surface": source.surface_type},
                    diff_status=diff_status,
                    applied=False,
                    apply_allowed=False,
                    blockers=["diff_blocked"],
                    warnings=[],
                    metadata={"source_runtime_guardrail_id": runtime_guardrail.runtime_guardrail_id},
                )
            )
        return diffs

    def _audit_trail(
        self,
        *,
        runtime_guardrail: SimuladoRuntimeApplicationGuardrail,
        readiness_state: str,
        actor_user_id: str,
    ) -> list[RuntimeApplicationAuditEntry]:
        events = [
            ("application_plan_created", "Dry-run runtime progress application plan was created."),
            ("no_runtime_application", "Runtime progress application remains non-applying in this foundation."),
        ]
        if readiness_state.startswith("blocked_by_"):
            events.append(("application_blocked", f"Application plan remains blocked by {readiness_state}."))
        if readiness_state == "blocked_by_runtime_policy_missing":
            events.append(("runtime_policy_missing", "Runtime policy remains unavailable for this application plan."))
        if readiness_state == "blocked_by_explicit_apply_not_allowed":
            events.append(
                ("explicit_apply_not_allowed", "Explicit apply remains unavailable for this application plan.")
            )
        items: list[RuntimeApplicationAuditEntry] = []
        for event_type, message in events:
            items.append(
                RuntimeApplicationAuditEntry(
                    audit_id=f"runtime-progress-audit:{event_type}:{runtime_guardrail.runtime_guardrail_id}",
                    event_type=event_type,
                    actor_user_id=actor_user_id,
                    message=message,
                    metadata={},
                )
            )
        return items

    def _blockers(
        self,
        runtime_guardrail: SimuladoRuntimeApplicationGuardrail,
        blocker_codes: list[str],
    ) -> list[RuntimeProgressApplicationBlocker]:
        messages = {
            "blocked_by_guardrail_not_eligible": "Runtime guardrail remains not eligible for planned runtime application.",
            "blocked_by_incomplete_guardrail": "Runtime guardrail remains incomplete for planned runtime application.",
            "blocked_by_runtime_policy_missing": "Runtime policy remains unavailable for planned runtime application.",
            "blocked_by_runtime_application_disabled": "Runtime application remains disabled for this foundation.",
            "blocked_by_explicit_apply_not_allowed": "Explicit apply remains unavailable for this foundation.",
            "blocked_by_audit_confirmation_missing": "Audit confirmation remains required before any future apply review.",
        }
        return [
            RuntimeProgressApplicationBlocker(
                blocker_id=f"runtime-progress-application-blocker:{code}:{runtime_guardrail.runtime_guardrail_id}",
                code=code,
                severity="blocked",
                message=messages[code],
                related_artifact_type="simulado_runtime_application_guardrail",
                related_artifact_id=runtime_guardrail.runtime_guardrail_id,
                metadata={},
            )
            for code in blocker_codes
        ]

    def _findings(
        self,
        runtime_guardrail: SimuladoRuntimeApplicationGuardrail,
    ) -> list[RuntimeProgressApplicationValidationFinding]:
        items = [
            RuntimeProgressApplicationValidationFinding(
                finding_id=f"runtime-progress-application-finding:dry-run:{runtime_guardrail.runtime_guardrail_id}",
                code="runtime_progress_application_dry_run_only",
                severity="info",
                message="Runtime progress application remains dry-run/planned-only in this foundation.",
                related_artifact_type="simulado_runtime_application_guardrail",
                related_artifact_id=runtime_guardrail.runtime_guardrail_id,
                metadata={},
            )
        ]
        for source in runtime_guardrail.validation_findings:
            items.append(
                RuntimeProgressApplicationValidationFinding(
                    finding_id=f"runtime-progress-application-finding:{source.code}:{runtime_guardrail.runtime_guardrail_id}",
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
        runtime_guardrail: SimuladoRuntimeApplicationGuardrail,
    ) -> list[RuntimeProgressApplicationWarning]:
        items = [
            RuntimeProgressApplicationWarning(
                code="runtime_progress_application_not_applied",
                message="Runtime progress application remains non-applying in this foundation.",
                severity="warning",
                related_artifact_type="simulado_runtime_application_guardrail",
                related_artifact_id=runtime_guardrail.runtime_guardrail_id,
                metadata={},
            )
        ]
        for source in runtime_guardrail.warnings:
            items.append(
                RuntimeProgressApplicationWarning(
                    code=source.code,
                    message=source.message,
                    severity=source.severity,
                    related_artifact_type=source.related_artifact_type,
                    related_artifact_id=source.related_artifact_id,
                    metadata={},
                )
            )
        return items
