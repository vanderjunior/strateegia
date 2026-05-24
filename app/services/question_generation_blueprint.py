from __future__ import annotations

import re

from app.domain.models import (
    CurriculumCoverageLink,
    CurriculumGapReference,
    CurriculumGraph,
    CurriculumSourceEvidence,
    CurriculumSubtopicNode,
    CurriculumTopicNode,
    DocumentChunk,
    DocumentExtractionResult,
    DocumentSection,
    ExamProfile,
    QuestionGenerationBlueprint,
    QuestionGenerationBlueprintSet,
    QuestionGenerationConstraint,
    QuestionGenerationWarning,
    QuestionSourceEvidence,
    SimuladoBlueprint,
    SimuladoQuestionSlot,
    UploadedMaterial,
    utc_now,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.exam_profiles import ExamProfileService
from app.services.question_style_profiles import enrich_question_generation_blueprint_with_style_profile


BLUEPRINT_SET_VERSION = "question-generation-blueprint-v1"
SAFE_SNIPPET_LIMIT = 240
MATERIAL_GAP_TYPES = {
    "missing_document_text",
    "missing_bibliography_material",
    "missing_material",
}


class QuestionGenerationBlueprintService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository
        self.exam_profiles = ExamProfileService(repository)

    def build_blueprint_set(
        self,
        source_simulado_blueprint_id: str,
        *,
        user_id: str | None,
    ) -> QuestionGenerationBlueprintSet | None:
        if user_id is None:
            return None
        existing = self.repository.get_question_generation_blueprint(
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

        graph = self.repository.get_curriculum_graph_by_id(simulado.graph_id, user_id=user_id)
        profile = (
            self.exam_profiles.get_exam_profile(simulado.exam_profile_id)
            if simulado.exam_profile_id
            else None
        )
        indexes = self._source_indexes(user_id=user_id)
        slot_blueprints = [
            self._slot_blueprint(
                simulado=simulado,
                slot=slot,
                graph=graph,
                profile=profile,
                indexes=indexes,
            )
            for slot in sorted(simulado.question_slots, key=lambda item: (item.order_index, item.slot_id))
        ]
        warnings = self._set_warnings(simulado=simulado, slot_blueprints=slot_blueprints)
        ready_slots = sum(1 for item in slot_blueprints if item.readiness_state == "ready_for_draft")
        blocked_slots = sum(1 for item in slot_blueprints if item.readiness_state.startswith("blocked_by_"))
        needs_review_slots = sum(1 for item in slot_blueprints if item.readiness_state == "needs_review")
        readiness_state = self._set_readiness_state(
            total_slots=len(slot_blueprints),
            ready_slots=ready_slots,
            blocked_slots=blocked_slots,
            needs_review_slots=needs_review_slots,
        )
        created_at = utc_now()
        result = QuestionGenerationBlueprintSet(
            blueprint_set_id=f"question-generation:{simulado.blueprint_id}",
            user_id=user_id,
            source_simulado_blueprint_id=simulado.blueprint_id,
            status=readiness_state,
            readiness_state=readiness_state,
            total_slots=len(slot_blueprints),
            ready_slots=ready_slots,
            blocked_slots=blocked_slots,
            needs_review_slots=needs_review_slots,
            slot_blueprints=slot_blueprints,
            constraints=self._global_constraints(simulado=simulado, profile=profile),
            warnings=warnings,
            build_method="heuristic_question_generation_blueprint_builder",
            created_at=created_at,
            metadata={
                "source_graph_id": simulado.graph_id,
                "source_cycle_id": simulado.cycle_id,
                "source_exam_profile_id": simulado.exam_profile_id,
                "source_blueprint_version": simulado.blueprint_version,
                "slot_ids": [item.source_question_slot_id for item in slot_blueprints],
                "source_evidence_policy": "existing_persisted_artifacts_only",
                "llm_used": False,
                "external_calls_used": False,
                "question_generation_blueprint_version": BLUEPRINT_SET_VERSION,
            },
        )
        self.repository.save_question_generation_blueprint(result, user_id=user_id)
        return result

    def get_blueprint_set(
        self,
        source_simulado_blueprint_id: str,
        *,
        user_id: str | None,
    ) -> QuestionGenerationBlueprintSet | None:
        return self.repository.get_question_generation_blueprint(
            source_simulado_blueprint_id,
            user_id=user_id,
        )

    def get_blueprint_set_by_id(
        self,
        blueprint_set_id: str,
        *,
        user_id: str | None,
    ) -> QuestionGenerationBlueprintSet | None:
        return self.repository.get_question_generation_blueprint_by_id(
            blueprint_set_id,
            user_id=user_id,
        )

    def _slot_blueprint(
        self,
        *,
        simulado: SimuladoBlueprint,
        slot: SimuladoQuestionSlot,
        graph: CurriculumGraph | None,
        profile: ExamProfile | None,
        indexes: dict[str, dict[str, object]],
    ) -> QuestionGenerationBlueprint:
        topic = self._topic_for_slot(graph, slot)
        subtopics = self._subtopics_for_slot(graph, slot)
        coverage_links = self._coverage_links_for_slot(graph, slot)
        gap_references = self._gaps_for_slot(graph, slot)
        question_kind, style_hints, format_supported = self._style_hints_for_slot(
            simulado=simulado,
            slot=slot,
            profile=profile,
        )
        source_evidence, evidence_warnings = self._source_evidence(
            slot=slot,
            topic=topic,
            coverage_links=coverage_links,
            indexes=indexes,
        )
        warnings: list[QuestionGenerationWarning] = list(evidence_warnings)
        blockers: list[str] = []
        gap_types = {item.gap_type for item in gap_references}
        coverage_state = topic.coverage_state if topic is not None else slot.required_coverage_state
        profile_warnings = self._profile_warnings(simulado=simulado, profile=profile, slot=slot)
        warnings.extend(profile_warnings)

        readiness_state = "needs_review"
        if profile is None:
            readiness_state = "blocked_by_ambiguous_profile"
            blockers.append("must_not_generate_if_profile_ambiguous")
            warnings.append(
                QuestionGenerationWarning(
                    code="ambiguous_profile",
                    message="Exam profile is unavailable or unresolved for this slot.",
                    severity="warning",
                    related_artifact_type="simulado_blueprint",
                    related_artifact_id=simulado.blueprint_id,
                )
            )
        elif slot.readiness_state == "blocked_by_ocr" or "ocr_required" in gap_types:
            readiness_state = "blocked_by_ocr"
            blockers.append("must_not_generate_if_ocr_required")
            warnings.append(
                QuestionGenerationWarning(
                    code="ocr_required",
                    message="Source material still requires OCR before a safe future draft can be attempted.",
                    severity="warning",
                    related_artifact_type="topic",
                    related_artifact_id=slot.target_topic_id,
                )
            )
        elif (
            slot.readiness_state == "blocked_by_material_gap"
            or gap_types & MATERIAL_GAP_TYPES
        ):
            readiness_state = "blocked_by_material_gap"
            blockers.append("must_not_generate_if_material_missing")
            code = "missing_document_text" if "missing_document_text" in gap_types else "material_gap"
            warnings.append(
                QuestionGenerationWarning(
                    code=code,
                    message="Document text or required material coverage is missing for this slot.",
                    severity="warning",
                    related_artifact_type="topic",
                    related_artifact_id=slot.target_topic_id,
                )
            )
        elif not format_supported:
            readiness_state = "blocked_by_unsupported_format"
            blockers.append("must_match_format")
            warnings.append(
                QuestionGenerationWarning(
                    code="unsupported_question_format",
                    message="Question format is unsupported for safe future drafting in this foundation pass.",
                    severity="warning",
                    related_artifact_type="question_slot",
                    related_artifact_id=slot.slot_id,
                )
            )
        elif slot.readiness_state == "blocked_by_ambiguity" or topic is None:
            readiness_state = "needs_review" if topic is not None else "blocked_by_missing_source"
            code = "ambiguous_coverage" if topic is not None else "source_evidence_missing"
            message = (
                "Coverage remains ambiguous and should be reviewed before drafting."
                if topic is not None
                else "No stable target topic/source mapping was found for this slot."
            )
            warnings.append(
                QuestionGenerationWarning(
                    code=code,
                    message=message,
                    severity="warning",
                    related_artifact_type="topic",
                    related_artifact_id=slot.target_topic_id,
                )
            )
        elif coverage_state == "uncovered" or slot.readiness_state == "insufficient_source_evidence":
            readiness_state = "blocked_by_insufficient_coverage"
            blockers.append("must_avoid_uncovered_topic")
            warnings.append(
                QuestionGenerationWarning(
                    code="topic_uncovered",
                    message="Coverage remains insufficient for a safe future draft.",
                    severity="warning",
                    related_artifact_type="topic",
                    related_artifact_id=slot.target_topic_id,
                )
            )
        elif not source_evidence:
            readiness_state = "blocked_by_missing_source"
            blockers.append("must_use_source_evidence")
            warnings.append(
                QuestionGenerationWarning(
                    code="source_evidence_missing",
                    message="At least one bounded source evidence item is required for future draft planning.",
                    severity="warning",
                    related_artifact_type="question_slot",
                    related_artifact_id=slot.slot_id,
                )
            )
        elif coverage_state in {"partially_covered", "weakly_covered"} or (
            topic is not None and topic.review_state in {"candidate", "needs_review", "ambiguous"}
        ):
            readiness_state = "needs_review"
            warnings.append(
                QuestionGenerationWarning(
                    code="topic_partially_covered",
                    message="Coverage exists but remains partial or review-sensitive for this slot.",
                    severity="info",
                    related_artifact_type="topic",
                    related_artifact_id=slot.target_topic_id,
                )
            )
        elif any(item.code in {"profile_needs_confirmation", "format_inferred_not_confirmed"} for item in warnings):
            readiness_state = "needs_review"
        else:
            readiness_state = "ready_for_draft"

        constraints = self._slot_constraints(
            slot=slot,
            question_kind=question_kind,
            style_hints=style_hints,
            readiness_state=readiness_state,
            blockers=blockers,
            profile=profile,
        )
        metadata = {
            "source_graph_id": simulado.graph_id,
            "source_cycle_id": simulado.cycle_id,
            "source_exam_profile_id": simulado.exam_profile_id,
            "source_slot_readiness": slot.readiness_state,
            "source_gap_ids": list(slot.blocked_by_gap_ids),
            "source_evidence_ids": list(slot.source_evidence_ids),
            "coverage_state": coverage_state,
            "style_hint_count": len(style_hints),
            "subtopic_count": len(subtopics),
            "no_question_text_generated": True,
            "no_alternatives_generated": True,
            "no_distractors_generated": True,
            "no_answer_key_generated": True,
            "no_explanations_generated": True,
        }
        metadata = enrich_question_generation_blueprint_with_style_profile(
            exam_profile_id=simulado.exam_profile_id,
            blueprint_metadata=metadata,
            source_titles=[item.source_title for item in source_evidence if item.source_title],
            source_present=bool(source_evidence),
            requested_archetype="technical_operational_scenario"
            if question_kind == "technical_maritime_scenario"
            else None,
            delivery_context="simulado",
        )
        return QuestionGenerationBlueprint(
            blueprint_id=f"question-generation-slot:{slot.slot_id}",
            user_id=simulado.user_id,
            source_simulado_blueprint_id=simulado.blueprint_id,
            source_question_slot_id=slot.slot_id,
            readiness_state=readiness_state,
            format_type=slot.format_type or simulado.format_type,
            board_id=profile.board_profile.board_id if profile else None,
            exam_family=profile.exam_family if profile else simulado.exam_family,
            target_subject_id=slot.target_subject_id,
            target_topic_id=slot.target_topic_id,
            target_subtopic_ids=[item.subtopic_id for item in subtopics] or list(slot.target_subtopic_ids),
            difficulty_hint=slot.difficulty_hint,
            cognitive_demand=slot.cognitive_demand,
            question_kind=question_kind,
            style_hints=style_hints,
            source_evidence=source_evidence,
            constraints=constraints,
            blockers=blockers,
            warnings=self._dedupe_warnings(warnings),
            metadata=metadata,
        )

    def _source_indexes(self, *, user_id: str) -> dict[str, dict[str, object]]:
        materials_by_doc: dict[str, UploadedMaterial] = {}
        chunks_by_id: dict[str, DocumentChunk] = {}
        sections_by_id: dict[str, DocumentSection] = {}
        extractions_by_doc: dict[str, DocumentExtractionResult] = {}
        for material in self.repository.list_uploaded_materials(user_id=user_id):
            document_id = material.metadata.document_id
            materials_by_doc[document_id] = material
            extraction = self.repository.get_document_extraction_result(document_id, user_id=user_id)
            if extraction is not None:
                extractions_by_doc[document_id] = extraction
            for chunk in self.repository.list_document_chunks(document_id, user_id=user_id):
                chunks_by_id[chunk.chunk_id] = chunk
            for section in self.repository.list_document_sections(document_id, user_id=user_id):
                sections_by_id[section.section_id] = section
        return {
            "materials": materials_by_doc,
            "chunks": chunks_by_id,
            "sections": sections_by_id,
            "extractions": extractions_by_doc,
        }

    def _topic_for_slot(
        self,
        graph: CurriculumGraph | None,
        slot: SimuladoQuestionSlot,
    ) -> CurriculumTopicNode | None:
        if graph is None:
            return None
        for topic in graph.topics:
            if topic.topic_id == slot.target_topic_id:
                return topic
        return None

    def _subtopics_for_slot(
        self,
        graph: CurriculumGraph | None,
        slot: SimuladoQuestionSlot,
    ) -> list[CurriculumSubtopicNode]:
        if graph is None:
            return []
        wanted = set(slot.target_subtopic_ids)
        return [item for item in graph.subtopics if item.subtopic_id in wanted]

    def _coverage_links_for_slot(
        self,
        graph: CurriculumGraph | None,
        slot: SimuladoQuestionSlot,
    ) -> list[CurriculumCoverageLink]:
        if graph is None:
            return []
        wanted = {slot.target_topic_id, *slot.target_subtopic_ids}
        links = [
            item
            for item in graph.coverage_links
            if item.target_id in wanted
        ]
        links.sort(key=lambda item: item.link_id)
        return links

    def _gaps_for_slot(
        self,
        graph: CurriculumGraph | None,
        slot: SimuladoQuestionSlot,
    ) -> list[CurriculumGapReference]:
        if graph is None:
            return []
        wanted_gap_ids = set(slot.blocked_by_gap_ids)
        items = []
        for gap in graph.gaps:
            if gap.gap_id in wanted_gap_ids or gap.target_id == slot.target_topic_id:
                items.append(gap)
        items.sort(key=lambda item: item.gap_id)
        return items

    def _source_evidence(
        self,
        *,
        slot: SimuladoQuestionSlot,
        topic: CurriculumTopicNode | None,
        coverage_links: list[CurriculumCoverageLink],
        indexes: dict[str, dict[str, object]],
    ) -> tuple[list[QuestionSourceEvidence], list[QuestionGenerationWarning]]:
        warnings: list[QuestionGenerationWarning] = []
        evidence: list[QuestionSourceEvidence] = []
        seen_ids: set[str] = set()
        chunks_by_id = indexes["chunks"]
        sections_by_id = indexes["sections"]
        materials_by_doc = indexes["materials"]

        for link in coverage_links:
            for chunk_id in link.chunk_ids:
                chunk = chunks_by_id.get(chunk_id)
                if chunk is None:
                    continue
                material = materials_by_doc.get(chunk.document_id)
                safe_snippet, snippet_warning = self._safe_snippet(chunk.text)
                if snippet_warning:
                    warnings.append(snippet_warning)
                evidence_id = f"question-evidence:{chunk.chunk_id}"
                if evidence_id in seen_ids:
                    continue
                evidence.append(
                    QuestionSourceEvidence(
                        evidence_id=evidence_id,
                        document_id=chunk.document_id,
                        material_id=chunk.document_id,
                        section_id=chunk.section_id,
                        chunk_id=chunk.chunk_id,
                        topic_id=slot.target_topic_id,
                        subtopic_id=slot.target_subtopic_ids[0] if slot.target_subtopic_ids else None,
                        evidence_role="primary_chunk",
                        evidence_strength=self._strength(link.confidence),
                        coverage_state=link.coverage_state,
                        source_title=(material.metadata.original_filename if material else None),
                        source_type="document_chunk",
                        safe_snippet=safe_snippet,
                        metadata={"chunk_index": chunk.chunk_index},
                    )
                )
                seen_ids.add(evidence_id)
            for section_id in link.section_ids:
                section = sections_by_id.get(section_id)
                if section is None:
                    continue
                material = materials_by_doc.get(section.document_id)
                safe_snippet, snippet_warning = self._safe_snippet(section.title)
                if snippet_warning:
                    warnings.append(snippet_warning)
                evidence_id = f"question-evidence:{section.section_id}"
                if evidence_id in seen_ids:
                    continue
                evidence.append(
                    QuestionSourceEvidence(
                        evidence_id=evidence_id,
                        document_id=section.document_id,
                        material_id=section.document_id,
                        section_id=section.section_id,
                        topic_id=slot.target_topic_id,
                        subtopic_id=slot.target_subtopic_ids[0] if slot.target_subtopic_ids else None,
                        evidence_role="section_context",
                        evidence_strength=self._strength(link.confidence),
                        coverage_state=link.coverage_state,
                        source_title=(material.metadata.original_filename if material else None),
                        source_type="document_section",
                        safe_snippet=safe_snippet,
                        metadata={"section_level": section.level},
                    )
                )
                seen_ids.add(evidence_id)
            for item in link.evidence:
                self._append_curriculum_evidence(
                    evidence=evidence,
                    warnings=warnings,
                    seen_ids=seen_ids,
                    source=item,
                    slot=slot,
                    coverage_state=link.coverage_state,
                    source_type="coverage_evidence",
                    materials_by_doc=materials_by_doc,
                )

        if topic is not None:
            for item in topic.evidence:
                self._append_curriculum_evidence(
                    evidence=evidence,
                    warnings=warnings,
                    seen_ids=seen_ids,
                    source=item,
                    slot=slot,
                    coverage_state=topic.coverage_state,
                    source_type="topic_evidence",
                    materials_by_doc=materials_by_doc,
                )

        evidence.sort(key=lambda item: item.evidence_id)
        if evidence and all(item.evidence_strength == "weak" for item in evidence):
            warnings.append(
                QuestionGenerationWarning(
                    code="source_evidence_weak",
                    message="Only weak source evidence was available for this slot.",
                    severity="info",
                    related_artifact_type="question_slot",
                    related_artifact_id=slot.slot_id,
                )
            )
        return evidence, warnings

    def _append_curriculum_evidence(
        self,
        *,
        evidence: list[QuestionSourceEvidence],
        warnings: list[QuestionGenerationWarning],
        seen_ids: set[str],
        source: CurriculumSourceEvidence,
        slot: SimuladoQuestionSlot,
        coverage_state: str,
        source_type: str,
        materials_by_doc: dict[str, UploadedMaterial],
    ) -> None:
        evidence_id = f"question-evidence:{source.evidence_id}"
        if evidence_id in seen_ids:
            return
        safe_snippet, snippet_warning = self._safe_snippet(source.excerpt)
        if snippet_warning:
            warnings.append(snippet_warning)
        material = materials_by_doc.get(source.document_id or "")
        evidence.append(
            QuestionSourceEvidence(
                evidence_id=evidence_id,
                document_id=source.document_id,
                material_id=source.document_id,
                section_id=source.section_id,
                chunk_id=source.chunk_id,
                topic_id=slot.target_topic_id,
                subtopic_id=slot.target_subtopic_ids[0] if slot.target_subtopic_ids else None,
                evidence_role=source_type,
                evidence_strength=self._strength(source.confidence),
                coverage_state=coverage_state,
                source_title=(material.metadata.original_filename if material else None),
                source_type=source.source_type or source_type,
                safe_snippet=safe_snippet,
                metadata={"matched_terms": list(source.matched_terms)},
            )
        )
        seen_ids.add(evidence_id)

    def _style_hints_for_slot(
        self,
        *,
        simulado: SimuladoBlueprint,
        slot: SimuladoQuestionSlot,
        profile: ExamProfile | None,
    ) -> tuple[str, list[str], bool]:
        format_type = slot.format_type or simulado.format_type
        board_id = profile.board_profile.board_id if profile else ""
        exam_family = profile.exam_family if profile else simulado.exam_family

        if format_type == "true_false" or board_id == "board:cebraspe":
            if format_type != "true_false":
                return "review_prompt_placeholder", ["profile_confirmation_required"], False
            return (
                "assertion_judgement",
                [
                    "single_assertion",
                    "technical_precision",
                    "avoid_obvious_falsehood",
                    "source_grounded_assertion_required",
                ],
                True,
            )
        if exam_family == "PSCPP" or board_id == "board:marinha-dpc":
            if format_type not in {"multiple_choice", "multiple_choice_4", "multiple_choice_5", "technical_maritime_block", "mixed"}:
                return "review_prompt_placeholder", ["profile_confirmation_required"], False
            return (
                "technical_maritime_scenario",
                [
                    "technical_operational_context",
                    "source_topic_mapping_required",
                    "allow_english_maritime_terms",
                    "avoid_generic_military_question",
                    "prioritize_bibliography_evidence",
                ],
                True,
            )
        if board_id == "board:fgv":
            if format_type not in {"multiple_choice", "multiple_choice_4", "multiple_choice_5", "mixed"}:
                return "review_prompt_placeholder", ["profile_confirmation_required"], False
            return (
                "case_based_multiple_choice",
                [
                    "medium_to_long_stem_future",
                    "plausible_distractors_future",
                    "single_best_answer",
                    "contextualized_command",
                ],
                True,
            )
        if format_type in {"multiple_choice", "multiple_choice_4", "multiple_choice_5"}:
            return (
                "direct_multiple_choice",
                ["single_best_answer", "source_grounded_fact_pattern"],
                True,
            )
        return ("review_prompt_placeholder", ["profile_confirmation_required"], False)

    def _profile_warnings(
        self,
        *,
        simulado: SimuladoBlueprint,
        profile: ExamProfile | None,
        slot: SimuladoQuestionSlot,
    ) -> list[QuestionGenerationWarning]:
        warnings: list[QuestionGenerationWarning] = []
        simulado_codes = {item.code for item in simulado.warnings}
        profile_codes = {item.code for item in profile.warnings} if profile else set()
        if "format_requires_confirmation" in simulado_codes or "format_requires_confirmation" in profile_codes:
            warnings.append(
                QuestionGenerationWarning(
                    code="format_inferred_not_confirmed",
                    message="Question format still depends on explicit confirmation from existing profile/simulado evidence.",
                    severity="info",
                    related_artifact_type="question_slot",
                    related_artifact_id=slot.slot_id,
                )
            )
        if "scoring_requires_confirmation" in simulado_codes:
            warnings.append(
                QuestionGenerationWarning(
                    code="scoring_unconfirmed",
                    message="Scoring remains informational only and should not drive future drafting assumptions.",
                    severity="info",
                    related_artifact_type="simulado_blueprint",
                    related_artifact_id=simulado.blueprint_id,
                )
            )
        if any(item.code in {"ambiguous_exam_profile_signals", "conflicting_board_and_format"} for item in (profile.warnings if profile else [])):
            warnings.append(
                QuestionGenerationWarning(
                    code="profile_needs_confirmation",
                    message="Exam profile signals remain ambiguous and should be reviewed before drafting.",
                    severity="warning",
                    related_artifact_type="question_slot",
                    related_artifact_id=slot.slot_id,
                )
            )
        return warnings

    def _slot_constraints(
        self,
        *,
        slot: SimuladoQuestionSlot,
        question_kind: str,
        style_hints: list[str],
        readiness_state: str,
        blockers: list[str],
        profile: ExamProfile | None,
    ) -> list[QuestionGenerationConstraint]:
        constraints = [
            QuestionGenerationConstraint(
                constraint_id=f"{slot.slot_id}:must_use_source_evidence",
                constraint_type="must_use_source_evidence",
                severity="error",
                description="A future draft must stay grounded in persisted source evidence.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{slot.slot_id}:must_match_exam_profile",
                constraint_type="must_match_exam_profile",
                severity="error",
                description="A future draft must preserve the resolved exam profile hints.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{slot.slot_id}:must_match_format",
                constraint_type="must_match_format",
                severity="error",
                description="A future draft must preserve the slot format and question kind expectations.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{slot.slot_id}:must_match_topic",
                constraint_type="must_match_topic",
                severity="error",
                description="A future draft must remain mapped to the declared topic/subtopic target.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{slot.slot_id}:must_keep_snippets_bounded",
                constraint_type="must_keep_snippets_bounded",
                severity="info",
                description="Only bounded safe snippets may be surfaced in planning artifacts.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{slot.slot_id}:no_final_question_text_in_this_pass",
                constraint_type="no_final_question_text_in_this_pass",
                severity="error",
                description="This pass must not generate final question text.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{slot.slot_id}:no_alternatives_in_this_pass",
                constraint_type="no_alternatives_in_this_pass",
                severity="error",
                description="This pass must not generate alternatives/options.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{slot.slot_id}:no_answer_key_in_this_pass",
                constraint_type="no_answer_key_in_this_pass",
                severity="error",
                description="This pass must not generate answer keys or gabarito.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{slot.slot_id}:no_distractors_in_this_pass",
                constraint_type="no_distractors_in_this_pass",
                severity="error",
                description="This pass must not generate distractors.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{slot.slot_id}:no_explanations_in_this_pass",
                constraint_type="no_explanations_in_this_pass",
                severity="error",
                description="This pass must not generate explanations or correction logic.",
            ),
        ]
        if readiness_state == "blocked_by_insufficient_coverage":
            constraints.append(
                QuestionGenerationConstraint(
                    constraint_id=f"{slot.slot_id}:must_avoid_uncovered_topic",
                    constraint_type="must_avoid_uncovered_topic",
                    severity="error",
                    description="Future drafting must stay blocked while topic coverage remains insufficient.",
                )
            )
        for blocker in blockers:
            constraints.append(
                QuestionGenerationConstraint(
                    constraint_id=f"{slot.slot_id}:{blocker}",
                    constraint_type=blocker,
                    severity="error",
                    description=f"Slot blocker {blocker} must be resolved before any future draft step.",
                )
            )
        if question_kind == "technical_maritime_scenario" or (
            profile and profile.exam_family == "PSCPP"
        ):
            constraints.extend(
                [
                    QuestionGenerationConstraint(
                        constraint_id=f"{slot.slot_id}:must_preserve_technical_maritime_context",
                        constraint_type="must_preserve_technical_maritime_context",
                        severity="error",
                        description="Future drafts for PSCPP/Praticagem must preserve technical maritime context.",
                    ),
                    QuestionGenerationConstraint(
                        constraint_id=f"{slot.slot_id}:must_keep_pscpp_source_anchor_visible",
                        constraint_type="must_keep_pscpp_source_anchor_visible",
                        severity="error",
                        description="PSCPP planning metadata must preserve a visible bibliography/source anchor.",
                    ),
                    QuestionGenerationConstraint(
                        constraint_id=f"{slot.slot_id}:must_require_human_review_for_answer_key",
                        constraint_type="must_require_human_review_for_answer_key",
                        severity="error",
                        description="PSCPP planning metadata must keep answer-key validation blocked behind human review.",
                    ),
                    QuestionGenerationConstraint(
                        constraint_id=f"{slot.slot_id}:must_keep_current_edital_alignment",
                        constraint_type="must_keep_current_edital_alignment",
                        severity="error",
                        description="PSCPP style hints must stay subordinate to current edital alignment.",
                    ),
                ]
            )
        if style_hints:
            constraints.append(
                QuestionGenerationConstraint(
                    constraint_id=f"{slot.slot_id}:must_preserve_board_style",
                    constraint_type="must_preserve_board_style",
                    severity="info",
                    description="Future drafting should preserve board/style hints already resolved in this plan.",
                    metadata={"style_hints": list(style_hints)},
                )
            )
        constraints.sort(key=lambda item: item.constraint_id)
        return constraints

    def _global_constraints(
        self,
        *,
        simulado: SimuladoBlueprint,
        profile: ExamProfile | None,
    ) -> list[QuestionGenerationConstraint]:
        constraints = [
            QuestionGenerationConstraint(
                constraint_id=f"{simulado.blueprint_id}:must_use_source_evidence",
                constraint_type="must_use_source_evidence",
                severity="error",
                description="Question generation planning remains source-grounded only.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{simulado.blueprint_id}:must_respect_edital_scope",
                constraint_type="must_respect_edital_scope",
                severity="error",
                description="Future drafts must remain inside the existing edital/curriculum scope.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{simulado.blueprint_id}:no_final_question_text_in_this_pass",
                constraint_type="no_final_question_text_in_this_pass",
                severity="error",
                description="This pass stores planning artifacts only and never final question text.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{simulado.blueprint_id}:no_alternatives_in_this_pass",
                constraint_type="no_alternatives_in_this_pass",
                severity="error",
                description="This pass does not generate alternatives or options.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{simulado.blueprint_id}:no_answer_key_in_this_pass",
                constraint_type="no_answer_key_in_this_pass",
                severity="error",
                description="This pass does not generate answer keys or gabarito.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{simulado.blueprint_id}:no_distractors_in_this_pass",
                constraint_type="no_distractors_in_this_pass",
                severity="error",
                description="This pass does not generate distractors.",
            ),
            QuestionGenerationConstraint(
                constraint_id=f"{simulado.blueprint_id}:no_explanations_in_this_pass",
                constraint_type="no_explanations_in_this_pass",
                severity="error",
                description="This pass does not generate explanations or corrections.",
            ),
        ]
        if profile is not None:
            constraints.append(
                QuestionGenerationConstraint(
                    constraint_id=f"{simulado.blueprint_id}:must_match_exam_profile",
                    constraint_type="must_match_exam_profile",
                    severity="error",
                    description="Future drafts must preserve the selected exam profile as a declarative hint only.",
                    metadata={"profile_id": profile.profile_id},
                )
            )
        constraints.sort(key=lambda item: item.constraint_id)
        return constraints

    def _set_readiness_state(
        self,
        *,
        total_slots: int,
        ready_slots: int,
        blocked_slots: int,
        needs_review_slots: int,
    ) -> str:
        if total_slots == 0:
            return "no_slots"
        if ready_slots == total_slots:
            return "ready_for_review"
        if ready_slots > 0:
            return "partially_ready"
        if needs_review_slots > 0:
            return "needs_review"
        if blocked_slots == total_slots:
            return "blocked"
        return "needs_review"

    def _set_warnings(
        self,
        *,
        simulado: SimuladoBlueprint,
        slot_blueprints: list[QuestionGenerationBlueprint],
    ) -> list[QuestionGenerationWarning]:
        warnings: list[QuestionGenerationWarning] = [
            QuestionGenerationWarning(
                code="no_question_text_generated",
                message="This planning artifact intentionally omits final question content.",
                severity="info",
                related_artifact_type="question_generation_blueprint",
                related_artifact_id=f"question-generation:{simulado.blueprint_id}",
            )
        ]
        for slot in slot_blueprints:
            warnings.extend(slot.warnings)
        return self._dedupe_warnings(warnings)

    def _dedupe_warnings(
        self,
        warnings: list[QuestionGenerationWarning],
    ) -> list[QuestionGenerationWarning]:
        grouped: dict[tuple[str, str | None], QuestionGenerationWarning] = {}
        for item in warnings:
            key = (item.code, item.related_artifact_id)
            grouped.setdefault(key, item)
        return [grouped[key] for key in sorted(grouped)]

    def _safe_snippet(
        self,
        text: str | None,
    ) -> tuple[str | None, QuestionGenerationWarning | None]:
        if not text:
            return None, None
        compact = " ".join(str(text).split())
        compact = self._sanitize_paths(compact)
        if not compact:
            return None, QuestionGenerationWarning(
                code="safe_snippet_omitted",
                message="Snippet was omitted because it could not be exposed safely.",
                severity="info",
            )
        if len(compact) <= SAFE_SNIPPET_LIMIT:
            return compact, None
        return (
            compact[: SAFE_SNIPPET_LIMIT - 1].rstrip() + "…",
            QuestionGenerationWarning(
                code="safe_snippet_truncated",
                message="Snippet was truncated to keep the planning artifact bounded.",
                severity="info",
            ),
        )

    def _sanitize_paths(self, text: str) -> str:
        sanitized = text.replace("file://", "[path]")
        sanitized = re.sub(r"/Users/[^\s]+", "[path]", sanitized)
        sanitized = re.sub(r"/private/[^\s]+", "[path]", sanitized)
        return sanitized

    def _strength(self, confidence: float) -> str:
        if confidence >= 0.8:
            return "high"
        if confidence >= 0.55:
            return "medium"
        return "weak"
