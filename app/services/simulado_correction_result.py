from __future__ import annotations

from app.domain.models import (
    AnswerKeyBoundaryValidationFinding,
    AnswerKeyBoundaryWarning,
    CorrectionInputAnswerRecord,
    CorrectionResultAnswerRecord,
    CorrectionResultBlocker,
    CorrectionResultSummary,
    CorrectionResultValidationFinding,
    CorrectionResultWarning,
    SimuladoAnswerKeyBoundary,
    SimuladoCorrectionResult,
)
from app.repositories.json_store import JsonStudyRepository


CORRECTION_RESULT_BUILD_METHOD = "heuristic_simulado_correction_result_builder"


class SimuladoCorrectionResultService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_correction_result(
        self,
        source_answer_key_boundary_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoCorrectionResult | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_correction_result(
            source_answer_key_boundary_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        boundary = self.repository.get_simulado_answer_key_boundary_by_id(
            source_answer_key_boundary_id,
            user_id=user_id,
        )
        if boundary is None:
            return None

        answer_records = self._answer_records(boundary)
        corrected_answer_count = sum(
            1 for record in answer_records if record.correction_state == "answer_correction_recorded_non_scoreable"
        )
        blocked_answer_count = sum(1 for record in answer_records if record.scoreable is False)
        needs_review_answer_count = sum(1 for record in answer_records if record.requires_review is True)
        blank_answer_count = sum(1 for record in answer_records if record.student_answer_blank is True)
        unsupported_answer_count = sum(
            1 for record in answer_records if record.correction_state == "answer_blocked_by_unsupported_answer_kind"
        )
        status, readiness_state = self._result_state(boundary=boundary, answer_records=answer_records)

        result = SimuladoCorrectionResult(
            correction_result_id=f"simulado-correction-result:{boundary.answer_key_boundary_id}",
            user_id=user_id,
            source_answer_key_boundary_id=boundary.answer_key_boundary_id,
            source_correction_shell_id=boundary.source_correction_shell_id,
            source_answer_submission_id=boundary.source_answer_submission_id,
            source_attempt_session_id=boundary.source_attempt_session_id,
            source_simulado_blueprint_id=boundary.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            total_answer_records=len(answer_records),
            corrected_answer_count=corrected_answer_count,
            blocked_answer_count=blocked_answer_count,
            needs_review_answer_count=needs_review_answer_count,
            blank_answer_count=blank_answer_count,
            unsupported_answer_count=unsupported_answer_count,
            answer_records=answer_records,
            summary=self._summary(answer_records=answer_records),
            blockers=self._blockers(boundary=boundary, answer_records=answer_records, readiness_state=readiness_state),
            validation_findings=self._findings(boundary),
            warnings=self._warnings(boundary),
            scoring_enabled=False,
            progress_mutation_enabled=False,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            no_score_created=True,
            no_progress_mutation=True,
            no_final_simulado_result_created=True,
            metadata={
                "build_method": CORRECTION_RESULT_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_correction_result(result, user_id=user_id)
        return result

    def get_correction_result(
        self,
        source_answer_key_boundary_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoCorrectionResult | None:
        return self.repository.get_simulado_correction_result(
            source_answer_key_boundary_id,
            user_id=user_id,
        )

    def get_correction_result_by_id(
        self,
        correction_result_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoCorrectionResult | None:
        return self.repository.get_simulado_correction_result_by_id(
            correction_result_id,
            user_id=user_id,
        )

    def _answer_records(
        self,
        boundary: SimuladoAnswerKeyBoundary,
    ) -> list[CorrectionResultAnswerRecord]:
        records: list[CorrectionResultAnswerRecord] = []
        for answer_record in boundary.answer_records:
            correction_state, candidate_result, requires_review = self._correction_state(answer_record)
            correction_input_available = (
                answer_record.has_internal_answer_key_reference and answer_record.has_correction_rule_reference
            )
            records.append(
                CorrectionResultAnswerRecord(
                    record_id=f"correction-result-record:{answer_record.record_id}",
                    source_boundary_answer_record_id=answer_record.record_id,
                    source_submitted_answer_id=answer_record.source_submitted_answer_id,
                    source_session_item_id=answer_record.source_session_item_id,
                    source_candidate_id=answer_record.source_candidate_id,
                    answer_kind=answer_record.answer_kind,
                    correction_state=correction_state,
                    correction_input_available=correction_input_available,
                    has_internal_answer_key_reference=answer_record.has_internal_answer_key_reference,
                    has_public_answer_key_content=answer_record.has_public_answer_key_content,
                    answer_key_publicly_exposed=False,
                    student_answer_recorded=True,
                    student_answer_blank=answer_record.answer_kind == "blank"
                    or answer_record.boundary_readiness_state == "answer_blank_not_corrected",
                    candidate_result=candidate_result,
                    requires_review=requires_review,
                    scoreable=False,
                    scoring_enabled=False,
                    blockers=list(answer_record.blockers),
                    warnings=list(answer_record.warnings),
                    metadata=dict(answer_record.metadata),
                )
            )
        return records

    def _correction_state(
        self,
        answer_record: CorrectionInputAnswerRecord,
    ) -> tuple[str, str | None, bool]:
        if answer_record.boundary_readiness_state == "answer_blank_not_corrected":
            return "answer_blank_not_scored", None, False
        if answer_record.boundary_readiness_state == "answer_blocked_by_unsupported_answer_kind":
            return "answer_blocked_by_unsupported_answer_kind", None, False
        if answer_record.boundary_readiness_state == "answer_needs_review":
            return "answer_needs_review", None, True
        if answer_record.has_internal_answer_key_reference is False:
            return "answer_blocked_by_missing_internal_answer_key_reference", None, False
        if answer_record.has_correction_rule_reference is False:
            return "answer_blocked_by_missing_correction_rule", None, False
        return "answer_correction_recorded_non_scoreable", "candidate_correction_recorded_non_scoreable", False

    def _result_state(
        self,
        *,
        boundary: SimuladoAnswerKeyBoundary,
        answer_records: list[CorrectionResultAnswerRecord],
    ) -> tuple[str, str]:
        if not answer_records:
            if any(
                finding.code in {"unknown_session_item", "blocked_by_invalid_submission"}
                for finding in boundary.validation_findings
            ):
                return "correction_result_blocked", "blocked_by_invalid_submission"
            return "correction_result_needs_review", "correction_result_needs_review"
        if any(record.correction_state == "answer_blocked_by_unsupported_answer_kind" for record in answer_records):
            return "correction_result_blocked", "blocked_by_unsupported_answer_kind"
        if any(record.correction_state == "answer_blocked_by_missing_internal_answer_key_reference" for record in answer_records):
            return "correction_result_blocked", "blocked_by_missing_internal_answer_key_reference"
        if any(record.correction_state == "answer_blocked_by_missing_correction_rule" for record in answer_records):
            return "correction_result_blocked", "blocked_by_missing_correction_rule"
        if any(record.requires_review for record in answer_records):
            return "correction_result_needs_review", "correction_result_needs_review"
        return "correction_result_created", "correction_result_recorded_non_scoreable"

    def _summary(
        self,
        *,
        answer_records: list[CorrectionResultAnswerRecord],
    ) -> CorrectionResultSummary:
        return CorrectionResultSummary(
            summary_id=f"correction-result-summary:{len(answer_records)}",
            correction_result_available=True,
            scoring_available=False,
            progress_mutation_available=False,
            public_answer_key_exposure_allowed=False,
            public_gabarito_exposure_allowed=False,
            correction_completed_for_all_answers=all(
                record.correction_state == "answer_correction_recorded_non_scoreable"
                for record in answer_records
            )
            and bool(answer_records),
            all_answers_blocked=all(record.scoreable is False for record in answer_records)
            if answer_records
            else True,
            has_unresolved_blockers=any(
                record.correction_state != "answer_correction_recorded_non_scoreable"
                for record in answer_records
            )
            or not answer_records,
            requires_human_review=any(record.requires_review for record in answer_records),
            metadata={},
        )

    def _blockers(
        self,
        *,
        boundary: SimuladoAnswerKeyBoundary,
        answer_records: list[CorrectionResultAnswerRecord],
        readiness_state: str,
    ) -> list[CorrectionResultBlocker]:
        blockers = [
            self._blocker(
                "blocked_by_scoring_disabled",
                "Scoring remains disabled for this correction result foundation.",
                boundary.answer_key_boundary_id,
            ),
            self._blocker(
                "blocked_by_public_answer_key_exposure_forbidden",
                "Public answer key and gabarito exposure remain forbidden for this correction result foundation.",
                boundary.answer_key_boundary_id,
            ),
        ]
        if readiness_state == "blocked_by_invalid_submission":
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_invalid_submission",
                    "Submitted answers remain structurally invalid for this correction result.",
                    boundary.answer_key_boundary_id,
                ),
            )
        if readiness_state == "blocked_by_unsupported_answer_kind":
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_unsupported_answer_kind",
                    "At least one submitted answer uses an unsupported answer kind for correction result recording.",
                    boundary.answer_key_boundary_id,
                ),
            )
        if any(record.correction_state == "answer_blocked_by_missing_internal_answer_key_reference" for record in answer_records):
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_missing_internal_answer_key_reference",
                    "Internal answer key references remain unavailable for this correction result.",
                    boundary.answer_key_boundary_id,
                ),
            )
        if any(
            record.correction_state == "answer_blocked_by_missing_correction_rule"
            or (
                record.answer_kind in {"selected_option", "true_false_value", "short_text"}
                and record.student_answer_blank is False
                and record.correction_input_available is False
            )
            for record in answer_records
        ):
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_missing_correction_rule",
                    "Correction rules remain unavailable for this correction result.",
                    boundary.answer_key_boundary_id,
                ),
            )
        if any(
            record.answer_kind in {"selected_option", "true_false_value", "short_text"}
            and record.student_answer_blank is False
            and record.scoreable is False
            for record in answer_records
        ):
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_missing_score_rule",
                    "Score rules remain unavailable for this correction result.",
                    boundary.answer_key_boundary_id,
                ),
            )
        return blockers

    def _findings(
        self,
        boundary: SimuladoAnswerKeyBoundary,
    ) -> list[CorrectionResultValidationFinding]:
        findings = [
            self._finding(
                "scoring_remains_disabled",
                "Scoring remains disabled in this foundation.",
                boundary.answer_key_boundary_id,
            ),
            self._finding(
                "progress_mutation_remains_disabled",
                "Progress mutation remains disabled in this foundation.",
                boundary.answer_key_boundary_id,
            ),
            self._finding(
                "public_answer_key_exposure_disabled",
                "Public answer key exposure remains disabled in this foundation.",
                boundary.answer_key_boundary_id,
            ),
            self._finding(
                "public_gabarito_exposure_disabled",
                "Public gabarito exposure remains disabled in this foundation.",
                boundary.answer_key_boundary_id,
            ),
        ]
        for source in boundary.validation_findings:
            findings.append(
                self._finding(
                    source.code,
                    source.message,
                    source.related_artifact_id or boundary.answer_key_boundary_id,
                    severity=source.severity,
                )
            )
        return findings

    def _warnings(
        self,
        boundary: SimuladoAnswerKeyBoundary,
    ) -> list[CorrectionResultWarning]:
        warnings = [
            self._warning(
                "correction_result_non_scoreable",
                "Correction result remains non-scoreable in this foundation.",
                boundary.answer_key_boundary_id,
            )
        ]
        for source in boundary.warnings:
            warnings.append(
                self._warning(
                    source.code,
                    source.message,
                    source.related_artifact_id or boundary.answer_key_boundary_id,
                )
            )
        return warnings

    def _blocker(
        self,
        code: str,
        message: str,
        related_artifact_id: str | None,
    ) -> CorrectionResultBlocker:
        return CorrectionResultBlocker(
            blocker_id=f"correction-result-blocker:{code}:{related_artifact_id or 'unknown'}",
            code=code,
            severity="blocked",
            message=message[:240],
            related_artifact_type="simulado_answer_key_boundary",
            related_artifact_id=related_artifact_id,
            metadata={},
        )

    def _finding(
        self,
        code: str,
        message: str,
        related_artifact_id: str | None,
        *,
        severity: str = "info",
    ) -> CorrectionResultValidationFinding:
        return CorrectionResultValidationFinding(
            finding_id=f"correction-result-finding:{code}:{related_artifact_id or 'unknown'}",
            code=code,
            severity=severity,
            message=message[:240],
            related_artifact_type="simulado_answer_key_boundary",
            related_artifact_id=related_artifact_id,
            metadata={},
        )

    def _warning(
        self,
        code: str,
        message: str,
        related_artifact_id: str | None,
    ) -> CorrectionResultWarning:
        return CorrectionResultWarning(
            code=code,
            message=message[:240],
            severity="warning",
            related_artifact_type="simulado_answer_key_boundary",
            related_artifact_id=related_artifact_id,
            metadata={},
        )
