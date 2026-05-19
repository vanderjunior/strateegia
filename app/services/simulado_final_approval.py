from __future__ import annotations

import json

from app.domain.models import (
    CandidateFinalizationSummary,
    FinalApprovalAuditTrailEntry,
    FinalApprovalCandidateRecord,
    FinalApprovalDecision,
    FinalApprovalValidationFinding,
    FinalApprovalWarning,
    SimuladoFinalApprovalArtifact,
    SimuladoFinalizationGuardrail,
)
from app.repositories.json_store import JsonStudyRepository


FINAL_APPROVAL_BUILD_METHOD = "heuristic_simulado_final_approval_builder"
ALLOWED_DECISION_TYPES = {
    "approve_for_future_execution_review",
    "reject",
    "request_revision",
    "block",
    "mark_not_reviewed",
}
REASON_MAX_LENGTH = 240
AUDIT_MESSAGE_MAX_LENGTH = 240


class SimuladoFinalApprovalService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_approval_artifact(
        self,
        source_finalization_guardrail_id: str,
        *,
        user_id: str | None,
        decision_payload: dict[str, object] | None = None,
    ) -> SimuladoFinalApprovalArtifact | None:
        if user_id is None:
            return None

        normalized_payload = self._normalize_payload(decision_payload, default_reviewer_id=user_id)
        payload_signature = self._payload_signature(normalized_payload)
        existing = self.repository.get_simulado_final_approval_artifact(
            source_finalization_guardrail_id,
            user_id=user_id,
        )
        if existing is not None and existing.metadata.get("decision_signature") == payload_signature:
            return existing

        guardrail = self.repository.get_simulado_finalization_guardrail_by_id(
            source_finalization_guardrail_id,
            user_id=user_id,
        )
        if guardrail is None:
            return None

        decisions = self._build_decisions(guardrail, normalized_payload)
        decision_map = {item.source_candidate_id: item for item in decisions if item.source_candidate_id}
        candidate_records = [
            self._candidate_record(summary, decision_map.get(summary.source_question_candidate_id))
            for summary in guardrail.candidate_summaries
        ]
        audit_trail = self._build_audit_trail(
            guardrail=guardrail,
            reviewer_id=user_id,
            approval_recorded=bool(decisions),
            decisions=decisions,
        )
        validation_findings = self._build_findings(guardrail, bool(decisions))
        warnings = self._build_warnings(guardrail, candidate_records, bool(decisions))
        status, readiness_state = self._artifact_state(guardrail, candidate_records, bool(decisions))
        counts = self._candidate_counts(candidate_records)

        human_approved = any(
            item.approval_state == "candidate_approved_for_future_execution_review"
            for item in candidate_records
        )
        human_reviewer_id = user_id if decisions else None

        result = SimuladoFinalApprovalArtifact(
            approval_artifact_id=f"simulado-final-approval:{source_finalization_guardrail_id}",
            user_id=user_id,
            source_finalization_guardrail_id=source_finalization_guardrail_id,
            source_attempt_shell_id=guardrail.source_attempt_shell_id,
            source_assembly_id=guardrail.source_assembly_id,
            source_simulado_blueprint_id=guardrail.source_simulado_blueprint_id,
            status=status,
            readiness_state=readiness_state,
            total_candidates=guardrail.total_candidates,
            approved_candidate_count=counts["approved"],
            blocked_candidate_count=counts["blocked"],
            needs_review_candidate_count=counts["needs_revision"],
            rejected_candidate_count=counts["rejected"],
            not_reviewed_candidate_count=counts["not_reviewed"],
            candidate_records=candidate_records,
            decisions=decisions,
            audit_trail=audit_trail,
            validation_findings=validation_findings,
            warnings=warnings,
            approval_recorded=bool(decisions),
            human_approved=human_approved,
            human_reviewer_id=human_reviewer_id,
            human_review_required=True,
            execution_enabled=False,
            correction_enabled=False,
            scoring_enabled=False,
            student_submission_enabled=False,
            progress_mutation_enabled=False,
            no_student_attempt_created=True,
            no_answer_submission_enabled=True,
            no_correction_result_created=True,
            no_score_created=True,
            metadata={
                "build_method": FINAL_APPROVAL_BUILD_METHOD,
                "decision_signature": payload_signature,
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_simulado_final_approval_artifact(result, user_id=user_id)
        return result

    def get_approval_artifact(
        self,
        source_finalization_guardrail_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoFinalApprovalArtifact | None:
        return self.repository.get_simulado_final_approval_artifact(
            source_finalization_guardrail_id,
            user_id=user_id,
        )

    def get_approval_artifact_by_id(
        self,
        approval_artifact_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoFinalApprovalArtifact | None:
        return self.repository.get_simulado_final_approval_artifact_by_id(
            approval_artifact_id,
            user_id=user_id,
        )

    def _normalize_payload(
        self,
        payload: dict[str, object] | None,
        *,
        default_reviewer_id: str,
    ) -> dict[str, object]:
        if not isinstance(payload, dict):
            return {"decisions": []}
        raw_decisions = payload.get("decisions")
        if not isinstance(raw_decisions, list):
            return {"decisions": []}
        normalized: list[dict[str, object]] = []
        for item in raw_decisions:
            if not isinstance(item, dict):
                continue
            source_candidate_id = item.get("source_candidate_id")
            decision_type = item.get("decision_type")
            if not isinstance(source_candidate_id, str) or not source_candidate_id:
                continue
            if not isinstance(decision_type, str) or decision_type not in ALLOWED_DECISION_TYPES:
                continue
            reviewer_id = item.get("reviewer_id")
            if not isinstance(reviewer_id, str) or not reviewer_id:
                reviewer_id = default_reviewer_id
            reason = item.get("reason")
            if not isinstance(reason, str):
                reason = ""
            normalized.append(
                {
                    "source_candidate_id": source_candidate_id,
                    "decision_type": decision_type,
                    "reviewer_id": reviewer_id,
                    "reason": self._truncate(reason, REASON_MAX_LENGTH),
                }
            )
        normalized.sort(key=lambda item: (str(item["source_candidate_id"]), str(item["decision_type"])))
        return {"decisions": normalized}

    def _payload_signature(self, payload: dict[str, object]) -> str:
        return json.dumps(payload, ensure_ascii=True, sort_keys=True)

    def _build_decisions(
        self,
        guardrail: SimuladoFinalizationGuardrail,
        payload: dict[str, object],
    ) -> list[FinalApprovalDecision]:
        allowed_candidate_ids = {
            item.source_question_candidate_id
            for item in guardrail.candidate_summaries
            if item.source_question_candidate_id
        }
        decisions: list[FinalApprovalDecision] = []
        for item in payload.get("decisions", []):
            if not isinstance(item, dict):
                continue
            source_candidate_id = item.get("source_candidate_id")
            decision_type = item.get("decision_type")
            reviewer_id = item.get("reviewer_id")
            reason = item.get("reason")
            if source_candidate_id not in allowed_candidate_ids:
                continue
            if not isinstance(decision_type, str):
                continue
            if not isinstance(reviewer_id, str):
                reviewer_id = None
            if not isinstance(reason, str):
                reason = None
            decisions.append(
                FinalApprovalDecision(
                    decision_id=f"final-approval-decision:{source_candidate_id}:{decision_type}",
                    source_candidate_id=source_candidate_id,
                    decision_type=decision_type,
                    decision_state=self._decision_state(decision_type),
                    reviewer_id=reviewer_id,
                    reason=reason,
                    metadata={},
                )
            )
        return decisions

    def _decision_state(self, decision_type: str) -> str:
        if decision_type == "request_revision":
            return "decision_needs_revision"
        if decision_type == "block":
            return "decision_blocked"
        return "decision_recorded"

    def _candidate_record(
        self,
        summary: CandidateFinalizationSummary,
        decision: FinalApprovalDecision | None,
    ) -> FinalApprovalCandidateRecord:
        default_state = self._default_approval_state(summary)
        approval_state = default_state if decision is None else self._decision_to_approval_state(decision.decision_type)
        return FinalApprovalCandidateRecord(
            record_id=f"final-approval-record:{summary.candidate_id}",
            source_candidate_id=summary.source_question_candidate_id,
            source_question_draft_id=summary.source_question_draft_id,
            source_guardrail_id=summary.source_guardrail_id,
            approval_state=approval_state,
            decision_id=decision.decision_id if decision is not None else None,
            blockers=list(summary.blockers),
            warnings=list(summary.warnings),
            final_question_ready=False,
            final_answer_key_ready=False,
            final_explanation_ready=False,
            requires_human_review=True,
            metadata={
                "source_readiness_state": summary.readiness_state,
                "finalization_blocked": summary.finalization_blocked,
            },
        )

    def _default_approval_state(self, summary: CandidateFinalizationSummary) -> str:
        if summary.readiness_state in {
            "candidate_blocked_by_unsupported_format",
            "candidate_blocked_by_source_issue",
            "candidate_blocked_by_unreviewed_draft",
            "candidate_blocked_by_unfinalized_guardrail",
        }:
            return "candidate_blocked"
        if summary.readiness_state == "candidate_needs_human_review":
            return "candidate_needs_revision"
        return "candidate_not_reviewed"

    def _decision_to_approval_state(self, decision_type: str) -> str:
        return {
            "approve_for_future_execution_review": "candidate_approved_for_future_execution_review",
            "reject": "candidate_rejected",
            "request_revision": "candidate_needs_revision",
            "block": "candidate_blocked",
            "mark_not_reviewed": "candidate_not_reviewed",
        }[decision_type]

    def _candidate_counts(self, records: list[FinalApprovalCandidateRecord]) -> dict[str, int]:
        counts = {
            "approved": 0,
            "blocked": 0,
            "needs_revision": 0,
            "rejected": 0,
            "not_reviewed": 0,
        }
        for record in records:
            if record.approval_state == "candidate_approved_for_future_execution_review":
                counts["approved"] += 1
            elif record.approval_state == "candidate_blocked":
                counts["blocked"] += 1
            elif record.approval_state == "candidate_needs_revision":
                counts["needs_revision"] += 1
            elif record.approval_state == "candidate_rejected":
                counts["rejected"] += 1
            else:
                counts["not_reviewed"] += 1
        return counts

    def _artifact_state(
        self,
        guardrail: SimuladoFinalizationGuardrail,
        records: list[FinalApprovalCandidateRecord],
        approval_recorded: bool,
    ) -> tuple[str, str]:
        if guardrail.total_candidates == 0:
            return "approval_blocked", "blocked_by_unreviewed_candidates"
        if any(item.code == "blocked_by_missing_final_questions" for item in guardrail.blockers):
            return "approval_blocked", "blocked_by_missing_final_question"
        if any(item.code == "blocked_by_missing_final_answer_keys" for item in guardrail.blockers):
            return "approval_blocked", "blocked_by_missing_final_answer_key"
        if any(item.code == "blocked_by_missing_final_explanations" for item in guardrail.blockers):
            return "approval_blocked", "blocked_by_missing_final_explanation"
        if any(item.code == "blocked_by_attempt_shell_not_executable" for item in guardrail.blockers):
            return "approval_blocked", "blocked_by_unfinalizable_candidates"
        if any(item.code == "blocked_by_non_final_assembly" for item in guardrail.blockers):
            return "approval_blocked", "blocked_by_unfinalizable_candidates"
        if not approval_recorded:
            return "approval_needs_review", "blocked_by_unreviewed_candidates"
        if any(item.approval_state == "candidate_not_reviewed" for item in records):
            return "approval_partially_recorded", "blocked_by_unreviewed_candidates"
        if any(item.approval_state in {"candidate_blocked", "candidate_needs_revision"} for item in records):
            return "approval_partially_recorded", "needs_human_review"
        return "approval_artifact_created", "ready_for_future_execution_review"

    def _build_audit_trail(
        self,
        *,
        guardrail: SimuladoFinalizationGuardrail,
        reviewer_id: str,
        approval_recorded: bool,
        decisions: list[FinalApprovalDecision],
    ) -> list[FinalApprovalAuditTrailEntry]:
        entries = [
            FinalApprovalAuditTrailEntry(
                audit_id=f"final-approval-audit:create:{guardrail.finalization_guardrail_id}",
                event_type="approval_artifact_created",
                actor_user_id=reviewer_id,
                message=self._truncate(
                    "Final approval artifact created; execution, correction, scoring, submissions and progress mutation remain disabled.",
                    AUDIT_MESSAGE_MAX_LENGTH,
                ),
                metadata={},
            )
        ]
        if not approval_recorded:
            entries.append(
                FinalApprovalAuditTrailEntry(
                    audit_id=f"final-approval-audit:review-required:{guardrail.finalization_guardrail_id}",
                    event_type="human_review_required",
                    actor_user_id=reviewer_id,
                    message=self._truncate(
                        "No manual approval decisions were recorded; human review remains required.",
                        AUDIT_MESSAGE_MAX_LENGTH,
                    ),
                    metadata={},
                )
            )
        for decision in decisions:
            entries.append(
                FinalApprovalAuditTrailEntry(
                    audit_id=f"final-approval-audit:{decision.decision_id}",
                    event_type=decision.decision_type,
                    actor_user_id=decision.reviewer_id,
                    message=self._truncate(
                        f"Manual decision recorded for {decision.source_candidate_id}: {decision.decision_type}.",
                        AUDIT_MESSAGE_MAX_LENGTH,
                    ),
                    metadata={},
                )
            )
        return entries

    def _build_findings(
        self,
        guardrail: SimuladoFinalizationGuardrail,
        approval_recorded: bool,
    ) -> list[FinalApprovalValidationFinding]:
        related_artifact_id = guardrail.finalization_guardrail_id
        findings = [
            self._finding(
                "execution_disabled",
                "Execution remains disabled for this approval artifact.",
                "simulado_final_approval_artifact",
                related_artifact_id,
            ),
            self._finding(
                "correction_disabled",
                "Correction remains disabled for this approval artifact.",
                "simulado_final_approval_artifact",
                related_artifact_id,
            ),
            self._finding(
                "scoring_disabled",
                "Scoring remains disabled for this approval artifact.",
                "simulado_final_approval_artifact",
                related_artifact_id,
            ),
            self._finding(
                "student_submission_disabled",
                "Student submission remains disabled for this approval artifact.",
                "simulado_final_approval_artifact",
                related_artifact_id,
            ),
            self._finding(
                "progress_mutation_disabled",
                "Progress mutation remains disabled for this approval artifact.",
                "simulado_final_approval_artifact",
                related_artifact_id,
            ),
            self._finding(
                "no_student_attempt_created",
                "No real student attempt is created in this pass.",
                "simulado_final_approval_artifact",
                related_artifact_id,
            ),
            self._finding(
                "no_answer_submission_enabled",
                "No student answer submission is enabled in this pass.",
                "simulado_final_approval_artifact",
                related_artifact_id,
            ),
            self._finding(
                "no_correction_result_created",
                "No correction result is created in this pass.",
                "simulado_final_approval_artifact",
                related_artifact_id,
            ),
            self._finding(
                "no_score_created",
                "No score is created in this pass.",
                "simulado_final_approval_artifact",
                related_artifact_id,
            ),
            self._finding(
                "human_review_required",
                "Human review remains required for this approval artifact.",
                "simulado_final_approval_artifact",
                related_artifact_id,
            ),
        ]
        if approval_recorded:
            findings.append(
                self._finding(
                    "approval_recorded",
                    "Manual approval decisions were recorded for this approval artifact.",
                    "simulado_final_approval_artifact",
                    related_artifact_id,
                )
            )
        return findings

    def _build_warnings(
        self,
        guardrail: SimuladoFinalizationGuardrail,
        records: list[FinalApprovalCandidateRecord],
        approval_recorded: bool,
    ) -> list[FinalApprovalWarning]:
        warnings: list[FinalApprovalWarning] = []
        if not approval_recorded:
            warnings.append(
                self._warning(
                    "approval_not_recorded",
                    "No explicit human approval decision was recorded in this pass.",
                    "warning",
                    "simulado_finalization_guardrail",
                    guardrail.finalization_guardrail_id,
                )
            )
        if any(item.approval_state == "candidate_approved_for_future_execution_review" for item in records):
            warnings.append(
                self._warning(
                    "approval_does_not_enable_execution",
                    "Approved candidates remain non-executable and non-scoreable in this pass.",
                    "warning",
                    "simulado_finalization_guardrail",
                    guardrail.finalization_guardrail_id,
                )
            )
        return warnings

    def _finding(
        self,
        code: str,
        message: str,
        related_artifact_type: str,
        related_artifact_id: str,
    ) -> FinalApprovalValidationFinding:
        return FinalApprovalValidationFinding(
            finding_id=f"final-approval-finding:{code}:{related_artifact_id}",
            code=code,
            severity="info",
            message=message,
            related_artifact_type=related_artifact_type,
            related_artifact_id=related_artifact_id,
            metadata={},
        )

    def _warning(
        self,
        code: str,
        message: str,
        severity: str,
        related_artifact_type: str,
        related_artifact_id: str,
    ) -> FinalApprovalWarning:
        return FinalApprovalWarning(
            code=code,
            message=message,
            severity=severity,
            related_artifact_type=related_artifact_type,
            related_artifact_id=related_artifact_id,
            metadata={},
        )

    def _truncate(self, value: str, limit: int) -> str:
        if len(value) <= limit:
            return value
        return value[: max(0, limit - 3)] + "..."
