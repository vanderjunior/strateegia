from __future__ import annotations

import re

from app.domain.models import (
    AnswerExplanationGuardrail,
    AssemblyValidationFinding,
    AssemblyWarning,
    CandidateDraftSummary,
    CandidateGuardrailSummary,
    CandidateSourceEvidenceSummary,
    QuestionDraft,
    QuestionDraftSet,
    QuestionGenerationBlueprint,
    QuestionGenerationBlueprintSet,
    SimuladoBlueprint,
    SimuladoQuestionAssembly,
    SimuladoQuestionCandidate,
    SimuladoQuestionSlot,
)
from app.repositories.json_store import JsonStudyRepository


MAX_DRAFT_STEM_PREVIEW_LENGTH = 240
MAX_DRAFT_COMMAND_PREVIEW_LENGTH = 160
MAX_SAFE_SNIPPET_LENGTH = 240
ASSEMBLY_BUILD_METHOD = "heuristic_simulado_question_assembly_builder"


class SimuladoQuestionAssemblyService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_assembly(
        self,
        source_simulado_blueprint_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoQuestionAssembly | None:
        if user_id is None:
            return None
        existing = self.repository.get_simulado_question_assembly(
            source_simulado_blueprint_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        simulado = self.repository.get_simulado_blueprint_by_id(
            source_simulado_blueprint_id,
            user_id=user_id,
        )
        if simulado is None:
            return None

        qgb_set = self.repository.get_question_generation_blueprint(
            source_simulado_blueprint_id,
            user_id=user_id,
        )
        if qgb_set is None:
            return None

        draft_set = self.repository.get_question_draft_set(
            qgb_set.blueprint_set_id,
            user_id=user_id,
        )

        qgb_by_slot = {item.source_question_slot_id: item for item in qgb_set.slot_blueprints}
        drafts_by_blueprint = {
            item.source_question_generation_blueprint_id: item
            for item in (draft_set.drafts if draft_set is not None else [])
        }
        guardrails_by_draft = {
            item.source_question_draft_id: item
            for item in self.repository.list_user_answer_explanation_guardrails(user_id=user_id)
        }

        candidates = [
            self._build_candidate(
                slot,
                qgb_by_slot.get(slot.slot_id),
                drafts_by_blueprint,
                guardrails_by_draft,
            )
            for slot in sorted(simulado.question_slots, key=lambda item: item.order_index)
        ]
        readiness_state = self._assembly_state(candidates)
        ready_for_review_count = sum(item.readiness_state == "candidate_ready_for_review" for item in candidates)
        blocked_count = sum(item.readiness_state.startswith("candidate_blocked_by_") for item in candidates)
        needs_review_count = sum(item.readiness_state == "candidate_needs_review" for item in candidates)
        validation_findings = self._aggregate_findings(candidates)
        warnings = self._aggregate_warnings(candidates)

        result = SimuladoQuestionAssembly(
            assembly_id=f"simulado-question-assembly:{source_simulado_blueprint_id}",
            user_id=user_id,
            source_simulado_blueprint_id=source_simulado_blueprint_id,
            source_question_generation_blueprint_set_id=qgb_set.blueprint_set_id,
            source_question_draft_set_id=draft_set.draft_set_id if draft_set is not None else None,
            status=readiness_state,
            readiness_state=readiness_state,
            total_candidates=len(candidates),
            ready_for_review_count=ready_for_review_count,
            blocked_count=blocked_count,
            needs_review_count=needs_review_count,
            candidates=candidates,
            validation_findings=validation_findings,
            warnings=warnings,
            requires_human_review=True,
            not_executable=True,
            not_scoreable=True,
            no_student_attempts_enabled=True,
            no_progress_mutation=True,
            no_final_questions_created=True,
            no_final_answer_keys_created=True,
            no_final_explanations_created=True,
            metadata={
                "build_method": ASSEMBLY_BUILD_METHOD,
                "llm_used": False,
                "external_calls_used": False,
                "question_generation_blueprint_available": qgb_set is not None,
                "question_draft_set_available": draft_set is not None,
            },
        )
        self.repository.save_simulado_question_assembly(result, user_id=user_id)
        return result

    def get_assembly(
        self,
        source_simulado_blueprint_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoQuestionAssembly | None:
        return self.repository.get_simulado_question_assembly(
            source_simulado_blueprint_id,
            user_id=user_id,
        )

    def get_assembly_by_id(
        self,
        assembly_id: str,
        *,
        user_id: str | None,
    ) -> SimuladoQuestionAssembly | None:
        return self.repository.get_simulado_question_assembly_by_id(assembly_id, user_id=user_id)

    def _build_candidate(
        self,
        slot: SimuladoQuestionSlot,
        slot_blueprint: QuestionGenerationBlueprint | None,
        drafts_by_blueprint: dict[str, QuestionDraft],
        guardrails_by_draft: dict[str, AnswerExplanationGuardrail],
    ) -> SimuladoQuestionCandidate:
        findings: list[AssemblyValidationFinding] = []
        warnings: list[AssemblyWarning] = []

        if slot_blueprint is None:
            findings.append(
                self._finding(
                    "missing_question_generation_blueprint",
                    "blocked",
                    "The simulado slot does not have a matching question generation blueprint.",
                    "simulado_question_slot",
                    slot.slot_id,
                )
            )
            return self._candidate_from_missing(
                slot,
                readiness_state="candidate_blocked_by_missing_draft",
                findings=findings,
                warnings=warnings,
            )

        draft = drafts_by_blueprint.get(slot_blueprint.blueprint_id)
        if draft is None:
            findings.append(
                self._finding(
                    "missing_question_draft",
                    "blocked",
                    "The simulado slot does not have a matching question draft.",
                    "question_generation_blueprint",
                    slot_blueprint.blueprint_id,
                )
            )
            return self._candidate(
                slot,
                slot_blueprint=slot_blueprint,
                readiness_state="candidate_blocked_by_missing_draft",
                findings=findings,
                warnings=warnings,
            )

        guardrail = guardrails_by_draft.get(draft.draft_id)
        if guardrail is None:
            findings.append(
                self._finding(
                    "missing_answer_explanation_guardrail",
                    "blocked",
                    "The question draft does not have a matching answer/explanation guardrail.",
                    "question_draft",
                    draft.draft_id,
                )
            )
            return self._candidate(
                slot,
                slot_blueprint=slot_blueprint,
                draft=draft,
                readiness_state="candidate_blocked_by_missing_guardrail",
                findings=findings,
                warnings=warnings,
            )

        readiness_state = self._candidate_state(draft, guardrail, findings, warnings)
        return self._candidate(
            slot,
            slot_blueprint=slot_blueprint,
            draft=draft,
            guardrail=guardrail,
            readiness_state=readiness_state,
            findings=findings,
            warnings=warnings,
        )

    def _candidate_state(
        self,
        draft: QuestionDraft,
        guardrail: AnswerExplanationGuardrail,
        findings: list[AssemblyValidationFinding],
        warnings: list[AssemblyWarning],
    ) -> str:
        if not draft.review_required or not draft.finalization_blocked or draft.draft_status == "blocked":
            findings.append(
                self._finding(
                    "draft_not_review_ready",
                    "blocked",
                    "The source question draft is not in a review-required state for safe assembly.",
                    "question_draft",
                    draft.draft_id,
                )
            )
            return "candidate_blocked_by_non_reviewed_draft"

        if draft.question_kind not in {
            "assertion_judgement",
            "case_based_multiple_choice",
            "technical_maritime_scenario",
            "direct_multiple_choice",
        }:
            findings.append(
                self._finding(
                    "unsupported_format",
                    "blocked",
                    "The source draft format is unsupported for this assembly foundation.",
                    "question_draft",
                    draft.draft_id,
                )
            )
            return "candidate_blocked_by_unsupported_format"

        if (
            not guardrail.review_required
            or not guardrail.finalization_blocked
            or not guardrail.no_final_answer_key_generated
            or not guardrail.no_final_explanation_generated
            or not guardrail.no_simulado_execution_enabled
        ):
            findings.append(
                self._finding(
                    "guardrail_not_review_ready",
                    "blocked",
                    "The guardrail is not in a safe review-only state for assembly.",
                    "answer_explanation_guardrail",
                    guardrail.guardrail_id,
                )
            )
            return "candidate_blocked_by_unfinalized_answer"

        if guardrail.answer_key_state == "answer_key_blocked_by_unsupported_format" or guardrail.status == "unsupported":
            findings.append(
                self._finding(
                    "unsupported_format",
                    "blocked",
                    "The guardrail marks this candidate as unsupported for safe assembly.",
                    "answer_explanation_guardrail",
                    guardrail.guardrail_id,
                )
            )
            return "candidate_blocked_by_unsupported_format"

        if guardrail.source_support_assessment.ocr_blocked:
            findings.append(
                self._finding(
                    "ocr_required",
                    "blocked",
                    "The source support indicates OCR is still blocking safe candidate assembly.",
                    "answer_explanation_guardrail",
                    guardrail.guardrail_id,
                )
            )
            return "candidate_blocked_by_ocr"

        source_codes = {item.code for item in guardrail.validation_findings} | {item.code for item in guardrail.warnings}
        if "material_gap" in source_codes:
            findings.append(
                self._finding(
                    "material_gap",
                    "blocked",
                    "The source support still indicates a material gap for this candidate.",
                    "answer_explanation_guardrail",
                    guardrail.guardrail_id,
                )
            )
            return "candidate_blocked_by_material_gap"

        if guardrail.source_support_assessment.missing_source:
            findings.append(
                self._finding(
                    "missing_source",
                    "blocked",
                    "The candidate still lacks source support.",
                    "answer_explanation_guardrail",
                    guardrail.guardrail_id,
                )
            )
            return "candidate_blocked_by_source_issue"

        if guardrail.source_support_assessment.ambiguous_support:
            warnings.append(
                self._warning(
                    "ambiguous_source",
                    "Source support remains ambiguous, so the candidate still needs review.",
                    "warning",
                    "answer_explanation_guardrail",
                    guardrail.guardrail_id,
                )
            )
            return "candidate_needs_review"

        if guardrail.status in {"blocked"} or guardrail.answer_key_state.startswith("answer_key_blocked_by_"):
            findings.append(
                self._finding(
                    "unfinalized_answer",
                    "blocked",
                    "The guardrail still blocks answer/explanation progression for this candidate.",
                    "answer_explanation_guardrail",
                    guardrail.guardrail_id,
                )
            )
            return "candidate_blocked_by_unfinalized_answer"

        warnings.append(
            self._warning(
                "human_review_required",
                "Candidate assembly remains review-required and non-executable.",
                "info",
                "question_draft",
                draft.draft_id,
            )
        )
        return "candidate_ready_for_review"

    def _candidate_from_missing(
        self,
        slot: SimuladoQuestionSlot,
        *,
        readiness_state: str,
        findings: list[AssemblyValidationFinding],
        warnings: list[AssemblyWarning],
    ) -> SimuladoQuestionCandidate:
        return self._candidate(
            slot,
            slot_blueprint=None,
            draft=None,
            guardrail=None,
            readiness_state=readiness_state,
            findings=findings,
            warnings=warnings,
        )

    def _candidate(
        self,
        slot: SimuladoQuestionSlot,
        *,
        slot_blueprint: QuestionGenerationBlueprint | None = None,
        draft: QuestionDraft | None = None,
        guardrail: AnswerExplanationGuardrail | None = None,
        readiness_state: str,
        findings: list[AssemblyValidationFinding],
        warnings: list[AssemblyWarning],
    ) -> SimuladoQuestionCandidate:
        draft_summary = CandidateDraftSummary(
            source_question_draft_id=draft.draft_id if draft is not None else "",
            draft_status=draft.draft_status if draft is not None else "missing",
            draft_readiness=draft.draft_readiness if draft is not None else "missing",
            review_required=draft.review_required if draft is not None else True,
            finalization_blocked=draft.finalization_blocked if draft is not None else True,
            draft_stem_preview=self._limit(draft.draft_stem, MAX_DRAFT_STEM_PREVIEW_LENGTH) if draft else None,
            draft_command_preview=self._limit(draft.draft_command, MAX_DRAFT_COMMAND_PREVIEW_LENGTH) if draft else None,
            draft_type=draft.question_kind if draft is not None else "missing",
            placeholder_count=len(draft.draft_option_placeholders) if draft is not None else 0,
            source_reference_count=len(draft.source_references) if draft is not None else 0,
            metadata={"format_type": draft.format_type if draft is not None else slot.format_type},
        )
        guardrail_summary = CandidateGuardrailSummary(
            source_guardrail_id=guardrail.guardrail_id if guardrail is not None else None,
            guardrail_status=guardrail.status if guardrail is not None else "missing",
            answer_key_state=guardrail.answer_key_state if guardrail is not None else "missing",
            explanation_state=guardrail.explanation_state if guardrail is not None else "missing",
            review_required=guardrail.review_required if guardrail is not None else True,
            finalization_blocked=guardrail.finalization_blocked if guardrail is not None else True,
            no_final_answer_key_generated=guardrail.no_final_answer_key_generated if guardrail is not None else True,
            no_final_explanation_generated=guardrail.no_final_explanation_generated if guardrail is not None else True,
            no_simulado_execution_enabled=guardrail.no_simulado_execution_enabled if guardrail is not None else True,
            source_support_state=(
                guardrail.source_support_assessment.source_coverage_state if guardrail is not None else "missing"
            ),
            metadata={},
        )
        source_evidence_summary = CandidateSourceEvidenceSummary(
            source_reference_count=len(draft.source_references) if draft is not None else 0,
            primary_source_available=(
                guardrail.source_support_assessment.primary_source_available if guardrail is not None else False
            ),
            missing_source=guardrail.source_support_assessment.missing_source if guardrail is not None else draft is None,
            ambiguous_support=(
                guardrail.source_support_assessment.ambiguous_support if guardrail is not None else False
            ),
            ocr_blocked=guardrail.source_support_assessment.ocr_blocked if guardrail is not None else False,
            material_gap=any(item.code == "material_gap" for item in findings),
            safe_snippets=(
                [self._limit(item, MAX_SAFE_SNIPPET_LENGTH) for item in guardrail.source_support_assessment.safe_snippets]
                if guardrail is not None
                else []
            ),
            metadata={},
        )
        return SimuladoQuestionCandidate(
            candidate_id=f"simulado-question-candidate:{slot.slot_id}",
            source_simulado_slot_id=slot.slot_id,
            source_question_generation_blueprint_id=slot_blueprint.blueprint_id if slot_blueprint else None,
            source_question_generation_slot_id=slot_blueprint.source_question_slot_id if slot_blueprint else None,
            source_question_draft_id=draft.draft_id if draft else None,
            source_guardrail_id=guardrail.guardrail_id if guardrail else None,
            format_type=(draft.format_type if draft else slot_blueprint.format_type if slot_blueprint else slot.format_type),
            question_kind=(draft.question_kind if draft else slot_blueprint.question_kind if slot_blueprint else "unknown"),
            board_id=(draft.board_id if draft else slot_blueprint.board_id if slot_blueprint else None),
            exam_family=(draft.exam_family if draft else slot_blueprint.exam_family if slot_blueprint else None),
            target_subject_id=(draft.target_subject_id if draft else slot.target_subject_id),
            target_topic_id=(draft.target_topic_id if draft else slot.target_topic_id),
            target_subtopic_ids=(
                list(draft.target_subtopic_ids)
                if draft
                else list(slot_blueprint.target_subtopic_ids)
                if slot_blueprint
                else list(slot.target_subtopic_ids)
            ),
            readiness_state=readiness_state,
            draft_summary=draft_summary,
            guardrail_summary=guardrail_summary,
            source_evidence_summary=source_evidence_summary,
            validation_findings=findings,
            warnings=warnings,
            requires_human_review=True,
            not_executable=True,
            not_scoreable=True,
            metadata={"slot_readiness_state": slot.readiness_state},
        )

    def _assembly_state(self, candidates: list[SimuladoQuestionCandidate]) -> str:
        if not candidates:
            return "assembly_no_candidates"
        ready = sum(item.readiness_state == "candidate_ready_for_review" for item in candidates)
        blocked = sum(item.readiness_state.startswith("candidate_blocked_by_") for item in candidates)
        review = sum(item.readiness_state == "candidate_needs_review" for item in candidates)
        if ready == 0 and blocked == len(candidates):
            return "assembly_blocked"
        if blocked > 0:
            return "assembly_partially_blocked"
        if review > 0:
            return "assembly_needs_review"
        return "assembly_ready_for_review"

    def _aggregate_findings(self, candidates: list[SimuladoQuestionCandidate]) -> list[AssemblyValidationFinding]:
        findings: list[AssemblyValidationFinding] = [
            self._finding(
                "not_executable",
                "info",
                "This assembly is non-executable in the current pass.",
                "simulado_question_assembly",
                "assembly",
            ),
            self._finding(
                "not_scoreable",
                "info",
                "This assembly is not scoreable and does not include correction rules.",
                "simulado_question_assembly",
                "assembly",
            ),
            self._finding(
                "no_student_attempts_enabled",
                "info",
                "Student attempts remain disabled in this pass.",
                "simulado_question_assembly",
                "assembly",
            ),
            self._finding(
                "no_progress_mutation",
                "info",
                "Building the assembly does not mutate user progress or runtime state.",
                "simulado_question_assembly",
                "assembly",
            ),
        ]
        findings.extend(item for candidate in candidates for item in candidate.validation_findings)
        deduped: dict[tuple[str, str | None], AssemblyValidationFinding] = {}
        for item in findings:
            deduped.setdefault((item.code, item.related_artifact_id), item)
        return [deduped[key] for key in sorted(deduped)]

    def _aggregate_warnings(self, candidates: list[SimuladoQuestionCandidate]) -> list[AssemblyWarning]:
        warnings: list[AssemblyWarning] = [
            self._warning(
                "human_review_required",
                "All assembled candidates remain review-required and non-executable.",
                "info",
                "simulado_question_assembly",
                "assembly",
            )
        ]
        warnings.extend(item for candidate in candidates for item in candidate.warnings)
        deduped: dict[tuple[str, str | None], AssemblyWarning] = {}
        for item in warnings:
            deduped.setdefault((item.code, item.related_artifact_id), item)
        return [deduped[key] for key in sorted(deduped)]

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

    def _finding(
        self,
        code: str,
        severity: str,
        message: str,
        related_artifact_type: str,
        related_artifact_id: str | None,
    ) -> AssemblyValidationFinding:
        return AssemblyValidationFinding(
            finding_id=f"assembly-finding:{related_artifact_type}:{related_artifact_id or code}:{code}",
            code=code,
            severity=severity,
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
        related_artifact_id: str | None,
    ) -> AssemblyWarning:
        return AssemblyWarning(
            code=code,
            message=message,
            severity=severity,
            related_artifact_type=related_artifact_type,
            related_artifact_id=related_artifact_id,
            metadata={},
        )
