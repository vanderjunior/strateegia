from __future__ import annotations

from app.domain.models import (
    CandidateProgressTarget,
    ProgressMutationBlocker,
    ProgressMutationEligibility,
    ProgressMutationValidationFinding,
    ProgressMutationWarning,
    ProgressScoreCompletenessAssessment,
    ScoreValidationFinding,
    ScoreWarning,
    SimuladoProgressMutationGuardrail,
    SimuladoScoreResult,
)
from app.repositories.json_store import JsonStudyRepository


PROGRESS_GUARDRAIL_BUILD_METHOD = "heuristic_simulado_progress_guardrail_builder"


class SimuladoProgressGuardrailsService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_progress_guardrail(
        self,
        source_score_result_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoProgressMutationGuardrail | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_progress_guardrail(
            source_score_result_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        score_result = self.repository.get_simulado_score_result_by_id(
            source_score_result_id,
            user_id=user_id,
        )
        if score_result is None:
            return None

        score_completeness = self._score_completeness(score_result)
        candidate_targets = self._candidate_targets(score_result=score_result, score_completeness=score_completeness)
        eligibility = self._eligibility(score_result=score_result, score_completeness=score_completeness)
        status, readiness_state = self._guardrail_state(
            score_result=score_result,
            score_completeness=score_completeness,
            eligibility=eligibility,
        )

        result = SimuladoProgressMutationGuardrail(
            progress_guardrail_id=f"simulado-progress-guardrail:{score_result.score_result_id}",
            user_id=user_id,
            source_score_result_id=score_result.score_result_id,
            source_correction_result_id=score_result.source_correction_result_id,
            source_answer_key_boundary_id=score_result.source_answer_key_boundary_id,
            source_answer_submission_id=score_result.source_answer_submission_id,
            source_attempt_session_id=score_result.source_attempt_session_id,
            source_simulado_blueprint_id=score_result.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            eligibility=eligibility,
            score_completeness=score_completeness,
            candidate_progress_targets=candidate_targets,
            blockers=self._blockers(
                score_result=score_result,
                score_completeness=score_completeness,
                eligibility=eligibility,
            ),
            validation_findings=self._findings(score_result=score_result),
            warnings=self._warnings(score_result=score_result),
            progress_mutation_enabled=False,
            ranking_mutation_enabled=False,
            retention_mutation_enabled=False,
            scheduler_mutation_enabled=False,
            study_cycle_mutation_enabled=False,
            curriculum_graph_mutation_enabled=False,
            adaptive_tuning_enabled=False,
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
                "build_method": PROGRESS_GUARDRAIL_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_progress_guardrail(result, user_id=user_id)
        return result

    def get_progress_guardrail(
        self,
        source_score_result_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoProgressMutationGuardrail | None:
        return self.repository.get_simulado_progress_guardrail(
            source_score_result_id,
            user_id=user_id,
        )

    def get_progress_guardrail_by_id(
        self,
        progress_guardrail_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoProgressMutationGuardrail | None:
        return self.repository.get_simulado_progress_guardrail_by_id(
            progress_guardrail_id,
            user_id=user_id,
        )

    def _score_completeness(
        self,
        score_result: SimuladoScoreResult,
    ) -> ProgressScoreCompletenessAssessment:
        enough_data = (
            score_result.scoreable_item_count > 0
            and score_result.scored_item_count == score_result.scoreable_item_count
            and score_result.score_summary.score_complete
            and not score_result.score_summary.needs_review_present
        )
        return ProgressScoreCompletenessAssessment(
            assessment_id=f"progress-score-completeness:{score_result.score_result_id}",
            total_items=score_result.total_answer_records,
            scored_items=score_result.scored_item_count,
            scoreable_items=score_result.scoreable_item_count,
            blocked_items=score_result.blocked_item_count,
            needs_review_items=score_result.needs_review_item_count,
            blank_items=score_result.blank_item_count,
            unsupported_items=score_result.unsupported_item_count,
            raw_score=score_result.score_summary.raw_score,
            max_score=score_result.score_summary.max_score,
            percentage_score=score_result.score_summary.percentage_score,
            score_complete=score_result.score_summary.score_complete,
            score_partial=score_result.score_summary.score_partial,
            score_blocked=score_result.status == "score_result_blocked" or score_result.score_summary.no_scoreable_items,
            enough_data_for_progress_update=enough_data,
            metadata={},
        )

    def _candidate_targets(
        self,
        *,
        score_result: SimuladoScoreResult,
        score_completeness: ProgressScoreCompletenessAssessment,
    ) -> list[CandidateProgressTarget]:
        targets: list[CandidateProgressTarget] = []
        for item in score_result.item_records:
            blockers = ["target_blocked_by_missing_mapping"]
            if score_completeness.enough_data_for_progress_update is False:
                blockers.append("target_blocked_by_incomplete_score")
            targets.append(
                CandidateProgressTarget(
                    target_id=f"progress-target:{item.record_id}",
                    target_type="unknown",
                    target_id_ref=item.source_session_item_id,
                    source_candidate_id=item.source_candidate_id,
                    source_session_item_id=item.source_session_item_id,
                    topic_id=None,
                    subtopic_id=None,
                    microtopic_id=None,
                    target_available=False,
                    mapping_confidence=0.0,
                    proposed_update_kind="no_update_applied",
                    future_update_allowed=False,
                    update_applied=False,
                    blockers=blockers,
                    warnings=[],
                    metadata={"source_score_state": item.score_state},
                )
            )
        return targets

    def _eligibility(
        self,
        *,
        score_result: SimuladoScoreResult,
        score_completeness: ProgressScoreCompletenessAssessment,
    ) -> ProgressMutationEligibility:
        requires_human_review = (
            score_result.needs_review_item_count > 0
            or score_result.status == "score_result_needs_review"
            or score_result.readiness_state == "score_needs_review"
        )
        enough = score_completeness.enough_data_for_progress_update
        return ProgressMutationEligibility(
            eligibility_id=f"progress-eligibility:{score_result.score_result_id}",
            eligible_for_future_progress_mutation=False,
            eligible_for_future_ranking_update=False,
            eligible_for_future_retention_update=False,
            eligible_for_future_scheduler_update=False,
            eligible_for_future_study_cycle_update=False,
            eligible_for_future_curriculum_graph_update=False,
            eligibility_state="needs_review" if requires_human_review and enough else "not_eligible",
            requires_human_review=requires_human_review,
            requires_complete_score=not enough,
            requires_topic_mapping=True,
            requires_policy_confirmation=True,
            metadata={},
        )

    def _guardrail_state(
        self,
        *,
        score_result: SimuladoScoreResult,
        score_completeness: ProgressScoreCompletenessAssessment,
        eligibility: ProgressMutationEligibility,
    ) -> tuple[str, str]:
        if score_result.scoreable_item_count == 0 or score_result.scored_item_count == 0:
            return "progress_guardrail_blocked", "blocked_by_no_scoreable_items"
        if eligibility.requires_human_review:
            return "progress_guardrail_needs_review", "blocked_by_score_needs_review"
        if score_completeness.enough_data_for_progress_update is False:
            return "progress_guardrail_blocked", "blocked_by_incomplete_score"
        return "progress_guardrail_ready_for_future_review", "ready_for_future_progress_review"

    def _blockers(
        self,
        *,
        score_result: SimuladoScoreResult,
        score_completeness: ProgressScoreCompletenessAssessment,
        eligibility: ProgressMutationEligibility,
    ) -> list[ProgressMutationBlocker]:
        blockers = [
            self._blocker(
                "blocked_by_runtime_mutation_disabled",
                "Runtime mutation remains disabled for this progress guardrail foundation.",
                score_result.score_result_id,
            ),
            self._blocker(
                "blocked_by_public_answer_key_exposure_forbidden",
                "Public answer key and gabarito exposure remain forbidden for this progress guardrail foundation.",
                score_result.score_result_id,
            ),
            self._blocker(
                "blocked_by_missing_topic_mapping",
                "Topic and microtopic mapping remain unavailable for progress mutation guardrails.",
                score_result.score_result_id,
            ),
            self._blocker(
                "blocked_by_missing_policy_confirmation",
                "Policy confirmation remains unavailable for future runtime mutation.",
                score_result.score_result_id,
            ),
        ]
        if score_completeness.scoreable_items == 0 or score_completeness.scored_items == 0:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_no_scoreable_items",
                    "No scoreable or scored items are available for future runtime mutation review.",
                    score_result.score_result_id,
                ),
            )
        if score_completeness.enough_data_for_progress_update is False:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_incomplete_score",
                    "Score completeness is insufficient for any future runtime mutation review.",
                    score_result.score_result_id,
                ),
            )
        if eligibility.requires_human_review:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_score_needs_review",
                    "Human review remains required before any future runtime mutation review.",
                    score_result.score_result_id,
                ),
            )
        if any(
            finding.code in {"unknown_session_item", "blocked_by_invalid_submission"}
            for finding in score_result.validation_findings
        ):
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_invalid_submission",
                    "Submitted answers remain structurally invalid for future progress review.",
                    score_result.score_result_id,
                ),
            )
        return blockers

    def _findings(
        self,
        *,
        score_result: SimuladoScoreResult,
    ) -> list[ProgressMutationValidationFinding]:
        findings = [
            self._finding(
                "progress_mutation_remains_disabled",
                "Progress mutation remains disabled in this foundation.",
                score_result.score_result_id,
            ),
            self._finding(
                "ranking_mutation_remains_disabled",
                "Ranking mutation remains disabled in this foundation.",
                score_result.score_result_id,
            ),
            self._finding(
                "retention_mutation_remains_disabled",
                "Retention mutation remains disabled in this foundation.",
                score_result.score_result_id,
            ),
            self._finding(
                "scheduler_mutation_remains_disabled",
                "Scheduler mutation remains disabled in this foundation.",
                score_result.score_result_id,
            ),
            self._finding(
                "study_cycle_mutation_remains_disabled",
                "Study cycle mutation remains disabled in this foundation.",
                score_result.score_result_id,
            ),
            self._finding(
                "curriculum_graph_mutation_remains_disabled",
                "Curriculum graph mutation remains disabled in this foundation.",
                score_result.score_result_id,
            ),
            self._finding(
                "adaptive_tuning_remains_disabled",
                "Adaptive tuning remains disabled in this foundation.",
                score_result.score_result_id,
            ),
        ]
        for source in score_result.validation_findings:
            findings.append(
                self._finding(
                    source.code,
                    source.message,
                    source.related_artifact_id or score_result.score_result_id,
                    severity=source.severity,
                )
            )
        return findings

    def _warnings(
        self,
        *,
        score_result: SimuladoScoreResult,
    ) -> list[ProgressMutationWarning]:
        warnings = [
            self._warning(
                "progress_guardrail_no_runtime_mutation",
                "Progress mutation guardrail remains isolated from runtime mutation in this foundation.",
                score_result.score_result_id,
            )
        ]
        for source in score_result.warnings:
            warnings.append(
                self._warning(
                    source.code,
                    source.message,
                    source.related_artifact_id or score_result.score_result_id,
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
    ) -> ProgressMutationBlocker:
        return ProgressMutationBlocker(
            blocker_id=f"progress-guardrail-blocker:{code}:{related_artifact_id}",
            code=code,
            severity=severity,
            message=message,
            related_artifact_type="simulado_score_result",
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
    ) -> ProgressMutationValidationFinding:
        return ProgressMutationValidationFinding(
            finding_id=f"progress-guardrail-finding:{code}:{related_artifact_id}",
            code=code,
            severity=severity,
            message=message,
            related_artifact_type="simulado_score_result",
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
    ) -> ProgressMutationWarning:
        return ProgressMutationWarning(
            code=code,
            message=message,
            severity=severity,
            related_artifact_type="simulado_score_result",
            related_artifact_id=related_artifact_id,
            metadata={},
        )
