from __future__ import annotations

from app.domain.models import (
    AffectedRuntimeSurfaceSummary,
    CandidateRuntimeMutationIntent,
    RuntimeApplicationBlocker,
    RuntimeApplicationEligibility,
    RuntimeApplicationSafetyAssessment,
    RuntimeApplicationValidationFinding,
    RuntimeApplicationWarning,
    SimuladoIntegratedExecutionCorrection,
    SimuladoRuntimeApplicationGuardrail,
)
from app.repositories.json_store import JsonStudyRepository


RUNTIME_APPLICATION_GUARDRAIL_BUILD_METHOD = "heuristic_simulado_runtime_application_guardrail_builder"


class SimuladoRuntimeApplicationGuardrailsService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_runtime_guardrail(
        self,
        source_integrated_result_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeApplicationGuardrail | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_runtime_guardrail(
            source_integrated_result_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        integrated_result = self.repository.get_simulado_integrated_result_by_id(
            source_integrated_result_id,
            user_id=user_id,
        )
        if integrated_result is None:
            return None

        safety_assessment = self._safety_assessment(integrated_result)
        eligibility = self._eligibility(integrated_result=integrated_result, safety_assessment=safety_assessment)
        candidate_mutation_intents = self._candidate_mutation_intents(
            integrated_result=integrated_result,
            safety_assessment=safety_assessment,
        )
        affected_runtime_surfaces = self._affected_runtime_surfaces(candidate_mutation_intents)
        status, readiness_state = self._state(
            integrated_result=integrated_result,
            safety_assessment=safety_assessment,
            eligibility=eligibility,
        )

        result = SimuladoRuntimeApplicationGuardrail(
            runtime_guardrail_id=f"simulado-runtime-guardrail:{integrated_result.integrated_result_id}",
            user_id=user_id,
            source_integrated_result_id=integrated_result.integrated_result_id,
            source_attempt_session_id=integrated_result.source_attempt_session_id,
            source_answer_submission_id=integrated_result.source_answer_submission_id,
            source_correction_result_id=integrated_result.source_correction_result_id,
            source_score_result_id=integrated_result.source_score_result_id,
            source_progress_guardrail_id=integrated_result.source_progress_guardrail_id,
            source_simulado_blueprint_id=integrated_result.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            eligibility=eligibility,
            safety_assessment=safety_assessment,
            candidate_mutation_intents=candidate_mutation_intents,
            affected_runtime_surfaces=affected_runtime_surfaces,
            blockers=self._blockers(
                integrated_result=integrated_result,
                safety_assessment=safety_assessment,
                eligibility=eligibility,
            ),
            validation_findings=self._findings(integrated_result),
            warnings=self._warnings(integrated_result),
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
                "build_method": RUNTIME_APPLICATION_GUARDRAIL_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_runtime_guardrail(result, user_id=user_id)
        return result

    def get_runtime_guardrail(
        self,
        source_integrated_result_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeApplicationGuardrail | None:
        return self.repository.get_simulado_runtime_guardrail(
            source_integrated_result_id,
            user_id=user_id,
        )

    def get_runtime_guardrail_by_id(
        self,
        runtime_guardrail_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoRuntimeApplicationGuardrail | None:
        return self.repository.get_simulado_runtime_guardrail_by_id(
            runtime_guardrail_id,
            user_id=user_id,
        )

    def _safety_assessment(
        self,
        integrated_result: SimuladoIntegratedExecutionCorrection,
    ) -> RuntimeApplicationSafetyAssessment:
        progress_guardrail_eligible = (
            integrated_result.progress_guardrail_summary.progress_guardrail_present
            and integrated_result.progress_guardrail_summary.eligible_for_future_progress_mutation
        )
        enough = (
            integrated_result.chain_summary.chain_complete
            and integrated_result.score_summary.score_result_present
            and integrated_result.score_summary.score_complete
            and progress_guardrail_eligible
            and False
        )
        return RuntimeApplicationSafetyAssessment(
            assessment_id=f"runtime-application-safety:{integrated_result.integrated_result_id}",
            integrated_chain_complete=integrated_result.chain_summary.chain_complete,
            score_result_present=integrated_result.score_summary.score_result_present,
            score_complete=integrated_result.score_summary.score_complete,
            progress_guardrail_present=integrated_result.progress_guardrail_summary.progress_guardrail_present,
            progress_guardrail_eligible=progress_guardrail_eligible,
            runtime_policy_available=False,
            public_answer_key_exposure_detected=integrated_result.answer_key_publicly_exposed,
            public_gabarito_exposure_detected=integrated_result.gabarito_publicly_exposed,
            unsafe_runtime_mutation_detected=True,
            enough_data_for_future_application=enough,
            metadata={},
        )

    def _eligibility(
        self,
        *,
        integrated_result: SimuladoIntegratedExecutionCorrection,
        safety_assessment: RuntimeApplicationSafetyAssessment,
    ) -> RuntimeApplicationEligibility:
        return RuntimeApplicationEligibility(
            eligibility_id=f"runtime-application-eligibility:{integrated_result.integrated_result_id}",
            eligible_for_future_runtime_application=False,
            eligible_for_future_progress_mutation=False,
            eligible_for_future_ranking_update=False,
            eligible_for_future_retention_update=False,
            eligible_for_future_scheduler_update=False,
            eligible_for_future_study_cycle_update=False,
            eligible_for_future_curriculum_graph_update=False,
            eligibility_state=(
                "needs_review"
                if safety_assessment.integrated_chain_complete
                and safety_assessment.score_result_present
                and safety_assessment.progress_guardrail_present
                else "not_eligible"
            ),
            requires_human_review=True,
            requires_explicit_application_approval=True,
            requires_complete_integrated_chain=not safety_assessment.integrated_chain_complete,
            requires_complete_score=not safety_assessment.score_complete,
            requires_progress_guardrail_eligibility=not safety_assessment.progress_guardrail_eligible,
            requires_runtime_policy_confirmation=True,
            metadata={},
        )

    def _candidate_mutation_intents(
        self,
        *,
        integrated_result: SimuladoIntegratedExecutionCorrection,
        safety_assessment: RuntimeApplicationSafetyAssessment,
    ) -> list[CandidateRuntimeMutationIntent]:
        intent_specs = [
            ("progress_update_candidate", "progress"),
            ("ranking_update_candidate", "ranking"),
            ("retention_update_candidate", "retention"),
            ("scheduler_update_candidate", "scheduler"),
            ("study_cycle_update_candidate", "study_cycle"),
            ("curriculum_graph_update_candidate", "curriculum_graph"),
            ("unknown", "adaptive_tuning"),
        ]
        intents: list[CandidateRuntimeMutationIntent] = []
        for index, (intent_type, surface) in enumerate(intent_specs, start=1):
            blockers: list[str] = ["intent_blocked_by_runtime_mutation_disabled", "intent_blocked_by_runtime_policy_missing"]
            if safety_assessment.integrated_chain_complete is False:
                blockers.append("intent_blocked_by_incomplete_chain")
            if safety_assessment.score_complete is False:
                blockers.append("intent_blocked_by_incomplete_score")
            if safety_assessment.progress_guardrail_present is False:
                blockers.append("intent_blocked_by_missing_progress_target")
            intents.append(
                CandidateRuntimeMutationIntent(
                    intent_id=f"runtime-mutation-intent:{surface}:{integrated_result.integrated_result_id}",
                    intent_type=intent_type,
                    source_target_id=f"{surface}-target:{index}",
                    source_score_item_id=None,
                    topic_id=None,
                    subtopic_id=None,
                    microtopic_id=None,
                    subject_id=None,
                    proposed_surface=surface,
                    proposed_update_kind="no_application_applied",
                    future_application_allowed=False,
                    application_applied=False,
                    requires_review=True,
                    blockers=blockers,
                    warnings=[],
                    metadata={},
                )
            )
        return intents

    def _affected_runtime_surfaces(
        self,
        candidate_mutation_intents: list[CandidateRuntimeMutationIntent],
    ) -> list[AffectedRuntimeSurfaceSummary]:
        surfaces: list[AffectedRuntimeSurfaceSummary] = []
        for intent in candidate_mutation_intents:
            surfaces.append(
                AffectedRuntimeSurfaceSummary(
                    surface_id=f"runtime-surface:{intent.proposed_surface}",
                    surface_type=intent.proposed_surface,
                    surface_name=intent.proposed_surface,
                    affected=True,
                    future_update_allowed=False,
                    update_applied=False,
                    blocker_count=len(intent.blockers),
                    warning_count=len(intent.warnings),
                    metadata={"source_intent_id": intent.intent_id},
                )
            )
        return surfaces

    def _state(
        self,
        *,
        integrated_result: SimuladoIntegratedExecutionCorrection,
        safety_assessment: RuntimeApplicationSafetyAssessment,
        eligibility: RuntimeApplicationEligibility,
    ) -> tuple[str, str]:
        if integrated_result.chain_summary.chain_complete is False:
            return "runtime_application_guardrail_blocked", "blocked_by_incomplete_integrated_chain"
        if integrated_result.score_summary.score_result_present is False:
            return "runtime_application_guardrail_blocked", "blocked_by_missing_score_result"
        if integrated_result.score_summary.score_complete is False:
            return "runtime_application_guardrail_blocked", "blocked_by_incomplete_score"
        if integrated_result.progress_guardrail_summary.progress_guardrail_present is False:
            return "runtime_application_guardrail_blocked", "blocked_by_missing_progress_guardrail"
        if safety_assessment.progress_guardrail_eligible is False:
            return "runtime_application_guardrail_needs_review", "blocked_by_progress_guardrail_not_eligible"
        if safety_assessment.runtime_policy_available is False:
            return "runtime_application_guardrail_blocked", "blocked_by_runtime_policy_missing"
        if eligibility.requires_human_review:
            return "runtime_application_guardrail_needs_review", "runtime_application_needs_review"
        return "runtime_application_guardrail_ready_for_future_review", "ready_for_future_runtime_application_review"

    def _blockers(
        self,
        *,
        integrated_result: SimuladoIntegratedExecutionCorrection,
        safety_assessment: RuntimeApplicationSafetyAssessment,
        eligibility: RuntimeApplicationEligibility,
    ) -> list[RuntimeApplicationBlocker]:
        blockers = [
            self._blocker(
                "blocked_by_runtime_mutation_disabled",
                "Runtime mutation remains disabled for this runtime application guardrail foundation.",
                integrated_result.integrated_result_id,
            ),
            self._blocker(
                "blocked_by_runtime_policy_missing",
                "Runtime application policy remains unavailable for this runtime application guardrail foundation.",
                integrated_result.integrated_result_id,
            ),
            self._blocker(
                "blocked_by_public_answer_key_exposure_forbidden",
                "Public answer key and gabarito exposure remain forbidden for this runtime application guardrail foundation.",
                integrated_result.integrated_result_id,
            ),
        ]
        if integrated_result.chain_summary.chain_complete is False:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_incomplete_integrated_chain",
                    "Integrated execution/correction chain remains incomplete for future runtime application review.",
                    integrated_result.integrated_result_id,
                ),
            )
        if integrated_result.score_summary.score_result_present is False:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_missing_score_result",
                    "Score result remains unavailable for future runtime application review.",
                    integrated_result.integrated_result_id,
                ),
            )
        if integrated_result.score_summary.score_complete is False:
            blockers.append(
                self._blocker(
                    "blocked_by_incomplete_score",
                    "Score remains incomplete for future runtime application review.",
                    integrated_result.integrated_result_id,
                ),
            )
        if integrated_result.progress_guardrail_summary.progress_guardrail_present is False:
            blockers.append(
                self._blocker(
                    "blocked_by_missing_progress_guardrail",
                    "Progress guardrail remains unavailable for future runtime application review.",
                    integrated_result.integrated_result_id,
                ),
            )
        if safety_assessment.progress_guardrail_eligible is False:
            blockers.append(
                self._blocker(
                    "blocked_by_progress_guardrail_not_eligible",
                    "Progress guardrail remains not eligible for future runtime application review.",
                    integrated_result.integrated_result_id,
                ),
            )
        if integrated_result.answer_key_publicly_exposed or integrated_result.gabarito_publicly_exposed:
            blockers.append(
                self._blocker(
                    "blocked_by_public_answer_key_exposure_forbidden",
                    "Unsafe answer key or gabarito exposure was detected in the integrated result.",
                    integrated_result.integrated_result_id,
                ),
            )
        if eligibility.requires_human_review:
            blockers.append(
                self._blocker(
                    "runtime_application_needs_review",
                    "Human review remains required before any future runtime application review.",
                    integrated_result.integrated_result_id,
                    severity="warning",
                ),
            )
        return blockers

    def _findings(
        self,
        integrated_result: SimuladoIntegratedExecutionCorrection,
    ) -> list[RuntimeApplicationValidationFinding]:
        findings = [
            self._finding(
                "runtime_application_remains_disabled",
                "Runtime application remains disabled in this foundation.",
                integrated_result.integrated_result_id,
            ),
            self._finding(
                "progress_mutation_remains_disabled",
                "Progress mutation remains disabled in this foundation.",
                integrated_result.integrated_result_id,
            ),
        ]
        for source in integrated_result.validation_findings:
            findings.append(
                self._finding(
                    source.code,
                    source.message,
                    source.related_artifact_id or integrated_result.integrated_result_id,
                    severity=source.severity,
                )
            )
        return findings

    def _warnings(
        self,
        integrated_result: SimuladoIntegratedExecutionCorrection,
    ) -> list[RuntimeApplicationWarning]:
        warnings = [
            self._warning(
                "runtime_application_guardrail_no_runtime_mutation",
                "Runtime application guardrail remains isolated from runtime mutation in this foundation.",
                integrated_result.integrated_result_id,
            )
        ]
        for source in integrated_result.warnings:
            warnings.append(
                self._warning(
                    source.code,
                    source.message,
                    source.related_artifact_id or integrated_result.integrated_result_id,
                    severity=source.severity,
                )
            )
        return warnings

    def _blocker(
        self,
        code: str,
        message: str,
        related_artifact_id: str,
        *,
        severity: str = "blocked",
    ) -> RuntimeApplicationBlocker:
        return RuntimeApplicationBlocker(
            blocker_id=f"runtime-application-blocker:{code}:{related_artifact_id}",
            code=code,
            severity=severity,
            message=message,
            related_artifact_type="simulado_integrated_execution_correction",
            related_artifact_id=related_artifact_id,
            metadata={},
        )

    def _finding(
        self,
        code: str,
        message: str,
        related_artifact_id: str,
        *,
        severity: str = "info",
    ) -> RuntimeApplicationValidationFinding:
        return RuntimeApplicationValidationFinding(
            finding_id=f"runtime-application-finding:{code}:{related_artifact_id}",
            code=code,
            severity=severity,
            message=message,
            related_artifact_type="simulado_integrated_execution_correction",
            related_artifact_id=related_artifact_id,
            metadata={},
        )

    def _warning(
        self,
        code: str,
        message: str,
        related_artifact_id: str,
        *,
        severity: str = "warning",
    ) -> RuntimeApplicationWarning:
        return RuntimeApplicationWarning(
            code=code,
            message=message,
            severity=severity,
            related_artifact_type="simulado_integrated_execution_correction",
            related_artifact_id=related_artifact_id,
            metadata={},
        )
