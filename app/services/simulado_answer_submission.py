from __future__ import annotations

import hashlib
import html
import json
from typing import Any

from app.domain.models import (
    AnswerSubmissionValidationFinding,
    AnswerSubmissionWarning,
    SimuladoAnswerSubmission,
    SimuladoAttemptSession,
    SimuladoAttemptSessionItem,
    SimuladoSubmittedAnswer,
)
from app.repositories.json_store import JsonStudyRepository


MAX_SHORT_TEXT_LENGTH = 1000
SUBMISSION_BUILD_METHOD = "heuristic_simulado_answer_submission_builder"


class SimuladoAnswerSubmissionService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_answer_submission(
        self,
        source_attempt_session_id: str,
        *,
        user_id: str | None,
        submission_payload: dict[str, object] | None,
    ) -> SimuladoAnswerSubmission | None:
        if user_id is None:
            return None

        attempt_session = self.repository.get_simulado_attempt_session_by_id(
            source_attempt_session_id,
            user_id=user_id,
        )
        if attempt_session is None:
            return None

        if attempt_session.session_prepared is False:
            return self._blocked_submission(
                attempt_session,
                user_id=user_id,
                code="blocked_by_session_not_prepared",
                message="Attempt session is not prepared for answer recording.",
            )

        normalized_payload = self._normalize_payload(submission_payload)
        payload_signature = self._payload_signature(source_attempt_session_id, normalized_payload)
        existing = self.repository.get_simulado_answer_submission(
            source_attempt_session_id,
            user_id=user_id,
        )
        if (
            existing is not None
            and existing.metadata.get("normalized_payload_signature") == payload_signature
        ):
            return existing

        answers, findings, warnings, duplicate_count, invalid_count, missing_count = self._submitted_answers(
            attempt_session,
            normalized_payload,
        )
        submission_recorded = len(answers) > 0 or duplicate_count > 0 or invalid_count > 0
        total_items = attempt_session.total_items
        submitted_answer_count = len(answers)
        status, readiness_state = self._submission_state(
            total_items=total_items,
            submitted_answer_count=submitted_answer_count,
            invalid_answer_count=invalid_count,
            missing_answer_count=missing_count,
        )

        warnings = [
            self._warning(
                "session_remains_non_submittable",
                (
                    "Source attempt session remains non-submittable; this foundation only records "
                    "raw user-provided answers."
                ),
                attempt_session.attempt_session_id,
            ),
            *warnings,
        ]

        result = SimuladoAnswerSubmission(
            answer_submission_id=f"simulado-answer-submission:{payload_signature[:24]}",
            user_id=user_id,
            source_attempt_session_id=attempt_session.attempt_session_id,
            source_execution_shell_id=attempt_session.source_execution_shell_id,
            source_simulado_blueprint_id=attempt_session.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            total_items=total_items,
            submitted_answer_count=submitted_answer_count,
            missing_answer_count=missing_count,
            invalid_answer_count=invalid_count,
            duplicate_answer_count=duplicate_count,
            submitted_answers=answers,
            validation_findings=findings,
            warnings=warnings,
            submission_recorded=submission_recorded,
            correction_enabled=False,
            scoring_enabled=False,
            progress_mutation_enabled=False,
            no_correction_result_created=True,
            no_score_created=True,
            no_progress_mutation=True,
            metadata={
                "build_method": SUBMISSION_BUILD_METHOD,
                "normalized_payload_signature": payload_signature,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_answer_submission(result, user_id=user_id)
        return result

    def get_answer_submission(
        self,
        source_attempt_session_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAnswerSubmission | None:
        return self.repository.get_simulado_answer_submission(
            source_attempt_session_id,
            user_id=user_id,
        )

    def get_answer_submission_by_id(
        self,
        answer_submission_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoAnswerSubmission | None:
        return self.repository.get_simulado_answer_submission_by_id(
            answer_submission_id,
            user_id=user_id,
        )

    def _blocked_submission(
        self,
        attempt_session: SimuladoAttemptSession,
        *,
        user_id: str,
        code: str,
        message: str,
    ) -> SimuladoAnswerSubmission:
        return SimuladoAnswerSubmission(
            answer_submission_id=f"simulado-answer-submission:blocked:{attempt_session.attempt_session_id}",
            user_id=user_id,
            source_attempt_session_id=attempt_session.attempt_session_id,
            source_execution_shell_id=attempt_session.source_execution_shell_id,
            source_simulado_blueprint_id=attempt_session.source_simulado_blueprint_id,
            status="answer_submission_blocked",
            readiness_state=code,
            total_items=attempt_session.total_items,
            submitted_answer_count=0,
            missing_answer_count=attempt_session.total_items,
            invalid_answer_count=0,
            duplicate_answer_count=0,
            submitted_answers=[],
            validation_findings=[
                self._finding(code, message, attempt_session.attempt_session_id, severity="blocked")
            ],
            warnings=[],
            submission_recorded=False,
            correction_enabled=False,
            scoring_enabled=False,
            progress_mutation_enabled=False,
            no_correction_result_created=True,
            no_score_created=True,
            no_progress_mutation=True,
            metadata={
                "build_method": SUBMISSION_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
            },
        )

    def _normalize_payload(self, submission_payload: dict[str, object] | None) -> dict[str, object]:
        answers = submission_payload.get("answers") if isinstance(submission_payload, dict) else []
        if not isinstance(answers, list):
            answers = []
        normalized_answers: list[dict[str, object]] = []
        for raw in answers:
            if not isinstance(raw, dict):
                continue
            source_session_item_id = str(raw.get("source_session_item_id") or "").strip()
            answer_kind = str(raw.get("answer_kind") or "").strip().lower()
            normalized_answers.append(
                {
                    "source_session_item_id": source_session_item_id,
                    "answer_kind": answer_kind,
                    "submitted_value": self._sanitize_value(raw.get("submitted_value")),
                    "submitted_values": self._sanitize_values(raw.get("submitted_values")),
                }
            )
        return {"answers": normalized_answers}

    def _payload_signature(self, source_attempt_session_id: str, payload: dict[str, object]) -> str:
        digest = hashlib.sha256(
            json.dumps(
                {
                    "source_attempt_session_id": source_attempt_session_id,
                    "payload": payload,
                },
                sort_keys=True,
                ensure_ascii=True,
            ).encode("utf-8")
        ).hexdigest()
        return digest

    def _submitted_answers(
        self,
        attempt_session: SimuladoAttemptSession,
        normalized_payload: dict[str, object],
    ) -> tuple[
        list[SimuladoSubmittedAnswer],
        list[AnswerSubmissionValidationFinding],
        list[AnswerSubmissionWarning],
        int,
        int,
        int,
    ]:
        items_by_id = {item.item_id: item for item in attempt_session.items}
        recorded: list[SimuladoSubmittedAnswer] = []
        findings: list[AnswerSubmissionValidationFinding] = []
        warnings: list[AnswerSubmissionWarning] = []
        duplicate_count = 0
        invalid_count = 0
        seen_item_ids: set[str] = set()

        for position, raw in enumerate(normalized_payload.get("answers", []), start=1):
            if not isinstance(raw, dict):
                continue
            session_item_id = str(raw.get("source_session_item_id") or "")
            answer_kind = str(raw.get("answer_kind") or "")
            item = items_by_id.get(session_item_id)
            if item is not None and answer_kind not in {
                "selected_option",
                "true_false_value",
                "short_text",
                "blank",
            }:
                invalid_count += 1
                recorded.append(
                    self._build_submitted_answer(
                        item,
                        answer_kind=answer_kind,
                        submitted_value=raw.get("submitted_value"),
                        submitted_values=raw.get("submitted_values"),
                        ordinal=position,
                    )
                )
                findings.append(
                    self._finding(
                        "unsupported_answer_kind",
                        "Submitted answer kind is unsupported for this foundation.",
                        session_item_id,
                        severity="warning",
                    )
                )
                continue

            if session_item_id in seen_item_ids:
                duplicate_count += 1
                warnings.append(
                    self._warning(
                        "duplicate_answer",
                        "Duplicate answer payload detected for the same attempt session item; keeping the first.",
                        session_item_id,
                    )
                )
                continue

            if item is None:
                invalid_count += 1
                findings.append(
                    self._finding(
                        "unknown_session_item",
                        "Submitted answer references an unknown attempt session item.",
                        session_item_id,
                        severity="warning",
                    )
                )
                continue

            seen_item_ids.add(session_item_id)
            submitted_answer = self._build_submitted_answer(
                item,
                answer_kind=answer_kind,
                submitted_value=raw.get("submitted_value"),
                submitted_values=raw.get("submitted_values"),
                ordinal=position,
            )
            if submitted_answer.is_structurally_valid is False and submitted_answer.validation_state != "blank_answer":
                invalid_count += 1
                if submitted_answer.validation_state == "unsupported_answer_kind":
                    findings.append(
                        self._finding(
                            "unsupported_answer_kind",
                            "Submitted answer kind is unsupported for this foundation.",
                            session_item_id,
                            severity="warning",
                        )
                    )
                elif submitted_answer.validation_state == "structurally_invalid":
                    findings.append(
                        self._finding(
                            "structurally_invalid",
                            "Submitted answer value is structurally invalid for this answer kind.",
                            session_item_id,
                            severity="warning",
                        )
                    )
            recorded.append(submitted_answer)

        missing_count = max(attempt_session.total_items - len(seen_item_ids & set(items_by_id)), 0)
        return recorded, findings, warnings, duplicate_count, invalid_count, missing_count

    def _build_submitted_answer(
        self,
        item: SimuladoAttemptSessionItem,
        *,
        answer_kind: str,
        submitted_value: object,
        submitted_values: object,
        ordinal: int,
    ) -> SimuladoSubmittedAnswer:
        validation_state = "not_corrected"
        is_structurally_valid = False
        is_blank = False
        normalized_value: str | None = None
        normalized_values: list[str] = []
        metadata: dict[str, Any] = {"source_item_status": item.item_status}

        if answer_kind == "blank":
            is_blank = True
            validation_state = "blank_answer"
            is_structurally_valid = True
        elif answer_kind == "selected_option":
            candidate = self._normalize_scalar(submitted_value)
            if candidate in {"A", "B", "C", "D", "E"}:
                normalized_value = candidate
                validation_state = "structurally_valid"
                is_structurally_valid = True
            else:
                normalized_value = candidate
                validation_state = "structurally_invalid"
        elif answer_kind == "true_false_value":
            candidate = self._normalize_scalar(submitted_value)
            if candidate in {"C", "E", "TRUE", "FALSE"}:
                normalized_value = candidate
                validation_state = "structurally_valid"
                is_structurally_valid = True
            else:
                normalized_value = candidate
                validation_state = "structurally_invalid"
        elif answer_kind == "short_text":
            candidate = self._normalize_short_text(submitted_value)
            normalized_value = candidate
            validation_state = "structurally_valid"
            is_structurally_valid = True
        else:
            normalized_value = self._normalize_scalar(submitted_value)
            normalized_values = self._normalize_scalar_list(submitted_values)
            validation_state = "unsupported_answer_kind"

        return SimuladoSubmittedAnswer(
            submitted_answer_id=f"submitted-answer:{item.item_id}:{ordinal}",
            source_session_item_id=item.item_id,
            source_candidate_id=item.source_candidate_id,
            order_index=item.order_index,
            display_position=item.display_position,
            answer_kind=answer_kind or "blank",
            submitted_value=normalized_value,
            submitted_values=normalized_values,
            is_blank=is_blank,
            is_structurally_valid=is_structurally_valid,
            validation_state=validation_state,
            warnings=[],
            metadata=metadata,
        )

    def _submission_state(
        self,
        *,
        total_items: int,
        submitted_answer_count: int,
        invalid_answer_count: int,
        missing_answer_count: int,
    ) -> tuple[str, str]:
        if submitted_answer_count == 0 and invalid_answer_count == 0:
            return "answer_submission_blocked", "blocked_by_no_session_items"
        if invalid_answer_count > 0 or missing_answer_count > 0 or submitted_answer_count < total_items:
            return "answer_submission_partial", "partial_submission_recorded_not_corrected"
        return "answer_submission_recorded", "submission_recorded_not_corrected"

    def _sanitize_value(self, value: object) -> str | None:
        if value is None:
            return None
        return self._normalize_short_text(value)

    def _sanitize_values(self, value: object) -> list[str]:
        return self._normalize_scalar_list(value)

    def _normalize_scalar(self, value: object) -> str | None:
        if value is None:
            return None
        return self._normalize_short_text(value).upper()

    def _normalize_short_text(self, value: object) -> str:
        text = str(value)
        text = text.replace("\x00", "").strip()
        text = html.escape(text, quote=False)
        return text[:MAX_SHORT_TEXT_LENGTH]

    def _normalize_scalar_list(self, value: object) -> list[str]:
        if not isinstance(value, list):
            return []
        normalized = [self._normalize_short_text(item) for item in value]
        return normalized[:10]

    def _finding(
        self,
        code: str,
        message: str,
        related_artifact_id: str | None,
        *,
        severity: str = "info",
    ) -> AnswerSubmissionValidationFinding:
        return AnswerSubmissionValidationFinding(
            finding_id=f"answer-submission-finding:{code}:{related_artifact_id or 'unknown'}",
            code=code,
            severity=severity,
            message=message[:240],
            related_artifact_type="simulado_attempt_session",
            related_artifact_id=related_artifact_id,
            metadata={},
        )

    def _warning(
        self,
        code: str,
        message: str,
        related_artifact_id: str | None,
    ) -> AnswerSubmissionWarning:
        return AnswerSubmissionWarning(
            code=code,
            message=message[:240],
            severity="warning",
            related_artifact_type="simulado_attempt_session",
            related_artifact_id=related_artifact_id,
            metadata={},
        )
