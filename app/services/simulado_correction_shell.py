from __future__ import annotations

from app.domain.models import (
    AnswerSubmissionValidationFinding,
    AnswerSubmissionWarning,
    CorrectionReadinessSummary,
    CorrectionShellAnswerRecord,
    CorrectionShellBlocker,
    CorrectionShellValidationFinding,
    CorrectionShellWarning,
    SimuladoAnswerSubmission,
    SimuladoCorrectionShell,
    SimuladoSubmittedAnswer,
)
from app.repositories.json_store import JsonStudyRepository


CORRECTION_SHELL_BUILD_METHOD = "heuristic_simulado_correction_shell_builder"


class SimuladoCorrectionShellService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_correction_shell(
        self,
        source_answer_submission_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoCorrectionShell | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_correction_shell(
            source_answer_submission_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        answer_submission = self.repository.get_simulado_answer_submission_by_id(
            source_answer_submission_id,
            user_id=user_id,
        )
        if answer_submission is None:
            return None

        attempt_session = self.repository.get_simulado_attempt_session_by_id(
            answer_submission.source_attempt_session_id,
            user_id=user_id,
        )
        answer_records = self._answer_records(answer_submission)
        structurally_valid_answer_count = sum(
            1 for record in answer_records if record.submission_validation_state == "structurally_valid"
        )
        blank_answer_count = sum(1 for record in answer_records if record.is_blank is True)
        invalid_answer_count = max(
            answer_submission.invalid_answer_count,
            sum(
                1
                for record in answer_records
                if record.correction_readiness_state
                in {"answer_blocked_by_invalid_submission", "answer_blocked_by_unsupported_answer_kind"}
            ),
        )
        total_submitted_answers = len(answer_records)
        blocked_answer_count = len(answer_records)
        status, readiness_state = self._shell_state(
            answer_submission=answer_submission,
            attempt_session_exists=attempt_session is not None,
            total_submitted_answers=total_submitted_answers,
            invalid_answer_count=invalid_answer_count,
            has_unsupported_answer=any(
                record.correction_readiness_state == "answer_blocked_by_unsupported_answer_kind"
                for record in answer_records
            ),
            has_structurally_valid_answer=structurally_valid_answer_count > 0,
        )
        result = SimuladoCorrectionShell(
            correction_shell_id=f"simulado-correction-shell:{answer_submission.answer_submission_id}",
            user_id=user_id,
            source_answer_submission_id=answer_submission.answer_submission_id,
            source_attempt_session_id=answer_submission.source_attempt_session_id,
            source_execution_shell_id=answer_submission.source_execution_shell_id,
            source_simulado_blueprint_id=answer_submission.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            total_submitted_answers=total_submitted_answers,
            structurally_valid_answer_count=structurally_valid_answer_count,
            blank_answer_count=blank_answer_count,
            invalid_answer_count=invalid_answer_count,
            correction_ready_answer_count=0,
            blocked_answer_count=blocked_answer_count,
            answer_records=answer_records,
            readiness_summary=self._summary(
                answer_submission=answer_submission,
                attempt_session_exists=attempt_session is not None,
                has_structurally_valid_answer=structurally_valid_answer_count > 0,
            ),
            blockers=self._blockers(
                answer_submission=answer_submission,
                attempt_session_exists=attempt_session is not None,
                total_submitted_answers=total_submitted_answers,
                invalid_answer_count=invalid_answer_count,
                has_unsupported_answer=any(
                    record.correction_readiness_state == "answer_blocked_by_unsupported_answer_kind"
                    for record in answer_records
                ),
                has_structurally_valid_answer=structurally_valid_answer_count > 0,
            ),
            validation_findings=self._findings(answer_submission),
            warnings=self._warnings(answer_submission),
            correction_enabled=False,
            scoring_enabled=False,
            progress_mutation_enabled=False,
            no_correction_result_created=True,
            no_score_created=True,
            no_progress_mutation=True,
            metadata={
                "build_method": CORRECTION_SHELL_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_correction_shell(result, user_id=user_id)
        return result

    def get_correction_shell(
        self,
        source_answer_submission_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoCorrectionShell | None:
        return self.repository.get_simulado_correction_shell(
            source_answer_submission_id,
            user_id=user_id,
        )

    def get_correction_shell_by_id(
        self,
        correction_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoCorrectionShell | None:
        return self.repository.get_simulado_correction_shell_by_id(
            correction_shell_id,
            user_id=user_id,
        )

    def _answer_records(
        self,
        answer_submission: SimuladoAnswerSubmission,
    ) -> list[CorrectionShellAnswerRecord]:
        records: list[CorrectionShellAnswerRecord] = []
        for submitted_answer in answer_submission.submitted_answers:
            readiness_state, blockers = self._answer_readiness(submitted_answer)
            records.append(
                CorrectionShellAnswerRecord(
                    record_id=f"correction-shell-record:{submitted_answer.submitted_answer_id}",
                    source_submitted_answer_id=submitted_answer.submitted_answer_id,
                    source_session_item_id=submitted_answer.source_session_item_id,
                    source_candidate_id=submitted_answer.source_candidate_id,
                    answer_kind=submitted_answer.answer_kind,
                    submission_validation_state=submitted_answer.validation_state,
                    correction_readiness_state=readiness_state,
                    has_submitted_answer=True,
                    is_blank=submitted_answer.is_blank,
                    has_final_answer_key=False,
                    has_correction_rule=False,
                    can_be_corrected=False,
                    can_be_scored=False,
                    blockers=blockers,
                    warnings=list(submitted_answer.warnings),
                    metadata={
                        "order_index": submitted_answer.order_index,
                        "display_position": submitted_answer.display_position,
                    },
                )
            )
        return records

    def _answer_readiness(self, submitted_answer: SimuladoSubmittedAnswer) -> tuple[str, list[str]]:
        if submitted_answer.is_blank:
            return "answer_blank_not_corrected", [
                "blank_answer_not_corrected",
                "blocked_by_correction_disabled",
                "blocked_by_scoring_disabled",
            ]
        if submitted_answer.validation_state == "unsupported_answer_kind":
            return "answer_blocked_by_unsupported_answer_kind", [
                "blocked_by_unsupported_answer_kind",
                "blocked_by_correction_disabled",
                "blocked_by_scoring_disabled",
            ]
        if submitted_answer.validation_state != "structurally_valid":
            return "answer_blocked_by_invalid_submission", [
                "blocked_by_invalid_submission",
                "blocked_by_correction_disabled",
                "blocked_by_scoring_disabled",
            ]
        return "answer_blocked_by_missing_final_answer_key", [
            "blocked_by_missing_final_answer_keys",
            "blocked_by_missing_correction_rules",
            "blocked_by_missing_score_rules",
            "blocked_by_correction_disabled",
            "blocked_by_scoring_disabled",
        ]

    def _shell_state(
        self,
        *,
        answer_submission: SimuladoAnswerSubmission,
        attempt_session_exists: bool,
        total_submitted_answers: int,
        invalid_answer_count: int,
        has_unsupported_answer: bool,
        has_structurally_valid_answer: bool,
    ) -> tuple[str, str]:
        if attempt_session_exists is False:
            return "correction_shell_blocked", "blocked_by_missing_attempt_session"
        if total_submitted_answers == 0 and invalid_answer_count > 0:
            return "correction_shell_blocked", "blocked_by_invalid_submission"
        if total_submitted_answers == 0:
            return "correction_shell_blocked", "blocked_by_no_submitted_answers"
        if has_unsupported_answer:
            return "correction_shell_blocked", "blocked_by_unsupported_answer_kind"
        if invalid_answer_count > 0:
            return "correction_shell_blocked", "blocked_by_invalid_submission"
        if has_structurally_valid_answer:
            return "correction_shell_blocked", "blocked_by_missing_final_answer_keys"
        return "correction_shell_needs_review", "needs_future_correction_review"

    def _summary(
        self,
        *,
        answer_submission: SimuladoAnswerSubmission,
        attempt_session_exists: bool,
        has_structurally_valid_answer: bool,
    ) -> CorrectionReadinessSummary:
        return CorrectionReadinessSummary(
            summary_id=f"correction-shell-summary:{answer_submission.answer_submission_id}",
            has_answer_submission=True,
            has_attempt_session=attempt_session_exists,
            has_final_answer_keys=False,
            has_correction_rules=False,
            has_score_rules=False,
            correction_possible_later=has_structurally_valid_answer,
            scoring_possible_later=False,
            correction_disabled_reason="Correction remains disabled in this foundation.",
            scoring_disabled_reason="Scoring remains disabled in this foundation.",
            progress_mutation_disabled_reason="Progress mutation remains disabled in this foundation.",
            metadata={},
        )

    def _blockers(
        self,
        *,
        answer_submission: SimuladoAnswerSubmission,
        attempt_session_exists: bool,
        total_submitted_answers: int,
        invalid_answer_count: int,
        has_unsupported_answer: bool,
        has_structurally_valid_answer: bool,
    ) -> list[CorrectionShellBlocker]:
        blockers = [
            self._blocker(
                "blocked_by_correction_disabled",
                "Correction remains disabled for this correction readiness shell.",
                answer_submission.answer_submission_id,
            ),
            self._blocker(
                "blocked_by_scoring_disabled",
                "Scoring remains disabled for this correction readiness shell.",
                answer_submission.answer_submission_id,
            ),
        ]
        if attempt_session_exists is False:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_missing_attempt_session",
                    "Attempt session is unavailable for this correction readiness shell.",
                    answer_submission.source_attempt_session_id,
                ),
            )
            return blockers
        if total_submitted_answers == 0:
            code = "blocked_by_invalid_submission" if invalid_answer_count > 0 else "blocked_by_no_submitted_answers"
            message = (
                "Submitted answers are structurally invalid for this correction readiness shell."
                if invalid_answer_count > 0
                else "No submitted answers are available for this correction readiness shell."
            )
            blockers.insert(0, self._blocker(code, message, answer_submission.answer_submission_id))
            return blockers
        if has_unsupported_answer:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_unsupported_answer_kind",
                    "At least one submitted answer uses an unsupported answer kind.",
                    answer_submission.answer_submission_id,
                ),
            )
        if invalid_answer_count > 0:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_invalid_submission",
                    "At least one submitted answer is structurally invalid for future correction.",
                    answer_submission.answer_submission_id,
                ),
            )
        if has_structurally_valid_answer:
            blockers.extend(
                [
                    self._blocker(
                        "blocked_by_missing_final_answer_keys",
                        "Final answer keys remain unavailable for this correction readiness shell.",
                        answer_submission.answer_submission_id,
                    ),
                    self._blocker(
                        "blocked_by_missing_correction_rules",
                        "Correction rules remain unavailable for this correction readiness shell.",
                        answer_submission.answer_submission_id,
                    ),
                    self._blocker(
                        "blocked_by_missing_score_rules",
                        "Score rules remain unavailable for this correction readiness shell.",
                        answer_submission.answer_submission_id,
                    ),
                ]
            )
        return blockers

    def _findings(
        self,
        answer_submission: SimuladoAnswerSubmission,
    ) -> list[CorrectionShellValidationFinding]:
        findings = [
            self._finding(
                "correction_remains_disabled",
                "Correction remains disabled in this foundation.",
                answer_submission.answer_submission_id,
            ),
            self._finding(
                "scoring_remains_disabled",
                "Scoring remains disabled in this foundation.",
                answer_submission.answer_submission_id,
            ),
            self._finding(
                "progress_mutation_remains_disabled",
                "Progress mutation remains disabled in this foundation.",
                answer_submission.answer_submission_id,
            ),
        ]
        for source in answer_submission.validation_findings:
            findings.append(
                self._finding(
                    source.code,
                    source.message,
                    source.related_artifact_id or answer_submission.answer_submission_id,
                    severity=source.severity,
                )
            )
        return findings

    def _warnings(
        self,
        answer_submission: SimuladoAnswerSubmission,
    ) -> list[CorrectionShellWarning]:
        warnings = [
            self._warning(
                "correction_shell_readiness_only",
                "Correction shell remains a readiness artifact and does not evaluate correctness.",
                answer_submission.answer_submission_id,
            )
        ]
        for source in answer_submission.warnings:
            warnings.append(
                self._warning(
                    source.code,
                    source.message,
                    source.related_artifact_id or answer_submission.answer_submission_id,
                )
            )
        return warnings

    def _blocker(
        self,
        code: str,
        message: str,
        related_artifact_id: str | None,
    ) -> CorrectionShellBlocker:
        return CorrectionShellBlocker(
            blocker_id=f"correction-shell-blocker:{code}:{related_artifact_id or 'unknown'}",
            code=code,
            severity="blocked",
            message=message[:240],
            related_artifact_type="simulado_answer_submission",
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
    ) -> CorrectionShellValidationFinding:
        return CorrectionShellValidationFinding(
            finding_id=f"correction-shell-finding:{code}:{related_artifact_id or 'unknown'}",
            code=code,
            severity=severity,
            message=message[:240],
            related_artifact_type="simulado_answer_submission",
            related_artifact_id=related_artifact_id,
            metadata={},
        )

    def _warning(
        self,
        code: str,
        message: str,
        related_artifact_id: str | None,
    ) -> CorrectionShellWarning:
        return CorrectionShellWarning(
            code=code,
            message=message[:240],
            severity="warning",
            related_artifact_type="simulado_answer_submission",
            related_artifact_id=related_artifact_id,
            metadata={},
        )
