from __future__ import annotations

from uuid import uuid4

from app.domain.models import LearningPlan, LearningPlanEntry, StudySession
from app.services.content_execution import execute_study_block
from app.services.cognitive_momentum import CognitiveMomentumLayer
from app.services.microtopic_session_composer import MicrotopicSessionComposer
from app.services.pedagogical_observability import PedagogicalObservabilityLayer
from app.services.pedagogical_validation import PedagogicalValidationLayer
from app.services.runtime_traceability import RuntimeTraceabilityLayer
from app.services.session_coherence import SessionCoherenceLayer
from app.services.session_equilibrium import SessionEquilibriumLayer
from app.services.session_export_debug import SessionExportDebugLayer
from app.services.session_narrative import SessionNarrativeLayer
from app.services.session_stability_metrics import SessionStabilityMetricsLayer
from app.services.session_snapshot_diff import SessionSnapshotDiffLayer
from app.services.validation_harness import ValidationHarnessLayer
from app.services.pedagogical_tuning_profiles import PedagogicalTuningProfilesLayer


class SessionManager:
    def __init__(self):
        self._sessions: dict[str, StudySession] = {}
        self._runtime_blocks: dict[str, list[dict]] = {}

    def create_session(self, plan: LearningPlan) -> StudySession:
        session_id = str(uuid4())
        runtime_blocks = self._build_runtime_blocks(plan.entries)
        session = StudySession(
            session_id=session_id,
            entries=plan.entries,
            completed=not runtime_blocks,
        )
        if runtime_blocks:
            self._sync_position(session, runtime_blocks[0])
        self._sessions[session_id] = session
        self._runtime_blocks[session_id] = runtime_blocks
        return session

    def get_session(self, session_id: str) -> StudySession | None:
        return self._sessions.get(session_id)

    def current_block(self, session_id: str) -> dict | None:
        session = self.get_session(session_id)
        if session is None or session.completed:
            return None
        runtime_blocks = self._runtime_blocks.get(session_id, [])
        if not runtime_blocks:
            return None
        index = self._current_runtime_index(session_id)
        if index >= len(runtime_blocks):
            return None
        block = dict(runtime_blocks[index])
        block.pop("_entry_index", None)
        block.pop("_block_index", None)
        block.pop("_question_index", None)
        return block

    def advance(self, session_id: str) -> StudySession | None:
        session = self.get_session(session_id)
        if session is None:
            return None
        if session.completed:
            return session

        runtime_blocks = self._runtime_blocks.get(session_id, [])
        next_index = self._current_runtime_index(session_id) + 1
        if next_index >= len(runtime_blocks):
            session.completed = True
            return session

        self._sync_position(session, runtime_blocks[next_index])
        return session

    def _current_runtime_index(self, session_id: str) -> int:
        session = self._sessions[session_id]
        runtime_blocks = self._runtime_blocks.get(session_id, [])
        for index, block in enumerate(runtime_blocks):
            if (
                block["_entry_index"] == session.current_entry_index
                and block["_block_index"] == session.current_block_index
                and block["_question_index"] == session.current_question_index
            ):
                return index
        return len(runtime_blocks)

    def _sync_position(self, session: StudySession, runtime_block: dict) -> None:
        session.current_entry_index = runtime_block["_entry_index"]
        session.current_block_index = runtime_block["_block_index"]
        session.current_question_index = runtime_block["_question_index"]
        session.completed = False

    def _build_runtime_blocks(self, entries: list[LearningPlanEntry]) -> list[dict]:
        composer = MicrotopicSessionComposer()
        equilibrium = SessionEquilibriumLayer()
        narrative = SessionNarrativeLayer()
        momentum = CognitiveMomentumLayer()
        coherence = SessionCoherenceLayer()
        observability = PedagogicalObservabilityLayer()
        traceability = RuntimeTraceabilityLayer()
        validation = PedagogicalValidationLayer()
        session_stability = SessionStabilityMetricsLayer()
        tuning_profiles = PedagogicalTuningProfilesLayer()
        validation_harness = ValidationHarnessLayer()
        snapshot_diff = SessionSnapshotDiffLayer()
        export_debug = SessionExportDebugLayer()
        candidates = composer.compose(entries)
        entry_index_by_topic = {entry.topic_id: index for index, entry in enumerate(entries)}
        summary_emitted: set[str] = set()
        question_count_by_topic: dict[str, int] = {}
        runtime_blocks: list[dict] = []

        for candidate in candidates:
            entry_index = entry_index_by_topic[candidate.topic_id]
            entry = entries[entry_index]
            if candidate.topic_id not in summary_emitted:
                summary_block = self._summary_block_for_topic(entry, candidate, entry_index=entry_index)
                if summary_block is not None:
                    runtime_blocks.append(summary_block)
                summary_emitted.add(candidate.topic_id)

            runtime_blocks.append(
                self._question_block_for_candidate(
                    entry,
                    candidate,
                    entry_index=entry_index,
                    question_index=question_count_by_topic.get(candidate.topic_id, 0),
                )
            )
            question_count_by_topic[candidate.topic_id] = question_count_by_topic.get(candidate.topic_id, 0) + 1

        runtime_blocks = equilibrium.balance(runtime_blocks)
        runtime_blocks = narrative.annotate(runtime_blocks)
        runtime_blocks = momentum.annotate(runtime_blocks)
        runtime_blocks = coherence.annotate(runtime_blocks)
        runtime_blocks = observability.annotate(runtime_blocks)
        runtime_blocks = traceability.annotate(runtime_blocks)
        runtime_blocks = validation.annotate(runtime_blocks)
        runtime_blocks = session_stability.annotate(runtime_blocks)
        runtime_blocks = tuning_profiles.annotate(runtime_blocks)
        runtime_blocks = validation_harness.annotate(runtime_blocks)
        runtime_blocks = snapshot_diff.annotate(runtime_blocks)
        return export_debug.annotate(runtime_blocks)

    def _summary_block_for_topic(
        self,
        entry: LearningPlanEntry,
        candidate,
        *,
        entry_index: int,
    ) -> dict | None:
        summary_index = next(
            (index for index, block in enumerate(entry.study_blocks) if block.type == "summary"),
            None,
        )
        if summary_index is None:
            return None
        block = entry.study_blocks[summary_index].model_copy(
            update={"selected_microtopic_ids": [candidate.microtopic_id]}
        )
        executed = execute_study_block(block)
        return {
            **executed,
            "topic_title": entry.topic_title,
            "curriculum_role": entry.curriculum_role,
            "review_intensity": entry.review_intensity,
            "_entry_index": entry_index,
            "_block_index": summary_index,
            "_question_index": 0,
        }

    def _question_block_for_candidate(
        self,
        entry: LearningPlanEntry,
        candidate,
        *,
        entry_index: int,
        question_index: int,
    ) -> dict:
        question_block_index = next(
            (index for index, block in enumerate(entry.study_blocks) if block.type == "questions"),
            0,
        )
        question_block = entry.study_blocks[question_block_index].model_copy(
            update={"quantity": 1, "selected_microtopic_ids": [candidate.microtopic_id]}
        )
        executed = execute_study_block(question_block)
        question = executed["questions"][0]
        return {
            "type": "question",
            "topic_id": entry.topic_id,
            "topic_title": entry.topic_title,
            "curriculum_role": entry.curriculum_role,
            "review_intensity": entry.review_intensity,
            "question_id": self._runtime_question_id(
                entry,
                block_index=question_block_index,
                question_index=question_index,
            ),
            "microtopic_id": question.get("microtopic_id"),
            "statement": question["statement"],
            "correct_answer": question["answer"],
            "explanation": question["explanation"],
            "pedagogical_mode": executed.get("pedagogical_mode"),
            "intervention_reason": executed.get("intervention_reason"),
            "explanation_depth": executed.get("explanation_depth"),
            "retrieval_intensity": executed.get("retrieval_intensity"),
            "pedagogical_reasoning": executed.get("pedagogical_reasoning"),
            "pedagogical_breakdown": executed.get("pedagogical_breakdown"),
            "adaptation_reasoning": executed.get("adaptation_reasoning"),
            "intervention_transition_reason": executed.get("intervention_transition_reason"),
            "pedagogical_confidence": executed.get("pedagogical_confidence"),
            "intervention_effectiveness": executed.get("intervention_effectiveness"),
            "pedagogical_stability": executed.get("pedagogical_stability"),
            "stabilization_stage": executed.get("stabilization_stage"),
            "longitudinal_retention": executed.get("longitudinal_retention"),
            "intervention_fatigue": executed.get("intervention_fatigue"),
            "reinforcement_reason": executed.get("reinforcement_reason"),
            "fatigue_reason": executed.get("fatigue_reason"),
            "stabilization_reasoning": executed.get("stabilization_reasoning"),
            "retention_reasoning": executed.get("retention_reasoning"),
            "recovery_signal": executed.get("recovery_signal"),
            "intervention_history_summary": executed.get("intervention_history_summary"),
            "why_this_now": executed.get("why_this_now"),
            "relationship_type": executed.get("relationship_type"),
            "relationship_reason": executed.get("relationship_reason"),
            "conceptual_anchor": executed.get("conceptual_anchor"),
            "prerequisite_signal": executed.get("prerequisite_signal"),
            "conceptual_transition": executed.get("conceptual_transition"),
            "semantic_continuity_reason": executed.get("semantic_continuity_reason"),
            "why_this_before_that": executed.get("why_this_before_that"),
            "cognitive_facets": executed.get("cognitive_facets"),
            "dominant_facet": executed.get("dominant_facet"),
            "facet_reasoning": executed.get("facet_reasoning"),
            "cognitive_dimension": executed.get("cognitive_dimension"),
            "retrieval_dimension": executed.get("retrieval_dimension"),
            "conceptual_dimension": executed.get("conceptual_dimension"),
            "transfer_signal": executed.get("transfer_signal"),
            "reconstruction_signal": executed.get("reconstruction_signal"),
            "recognition_signal": executed.get("recognition_signal"),
            "why_this_facet_now": executed.get("why_this_facet_now"),
            "facet_support_reason": executed.get("facet_support_reason"),
            "cognitive_trajectory": executed.get("cognitive_trajectory"),
            "trajectory_state": executed.get("trajectory_state"),
            "trajectory_reasoning": executed.get("trajectory_reasoning"),
            "consolidation_state": executed.get("consolidation_state"),
            "stabilization_quality": executed.get("stabilization_quality"),
            "false_fluency_signal": executed.get("false_fluency_signal"),
            "reconstruction_fragility": executed.get("reconstruction_fragility"),
            "transfer_fragility": executed.get("transfer_fragility"),
            "longitudinal_consistency": executed.get("longitudinal_consistency"),
            "why_this_trajectory_now": executed.get("why_this_trajectory_now"),
            "trajectory_support_reason": executed.get("trajectory_support_reason"),
            "pedagogical_expression_mode": executed.get("pedagogical_expression_mode"),
            "expression_reasoning": executed.get("expression_reasoning"),
            "readability_adjustment": executed.get("readability_adjustment"),
            "pacing_adjustment": executed.get("pacing_adjustment"),
            "continuity_support": executed.get("continuity_support"),
            "retrieval_framing": executed.get("retrieval_framing"),
            "explanation_density": executed.get("explanation_density"),
            "cognitive_friction_reduction": executed.get("cognitive_friction_reduction"),
            "transition_support_reason": executed.get("transition_support_reason"),
            "why_this_expression_now": executed.get("why_this_expression_now"),
            "cognitive_compression_mode": executed.get("cognitive_compression_mode"),
            "compression_reasoning": executed.get("compression_reasoning"),
            "informational_density": executed.get("informational_density"),
            "contextual_support_level": executed.get("contextual_support_level"),
            "retrieval_compaction": executed.get("retrieval_compaction"),
            "explanatory_expansion": executed.get("explanatory_expansion"),
            "redundancy_adjustment": executed.get("redundancy_adjustment"),
            "prerequisite_support_signal": executed.get("prerequisite_support_signal"),
            "compression_transition_reason": executed.get("compression_transition_reason"),
            "why_this_compression_now": executed.get("why_this_compression_now"),
            "adaptive_signal_state": executed.get("adaptive_signal_state"),
            "consolidation_reasoning": executed.get("consolidation_reasoning"),
            "modulation_overlap": executed.get("modulation_overlap"),
            "reinforcement_convergence": executed.get("reinforcement_convergence"),
            "retrieval_pressure_balance": executed.get("retrieval_pressure_balance"),
            "reconstruction_support_balance": executed.get("reconstruction_support_balance"),
            "pacing_consolidation": executed.get("pacing_consolidation"),
            "stabilization_consolidation": executed.get("stabilization_consolidation"),
            "cognitive_signal_alignment": executed.get("cognitive_signal_alignment"),
            "why_this_consolidation_now": executed.get("why_this_consolidation_now"),
            "pedagogical_observability_state": executed.get("pedagogical_observability_state"),
            "observability_reasoning": executed.get("observability_reasoning"),
            "signal_overlap_density": executed.get("signal_overlap_density"),
            "retrieval_pressure_accumulation": executed.get("retrieval_pressure_accumulation"),
            "compression_support_alignment": executed.get("compression_support_alignment"),
            "scaffold_density": executed.get("scaffold_density"),
            "continuity_stability": executed.get("continuity_stability"),
            "modulation_redundancy": executed.get("modulation_redundancy"),
            "expression_variation_balance": executed.get("expression_variation_balance"),
            "intervention_repetition_signal": executed.get("intervention_repetition_signal"),
            "trajectory_consistency": executed.get("trajectory_consistency"),
            "adaptive_behavior_summary": executed.get("adaptive_behavior_summary"),
            "signal_overlap_reason": executed.get("signal_overlap_reason"),
            "support_density_reason": executed.get("support_density_reason"),
            "retrieval_balance_reason": executed.get("retrieval_balance_reason"),
            "modulation_consistency": executed.get("modulation_consistency"),
            "continuity_observation": executed.get("continuity_observation"),
            "stability_profile": executed.get("stability_profile"),
            "why_this_observation_now": executed.get("why_this_observation_now"),
            "runtime_trace_state": executed.get("runtime_trace_state"),
            "behavioral_trace": executed.get("behavioral_trace"),
            "trace_reasoning": executed.get("trace_reasoning"),
            "signal_contributors": executed.get("signal_contributors"),
            "adaptation_stack": executed.get("adaptation_stack"),
            "runtime_pressure_summary": executed.get("runtime_pressure_summary"),
            "retrieval_density_trace": executed.get("retrieval_density_trace"),
            "support_overlap_trace": executed.get("support_overlap_trace"),
            "continuity_transition_trace": executed.get("continuity_transition_trace"),
            "stabilization_trace": executed.get("stabilization_trace"),
            "modulation_trace": executed.get("modulation_trace"),
            "trace_alignment": executed.get("trace_alignment"),
            "why_this_trace_now": executed.get("why_this_trace_now"),
            "pedagogical_validation_state": executed.get("pedagogical_validation_state"),
            "learning_effect_profile": executed.get("learning_effect_profile"),
            "validation_reasoning": executed.get("validation_reasoning"),
            "retrieval_effectiveness_signal": executed.get("retrieval_effectiveness_signal"),
            "stabilization_quality_signal": executed.get("stabilization_quality_signal"),
            "false_fluency_risk": executed.get("false_fluency_risk"),
            "scaffold_dependency_signal": executed.get("scaffold_dependency_signal"),
            "transfer_stability_signal": executed.get("transfer_stability_signal"),
            "reconstruction_progress_signal": executed.get("reconstruction_progress_signal"),
            "adaptation_overlap_signal": executed.get("adaptation_overlap_signal"),
            "reinforcement_density_signal": executed.get("reinforcement_density_signal"),
            "longitudinal_validation_signal": executed.get("longitudinal_validation_signal"),
            "validation_alignment": executed.get("validation_alignment"),
            "why_this_validation_now": executed.get("why_this_validation_now"),
            "retrieval_family": executed.get("retrieval_family"),
            "support_family": executed.get("support_family"),
            "continuity_family": executed.get("continuity_family"),
            "stabilization_family": executed.get("stabilization_family"),
            "overlap_family": executed.get("overlap_family"),
            "semantic_normalization_reasoning": executed.get("semantic_normalization_reasoning"),
            "runtime_semantic_summary": executed.get("runtime_semantic_summary"),
            "session_stability_state": executed.get("session_stability_state"),
            "session_stability_reasoning": executed.get("session_stability_reasoning"),
            "retrieval_density_metric": executed.get("retrieval_density_metric"),
            "scaffold_load_metric": executed.get("scaffold_load_metric"),
            "continuity_smoothness_metric": executed.get("continuity_smoothness_metric"),
            "reconstruction_pressure_metric": executed.get("reconstruction_pressure_metric"),
            "compression_safety_metric": executed.get("compression_safety_metric"),
            "modulation_convergence_metric": executed.get("modulation_convergence_metric"),
            "stabilization_sustainability_metric": executed.get("stabilization_sustainability_metric"),
            "support_density": executed.get("support_density"),
            "pacing_stability_metric": executed.get("pacing_stability_metric"),
            "cognitive_balance_metric": executed.get("cognitive_balance_metric"),
            "session_pressure_summary": executed.get("session_pressure_summary"),
            "session_stability_summary": executed.get("session_stability_summary"),
            "why_this_session_state": executed.get("why_this_session_state"),
            "pedagogical_tuning_state": executed.get("pedagogical_tuning_state"),
            "tuning_profile_summary": executed.get("tuning_profile_summary"),
            "tuning_reasoning": executed.get("tuning_reasoning"),
            "retrieval_tolerance": executed.get("retrieval_tolerance"),
            "scaffold_sensitivity": executed.get("scaffold_sensitivity"),
            "continuity_smoothing_strength": executed.get("continuity_smoothing_strength"),
            "compression_conservatism": executed.get("compression_conservatism"),
            "reconstruction_support_level": executed.get("reconstruction_support_level"),
            "pacing_relief_sensitivity": executed.get("pacing_relief_sensitivity"),
            "overlap_tolerance": executed.get("overlap_tolerance"),
            "stabilization_threshold": executed.get("stabilization_threshold"),
            "modulation_density_tolerance": executed.get("modulation_density_tolerance"),
            "intervention_rotation_sensitivity": executed.get("intervention_rotation_sensitivity"),
            "why_this_tuning_profile": executed.get("why_this_tuning_profile"),
            "validation_harness_state": executed.get("validation_harness_state"),
            "validation_harness_reasoning": executed.get("validation_harness_reasoning"),
            "retrieval_sustainability_signal": executed.get("retrieval_sustainability_signal"),
            "scaffold_dependency_signal": executed.get("scaffold_dependency_signal"),
            "reconstruction_sustainability_signal": executed.get("reconstruction_sustainability_signal"),
            "transfer_stability_signal": executed.get("transfer_stability_signal"),
            "resurfacing_effectiveness_signal": executed.get("resurfacing_effectiveness_signal"),
            "stabilization_reliability_signal": executed.get("stabilization_reliability_signal"),
            "compression_safety_signal": executed.get("compression_safety_signal"),
            "continuity_sustainability_signal": executed.get("continuity_sustainability_signal"),
            "pacing_sustainability_signal": executed.get("pacing_sustainability_signal"),
            "cognitive_friction_signal": executed.get("cognitive_friction_signal"),
            "adaptive_overlap_signal": executed.get("adaptive_overlap_signal"),
            "pedagogical_balance_signal": executed.get("pedagogical_balance_signal"),
            "validation_confidence": executed.get("validation_confidence"),
            "runtime_validation_summary": executed.get("runtime_validation_summary"),
            "evidence_alignment": executed.get("evidence_alignment"),
            "why_this_validation_state": executed.get("why_this_validation_state"),
            "session_snapshot_state": executed.get("session_snapshot_state"),
            "session_snapshot_summary": executed.get("session_snapshot_summary"),
            "behavioral_diff_state": executed.get("behavioral_diff_state"),
            "behavioral_diff_reasoning": executed.get("behavioral_diff_reasoning"),
            "retrieval_shift": executed.get("retrieval_shift"),
            "scaffold_shift": executed.get("scaffold_shift"),
            "continuity_shift": executed.get("continuity_shift"),
            "pacing_shift": executed.get("pacing_shift"),
            "compression_shift": executed.get("compression_shift"),
            "stabilization_shift": executed.get("stabilization_shift"),
            "overlap_shift": executed.get("overlap_shift"),
            "modulation_shift": executed.get("modulation_shift"),
            "validation_shift": executed.get("validation_shift"),
            "convergence_summary": executed.get("convergence_summary"),
            "divergence_summary": executed.get("divergence_summary"),
            "runtime_behavior_delta": executed.get("runtime_behavior_delta"),
            "why_this_behavioral_diff": executed.get("why_this_behavioral_diff"),
            "session_export_state": executed.get("session_export_state"),
            "runtime_export_summary": executed.get("runtime_export_summary"),
            "pedagogical_runtime_snapshot": executed.get("pedagogical_runtime_snapshot"),
            "validation_snapshot": executed.get("validation_snapshot"),
            "behavioral_diff_snapshot": executed.get("behavioral_diff_snapshot"),
            "runtime_trace_snapshot": executed.get("runtime_trace_snapshot"),
            "stability_snapshot": executed.get("stability_snapshot"),
            "tuning_snapshot": executed.get("tuning_snapshot"),
            "compression_snapshot": executed.get("compression_snapshot"),
            "continuity_snapshot": executed.get("continuity_snapshot"),
            "support_snapshot": executed.get("support_snapshot"),
            "retrieval_snapshot": executed.get("retrieval_snapshot"),
            "reconstruction_snapshot": executed.get("reconstruction_snapshot"),
            "export_reasoning": executed.get("export_reasoning"),
            "export_alignment": executed.get("export_alignment"),
            "export_trace_summary": executed.get("export_trace_summary"),
            "session_coherence_state": executed.get("session_coherence_state"),
            "coherence_reasoning": executed.get("coherence_reasoning"),
            "pacing_transition_reason": executed.get("pacing_transition_reason"),
            "progression_continuity": executed.get("progression_continuity"),
            "coherence_support_reason": executed.get("coherence_support_reason"),
            "framing_stability": executed.get("framing_stability"),
            "cognitive_rhythm": executed.get("cognitive_rhythm"),
            "continuity_smoothing_reason": executed.get("continuity_smoothing_reason"),
            "why_this_transition_now": executed.get("why_this_transition_now"),
            "micro_intervention": executed.get("micro_intervention"),
            "micro_intervention_reason": executed.get("micro_intervention_reason"),
            "cognitive_goal": executed.get("cognitive_goal"),
            "retrieval_support_reason": executed.get("retrieval_support_reason"),
            "conceptual_support_reason": executed.get("conceptual_support_reason"),
            "intervention_transition": executed.get("intervention_transition"),
            "why_this_intervention": executed.get("why_this_intervention"),
            "local_cognitive_strategy": executed.get("local_cognitive_strategy"),
            "intervention_signal": executed.get("intervention_signal"),
            "_entry_index": entry_index,
            "_block_index": question_block_index,
            "_question_index": question_index,
        }

    def _runtime_question_id(
        self,
        entry: LearningPlanEntry,
        *,
        block_index: int,
        question_index: int,
    ) -> str:
        if not entry.question_ids:
            return f"{entry.topic_id}:{block_index}:{question_index}"
        base = entry.question_ids[min(question_index, len(entry.question_ids) - 1)]
        if question_index < len(entry.question_ids):
            return base
        return f"{base}:{block_index}:{question_index}"
