from __future__ import annotations

import re
from collections import Counter

from app.domain.models import (
    CurriculumGraph,
    EditalExtractionResult,
    ExamProfile,
    ExamProfileSelectionCandidate,
    SimuladoBlueprint,
    SimuladoBlueprintRationale,
    SimuladoBlueprintState,
    SimuladoBlueprintWarning,
    SimuladoCoveragePlan,
    SimuladoDistributionPlan,
    SimuladoGenerationConstraint,
    SimuladoQuestionSlot,
    SimuladoReadinessProfile,
    SimuladoScoringPlan,
    SimuladoSectionBlueprint,
    SimuladoTimingPlan,
    StudyCyclePlan,
    StudyCycleTopicSlot,
    utc_now,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.exam_profiles import ExamProfileService


BLUEPRINT_VERSION = "simulado-blueprint-v1"
FINAL_BLUEPRINT_STATUSES = {"ready_for_review", "insufficient_sources", "insufficient_profile"}


class SimuladoBlueprintBuilderService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository
        self.exam_profiles = ExamProfileService(repository)

    def build_blueprint(
        self,
        cycle_id: str,
        *,
        user_id: str | None,
        profile_id: str | None = None,
    ) -> SimuladoBlueprintState | None:
        cycle = self.repository.get_study_cycle_plan_by_id(cycle_id, user_id=user_id)
        if cycle is None:
            return SimuladoBlueprintState(
                blueprint_id=f"simulado:{cycle_id}:{profile_id or 'unknown'}",
                graph_id="",
                cycle_id=cycle_id,
                exam_profile_id=profile_id,
                user_id=user_id,
                current_stage="insufficient_cycle",
                status="insufficient_cycle",
                warnings=["missing_study_cycle"],
                readiness_state="blueprint_insufficient_sources",
                created_at=utc_now(),
                updated_at=utc_now(),
                blueprint_version=BLUEPRINT_VERSION,
            )

        profile, suggestion, requested_profile_id = self._resolve_profile(cycle, user_id=user_id, profile_id=profile_id)
        blueprint_id = f"simulado:{cycle.cycle_id}:{requested_profile_id}"
        existing = self.repository.get_simulado_blueprint_state(cycle.cycle_id, user_id=user_id)
        if (
            existing is not None
            and existing.status in FINAL_BLUEPRINT_STATUSES
            and existing.blueprint_id == blueprint_id
        ):
            return existing

        graph = self.repository.get_curriculum_graph_by_id(cycle.graph_id, user_id=user_id)
        if graph is None:
            return self._persist_insufficient(
                cycle=cycle,
                blueprint_id=blueprint_id,
                requested_profile_id=requested_profile_id,
                user_id=user_id,
                status="insufficient_graph",
                warning_code="missing_curriculum_graph",
                warning_message="Curriculum graph is not available for simulado blueprint planning.",
            )

        if profile is None:
            return self._persist_insufficient(
                cycle=cycle,
                blueprint_id=blueprint_id,
                requested_profile_id=requested_profile_id,
                user_id=user_id,
                status="insufficient_profile",
                warning_code="insufficient_exam_profile",
                warning_message="Exam profile could not be resolved safely for this simulado blueprint.",
                graph=graph,
                suggestion=suggestion,
            )

        return self._build(
            cycle=cycle,
            graph=graph,
            profile=profile,
            suggestion=suggestion,
            requested_profile_id=requested_profile_id,
            user_id=user_id,
        )

    def _persist_insufficient(
        self,
        *,
        cycle: StudyCyclePlan,
        blueprint_id: str,
        requested_profile_id: str,
        user_id: str | None,
        status: str,
        warning_code: str,
        warning_message: str,
        graph: CurriculumGraph | None = None,
        suggestion: ExamProfileSelectionCandidate | None = None,
    ) -> SimuladoBlueprintState:
        warning = SimuladoBlueprintWarning(code=warning_code, message=warning_message, severity="warning")
        warnings = [warning]
        if not cycle.topic_slots:
            warnings.append(
                SimuladoBlueprintWarning(
                    code="insufficient_study_cycle",
                    message="Study cycle does not contain usable topic slots for blueprint planning.",
                    severity="warning",
                )
            )
        limitations = [
            "This blueprint remains candidate-only and does not activate simulated exams.",
            "No final question text, alternatives, answers or gabarito are generated in this pass.",
        ]
        blueprint = SimuladoBlueprint(
            blueprint_id=blueprint_id,
            graph_id=cycle.graph_id,
            cycle_id=cycle.cycle_id,
            exam_profile_id=requested_profile_id if requested_profile_id != "unknown" else None,
            user_id=user_id,
            exam_board=suggestion.exam_board if suggestion else None,
            exam_family=suggestion.exam_family if suggestion else None,
            warnings=warnings,
            rationale=SimuladoBlueprintRationale(
                summary="Simulado blueprint planning is blocked because one or more required sources are missing or unresolved.",
                priorities=["Resolve the missing cycle/graph/profile dependency before trusting simulado planning output."],
                limitations=limitations,
                source_graph_id=cycle.graph_id,
                source_cycle_id=cycle.cycle_id,
                source_exam_profile_id=requested_profile_id if requested_profile_id != "unknown" else None,
                confidence=0.0,
                reasoning=[warning_message],
            ),
            metadata={
                "graph_version": graph.graph_version if graph else None,
                "negative_marking_confirmed": bool((suggestion.metadata if suggestion else {}).get("negative_marking_confirmed")),
                "allow_english_terms": False,
                "bibliography_driven": False,
            },
        )
        state = SimuladoBlueprintState(
            blueprint_id=blueprint_id,
            graph_id=cycle.graph_id,
            cycle_id=cycle.cycle_id,
            exam_profile_id=requested_profile_id if requested_profile_id != "unknown" else None,
            user_id=user_id,
            current_stage=status,
            status=status,
            section_count=0,
            question_slot_count=0,
            coverage_gap_count=len(graph.gaps) if graph else 0,
            readiness_state="blueprint_insufficient_sources",
            warnings=[item.code for item in warnings],
            created_at=utc_now(),
            updated_at=utc_now(),
            blueprint_version=BLUEPRINT_VERSION,
        )
        self.repository.save_simulado_blueprint(blueprint, user_id=user_id)
        self.repository.save_simulado_blueprint_state(state, user_id=user_id)
        return state

    def _build(
        self,
        *,
        cycle: StudyCyclePlan,
        graph: CurriculumGraph,
        profile: ExamProfile,
        suggestion: ExamProfileSelectionCandidate | None,
        requested_profile_id: str,
        user_id: str | None,
    ) -> SimuladoBlueprintState:
        created_at = utc_now()
        blueprint_id = f"simulado:{cycle.cycle_id}:{requested_profile_id}"
        edital_result = self.repository.get_edital_extraction_by_id(graph.edital_id, user_id=user_id)

        format_type, format_confirmed = self._resolve_format(profile, suggestion)
        question_slot_format = self._question_slot_format(format_type, profile)
        scoring_plan = self._scoring_plan(profile, suggestion)
        sections = self._sections(
            graph=graph,
            profile=profile,
            format_type=format_type,
            question_slot_format=question_slot_format,
            scoring_plan=scoring_plan,
        )
        primary_section_id = sections[0].section_id if sections else "section:primary"
        question_slots = [
            self._question_slot(
                slot=item,
                section_id=primary_section_id,
                format_type=question_slot_format,
                profile=profile,
            )
            for item in sorted(cycle.topic_slots, key=lambda entry: entry.order_index)
        ]
        warnings = self._warnings(
            cycle=cycle,
            question_slots=question_slots,
            format_type=format_type,
            format_confirmed=format_confirmed,
            scoring_plan=scoring_plan,
        )
        distribution_plan = self._distribution_plan(
            cycle=cycle,
            sections=sections,
            question_slots=question_slots,
            edital_result=edital_result,
            profile=profile,
        )
        timing_plan = self._timing_plan(
            sections=sections,
            distribution_plan=distribution_plan,
            edital_result=edital_result,
            profile=profile,
        )
        coverage_plan = self._coverage_plan(question_slots)
        readiness_profile = self._readiness_profile(
            question_slots=question_slots,
            warnings=warnings,
            format_type=format_type,
            format_confirmed=format_confirmed,
            scoring_plan=scoring_plan,
        )
        constraints = self._constraints(
            cycle=cycle,
            question_slots=question_slots,
            suggestion=suggestion,
            format_type=format_type,
            format_confirmed=format_confirmed,
            scoring_plan=scoring_plan,
            distribution_plan=distribution_plan,
        )
        rationale = self._rationale(
            cycle=cycle,
            graph=graph,
            requested_profile_id=requested_profile_id,
            readiness_profile=readiness_profile,
            warnings=warnings,
        )

        blueprint = SimuladoBlueprint(
            blueprint_id=blueprint_id,
            graph_id=graph.graph_id,
            cycle_id=cycle.cycle_id,
            exam_profile_id=requested_profile_id if requested_profile_id != "unknown" else profile.profile_id,
            user_id=user_id,
            exam_board=profile.exam_board,
            exam_family=suggestion.exam_family if suggestion and suggestion.exam_family else profile.exam_family,
            format_type=format_type,
            sections=sections,
            question_slots=question_slots,
            distribution_plan=distribution_plan,
            timing_plan=timing_plan,
            scoring_plan=scoring_plan,
            coverage_plan=coverage_plan,
            readiness_profile=readiness_profile,
            generation_constraints=constraints,
            warnings=warnings,
            rationale=rationale,
            blueprint_version=BLUEPRINT_VERSION,
            metadata={
                "graph_version": graph.graph_version,
                "cycle_version": cycle.cycle_version,
                "profile_version": profile.profile_version,
                "negative_marking_confirmed": bool((suggestion.metadata if suggestion else {}).get("negative_marking_confirmed")),
                "allow_english_terms": profile.generation_profile.allow_english_terms,
                "bibliography_driven": profile.content_behavior_profile.bibliography_weight in {"high", "medium"},
            },
        )
        state = SimuladoBlueprintState(
            blueprint_id=blueprint_id,
            graph_id=graph.graph_id,
            cycle_id=cycle.cycle_id,
            exam_profile_id=requested_profile_id if requested_profile_id != "unknown" else profile.profile_id,
            user_id=user_id,
            current_stage="ready_for_review",
            status="ready_for_review",
            section_count=len(sections),
            question_slot_count=len(question_slots),
            coverage_gap_count=len(coverage_plan.excluded_gap_ids),
            readiness_state=readiness_profile.readiness_state,
            warnings=[item.code for item in warnings],
            created_at=created_at,
            updated_at=created_at,
            blueprint_version=BLUEPRINT_VERSION,
        )
        self.repository.save_simulado_blueprint(blueprint, user_id=user_id)
        self.repository.save_simulado_blueprint_state(state, user_id=user_id)
        return state

    def _resolve_profile(
        self,
        cycle: StudyCyclePlan,
        *,
        user_id: str | None,
        profile_id: str | None,
    ) -> tuple[ExamProfile | None, ExamProfileSelectionCandidate | None, str]:
        requested_profile_id = profile_id or "unknown"
        suggestion = None
        profile = self.exam_profiles.get_exam_profile(profile_id) if profile_id else None
        if profile is not None:
            return profile, suggestion, profile.profile_id
        graph = self.repository.get_curriculum_graph_by_id(cycle.graph_id, user_id=user_id)
        if graph is not None:
            suggestion = self.exam_profiles.suggest_exam_profile_for_edital_id(graph.edital_id, user_id=user_id)
            if suggestion and suggestion.profile_id:
                inferred = self.exam_profiles.get_exam_profile(suggestion.profile_id)
                if inferred is not None:
                    return inferred, suggestion, inferred.profile_id
        return None, suggestion, requested_profile_id

    def _resolve_format(
        self,
        profile: ExamProfile,
        suggestion: ExamProfileSelectionCandidate | None,
    ) -> tuple[str, bool]:
        if suggestion and suggestion.format_type and suggestion.format_type != "unknown":
            confirmed = bool(suggestion.metadata.get("format_requires_confirmation") is False)
            return suggestion.format_type, confirmed
        profile_format = profile.question_format.format_type or "unknown"
        confirmed = profile.question_format.explicit_format_confirmed
        return profile_format, confirmed

    def _question_slot_format(self, format_type: str, profile: ExamProfile) -> str:
        if format_type == "mixed":
            if profile.question_format.options_count == 5:
                return "multiple_choice_5"
            if profile.question_format.options_count == 4:
                return "multiple_choice_4"
            return "unknown"
        return format_type

    def _sections(
        self,
        *,
        graph: CurriculumGraph,
        profile: ExamProfile,
        format_type: str,
        question_slot_format: str,
        scoring_plan: SimuladoScoringPlan,
    ) -> list[SimuladoSectionBlueprint]:
        section_type = "unknown"
        section_title = "Objective Candidate Block"
        if (profile.exam_family == "PSCPP") or graph.subjects and any("praticagem" in item.normalized_title for item in graph.subjects):
            section_type = "technical_maritime_block"
            section_title = "Technical Maritime Candidate Block"
        elif format_type == "true_false":
            section_type = "true_false_block"
            section_title = "True/False Candidate Block"
        elif question_slot_format in {"multiple_choice_5", "multiple_choice_4"}:
            section_type = "multiple_choice_block"
            section_title = "Multiple Choice Candidate Block"
        elif format_type == "discursive":
            section_type = "discursive_hint"
            section_title = "Discursive Candidate Hint"
        primary = SimuladoSectionBlueprint(
            section_id="section:primary",
            section_title=section_title,
            section_type=section_type,
            order_index=0,
            target_subject_ids=[item.subject_id for item in sorted(graph.subjects, key=lambda entry: entry.order_index)],
            target_topic_ids=[item.topic_id for item in sorted(graph.topics, key=lambda entry: entry.order_index)],
            planned_question_count=max(0, len(graph.topics)),
            format_type=question_slot_format if section_type != "discursive_hint" else format_type,
            scoring_notes=scoring_plan.reasoning,
            confidence=0.72 if format_type != "unknown" else 0.45,
            reasoning="Primary simulado section preserves resolved format and subject/topic scope conservatively.",
            metadata={"exam_family": profile.exam_family},
        )
        sections = [primary]
        if format_type == "mixed":
            sections.append(
                SimuladoSectionBlueprint(
                    section_id="section:discursive-hint",
                    section_title="Discursive Module Hint",
                    section_type="discursive_hint",
                    order_index=1,
                    planned_question_count=0,
                    format_type="discursive",
                    confidence=0.7,
                    reasoning="Discursive wording was detected, but this pass only records the hint without generating items.",
                )
            )
        return sections

    def _question_slot(
        self,
        *,
        slot: StudyCycleTopicSlot,
        section_id: str,
        format_type: str,
        profile: ExamProfile,
    ) -> SimuladoQuestionSlot:
        readiness_state = "needs_review"
        if slot.slot_type == "ocr_blocked":
            readiness_state = "blocked_by_ocr"
        elif slot.slot_type == "gap_blocked":
            readiness_state = "blocked_by_material_gap"
        elif slot.slot_type == "ambiguous_review":
            readiness_state = "blocked_by_ambiguity"
        elif slot.slot_type in {"reinforce", "review_needed"} and slot.source_evidence_ids:
            readiness_state = "ready_for_generation" if slot.slot_type == "reinforce" else "needs_review"
        elif slot.slot_type == "weak_topic_resurfacing":
            readiness_state = "needs_review"
        elif not slot.source_evidence_ids:
            readiness_state = "insufficient_source_evidence"

        difficulty_hint = {
            "light": "easy",
            "moderate": "medium",
            "high": "hard",
            "blocked_by_material_gap": "unknown",
        }.get(slot.intensity_level, "unknown")

        cognitive_demand = "unknown"
        if profile.cognitive_demand_profile.application_demand in {"high", "medium"}:
            cognitive_demand = profile.cognitive_demand_profile.application_demand
        elif profile.cognitive_demand_profile.reading_precision_demand in {"high", "medium"}:
            cognitive_demand = profile.cognitive_demand_profile.reading_precision_demand

        return SimuladoQuestionSlot(
            slot_id=f"question-slot:{slot.topic_id}",
            section_id=section_id,
            order_index=slot.order_index,
            target_subject_id=slot.subject_id,
            target_topic_id=slot.topic_id,
            format_type=format_type,
            cognitive_demand=cognitive_demand,
            difficulty_hint=difficulty_hint,
            generation_style=profile.generation_profile.generation_style,
            source_evidence_ids=slot.source_evidence_ids,
            required_coverage_state=slot.coverage_state,
            blocked_by_gap_ids=slot.gap_ids,
            readiness_state=readiness_state,
            confidence=slot.confidence,
            reasoning="Candidate question slot derived from study-cycle topic slot without generating final question content.",
            metadata={
                "slot_type": slot.slot_type,
                "review_state": slot.review_state,
                "suggested_action": slot.suggested_action,
                "redundancy_ids": slot.redundancy_ids,
                "allow_english_terms": profile.generation_profile.allow_english_terms,
            },
        )

    def _distribution_plan(
        self,
        *,
        cycle: StudyCyclePlan,
        sections: list[SimuladoSectionBlueprint],
        question_slots: list[SimuladoQuestionSlot],
        edital_result: EditalExtractionResult | None,
        profile: ExamProfile,
    ) -> SimuladoDistributionPlan:
        total_question_count = 0
        source = "insufficient_evidence"
        if edital_result is not None:
            for hint in edital_result.weight_hints:
                if hint.weight_type == "question_count" and hint.value > 0:
                    total_question_count = int(hint.value)
                    source = "explicit_edital"
                    break
            if not total_question_count:
                preview = str(edital_result.metadata.get("source_text_preview", ""))
                match = re.search(r"(\d{2,3})\s+quest", preview.lower())
                if match:
                    total_question_count = int(match.group(1))
                    source = "explicit_edital"
        if not total_question_count and profile.question_format.expected_question_count:
            total_question_count = profile.question_format.expected_question_count
            source = "exam_profile_hint"
        if not total_question_count:
            total_question_count = max(10, len(question_slots))
            source = "default_candidate"

        section_distribution = {section.section_id: section.planned_question_count for section in sections}
        if sections:
            section_distribution[sections[0].section_id] = total_question_count
        subject_distribution = dict(Counter(slot.target_subject_id for slot in question_slots))
        topic_distribution = dict(Counter(slot.target_topic_id for slot in question_slots))
        weak_topics = [
            slot.target_topic_id
            for slot in question_slots
            if slot.required_coverage_state == "weakly_covered"
        ]
        gap_exclusions = sorted(
            {
                gap_slot.source_gap_id
                for gap_slot in cycle.gap_slots
                if gap_slot.gap_type in {"missing_bibliography_material", "missing_document_text", "ocr_required", "uncovered_topic"}
            }
        )
        confidence = 0.82 if source == "explicit_edital" else 0.68 if source == "exam_profile_hint" else 0.5
        return SimuladoDistributionPlan(
            total_question_count=total_question_count,
            question_count_source=source,
            section_distribution=section_distribution,
            subject_distribution=subject_distribution,
            topic_distribution=topic_distribution,
            weak_topic_allocation=weak_topics,
            gap_exclusions=gap_exclusions,
            confidence=confidence,
            reasoning="Distribution preserves study-cycle order, source evidence and gap exclusions without becoming authoritative.",
            metadata={"topic_slot_count": len(question_slots)},
        )

    def _timing_plan(
        self,
        *,
        sections: list[SimuladoSectionBlueprint],
        distribution_plan: SimuladoDistributionPlan,
        edital_result: EditalExtractionResult | None,
        profile: ExamProfile,
    ) -> SimuladoTimingPlan:
        total_duration = 0
        source = "unknown"
        preview = ""
        if edital_result is not None:
            preview = str(edital_result.metadata.get("source_text_preview", "")).lower()
            minute_match = re.search(r"(\d{2,3})\s+min", preview)
            hour_match = re.search(r"(\d)\s+hora", preview)
            if minute_match:
                total_duration = int(minute_match.group(1))
                source = "explicit_edital"
            elif hour_match:
                total_duration = int(hour_match.group(1)) * 60
                source = "explicit_edital"
        if not total_duration and profile.timing_profile.total_duration_minutes:
            total_duration = profile.timing_profile.total_duration_minutes
            source = "exam_profile_hint"
        if not total_duration:
            total_duration = max(distribution_plan.total_question_count, 60)
            source = "default_candidate"
        minutes_per_question = round(
            total_duration / max(1, distribution_plan.total_question_count),
            2,
        )
        section_timing = {}
        for section in sections:
            proportion = 0 if distribution_plan.total_question_count == 0 else distribution_plan.section_distribution.get(section.section_id, 0) / distribution_plan.total_question_count
            allocated = int(round(total_duration * proportion)) if proportion else 0
            section_timing[section.section_id] = allocated
            section.timing_minutes = allocated
        return SimuladoTimingPlan(
            total_duration_minutes=total_duration,
            duration_source=source,
            estimated_minutes_per_question=minutes_per_question,
            timing_pressure=profile.timing_profile.timing_pressure if profile.timing_profile.timing_pressure != "unknown" else "moderate",
            section_timing=section_timing,
            confidence=0.82 if source == "explicit_edital" else 0.66 if source == "exam_profile_hint" else 0.48,
            reasoning="Timing plan remains candidate-only and uses edital/profile hints before any default fallback.",
            metadata={"preview_has_duration_signal": bool(preview)},
        )

    def _scoring_plan(
        self,
        profile: ExamProfile,
        suggestion: ExamProfileSelectionCandidate | None,
    ) -> SimuladoScoringPlan:
        metadata = suggestion.metadata if suggestion else {}
        negative_confirmed = bool(metadata.get("negative_marking_confirmed"))
        if negative_confirmed:
            return SimuladoScoringPlan(
                scoring_type=profile.scoring_profile.scoring_type if profile.scoring_profile.scoring_type != "unknown" else "right_wrong",
                negative_marking=True,
                scoring_source="explicit_edital",
                correct_value=1.0,
                wrong_value=-1.0,
                blank_value=0.0,
                confidence=0.88,
                reasoning="Negative marking was only confirmed because explicit scoring evidence was found in the edital.",
            )
        if profile.scoring_profile.scoring_source != "unknown":
            return SimuladoScoringPlan(
                scoring_type=profile.scoring_profile.scoring_type,
                negative_marking=False,
                scoring_source="exam_profile_hint",
                correct_value=profile.scoring_profile.correct,
                wrong_value=profile.scoring_profile.wrong,
                blank_value=profile.scoring_profile.blank,
                double_mark_value=profile.scoring_profile.double_mark,
                confidence=max(0.35, profile.scoring_profile.scoring_confidence),
                reasoning="Scoring remains a non-authoritative board/profile hint because the edital did not confirm it explicitly.",
            )
        return SimuladoScoringPlan(
            scoring_type="unknown",
            negative_marking=False,
            scoring_source="unknown",
            confidence=0.2,
            reasoning="Scoring could not be confirmed safely from either edital evidence or a stable board hint.",
        )

    def _coverage_plan(self, question_slots: list[SimuladoQuestionSlot]) -> SimuladoCoveragePlan:
        covered = sum(1 for item in question_slots if item.required_coverage_state == "covered")
        partial = sum(1 for item in question_slots if item.required_coverage_state == "partially_covered")
        weak = sum(1 for item in question_slots if item.required_coverage_state == "weakly_covered")
        uncovered = sum(1 for item in question_slots if item.required_coverage_state == "uncovered")
        ocr = sum(1 for item in question_slots if item.readiness_state == "blocked_by_ocr")
        ambiguity = sum(1 for item in question_slots if item.readiness_state == "blocked_by_ambiguity")
        excluded_gap_ids = sorted({gap_id for item in question_slots for gap_id in item.blocked_by_gap_ids})
        return SimuladoCoveragePlan(
            covered_topic_slots=covered,
            partially_covered_topic_slots=partial,
            weak_topic_slots=weak,
            uncovered_topic_slots=uncovered,
            ocr_blocked_slots=ocr,
            ambiguous_slots=ambiguity,
            excluded_gap_ids=excluded_gap_ids,
            readiness_summary="Coverage plan preserves blocked and ambiguous areas instead of marking them as ready.",
            confidence=0.74 if question_slots else 0.0,
            reasoning="Coverage plan aggregates slot-level coverage/readiness without inventing study-ready evidence.",
            metadata={"slot_count": len(question_slots)},
        )

    def _readiness_profile(
        self,
        *,
        question_slots: list[SimuladoQuestionSlot],
        warnings: list[SimuladoBlueprintWarning],
        format_type: str,
        format_confirmed: bool,
        scoring_plan: SimuladoScoringPlan,
    ) -> SimuladoReadinessProfile:
        ready = sum(1 for item in question_slots if item.readiness_state == "ready_for_generation")
        blocked_ocr = sum(1 for item in question_slots if item.readiness_state == "blocked_by_ocr")
        blocked_gap = sum(1 for item in question_slots if item.readiness_state == "blocked_by_material_gap")
        blocked_amb = sum(1 for item in question_slots if item.readiness_state == "blocked_by_ambiguity")
        blocked_total = blocked_ocr + blocked_gap + blocked_amb
        review_needed = sum(1 for item in question_slots if item.readiness_state in {"needs_review", "insufficient_source_evidence", "deferred"})
        if not question_slots:
            state = "blueprint_insufficient_sources"
        elif blocked_amb >= max(1, len(question_slots) // 2) or format_type == "unknown":
            state = "blueprint_ambiguous"
        elif blocked_ocr >= max(1, len(question_slots) // 2):
            state = "blueprint_ocr_blocked"
        elif blocked_gap + blocked_ocr >= max(1, len(question_slots) // 2):
            state = "blueprint_material_blocked"
        elif ready == 0:
            state = "blueprint_not_ready"
        elif not format_confirmed or scoring_plan.scoring_source == "unknown" or review_needed or blocked_total:
            state = "blueprint_partially_ready"
        else:
            state = "blueprint_ready_for_review"
        return SimuladoReadinessProfile(
            readiness_state=state,
            ready_slot_count=ready,
            blocked_slot_count=blocked_total,
            review_needed_slot_count=review_needed,
            ocr_blocked_count=blocked_ocr,
            material_gap_count=blocked_gap,
            ambiguity_count=blocked_amb,
            warnings_count=len(warnings),
            confidence=0.78 if state == "blueprint_ready_for_review" else 0.55 if ready else 0.3,
            reasoning="Readiness profile stays conservative whenever format, scoring or source coverage remain incomplete.",
            metadata={"format_confirmed": format_confirmed},
        )

    def _constraints(
        self,
        *,
        cycle: StudyCyclePlan,
        question_slots: list[SimuladoQuestionSlot],
        suggestion: ExamProfileSelectionCandidate | None,
        format_type: str,
        format_confirmed: bool,
        scoring_plan: SimuladoScoringPlan,
        distribution_plan: SimuladoDistributionPlan,
    ) -> list[SimuladoGenerationConstraint]:
        constraints = [
            SimuladoGenerationConstraint(
                constraint_id="constraint:no-question-generation",
                constraint_type="no_question_generation_in_this_pass",
                description="This foundation only produces a simulado blueprint and must not generate final question text, options or answers.",
                severity="info",
                reasoning="Scope control for the blueprint-only pass.",
            ),
            SimuladoGenerationConstraint(
                constraint_id="constraint:source-topic-mapping",
                constraint_type="require_source_topic_mapping",
                description="Question slots should remain anchored to mapped curriculum topics and evidence identifiers.",
                severity="warning",
                reasoning="Prevents free-floating question planning without curriculum/evidence traceability.",
            ),
        ]
        if any(item.readiness_state == "blocked_by_material_gap" for item in question_slots):
            constraints.append(
                SimuladoGenerationConstraint(
                    constraint_id="constraint:avoid-uncovered",
                    constraint_type="avoid_uncovered_topic",
                    description="Topics blocked by missing materials should not be treated as normal ready slots.",
                    severity="warning",
                    reasoning="Material gaps are preserved as blockers instead of hidden exclusions.",
                )
            )
        if any(item.readiness_state == "blocked_by_ocr" for item in question_slots):
            constraints.append(
                SimuladoGenerationConstraint(
                    constraint_id="constraint:avoid-ocr",
                    constraint_type="avoid_ocr_blocked_topic",
                    description="OCR-blocked topics should not be treated as normal ready slots.",
                    severity="warning",
                    reasoning="OCR is explicitly out of scope for this pass.",
                )
            )
        if any(item.readiness_state == "blocked_by_ambiguity" for item in question_slots):
            constraints.append(
                SimuladoGenerationConstraint(
                    constraint_id="constraint:manual-review",
                    constraint_type="require_manual_review",
                    description="Ambiguous topics require manual review before any later generation step.",
                    severity="warning",
                    reasoning="Ambiguity is preserved instead of auto-resolved.",
                )
            )
        if not format_confirmed or format_type == "unknown":
            constraints.append(
                SimuladoGenerationConstraint(
                    constraint_id="constraint:format-confirmation",
                    constraint_type="format_requires_confirmation",
                    description="The final answer format still requires edital confirmation.",
                    severity="warning",
                    reasoning="Board defaults never override missing explicit format evidence.",
                )
            )
        if scoring_plan.scoring_source != "explicit_edital":
            constraints.append(
                SimuladoGenerationConstraint(
                    constraint_id="constraint:scoring-confirmation",
                    constraint_type="scoring_requires_confirmation",
                    description="Scoring should be confirmed from explicit edital wording before any later simulation pass.",
                    severity="warning",
                    reasoning="Negative marking is never treated as universally confirmed by board name alone.",
                )
            )
        if distribution_plan.question_count_source != "explicit_edital":
            constraints.append(
                SimuladoGenerationConstraint(
                    constraint_id="constraint:question-count-confirmation",
                    constraint_type="question_count_requires_confirmation",
                    description="The target question count still depends on profile/default hints and should be confirmed by the edital.",
                    severity="info",
                    reasoning="Question count remains a candidate planning hint in the absence of explicit edital evidence.",
                )
            )
        if suggestion and any(item.code == "exam_family_over_board" for item in suggestion.warnings):
            constraints.append(
                SimuladoGenerationConstraint(
                    constraint_id="constraint:family-over-board",
                    constraint_type="exam_family_over_board",
                    description="Special exam-family signals took precedence over generic board defaults.",
                    severity="info",
                    reasoning="PSCPP/Praticagem family evidence remains more important than generic organizer style.",
                )
            )
        if cycle.topic_slots and not question_slots:
            constraints.append(
                SimuladoGenerationConstraint(
                    constraint_id="constraint:no-slots",
                    constraint_type="require_manual_review",
                    description="No usable question slots were produced from the current study cycle.",
                    severity="warning",
                    reasoning="Insufficient planning evidence prevents blueprint readiness.",
                )
            )
        return constraints

    def _warnings(
        self,
        *,
        cycle: StudyCyclePlan,
        question_slots: list[SimuladoQuestionSlot],
        format_type: str,
        format_confirmed: bool,
        scoring_plan: SimuladoScoringPlan,
    ) -> list[SimuladoBlueprintWarning]:
        warnings: list[SimuladoBlueprintWarning] = []
        if format_type == "unknown" or not format_confirmed:
            warnings.append(
                SimuladoBlueprintWarning(
                    code="format_requires_confirmation",
                    message="The simulado answer format still needs edital confirmation.",
                    severity="warning",
                )
            )
        if scoring_plan.scoring_source != "explicit_edital":
            warnings.append(
                SimuladoBlueprintWarning(
                    code="scoring_requires_confirmation",
                    message="The scoring model remains a hint until explicit edital wording confirms it.",
                    severity="warning",
                )
            )
        if any(item.readiness_state == "blocked_by_ocr" for item in question_slots):
            warnings.append(
                SimuladoBlueprintWarning(
                    code="ocr_blocked_slots_present",
                    message="Some candidate slots remain blocked by OCR-required sources.",
                    severity="warning",
                )
            )
        if any(item.readiness_state == "blocked_by_material_gap" for item in question_slots):
            warnings.append(
                SimuladoBlueprintWarning(
                    code="material_gap_slots_present",
                    message="Some candidate slots remain blocked by missing materials or missing text.",
                    severity="warning",
                )
            )
        if any(item.readiness_state == "blocked_by_ambiguity" for item in question_slots):
            warnings.append(
                SimuladoBlueprintWarning(
                    code="ambiguous_slots_require_manual_review",
                    message="Some candidate slots remain ambiguous and require manual review.",
                    severity="warning",
                )
            )
        if not cycle.topic_slots:
            warnings.append(
                SimuladoBlueprintWarning(
                    code="insufficient_study_cycle",
                    message="Study cycle did not provide usable topic slots for simulado planning.",
                    severity="warning",
                )
            )
        return warnings

    def _rationale(
        self,
        *,
        cycle: StudyCyclePlan,
        graph: CurriculumGraph,
        requested_profile_id: str,
        readiness_profile: SimuladoReadinessProfile,
        warnings: list[SimuladoBlueprintWarning],
    ) -> SimuladoBlueprintRationale:
        priorities = [
            "Preserve study-cycle topic ordering and evidence instead of inventing a new curriculum ranking.",
            "Favor ready and partially covered topics while surfacing weak or blocked areas as constrained slots.",
        ]
        limitations = [
            "This pass creates question slots only and does not generate final questions, alternatives, answers or gabarito.",
            "No active exam scheduling, no runtime mutation and no study-cycle replacement occur here.",
            "Manual review is still required when format, scoring or source readiness remain uncertain.",
        ]
        reasoning = [
            "Blueprint sections, slots and readiness were derived deterministically from study-cycle, graph and exam-profile artifacts.",
            "Blocked, OCR-dependent and ambiguous topics were preserved as constraints instead of being hidden.",
        ]
        confidence = 0.0
        if cycle.topic_slots:
            confidence = round(sum(item.confidence for item in cycle.topic_slots) / len(cycle.topic_slots), 4)
        return SimuladoBlueprintRationale(
            summary=(
                "Candidate simulado blueprint organizes sections, slot targets, timing and scoring hints "
                "without generating final exam questions."
            ),
            priorities=priorities,
            limitations=limitations,
            source_graph_id=graph.graph_id,
            source_cycle_id=cycle.cycle_id,
            source_exam_profile_id=requested_profile_id if requested_profile_id != "unknown" else None,
            confidence=confidence,
            reasoning=reasoning + [f"Blueprint readiness ended in state: {readiness_profile.readiness_state}."],
            metadata={"warning_count": len(warnings)},
        )
