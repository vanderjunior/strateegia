from __future__ import annotations

from collections import defaultdict

from app.domain.models import (
    CurriculumGapReference,
    CurriculumGraph,
    CurriculumRedundancyReference,
    CurriculumTopicNode,
    StudyCycleBalanceSummary,
    StudyCycleFatigueProfile,
    StudyCycleGapSlot,
    StudyCyclePlan,
    StudyCyclePlanState,
    StudyCycleRationale,
    StudyCycleReviewSlot,
    StudyCycleSubjectRotation,
    StudyCycleTopicSlot,
    StudyCycleWarning,
    utc_now,
)
from app.repositories.json_store import JsonStudyRepository


CYCLE_VERSION = "study-cycle-v1"
FINAL_CYCLE_STATUSES = {"ready_for_review", "insufficient_graph"}


class StudyCycleOrchestratorService:
    def __init__(self, repository: JsonStudyRepository):
        self.repository = repository

    def build_cycle(
        self,
        graph_id: str,
        *,
        user_id: str | None,
    ) -> StudyCyclePlanState | None:
        graph = self.repository.get_curriculum_graph_by_id(graph_id, user_id=user_id)
        if graph is None:
            return StudyCyclePlanState(
                cycle_id=f"cycle:{graph_id}",
                graph_id=graph_id,
                user_id=user_id,
                current_stage="insufficient_graph",
                status="insufficient_graph",
                warnings=["missing_curriculum_graph"],
                created_at=utc_now(),
                updated_at=utc_now(),
                cycle_version=CYCLE_VERSION,
            )

        existing = self.repository.get_study_cycle_plan_state(graph_id, user_id=user_id)
        if existing is not None and existing.status in FINAL_CYCLE_STATUSES:
            return existing

        return self._build(graph, user_id=user_id)

    def _build(
        self,
        graph: CurriculumGraph,
        *,
        user_id: str | None,
    ) -> StudyCyclePlanState:
        created_at = utc_now()
        cycle_id = f"cycle:{graph.graph_id}"
        warnings: list[StudyCycleWarning] = []

        if not graph.subjects or not graph.topics:
            warnings.append(
                StudyCycleWarning(
                    code="insufficient_curriculum_graph",
                    message="Curriculum graph does not yet contain enough subject/topic structure for cycle planning.",
                    severity="warning",
                )
            )
            plan = StudyCyclePlan(
                cycle_id=cycle_id,
                graph_id=graph.graph_id,
                user_id=user_id,
                warnings=warnings,
                rationale=StudyCycleRationale(
                    summary="Cycle planning is blocked because the curriculum graph is incomplete.",
                    reasons=["No usable subject/topic structure was found in the current graph."],
                    limitations=["This candidate plan cannot propose slots without a minimally populated graph."],
                    source_graph_id=graph.graph_id,
                    confidence=0.0,
                ),
                metadata={"graph_version": graph.graph_version},
            )
            state = StudyCyclePlanState(
                cycle_id=cycle_id,
                graph_id=graph.graph_id,
                user_id=user_id,
                current_stage="insufficient_graph",
                status="insufficient_graph",
                warnings=[item.code for item in warnings],
                created_at=created_at,
                updated_at=created_at,
                cycle_version=CYCLE_VERSION,
            )
            self.repository.save_study_cycle_plan(plan, user_id=user_id)
            self.repository.save_study_cycle_plan_state(state, user_id=user_id)
            return state

        gaps_by_topic: dict[str, list[CurriculumGapReference]] = defaultdict(list)
        redundancies_by_topic: dict[str, list[CurriculumRedundancyReference]] = defaultdict(list)
        for gap in graph.gaps:
            if gap.target_type == "topic":
                gaps_by_topic[gap.target_id].append(gap)
        for redundancy in graph.redundancies:
            if redundancy.target_type == "topic":
                redundancies_by_topic[redundancy.target_id].append(redundancy)

        topic_slots: list[StudyCycleTopicSlot] = []
        review_slots: list[StudyCycleReviewSlot] = []
        gap_slots = [self._gap_slot(item, index=index) for index, item in enumerate(graph.gaps)]

        topics_by_subject: dict[str, list[CurriculumTopicNode]] = defaultdict(list)
        for topic in sorted(graph.topics, key=lambda item: item.order_index):
            topics_by_subject[topic.subject_id].append(topic)
            topic_gaps = gaps_by_topic.get(topic.topic_id, [])
            topic_redundancies = redundancies_by_topic.get(topic.topic_id, [])
            slot = self._topic_slot(topic, topic_gaps, topic_redundancies)
            topic_slots.append(slot)
            review = self._review_slot(topic, slot, topic_gaps, topic_redundancies)
            if review is not None:
                review_slots.append(review)

        subject_rotations: list[StudyCycleSubjectRotation] = []
        for index, subject in enumerate(sorted(graph.subjects, key=lambda item: item.order_index)):
            related_slots = [slot for slot in topic_slots if slot.subject_id == subject.subject_id]
            subject_rotations.append(self._subject_rotation(subject, related_slots, order_index=index))

        fatigue_profile = self._fatigue_profile(topic_slots, subject_rotations)
        balance_summary = self._balance_summary(graph, topic_slots, review_slots, gap_slots)
        warnings.extend(self._warnings(graph, topic_slots, gap_slots, balance_summary))
        rationale = self._rationale(graph, topic_slots, gap_slots, warnings)

        plan = StudyCyclePlan(
            cycle_id=cycle_id,
            graph_id=graph.graph_id,
            user_id=user_id,
            subject_rotations=subject_rotations,
            topic_slots=topic_slots,
            review_slots=review_slots,
            gap_slots=gap_slots,
            fatigue_profile=fatigue_profile,
            balance_summary=balance_summary,
            warnings=warnings,
            rationale=rationale,
            cycle_version=CYCLE_VERSION,
            metadata={"graph_version": graph.graph_version, "graph_summary": graph.summary.model_dump(mode="json")},
        )
        state = StudyCyclePlanState(
            cycle_id=cycle_id,
            graph_id=graph.graph_id,
            user_id=user_id,
            current_stage="ready_for_review",
            status="ready_for_review",
            subject_count=len(subject_rotations),
            topic_slot_count=len(topic_slots),
            review_slot_count=len(review_slots),
            gap_slot_count=len(gap_slots),
            warnings=[item.code for item in warnings],
            created_at=created_at,
            updated_at=created_at,
            cycle_version=CYCLE_VERSION,
        )
        self.repository.save_study_cycle_plan(plan, user_id=user_id)
        self.repository.save_study_cycle_plan_state(state, user_id=user_id)
        return state

    def _topic_slot(
        self,
        topic: CurriculumTopicNode,
        gaps: list[CurriculumGapReference],
        redundancies: list[CurriculumRedundancyReference],
    ) -> StudyCycleTopicSlot:
        gap_types = {item.gap_type for item in gaps}
        if topic.review_state == "ocr_required" or "ocr_required" in gap_types:
            slot_type = "ocr_blocked"
            action = "process_ocr_material"
            intensity = "blocked_by_material_gap"
        elif topic.review_state == "ambiguous" or "ambiguous_reference" in gap_types or redundancies:
            slot_type = "ambiguous_review"
            action = "manual_review_required"
            intensity = "moderate"
        elif topic.coverage_state == "covered" and topic.review_state == "ready_for_review":
            slot_type = "reinforce"
            action = "reinforce_with_existing_material"
            intensity = "light"
        elif topic.coverage_state == "partially_covered":
            slot_type = "review_needed"
            action = "reinforce_with_existing_material"
            intensity = "moderate"
        elif topic.coverage_state == "weakly_covered":
            slot_type = "weak_topic_resurfacing"
            action = "study_now_candidate"
            intensity = "high"
        elif topic.coverage_state == "uncovered":
            if gap_types & {"missing_document_text", "missing_bibliography_material", "uncovered_topic"}:
                slot_type = "gap_blocked"
                action = "resolve_material_gap"
                intensity = "blocked_by_material_gap"
            else:
                slot_type = "learn"
                action = "study_now_candidate"
                intensity = "high"
        else:
            slot_type = "review_needed"
            action = "manual_review_required" if topic.review_state == "needs_review" else "review_later_candidate"
            intensity = "moderate"
        return StudyCycleTopicSlot(
            slot_id=f"slot:{topic.topic_id}",
            subject_id=topic.subject_id,
            topic_id=topic.topic_id,
            topic_title=topic.title,
            order_index=topic.order_index,
            slot_type=slot_type,
            coverage_state=topic.coverage_state,
            review_state=topic.review_state,
            suggested_action=action,
            intensity_level=intensity,
            source_evidence_ids=[item.evidence_id for item in topic.evidence],
            gap_ids=[item.gap_id for item in gaps],
            redundancy_ids=[item.redundancy_id for item in redundancies],
            confidence=topic.confidence,
            reasoning="candidate study slot derived conservatively from curriculum graph coverage and review state",
            metadata={"source_topic_candidate_id": topic.source_topic_candidate_id},
        )

    def _review_slot(
        self,
        topic: CurriculumTopicNode,
        slot: StudyCycleTopicSlot,
        gaps: list[CurriculumGapReference],
        redundancies: list[CurriculumRedundancyReference],
    ) -> StudyCycleReviewSlot | None:
        if slot.slot_type in {"reinforce", "learn"} and not redundancies and topic.review_state not in {"needs_review", "ambiguous", "source_missing", "ocr_required"} and topic.coverage_state not in {"partially_covered", "weakly_covered"}:
            return None
        if slot.slot_type == "ambiguous_review":
            trigger = "ambiguity"
            priority = "high"
            reason = "Topic has ambiguous coverage or redundancy signals that require manual review."
        elif slot.slot_type == "ocr_blocked":
            trigger = "needs_review"
            priority = "high"
            reason = "Topic is blocked by OCR-dependent material and should remain in a candidate review queue."
        elif slot.slot_type == "gap_blocked":
            trigger = "uncovered_topic"
            priority = "high"
            reason = "Topic is blocked by a material gap and should remain visible in candidate review planning."
        elif topic.coverage_state == "weakly_covered":
            trigger = "weak_coverage"
            priority = "high"
            reason = "Topic has weak coverage and should resurface in a review-oriented slot."
        elif topic.coverage_state == "partially_covered":
            trigger = "partial_coverage"
            priority = "medium"
            reason = "Topic has partial coverage and benefits from a reinforcement/review slot."
        elif topic.review_state in {"needs_review", "source_missing", "ocr_required"}:
            trigger = "needs_review"
            priority = "high" if topic.review_state in {"source_missing", "ocr_required"} else "medium"
            reason = "Topic is blocked or uncertain enough to justify a candidate review slot."
        elif redundancies:
            trigger = "redundancy"
            priority = "medium"
            reason = "Multiple overlapping sources suggest a manual consolidation review."
        else:
            return None
        return StudyCycleReviewSlot(
            review_slot_id=f"review:{topic.topic_id}",
            topic_id=topic.topic_id,
            topic_title=topic.title,
            reason=reason,
            review_trigger=trigger,
            priority_hint=priority,
            confidence=min(1.0, topic.confidence + 0.05),
            reasoning="candidate review slot generated from graph review/coverage state",
            metadata={"gap_ids": [item.gap_id for item in gaps], "redundancy_ids": [item.redundancy_id for item in redundancies]},
        )

    def _gap_slot(self, gap: CurriculumGapReference, *, index: int) -> StudyCycleGapSlot:
        resolution_map = {
            "missing_bibliography_material": "upload_material",
            "uncovered_topic": "resolve_material_gap",
            "missing_document_text": "process_existing_material",
            "ocr_required": "run_ocr_future",
            "ambiguous_reference": "manual_review",
        }
        return StudyCycleGapSlot(
            gap_slot_id=f"gap-slot:{index}:{gap.source_gap_id}",
            source_gap_id=gap.source_gap_id,
            gap_type=gap.gap_type,
            target_title=gap.target_title,
            suggested_resolution=resolution_map.get(gap.gap_type, "manual_review"),
            severity=gap.severity,
            reasoning=gap.reason,
            metadata={"target_id": gap.target_id, "review_state": gap.review_state},
        )

    def _subject_rotation(
        self,
        subject,
        slots: list[StudyCycleTopicSlot],
        *,
        order_index: int,
    ) -> StudyCycleSubjectRotation:
        if not slots:
            return StudyCycleSubjectRotation(
                rotation_id=f"rotation:{subject.subject_id}",
                subject_id=subject.subject_id,
                subject_title=subject.title,
                order_index=order_index,
                suggested_frequency="unavailable",
                intensity_level="blocked_by_material_gap",
                review_need_level="unavailable",
                fatigue_risk="unknown",
                confidence=subject.confidence,
                reasoning="subject has no candidate topic slots available",
            )
        slot_types = [item.slot_type for item in slots]
        weak_count = sum(1 for item in slots if item.slot_type == "weak_topic_resurfacing")
        blocked_count = sum(1 for item in slots if item.slot_type in {"gap_blocked", "ocr_blocked"})
        review_count = sum(1 for item in slots if item.slot_type in {"review_needed", "ambiguous_review", "weak_topic_resurfacing"})
        coverage_mix = {kind: slot_types.count(kind) for kind in sorted(set(slot_types))}
        if blocked_count == len(slots):
            frequency = "unavailable"
            intensity = "blocked_by_material_gap"
            review_need = "unavailable"
            fatigue = "high"
        elif weak_count + blocked_count >= max(1, len(slots) // 2):
            frequency = "high"
            intensity = "high"
            review_need = "high"
            fatigue = "high"
        elif review_count > 0:
            frequency = "medium"
            intensity = "moderate"
            review_need = "medium"
            fatigue = "moderate"
        else:
            frequency = "low"
            intensity = "light"
            review_need = "low"
            fatigue = "low"
        return StudyCycleSubjectRotation(
            rotation_id=f"rotation:{subject.subject_id}",
            subject_id=subject.subject_id,
            subject_title=subject.title,
            order_index=order_index,
            topic_ids=[item.topic_id for item in sorted(slots, key=lambda item: item.order_index)],
            suggested_frequency=frequency,
            intensity_level=intensity,
            coverage_mix=coverage_mix,
            review_need_level=review_need,
            fatigue_risk=fatigue,
            confidence=subject.confidence,
            reasoning="subject rotation derived from candidate topic slot mix and blocking signals",
            metadata={"review_states": sorted({item.review_state for item in slots})},
        )

    def _fatigue_profile(
        self,
        topic_slots: list[StudyCycleTopicSlot],
        rotations: list[StudyCycleSubjectRotation],
    ) -> StudyCycleFatigueProfile:
        high_count = sum(1 for item in topic_slots if item.intensity_level == "high")
        blocked_count = sum(1 for item in topic_slots if item.slot_type in {"gap_blocked", "ocr_blocked"})
        weak_count = sum(1 for item in topic_slots if item.slot_type == "weak_topic_resurfacing")
        if not topic_slots:
            risk = "unknown"
            complexity = "unknown"
        elif blocked_count >= max(1, len(topic_slots) // 2) or high_count >= 3:
            risk = "high"
            complexity = "high"
        elif high_count or weak_count or len(rotations) > 2:
            risk = "moderate"
            complexity = "moderate"
        else:
            risk = "low"
            complexity = "low"
        return StudyCycleFatigueProfile(
            estimated_cycle_load=len(topic_slots),
            high_intensity_topic_count=high_count,
            gap_blocked_count=blocked_count,
            weak_topic_count=weak_count,
            rotation_complexity=complexity,
            fatigue_risk_level=risk,
            reasoning="fatigue profile derived from slot intensity, blocked topics and subject rotation breadth",
            metadata={"subject_rotation_count": len(rotations)},
        )

    def _balance_summary(
        self,
        graph: CurriculumGraph,
        topic_slots: list[StudyCycleTopicSlot],
        review_slots: list[StudyCycleReviewSlot],
        gap_slots: list[StudyCycleGapSlot],
    ) -> StudyCycleBalanceSummary:
        slot_types = [item.slot_type for item in topic_slots]
        covered = sum(1 for item in topic_slots if item.coverage_state == "covered")
        partial = sum(1 for item in topic_slots if item.coverage_state == "partially_covered")
        weak = sum(1 for item in topic_slots if item.coverage_state == "weakly_covered")
        uncovered = sum(1 for item in topic_slots if item.coverage_state == "uncovered")
        if not topic_slots:
            state = "insufficient_graph"
        elif slot_types.count("ocr_blocked") + slot_types.count("gap_blocked") >= max(1, len(topic_slots) // 2):
            state = "material_blocked"
        elif len(gap_slots) > len(topic_slots) // 2:
            state = "gap_heavy"
        elif len(review_slots) >= max(1, len(topic_slots) // 2):
            state = "review_heavy"
        elif covered >= partial + weak + uncovered:
            state = "coverage_heavy"
        else:
            state = "balanced_candidate"
        return StudyCycleBalanceSummary(
            subject_count=len(graph.subjects),
            topic_slot_count=len(topic_slots),
            learn_slot_count=slot_types.count("learn"),
            reinforce_slot_count=slot_types.count("reinforce"),
            review_needed_slot_count=slot_types.count("review_needed") + slot_types.count("weak_topic_resurfacing") + slot_types.count("ambiguous_review"),
            gap_blocked_slot_count=slot_types.count("gap_blocked"),
            ocr_blocked_slot_count=slot_types.count("ocr_blocked"),
            ambiguous_slot_count=slot_types.count("ambiguous_review"),
            covered_topic_count=covered,
            partially_covered_topic_count=partial,
            weak_topic_count=weak,
            uncovered_topic_count=uncovered,
            balance_state=state,
            reasoning="balance summary derived from topic slot distribution, review need and blocking signals",
            metadata={"gap_slot_count": len(gap_slots), "graph_summary": graph.summary.model_dump(mode="json")},
        )

    def _warnings(
        self,
        graph: CurriculumGraph,
        topic_slots: list[StudyCycleTopicSlot],
        gap_slots: list[StudyCycleGapSlot],
        balance_summary: StudyCycleBalanceSummary,
    ) -> list[StudyCycleWarning]:
        warnings: list[StudyCycleWarning] = []
        if graph.summary.ocr_required_count:
            warnings.append(
                StudyCycleWarning(
                    code="ocr_required_topics_present",
                    message="Some candidate topics depend on OCR-blocked materials.",
                    severity="warning",
                )
            )
        if any(item.slot_type == "ambiguous_review" for item in topic_slots):
            warnings.append(
                StudyCycleWarning(
                    code="ambiguous_topics_require_manual_review",
                    message="At least one topic remains ambiguous and should not be scheduled as final truth.",
                    severity="warning",
                )
            )
        if balance_summary.balance_state == "material_blocked":
            warnings.append(
                StudyCycleWarning(
                    code="material_blocked_cycle",
                    message="Large parts of this candidate cycle are blocked by missing text or OCR requirements.",
                    severity="warning",
                )
            )
        if gap_slots and not topic_slots:
            warnings.append(
                StudyCycleWarning(
                    code="gaps_without_slots",
                    message="Only gap remediation was possible because no usable topic slots were produced.",
                    severity="warning",
                )
            )
        return warnings

    def _rationale(
        self,
        graph: CurriculumGraph,
        topic_slots: list[StudyCycleTopicSlot],
        gap_slots: list[StudyCycleGapSlot],
        warnings: list[StudyCycleWarning],
    ) -> StudyCycleRationale:
        reasons = [
            "Subject rotation preserves the candidate graph order instead of replacing the live runtime curriculum.",
            "Weak, partial and ambiguous topics are surfaced as review-oriented candidate slots.",
        ]
        if gap_slots:
            reasons.append("Material and OCR gaps were preserved as blocking/remediation slots instead of being hidden.")
        limitations = [
            "This plan is candidate-only and does not activate live scheduling.",
            "No calendar, no review scheduler and no runtime session composition changes are applied here.",
            "Manual review is still required before trusting blocked or ambiguous areas.",
        ]
        summary = (
            "Candidate study cycle prioritizes reinforcement where coverage exists, review where coverage is weak or partial, "
            "and remediation where materials are blocked or ambiguous."
        )
        confidence = round(sum(item.confidence for item in topic_slots) / len(topic_slots), 4) if topic_slots else 0.0
        return StudyCycleRationale(
            summary=summary,
            reasons=reasons,
            limitations=limitations,
            source_graph_id=graph.graph_id,
            confidence=confidence,
            metadata={"warning_count": len(warnings), "gap_count": len(gap_slots)},
        )
