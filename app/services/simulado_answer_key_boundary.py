from __future__ import annotations

from app.domain.models import (
    AnswerKeyBoundaryBlocker,
    AnswerKeyBoundaryValidationFinding,
    AnswerKeyBoundaryWarning,
    CorrectionInputAnswerRecord,
    CorrectionInputContract,
    CorrectionShellAnswerRecord,
    CorrectionShellValidationFinding,
    CorrectionShellWarning,
    InternalAnswerKeyReference,
    SimuladoAnswerKeyBoundary,
    SimuladoCorrectionShell,
)
from app.repositories.json_store import JsonStudyRepository


ANSWER_KEY_BOUNDARY_BUILD_METHOD = "heuristic_simulado_answer_key_boundary_builder"
SUPPORTED_FUTURE_CORRECTION_KINDS = {"selected_option", "true_false_value", "short_text"}


class SimuladoAnswerKeyBoundaryService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_answer_key_boundary(
        self,
        source_correction_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAnswerKeyBoundary | None:
        if user_id is None:
            return None

        existing = self.repository.get_simulado_answer_key_boundary(
            source_correction_shell_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        correction_shell = self.repository.get_simulado_correction_shell_by_id(
            source_correction_shell_id,
            user_id=user_id,
        )
        if correction_shell is None:
            return None

        answer_records = self._answer_records(correction_shell)
        internal_references = self._internal_references(correction_shell, answer_records)
        supported_answer_record_count = sum(1 for record in answer_records if record.future_correction_supported)
        blocked_answer_record_count = sum(1 for record in answer_records if record.correction_allowed_now is False)
        internal_answer_key_reference_count = sum(
            1 for reference in internal_references if reference.answer_key_reference_available
        )
        status, readiness_state = self._boundary_state(answer_records)

        result = SimuladoAnswerKeyBoundary(
            answer_key_boundary_id=f"simulado-answer-key-boundary:{correction_shell.correction_shell_id}",
            user_id=user_id,
            source_correction_shell_id=correction_shell.correction_shell_id,
            source_answer_submission_id=correction_shell.source_answer_submission_id,
            source_attempt_session_id=correction_shell.source_attempt_session_id,
            source_simulado_blueprint_id=correction_shell.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            total_answer_records=len(answer_records),
            supported_answer_record_count=supported_answer_record_count,
            blocked_answer_record_count=blocked_answer_record_count,
            internal_answer_key_reference_count=internal_answer_key_reference_count,
            correction_input_contract=self._contract(answer_records),
            answer_records=answer_records,
            internal_answer_key_references=internal_references,
            blockers=self._blockers(correction_shell, answer_records),
            validation_findings=self._findings(correction_shell),
            warnings=self._warnings(correction_shell),
            correction_enabled=False,
            scoring_enabled=False,
            progress_mutation_enabled=False,
            answer_key_publicly_exposed=False,
            gabarito_publicly_exposed=False,
            no_correction_result_created=True,
            no_score_created=True,
            no_progress_mutation=True,
            metadata={
                "build_method": ANSWER_KEY_BOUNDARY_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_answer_key_boundary(result, user_id=user_id)
        return result

    def get_answer_key_boundary(
        self,
        source_correction_shell_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAnswerKeyBoundary | None:
        return self.repository.get_simulado_answer_key_boundary(
            source_correction_shell_id,
            user_id=user_id,
        )

    def get_answer_key_boundary_by_id(
        self,
        answer_key_boundary_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAnswerKeyBoundary | None:
        return self.repository.get_simulado_answer_key_boundary_by_id(
            answer_key_boundary_id,
            user_id=user_id,
        )

    def _answer_records(
        self,
        correction_shell: SimuladoCorrectionShell,
    ) -> list[CorrectionInputAnswerRecord]:
        records: list[CorrectionInputAnswerRecord] = []
        for answer_record in correction_shell.answer_records:
            boundary_state, future_supported = self._record_readiness(answer_record)
            records.append(
                CorrectionInputAnswerRecord(
                    record_id=f"answer-key-boundary-record:{answer_record.record_id}",
                    source_correction_shell_answer_record_id=answer_record.record_id,
                    source_submitted_answer_id=answer_record.source_submitted_answer_id,
                    source_session_item_id=answer_record.source_session_item_id,
                    source_candidate_id=answer_record.source_candidate_id,
                    answer_kind=answer_record.answer_kind,
                    format_type=self._format_type(answer_record.answer_kind),
                    boundary_readiness_state=boundary_state,
                    has_internal_answer_key_reference=False,
                    has_public_answer_key_content=False,
                    answer_key_publicly_exposed=False,
                    has_correction_rule_reference=False,
                    has_score_rule_reference=False,
                    future_correction_supported=future_supported,
                    correction_allowed_now=False,
                    scoring_allowed_now=False,
                    blockers=self._record_blockers(answer_record, boundary_state, future_supported),
                    warnings=list(answer_record.warnings),
                    metadata=dict(answer_record.metadata),
                )
            )
        return records

    def _record_readiness(self, answer_record: CorrectionShellAnswerRecord) -> tuple[str, bool]:
        if answer_record.is_blank:
            return "answer_blank_not_corrected", False
        if answer_record.answer_kind not in SUPPORTED_FUTURE_CORRECTION_KINDS:
            return "answer_blocked_by_unsupported_answer_kind", False
        if answer_record.submission_validation_state != "structurally_valid":
            return "answer_needs_review", False
        return "answer_blocked_by_missing_internal_answer_key_reference", True

    def _record_blockers(
        self,
        answer_record: CorrectionShellAnswerRecord,
        boundary_state: str,
        future_supported: bool,
    ) -> list[str]:
        if answer_record.is_blank:
            return [
                "blank_answer_not_corrected",
                "blocked_by_correction_disabled",
                "blocked_by_scoring_disabled",
            ]
        if boundary_state == "answer_blocked_by_unsupported_answer_kind":
            return [
                "blocked_by_unsupported_answer_kind",
                "blocked_by_correction_disabled",
                "blocked_by_scoring_disabled",
            ]
        if future_supported is False:
            return [
                "blocked_by_no_answer_records",
                "blocked_by_correction_disabled",
                "blocked_by_scoring_disabled",
            ]
        return [
            "blocked_by_missing_internal_answer_key_reference",
            "blocked_by_missing_correction_rule",
            "blocked_by_missing_score_rule",
            "blocked_by_correction_disabled",
            "blocked_by_scoring_disabled",
        ]

    def _format_type(self, answer_kind: str) -> str:
        return {
            "selected_option": "objective_option",
            "true_false_value": "true_false",
            "short_text": "short_text",
            "blank": "blank",
        }.get(answer_kind, "unknown")

    def _internal_references(
        self,
        correction_shell: SimuladoCorrectionShell,
        answer_records: list[CorrectionInputAnswerRecord],
    ) -> list[InternalAnswerKeyReference]:
        references: list[InternalAnswerKeyReference] = []
        for answer_record in answer_records:
            if answer_record.future_correction_supported is False:
                continue
            references.append(
                InternalAnswerKeyReference(
                    reference_id=f"internal-answer-key-reference:{answer_record.source_candidate_id or answer_record.source_session_item_id}",
                    source_candidate_id=answer_record.source_candidate_id,
                    source_guardrail_id=None,
                    source_approval_artifact_id=None,
                    source_finalization_artifact_id=None,
                    answer_key_reference_available=False,
                    answer_key_value_stored=False,
                    answer_key_value_publicly_exposed=False,
                    answer_key_value_hash=None,
                    answer_key_value_redacted=True,
                    allowed_values=[],
                    reference_state="missing_internal_answer_key_reference",
                    metadata={
                        "source_correction_shell_id": correction_shell.correction_shell_id,
                    },
                )
            )
        return references

    def _boundary_state(
        self,
        answer_records: list[CorrectionInputAnswerRecord],
    ) -> tuple[str, str]:
        if not answer_records:
            return "answer_key_boundary_blocked", "blocked_by_no_answer_records"
        if any(record.boundary_readiness_state == "answer_blocked_by_unsupported_answer_kind" for record in answer_records):
            return "answer_key_boundary_blocked", "blocked_by_unsupported_answer_kind"
        if any(record.future_correction_supported for record in answer_records):
            return "answer_key_boundary_blocked", "blocked_by_missing_internal_answer_key_reference"
        return "answer_key_boundary_needs_review", "needs_future_answer_key_finalization"

    def _contract(
        self,
        answer_records: list[CorrectionInputAnswerRecord],
    ) -> CorrectionInputContract:
        supported_answer_kinds = sorted(
            {
                record.answer_kind
                for record in answer_records
                if record.future_correction_supported
            }
        )
        supported_formats = sorted(
            {
                record.format_type
                for record in answer_records
                if record.future_correction_supported
            }
        )
        unsupported_answer_kinds = sorted(
            {
                record.answer_kind
                for record in answer_records
                if record.boundary_readiness_state == "answer_blocked_by_unsupported_answer_kind"
            }
        )
        return CorrectionInputContract(
            contract_id=f"correction-input-contract:{len(answer_records)}:{'-'.join(supported_answer_kinds) or 'none'}",
            contract_available=True,
            internal_only=True,
            public_exposure_allowed=False,
            supported_formats=supported_formats,
            supported_answer_kinds=supported_answer_kinds,
            unsupported_answer_kinds=unsupported_answer_kinds,
            requires_final_answer_key=True,
            requires_correction_rule=True,
            requires_score_rule=True,
            correction_allowed_now=False,
            scoring_allowed_now=False,
            future_correction_possible=any(record.future_correction_supported for record in answer_records),
            metadata={},
        )

    def _blockers(
        self,
        correction_shell: SimuladoCorrectionShell,
        answer_records: list[CorrectionInputAnswerRecord],
    ) -> list[AnswerKeyBoundaryBlocker]:
        blockers = [
            self._blocker(
                "blocked_by_correction_disabled",
                "Correction remains disabled for this internal correction input contract.",
                correction_shell.correction_shell_id,
            ),
            self._blocker(
                "blocked_by_scoring_disabled",
                "Scoring remains disabled for this internal correction input contract.",
                correction_shell.correction_shell_id,
            ),
        ]
        if not answer_records:
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_no_answer_records",
                    "No answer records are available for this internal correction input contract.",
                    correction_shell.correction_shell_id,
                ),
            )
            return blockers
        if any(record.boundary_readiness_state == "answer_blocked_by_unsupported_answer_kind" for record in answer_records):
            blockers.insert(
                0,
                self._blocker(
                    "blocked_by_unsupported_answer_kind",
                    "At least one answer record uses an unsupported answer kind for future correction.",
                    correction_shell.correction_shell_id,
                ),
            )
        if any(record.future_correction_supported for record in answer_records):
            blockers.extend(
                [
                    self._blocker(
                        "blocked_by_missing_internal_answer_key_reference",
                        "Internal answer key references remain unavailable for future correction.",
                        correction_shell.correction_shell_id,
                    ),
                    self._blocker(
                        "blocked_by_missing_correction_rule",
                        "Correction rule references remain unavailable for future correction.",
                        correction_shell.correction_shell_id,
                    ),
                    self._blocker(
                        "blocked_by_missing_score_rule",
                        "Score rule references remain unavailable for future scoring.",
                        correction_shell.correction_shell_id,
                    ),
                ]
            )
        return blockers

    def _findings(
        self,
        correction_shell: SimuladoCorrectionShell,
    ) -> list[AnswerKeyBoundaryValidationFinding]:
        findings = [
            self._finding(
                "answer_key_public_exposure_disabled",
                "Answer key public exposure remains disabled in this foundation.",
                correction_shell.correction_shell_id,
            ),
            self._finding(
                "gabarito_public_exposure_disabled",
                "Gabarito public exposure remains disabled in this foundation.",
                correction_shell.correction_shell_id,
            ),
            self._finding(
                "correction_remains_disabled",
                "Correction remains disabled in this foundation.",
                correction_shell.correction_shell_id,
            ),
            self._finding(
                "scoring_remains_disabled",
                "Scoring remains disabled in this foundation.",
                correction_shell.correction_shell_id,
            ),
            self._finding(
                "progress_mutation_remains_disabled",
                "Progress mutation remains disabled in this foundation.",
                correction_shell.correction_shell_id,
            ),
        ]
        for source in correction_shell.validation_findings:
            findings.append(
                self._finding(
                    source.code,
                    source.message,
                    source.related_artifact_id or correction_shell.correction_shell_id,
                    severity=source.severity,
                )
            )
        return findings

    def _warnings(
        self,
        correction_shell: SimuladoCorrectionShell,
    ) -> list[AnswerKeyBoundaryWarning]:
        warnings = [
            self._warning(
                "answer_key_boundary_internal_only",
                "Answer key boundary remains internal-only and does not expose answer key content publicly.",
                correction_shell.correction_shell_id,
            )
        ]
        for source in correction_shell.warnings:
            warnings.append(
                self._warning(
                    source.code,
                    source.message,
                    source.related_artifact_id or correction_shell.correction_shell_id,
                )
            )
        return warnings

    def _blocker(
        self,
        code: str,
        message: str,
        related_artifact_id: str | None,
    ) -> AnswerKeyBoundaryBlocker:
        return AnswerKeyBoundaryBlocker(
            blocker_id=f"answer-key-boundary-blocker:{code}:{related_artifact_id or 'unknown'}",
            code=code,
            severity="blocked",
            message=message[:240],
            related_artifact_type="simulado_correction_shell",
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
    ) -> AnswerKeyBoundaryValidationFinding:
        return AnswerKeyBoundaryValidationFinding(
            finding_id=f"answer-key-boundary-finding:{code}:{related_artifact_id or 'unknown'}",
            code=code,
            severity=severity,
            message=message[:240],
            related_artifact_type="simulado_correction_shell",
            related_artifact_id=related_artifact_id,
            metadata={},
        )

    def _warning(
        self,
        code: str,
        message: str,
        related_artifact_id: str | None,
    ) -> AnswerKeyBoundaryWarning:
        return AnswerKeyBoundaryWarning(
            code=code,
            message=message[:240],
            severity="warning",
            related_artifact_type="simulado_correction_shell",
            related_artifact_id=related_artifact_id,
            metadata={},
        )
