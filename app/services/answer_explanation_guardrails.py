from __future__ import annotations

import re

from app.domain.models import (
    AnswerExplanationGuardrail,
    AnswerExplanationWarning,
    AnswerKeyCandidate,
    ExplanationCandidate,
    QuestionDraft,
    QuestionDraftSet,
    SourceSupportAssessment,
    ValidationFinding,
)
from app.repositories.json_store import JsonStudyRepository


MAX_SAFE_SNIPPET_LENGTH = 240
MAX_EXPLANATION_OUTLINE_LENGTH = 600
GUARDRAIL_BUILD_METHOD = "heuristic_answer_explanation_guardrail_builder"
SUPPORTED_QUESTION_KINDS = {
    "assertion_judgement",
    "case_based_multiple_choice",
    "technical_maritime_scenario",
    "direct_multiple_choice",
}


class AnswerExplanationGuardrailService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_guardrail(
        self,
        source_question_draft_id: str,
        *,
        user_id: str | None,
    ) -> AnswerExplanationGuardrail | None:
        if user_id is None:
            return None
        existing = self.repository.get_answer_explanation_guardrail(
            source_question_draft_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        located = self._find_draft(source_question_draft_id, user_id=user_id)
        if located is None:
            return None
        draft_set, draft = located

        source_support = self._source_support_assessment(draft)
        status, answer_key_state, explanation_state, findings = self._assess_states(draft, source_support)
        warnings = self._warnings(draft, findings)
        candidate_answer_key = self._answer_key_candidate(draft, answer_key_state, source_support)
        candidate_explanation = self._explanation_candidate(draft, explanation_state, source_support)
        result = AnswerExplanationGuardrail(
            guardrail_id=f"answer-explanation-guardrail:{source_question_draft_id}",
            user_id=user_id,
            source_question_draft_id=draft.draft_id,
            source_question_draft_set_id=draft_set.draft_set_id,
            source_question_generation_blueprint_id=draft.source_question_generation_blueprint_id,
            source_question_generation_blueprint_set_id=draft_set.source_question_generation_blueprint_set_id,
            source_simulado_blueprint_id=draft.source_simulado_blueprint_id,
            status=status,
            answer_key_state=answer_key_state,
            explanation_state=explanation_state,
            candidate_answer_key=candidate_answer_key,
            candidate_explanation=candidate_explanation,
            source_support_assessment=source_support,
            validation_findings=findings,
            warnings=warnings,
            review_required=True,
            finalization_blocked=True,
            metadata={
                "build_method": GUARDRAIL_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
                "source_question_kind": draft.question_kind,
                "source_format_type": draft.format_type,
            },
        )
        self.repository.save_answer_explanation_guardrail(result, user_id=user_id)
        return result

    def get_guardrail(
        self,
        source_question_draft_id: str,
        *,
        user_id: str | None,
    ) -> AnswerExplanationGuardrail | None:
        return self.repository.get_answer_explanation_guardrail(
            source_question_draft_id,
            user_id=user_id,
        )

    def get_guardrail_by_id(
        self,
        guardrail_id: str,
        *,
        user_id: str | None,
    ) -> AnswerExplanationGuardrail | None:
        return self.repository.get_answer_explanation_guardrail_by_id(guardrail_id, user_id=user_id)

    def _find_draft(
        self,
        source_question_draft_id: str,
        *,
        user_id: str,
    ) -> tuple[QuestionDraftSet, QuestionDraft] | None:
        for draft_set in self.repository.list_user_question_draft_sets(user_id=user_id):
            for draft in draft_set.drafts:
                if draft.draft_id == source_question_draft_id:
                    return draft_set, draft
        return None

    def _source_support_assessment(self, draft: QuestionDraft) -> SourceSupportAssessment:
        safe_snippets = [
            self._limit(self._sanitize_text(item.safe_snippet), MAX_SAFE_SNIPPET_LENGTH)
            for item in draft.source_references
            if item.safe_snippet
        ]
        evidence_strengths = {item.evidence_strength for item in draft.source_references}
        missing_source = not draft.source_references or not draft.validation_summary.has_required_source_evidence
        ocr_blocked = any(item.code == "ocr_required" for item in draft.warnings)
        ambiguous_support = (
            draft.draft_status != "draft_created"
            or draft.draft_readiness != "draft_for_review"
            or not safe_snippets
            or "weak" in evidence_strengths
            or "unknown" in evidence_strengths
        )
        if missing_source:
            source_coverage_state = "missing"
        elif ambiguous_support:
            source_coverage_state = "ambiguous"
        else:
            source_coverage_state = "supported"
        return SourceSupportAssessment(
            assessment_id=f"source-support:{draft.draft_id}",
            source_evidence_count=len(draft.source_references),
            primary_source_available=bool(draft.source_references),
            source_coverage_state=source_coverage_state,
            source_conflict_detected=False,
            ocr_blocked=ocr_blocked,
            missing_source=missing_source,
            ambiguous_support=ambiguous_support and not missing_source,
            safe_snippets=safe_snippets,
            metadata={
                "source_grounded": draft.validation_summary.source_grounded,
                "has_required_source_evidence": draft.validation_summary.has_required_source_evidence,
            },
        )

    def _assess_states(
        self,
        draft: QuestionDraft,
        source_support: SourceSupportAssessment,
    ) -> tuple[str, str, str, list[ValidationFinding]]:
        findings = self._base_findings(draft)
        if draft.draft_status == "blocked" or draft.draft_readiness.startswith("blocked_"):
            findings.append(
                self._finding(
                    draft,
                    "draft_not_ready",
                    "blocked",
                    "The source draft is blocked and cannot progress to answer/explanation assessment.",
                )
            )
            return (
                "blocked",
                "answer_key_blocked_by_non_ready_draft",
                "explanation_blocked_by_non_ready_draft",
                findings,
            )
        if draft.question_kind not in SUPPORTED_QUESTION_KINDS:
            findings.append(
                self._finding(
                    draft,
                    "unsupported_format",
                    "blocked",
                    "The draft question kind is not supported by this guardrail foundation.",
                )
            )
            return (
                "unsupported",
                "answer_key_blocked_by_unsupported_format",
                "explanation_blocked_by_unsupported_format",
                findings,
            )
        if source_support.missing_source:
            findings.append(
                self._finding(
                    draft,
                    "source_missing",
                    "blocked",
                    "The draft does not have enough source evidence for guarded answer/explanation assessment.",
                )
            )
            return (
                "blocked",
                "answer_key_blocked_by_missing_source",
                "explanation_blocked_by_missing_source",
                findings,
            )

        if draft.question_kind == "assertion_judgement":
            if source_support.ambiguous_support:
                findings.append(
                    self._finding(
                        draft,
                        "source_ambiguous",
                        "warning",
                        "Source support exists, but it still needs human review before any answer candidate step.",
                    )
                )
                return (
                    "needs_review",
                    "answer_key_needs_human_review",
                    "explanation_needs_human_review",
                    findings,
                )
            return (
                "ready_for_review",
                "answer_key_candidate_ready_for_review",
                "explanation_candidate_ready_for_review",
                findings,
            )

        if draft.question_kind in {"case_based_multiple_choice", "direct_multiple_choice"}:
            findings.append(
                self._finding(
                    draft,
                    "placeholders_not_final",
                    "warning",
                    "Placeholder alternatives remain non-final, so answer key selection stays blocked.",
                )
            )
            findings.append(
                self._finding(
                    draft,
                    "alternatives_not_final",
                    "info",
                    "Alternative placeholders do not authorize a final answer key or distractor analysis.",
                )
            )
            explanation_state = (
                "explanation_needs_human_review"
                if source_support.ambiguous_support
                else "explanation_candidate_ready_for_review"
            )
            return (
                "needs_review",
                "answer_key_blocked_by_ambiguous_draft",
                explanation_state,
                findings,
            )

        if draft.question_kind == "technical_maritime_scenario":
            findings.append(
                self._finding(
                    draft,
                    "technical_term_review_required",
                    "warning",
                    "Technical maritime terminology still requires specialized human review.",
                )
            )
            findings.append(
                self._finding(
                    draft,
                    "source_topic_mapping_required",
                    "warning",
                    "The future answer/explanation step must preserve explicit source-to-topic mapping.",
                )
            )
            findings.append(
                self._finding(
                    draft,
                    "human_review_required",
                    "warning",
                    "Technical maritime drafts require human review before any candidate answer use.",
                )
            )
            explanation_state = (
                "explanation_needs_human_review"
                if source_support.ambiguous_support
                else "explanation_candidate_ready_for_review"
            )
            return (
                "needs_review",
                "answer_key_needs_human_review",
                explanation_state,
                findings,
            )

        findings.append(
            self._finding(
                draft,
                "unsupported_format",
                "blocked",
                "The draft question kind is not supported by this guardrail foundation.",
            )
        )
        return (
            "unsupported",
            "answer_key_blocked_by_unsupported_format",
            "explanation_blocked_by_unsupported_format",
            findings,
        )

    def _base_findings(self, draft: QuestionDraft) -> list[ValidationFinding]:
        return [
            self._finding(
                draft,
                "answer_not_final",
                "info",
                "Any candidate answer key produced by this guardrail remains non-final.",
            ),
            self._finding(
                draft,
                "explanation_not_final",
                "info",
                "Any explanation candidate produced by this guardrail remains non-final.",
            ),
            self._finding(
                draft,
                "human_review_required",
                "warning",
                "Human review remains required before any downstream use.",
            ),
            self._finding(
                draft,
                "finalization_blocked",
                "info",
                "Question finalization remains blocked in this pass.",
            ),
            self._finding(
                draft,
                "no_simulado_execution",
                "info",
                "This assessment does not enable simulado execution, scoring or correction.",
            ),
        ]

    def _answer_key_candidate(
        self,
        draft: QuestionDraft,
        answer_key_state: str,
        source_support: SourceSupportAssessment,
    ) -> AnswerKeyCandidate:
        return AnswerKeyCandidate(
            candidate_id=f"answer-key-candidate:{draft.draft_id}",
            format_type=draft.format_type,
            candidate_value=None,
            allowed_values=self._allowed_values(draft),
            confidence=0.0 if answer_key_state.startswith("answer_key_blocked") else 0.35,
            support_state=source_support.source_coverage_state,
            requires_review=True,
            finalization_blocked=True,
            rationale_summary=self._answer_rationale(draft, answer_key_state),
            metadata={"question_kind": draft.question_kind},
        )

    def _explanation_candidate(
        self,
        draft: QuestionDraft,
        explanation_state: str,
        source_support: SourceSupportAssessment,
    ) -> ExplanationCandidate:
        outline = None
        if explanation_state in {
            "explanation_candidate_ready_for_review",
            "explanation_needs_human_review",
        } and source_support.safe_snippets:
            topic_label = self._topic_label(draft.target_topic_id)
            outline = self._limit(
                (
                    f"Outline provisiorio de explicacao ancorada em fonte sobre {topic_label}: "
                    f"revisar o trecho '{source_support.safe_snippets[0]}' antes de qualquer justificativa final."
                ),
                MAX_EXPLANATION_OUTLINE_LENGTH,
            )
        return ExplanationCandidate(
            candidate_id=f"explanation-candidate:{draft.draft_id}",
            explanation_outline=outline,
            source_anchor_ids=[item.evidence_id for item in draft.source_references],
            support_state=source_support.source_coverage_state,
            confidence=0.0 if outline is None else 0.35,
            requires_review=True,
            finalization_blocked=True,
            metadata={"question_kind": draft.question_kind},
        )

    def _warnings(
        self,
        draft: QuestionDraft,
        findings: list[ValidationFinding],
    ) -> list[AnswerExplanationWarning]:
        warnings = [
            AnswerExplanationWarning(
                code=item.code,
                message=item.message,
                severity=item.severity,
                related_artifact_type=item.related_artifact_type,
                related_artifact_id=item.related_artifact_id,
                metadata=dict(item.metadata),
            )
            for item in draft.warnings
        ]
        warnings.extend(
            [
                AnswerExplanationWarning(
                    code=item.code,
                    message=item.message,
                    severity=item.severity,
                    related_artifact_type=item.related_artifact_type,
                    related_artifact_id=item.related_artifact_id,
                    metadata=dict(item.metadata),
                )
                for item in findings
            ]
        )
        deduped: dict[tuple[str, str | None], AnswerExplanationWarning] = {}
        for item in warnings:
            deduped.setdefault((item.code, item.related_artifact_id), item)
        return [deduped[key] for key in sorted(deduped)]

    def _allowed_values(self, draft: QuestionDraft) -> list[str]:
        if draft.question_kind == "assertion_judgement" and draft.format_type == "true_false":
            return ["C", "E"]
        if draft.format_type == "multiple_choice_5":
            return ["A", "B", "C", "D", "E"]
        if draft.format_type == "multiple_choice_4":
            return ["A", "B", "C", "D"]
        return []

    def _answer_rationale(self, draft: QuestionDraft, answer_key_state: str) -> str:
        topic_label = self._topic_label(draft.target_topic_id)
        if answer_key_state == "answer_key_candidate_ready_for_review":
            return f"A future answer candidate may be reviewed later for {topic_label}, but it remains non-final."
        if answer_key_state == "answer_key_needs_human_review":
            return f"Human review remains necessary before any answer candidate can be considered for {topic_label}."
        if answer_key_state == "answer_key_blocked_by_ambiguous_draft":
            return f"The draft for {topic_label} is still ambiguous, so answer key selection remains blocked."
        if answer_key_state == "answer_key_blocked_by_missing_source":
            return f"The draft for {topic_label} lacks enough source evidence for answer key assessment."
        if answer_key_state == "answer_key_blocked_by_non_ready_draft":
            return f"The source draft for {topic_label} is not ready for answer key assessment."
        if answer_key_state == "answer_key_blocked_by_unsupported_format":
            return f"The current draft format for {topic_label} is unsupported by this guardrail layer."
        return f"Answer key assessment remains conservative for {topic_label}."

    def _finding(
        self,
        draft: QuestionDraft,
        code: str,
        severity: str,
        message: str,
    ) -> ValidationFinding:
        return ValidationFinding(
            finding_id=f"finding:{draft.draft_id}:{code}",
            code=code,
            severity=severity,
            message=message,
            related_artifact_type="question_draft",
            related_artifact_id=draft.draft_id,
            metadata={"question_kind": draft.question_kind},
        )

    def _topic_label(self, topic_id: str) -> str:
        value = topic_id.split(":")[-1].replace("_", " ").replace("-", " ").strip()
        return value.title() if value else "Topico"

    def _sanitize_text(self, value: str | None) -> str:
        if not value:
            return ""
        compact = " ".join(str(value).split())
        compact = compact.replace("file://", "[path]")
        compact = re.sub(r"/Users/[^\s]+", "[path]", compact)
        compact = re.sub(r"/private/[^\s]+", "[path]", compact)
        return compact

    def _limit(self, value: str | None, max_length: int) -> str | None:
        if value is None:
            return None
        compact = self._sanitize_text(value)
        if len(compact) <= max_length:
            return compact
        return compact[: max_length - 1].rstrip() + "…"
