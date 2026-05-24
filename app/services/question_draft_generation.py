from __future__ import annotations

import re

from app.domain.models import (
    QuestionDraft,
    QuestionDraftConstraint,
    QuestionDraftProvenance,
    QuestionDraftSet,
    QuestionDraftSourceReference,
    QuestionDraftValidationSummary,
    QuestionDraftWarning,
    QuestionGenerationBlueprint,
    QuestionGenerationBlueprintSet,
)
from app.repositories.json_store import JsonStudyRepository


MAX_STEM_LENGTH = 800
MAX_COMMAND_LENGTH = 240
MAX_STATEMENT_LENGTH = 600
MAX_SCENARIO_LENGTH = 800
MAX_OPTION_PLACEHOLDER_LENGTH = 160
MAX_SAFE_SNIPPET_LENGTH = 240
DRAFT_BUILD_METHOD = "heuristic_question_draft_generator"


class QuestionDraftGenerationService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_draft_set(
        self,
        source_question_generation_blueprint_set_id: str,
        *,
        user_id: str | None,
    ) -> QuestionDraftSet | None:
        if user_id is None:
            return None
        existing = self.repository.get_question_draft_set(
            source_question_generation_blueprint_set_id,
            user_id=user_id,
        )
        if existing is not None:
            return existing

        blueprint_set = self.repository.get_question_generation_blueprint_by_id(
            source_question_generation_blueprint_set_id,
            user_id=user_id,
        )
        if blueprint_set is None:
            return None

        drafts: list[QuestionDraft] = []
        skipped_blueprint_ids: list[str] = []
        blocked_count = 0
        needs_review_count = 0
        skipped_count = 0

        for slot_blueprint in sorted(blueprint_set.slot_blueprints, key=lambda item: item.blueprint_id):
            if slot_blueprint.readiness_state != "ready_for_draft":
                skipped_blueprint_ids.append(slot_blueprint.blueprint_id)
                if slot_blueprint.readiness_state.startswith("blocked_by_"):
                    blocked_count += 1
                elif slot_blueprint.readiness_state == "needs_review":
                    needs_review_count += 1
                else:
                    skipped_count += 1
                continue
            draft = self._build_draft(slot_blueprint, blueprint_set)
            if draft is None:
                skipped_blueprint_ids.append(slot_blueprint.blueprint_id)
                blocked_count += 1
                continue
            drafts.append(draft)

        readiness_state = self._draft_set_readiness(
            total_slots=blueprint_set.total_slots,
            draft_count=len(drafts),
            blocked_count=blocked_count,
            needs_review_count=needs_review_count,
            skipped_count=skipped_count,
        )
        warnings = self._set_warnings(blueprint_set, drafts, blocked_count, needs_review_count)
        result = QuestionDraftSet(
            draft_set_id=f"question-draft-set:{source_question_generation_blueprint_set_id}",
            user_id=user_id,
            source_question_generation_blueprint_set_id=blueprint_set.blueprint_set_id,
            source_simulado_blueprint_id=blueprint_set.source_simulado_blueprint_id,
            status=readiness_state,
            readiness_state=readiness_state,
            total_blueprint_slots=blueprint_set.total_slots,
            draft_count=len(drafts),
            skipped_count=skipped_count,
            blocked_count=blocked_count,
            needs_review_count=needs_review_count,
            drafts=drafts,
            skipped_blueprint_ids=sorted(skipped_blueprint_ids),
            warnings=warnings,
            review_required=True,
            build_method=DRAFT_BUILD_METHOD,
            metadata={
                "source_question_generation_ready_slots": blueprint_set.ready_slots,
                "source_question_generation_blocked_slots": blueprint_set.blocked_slots,
                "source_question_generation_needs_review_slots": blueprint_set.needs_review_slots,
                "source_evidence_policy": "question_generation_blueprint_only",
                "llm_used": False,
                "external_calls_used": False,
            },
        )
        self.repository.save_question_draft_set(result, user_id=user_id)
        return result

    def get_draft_set(
        self,
        source_question_generation_blueprint_set_id: str,
        *,
        user_id: str | None,
    ) -> QuestionDraftSet | None:
        return self.repository.get_question_draft_set(
            source_question_generation_blueprint_set_id,
            user_id=user_id,
        )

    def get_draft_set_by_id(
        self,
        draft_set_id: str,
        *,
        user_id: str | None,
    ) -> QuestionDraftSet | None:
        return self.repository.get_question_draft_set_by_id(draft_set_id, user_id=user_id)

    def _build_draft(
        self,
        slot_blueprint: QuestionGenerationBlueprint,
        blueprint_set: QuestionGenerationBlueprintSet,
    ) -> QuestionDraft | None:
        source_references = [self._source_reference(item) for item in slot_blueprint.source_evidence]
        if not source_references:
            return None

        question_kind = slot_blueprint.question_kind
        format_type = slot_blueprint.format_type
        template_family = f"{question_kind}:{format_type}"
        draft_status = "draft_created"
        draft_readiness = "draft_for_review"
        warnings = list(self._warnings_from_blueprint(slot_blueprint))
        constraints = [self._constraint_from_blueprint(item) for item in slot_blueprint.constraints]
        if any(item.safe_snippet for item in source_references):
            source_snippet = next(item.safe_snippet for item in source_references if item.safe_snippet)
        else:
            source_snippet = None
            draft_status = "needs_review"
            draft_readiness = "needs_source_review"
            warnings.append(
                QuestionDraftWarning(
                    code="safe_snippet_missing",
                    message="Source evidence exists, but the draft still needs human review because no safe snippet was available.",
                    severity="warning",
                    related_artifact_type="question_generation_blueprint",
                    related_artifact_id=slot_blueprint.blueprint_id,
                )
            )

        if question_kind == "assertion_judgement":
            draft_fields = self._assertion_draft(slot_blueprint, source_snippet)
            warnings.append(
                QuestionDraftWarning(
                    code="answer_key_not_generated",
                    message="Answer key generation remains intentionally blocked in this pass.",
                    severity="info",
                    related_artifact_type="question_draft",
                    related_artifact_id=f"question-draft:{slot_blueprint.blueprint_id}",
                )
            )
        elif question_kind == "case_based_multiple_choice":
            draft_fields = self._case_based_multiple_choice_draft(slot_blueprint, source_snippet)
            warnings.append(
                QuestionDraftWarning(
                    code="alternatives_not_generated",
                    message="Only placeholder alternatives were created; final alternatives remain blocked.",
                    severity="info",
                    related_artifact_type="question_draft",
                    related_artifact_id=f"question-draft:{slot_blueprint.blueprint_id}",
                )
            )
        elif question_kind == "technical_maritime_scenario":
            draft_fields = self._technical_maritime_draft(slot_blueprint, source_snippet)
            warnings.append(
                QuestionDraftWarning(
                    code="alternatives_not_generated",
                    message="Only placeholder alternatives were created; final alternatives remain blocked.",
                    severity="info",
                    related_artifact_type="question_draft",
                    related_artifact_id=f"question-draft:{slot_blueprint.blueprint_id}",
                )
            )
            warnings.append(
                QuestionDraftWarning(
                    code="maritime_draft_requires_review",
                    message="Technical maritime drafts remain provisional and require human review.",
                    severity="warning",
                    related_artifact_type="question_draft",
                    related_artifact_id=f"question-draft:{slot_blueprint.blueprint_id}",
                )
            )
        elif question_kind == "direct_multiple_choice":
            draft_fields = self._direct_multiple_choice_draft(slot_blueprint, source_snippet)
            warnings.append(
                QuestionDraftWarning(
                    code="alternatives_not_generated",
                    message="Only placeholder alternatives were created; final alternatives remain blocked.",
                    severity="info",
                    related_artifact_type="question_draft",
                    related_artifact_id=f"question-draft:{slot_blueprint.blueprint_id}",
                )
            )
        else:
            return None

        validation_summary = QuestionDraftValidationSummary(
            source_grounded=bool(source_references),
            has_required_source_evidence=bool(source_references),
            format_supported=question_kind in {
                "assertion_judgement",
                "case_based_multiple_choice",
                "technical_maritime_scenario",
                "direct_multiple_choice",
            },
            profile_supported=slot_blueprint.board_id is not None or slot_blueprint.exam_family is not None,
            needs_human_review=True,
            final_answer_absent=True,
            final_alternatives_absent=True,
            final_explanation_absent=True,
            warnings_count=len(warnings),
            blockers_count=len(slot_blueprint.blockers),
            metadata={
                "source_blueprint_readiness": slot_blueprint.readiness_state,
                "style_hint_count": len(slot_blueprint.style_hints),
                "question_style_profile_id": slot_blueprint.metadata.get("question_style_profile_id"),
            },
        )
        provenance = QuestionDraftProvenance(
            build_method=DRAFT_BUILD_METHOD,
            source_blueprint_id=slot_blueprint.blueprint_id,
            source_evidence_count=len(source_references),
            source_constraints_count=len(constraints),
            template_family=question_kind,
            deterministic_template_id=f"draft-template:{template_family}",
            metadata={"format_type": format_type},
        )
        return QuestionDraft(
            draft_id=f"question-draft:{slot_blueprint.blueprint_id}",
            user_id=slot_blueprint.user_id,
            source_question_generation_blueprint_id=slot_blueprint.blueprint_id,
            source_question_generation_slot_id=slot_blueprint.blueprint_id,
            source_simulado_blueprint_id=blueprint_set.source_simulado_blueprint_id,
            source_question_slot_id=slot_blueprint.source_question_slot_id,
            draft_status=draft_status,
            draft_readiness=draft_readiness,
            format_type=format_type,
            question_kind=question_kind,
            board_id=slot_blueprint.board_id,
            exam_family=slot_blueprint.exam_family,
            target_subject_id=slot_blueprint.target_subject_id,
            target_topic_id=slot_blueprint.target_topic_id,
            target_subtopic_ids=list(slot_blueprint.target_subtopic_ids),
            draft_stem=draft_fields["draft_stem"],
            draft_command=draft_fields["draft_command"],
            draft_statement=draft_fields["draft_statement"],
            draft_scenario=draft_fields["draft_scenario"],
            draft_option_placeholders=draft_fields["draft_option_placeholders"],
            source_references=source_references,
            constraints=constraints,
            warnings=warnings,
            validation_summary=validation_summary,
            provenance=provenance,
            review_required=True,
            finalization_blocked=True,
            metadata={
                "no_final_question_generated": True,
                "no_answer_key_generated": True,
                "no_final_alternatives_generated": True,
                "no_distractors_generated": True,
                "no_final_explanations_generated": True,
                "style_hints": list(slot_blueprint.style_hints),
                "question_style_profile_id": slot_blueprint.metadata.get("question_style_profile_id"),
                "source_required": slot_blueprint.metadata.get("source_required"),
                "bibliography_anchor_required": slot_blueprint.metadata.get("bibliography_anchor_required"),
                "allowed_archetypes": list(slot_blueprint.metadata.get("allowed_archetypes", [])),
                "preferred_templates": list(slot_blueprint.metadata.get("preferred_templates", [])),
                "distractor_policy": dict(slot_blueprint.metadata.get("distractor_policy", {})),
                "scoring_behavior": dict(slot_blueprint.metadata.get("scoring_behavior", {})),
                "safety_rules": dict(slot_blueprint.metadata.get("safety_rules", {})),
                "human_review_required_for_answer_key": slot_blueprint.metadata.get(
                    "human_review_required_for_answer_key"
                ),
                "visible_source_titles": list(slot_blueprint.metadata.get("visible_source_titles", [])),
                "question_style_validation": dict(slot_blueprint.metadata.get("question_style_validation", {})),
            },
        )

    def _assertion_draft(self, slot_blueprint: QuestionGenerationBlueprint, snippet: str | None) -> dict[str, object]:
        topic_label = self._topic_label(slot_blueprint.target_topic_id)
        statement_source = snippet or f"referencia tecnica sobre {topic_label}"
        return {
            "draft_stem": self._limit(
                f"Com base nas fontes indicadas sobre {topic_label}, avalie o item em revisao humana posterior.",
                MAX_STEM_LENGTH,
            ),
            "draft_command": self._limit("Julgue o item a seguir.", MAX_COMMAND_LENGTH),
            "draft_statement": self._limit(
                f"Rascunho provisiorio de afirmacao sobre {topic_label}: {statement_source}",
                MAX_STATEMENT_LENGTH,
            ),
            "draft_scenario": None,
            "draft_option_placeholders": [],
        }

    def _case_based_multiple_choice_draft(self, slot_blueprint: QuestionGenerationBlueprint, snippet: str | None) -> dict[str, object]:
        topic_label = self._topic_label(slot_blueprint.target_topic_id)
        scenario = snippet or f"contexto provisiorio sobre {topic_label}"
        return {
            "draft_stem": self._limit(
                f"Rascunho provisiorio de item objetivo sobre {topic_label}, ainda sujeito a revisao humana.",
                MAX_STEM_LENGTH,
            ),
            "draft_command": self._limit(
                "Assinale, em etapa posterior de revisao, a alternativa mais adequada.",
                MAX_COMMAND_LENGTH,
            ),
            "draft_statement": None,
            "draft_scenario": self._limit(
                f"Cenario provisiorio derivado da evidencia principal sobre {topic_label}: {scenario}",
                MAX_SCENARIO_LENGTH,
            ),
            "draft_option_placeholders": self._option_placeholders(slot_blueprint.format_type),
        }

    def _technical_maritime_draft(self, slot_blueprint: QuestionGenerationBlueprint, snippet: str | None) -> dict[str, object]:
        topic_label = self._topic_label(slot_blueprint.target_topic_id)
        scenario = snippet or f"contexto tecnico-maritimo provisiorio sobre {topic_label}"
        return {
            "draft_stem": self._limit(
                f"Rascunho provisiorio de item tecnico-maritimo sobre {topic_label}, sujeito a revisao especializada.",
                MAX_STEM_LENGTH,
            ),
            "draft_command": self._limit(
                "Considere o contexto tecnico a seguir e assinale, em revisao posterior, a alternativa mais adequada.",
                MAX_COMMAND_LENGTH,
            ),
            "draft_statement": None,
            "draft_scenario": self._limit(
                f"Cenario tecnico-maritimo provisiorio derivado da evidencia principal: {scenario}",
                MAX_SCENARIO_LENGTH,
            ),
            "draft_option_placeholders": self._option_placeholders(slot_blueprint.format_type),
        }

    def _direct_multiple_choice_draft(self, slot_blueprint: QuestionGenerationBlueprint, snippet: str | None) -> dict[str, object]:
        topic_label = self._topic_label(slot_blueprint.target_topic_id)
        scenario = snippet or f"referencia provisioria sobre {topic_label}"
        return {
            "draft_stem": self._limit(
                f"Rascunho provisiorio de item objetivo sobre {topic_label}, com revisao humana obrigatoria.",
                MAX_STEM_LENGTH,
            ),
            "draft_command": self._limit(
                "Assinale, em etapa posterior de revisao, a alternativa mais adequada.",
                MAX_COMMAND_LENGTH,
            ),
            "draft_statement": None,
            "draft_scenario": self._limit(
                f"Base provisioria para elaboracao futura: {scenario}",
                MAX_SCENARIO_LENGTH,
            ),
            "draft_option_placeholders": self._option_placeholders(slot_blueprint.format_type),
        }

    def _option_placeholders(self, format_type: str) -> list[str]:
        count = 4
        if format_type == "multiple_choice_5":
            count = 5
        elif format_type == "multiple_choice_4":
            count = 4
        labels = "ABCDE"[:count]
        return [
            self._limit(
                f"Placeholder {label}: alternativa futura baseada na evidencia principal.",
                MAX_OPTION_PLACEHOLDER_LENGTH,
            )
            for label in labels
        ]

    def _warnings_from_blueprint(
        self,
        slot_blueprint: QuestionGenerationBlueprint,
    ) -> list[QuestionDraftWarning]:
        warnings = [
            QuestionDraftWarning(
                code=item.code,
                message=item.message,
                severity=item.severity,
                related_artifact_type=item.related_artifact_type,
                related_artifact_id=item.related_artifact_id,
                metadata=dict(item.metadata),
            )
            for item in slot_blueprint.warnings
        ]
        warnings.append(
            QuestionDraftWarning(
                code="draft_review_required",
                message="This draft is provisional and requires human review before any downstream use.",
                severity="info",
                related_artifact_type="question_generation_blueprint",
                related_artifact_id=slot_blueprint.blueprint_id,
            )
        )
        return warnings

    def _constraint_from_blueprint(self, constraint) -> QuestionDraftConstraint:
        return QuestionDraftConstraint(
            constraint_id=constraint.constraint_id,
            constraint_type=constraint.constraint_type,
            severity=constraint.severity,
            description=constraint.description,
            source="question_generation_blueprint",
            metadata=dict(constraint.metadata),
        )

    def _source_reference(self, evidence) -> QuestionDraftSourceReference:
        return QuestionDraftSourceReference(
            evidence_id=evidence.evidence_id,
            document_id=evidence.document_id,
            material_id=evidence.material_id,
            section_id=evidence.section_id,
            chunk_id=evidence.chunk_id,
            topic_id=evidence.topic_id,
            subtopic_id=evidence.subtopic_id,
            evidence_role=evidence.evidence_role,
            evidence_strength=evidence.evidence_strength,
            source_title=evidence.source_title,
            safe_snippet=self._limit(self._sanitize_text(evidence.safe_snippet), MAX_SAFE_SNIPPET_LENGTH)
            if evidence.safe_snippet
            else None,
            metadata=dict(evidence.metadata),
        )

    def _draft_set_readiness(
        self,
        *,
        total_slots: int,
        draft_count: int,
        blocked_count: int,
        needs_review_count: int,
        skipped_count: int,
    ) -> str:
        if total_slots == 0 or draft_count == 0:
            if blocked_count > 0 and needs_review_count == 0 and skipped_count == 0:
                return "blocked"
            if needs_review_count > 0 and blocked_count == 0 and skipped_count == 0:
                return "needs_review"
            return "no_ready_blueprints"
        if blocked_count or needs_review_count or skipped_count:
            return "partially_created"
        return "drafts_created"

    def _set_warnings(
        self,
        blueprint_set: QuestionGenerationBlueprintSet,
        drafts: list[QuestionDraft],
        blocked_count: int,
        needs_review_count: int,
    ) -> list[QuestionDraftWarning]:
        warnings: list[QuestionDraftWarning] = [
            QuestionDraftWarning(
                code="drafts_are_provisional",
                message="Question drafts remain provisional, review-required and blocked from finalization in this pass.",
                severity="info",
                related_artifact_type="question_generation_blueprint_set",
                related_artifact_id=blueprint_set.blueprint_set_id,
            )
        ]
        if blocked_count:
            warnings.append(
                QuestionDraftWarning(
                    code="blocked_blueprints_skipped",
                    message="One or more source blueprints remained blocked and were not drafted.",
                    severity="warning",
                    related_artifact_type="question_generation_blueprint_set",
                    related_artifact_id=blueprint_set.blueprint_set_id,
                )
            )
        if needs_review_count:
            warnings.append(
                QuestionDraftWarning(
                    code="review_blueprints_skipped",
                    message="One or more source blueprints still need review and were not drafted.",
                    severity="info",
                    related_artifact_type="question_generation_blueprint_set",
                    related_artifact_id=blueprint_set.blueprint_set_id,
                )
            )
        for draft in drafts:
            warnings.extend(draft.warnings)
        deduped: dict[tuple[str, str | None], QuestionDraftWarning] = {}
        for item in warnings:
            deduped.setdefault((item.code, item.related_artifact_id), item)
        return [deduped[key] for key in sorted(deduped)]

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
