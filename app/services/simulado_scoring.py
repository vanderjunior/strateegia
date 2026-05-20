from __future__ import annotations

from app.domain.models import (
    CorrectionResultValidationFinding,
    CorrectionResultWarning,
    ScoreBlocker,
    ScoreItemRecord,
    ScorePolicySnapshot,
    ScoreSummary,
    ScoreValidationFinding,
    ScoreWarning,
    SimuladoCorrectionResult,
    SimuladoScoreResult,
)
from app.repositories.json_store import JsonStudyRepository


SCORING_BUILD_METHOD = "heuristic_simulado_scoring_builder"


class SimuladoScoringService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_score_result(
        self,
        source_correction_result_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoScoreResult | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_score_result(
            source_correction_result_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        correction_result = self.repository.get_simulado_correction_result_by_id(
            source_correction_result_id,
            user_id=user_id,
        )
        if correction_result is None:
            return None

        score_policy = self._score_policy(correction_result)
        item_records = self._item_records(correction_result=correction_result, score_policy=score_policy)
        scoreable_item_count = sum(1 for item in item_records if item.scoreable)
        scored_item_count = sum(1 for item in item_records if item.scored)
        blocked_item_count = sum(1 for item in item_records if not item.scoreable)
        needs_review_item_count = sum(1 for item in item_records if item.requires_review)
        blank_item_count = sum(1 for item in item_records if item.score_state == "item_blank_not_scored")
        unsupported_item_count = sum(
            1 for item in item_records if item.score_state == "item_blocked_by_unsupported_answer_kind"
        )
        status, readiness_state = self._result_state(
            correction_result=correction_result,
            item_records=item_records,
            scoreable_item_count=scoreable_item_count,
            scored_item_count=scored_item_count,
            needs_review_item_count=needs_review_item_count,
        )

        result = SimuladoScoreResult(
            score_result_id=f"simulado-score-result:{correction_result.correction_result_id}",
            user_id=user_id,
            source_correction_result_id=correction_result.correction_result_id,
            source_answer_key_boundary_id=correction_result.source_answer_key_boundary_id,
            source_correction_shell_id=correction_result.source_correction_shell_id,
            source_answer_submission_id=correction_result.source_answer_submission_id,
            source_attempt_session_id=correction_result.source_attempt_session_id,
            source_simulado_blueprint_id=correction_result.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            total_answer_records=len(item_records),
            scoreable_item_count=scoreable_item_count,
            scored_item_count=scored_item_count,
            blocked_item_count=blocked_item_count,
            needs_review_item_count=needs_review_item_count,
            blank_item_count=blank_item_count,
            unsupported_item_count=unsupported_item_count,
            item_records=item_records,
            score_summary=self._score_summary(
                item_records=item_records,
                scoreable_item_count=scoreable_item_count,
                scored_item_count=scored_item_count,
            ),
            score_policy=score_policy,
            blockers=self._blockers(
                correction_result=correction_result,
                item_records=item_records,
                score_policy=score_policy,
                scoreable_item_count=scoreable_item_count,
            ),
            validation_findings=self._findings(correction_result=correction_result, score_policy=score_policy),
            warnings=self._warnings(correction_result=correction_result),
            progress_mutation_enabled=False,
            ranking_mutation_enabled=False,
            retention_mutation_enabled=False,
            scheduler_mutation_enabled=False,
            study_cycle_mutation_enabled=False,
            curriculum_graph_mutation_enabled=False,
            no_progress_mutation=True,
            no_ranking_update=True,
            no_retention_update=True,
            no_scheduler_update=True,
            no_study_cycle_update=True,
            no_curriculum_graph_update=True,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            metadata={
                "build_method": SCORING_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_score_result(result, user_id=user_id)
        return result

    def get_score_result(
        self,
        source_correction_result_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoScoreResult | None:
        return self.repository.get_simulado_score_result(
            source_correction_result_id,
            user_id=user_id,
        )

    def get_score_result_by_id(
        self,
        score_result_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoScoreResult | None:
        return self.repository.get_simulado_score_result_by_id(
            score_result_id,
            user_id=user_id,
        )

    def _score_policy(self, correction_result: SimuladoCorrectionResult) -> ScorePolicySnapshot:
        return ScorePolicySnapshot(
            policy_id=f"score-policy:{correction_result.correction_result_id}",
            policy_source=None,
            policy_available=False,
            per_item_default_points=None,
            negative_marking_enabled=False,
            negative_marking_source=None,
            blank_penalty_enabled=False,
            unsupported_items_scoreable=False,
            metadata={},
        )

    def _item_records(
        self,
        *,
        correction_result: SimuladoCorrectionResult,
        score_policy: ScorePolicySnapshot,
    ) -> list[ScoreItemRecord]:
        records: list[ScoreItemRecord] = []
        for answer_record in correction_result.answer_records:
            score_state, scoreable, scored, points_awarded, max_points, requires_review = self._score_state(
                answer_record=answer_record,
                score_policy=score_policy,
            )
            scoring_blockers = list(answer_record.blockers)
            if score_policy.policy_available is False and score_state != "item_blank_not_scored":
                scoring_blockers.append("blocked_by_missing_score_policy")
            records.append(
                ScoreItemRecord(
                    record_id=f"score-item-record:{answer_record.record_id}",
                    source_correction_result_answer_record_id=answer_record.record_id,
                    source_submitted_answer_id=answer_record.source_submitted_answer_id,
                    source_session_item_id=answer_record.source_session_item_id,
                    source_candidate_id=answer_record.source_candidate_id,
                    answer_kind=answer_record.answer_kind,
                    correction_state=answer_record.correction_state,
                    score_state=score_state,
                    scoreable=scoreable,
                    scored=scored,
                    points_awarded=points_awarded,
                    max_points=max_points,
                    scoring_blockers=scoring_blockers,
                    requires_review=requires_review,
                    metadata=dict(answer_record.metadata),
                )
            )
        return records

    def _score_state(
        self,
        *,
        answer_record,
        score_policy: ScorePolicySnapshot,
    ) -> tuple[str, bool, bool, float, float, bool]:
        if answer_record.student_answer_blank or answer_record.correction_state == "answer_blank_not_scored":
            return "item_blank_not_scored", False, False, 0.0, 0.0, False
        if answer_record.correction_state == "answer_blocked_by_unsupported_answer_kind":
            return "item_blocked_by_unsupported_answer_kind", False, False, 0.0, 0.0, False
        if answer_record.requires_review or answer_record.correction_state == "answer_needs_review":
            return "item_needs_review", False, False, 0.0, 0.0, True
        if answer_record.scoreable is False:
            return "item_blocked_by_missing_correction_state", False, False, 0.0, 0.0, False
        if score_policy.policy_available is False:
            return "item_blocked_by_missing_score_policy", False, False, 0.0, 0.0, False

        max_points = float(score_policy.per_item_default_points or 0.0)
        return "item_scored_no_runtime_mutation", True, True, max_points, max_points, False

    def _result_state(
        self,
        *,
        correction_result: SimuladoCorrectionResult,
        item_records: list[ScoreItemRecord],
        scoreable_item_count: int,
        scored_item_count: int,
        needs_review_item_count: int,
    ) -> tuple[str, str]:
        if scoreable_item_count == 0:
            return "score_result_blocked", "blocked_by_no_scoreable_correction_records"
        if needs_review_item_count > 0 and scored_item_count == 0:
            return "score_result_needs_review", "score_needs_review"
        if scored_item_count < scoreable_item_count or scored_item_count < len(item_records):
            return "score_result_partial", "score_partial_no_runtime_mutation"
        return "score_result_created", "score_recorded_no_runtime_mutation"

    def _score_summary(
        self,
        *,
        item_records: list[ScoreItemRecord],
        scoreable_item_count: int,
        scored_item_count: int,
    ) -> ScoreSummary:
        raw_score = float(sum(item.points_awarded for item in item_records if item.scored))
        max_score = float(sum(item.max_points for item in item_records if item.scored))
        percentage_score = None
        if max_score > 0:
            percentage_score = round((raw_score / max_score) * 100.0, 2)
        return ScoreSummary(
            summary_id=f"score-summary:{len(item_records)}",
            raw_score=raw_score,
            max_score=max_score,
            percentage_score=percentage_score,
            score_computable=scored_item_count > 0 and max_score > 0,
            score_complete=bool(item_records) and scored_item_count == len(item_records),
            score_partial=scored_item_count > 0 and scored_item_count < len(item_records),
            no_scoreable_items=scoreable_item_count == 0,
            blocked_items_present=any(not item.scoreable for item in item_records) or not item_records,
            needs_review_present=any(item.requires_review for item in item_records),
            metadata={},
        )

    def _blockers(
        self,
        *,
        correction_result: SimuladoCorrectionResult,
        item_records: list[ScoreItemRecord],
        score_policy: ScorePolicySnapshot,
        scoreable_item_count: int,
    ) -> list[ScoreBlocker]:
        blockers = [
            self._blocker(
                "blocked_by_public_answer_key_exposure_forbidden",
                "Public answer key and gabarito exposure remain forbidden for this scoring foundation.",
                correction_result.correction_result_id,
            ),
        ]
        if score_policy.policy_available is False:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_missing_score_policy",
                    "Scoring policy remains unavailable for this scoring foundation.",
                    correction_result.correction_result_id,
                ),
            )
        if scoreable_item_count == 0:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_no_scoreable_correction_records",
                    "No correction records are safely scoreable in this scoring foundation.",
                    correction_result.correction_result_id,
                ),
            )
        if any(item.score_state == "item_blocked_by_unsupported_answer_kind" for item in item_records):
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_unsupported_answer_kind",
                    "At least one correction record uses an unsupported answer kind for scoring.",
                    correction_result.correction_result_id,
                ),
            )
        if any(
            finding.code in {"unknown_session_item", "blocked_by_invalid_submission"}
            for finding in correction_result.validation_findings
        ):
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_invalid_submission",
                    "Submitted answers remain structurally invalid for scoring.",
                    correction_result.correction_result_id,
                ),
            )
        return blockers

    def _findings(
        self,
        *,
        correction_result: SimuladoCorrectionResult,
        score_policy: ScorePolicySnapshot,
    ) -> list[ScoreValidationFinding]:
        findings = [
            self._finding(
                "progress_mutation_remains_disabled",
                "Progress mutation remains disabled in this scoring foundation.",
                correction_result.correction_result_id,
            ),
            self._finding(
                "ranking_mutation_remains_disabled",
                "Ranking mutation remains disabled in this scoring foundation.",
                correction_result.correction_result_id,
            ),
            self._finding(
                "retention_mutation_remains_disabled",
                "Retention mutation remains disabled in this scoring foundation.",
                correction_result.correction_result_id,
            ),
            self._finding(
                "scheduler_mutation_remains_disabled",
                "Scheduler mutation remains disabled in this scoring foundation.",
                correction_result.correction_result_id,
            ),
            self._finding(
                "public_answer_key_exposure_disabled",
                "Public answer key exposure remains disabled in this scoring foundation.",
                correction_result.correction_result_id,
            ),
            self._finding(
                "public_gabarito_exposure_disabled",
                "Public gabarito exposure remains disabled in this scoring foundation.",
                correction_result.correction_result_id,
            ),
        ]
        if score_policy.policy_available is False:
            findings.append(
                self._finding(
                    "score_policy_unavailable",
                    "Score policy remains unavailable in this scoring foundation.",
                    correction_result.correction_result_id,
                )
            )
        for source in correction_result.validation_findings:
            findings.append(
                self._finding(
                    source.code,
                    source.message,
                    source.related_artifact_id or correction_result.correction_result_id,
                    severity=source.severity,
                )
            )
        return findings

    def _warnings(
        self,
        *,
        correction_result: SimuladoCorrectionResult,
    ) -> list[ScoreWarning]:
        warnings = [
            self._warning(
                "score_result_no_runtime_mutation",
                "Score result remains isolated from pedagogical runtime mutation in this foundation.",
                correction_result.correction_result_id,
            )
        ]
        for source in correction_result.warnings:
            warnings.append(
                self._warning(
                    source.code,
                    source.message,
                    source.related_artifact_id or correction_result.correction_result_id,
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
    ) -> ScoreBlocker:
        return ScoreBlocker(
            blocker_id=f"score-blocker:{code}:{related_artifact_id}",
            code=code,
            severity=severity,
            message=message,
            related_artifact_type="simulado_correction_result",
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
    ) -> ScoreValidationFinding:
        return ScoreValidationFinding(
            finding_id=f"score-finding:{code}:{related_artifact_id}",
            code=code,
            severity=severity,
            message=message,
            related_artifact_type="simulado_correction_result",
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
    ) -> ScoreWarning:
        return ScoreWarning(
            code=code,
            message=message,
            severity=severity,
            related_artifact_type="simulado_correction_result",
            related_artifact_id=related_artifact_id,
            metadata={},
        )
