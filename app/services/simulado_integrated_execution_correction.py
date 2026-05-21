from __future__ import annotations

from app.domain.models import (
    IntegratedArtifactChainSummary,
    IntegratedCorrectionStatusSummary,
    IntegratedExecutionCorrectionBlocker,
    IntegratedExecutionCorrectionValidationFinding,
    IntegratedExecutionCorrectionWarning,
    IntegratedExecutionStatusSummary,
    IntegratedProgressGuardrailSummary,
    IntegratedScoreStatusSummary,
    SimuladoAnswerKeyBoundary,
    SimuladoAnswerSubmission,
    SimuladoAttemptSession,
    SimuladoCorrectionResult,
    SimuladoCorrectionShell,
    SimuladoIntegratedExecutionCorrection,
    SimuladoProgressMutationGuardrail,
    SimuladoScoreResult,
)
from app.repositories.json_store import JsonStudyRepository


INTEGRATED_EXECUTION_CORRECTION_BUILD_METHOD = "heuristic_simulado_integrated_execution_correction_builder"


class SimuladoIntegratedExecutionCorrectionService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_integrated_result(
        self,
        source_attempt_session_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoIntegratedExecutionCorrection | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_integrated_result(
            source_attempt_session_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        attempt_session = self.repository.get_simulado_attempt_session_by_id(
            source_attempt_session_id,
            user_id=user_id,
        )
        if attempt_session is None:
            return None

        answer_submission = self.repository.get_simulado_answer_submission(
            attempt_session.attempt_session_id,
            user_id=user_id,
        )
        correction_shell = None
        answer_key_boundary = None
        correction_result = None
        score_result = None
        progress_guardrail = None

        if answer_submission is not None:
            correction_shell = self.repository.get_simulado_correction_shell(
                answer_submission.answer_submission_id,
                user_id=user_id,
            )
        if correction_shell is not None:
            answer_key_boundary = self.repository.get_simulado_answer_key_boundary(
                correction_shell.correction_shell_id,
                user_id=user_id,
            )
        if answer_key_boundary is not None:
            correction_result = self.repository.get_simulado_correction_result(
                answer_key_boundary.answer_key_boundary_id,
                user_id=user_id,
            )
        if correction_result is not None:
            score_result = self.repository.get_simulado_score_result(
                correction_result.correction_result_id,
                user_id=user_id,
            )
        if score_result is not None:
            progress_guardrail = self.repository.get_simulado_progress_guardrail(
                score_result.score_result_id,
                user_id=user_id,
            )

        chain_summary = self._chain_summary(
            attempt_session=attempt_session,
            answer_submission=answer_submission,
            correction_shell=correction_shell,
            answer_key_boundary=answer_key_boundary,
            correction_result=correction_result,
            score_result=score_result,
            progress_guardrail=progress_guardrail,
        )
        execution_summary = self._execution_summary(
            attempt_session=attempt_session,
            answer_submission=answer_submission,
        )
        correction_summary = self._correction_summary(
            correction_shell=correction_shell,
            answer_key_boundary=answer_key_boundary,
            correction_result=correction_result,
        )
        score_summary = self._score_summary(score_result=score_result)
        progress_guardrail_summary = self._progress_guardrail_summary(progress_guardrail=progress_guardrail)
        status, readiness_state = self._state(
            chain_summary=chain_summary,
            correction_summary=correction_summary,
            score_summary=score_summary,
            progress_guardrail_summary=progress_guardrail_summary,
        )

        result = SimuladoIntegratedExecutionCorrection(
            integrated_result_id=f"simulado-integrated-result:{attempt_session.attempt_session_id}",
            user_id=user_id,
            source_attempt_session_id=attempt_session.attempt_session_id,
            source_answer_submission_id=answer_submission.answer_submission_id if answer_submission else None,
            source_correction_shell_id=correction_shell.correction_shell_id if correction_shell else None,
            source_answer_key_boundary_id=answer_key_boundary.answer_key_boundary_id if answer_key_boundary else None,
            source_correction_result_id=correction_result.correction_result_id if correction_result else None,
            source_score_result_id=score_result.score_result_id if score_result else None,
            source_progress_guardrail_id=(
                progress_guardrail.progress_guardrail_id if progress_guardrail else None
            ),
            source_simulado_blueprint_id=attempt_session.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            chain_summary=chain_summary,
            execution_summary=execution_summary,
            correction_summary=correction_summary,
            score_summary=score_summary,
            progress_guardrail_summary=progress_guardrail_summary,
            blockers=self._blockers(
                attempt_session=attempt_session,
                chain_summary=chain_summary,
                correction_summary=correction_summary,
                score_summary=score_summary,
                progress_guardrail_summary=progress_guardrail_summary,
            ),
            validation_findings=self._findings(
                attempt_session=attempt_session,
                answer_submission=answer_submission,
                correction_result=correction_result,
                score_result=score_result,
                progress_guardrail=progress_guardrail,
            ),
            warnings=self._warnings(
                attempt_session=attempt_session,
                answer_submission=answer_submission,
                correction_shell=correction_shell,
                answer_key_boundary=answer_key_boundary,
                correction_result=correction_result,
                score_result=score_result,
                progress_guardrail=progress_guardrail,
            ),
            progress_mutation_applied=False,
            ranking_update_applied=False,
            retention_update_applied=False,
            scheduler_update_applied=False,
            study_cycle_update_applied=False,
            curriculum_graph_update_applied=False,
            adaptive_tuning_applied=False,
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
                "build_method": INTEGRATED_EXECUTION_CORRECTION_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_integrated_result(result, user_id=user_id)
        return result

    def get_integrated_result(
        self,
        source_attempt_session_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoIntegratedExecutionCorrection | None:
        return self.repository.get_simulado_integrated_result(
            source_attempt_session_id,
            user_id=user_id,
        )

    def get_integrated_result_by_id(
        self,
        integrated_result_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoIntegratedExecutionCorrection | None:
        return self.repository.get_simulado_integrated_result_by_id(
            integrated_result_id,
            user_id=user_id,
        )

    def _chain_summary(
        self,
        *,
        attempt_session: SimuladoAttemptSession,
        answer_submission: SimuladoAnswerSubmission | None,
        correction_shell: SimuladoCorrectionShell | None,
        answer_key_boundary: SimuladoAnswerKeyBoundary | None,
        correction_result: SimuladoCorrectionResult | None,
        score_result: SimuladoScoreResult | None,
        progress_guardrail: SimuladoProgressMutationGuardrail | None,
    ) -> IntegratedArtifactChainSummary:
        missing_artifacts: list[str] = []
        if answer_submission is None:
            missing_artifacts.append("answer_submission")
        if correction_shell is None:
            missing_artifacts.append("correction_shell")
        if answer_key_boundary is None:
            missing_artifacts.append("answer_key_boundary")
        if correction_result is None:
            missing_artifacts.append("correction_result")
        if score_result is None:
            missing_artifacts.append("score_result")
        if progress_guardrail is None:
            missing_artifacts.append("progress_guardrail")
        return IntegratedArtifactChainSummary(
            chain_summary_id=f"integrated-chain-summary:{attempt_session.attempt_session_id}",
            attempt_session_available=True,
            answer_submission_available=answer_submission is not None,
            correction_shell_available=correction_shell is not None,
            answer_key_boundary_available=answer_key_boundary is not None,
            correction_result_available=correction_result is not None,
            score_result_available=score_result is not None,
            progress_guardrail_available=progress_guardrail is not None,
            chain_complete=not missing_artifacts,
            missing_artifacts=missing_artifacts,
            metadata={},
        )

    def _execution_summary(
        self,
        *,
        attempt_session: SimuladoAttemptSession,
        answer_submission: SimuladoAnswerSubmission | None,
    ) -> IntegratedExecutionStatusSummary:
        return IntegratedExecutionStatusSummary(
            summary_id=f"integrated-execution-summary:{attempt_session.attempt_session_id}",
            session_prepared=attempt_session.session_prepared,
            session_active=attempt_session.session_active,
            session_submitted=attempt_session.session_submitted,
            session_completed=attempt_session.session_completed,
            answer_submission_present=answer_submission is not None,
            submitted_answer_count=answer_submission.submitted_answer_count if answer_submission else 0,
            non_submittable_items_present=any(item.can_accept_answer is False for item in attempt_session.items),
            metadata={},
        )

    def _correction_summary(
        self,
        *,
        correction_shell: SimuladoCorrectionShell | None,
        answer_key_boundary: SimuladoAnswerKeyBoundary | None,
        correction_result: SimuladoCorrectionResult | None,
    ) -> IntegratedCorrectionStatusSummary:
        return IntegratedCorrectionStatusSummary(
            summary_id=(
                f"integrated-correction-summary:{correction_result.correction_result_id}"
                if correction_result
                else "integrated-correction-summary:missing"
            ),
            correction_shell_present=correction_shell is not None,
            answer_key_boundary_present=answer_key_boundary is not None,
            correction_result_present=correction_result is not None,
            total_answer_records=correction_result.total_answer_records if correction_result else 0,
            corrected_answer_count=correction_result.corrected_answer_count if correction_result else 0,
            blocked_answer_count=correction_result.blocked_answer_count if correction_result else 0,
            needs_review_answer_count=correction_result.needs_review_answer_count if correction_result else 0,
            correction_complete=(
                correction_result.summary.correction_completed_for_all_answers if correction_result else False
            ),
            correction_blocked=(
                correction_result is None
                or correction_result.summary.has_unresolved_blockers
                or correction_result.status != "correction_result_created"
            ),
            metadata={},
        )

    def _score_summary(
        self,
        *,
        score_result: SimuladoScoreResult | None,
    ) -> IntegratedScoreStatusSummary:
        return IntegratedScoreStatusSummary(
            summary_id=(
                f"integrated-score-summary:{score_result.score_result_id}"
                if score_result
                else "integrated-score-summary:missing"
            ),
            score_result_present=score_result is not None,
            raw_score=score_result.score_summary.raw_score if score_result else 0.0,
            max_score=score_result.score_summary.max_score if score_result else 0.0,
            percentage_score=score_result.score_summary.percentage_score if score_result else None,
            scoreable_item_count=score_result.scoreable_item_count if score_result else 0,
            scored_item_count=score_result.scored_item_count if score_result else 0,
            blocked_item_count=score_result.blocked_item_count if score_result else 0,
            needs_review_item_count=score_result.needs_review_item_count if score_result else 0,
            score_complete=score_result.score_summary.score_complete if score_result else False,
            score_blocked=(
                score_result is None
                or score_result.status == "score_result_blocked"
                or score_result.score_summary.no_scoreable_items
            ),
            metadata={},
        )

    def _progress_guardrail_summary(
        self,
        *,
        progress_guardrail: SimuladoProgressMutationGuardrail | None,
    ) -> IntegratedProgressGuardrailSummary:
        return IntegratedProgressGuardrailSummary(
            summary_id=(
                f"integrated-progress-guardrail-summary:{progress_guardrail.progress_guardrail_id}"
                if progress_guardrail
                else "integrated-progress-guardrail-summary:missing"
            ),
            progress_guardrail_present=progress_guardrail is not None,
            eligible_for_future_progress_mutation=(
                progress_guardrail.eligibility.eligible_for_future_progress_mutation
                if progress_guardrail
                else False
            ),
            eligible_for_future_ranking_update=(
                progress_guardrail.eligibility.eligible_for_future_ranking_update
                if progress_guardrail
                else False
            ),
            eligible_for_future_retention_update=(
                progress_guardrail.eligibility.eligible_for_future_retention_update
                if progress_guardrail
                else False
            ),
            eligible_for_future_scheduler_update=(
                progress_guardrail.eligibility.eligible_for_future_scheduler_update
                if progress_guardrail
                else False
            ),
            candidate_target_count=len(progress_guardrail.candidate_progress_targets) if progress_guardrail else 0,
            update_applied_count=(
                sum(1 for target in progress_guardrail.candidate_progress_targets if target.update_applied)
                if progress_guardrail
                else 0
            ),
            mutation_blocked=(
                progress_guardrail is None
                or progress_guardrail.eligibility.eligible_for_future_progress_mutation is False
                or progress_guardrail.progress_mutation_enabled is False
            ),
            metadata={},
        )

    def _state(
        self,
        *,
        chain_summary: IntegratedArtifactChainSummary,
        correction_summary: IntegratedCorrectionStatusSummary,
        score_summary: IntegratedScoreStatusSummary,
        progress_guardrail_summary: IntegratedProgressGuardrailSummary,
    ) -> tuple[str, str]:
        if not chain_summary.chain_complete:
            first_missing = chain_summary.missing_artifacts[0] if chain_summary.missing_artifacts else "chain"
            return "integrated_execution_correction_blocked", f"blocked_by_missing_{first_missing}"
        if correction_summary.correction_complete is False:
            return "integrated_execution_correction_partial", "blocked_by_incomplete_correction"
        if score_summary.score_complete is False:
            return "integrated_execution_correction_partial", "blocked_by_incomplete_score"
        if progress_guardrail_summary.mutation_blocked:
            return "integrated_execution_correction_needs_review", "blocked_by_progress_guardrail_not_eligible"
        return "integrated_execution_correction_complete_readonly", "integrated_readonly_ready"

    def _blockers(
        self,
        *,
        attempt_session: SimuladoAttemptSession,
        chain_summary: IntegratedArtifactChainSummary,
        correction_summary: IntegratedCorrectionStatusSummary,
        score_summary: IntegratedScoreStatusSummary,
        progress_guardrail_summary: IntegratedProgressGuardrailSummary,
    ) -> list[IntegratedExecutionCorrectionBlocker]:
        blockers = [
            self._blocker(
                "blocked_by_runtime_mutation_disabled",
                "Runtime mutation remains disabled for this integrated execution/correction foundation.",
                attempt_session.attempt_session_id,
            ),
            self._blocker(
                "blocked_by_public_answer_key_exposure_forbidden",
                "Public answer key and gabarito exposure remain forbidden for this integrated execution/correction foundation.",
                attempt_session.attempt_session_id,
            ),
        ]
        for missing in chain_summary.missing_artifacts:
            blockers.insert(
                0,
                self._blocker(
                    f"blocked_by_missing_{missing}",
                    f"Required artifact `{missing}` is not available in the integrated execution/correction chain.",
                    attempt_session.attempt_session_id,
                ),
            )
        if correction_summary.correction_complete is False:
            blockers.append(
                self._blocker(
                    "blocked_by_incomplete_correction",
                    "Correction remains incomplete for this integrated execution/correction foundation.",
                    attempt_session.attempt_session_id,
                )
            )
        if score_summary.score_complete is False:
            blockers.append(
                self._blocker(
                    "blocked_by_incomplete_score",
                    "Score remains incomplete for this integrated execution/correction foundation.",
                    attempt_session.attempt_session_id,
                )
            )
        if progress_guardrail_summary.mutation_blocked:
            blockers.append(
                self._blocker(
                    "blocked_by_progress_guardrail_not_eligible",
                    "Progress guardrail remains not eligible for any future runtime mutation review.",
                    attempt_session.attempt_session_id,
                )
            )
        return blockers

    def _findings(
        self,
        *,
        attempt_session: SimuladoAttemptSession,
        answer_submission: SimuladoAnswerSubmission | None,
        correction_result: SimuladoCorrectionResult | None,
        score_result: SimuladoScoreResult | None,
        progress_guardrail: SimuladoProgressMutationGuardrail | None,
    ) -> list[IntegratedExecutionCorrectionValidationFinding]:
        findings = [
            self._finding(
                "integrated_execution_correction_readonly",
                "Integrated execution/correction remains read-only in this foundation.",
                attempt_session.attempt_session_id,
            ),
            self._finding(
                "progress_mutation_remains_disabled",
                "Progress mutation remains disabled in this integrated execution/correction foundation.",
                attempt_session.attempt_session_id,
            ),
        ]
        for source_list in (
            answer_submission.validation_findings if answer_submission else [],
            correction_result.validation_findings if correction_result else [],
            score_result.validation_findings if score_result else [],
            progress_guardrail.validation_findings if progress_guardrail else [],
        ):
            for source in source_list:
                findings.append(
                    self._finding(
                        source.code,
                        source.message,
                        source.related_artifact_id or attempt_session.attempt_session_id,
                        severity=source.severity,
                    )
                )
        return findings

    def _warnings(
        self,
        *,
        attempt_session: SimuladoAttemptSession,
        answer_submission: SimuladoAnswerSubmission | None,
        correction_shell: SimuladoCorrectionShell | None,
        answer_key_boundary: SimuladoAnswerKeyBoundary | None,
        correction_result: SimuladoCorrectionResult | None,
        score_result: SimuladoScoreResult | None,
        progress_guardrail: SimuladoProgressMutationGuardrail | None,
    ) -> list[IntegratedExecutionCorrectionWarning]:
        warnings = [
            self._warning(
                "integrated_execution_correction_no_runtime_mutation",
                "Integrated execution/correction remains isolated from runtime mutation in this foundation.",
                attempt_session.attempt_session_id,
            )
        ]
        for source_list in (
            answer_submission.warnings if answer_submission else [],
            correction_shell.warnings if correction_shell else [],
            answer_key_boundary.warnings if answer_key_boundary else [],
            correction_result.warnings if correction_result else [],
            score_result.warnings if score_result else [],
            progress_guardrail.warnings if progress_guardrail else [],
        ):
            for source in source_list:
                warnings.append(
                    self._warning(
                        source.code,
                        source.message,
                        source.related_artifact_id or attempt_session.attempt_session_id,
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
    ) -> IntegratedExecutionCorrectionBlocker:
        return IntegratedExecutionCorrectionBlocker(
            blocker_id=f"integrated-execution-correction-blocker:{code}:{related_artifact_id}",
            code=code,
            severity=severity,
            message=message,
            related_artifact_type="simulado_attempt_session",
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
    ) -> IntegratedExecutionCorrectionValidationFinding:
        return IntegratedExecutionCorrectionValidationFinding(
            finding_id=f"integrated-execution-correction-finding:{code}:{related_artifact_id}",
            code=code,
            severity=severity,
            message=message,
            related_artifact_type="simulado_attempt_session",
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
    ) -> IntegratedExecutionCorrectionWarning:
        return IntegratedExecutionCorrectionWarning(
            code=code,
            message=message,
            severity=severity,
            related_artifact_type="simulado_attempt_session",
            related_artifact_id=related_artifact_id,
            metadata={},
        )
