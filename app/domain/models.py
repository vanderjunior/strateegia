from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Self
from uuid import uuid4

from pydantic import BaseModel, Field


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


class BoardStyle(str, Enum):
    FGV = "fgv"
    CEBRASPE = "cebraspe"


class MaterialSourceType(str, Enum):
    USER_UPLOAD = "user_upload"


class DocumentIngestionStatus(str, Enum):
    UPLOADED = "uploaded"
    TYPE_DETECTED = "type_detected"
    PENDING_EXTRACTION = "pending_extraction"
    EXTRACTION_STARTED = "extraction_started"
    EXTRACTED = "extracted"
    CHUNKED = "chunked"
    SECTIONED = "sectioned"
    METADATA_READY = "metadata_ready"
    FAILED = "failed"
    UNSUPPORTED = "unsupported"


class ErrorType(str, Enum):
    KNOWLEDGE_GAP = "knowledge_gap"
    INTERPRETATION = "interpretation"
    DISTRACTION = "distraction"
    CONCEPT_CONFUSION = "concept_confusion"
    MEMORIZATION = "memorization"


class StudyStrategy(str, Enum):
    QUESTIONS = "questions"
    THEORY_REVIEW = "theory_review"
    MIXED = "mixed"
    QUICK_REVIEW = "quick_review"


class PedagogicalMode(str, Enum):
    GUIDED_EXPLANATION = "guided_explanation"
    CONCEPTUAL_REINFORCEMENT = "conceptual_reinforcement"
    CONTEXTUAL_APPLICATION = "contextual_application"
    ACTIVE_RECALL = "active_recall"
    RAPID_REVIEW = "rapid_review"
    REINFORCEMENT_CHECK = "reinforcement_check"


class PedagogicalOutcome(str, Enum):
    EFFECTIVE = "effective"
    NEUTRAL = "neutral"
    INEFFECTIVE = "ineffective"


class RelationshipType(str, Enum):
    PREREQUISITE = "prerequisite"
    REINFORCES = "reinforces"
    EXCEPTION_OF = "exception_of"
    APPLIED_BY = "applied_by"
    CONTRASTS_WITH = "contrasts_with"
    CUMULATIVE_EXTENSION = "cumulative_extension"


class MicroInterventionType(str, Enum):
    RAPID_ANCHOR = "rapid_anchor"
    PREREQUISITE_RECALL = "prerequisite_recall"
    CONTRAST_RECONCILIATION = "contrast_reconciliation"
    CONFIDENCE_CHECK = "confidence_check"
    GUIDED_RECONSTRUCTION = "guided_reconstruction"
    LIGHTWEIGHT_RETRIEVAL = "lightweight_retrieval"
    EXCEPTION_ALIGNMENT = "exception_alignment"
    CUMULATIVE_BRIDGE = "cumulative_bridge"
    VERIFICATION_STEP = "verification_step"
    SEMANTIC_REACTIVATION = "semantic_reactivation"


class MomentumTrend(str, Enum):
    STABLE = "stable"
    CONCEPTUALLY_DENSE = "conceptually_dense"
    RETRIEVAL_HEAVY = "retrieval_heavy"
    CONTINUITY_FRAGILE = "continuity_fragile"
    PRESSURED = "pressured"
    BALANCED = "balanced"


class FacetType(str, Enum):
    DEFINITION = "definition"
    RULE = "rule"
    EXCEPTION = "exception"
    APPLICATION = "application"
    INTERPRETATION = "interpretation"
    RECOGNITION = "recognition"
    RECONSTRUCTION = "reconstruction"
    CONTEXTUAL_TRANSFER = "contextual_transfer"


class ConsolidationState(str, Enum):
    EMERGING = "emerging"
    STABILIZING = "stabilizing"
    UNSTABLE = "unstable"
    SUPERFICIALLY_STABLE = "superficially_stable"
    CONSOLIDATED = "consolidated"
    TRANSFER_FRAGILE = "transfer_fragile"
    RECONSTRUCTION_FRAGILE = "reconstruction_fragile"


class PedagogicalProfile(BaseModel):
    pedagogical_mode: str
    intervention_reason: str
    explanation_depth: str
    retrieval_intensity: str
    reinforcement_level: str
    cognitive_load: str
    cognitive_load_score: float = 0.0
    intervention_transition_reason: str | None = None
    stabilization_signal: float = 0.0
    escalation_signal: float = 0.0
    pedagogical_confidence: float = 0.5
    intervention_effectiveness: str = PedagogicalOutcome.NEUTRAL.value
    pedagogical_stability: str = "adaptive"
    stabilization_stage: str = "unstable"
    longitudinal_retention: float = 0.0
    intervention_fatigue: float = 0.0
    reinforcement_reason: str | None = None
    fatigue_reason: str | None = None
    stabilization_reasoning: list[str] = Field(default_factory=list)
    retention_reasoning: list[str] = Field(default_factory=list)
    recovery_signal: float = 0.0
    cognitive_trajectory: str = ConsolidationState.EMERGING.value
    trajectory_state: str = ConsolidationState.EMERGING.value
    trajectory_reasoning: list[str] = Field(default_factory=list)
    consolidation_state: str = ConsolidationState.EMERGING.value
    stabilization_quality: float = 0.0
    false_fluency_signal: float = 0.0
    reconstruction_fragility: float = 0.0
    transfer_fragility: float = 0.0
    longitudinal_consistency: float = 0.0
    why_this_trajectory_now: str = ""
    trajectory_support_reason: str | None = None
    adaptation_reasoning: list[str] = Field(default_factory=list)
    intervention_history_summary: dict[str, object] = Field(default_factory=dict)
    profile_breakdown: dict[str, float] = Field(default_factory=dict)


class SessionEquilibriumDecision(BaseModel):
    cognitive_load: str
    cognitive_load_score: float = 0.0
    session_density: float = 0.0
    intervention_rotation_pressure: float = 0.0
    equilibrium_pressure: float = 0.0
    pacing_signal: float = 0.0
    cumulative_fatigue_signal: float = 0.0
    equilibrium_reason: str
    pacing_reason: str
    intervention_rotation_reason: str
    density_reason: str
    fatigue_mitigation_reason: str
    why_this_block_now: str


class SessionNarrativeDecision(BaseModel):
    narrative_relation: str
    narrative_role: str
    continuity_signal: float = 0.0
    contextual_anchor: str | None = None
    relationship_type: str | None = None
    relationship_reason: str | None = None
    prerequisite_signal: float = 0.0
    conceptual_transition: str | None = None
    semantic_continuity_reason: str | None = None
    why_this_before_that: str | None = None
    transition_reason: str
    comparison_reason: str | None = None
    recall_reason: str | None = None
    progression_reason: str | None = None
    why_this_after_previous: str


class StudyBlock(BaseModel):
    type: str
    topic_id: str
    quantity: int | None = None
    depth: str | None = None
    curriculum_role: str | None = None
    review_intensity: str | None = None
    topic_node: TopicNode | None = None
    microtopic_performance: dict[str, dict[str, object]] = Field(default_factory=dict)
    pedagogical_memory: dict[str, dict[str, object]] = Field(default_factory=dict)
    selected_microtopic_ids: list[str] = Field(default_factory=list)


class StudySession(BaseModel):
    session_id: str
    user_id: str | None = None
    entries: list["LearningPlanEntry"] = Field(default_factory=list)
    current_entry_index: int = 0
    current_block_index: int = 0
    current_question_index: int = 0
    completed: bool = False


class TopicNode(BaseModel):
    title: str
    level: int
    content: str
    children: list["TopicNode"] = Field(default_factory=list)


class StudyContent(BaseModel):
    source_path: str
    title: str
    topics: list[TopicNode] = Field(default_factory=list)


class MicroTopic(BaseModel):
    id: str
    title: str
    content: str
    source_topic_title: str
    difficulty_weight: float = 1.0


class ConceptualRelationship(BaseModel):
    source_microtopic_id: str
    target_microtopic_id: str
    relationship_type: str
    reason: str
    strength: float = 0.0


class ConceptualAnchor(BaseModel):
    microtopic_id: str
    title: str
    relationship_type: str | None = None


class RelationshipSignal(BaseModel):
    relationship_type: str | None = None
    relationship_reason: str | None = None
    conceptual_anchor: str | None = None
    anchor_microtopic_id: str | None = None
    prerequisite_signal: float = 0.0
    support_signal: float = 0.0
    conceptual_transition: str | None = None
    reinforcement_reason: str | None = None
    semantic_continuity_reason: str | None = None
    why_this_before_that: str | None = None


class InterventionContext(BaseModel):
    block_type: str
    curriculum_role: str
    review_intensity: str
    pedagogical_mode: str
    explanation_depth: str
    retrieval_intensity: str
    stabilization_stage: str
    longitudinal_retention: float = 0.0
    intervention_fatigue: float = 0.0
    relationship_type: str | None = None
    prerequisite_signal: float = 0.0
    conceptual_anchor: str | None = None


class InterventionSignal(BaseModel):
    support_strength: float = 0.0
    retrieval_shift: float = 0.0
    fatigue_mitigation: float = 0.0


class MicroIntervention(BaseModel):
    intervention_type: str
    intervention_reason: str
    cognitive_goal: str
    retrieval_support_reason: str | None = None
    conceptual_support_reason: str | None = None
    intervention_transition: str | None = None
    why_this_intervention: str
    local_cognitive_strategy: str
    intervention_signal: InterventionSignal = Field(default_factory=InterventionSignal)


class FacetSignal(BaseModel):
    transfer_signal: float = 0.0
    reconstruction_signal: float = 0.0
    recognition_signal: float = 0.0


class CognitiveFacet(BaseModel):
    facet_type: str
    strength: float = 0.0
    reason: str


class CognitiveFacetProfile(BaseModel):
    cognitive_facets: list[CognitiveFacet] = Field(default_factory=list)
    dominant_facet: str | None = None
    facet_reasoning: list[str] = Field(default_factory=list)
    cognitive_dimension: str = "general"
    retrieval_dimension: str = "balanced"
    conceptual_dimension: str = "single_focus"
    transfer_signal: float = 0.0
    reconstruction_signal: float = 0.0
    recognition_signal: float = 0.0
    why_this_facet_now: str = ""
    facet_support_reason: str | None = None
    facet_signal: FacetSignal = Field(default_factory=FacetSignal)


class TrajectorySignal(BaseModel):
    stabilization_quality: float = 0.0
    false_fluency_signal: float = 0.0
    reconstruction_fragility: float = 0.0
    transfer_fragility: float = 0.0
    longitudinal_consistency: float = 0.0


class FacetTrajectory(BaseModel):
    facet_type: str
    consolidation_state: str
    strength: float = 0.0
    reason: str


class CognitiveTrajectory(BaseModel):
    cognitive_trajectory: str
    trajectory_state: str
    trajectory_reasoning: list[str] = Field(default_factory=list)
    consolidation_state: str
    stabilization_quality: float = 0.0
    false_fluency_signal: float = 0.0
    reconstruction_fragility: float = 0.0
    transfer_fragility: float = 0.0
    longitudinal_consistency: float = 0.0
    why_this_trajectory_now: str
    trajectory_support_reason: str | None = None
    trajectory_signal: TrajectorySignal = Field(default_factory=TrajectorySignal)
    facet_trajectories: list[FacetTrajectory] = Field(default_factory=list)


class PedagogicalExpressionProfile(BaseModel):
    pedagogical_expression_mode: str
    expression_reasoning: list[str] = Field(default_factory=list)
    readability_adjustment: float = 0.0
    pacing_adjustment: float = 0.0
    continuity_support: float = 0.0
    retrieval_framing: float = 0.0
    explanation_density: float = 0.0
    cognitive_friction_reduction: float = 0.0
    transition_support_reason: str | None = None
    why_this_expression_now: str = ""


class SessionCoherenceDecision(BaseModel):
    session_coherence_state: str
    coherence_reasoning: list[str] = Field(default_factory=list)
    pacing_transition_reason: str
    progression_continuity: float = 0.0
    coherence_support_reason: str | None = None
    framing_stability: float = 0.0
    cognitive_rhythm: float = 0.0
    continuity_smoothing_reason: str | None = None
    why_this_transition_now: str


class CognitiveCompressionProfile(BaseModel):
    cognitive_compression_mode: str
    compression_reasoning: list[str] = Field(default_factory=list)
    informational_density: float = 0.0
    contextual_support_level: float = 0.0
    retrieval_compaction: float = 0.0
    explanatory_expansion: float = 0.0
    redundancy_adjustment: float = 0.0
    prerequisite_support_signal: float = 0.0
    compression_transition_reason: str | None = None
    why_this_compression_now: str = ""


class AdaptiveSignalConsolidationProfile(BaseModel):
    adaptive_signal_state: str
    consolidation_reasoning: list[str] = Field(default_factory=list)
    modulation_overlap: float = 0.0
    reinforcement_convergence: float = 0.0
    retrieval_pressure_balance: float = 0.0
    reconstruction_support_balance: float = 0.0
    pacing_consolidation: float = 0.0
    stabilization_consolidation: float = 0.0
    cognitive_signal_alignment: float = 0.0
    why_this_consolidation_now: str = ""


class PedagogicalObservabilityProfile(BaseModel):
    pedagogical_observability_state: str
    observability_reasoning: list[str] = Field(default_factory=list)
    signal_overlap_density: float = 0.0
    retrieval_pressure_accumulation: float = 0.0
    compression_support_alignment: float = 0.0
    scaffold_density: float = 0.0
    continuity_stability: float = 0.0
    modulation_redundancy: float = 0.0
    expression_variation_balance: float = 0.0
    intervention_repetition_signal: float = 0.0
    trajectory_consistency: float = 0.0
    adaptive_behavior_summary: str = ""
    signal_overlap_reason: str = ""
    support_density_reason: str = ""
    retrieval_balance_reason: str = ""
    modulation_consistency: str = ""
    continuity_observation: str = ""
    stability_profile: str = ""
    why_this_observation_now: str = ""


class RuntimeTraceProfile(BaseModel):
    runtime_trace_state: str
    behavioral_trace: list[str] = Field(default_factory=list)
    trace_reasoning: list[str] = Field(default_factory=list)
    signal_contributors: list[str] = Field(default_factory=list)
    adaptation_stack: list[str] = Field(default_factory=list)
    runtime_pressure_summary: str = ""
    retrieval_density_trace: str = ""
    support_overlap_trace: str = ""
    continuity_transition_trace: str = ""
    stabilization_trace: str = ""
    modulation_trace: str = ""
    trace_alignment: float = 0.0
    why_this_trace_now: str = ""


class PedagogicalValidationProfile(BaseModel):
    pedagogical_validation_state: str
    learning_effect_profile: str = ""
    validation_reasoning: list[str] = Field(default_factory=list)
    retrieval_effectiveness_signal: float = 0.0
    stabilization_quality_signal: float = 0.0
    false_fluency_risk: float = 0.0
    scaffold_dependency_signal: float = 0.0
    transfer_stability_signal: float = 0.0
    reconstruction_progress_signal: float = 0.0
    adaptation_overlap_signal: float = 0.0
    reinforcement_density_signal: float = 0.0
    longitudinal_validation_signal: float = 0.0
    validation_alignment: float = 0.0
    why_this_validation_now: str = ""


class RuntimeSignalNormalizationProfile(BaseModel):
    retrieval_family: str
    support_family: str
    continuity_family: str
    stabilization_family: str
    overlap_family: str
    semantic_normalization_reasoning: list[str] = Field(default_factory=list)
    runtime_semantic_summary: str = ""


class SessionStabilityMetricsProfile(BaseModel):
    session_stability_state: str
    session_stability_reasoning: list[str] = Field(default_factory=list)
    retrieval_density_metric: float = 0.0
    scaffold_load_metric: float = 0.0
    continuity_smoothness_metric: float = 0.0
    reconstruction_pressure_metric: float = 0.0
    compression_safety_metric: float = 0.0
    modulation_convergence_metric: float = 0.0
    stabilization_sustainability_metric: float = 0.0
    support_density: float = 0.0
    pacing_stability_metric: float = 0.0
    cognitive_balance_metric: float = 0.0
    session_pressure_summary: str = ""
    session_stability_summary: str = ""
    why_this_session_state: str = ""


class PedagogicalTuningProfile(BaseModel):
    pedagogical_tuning_state: str
    tuning_profile_summary: str = ""
    tuning_reasoning: list[str] = Field(default_factory=list)
    retrieval_tolerance: float = 0.0
    scaffold_sensitivity: float = 0.0
    continuity_smoothing_strength: float = 0.0
    compression_conservatism: float = 0.0
    reconstruction_support_level: float = 0.0
    pacing_relief_sensitivity: float = 0.0
    overlap_tolerance: float = 0.0
    stabilization_threshold: float = 0.0
    modulation_density_tolerance: float = 0.0
    intervention_rotation_sensitivity: float = 0.0
    why_this_tuning_profile: str = ""


class ValidationHarnessProfile(BaseModel):
    validation_harness_state: str
    validation_harness_reasoning: list[str] = Field(default_factory=list)
    retrieval_sustainability_signal: float = 0.0
    scaffold_dependency_signal: float = 0.0
    reconstruction_sustainability_signal: float = 0.0
    transfer_stability_signal: float = 0.0
    resurfacing_effectiveness_signal: float = 0.0
    stabilization_reliability_signal: float = 0.0
    compression_safety_signal: float = 0.0
    continuity_sustainability_signal: float = 0.0
    pacing_sustainability_signal: float = 0.0
    cognitive_friction_signal: float = 0.0
    adaptive_overlap_signal: float = 0.0
    pedagogical_balance_signal: float = 0.0
    validation_confidence: float = 0.0
    runtime_validation_summary: str = ""
    evidence_alignment: float = 0.0
    why_this_validation_state: str = ""


class ValidationDatasetAwarenessProfile(BaseModel):
    validation_dataset_state: str
    validation_dataset_reasoning: list[str] = Field(default_factory=list)
    pedagogical_scenario_family: str = ""
    retrieval_condition_profile: str = ""
    scaffold_condition_profile: str = ""
    continuity_condition_profile: str = ""
    reconstruction_condition_profile: str = ""
    compression_condition_profile: str = ""
    transfer_condition_profile: str = ""
    stabilization_condition_profile: str = ""
    overlap_condition_profile: str = ""
    pacing_condition_profile: str = ""
    reinforcement_condition_profile: str = ""
    runtime_validation_context: str = ""
    comparative_validation_alignment: float = 0.0
    dataset_awareness_summary: str = ""
    why_this_validation_context: str = ""


class RuntimeBenchmarkProfile(BaseModel):
    runtime_benchmark_state: str
    runtime_benchmark_summary: str = ""
    comparative_runtime_alignment: float = 0.0
    reproducibility_summary: str = ""


class RuntimeRegressionProfile(BaseModel):
    regression_detection_state: str
    pedagogical_regression_summary: str = ""
    overlap_inflation_profile: str = ""
    reinforcement_redundancy_profile: str = ""


class CognitiveSustainabilityProfile(BaseModel):
    sustainability_validation_state: str
    cognitive_load_profile: str = ""
    retrieval_reliability_profile: str = ""
    scaffold_dependency_profile: str = ""
    compression_safety_profile: str = ""
    stabilization_reliability_profile: str = ""
    continuity_reliability_profile: str = ""


class ScientificRuntimeValidationProfile(BaseModel):
    scientific_validation_state: str
    scientific_validation_reasoning: list[str] = Field(default_factory=list)
    runtime_benchmark_state: str = ""
    regression_detection_state: str = ""
    sustainability_validation_state: str = ""
    cognitive_load_profile: str = ""
    retrieval_reliability_profile: str = ""
    scaffold_dependency_profile: str = ""
    compression_safety_profile: str = ""
    overlap_inflation_profile: str = ""
    stabilization_reliability_profile: str = ""
    continuity_reliability_profile: str = ""
    reinforcement_redundancy_profile: str = ""
    pedagogical_regression_summary: str = ""
    runtime_benchmark_summary: str = ""
    empirical_validation_context: str = ""
    comparative_runtime_alignment: float = 0.0
    reproducibility_summary: str = ""
    why_this_validation_profile: str = ""


class ComparativeRuntimeSummary(BaseModel):
    retrieval_level: float = 0.0
    scaffold_level: float = 0.0
    compression_level: float = 0.0
    continuity_level: float = 0.0
    pacing_level: float = 0.0
    reconstruction_level: float = 0.0
    validation_level: float = 0.0
    sustainability_level: float = 0.0
    balance_level: float = 0.0


class SessionComparisonProfile(BaseModel):
    baseline_session_signature: ComparativeRuntimeSummary = Field(default_factory=ComparativeRuntimeSummary)
    candidate_session_signature: ComparativeRuntimeSummary = Field(default_factory=ComparativeRuntimeSummary)
    comparison_context: str = ""


class PedagogicalRegressionSignal(BaseModel):
    retrieval_inflation_risk: float = 0.0
    scaffold_dependency_delta: float = 0.0
    compression_safety_delta: float = 0.0
    continuity_degradation_delta: float = 0.0
    reconstruction_pressure_delta: float = 0.0
    pacing_instability_delta: float = 0.0
    validation_confidence_delta: float = 0.0
    sustainability_delta: float = 0.0
    behavioral_drift_signal: float = 0.0
    pedagogical_regression_signal: str = ""


class ComparativeSessionAnalyticsProfile(BaseModel):
    comparative_session_state: str
    comparative_session_reasoning: list[str] = Field(default_factory=list)
    comparative_runtime_summary: str = ""
    session_comparison_profile: SessionComparisonProfile = Field(default_factory=SessionComparisonProfile)
    baseline_session_signature: dict[str, float] = Field(default_factory=dict)
    candidate_session_signature: dict[str, float] = Field(default_factory=dict)
    retrieval_delta: float = 0.0
    scaffold_delta: float = 0.0
    compression_delta: float = 0.0
    continuity_delta: float = 0.0
    reconstruction_delta: float = 0.0
    pacing_delta: float = 0.0
    validation_delta: float = 0.0
    sustainability_delta: float = 0.0
    behavioral_drift_signal: float = 0.0
    pedagogical_regression_signal: str = ""
    comparative_validation_alignment: float = 0.0
    why_this_comparison_state: str = ""


class ScenarioReplaySnapshot(BaseModel):
    retrieval_level: float = 0.0
    scaffold_level: float = 0.0
    compression_safety: float = 0.0
    reconstruction_pressure: float = 0.0
    transfer_stability: float = 0.0
    continuity_level: float = 0.0
    pacing_stability: float = 0.0
    validation_confidence: float = 0.0
    sustainability_level: float = 0.0
    overlap_level: float = 0.0
    expected_classification: str = ""


class ScenarioExpectation(BaseModel):
    expected_validation_state: str = ""
    expected_dataset_awareness_state: str = ""
    expected_scientific_validation_state: str = ""
    expected_comparative_state: str = ""
    expected_regression_signal: str = ""
    expected_risk_flags: list[str] = Field(default_factory=list)


class RuntimeScenarioProfile(BaseModel):
    scenario_category: str
    scenario_expected_states: ScenarioExpectation = Field(default_factory=ScenarioExpectation)
    scenario_notes: str = ""


class ScenarioValidationOutcome(BaseModel):
    runtime_scenario_state: str
    scenario_validation_outcome: str = ""
    scenario_expectation_alignment: float = 0.0
    scenario_regression_signal: str = ""
    scenario_mismatch_reason: str = ""
    scenario_replay_summary: str = ""
    why_this_scenario_outcome: str = ""


class ScenarioSimulationResult(BaseModel):
    runtime_scenario_state: str
    scenario_simulation_reasoning: list[str] = Field(default_factory=list)
    scenario_category: str = ""
    scenario_replay_snapshot: dict[str, object] = Field(default_factory=dict)
    scenario_expected_states: dict[str, object] = Field(default_factory=dict)
    scenario_observed_states: dict[str, object] = Field(default_factory=dict)
    scenario_expectation_alignment: float = 0.0
    scenario_validation_outcome: str = ""
    scenario_regression_signal: str = ""
    scenario_mismatch_reason: str = ""
    scenario_replay_summary: str = ""
    why_this_scenario_outcome: str = ""


class EmpiricalValidationExpectation(BaseModel):
    expected_scenario_category: str = ""
    expected_validation_state: str = ""
    expected_dataset_awareness_state: str = ""
    expected_scientific_validation_state: str = ""
    expected_comparative_state: str = ""
    expected_regression_signal: str = ""
    expected_risk_flags: list[str] = Field(default_factory=list)
    expected_case_state: str = ""


class EmpiricalValidationCase(BaseModel):
    case_id: str
    case_name: str
    case_category: str
    expected_states: EmpiricalValidationExpectation = Field(default_factory=EmpiricalValidationExpectation)
    case_notes: str = ""


class EmpiricalValidationCaseResult(BaseModel):
    case_id: str
    case_name: str
    case_category: str
    expected_states: dict[str, object] = Field(default_factory=dict)
    observed_states: dict[str, object] = Field(default_factory=dict)
    expectation_alignment: float = 0.0
    case_result_state: str = ""
    case_reasoning: list[str] = Field(default_factory=list)
    mismatch_reasons: list[str] = Field(default_factory=list)
    regression_flags: list[str] = Field(default_factory=list)
    validation_confidence: float = 0.0
    why_this_case_result: str = ""


class EmpiricalValidationDataset(BaseModel):
    dataset_id: str
    dataset_name: str
    cases: list[EmpiricalValidationCase] = Field(default_factory=list)


class EmpiricalValidationDatasetSummary(BaseModel):
    empirical_dataset_state: str
    empirical_dataset_summary: str = ""
    empirical_dataset_reasoning: list[str] = Field(default_factory=list)
    validation_case_results: list[EmpiricalValidationCaseResult] = Field(default_factory=list)
    passed_cases: list[str] = Field(default_factory=list)
    failed_cases: list[str] = Field(default_factory=list)
    inconclusive_cases: list[str] = Field(default_factory=list)
    dataset_alignment_score: float = 0.0
    dataset_regression_flags: list[str] = Field(default_factory=list)
    dataset_coverage_summary: str = ""
    empirical_validation_context: str = ""
    why_this_dataset_result: str = ""


class PedagogicalBenchmarkRun(BaseModel):
    benchmark_id: str
    benchmark_name: str
    dataset_id: str = ""
    dataset_name: str = ""
    case_ids: list[str] = Field(default_factory=list)


class PedagogicalBenchmarkCaseReport(BaseModel):
    case_id: str
    case_name: str
    case_category: str
    case_result_state: str
    expectation_alignment: float = 0.0
    regression_flags: list[str] = Field(default_factory=list)
    validation_confidence: float = 0.0
    benchmark_case_status: str = "inconclusive"
    case_benchmark_summary: str = ""
    case_benchmark_reasoning: list[str] = Field(default_factory=list)


class PedagogicalBenchmarkRegressionReport(BaseModel):
    regression_case_ids: list[str] = Field(default_factory=list)
    regression_flags: list[str] = Field(default_factory=list)
    regression_summary: str = ""
    regression_severity: str = "none"
    regression_reasoning: list[str] = Field(default_factory=list)


class PedagogicalBenchmarkSummary(BaseModel):
    benchmark_total_cases: int = 0
    benchmark_passed_cases: list[str] = Field(default_factory=list)
    benchmark_failed_cases: list[str] = Field(default_factory=list)
    benchmark_inconclusive_cases: list[str] = Field(default_factory=list)
    benchmark_regression_cases: list[str] = Field(default_factory=list)
    benchmark_alignment_score: float = 0.0
    benchmark_coverage_summary: str = ""
    benchmark_readiness: str = "benchmark_insufficient"


class PedagogicalBenchmarkResult(BaseModel):
    benchmark_run: PedagogicalBenchmarkRun
    benchmark_summary_profile: PedagogicalBenchmarkSummary
    regression_report: PedagogicalBenchmarkRegressionReport
    pedagogical_benchmark_state: str
    pedagogical_benchmark_summary: str = ""
    pedagogical_benchmark_reasoning: list[str] = Field(default_factory=list)
    benchmark_case_reports: list[PedagogicalBenchmarkCaseReport] = Field(default_factory=list)
    benchmark_total_cases: int = 0
    benchmark_passed_cases: list[str] = Field(default_factory=list)
    benchmark_failed_cases: list[str] = Field(default_factory=list)
    benchmark_inconclusive_cases: list[str] = Field(default_factory=list)
    benchmark_regression_cases: list[str] = Field(default_factory=list)
    benchmark_regression_flags: list[str] = Field(default_factory=list)
    benchmark_regression_severity: str = "none"
    benchmark_readiness: str = "benchmark_insufficient"
    benchmark_alignment_score: float = 0.0
    benchmark_coverage_summary: str = ""
    why_this_benchmark_result: str = ""


class ControlledTuningDimension(BaseModel):
    dimension_id: str
    current_reference: str = ""
    hypothetical_direction: str = ""
    rationale: str = ""


class ControlledTuningHypothesis(BaseModel):
    hypothesis_id: str
    statement: str
    expected_directional_effects: list[str] = Field(default_factory=list)
    relevant_benchmark_cases: list[str] = Field(default_factory=list)


class ControlledTuningProfile(BaseModel):
    profile_id: str
    profile_name: str
    tuning_dimensions: list[ControlledTuningDimension] = Field(default_factory=list)


class ControlledTuningExperiment(BaseModel):
    experiment_id: str
    experiment_name: str
    experiment_category: str
    experiment_description: str = ""
    tuning_dimensions: list[ControlledTuningDimension] = Field(default_factory=list)
    hypothesis: ControlledTuningHypothesis
    expected_directional_effects: list[str] = Field(default_factory=list)
    relevant_benchmark_cases: list[str] = Field(default_factory=list)
    risk_level: str = "low"
    read_only: bool = True
    executable: bool = False
    experiment_reasoning: list[str] = Field(default_factory=list)


class ControlledTuningExperimentRegistry(BaseModel):
    tuning_experiment_registry_state: str
    tuning_experiment_registry_summary: str = ""
    tuning_experiments: list[ControlledTuningExperiment] = Field(default_factory=list)
    total_experiments: int = 0
    read_only_experiments: int = 0
    executable_experiments: int = 0
    experiment_categories: list[str] = Field(default_factory=list)
    benchmark_case_coverage: dict[str, list[str]] = Field(default_factory=dict)
    experiment_risk_summary: dict[str, int] = Field(default_factory=dict)
    why_this_registry_state: str = ""


class TuningProfileCoverageReport(BaseModel):
    covered_benchmark_cases: list[str] = Field(default_factory=list)
    uncovered_priority_cases: list[str] = Field(default_factory=list)
    coverage_count: int = 0
    coverage_family_summary: str = ""


class TuningProfileRiskTradeoff(BaseModel):
    expected_benefits: list[str] = Field(default_factory=list)
    expected_risks: list[str] = Field(default_factory=list)
    possible_tradeoffs: list[str] = Field(default_factory=list)
    affected_runtime_dimensions: list[str] = Field(default_factory=list)


class TuningProfileBenchmarkAlignment(BaseModel):
    alignment_state: str = ""
    covered_regression_sensitive_cases: list[str] = Field(default_factory=list)
    benchmark_available: bool = False
    alignment_reasoning: list[str] = Field(default_factory=list)


class TuningProfileComparisonResult(BaseModel):
    experiment_id: str
    experiment_name: str
    comparison_state: str
    covered_benchmark_cases: list[str] = Field(default_factory=list)
    uncovered_priority_cases: list[str] = Field(default_factory=list)
    shared_benchmark_cases: list[str] = Field(default_factory=list)
    shared_tuning_dimensions: list[str] = Field(default_factory=list)
    expected_benefits: list[str] = Field(default_factory=list)
    expected_risks: list[str] = Field(default_factory=list)
    possible_tradeoffs: list[str] = Field(default_factory=list)
    profile_overlap_signal: float = 0.0
    coverage_gap_signal: float = 0.0
    benchmark_alignment: TuningProfileBenchmarkAlignment = Field(default_factory=TuningProfileBenchmarkAlignment)
    profile_candidate_reasoning: list[str] = Field(default_factory=list)
    why_this_profile_state: str = ""
    read_only: bool = True
    executable: bool = False


class TuningProfileBenchmarkComparison(BaseModel):
    tuning_profile_comparison_state: str
    tuning_profile_comparison_summary: str = ""
    tuning_profile_comparison_reasoning: list[str] = Field(default_factory=list)
    profile_comparison_results: list[TuningProfileComparisonResult] = Field(default_factory=list)
    total_profiles_compared: int = 0
    high_coverage_profiles: list[str] = Field(default_factory=list)
    redundant_profiles: list[str] = Field(default_factory=list)
    complementary_profiles: list[str] = Field(default_factory=list)
    tradeoff_sensitive_profiles: list[str] = Field(default_factory=list)
    uncovered_benchmark_cases: list[str] = Field(default_factory=list)
    profile_overlap_summary: str = ""
    benchmark_case_coverage_summary: dict[str, list[str]] = Field(default_factory=dict)
    comparison_readiness: str = "comparison_insufficient"
    why_this_tuning_profile_comparison: str = ""


class ManualExperimentCautionFlag(BaseModel):
    flag_id: str
    flag_summary: str = ""
    affected_profiles: list[str] = Field(default_factory=list)
    reasoning: list[str] = Field(default_factory=list)


class ManualExperimentRecommendation(BaseModel):
    experiment_id: str
    decision_state: str
    candidate_readiness: str = ""
    reasoning: list[str] = Field(default_factory=list)


class ManualExperimentDecisionSummary(BaseModel):
    decision_state: str
    decision_summary: str = ""
    recommended_profiles: list[str] = Field(default_factory=list)
    blocked_profiles: list[str] = Field(default_factory=list)
    caution_flags: list[str] = Field(default_factory=list)


class ManualExperimentInspectionItem(BaseModel):
    experiment_id: str
    experiment_name: str
    manual_inspection_state: str
    candidate_status: str = ""
    candidate_reasoning: list[str] = Field(default_factory=list)
    caution_flags: list[str] = Field(default_factory=list)
    readiness_blockers: list[str] = Field(default_factory=list)
    benchmark_case_coverage: list[str] = Field(default_factory=list)
    overlap_summary: str = ""
    tradeoff_summary: str = ""
    manual_review_summary: str = ""
    recommendation: ManualExperimentRecommendation | None = None
    caution_flag_details: list[ManualExperimentCautionFlag] = Field(default_factory=list)
    why_this_candidate_status: str = ""
    read_only: bool = True
    executable: bool = False


class ManualExperimentInspectionProfile(BaseModel):
    manual_experiment_inspection_state: str
    manual_experiment_inspection_summary: str = ""
    manual_experiment_inspection_reasoning: list[str] = Field(default_factory=list)
    promising_candidate_profiles: list[str] = Field(default_factory=list)
    redundant_profiles: list[str] = Field(default_factory=list)
    tradeoff_sensitive_profiles: list[str] = Field(default_factory=list)
    low_coverage_profiles: list[str] = Field(default_factory=list)
    not_ready_profiles: list[str] = Field(default_factory=list)
    caution_flags: list[str] = Field(default_factory=list)
    caution_flag_details: list[ManualExperimentCautionFlag] = Field(default_factory=list)
    manual_decision_summary: ManualExperimentDecisionSummary = Field(
        default_factory=lambda: ManualExperimentDecisionSummary(decision_state="inspection_inconclusive")
    )
    inspection_readiness: str = "inspection_insufficient"
    experiment_review_items: list[ManualExperimentInspectionItem] = Field(default_factory=list)
    why_this_manual_inspection_state: str = ""


class RetentionSignalProfile(BaseModel):
    retention_durability_state: str = "insufficient_evidence"
    retention_durability_signal: float = 0.0
    resurfacing_effectiveness_state: str = "not_enough_cycles"
    resurfacing_effectiveness_signal: float = 0.0
    reconstruction_retention_state: str = "reconstruction_insufficient_evidence"
    reconstruction_retention_signal: float = 0.0
    transfer_retention_state: str = "transfer_insufficient_evidence"
    transfer_retention_signal: float = 0.0


class RetentionRecoveryProfile(BaseModel):
    recovery_state: str = "recovery_insufficient_evidence"
    recovery_signal: float = 0.0
    recovery_reasoning: list[str] = Field(default_factory=list)


class RetentionRiskProfile(BaseModel):
    false_fluency_retention_risk: float = 0.0
    superficial_stability_signal: float = 0.0
    retention_risk_flags: list[str] = Field(default_factory=list)


class RetentionStabilitySummary(BaseModel):
    longitudinal_retention_state: str = "retention_insufficient_evidence"
    longitudinal_retention_summary: str = ""
    longitudinal_retention_reasoning: list[str] = Field(default_factory=list)
    retention_evidence_level: str = "insufficient"
    retention_confidence_indicator: float = 0.0
    why_this_retention_state: str = ""


class RetentionObservabilitySummary(BaseModel):
    reconstruction_retention_reasoning: list[str] = Field(default_factory=list)
    transfer_retention_reasoning: list[str] = Field(default_factory=list)
    retention_durability_reasoning: list[str] = Field(default_factory=list)


class LongitudinalRetentionProfile(BaseModel):
    longitudinal_retention_state: str
    longitudinal_retention_summary: str = ""
    longitudinal_retention_reasoning: list[str] = Field(default_factory=list)
    retention_durability_state: str = "insufficient_evidence"
    retention_durability_signal: float = 0.0
    resurfacing_effectiveness_state: str = "not_enough_cycles"
    resurfacing_effectiveness_signal: float = 0.0
    recovery_state: str = "recovery_insufficient_evidence"
    recovery_signal: float = 0.0
    recovery_reasoning: list[str] = Field(default_factory=list)
    reconstruction_retention_state: str = "reconstruction_insufficient_evidence"
    reconstruction_retention_signal: float = 0.0
    reconstruction_retention_reasoning: list[str] = Field(default_factory=list)
    transfer_retention_state: str = "transfer_insufficient_evidence"
    transfer_retention_signal: float = 0.0
    transfer_retention_reasoning: list[str] = Field(default_factory=list)
    false_fluency_retention_risk: float = 0.0
    superficial_stability_signal: float = 0.0
    retention_risk_flags: list[str] = Field(default_factory=list)
    retention_evidence_level: str = "insufficient"
    retention_confidence_indicator: float = 0.0
    retention_signal_profile: RetentionSignalProfile = Field(default_factory=RetentionSignalProfile)
    retention_recovery_profile: RetentionRecoveryProfile = Field(default_factory=RetentionRecoveryProfile)
    retention_risk_profile: RetentionRiskProfile = Field(default_factory=RetentionRiskProfile)
    retention_stability_summary: RetentionStabilitySummary = Field(default_factory=RetentionStabilitySummary)
    retention_observability_summary: RetentionObservabilitySummary = Field(
        default_factory=RetentionObservabilitySummary
    )
    why_this_retention_state: str = ""


class AggregateRetentionMetric(BaseModel):
    metric_name: str
    metric_value: float = 0.0
    interpretation: str = ""


class RetentionCohortSummary(BaseModel):
    cohort_name: str
    count: int = 0
    ratio: float = 0.0


class AggregateRetentionPopulationSummary(BaseModel):
    total_microtopics_observed: int = 0
    durable_microtopics_count: int = 0
    emerging_microtopics_count: int = 0
    fragile_microtopics_count: int = 0
    superficial_microtopics_count: int = 0
    insufficient_evidence_count: int = 0
    false_fluency_count: int = 0
    resurfacing_effective_count: int = 0
    resurfacing_inconclusive_count: int = 0
    resurfacing_ineffective_count: int = 0
    no_resurfacing_evidence_count: int = 0
    recovery_improving_count: int = 0
    recovery_stalled_count: int = 0
    recovery_unstable_count: int = 0
    recovery_insufficient_evidence_count: int = 0
    reconstruction_fragile_count: int = 0
    reconstruction_durable_count: int = 0
    reconstruction_improving_count: int = 0
    transfer_fragile_count: int = 0
    transfer_durable_count: int = 0
    transfer_improving_count: int = 0
    retention_population_reasoning: list[str] = Field(default_factory=list)
    cohorts: list[RetentionCohortSummary] = Field(default_factory=list)


class TopicRetentionRiskSummary(BaseModel):
    topic_id: str
    observed_microtopics: int = 0
    durable_count: int = 0
    fragile_count: int = 0
    superficial_count: int = 0
    insufficient_evidence_count: int = 0
    false_fluency_count: int = 0
    risk_flags: list[str] = Field(default_factory=list)
    topic_retention_state: str = "topic_retention_insufficient_evidence"
    topic_retention_reasoning: list[str] = Field(default_factory=list)


class AggregateRetentionRiskProfile(BaseModel):
    aggregate_retention_risk_flags: list[str] = Field(default_factory=list)
    aggregate_false_fluency_risk: float = 0.0
    aggregate_resurfacing_failure_risk: float = 0.0
    aggregate_reconstruction_decay_risk: float = 0.0
    aggregate_transfer_decay_risk: float = 0.0
    aggregate_unstable_recovery_risk: float = 0.0
    aggregate_superficial_stabilization_risk: float = 0.0
    aggregate_topic_risk_concentration: float = 0.0


class AggregateRetentionEvidenceSummary(BaseModel):
    aggregate_retention_evidence_state: str = "evidence_insufficient"
    aggregate_retention_evidence_reasoning: list[str] = Field(default_factory=list)
    evidence_coverage_ratio: float = 0.0
    observed_with_attempts: int = 0
    observed_with_timestamps: int = 0
    observed_with_resurfacing_cycles: int = 0
    observed_with_retention_evidence: int = 0


class AggregateRetentionProfile(BaseModel):
    aggregate_retention_state: str
    aggregate_retention_summary: str = ""
    aggregate_retention_reasoning: list[str] = Field(default_factory=list)
    retention_population_summary: AggregateRetentionPopulationSummary = Field(
        default_factory=AggregateRetentionPopulationSummary
    )
    topic_retention_risk_summary: list[TopicRetentionRiskSummary] = Field(default_factory=list)
    aggregate_retention_risk_profile: AggregateRetentionRiskProfile = Field(
        default_factory=AggregateRetentionRiskProfile
    )
    aggregate_retention_evidence_summary: AggregateRetentionEvidenceSummary = Field(
        default_factory=AggregateRetentionEvidenceSummary
    )
    aggregate_resurfacing_state: str = "aggregate_resurfacing_insufficient_evidence"
    aggregate_recovery_state: str = "aggregate_recovery_insufficient_evidence"
    aggregate_reconstruction_state: str = "aggregate_reconstruction_insufficient_evidence"
    aggregate_transfer_state: str = "aggregate_transfer_insufficient_evidence"
    aggregate_retention_metrics: list[AggregateRetentionMetric] = Field(default_factory=list)
    aggregate_retention_risk_flags: list[str] = Field(default_factory=list)
    total_microtopics_observed: int = 0
    durable_microtopics_count: int = 0
    fragile_microtopics_count: int = 0
    superficial_microtopics_count: int = 0
    insufficient_evidence_count: int = 0
    false_fluency_count: int = 0
    evidence_coverage_ratio: float = 0.0
    durable_ratio: float = 0.0
    fragile_ratio: float = 0.0
    superficial_ratio: float = 0.0
    why_this_aggregate_retention_state: str = ""


class OfflineSnapshotMetadata(BaseModel):
    schema_version: str = ""
    export_kind: str = ""
    exported_at: str = ""
    source: str = ""
    inspection_available: bool = False
    snapshot_id: str = ""
    payload_keys: list[str] = Field(default_factory=list)


class OfflineSnapshotEnvelope(BaseModel):
    schema_version: str
    export_kind: str
    exported_at: str = ""
    source: str = ""
    inspection_available: bool = False
    snapshot_id: str = ""
    snapshot_payload: dict[str, object] = Field(default_factory=dict)
    payload_keys: list[str] = Field(default_factory=list)
    validation_state: str = "snapshot_invalid"
    export_reasoning: list[str] = Field(default_factory=list)


class OfflineSnapshotValidationResult(BaseModel):
    validation_state: str
    schema_version: str = ""
    missing_required_keys: list[str] = Field(default_factory=list)
    present_keys: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    is_valid: bool = False
    validation_reasoning: list[str] = Field(default_factory=list)


class OfflineSnapshotImportResult(BaseModel):
    import_state: str
    imported_payload: dict[str, object] = Field(default_factory=dict)
    snapshot_metadata: OfflineSnapshotMetadata = Field(default_factory=OfflineSnapshotMetadata)
    validation: OfflineSnapshotValidationResult = Field(
        default_factory=lambda: OfflineSnapshotValidationResult(validation_state="snapshot_invalid")
    )
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    import_reasoning: list[str] = Field(default_factory=list)


class OfflineSnapshotExportResult(BaseModel):
    export_state: str
    snapshot_envelope: OfflineSnapshotEnvelope
    snapshot_metadata: OfflineSnapshotMetadata
    validation: OfflineSnapshotValidationResult
    warnings: list[str] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)
    export_reasoning: list[str] = Field(default_factory=list)


class OfflineSnapshotMetricDelta(BaseModel):
    path: str
    baseline_value: float | None = None
    candidate_value: float | None = None
    delta: float | None = None
    delta_direction: str = "unavailable"
    interpretation: str = ""


class OfflineSnapshotDeltaSummary(BaseModel):
    path: str
    baseline_value: object | None = None
    candidate_value: object | None = None
    delta_state: str = "unavailable"
    added_items: list[str] = Field(default_factory=list)
    removed_items: list[str] = Field(default_factory=list)
    shared_items: list[str] = Field(default_factory=list)
    changed_keys: list[str] = Field(default_factory=list)
    interpretation: str = ""


class OfflineSnapshotRegressionSignal(BaseModel):
    signal_name: str
    signal_state: str = "not_detected"
    severity: str = "none"
    reasoning: list[str] = Field(default_factory=list)


class OfflineSnapshotComparisonInput(BaseModel):
    baseline_snapshot_id: str = ""
    candidate_snapshot_id: str = ""
    baseline_schema_version: str = ""
    candidate_schema_version: str = ""
    baseline_import_state: str = ""
    candidate_import_state: str = ""


class OfflineSnapshotComparisonSummary(BaseModel):
    total_metric_deltas: int = 0
    total_state_changes: int = 0
    total_list_changes: int = 0
    total_regression_signals: int = 0
    comparison_confidence: float = 0.0
    comparison_limitations: list[str] = Field(default_factory=list)


class OfflineSnapshotComparisonResult(BaseModel):
    offline_comparison_state: str
    offline_comparison_summary: str = ""
    offline_comparison_reasoning: list[str] = Field(default_factory=list)
    comparison_input: OfflineSnapshotComparisonInput = Field(default_factory=OfflineSnapshotComparisonInput)
    comparison_summary: OfflineSnapshotComparisonSummary = Field(default_factory=OfflineSnapshotComparisonSummary)
    baseline_snapshot_id: str = ""
    candidate_snapshot_id: str = ""
    baseline_schema_version: str = ""
    candidate_schema_version: str = ""
    metric_deltas: list[OfflineSnapshotMetricDelta] = Field(default_factory=list)
    state_deltas: list[OfflineSnapshotDeltaSummary] = Field(default_factory=list)
    list_deltas: list[OfflineSnapshotDeltaSummary] = Field(default_factory=list)
    regression_signals: list[OfflineSnapshotRegressionSignal] = Field(default_factory=list)
    added_payload_keys: list[str] = Field(default_factory=list)
    removed_payload_keys: list[str] = Field(default_factory=list)
    shared_payload_keys: list[str] = Field(default_factory=list)
    comparison_confidence: float = 0.0
    comparison_limitations: list[str] = Field(default_factory=list)
    why_this_offline_comparison_state: str = ""


class SessionSnapshotProfile(BaseModel):
    session_snapshot_state: str
    session_snapshot_summary: str = ""
    retrieval_density: float = 0.0
    scaffold_load: float = 0.0
    continuity_smoothness: float = 0.0
    reconstruction_pressure: float = 0.0
    compression_safety: float = 0.0
    modulation_overlap: float = 0.0
    stabilization_sustainability: float = 0.0
    pacing_stability: float = 0.0
    cognitive_balance: float = 0.0
    support_density: float = 0.0
    adaptive_overlap: float = 0.0
    validation_confidence: float = 0.0


class BehavioralDiffProfile(BaseModel):
    behavioral_diff_state: str
    behavioral_diff_reasoning: list[str] = Field(default_factory=list)
    retrieval_shift: float = 0.0
    scaffold_shift: float = 0.0
    continuity_shift: float = 0.0
    pacing_shift: float = 0.0
    compression_shift: float = 0.0
    stabilization_shift: float = 0.0
    overlap_shift: float = 0.0
    modulation_shift: float = 0.0
    validation_shift: float = 0.0
    convergence_summary: str = ""
    divergence_summary: str = ""
    runtime_behavior_delta: float = 0.0
    why_this_behavioral_diff: str = ""


class SessionExportSnapshot(BaseModel):
    session_export_state: str
    runtime_export_summary: str = ""
    pedagogical_runtime_snapshot: dict[str, object] = Field(default_factory=dict)
    validation_snapshot: dict[str, object] = Field(default_factory=dict)
    behavioral_diff_snapshot: dict[str, object] = Field(default_factory=dict)
    runtime_trace_snapshot: dict[str, object] = Field(default_factory=dict)
    stability_snapshot: dict[str, object] = Field(default_factory=dict)
    tuning_snapshot: dict[str, object] = Field(default_factory=dict)
    compression_snapshot: dict[str, object] = Field(default_factory=dict)
    continuity_snapshot: dict[str, object] = Field(default_factory=dict)
    support_snapshot: dict[str, object] = Field(default_factory=dict)
    retrieval_snapshot: dict[str, object] = Field(default_factory=dict)
    reconstruction_snapshot: dict[str, object] = Field(default_factory=dict)
    export_reasoning: list[str] = Field(default_factory=list)
    export_alignment: float = 0.0
    export_trace_summary: str = ""


class RuntimeDebugEntry(BaseModel):
    block_type: str
    topic_id: str = ""
    state_labels: list[str] = Field(default_factory=list)
    signal_families: dict[str, str] = Field(default_factory=dict)
    primary_summary: str = ""


class BehavioralDiffExport(BaseModel):
    behavioral_diff_state: str
    retrieval_shift: float = 0.0
    scaffold_shift: float = 0.0
    continuity_shift: float = 0.0
    pacing_shift: float = 0.0
    compression_shift: float = 0.0
    stabilization_shift: float = 0.0
    overlap_shift: float = 0.0
    modulation_shift: float = 0.0
    validation_shift: float = 0.0
    convergence_summary: str = ""
    divergence_summary: str = ""
    runtime_behavior_delta: float = 0.0
    why_this_behavioral_diff: str = ""


class SessionInspectionSummary(BaseModel):
    dominant_runtime_pressures: list[str] = Field(default_factory=list)
    dominant_runtime_states: list[str] = Field(default_factory=list)
    validation_confidence: float = 0.0
    inspection_summary: str = ""


class CognitiveMomentumSignal(BaseModel):
    conceptual_density: float = 0.0
    abstraction_load: float = 0.0
    retrieval_fatigue: float = 0.0
    intervention_fatigue: float = 0.0
    continuity_stability: float = 0.0
    stabilization_balance: float = 0.0
    cognitive_pressure: float = 0.0
    resurfacing_balance: float = 0.0


class SessionCognitiveSnapshot(BaseModel):
    state_label: str
    window_size: int = 0
    heavy_block_count: int = 0
    retrieval_heavy_count: int = 0
    continuity_average: float = 0.0


class CognitiveMomentumState(BaseModel):
    cognitive_momentum: str
    momentum_signal: CognitiveMomentumSignal = Field(default_factory=CognitiveMomentumSignal)
    conceptual_density_reason: str
    retrieval_fatigue_reason: str
    continuity_pressure_reason: str
    stabilization_balance_reason: str
    pacing_relief_reason: str
    why_this_relief_now: str
    cognitive_session_state: SessionCognitiveSnapshot
    local_momentum_reasoning: list[str] = Field(default_factory=list)


class Topic(BaseModel):
    id: str
    title: str
    content: str
    key_points: list[str] = Field(default_factory=list)
    trap_points: list[str] = Field(default_factory=list)
    relevance_score: float = 0.0
    source_pages: list[int] = Field(default_factory=list)


class TopicSummary(BaseModel):
    topic_id: str
    title: str
    structured_summary: str
    key_points: list[str] = Field(default_factory=list)
    trap_points: list[str] = Field(default_factory=list)


class GeneratedQuestion(BaseModel):
    id: str
    document_id: str
    topic_id: str
    microtopic_id: str | None = None
    style: str
    stem: str
    options: list[str]
    correct_answer: str
    explanation: str
    difficulty_level: int = 1
    similarity_group: str | None = None


class Document(BaseModel):
    id: str
    title: str
    source_filename: str
    board: BoardStyle
    exam_context: str
    source_excerpt: str
    topics: list[Topic] = Field(default_factory=list)
    summaries: list[TopicSummary] = Field(default_factory=list)
    questions: list[GeneratedQuestion] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)

    @classmethod
    def create(
        cls,
        *,
        title: str,
        source_filename: str,
        board: BoardStyle,
        exam_context: str,
        source_excerpt: str,
        topics: list[Topic],
        summaries: list[TopicSummary],
        questions: list[GeneratedQuestion],
    ) -> Self:
        return cls(
            id=str(uuid4()),
            title=title,
            source_filename=source_filename,
            board=board,
            exam_context=exam_context,
            source_excerpt=source_excerpt,
            topics=topics,
            summaries=summaries,
            questions=questions,
        )


class User(BaseModel):
    user_id: str
    username: str
    email: str | None = None
    display_name: str
    password_hash: str
    created_at: datetime = Field(default_factory=utc_now)
    last_login_at: datetime | None = None
    is_active: bool = True


class DocumentMetadata(BaseModel):
    document_id: str
    user_id: str | None = None
    filename: str
    original_filename: str
    content_type: str = ""
    size_bytes: int = 0
    storage_path: str = ""
    source_type: str = MaterialSourceType.USER_UPLOAD.value
    status: str = DocumentIngestionStatus.UPLOADED.value
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    extraction_status: str = DocumentIngestionStatus.UPLOADED.value
    metadata: dict[str, object] = Field(default_factory=dict)
    error_message: str | None = None


class UploadedMaterial(BaseModel):
    metadata: DocumentMetadata
    extracted_text: str | None = None


class DocumentProcessingError(BaseModel):
    code: str
    message: str
    stage: str
    recoverable: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class PdfTextExtractionResult(BaseModel):
    text: str | None = None
    page_count: int = 0
    pages_extracted: int = 0
    extraction_method: str = ""
    warnings: list[str] = Field(default_factory=list)
    errors: list[DocumentProcessingError] = Field(default_factory=list)
    requires_ocr: bool = False
    extraction_status: str = DocumentIngestionStatus.PENDING_EXTRACTION.value


class OcrPageResult(BaseModel):
    page_index: int = 0
    text: str | None = None
    confidence: float = 0.0
    status: str = "ocr_required"
    warnings: list[str] = Field(default_factory=list)
    errors: list[DocumentProcessingError] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class OcrExtractionResult(BaseModel):
    text: str | None = None
    page_count: int = 0
    pages_attempted: int = 0
    pages_succeeded: int = 0
    pages_failed: int = 0
    requires_ocr: bool = True
    ocr_attempted: bool = False
    ocr_available: bool = False
    ocr_enabled: bool = False
    ocr_engine: str = "tesseract"
    ocr_language: str = "por+eng"
    extraction_method: str = "ocr_unavailable"
    extraction_status: str = "ocr_required"
    warnings: list[str] = Field(default_factory=list)
    errors: list[DocumentProcessingError] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class EditalExtractionWarning(BaseModel):
    code: str
    message: str
    severity: str = "info"
    source_section_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class EditalSectionCandidate(BaseModel):
    section_id: str
    title: str
    normalized_title: str
    section_type: str = "unknown"
    order_index: int = 0
    source_chunk_ids: list[str] = Field(default_factory=list)
    text_excerpt: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class EditalTopicCandidate(BaseModel):
    topic_id: str
    title: str
    normalized_title: str
    subject_hint: str | None = None
    parent_section_id: str | None = None
    order_index: int = 0
    source_chunk_ids: list[str] = Field(default_factory=list)
    source_excerpt: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class EditalSubtopicCandidate(BaseModel):
    subtopic_id: str
    parent_topic_id: str
    title: str
    normalized_title: str
    order_index: int = 0
    source_chunk_ids: list[str] = Field(default_factory=list)
    source_excerpt: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class EditalBibliographyCandidate(BaseModel):
    bibliography_id: str
    title: str = ""
    authors: list[str] = Field(default_factory=list)
    publisher: str | None = None
    edition: str | None = None
    year: str | None = None
    raw_reference: str
    source_section_id: str | None = None
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class EditalExclusionCandidate(BaseModel):
    exclusion_id: str
    text: str
    normalized_text: str
    source_section_id: str | None = None
    source_excerpt: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class EditalWeightHint(BaseModel):
    weight_id: str
    target_type: str = "section"
    target_id: str | None = None
    target_title: str = ""
    weight_type: str = "unknown"
    value: float = 0.0
    raw_text: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class EditalIngestionEvent(BaseModel):
    event_id: str
    edital_id: str
    document_id: str
    user_id: str | None = None
    stage: str
    status: str
    message: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class EditalExtractionResult(BaseModel):
    edital_id: str
    document_id: str
    user_id: str | None = None
    source_text_length: int = 0
    sections: list[EditalSectionCandidate] = Field(default_factory=list)
    topics: list[EditalTopicCandidate] = Field(default_factory=list)
    subtopics: list[EditalSubtopicCandidate] = Field(default_factory=list)
    bibliography: list[EditalBibliographyCandidate] = Field(default_factory=list)
    exclusions: list[EditalExclusionCandidate] = Field(default_factory=list)
    weight_hints: list[EditalWeightHint] = Field(default_factory=list)
    warnings: list[EditalExtractionWarning] = Field(default_factory=list)
    confidence_summary: dict[str, object] = Field(default_factory=dict)
    extraction_method: str = "heuristic_edital_ingestion"
    ingestion_version: str = "edital-ingestion-v1"
    metadata: dict[str, object] = Field(default_factory=dict)


class EditalIngestionState(BaseModel):
    edital_id: str
    document_id: str
    user_id: str | None = None
    current_stage: str = "pending"
    status: str = "pending"
    sections_detected: int = 0
    topics_detected: int = 0
    subtopics_detected: int = 0
    bibliography_items_detected: int = 0
    exclusions_detected: int = 0
    weight_hints_detected: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[DocumentProcessingError] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    ingestion_version: str = "edital-ingestion-v1"


class AlignmentEvidence(BaseModel):
    source_type: str
    source_id: str
    excerpt: str = ""
    matched_terms: list[str] = Field(default_factory=list)
    reasoning: str = ""
    confidence: float = 0.0


class AlignmentWarning(BaseModel):
    code: str
    message: str
    severity: str = "info"
    target_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class BibliographyItemAlignment(BaseModel):
    bibliography_id: str
    raw_reference: str
    matched_document_ids: list[str] = Field(default_factory=list)
    candidate_matches: list[str] = Field(default_factory=list)
    match_state: str = "unmatched"
    confidence: float = 0.0
    reasoning: str = ""
    evidence: list[AlignmentEvidence] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class DocumentCoverageCandidate(BaseModel):
    document_id: str
    material_id: str
    filename: str
    title_hint: str = ""
    matched_bibliography_ids: list[str] = Field(default_factory=list)
    covered_topic_ids: list[str] = Field(default_factory=list)
    covered_subtopic_ids: list[str] = Field(default_factory=list)
    matched_section_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    evidence: list[AlignmentEvidence] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class TopicCoverageCandidate(BaseModel):
    topic_id: str
    topic_title: str
    matched_document_ids: list[str] = Field(default_factory=list)
    matched_chunk_ids: list[str] = Field(default_factory=list)
    matched_section_ids: list[str] = Field(default_factory=list)
    coverage_state: str = "uncovered"
    confidence: float = 0.0
    reasoning: str = ""
    evidence: list[AlignmentEvidence] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class SectionCoverageCandidate(BaseModel):
    section_id: str
    section_title: str
    document_id: str
    matched_topic_ids: list[str] = Field(default_factory=list)
    matched_terms: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    evidence: list[AlignmentEvidence] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class CoverageGap(BaseModel):
    gap_id: str
    gap_type: str
    target_id: str
    target_title: str
    reason: str
    severity: str = "medium"
    evidence: list[AlignmentEvidence] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class CoverageRedundancy(BaseModel):
    redundancy_id: str
    redundancy_type: str
    target_id: str
    target_title: str
    overlapping_document_ids: list[str] = Field(default_factory=list)
    reason: str
    severity: str = "low"
    evidence: list[AlignmentEvidence] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class BibliographyAlignmentResult(BaseModel):
    alignment_id: str
    edital_id: str
    user_id: str | None = None
    bibliography_alignments: list[BibliographyItemAlignment] = Field(default_factory=list)
    topic_coverage: list[TopicCoverageCandidate] = Field(default_factory=list)
    document_coverage: list[DocumentCoverageCandidate] = Field(default_factory=list)
    section_coverage: list[SectionCoverageCandidate] = Field(default_factory=list)
    gaps: list[CoverageGap] = Field(default_factory=list)
    redundancies: list[CoverageRedundancy] = Field(default_factory=list)
    warnings: list[AlignmentWarning] = Field(default_factory=list)
    confidence_summary: dict[str, object] = Field(default_factory=dict)
    alignment_method: str = "heuristic_bibliography_alignment"
    alignment_version: str = "bibliography-alignment-v1"
    metadata: dict[str, object] = Field(default_factory=dict)


class BibliographyAlignmentState(BaseModel):
    alignment_id: str
    edital_id: str
    user_id: str | None = None
    current_stage: str = "pending"
    status: str = "pending"
    bibliography_items_total: int = 0
    bibliography_items_matched: int = 0
    topics_total: int = 0
    topics_with_coverage: int = 0
    gaps_detected: int = 0
    redundancies_detected: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[DocumentProcessingError] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    alignment_version: str = "bibliography-alignment-v1"


class CurriculumSourceEvidence(BaseModel):
    evidence_id: str
    source_type: str
    source_id: str
    document_id: str | None = None
    chunk_id: str | None = None
    section_id: str | None = None
    excerpt: str = ""
    matched_terms: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class CurriculumCoverageLink(BaseModel):
    link_id: str
    target_type: str
    target_id: str
    document_ids: list[str] = Field(default_factory=list)
    chunk_ids: list[str] = Field(default_factory=list)
    section_ids: list[str] = Field(default_factory=list)
    coverage_state: str = "uncovered"
    confidence: float = 0.0
    reasoning: str = ""
    evidence: list[CurriculumSourceEvidence] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class CurriculumSubjectNode(BaseModel):
    subject_id: str
    title: str
    normalized_title: str
    order_index: int = 0
    source_section_ids: list[str] = Field(default_factory=list)
    topic_ids: list[str] = Field(default_factory=list)
    coverage_state: str = "uncovered"
    review_state: str = "candidate"
    confidence: float = 0.0
    reasoning: str = ""
    evidence: list[CurriculumSourceEvidence] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class CurriculumTopicNode(BaseModel):
    topic_id: str
    title: str
    normalized_title: str
    subject_id: str
    source_topic_candidate_id: str
    order_index: int = 0
    subtopic_ids: list[str] = Field(default_factory=list)
    coverage_state: str = "uncovered"
    review_state: str = "candidate"
    confidence: float = 0.0
    reasoning: str = ""
    evidence: list[CurriculumSourceEvidence] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class CurriculumSubtopicNode(BaseModel):
    subtopic_id: str
    title: str
    normalized_title: str
    parent_topic_id: str
    source_subtopic_candidate_id: str
    order_index: int = 0
    coverage_state: str = "uncovered"
    review_state: str = "candidate"
    confidence: float = 0.0
    reasoning: str = ""
    evidence: list[CurriculumSourceEvidence] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class CurriculumGapReference(BaseModel):
    gap_id: str
    source_gap_id: str
    gap_type: str
    target_type: str
    target_id: str
    target_title: str
    severity: str = "medium"
    reason: str = ""
    evidence: list[CurriculumSourceEvidence] = Field(default_factory=list)
    review_state: str = "needs_review"
    metadata: dict[str, object] = Field(default_factory=dict)


class CurriculumRedundancyReference(BaseModel):
    redundancy_id: str
    source_redundancy_id: str
    redundancy_type: str
    target_type: str
    target_id: str
    target_title: str
    overlapping_document_ids: list[str] = Field(default_factory=list)
    severity: str = "low"
    reason: str = ""
    evidence: list[CurriculumSourceEvidence] = Field(default_factory=list)
    review_state: str = "ambiguous"
    metadata: dict[str, object] = Field(default_factory=dict)


class CurriculumGraphWarning(BaseModel):
    code: str
    message: str
    severity: str = "info"
    target_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class CurriculumGraphSummary(BaseModel):
    subject_count: int = 0
    topic_count: int = 0
    subtopic_count: int = 0
    covered_topics_count: int = 0
    partially_covered_topics_count: int = 0
    weakly_covered_topics_count: int = 0
    uncovered_topics_count: int = 0
    ambiguous_topics_count: int = 0
    gap_count: int = 0
    redundancy_count: int = 0
    ocr_required_count: int = 0
    needs_review_count: int = 0
    confidence_summary: dict[str, object] = Field(default_factory=dict)
    coverage_summary: dict[str, object] = Field(default_factory=dict)
    metadata: dict[str, object] = Field(default_factory=dict)


class CurriculumGraph(BaseModel):
    graph_id: str
    edital_id: str
    alignment_id: str | None = None
    user_id: str | None = None
    subjects: list[CurriculumSubjectNode] = Field(default_factory=list)
    topics: list[CurriculumTopicNode] = Field(default_factory=list)
    subtopics: list[CurriculumSubtopicNode] = Field(default_factory=list)
    coverage_links: list[CurriculumCoverageLink] = Field(default_factory=list)
    gaps: list[CurriculumGapReference] = Field(default_factory=list)
    redundancies: list[CurriculumRedundancyReference] = Field(default_factory=list)
    warnings: list[CurriculumGraphWarning] = Field(default_factory=list)
    summary: CurriculumGraphSummary = Field(default_factory=CurriculumGraphSummary)
    build_method: str = "heuristic_curriculum_graph_builder"
    graph_version: str = "curriculum-graph-v1"
    metadata: dict[str, object] = Field(default_factory=dict)


class CurriculumGraphState(BaseModel):
    graph_id: str
    edital_id: str
    alignment_id: str | None = None
    user_id: str | None = None
    current_stage: str = "pending"
    status: str = "pending"
    subject_count: int = 0
    topic_count: int = 0
    subtopic_count: int = 0
    coverage_links_count: int = 0
    gaps_count: int = 0
    redundancies_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[DocumentProcessingError] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    graph_version: str = "curriculum-graph-v1"


class StudyCycleSubjectRotation(BaseModel):
    rotation_id: str
    subject_id: str
    subject_title: str
    order_index: int = 0
    topic_ids: list[str] = Field(default_factory=list)
    suggested_frequency: str = "low"
    intensity_level: str = "light"
    coverage_mix: dict[str, int] = Field(default_factory=dict)
    review_need_level: str = "low"
    fatigue_risk: str = "low"
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class StudyCycleTopicSlot(BaseModel):
    slot_id: str
    subject_id: str
    topic_id: str
    topic_title: str
    order_index: int = 0
    slot_type: str = "learn"
    coverage_state: str = "uncovered"
    review_state: str = "candidate"
    suggested_action: str = "study_now_candidate"
    intensity_level: str = "moderate"
    source_evidence_ids: list[str] = Field(default_factory=list)
    gap_ids: list[str] = Field(default_factory=list)
    redundancy_ids: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class StudyCycleReviewSlot(BaseModel):
    review_slot_id: str
    topic_id: str
    topic_title: str
    reason: str
    review_trigger: str
    priority_hint: str = "medium"
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class StudyCycleGapSlot(BaseModel):
    gap_slot_id: str
    source_gap_id: str
    gap_type: str
    target_title: str
    suggested_resolution: str
    severity: str = "medium"
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class StudyCycleFatigueProfile(BaseModel):
    estimated_cycle_load: int = 0
    high_intensity_topic_count: int = 0
    gap_blocked_count: int = 0
    weak_topic_count: int = 0
    rotation_complexity: str = "unknown"
    fatigue_risk_level: str = "unknown"
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class StudyCycleBalanceSummary(BaseModel):
    subject_count: int = 0
    topic_slot_count: int = 0
    learn_slot_count: int = 0
    reinforce_slot_count: int = 0
    review_needed_slot_count: int = 0
    gap_blocked_slot_count: int = 0
    ocr_blocked_slot_count: int = 0
    ambiguous_slot_count: int = 0
    covered_topic_count: int = 0
    partially_covered_topic_count: int = 0
    weak_topic_count: int = 0
    uncovered_topic_count: int = 0
    balance_state: str = "insufficient_graph"
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class StudyCycleWarning(BaseModel):
    code: str
    message: str
    severity: str = "info"
    target_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class StudyCycleRationale(BaseModel):
    summary: str = ""
    reasons: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    source_graph_id: str
    confidence: float = 0.0
    metadata: dict[str, object] = Field(default_factory=dict)


class StudyCyclePlan(BaseModel):
    cycle_id: str
    graph_id: str
    user_id: str | None = None
    subject_rotations: list[StudyCycleSubjectRotation] = Field(default_factory=list)
    topic_slots: list[StudyCycleTopicSlot] = Field(default_factory=list)
    review_slots: list[StudyCycleReviewSlot] = Field(default_factory=list)
    gap_slots: list[StudyCycleGapSlot] = Field(default_factory=list)
    fatigue_profile: StudyCycleFatigueProfile = Field(default_factory=StudyCycleFatigueProfile)
    balance_summary: StudyCycleBalanceSummary = Field(default_factory=StudyCycleBalanceSummary)
    warnings: list[StudyCycleWarning] = Field(default_factory=list)
    rationale: StudyCycleRationale
    build_method: str = "heuristic_study_cycle_orchestrator"
    cycle_version: str = "study-cycle-v1"
    metadata: dict[str, object] = Field(default_factory=dict)


class StudyCyclePlanState(BaseModel):
    cycle_id: str
    graph_id: str
    user_id: str | None = None
    current_stage: str = "pending"
    status: str = "pending"
    subject_count: int = 0
    topic_slot_count: int = 0
    review_slot_count: int = 0
    gap_slot_count: int = 0
    warnings: list[str] = Field(default_factory=list)
    errors: list[DocumentProcessingError] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    cycle_version: str = "study-cycle-v1"


class ExamBoardProfile(BaseModel):
    board_id: str
    board_name: str
    aliases: list[str] = Field(default_factory=list)
    default_style_hints: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamQuestionFormatProfile(BaseModel):
    format_type: str = "unknown"
    options_count: int = 0
    answer_options: list[str] = Field(default_factory=list)
    expected_question_count: int = 0
    question_count_range: list[int] = Field(default_factory=list)
    single_correct_answer: bool = False
    format_source: str = "unknown"
    format_confidence: float = 0.0
    explicit_format_confirmed: bool = False
    supports_true_false: bool = False
    supports_multiple_choice: bool = False
    supports_discursive: bool = False
    supports_oral: bool = False
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamTimingProfile(BaseModel):
    total_duration_minutes: int = 0
    estimated_minutes_per_question: float = 0.0
    timing_pressure: str = "unknown"
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamScoringProfile(BaseModel):
    scoring_type: str = "unknown"
    correct: float | None = None
    wrong: float | None = None
    blank: float | None = None
    double_mark: float | None = None
    negative_marking: bool = False
    penalty_hint: bool = False
    negative_marking_hint: bool = False
    partial_credit_hint: bool = False
    scoring_source: str = "unknown"
    explicit_scoring_confirmed: bool = False
    scoring_confidence: float = 0.0
    raw_scoring_notes: str = ""
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamContentDistributionHint(BaseModel):
    hint_id: str
    target_subject: str | None = None
    target_topic: str | None = None
    distribution_type: str = "unknown"
    value: float = 0.0
    source: str = "profile_default"
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamDifficultyProfile(BaseModel):
    default_difficulty: str = "unknown"
    difficulty_distribution: dict[str, float] = Field(default_factory=dict)
    expected_variability: str = "unknown"
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamCognitiveDemandProfile(BaseModel):
    recall_demand: str = "unknown"
    interpretation_demand: str = "unknown"
    application_demand: str = "unknown"
    trap_sensitivity: str = "unknown"
    time_pressure_sensitivity: str = "unknown"
    reading_precision_demand: str = "unknown"
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamGenerationProfile(BaseModel):
    generation_style: str = "unknown"
    stem_style: str = "unknown"
    distractor_quality: str = "unknown"
    trap_patterns: list[str] = Field(default_factory=list)
    command_patterns: list[str] = Field(default_factory=list)
    allow_english_terms: bool = False
    allow_multitopic_items: bool = False
    require_source_topic_mapping: bool = True
    avoid_unsupported_tricks: bool = True
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamQuestionStyleProfile(BaseModel):
    stem_length: str = "unknown"
    contextualization: str = "unknown"
    literalness: str = "unknown"
    case_based: str = "unknown"
    technical_depth: str = "unknown"
    distractor_similarity: str = "unknown"
    reading_precision: str = "unknown"
    technical_language: str = "unknown"
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamContentBehaviorProfile(BaseModel):
    law_dry_text_weight: str = "unknown"
    jurisprudence_weight: str = "unknown"
    doctrine_weight: str = "unknown"
    calculation_weight: str = "unknown"
    technical_standard_weight: str = "unknown"
    bibliography_weight: str = "unknown"
    case_problem_weight: str = "unknown"
    normative_detail_weight: str = "unknown"
    technical_operational_weight: str = "unknown"
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamBoardBehaviorHint(BaseModel):
    hint_id: str
    behavior_type: str = "unknown"
    description: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamProfileWarning(BaseModel):
    code: str
    message: str
    severity: str = "info"
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamProfileSummary(BaseModel):
    exam_board: str
    profile_name: str
    format_summary: str = ""
    timing_summary: str = ""
    scoring_summary: str = ""
    difficulty_summary: str = ""
    cognitive_demand_summary: str = ""
    limitation_summary: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamProfile(BaseModel):
    profile_id: str
    exam_board: str
    profile_name: str
    board_profile: ExamBoardProfile
    exam_family: str = "generic"
    description: str = ""
    question_format: ExamQuestionFormatProfile = Field(default_factory=ExamQuestionFormatProfile)
    timing_profile: ExamTimingProfile = Field(default_factory=ExamTimingProfile)
    scoring_profile: ExamScoringProfile = Field(default_factory=ExamScoringProfile)
    content_distribution_hints: list[ExamContentDistributionHint] = Field(default_factory=list)
    difficulty_profile: ExamDifficultyProfile = Field(default_factory=ExamDifficultyProfile)
    cognitive_demand_profile: ExamCognitiveDemandProfile = Field(default_factory=ExamCognitiveDemandProfile)
    generation_profile: ExamGenerationProfile = Field(default_factory=ExamGenerationProfile)
    question_style_profile: ExamQuestionStyleProfile = Field(default_factory=ExamQuestionStyleProfile)
    content_behavior_profile: ExamContentBehaviorProfile = Field(default_factory=ExamContentBehaviorProfile)
    board_behavior_hints: list[ExamBoardBehaviorHint] = Field(default_factory=list)
    warnings: list[ExamProfileWarning] = Field(default_factory=list)
    summary: ExamProfileSummary
    profile_version: str = "exam-profiles-v1"
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamProfileState(BaseModel):
    profile_id: str
    exam_board: str
    profile_name: str
    status: str = "available"
    profile_version: str = "exam-profiles-v1"
    supported: bool = True
    warnings: list[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExamProfileSelectionCandidate(BaseModel):
    profile_id: str | None = None
    board_id: str | None = None
    exam_board: str | None = None
    profile_name: str | None = None
    exam_family: str | None = None
    format_type: str | None = None
    confidence: float = 0.0
    heuristic_confidence: float = 0.0
    format_confidence: float = 0.0
    board_confidence: float = 0.0
    family_confidence: float = 0.0
    scoring_confidence: float = 0.0
    reasoning: list[str] = Field(default_factory=list)
    selection_reasoning: list[str] = Field(default_factory=list)
    format_evidence: list[str] = Field(default_factory=list)
    scoring_evidence: list[str] = Field(default_factory=list)
    family_evidence: list[str] = Field(default_factory=list)
    board_evidence: list[str] = Field(default_factory=list)
    warnings: list[ExamProfileWarning] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoSectionBlueprint(BaseModel):
    section_id: str
    section_title: str
    section_type: str = "unknown"
    order_index: int = 0
    target_subject_ids: list[str] = Field(default_factory=list)
    target_topic_ids: list[str] = Field(default_factory=list)
    planned_question_count: int = 0
    format_type: str = "unknown"
    timing_minutes: int = 0
    scoring_notes: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoQuestionSlot(BaseModel):
    slot_id: str
    section_id: str
    order_index: int = 0
    target_subject_id: str
    target_topic_id: str
    target_subtopic_ids: list[str] = Field(default_factory=list)
    format_type: str = "unknown"
    cognitive_demand: str = "unknown"
    difficulty_hint: str = "unknown"
    generation_style: str = "unknown"
    source_evidence_ids: list[str] = Field(default_factory=list)
    required_coverage_state: str = "uncovered"
    blocked_by_gap_ids: list[str] = Field(default_factory=list)
    readiness_state: str = "needs_review"
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoDistributionPlan(BaseModel):
    total_question_count: int = 0
    question_count_source: str = "insufficient_evidence"
    section_distribution: dict[str, int] = Field(default_factory=dict)
    subject_distribution: dict[str, int] = Field(default_factory=dict)
    topic_distribution: dict[str, int] = Field(default_factory=dict)
    weak_topic_allocation: list[str] = Field(default_factory=list)
    gap_exclusions: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoTimingPlan(BaseModel):
    total_duration_minutes: int = 0
    duration_source: str = "unknown"
    estimated_minutes_per_question: float = 0.0
    timing_pressure: str = "unknown"
    section_timing: dict[str, int] = Field(default_factory=dict)
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoScoringPlan(BaseModel):
    scoring_type: str = "unknown"
    negative_marking: bool = False
    scoring_source: str = "unknown"
    correct_value: float | None = None
    wrong_value: float | None = None
    blank_value: float | None = None
    double_mark_value: float | None = None
    section_scoring: dict[str, dict[str, object]] = Field(default_factory=dict)
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoCoveragePlan(BaseModel):
    covered_topic_slots: int = 0
    partially_covered_topic_slots: int = 0
    weak_topic_slots: int = 0
    uncovered_topic_slots: int = 0
    ocr_blocked_slots: int = 0
    ambiguous_slots: int = 0
    excluded_gap_ids: list[str] = Field(default_factory=list)
    readiness_summary: str = ""
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoReadinessProfile(BaseModel):
    readiness_state: str = "blueprint_not_ready"
    ready_slot_count: int = 0
    blocked_slot_count: int = 0
    review_needed_slot_count: int = 0
    ocr_blocked_count: int = 0
    material_gap_count: int = 0
    ambiguity_count: int = 0
    warnings_count: int = 0
    confidence: float = 0.0
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoGenerationConstraint(BaseModel):
    constraint_id: str
    constraint_type: str
    target_id: str | None = None
    description: str
    severity: str = "warning"
    reasoning: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoBlueprintWarning(BaseModel):
    code: str
    message: str
    severity: str = "info"
    target_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoBlueprintRationale(BaseModel):
    summary: str = ""
    priorities: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)
    source_graph_id: str
    source_cycle_id: str
    source_exam_profile_id: str | None = None
    confidence: float = 0.0
    reasoning: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoBlueprint(BaseModel):
    blueprint_id: str
    graph_id: str
    cycle_id: str
    exam_profile_id: str | None = None
    user_id: str | None = None
    exam_board: str | None = None
    exam_family: str | None = None
    format_type: str = "unknown"
    sections: list[SimuladoSectionBlueprint] = Field(default_factory=list)
    question_slots: list[SimuladoQuestionSlot] = Field(default_factory=list)
    distribution_plan: SimuladoDistributionPlan = Field(default_factory=SimuladoDistributionPlan)
    timing_plan: SimuladoTimingPlan = Field(default_factory=SimuladoTimingPlan)
    scoring_plan: SimuladoScoringPlan = Field(default_factory=SimuladoScoringPlan)
    coverage_plan: SimuladoCoveragePlan = Field(default_factory=SimuladoCoveragePlan)
    readiness_profile: SimuladoReadinessProfile = Field(default_factory=SimuladoReadinessProfile)
    generation_constraints: list[SimuladoGenerationConstraint] = Field(default_factory=list)
    warnings: list[SimuladoBlueprintWarning] = Field(default_factory=list)
    rationale: SimuladoBlueprintRationale
    build_method: str = "heuristic_simulado_blueprint_builder"
    blueprint_version: str = "simulado-blueprint-v1"
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoBlueprintState(BaseModel):
    blueprint_id: str
    graph_id: str
    cycle_id: str
    exam_profile_id: str | None = None
    user_id: str | None = None
    current_stage: str = "pending"
    status: str = "pending"
    section_count: int = 0
    question_slot_count: int = 0
    coverage_gap_count: int = 0
    readiness_state: str = "blueprint_not_ready"
    warnings: list[str] = Field(default_factory=list)
    errors: list[DocumentProcessingError] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    blueprint_version: str = "simulado-blueprint-v1"


class QuestionSourceEvidence(BaseModel):
    evidence_id: str
    document_id: str | None = None
    material_id: str | None = None
    section_id: str | None = None
    chunk_id: str | None = None
    topic_id: str | None = None
    subtopic_id: str | None = None
    evidence_role: str = "source_evidence"
    evidence_strength: str = "unknown"
    coverage_state: str = "unknown"
    source_title: str | None = None
    source_type: str = "unknown"
    safe_snippet: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestionGenerationConstraint(BaseModel):
    constraint_id: str
    constraint_type: str
    severity: str = "warning"
    description: str
    source: str = "question_generation_blueprint"
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestionGenerationWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestionGenerationBlueprint(BaseModel):
    blueprint_id: str
    user_id: str | None = None
    source_simulado_blueprint_id: str
    source_question_slot_id: str
    readiness_state: str = "needs_review"
    format_type: str = "unknown"
    board_id: str | None = None
    exam_family: str | None = None
    target_subject_id: str
    target_topic_id: str
    target_subtopic_ids: list[str] = Field(default_factory=list)
    difficulty_hint: str = "unknown"
    cognitive_demand: str = "unknown"
    question_kind: str = "review_prompt_placeholder"
    style_hints: list[str] = Field(default_factory=list)
    source_evidence: list[QuestionSourceEvidence] = Field(default_factory=list)
    constraints: list[QuestionGenerationConstraint] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    warnings: list[QuestionGenerationWarning] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestionGenerationBlueprintSet(BaseModel):
    blueprint_set_id: str
    user_id: str | None = None
    source_simulado_blueprint_id: str
    status: str = "no_slots"
    readiness_state: str = "no_slots"
    total_slots: int = 0
    ready_slots: int = 0
    blocked_slots: int = 0
    needs_review_slots: int = 0
    slot_blueprints: list[QuestionGenerationBlueprint] = Field(default_factory=list)
    constraints: list[QuestionGenerationConstraint] = Field(default_factory=list)
    warnings: list[QuestionGenerationWarning] = Field(default_factory=list)
    no_question_text_generated: bool = True
    no_alternatives_generated: bool = True
    no_distractors_generated: bool = True
    no_answer_key_generated: bool = True
    no_explanations_generated: bool = True
    build_method: str = "heuristic_question_generation_blueprint_builder"
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestionDraftSourceReference(BaseModel):
    evidence_id: str
    document_id: str | None = None
    material_id: str | None = None
    section_id: str | None = None
    chunk_id: str | None = None
    topic_id: str | None = None
    subtopic_id: str | None = None
    evidence_role: str = "source_evidence"
    evidence_strength: str = "unknown"
    source_title: str | None = None
    safe_snippet: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestionDraftConstraint(BaseModel):
    constraint_id: str
    constraint_type: str
    severity: str = "warning"
    description: str
    source: str = "question_draft_generation"
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestionDraftWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestionDraftValidationSummary(BaseModel):
    source_grounded: bool = False
    has_required_source_evidence: bool = False
    format_supported: bool = False
    profile_supported: bool = False
    needs_human_review: bool = True
    final_answer_absent: bool = True
    final_alternatives_absent: bool = True
    final_explanation_absent: bool = True
    warnings_count: int = 0
    blockers_count: int = 0
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestionDraftProvenance(BaseModel):
    build_method: str = "heuristic_question_draft_generator"
    source_blueprint_id: str
    source_evidence_count: int = 0
    source_constraints_count: int = 0
    template_family: str = "unknown"
    deterministic_template_id: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestionDraft(BaseModel):
    draft_id: str
    user_id: str | None = None
    source_question_generation_blueprint_id: str
    source_question_generation_slot_id: str
    source_simulado_blueprint_id: str
    source_question_slot_id: str
    draft_status: str = "draft_created"
    draft_readiness: str = "draft_for_review"
    format_type: str = "unknown"
    question_kind: str = "review_prompt_placeholder"
    board_id: str | None = None
    exam_family: str | None = None
    target_subject_id: str
    target_topic_id: str
    target_subtopic_ids: list[str] = Field(default_factory=list)
    draft_stem: str | None = None
    draft_command: str | None = None
    draft_statement: str | None = None
    draft_scenario: str | None = None
    draft_option_placeholders: list[str] = Field(default_factory=list)
    source_references: list[QuestionDraftSourceReference] = Field(default_factory=list)
    constraints: list[QuestionDraftConstraint] = Field(default_factory=list)
    warnings: list[QuestionDraftWarning] = Field(default_factory=list)
    validation_summary: QuestionDraftValidationSummary = Field(default_factory=QuestionDraftValidationSummary)
    provenance: QuestionDraftProvenance
    review_required: bool = True
    finalization_blocked: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class QuestionDraftSet(BaseModel):
    draft_set_id: str
    user_id: str | None = None
    source_question_generation_blueprint_set_id: str
    source_simulado_blueprint_id: str
    status: str = "no_ready_blueprints"
    readiness_state: str = "no_ready_blueprints"
    total_blueprint_slots: int = 0
    draft_count: int = 0
    skipped_count: int = 0
    blocked_count: int = 0
    needs_review_count: int = 0
    drafts: list[QuestionDraft] = Field(default_factory=list)
    skipped_blueprint_ids: list[str] = Field(default_factory=list)
    warnings: list[QuestionDraftWarning] = Field(default_factory=list)
    no_final_question_generated: bool = True
    no_answer_key_generated: bool = True
    no_final_alternatives_generated: bool = True
    no_distractors_generated: bool = True
    no_final_explanations_generated: bool = True
    review_required: bool = True
    build_method: str = "heuristic_question_draft_generator"
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class AnswerKeyCandidate(BaseModel):
    candidate_id: str
    format_type: str = "unknown"
    candidate_value: str | None = None
    allowed_values: list[str] = Field(default_factory=list)
    confidence: float = 0.0
    support_state: str = "unknown"
    requires_review: bool = True
    finalization_blocked: bool = True
    rationale_summary: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ExplanationCandidate(BaseModel):
    candidate_id: str
    explanation_outline: str | None = None
    source_anchor_ids: list[str] = Field(default_factory=list)
    support_state: str = "unknown"
    confidence: float = 0.0
    requires_review: bool = True
    finalization_blocked: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class SourceSupportAssessment(BaseModel):
    assessment_id: str
    source_evidence_count: int = 0
    primary_source_available: bool = False
    source_coverage_state: str = "missing"
    source_conflict_detected: bool = False
    ocr_blocked: bool = False
    missing_source: bool = False
    ambiguous_support: bool = False
    safe_snippets: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "warning"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AnswerExplanationWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AnswerExplanationGuardrail(BaseModel):
    guardrail_id: str
    user_id: str | None = None
    source_question_draft_id: str
    source_question_draft_set_id: str
    source_question_generation_blueprint_id: str
    source_question_generation_blueprint_set_id: str
    source_simulado_blueprint_id: str
    status: str = "needs_review"
    answer_key_state: str = "answer_key_needs_human_review"
    explanation_state: str = "explanation_needs_human_review"
    candidate_answer_key: AnswerKeyCandidate
    candidate_explanation: ExplanationCandidate
    source_support_assessment: SourceSupportAssessment
    validation_findings: list[ValidationFinding] = Field(default_factory=list)
    warnings: list[AnswerExplanationWarning] = Field(default_factory=list)
    review_required: bool = True
    finalization_blocked: bool = True
    no_final_answer_key_generated: bool = True
    no_final_explanation_generated: bool = True
    no_simulado_execution_enabled: bool = True
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class CandidateDraftSummary(BaseModel):
    source_question_draft_id: str
    draft_status: str = "unknown"
    draft_readiness: str = "unknown"
    review_required: bool = True
    finalization_blocked: bool = True
    draft_stem_preview: str | None = None
    draft_command_preview: str | None = None
    draft_type: str = "unknown"
    placeholder_count: int = 0
    source_reference_count: int = 0
    metadata: dict[str, object] = Field(default_factory=dict)


class CandidateGuardrailSummary(BaseModel):
    source_guardrail_id: str | None = None
    guardrail_status: str = "missing"
    answer_key_state: str = "unknown"
    explanation_state: str = "unknown"
    review_required: bool = True
    finalization_blocked: bool = True
    no_final_answer_key_generated: bool = True
    no_final_explanation_generated: bool = True
    no_simulado_execution_enabled: bool = True
    source_support_state: str = "unknown"
    metadata: dict[str, object] = Field(default_factory=dict)


class CandidateSourceEvidenceSummary(BaseModel):
    source_reference_count: int = 0
    primary_source_available: bool = False
    missing_source: bool = False
    ambiguous_support: bool = False
    ocr_blocked: bool = False
    material_gap: bool = False
    safe_snippets: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class AssemblyValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "warning"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AssemblyWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoQuestionCandidate(BaseModel):
    candidate_id: str
    source_simulado_slot_id: str
    source_question_generation_blueprint_id: str | None = None
    source_question_generation_slot_id: str | None = None
    source_question_draft_id: str | None = None
    source_guardrail_id: str | None = None
    format_type: str = "unknown"
    question_kind: str = "unknown"
    board_id: str | None = None
    exam_family: str | None = None
    target_subject_id: str
    target_topic_id: str
    target_subtopic_ids: list[str] = Field(default_factory=list)
    readiness_state: str = "candidate_blocked_by_missing_draft"
    draft_summary: CandidateDraftSummary
    guardrail_summary: CandidateGuardrailSummary
    source_evidence_summary: CandidateSourceEvidenceSummary
    validation_findings: list[AssemblyValidationFinding] = Field(default_factory=list)
    warnings: list[AssemblyWarning] = Field(default_factory=list)
    requires_human_review: bool = True
    not_executable: bool = True
    not_scoreable: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoQuestionAssembly(BaseModel):
    assembly_id: str
    user_id: str | None = None
    source_simulado_blueprint_id: str
    source_question_generation_blueprint_set_id: str | None = None
    source_question_draft_set_id: str | None = None
    status: str = "assembly_no_candidates"
    readiness_state: str = "assembly_no_candidates"
    total_candidates: int = 0
    ready_for_review_count: int = 0
    blocked_count: int = 0
    needs_review_count: int = 0
    candidates: list[SimuladoQuestionCandidate] = Field(default_factory=list)
    validation_findings: list[AssemblyValidationFinding] = Field(default_factory=list)
    warnings: list[AssemblyWarning] = Field(default_factory=list)
    requires_human_review: bool = True
    not_executable: bool = True
    not_scoreable: bool = True
    no_student_attempts_enabled: bool = True
    no_progress_mutation: bool = True
    no_final_questions_created: bool = True
    no_final_answer_keys_created: bool = True
    no_final_explanations_created: bool = True
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoExecutionBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoAttemptShellValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoAttemptShellWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoAttemptShell(BaseModel):
    attempt_shell_id: str
    user_id: str | None = None
    source_assembly_id: str
    source_simulado_blueprint_id: str
    status: str = "execution_not_enabled"
    readiness_state: str = "blocked_by_non_final_assembly"
    total_candidates: int = 0
    review_ready_candidates: int = 0
    blocked_candidates: int = 0
    needs_review_candidates: int = 0
    executable_questions_count: int = 0
    execution_enabled: bool = False
    correction_enabled: bool = False
    scoring_enabled: bool = False
    student_submission_enabled: bool = False
    progress_mutation_enabled: bool = False
    requires_human_finalization: bool = True
    no_student_attempt_created: bool = True
    no_answer_submission_enabled: bool = True
    no_correction_result_created: bool = True
    no_score_created: bool = True
    validation_findings: list[SimuladoAttemptShellValidationFinding] = Field(default_factory=list)
    blockers: list[SimuladoExecutionBlocker] = Field(default_factory=list)
    warnings: list[SimuladoAttemptShellWarning] = Field(default_factory=list)
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class CandidateFinalizationSummary(BaseModel):
    candidate_id: str
    source_question_candidate_id: str | None = None
    source_question_draft_id: str | None = None
    source_guardrail_id: str | None = None
    readiness_state: str = "candidate_finalization_blocked"
    review_required: bool = True
    finalization_blocked: bool = True
    has_final_question: bool = False
    has_final_answer_key: bool = False
    has_final_explanation: bool = False
    approval_state: str = "approval_required"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class FinalizationBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class FinalizationValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class FinalizationWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoFinalizationGuardrail(BaseModel):
    finalization_guardrail_id: str
    user_id: str | None = None
    source_assembly_id: str
    source_attempt_shell_id: str
    source_simulado_blueprint_id: str
    status: str = "finalization_not_available"
    readiness_state: str = "blocked_by_non_final_assembly"
    total_candidates: int = 0
    review_ready_candidates: int = 0
    blocked_candidates: int = 0
    needs_review_candidates: int = 0
    finalizable_candidates_count: int = 0
    approved_candidates_count: int = 0
    missing_final_questions_count: int = 0
    missing_final_answer_keys_count: int = 0
    missing_final_explanations_count: int = 0
    candidate_summaries: list[CandidateFinalizationSummary] = Field(default_factory=list)
    blockers: list[FinalizationBlocker] = Field(default_factory=list)
    validation_findings: list[FinalizationValidationFinding] = Field(default_factory=list)
    warnings: list[FinalizationWarning] = Field(default_factory=list)
    approval_required: bool = True
    human_review_required: bool = True
    execution_enabled: bool = False
    correction_enabled: bool = False
    scoring_enabled: bool = False
    student_submission_enabled: bool = False
    progress_mutation_enabled: bool = False
    no_student_attempt_created: bool = True
    no_answer_submission_enabled: bool = True
    no_correction_result_created: bool = True
    no_score_created: bool = True
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class FinalApprovalCandidateRecord(BaseModel):
    record_id: str
    source_candidate_id: str | None = None
    source_question_draft_id: str | None = None
    source_guardrail_id: str | None = None
    approval_state: str = "candidate_not_reviewed"
    decision_id: str | None = None
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    final_question_ready: bool = False
    final_answer_key_ready: bool = False
    final_explanation_ready: bool = False
    requires_human_review: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class FinalApprovalDecision(BaseModel):
    decision_id: str
    source_candidate_id: str | None = None
    decision_type: str
    decision_state: str = "decision_recorded"
    reviewer_id: str | None = None
    reason: str | None = None
    approved_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class FinalApprovalAuditTrailEntry(BaseModel):
    audit_id: str
    event_type: str
    actor_user_id: str | None = None
    message: str
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class FinalApprovalValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class FinalApprovalWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoFinalApprovalArtifact(BaseModel):
    approval_artifact_id: str
    user_id: str | None = None
    source_finalization_guardrail_id: str
    source_attempt_shell_id: str
    source_assembly_id: str
    source_simulado_blueprint_id: str
    status: str = "approval_needs_review"
    readiness_state: str = "needs_human_review"
    total_candidates: int = 0
    approved_candidate_count: int = 0
    blocked_candidate_count: int = 0
    needs_review_candidate_count: int = 0
    rejected_candidate_count: int = 0
    not_reviewed_candidate_count: int = 0
    candidate_records: list[FinalApprovalCandidateRecord] = Field(default_factory=list)
    decisions: list[FinalApprovalDecision] = Field(default_factory=list)
    audit_trail: list[FinalApprovalAuditTrailEntry] = Field(default_factory=list)
    validation_findings: list[FinalApprovalValidationFinding] = Field(default_factory=list)
    warnings: list[FinalApprovalWarning] = Field(default_factory=list)
    approval_recorded: bool = False
    human_approved: bool = False
    human_reviewer_id: str | None = None
    human_review_required: bool = True
    execution_enabled: bool = False
    correction_enabled: bool = False
    scoring_enabled: bool = False
    student_submission_enabled: bool = False
    progress_mutation_enabled: bool = False
    no_student_attempt_created: bool = True
    no_answer_submission_enabled: bool = True
    no_correction_result_created: bool = True
    no_score_created: bool = True
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExecutionShellCandidateRecord(BaseModel):
    record_id: str
    source_candidate_id: str | None = None
    source_approval_record_id: str | None = None
    approval_state: str = "candidate_not_reviewed"
    execution_readiness_state: str = "candidate_execution_blocked"
    order_index: int = 0
    display_position: int = 1
    has_final_question: bool = False
    has_final_answer_key: bool = False
    has_final_explanation: bool = False
    can_be_presented_to_student: bool = False
    can_accept_answer: bool = False
    can_be_corrected: bool = False
    can_be_scored: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExecutionShellOperationalSummary(BaseModel):
    summary_id: str
    has_final_approval_artifact: bool = True
    has_approved_candidates: bool = False
    has_final_questions: bool = False
    has_final_answer_keys: bool = False
    has_final_explanations: bool = False
    has_execution_session: bool = False
    future_execution_possible_after_finalization: bool = False
    execution_disabled_reason: str = ""
    candidate_ordering_strategy: str = "stable_source_candidate_id"
    estimated_question_count: int = 0
    estimated_duration_minutes: int = 0
    metadata: dict[str, object] = Field(default_factory=dict)


class ExecutionShellBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ExecutionShellValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ExecutionShellWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoExecutionShell(BaseModel):
    execution_shell_id: str
    user_id: str | None = None
    source_final_approval_artifact_id: str
    source_finalization_guardrail_id: str
    source_attempt_shell_id: str
    source_assembly_id: str
    source_simulado_blueprint_id: str
    status: str = "execution_shell_blocked"
    readiness_state: str = "blocked_by_missing_final_approval"
    total_candidates: int = 0
    approved_candidate_count: int = 0
    blocked_candidate_count: int = 0
    needs_review_candidate_count: int = 0
    executable_candidate_count: int = 0
    candidate_records: list[ExecutionShellCandidateRecord] = Field(default_factory=list)
    operational_summary: ExecutionShellOperationalSummary
    blockers: list[ExecutionShellBlocker] = Field(default_factory=list)
    validation_findings: list[ExecutionShellValidationFinding] = Field(default_factory=list)
    warnings: list[ExecutionShellWarning] = Field(default_factory=list)
    execution_shell_active: bool = False
    execution_started: bool = False
    attempt_created: bool = False
    student_submission_enabled: bool = False
    correction_enabled: bool = False
    scoring_enabled: bool = False
    progress_mutation_enabled: bool = False
    no_student_attempt_created: bool = True
    no_answer_submission_created: bool = True
    no_correction_result_created: bool = True
    no_score_created: bool = True
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoAttemptSessionItem(BaseModel):
    item_id: str
    source_execution_candidate_record_id: str | None = None
    source_candidate_id: str | None = None
    order_index: int = 0
    display_position: int = 1
    item_status: str = "item_blocked"
    item_readiness_state: str = "item_blocked_by_execution_shell"
    can_be_displayed: bool = False
    can_accept_answer: bool = False
    has_submitted_answer: bool = False
    can_be_corrected: bool = False
    can_be_scored: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class AttemptSessionTimingPlan(BaseModel):
    timing_plan_id: str
    timing_available: bool = False
    estimated_duration_minutes: int = 0
    per_item_time_limit_seconds: int | None = None
    timer_active: bool = False
    timer_started_at: datetime | None = None
    timer_completed_at: datetime | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AttemptSessionBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AttemptSessionValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AttemptSessionWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoAttemptSession(BaseModel):
    attempt_session_id: str
    user_id: str | None = None
    source_execution_shell_id: str
    source_final_approval_artifact_id: str
    source_simulado_blueprint_id: str
    status: str = "attempt_session_blocked"
    readiness_state: str = "blocked_by_missing_execution_shell"
    total_items: int = 0
    prepared_item_count: int = 0
    blocked_item_count: int = 0
    items: list[SimuladoAttemptSessionItem] = Field(default_factory=list)
    timing_plan: AttemptSessionTimingPlan
    blockers: list[AttemptSessionBlocker] = Field(default_factory=list)
    validation_findings: list[AttemptSessionValidationFinding] = Field(default_factory=list)
    warnings: list[AttemptSessionWarning] = Field(default_factory=list)
    session_prepared: bool = True
    session_active: bool = False
    session_submitted: bool = False
    session_completed: bool = False
    answer_submission_enabled: bool = False
    correction_enabled: bool = False
    scoring_enabled: bool = False
    progress_mutation_enabled: bool = False
    no_answer_submission_created: bool = True
    no_correction_result_created: bool = True
    no_score_created: bool = True
    no_progress_mutation: bool = True
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class AnswerSubmissionValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AnswerSubmissionWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoSubmittedAnswer(BaseModel):
    submitted_answer_id: str
    source_session_item_id: str
    source_candidate_id: str | None = None
    order_index: int = 0
    display_position: int = 1
    answer_kind: str = "blank"
    submitted_value: str | None = None
    submitted_values: list[str] = Field(default_factory=list)
    is_blank: bool = False
    is_structurally_valid: bool = False
    validation_state: str = "not_corrected"
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoAnswerSubmission(BaseModel):
    answer_submission_id: str
    user_id: str | None = None
    source_attempt_session_id: str
    source_execution_shell_id: str
    source_simulado_blueprint_id: str
    status: str = "answer_submission_blocked"
    readiness_state: str = "blocked_by_missing_attempt_session"
    total_items: int = 0
    submitted_answer_count: int = 0
    missing_answer_count: int = 0
    invalid_answer_count: int = 0
    duplicate_answer_count: int = 0
    submitted_answers: list[SimuladoSubmittedAnswer] = Field(default_factory=list)
    validation_findings: list[AnswerSubmissionValidationFinding] = Field(default_factory=list)
    warnings: list[AnswerSubmissionWarning] = Field(default_factory=list)
    submission_recorded: bool = False
    correction_enabled: bool = False
    scoring_enabled: bool = False
    progress_mutation_enabled: bool = False
    no_correction_result_created: bool = True
    no_score_created: bool = True
    no_progress_mutation: bool = True
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionShellAnswerRecord(BaseModel):
    record_id: str
    source_submitted_answer_id: str
    source_session_item_id: str
    source_candidate_id: str | None = None
    answer_kind: str = "blank"
    submission_validation_state: str = "not_corrected"
    correction_readiness_state: str = "answer_not_corrected"
    has_submitted_answer: bool = False
    is_blank: bool = False
    has_final_answer_key: bool = False
    has_correction_rule: bool = False
    can_be_corrected: bool = False
    can_be_scored: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionReadinessSummary(BaseModel):
    summary_id: str
    has_answer_submission: bool = True
    has_attempt_session: bool = False
    has_final_answer_keys: bool = False
    has_correction_rules: bool = False
    has_score_rules: bool = False
    correction_possible_later: bool = False
    scoring_possible_later: bool = False
    correction_disabled_reason: str = ""
    scoring_disabled_reason: str = ""
    progress_mutation_disabled_reason: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionShellBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionShellValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionShellWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoCorrectionShell(BaseModel):
    correction_shell_id: str
    user_id: str | None = None
    source_answer_submission_id: str
    source_attempt_session_id: str
    source_execution_shell_id: str
    source_simulado_blueprint_id: str
    status: str = "correction_shell_blocked"
    readiness_state: str = "blocked_by_missing_answer_submission"
    total_submitted_answers: int = 0
    structurally_valid_answer_count: int = 0
    blank_answer_count: int = 0
    invalid_answer_count: int = 0
    correction_ready_answer_count: int = 0
    blocked_answer_count: int = 0
    answer_records: list[CorrectionShellAnswerRecord] = Field(default_factory=list)
    readiness_summary: CorrectionReadinessSummary
    blockers: list[CorrectionShellBlocker] = Field(default_factory=list)
    validation_findings: list[CorrectionShellValidationFinding] = Field(default_factory=list)
    warnings: list[CorrectionShellWarning] = Field(default_factory=list)
    correction_enabled: bool = False
    scoring_enabled: bool = False
    progress_mutation_enabled: bool = False
    no_correction_result_created: bool = True
    no_score_created: bool = True
    no_progress_mutation: bool = True
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionInputContract(BaseModel):
    contract_id: str
    contract_available: bool = True
    internal_only: bool = True
    public_exposure_allowed: bool = False
    supported_formats: list[str] = Field(default_factory=list)
    supported_answer_kinds: list[str] = Field(default_factory=list)
    unsupported_answer_kinds: list[str] = Field(default_factory=list)
    requires_final_answer_key: bool = True
    requires_correction_rule: bool = True
    requires_score_rule: bool = True
    correction_allowed_now: bool = False
    scoring_allowed_now: bool = False
    future_correction_possible: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionInputAnswerRecord(BaseModel):
    record_id: str
    source_correction_shell_answer_record_id: str
    source_submitted_answer_id: str
    source_session_item_id: str
    source_candidate_id: str | None = None
    answer_kind: str = "blank"
    format_type: str = "unknown"
    boundary_readiness_state: str = "answer_not_corrected"
    has_internal_answer_key_reference: bool = False
    has_public_answer_key_content: bool = False
    answer_key_publicly_exposed: bool = False
    has_correction_rule_reference: bool = False
    has_score_rule_reference: bool = False
    future_correction_supported: bool = False
    correction_allowed_now: bool = False
    scoring_allowed_now: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class InternalAnswerKeyReference(BaseModel):
    reference_id: str
    source_candidate_id: str | None = None
    source_guardrail_id: str | None = None
    source_approval_artifact_id: str | None = None
    source_finalization_artifact_id: str | None = None
    answer_key_reference_available: bool = False
    answer_key_value_stored: bool = False
    answer_key_value_publicly_exposed: bool = False
    answer_key_value_hash: str | None = None
    answer_key_value_redacted: bool = True
    allowed_values: list[str] = Field(default_factory=list)
    reference_state: str = "missing_internal_answer_key_reference"
    metadata: dict[str, object] = Field(default_factory=dict)


class AnswerKeyBoundaryBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AnswerKeyBoundaryValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class AnswerKeyBoundaryWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoAnswerKeyBoundary(BaseModel):
    answer_key_boundary_id: str
    user_id: str | None = None
    source_correction_shell_id: str
    source_answer_submission_id: str
    source_attempt_session_id: str
    source_simulado_blueprint_id: str
    status: str = "answer_key_boundary_blocked"
    readiness_state: str = "blocked_by_missing_correction_shell"
    total_answer_records: int = 0
    supported_answer_record_count: int = 0
    blocked_answer_record_count: int = 0
    internal_answer_key_reference_count: int = 0
    correction_input_contract: CorrectionInputContract
    answer_records: list[CorrectionInputAnswerRecord] = Field(default_factory=list)
    internal_answer_key_references: list[InternalAnswerKeyReference] = Field(default_factory=list)
    blockers: list[AnswerKeyBoundaryBlocker] = Field(default_factory=list)
    validation_findings: list[AnswerKeyBoundaryValidationFinding] = Field(default_factory=list)
    warnings: list[AnswerKeyBoundaryWarning] = Field(default_factory=list)
    correction_enabled: bool = False
    scoring_enabled: bool = False
    progress_mutation_enabled: bool = False
    answer_key_publicly_exposed: bool = False
    gabarito_publicly_exposed: bool = False
    no_correction_result_created: bool = True
    no_score_created: bool = True
    no_progress_mutation: bool = True
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionResultAnswerRecord(BaseModel):
    record_id: str
    source_boundary_answer_record_id: str
    source_submitted_answer_id: str
    source_session_item_id: str
    source_candidate_id: str | None = None
    answer_kind: str = "blank"
    correction_state: str = "answer_not_corrected"
    correction_input_available: bool = False
    has_internal_answer_key_reference: bool = False
    has_public_answer_key_content: bool = False
    answer_key_publicly_exposed: bool = False
    student_answer_recorded: bool = False
    student_answer_blank: bool = False
    candidate_result: str | None = None
    requires_review: bool = False
    scoreable: bool = False
    scoring_enabled: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionResultSummary(BaseModel):
    summary_id: str
    correction_result_available: bool = True
    scoring_available: bool = False
    progress_mutation_available: bool = False
    public_answer_key_exposure_allowed: bool = False
    public_gabarito_exposure_allowed: bool = False
    correction_completed_for_all_answers: bool = False
    all_answers_blocked: bool = True
    has_unresolved_blockers: bool = True
    requires_human_review: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionResultBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionResultValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class CorrectionResultWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoCorrectionResult(BaseModel):
    correction_result_id: str
    user_id: str | None = None
    source_answer_key_boundary_id: str
    source_correction_shell_id: str
    source_answer_submission_id: str
    source_attempt_session_id: str
    source_simulado_blueprint_id: str
    status: str = "correction_result_blocked"
    readiness_state: str = "blocked_by_missing_answer_key_boundary"
    total_answer_records: int = 0
    corrected_answer_count: int = 0
    blocked_answer_count: int = 0
    needs_review_answer_count: int = 0
    blank_answer_count: int = 0
    unsupported_answer_count: int = 0
    answer_records: list[CorrectionResultAnswerRecord] = Field(default_factory=list)
    summary: CorrectionResultSummary
    blockers: list[CorrectionResultBlocker] = Field(default_factory=list)
    validation_findings: list[CorrectionResultValidationFinding] = Field(default_factory=list)
    warnings: list[CorrectionResultWarning] = Field(default_factory=list)
    scoring_enabled: bool = False
    progress_mutation_enabled: bool = False
    answer_key_publicly_exposed: bool = False
    gabarito_publicly_exposed: bool = False
    no_score_created: bool = True
    no_progress_mutation: bool = True
    no_final_simulado_result_created: bool = True
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class ScoreItemRecord(BaseModel):
    record_id: str
    source_correction_result_answer_record_id: str
    source_submitted_answer_id: str
    source_session_item_id: str
    source_candidate_id: str | None = None
    answer_kind: str = "blank"
    correction_state: str = "answer_not_corrected"
    score_state: str = "item_not_scoreable"
    scoreable: bool = False
    scored: bool = False
    points_awarded: float = 0.0
    max_points: float = 0.0
    scoring_blockers: list[str] = Field(default_factory=list)
    requires_review: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class ScoreSummary(BaseModel):
    summary_id: str
    raw_score: float = 0.0
    max_score: float = 0.0
    percentage_score: float | None = None
    score_computable: bool = False
    score_complete: bool = False
    score_partial: bool = False
    no_scoreable_items: bool = True
    blocked_items_present: bool = True
    needs_review_present: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class ScorePolicySnapshot(BaseModel):
    policy_id: str
    policy_source: str | None = None
    policy_available: bool = False
    per_item_default_points: float | None = None
    negative_marking_enabled: bool = False
    negative_marking_source: str | None = None
    blank_penalty_enabled: bool = False
    unsupported_items_scoreable: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class ScoreBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ScoreValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ScoreWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoScoreResult(BaseModel):
    score_result_id: str
    user_id: str | None = None
    source_correction_result_id: str
    source_answer_key_boundary_id: str
    source_correction_shell_id: str
    source_answer_submission_id: str
    source_attempt_session_id: str
    source_simulado_blueprint_id: str
    status: str = "score_result_blocked"
    readiness_state: str = "blocked_by_missing_correction_result"
    total_answer_records: int = 0
    scoreable_item_count: int = 0
    scored_item_count: int = 0
    blocked_item_count: int = 0
    needs_review_item_count: int = 0
    blank_item_count: int = 0
    unsupported_item_count: int = 0
    item_records: list[ScoreItemRecord] = Field(default_factory=list)
    score_summary: ScoreSummary
    score_policy: ScorePolicySnapshot
    blockers: list[ScoreBlocker] = Field(default_factory=list)
    validation_findings: list[ScoreValidationFinding] = Field(default_factory=list)
    warnings: list[ScoreWarning] = Field(default_factory=list)
    progress_mutation_enabled: bool = False
    ranking_mutation_enabled: bool = False
    retention_mutation_enabled: bool = False
    scheduler_mutation_enabled: bool = False
    study_cycle_mutation_enabled: bool = False
    curriculum_graph_mutation_enabled: bool = False
    no_progress_mutation: bool = True
    no_ranking_update: bool = True
    no_retention_update: bool = True
    no_scheduler_update: bool = True
    no_study_cycle_update: bool = True
    no_curriculum_graph_update: bool = True
    answer_key_publicly_exposed: bool = False
    gabarito_publicly_exposed: bool = False
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class ProgressMutationEligibility(BaseModel):
    eligibility_id: str
    eligible_for_future_progress_mutation: bool = False
    eligible_for_future_ranking_update: bool = False
    eligible_for_future_retention_update: bool = False
    eligible_for_future_scheduler_update: bool = False
    eligible_for_future_study_cycle_update: bool = False
    eligible_for_future_curriculum_graph_update: bool = False
    eligibility_state: str = "not_eligible"
    requires_human_review: bool = False
    requires_complete_score: bool = True
    requires_topic_mapping: bool = True
    requires_policy_confirmation: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class CandidateProgressTarget(BaseModel):
    target_id: str
    target_type: str = "unknown"
    target_id_ref: str | None = None
    source_candidate_id: str | None = None
    source_session_item_id: str | None = None
    topic_id: str | None = None
    subtopic_id: str | None = None
    microtopic_id: str | None = None
    target_available: bool = False
    mapping_confidence: float = 0.0
    proposed_update_kind: str = "no_update_applied"
    future_update_allowed: bool = False
    update_applied: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ProgressScoreCompletenessAssessment(BaseModel):
    assessment_id: str
    total_items: int = 0
    scored_items: int = 0
    scoreable_items: int = 0
    blocked_items: int = 0
    needs_review_items: int = 0
    blank_items: int = 0
    unsupported_items: int = 0
    raw_score: float = 0.0
    max_score: float = 0.0
    percentage_score: float | None = None
    score_complete: bool = False
    score_partial: bool = False
    score_blocked: bool = True
    enough_data_for_progress_update: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class ProgressMutationBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ProgressMutationValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ProgressMutationWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoProgressMutationGuardrail(BaseModel):
    progress_guardrail_id: str
    user_id: str | None = None
    source_score_result_id: str
    source_correction_result_id: str
    source_answer_key_boundary_id: str
    source_answer_submission_id: str
    source_attempt_session_id: str
    source_simulado_blueprint_id: str
    status: str = "progress_guardrail_blocked"
    readiness_state: str = "blocked_by_missing_score_result"
    eligibility: ProgressMutationEligibility
    score_completeness: ProgressScoreCompletenessAssessment
    candidate_progress_targets: list[CandidateProgressTarget] = Field(default_factory=list)
    blockers: list[ProgressMutationBlocker] = Field(default_factory=list)
    validation_findings: list[ProgressMutationValidationFinding] = Field(default_factory=list)
    warnings: list[ProgressMutationWarning] = Field(default_factory=list)
    progress_mutation_enabled: bool = False
    ranking_mutation_enabled: bool = False
    retention_mutation_enabled: bool = False
    scheduler_mutation_enabled: bool = False
    study_cycle_mutation_enabled: bool = False
    curriculum_graph_mutation_enabled: bool = False
    adaptive_tuning_enabled: bool = False
    no_progress_mutation: bool = True
    no_ranking_update: bool = True
    no_retention_update: bool = True
    no_scheduler_update: bool = True
    no_study_cycle_update: bool = True
    no_curriculum_graph_update: bool = True
    no_adaptive_tuning_update: bool = True
    answer_key_publicly_exposed: bool = False
    gabarito_publicly_exposed: bool = False
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class IntegratedArtifactChainSummary(BaseModel):
    chain_summary_id: str
    attempt_session_available: bool = False
    answer_submission_available: bool = False
    correction_shell_available: bool = False
    answer_key_boundary_available: bool = False
    correction_result_available: bool = False
    score_result_available: bool = False
    progress_guardrail_available: bool = False
    chain_complete: bool = False
    missing_artifacts: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class IntegratedExecutionStatusSummary(BaseModel):
    summary_id: str
    session_prepared: bool = False
    session_active: bool = False
    session_submitted: bool = False
    session_completed: bool = False
    answer_submission_present: bool = False
    submitted_answer_count: int = 0
    non_submittable_items_present: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class IntegratedCorrectionStatusSummary(BaseModel):
    summary_id: str
    correction_shell_present: bool = False
    answer_key_boundary_present: bool = False
    correction_result_present: bool = False
    total_answer_records: int = 0
    corrected_answer_count: int = 0
    blocked_answer_count: int = 0
    needs_review_answer_count: int = 0
    correction_complete: bool = False
    correction_blocked: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class IntegratedScoreStatusSummary(BaseModel):
    summary_id: str
    score_result_present: bool = False
    raw_score: float = 0.0
    max_score: float = 0.0
    percentage_score: float | None = None
    scoreable_item_count: int = 0
    scored_item_count: int = 0
    blocked_item_count: int = 0
    needs_review_item_count: int = 0
    score_complete: bool = False
    score_blocked: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class IntegratedProgressGuardrailSummary(BaseModel):
    summary_id: str
    progress_guardrail_present: bool = False
    eligible_for_future_progress_mutation: bool = False
    eligible_for_future_ranking_update: bool = False
    eligible_for_future_retention_update: bool = False
    eligible_for_future_scheduler_update: bool = False
    candidate_target_count: int = 0
    update_applied_count: int = 0
    mutation_blocked: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class IntegratedExecutionCorrectionBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class IntegratedExecutionCorrectionValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class IntegratedExecutionCorrectionWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoIntegratedExecutionCorrection(BaseModel):
    integrated_result_id: str
    user_id: str | None = None
    source_attempt_session_id: str
    source_answer_submission_id: str | None = None
    source_correction_shell_id: str | None = None
    source_answer_key_boundary_id: str | None = None
    source_correction_result_id: str | None = None
    source_score_result_id: str | None = None
    source_progress_guardrail_id: str | None = None
    source_simulado_blueprint_id: str | None = None
    status: str = "integrated_execution_correction_blocked"
    readiness_state: str = "blocked_by_missing_attempt_session"
    chain_summary: IntegratedArtifactChainSummary
    execution_summary: IntegratedExecutionStatusSummary
    correction_summary: IntegratedCorrectionStatusSummary
    score_summary: IntegratedScoreStatusSummary
    progress_guardrail_summary: IntegratedProgressGuardrailSummary
    blockers: list[IntegratedExecutionCorrectionBlocker] = Field(default_factory=list)
    validation_findings: list[IntegratedExecutionCorrectionValidationFinding] = Field(default_factory=list)
    warnings: list[IntegratedExecutionCorrectionWarning] = Field(default_factory=list)
    progress_mutation_applied: bool = False
    ranking_update_applied: bool = False
    retention_update_applied: bool = False
    scheduler_update_applied: bool = False
    study_cycle_update_applied: bool = False
    curriculum_graph_update_applied: bool = False
    adaptive_tuning_applied: bool = False
    progress_mutation_enabled: bool = False
    ranking_mutation_enabled: bool = False
    retention_mutation_enabled: bool = False
    scheduler_mutation_enabled: bool = False
    study_cycle_mutation_enabled: bool = False
    curriculum_graph_mutation_enabled: bool = False
    adaptive_tuning_enabled: bool = False
    no_progress_mutation: bool = True
    no_ranking_update: bool = True
    no_retention_update: bool = True
    no_scheduler_update: bool = True
    no_study_cycle_update: bool = True
    no_curriculum_graph_update: bool = True
    no_adaptive_tuning_update: bool = True
    answer_key_publicly_exposed: bool = False
    gabarito_publicly_exposed: bool = False
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeApplicationEligibility(BaseModel):
    eligibility_id: str
    eligible_for_future_runtime_application: bool = False
    eligible_for_future_progress_mutation: bool = False
    eligible_for_future_ranking_update: bool = False
    eligible_for_future_retention_update: bool = False
    eligible_for_future_scheduler_update: bool = False
    eligible_for_future_study_cycle_update: bool = False
    eligible_for_future_curriculum_graph_update: bool = False
    eligibility_state: str = "not_eligible"
    requires_human_review: bool = True
    requires_explicit_application_approval: bool = True
    requires_complete_integrated_chain: bool = True
    requires_complete_score: bool = True
    requires_progress_guardrail_eligibility: bool = True
    requires_runtime_policy_confirmation: bool = True
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeApplicationSafetyAssessment(BaseModel):
    assessment_id: str
    integrated_chain_complete: bool = False
    score_result_present: bool = False
    score_complete: bool = False
    progress_guardrail_present: bool = False
    progress_guardrail_eligible: bool = False
    runtime_policy_available: bool = False
    public_answer_key_exposure_detected: bool = False
    public_gabarito_exposure_detected: bool = False
    unsafe_runtime_mutation_detected: bool = True
    enough_data_for_future_application: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class CandidateRuntimeMutationIntent(BaseModel):
    intent_id: str
    intent_type: str = "unknown"
    source_target_id: str | None = None
    source_score_item_id: str | None = None
    topic_id: str | None = None
    subtopic_id: str | None = None
    microtopic_id: str | None = None
    subject_id: str | None = None
    proposed_surface: str = "unknown"
    proposed_update_kind: str = "no_application_applied"
    future_application_allowed: bool = False
    application_applied: bool = False
    requires_review: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class AffectedRuntimeSurfaceSummary(BaseModel):
    surface_id: str
    surface_type: str = "unknown"
    surface_name: str = "unknown"
    affected: bool = False
    future_update_allowed: bool = False
    update_applied: bool = False
    blocker_count: int = 0
    warning_count: int = 0
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeApplicationBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeApplicationValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeApplicationWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoRuntimeApplicationGuardrail(BaseModel):
    runtime_guardrail_id: str
    user_id: str | None = None
    source_integrated_result_id: str
    source_attempt_session_id: str | None = None
    source_answer_submission_id: str | None = None
    source_correction_result_id: str | None = None
    source_score_result_id: str | None = None
    source_progress_guardrail_id: str | None = None
    source_simulado_blueprint_id: str | None = None
    status: str = "runtime_application_guardrail_blocked"
    readiness_state: str = "blocked_by_missing_integrated_result"
    eligibility: RuntimeApplicationEligibility
    safety_assessment: RuntimeApplicationSafetyAssessment
    candidate_mutation_intents: list[CandidateRuntimeMutationIntent] = Field(default_factory=list)
    affected_runtime_surfaces: list[AffectedRuntimeSurfaceSummary] = Field(default_factory=list)
    blockers: list[RuntimeApplicationBlocker] = Field(default_factory=list)
    validation_findings: list[RuntimeApplicationValidationFinding] = Field(default_factory=list)
    warnings: list[RuntimeApplicationWarning] = Field(default_factory=list)
    runtime_application_enabled: bool = False
    runtime_application_applied: bool = False
    progress_mutation_enabled: bool = False
    progress_mutation_applied: bool = False
    ranking_update_enabled: bool = False
    ranking_update_applied: bool = False
    retention_update_enabled: bool = False
    retention_update_applied: bool = False
    scheduler_update_enabled: bool = False
    scheduler_update_applied: bool = False
    study_cycle_update_enabled: bool = False
    study_cycle_update_applied: bool = False
    curriculum_graph_update_enabled: bool = False
    curriculum_graph_update_applied: bool = False
    adaptive_tuning_enabled: bool = False
    adaptive_tuning_applied: bool = False
    no_runtime_application: bool = True
    no_progress_mutation: bool = True
    no_ranking_update: bool = True
    no_retention_update: bool = True
    no_scheduler_update: bool = True
    no_study_cycle_update: bool = True
    no_curriculum_graph_update: bool = True
    no_adaptive_tuning_update: bool = True
    answer_key_publicly_exposed: bool = False
    gabarito_publicly_exposed: bool = False
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeProgressApplicationPlan(BaseModel):
    plan_id: str
    plan_status: str = "plan_blocked"
    planned_only: bool = True
    dry_run: bool = True
    can_apply_now: bool = False
    requires_runtime_policy: bool = True
    requires_explicit_final_approval: bool = True
    requires_complete_guardrail: bool = True
    requires_audit_confirmation: bool = True
    mutation_intent_count: int = 0
    proposed_surface_count: int = 0
    blocker_count: int = 0
    metadata: dict[str, object] = Field(default_factory=dict)


class PlannedRuntimeMutationIntent(BaseModel):
    intent_id: str
    source_intent_id: str | None = None
    intent_type: str = "unknown"
    proposed_surface: str = "unknown"
    proposed_update_kind: str = "intent_planned_not_applied"
    source_target_id: str | None = None
    topic_id: str | None = None
    subtopic_id: str | None = None
    microtopic_id: str | None = None
    subject_id: str | None = None
    planned: bool = True
    applied: bool = False
    apply_allowed: bool = False
    requires_review: bool = True
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ProposedRuntimeSurfaceDiff(BaseModel):
    diff_id: str
    surface_type: str = "unknown"
    surface_name: str = "unknown"
    target_ref: str | None = None
    before_snapshot_available: bool = False
    after_snapshot_available: bool = False
    before_summary: dict[str, object] = Field(default_factory=dict)
    proposed_after_summary: dict[str, object] = Field(default_factory=dict)
    diff_status: str = "diff_planned_not_applied"
    applied: bool = False
    apply_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeApplicationAuditEntry(BaseModel):
    audit_id: str
    event_type: str
    actor_user_id: str | None = None
    message: str
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeProgressApplicationBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeProgressApplicationValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeProgressApplicationWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoRuntimeProgressApplication(BaseModel):
    application_id: str
    user_id: str | None = None
    source_runtime_guardrail_id: str
    source_integrated_result_id: str | None = None
    source_score_result_id: str | None = None
    source_progress_guardrail_id: str | None = None
    source_attempt_session_id: str | None = None
    source_simulado_blueprint_id: str | None = None
    application_mode: str = "planned_only"
    application_status: str = "application_blocked"
    readiness_state: str = "blocked_by_missing_runtime_guardrail"
    plan: RuntimeProgressApplicationPlan
    planned_mutation_intents: list[PlannedRuntimeMutationIntent] = Field(default_factory=list)
    proposed_surface_diffs: list[ProposedRuntimeSurfaceDiff] = Field(default_factory=list)
    audit_trail: list[RuntimeApplicationAuditEntry] = Field(default_factory=list)
    blockers: list[RuntimeProgressApplicationBlocker] = Field(default_factory=list)
    validation_findings: list[RuntimeProgressApplicationValidationFinding] = Field(default_factory=list)
    warnings: list[RuntimeProgressApplicationWarning] = Field(default_factory=list)
    runtime_application_enabled: bool = False
    runtime_application_applied: bool = False
    progress_mutation_enabled: bool = False
    progress_mutation_applied: bool = False
    ranking_update_enabled: bool = False
    ranking_update_applied: bool = False
    retention_update_enabled: bool = False
    retention_update_applied: bool = False
    scheduler_update_enabled: bool = False
    scheduler_update_applied: bool = False
    study_cycle_update_enabled: bool = False
    study_cycle_update_applied: bool = False
    curriculum_graph_update_enabled: bool = False
    curriculum_graph_update_applied: bool = False
    adaptive_tuning_enabled: bool = False
    adaptive_tuning_applied: bool = False
    no_runtime_application: bool = True
    no_progress_mutation: bool = True
    no_ranking_update: bool = True
    no_retention_update: bool = True
    no_scheduler_update: bool = True
    no_study_cycle_update: bool = True
    no_curriculum_graph_update: bool = True
    no_adaptive_tuning_update: bool = True
    answer_key_publicly_exposed: bool = False
    gabarito_publicly_exposed: bool = False
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class ControlledApplyPreconditionSummary(BaseModel):
    summary_id: str
    source_application_present: bool = True
    source_application_planned_only: bool = True
    source_application_not_applied: bool = True
    runtime_policy_present: bool = False
    explicit_apply_approval_present: bool = False
    audit_confirmation_present: bool = False
    rollback_plan_present: bool = False
    all_intents_apply_allowed: bool = False
    all_surfaces_apply_allowed: bool = False
    unsafe_public_answer_key_exposure_detected: bool = False
    unsafe_gabarito_exposure_detected: bool = False
    preconditions_satisfied: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class ControlledApplyIntentDecision(BaseModel):
    decision_id: str
    source_intent_id: str | None = None
    intent_type: str = "unknown"
    proposed_surface: str = "unknown"
    planned: bool = True
    source_applied: bool = False
    apply_allowed: bool = False
    apply_decision: str = "intent_rejected_pre_apply"
    apply_decision_reason: str = ""
    applied: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ControlledApplySurfaceDecision(BaseModel):
    decision_id: str
    source_diff_id: str | None = None
    surface_type: str = "unknown"
    diff_status: str = "diff_blocked"
    source_applied: bool = False
    apply_allowed: bool = False
    apply_decision: str = "surface_rejected_pre_apply"
    apply_decision_reason: str = ""
    applied: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ControlledApplyAuditRequirement(BaseModel):
    requirement_id: str
    requirement_type: str
    required: bool = True
    satisfied: bool = False
    reason: str = ""
    metadata: dict[str, object] = Field(default_factory=dict)


class ControlledApplyAuditEntry(BaseModel):
    audit_id: str
    event_type: str
    actor_user_id: str | None = None
    message: str
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class ControlledApplyBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ControlledApplyValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ControlledApplyWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoControlledRuntimeApplyShell(BaseModel):
    apply_shell_id: str
    user_id: str | None = None
    source_application_id: str
    source_runtime_guardrail_id: str
    source_integrated_result_id: str | None = None
    source_score_result_id: str | None = None
    source_progress_guardrail_id: str | None = None
    source_attempt_session_id: str | None = None
    source_simulado_blueprint_id: str | None = None
    application_mode: str = "pre_apply_shell"
    apply_status: str = "apply_blocked"
    readiness_state: str = "blocked_by_missing_runtime_progress_application"
    precondition_summary: ControlledApplyPreconditionSummary
    intent_decisions: list[ControlledApplyIntentDecision] = Field(default_factory=list)
    surface_decisions: list[ControlledApplySurfaceDecision] = Field(default_factory=list)
    audit_requirements: list[ControlledApplyAuditRequirement] = Field(default_factory=list)
    audit_trail: list[ControlledApplyAuditEntry] = Field(default_factory=list)
    blockers: list[ControlledApplyBlocker] = Field(default_factory=list)
    validation_findings: list[ControlledApplyValidationFinding] = Field(default_factory=list)
    warnings: list[ControlledApplyWarning] = Field(default_factory=list)
    apply_shell_created: bool = True
    apply_request_accepted: bool = False
    apply_preconditions_satisfied: bool = False
    runtime_application_enabled: bool = False
    runtime_application_applied: bool = False
    progress_mutation_enabled: bool = False
    progress_mutation_applied: bool = False
    ranking_update_enabled: bool = False
    ranking_update_applied: bool = False
    retention_update_enabled: bool = False
    retention_update_applied: bool = False
    scheduler_update_enabled: bool = False
    scheduler_update_applied: bool = False
    study_cycle_update_enabled: bool = False
    study_cycle_update_applied: bool = False
    curriculum_graph_update_enabled: bool = False
    curriculum_graph_update_applied: bool = False
    adaptive_tuning_enabled: bool = False
    adaptive_tuning_applied: bool = False
    no_runtime_application: bool = True
    no_progress_mutation: bool = True
    no_ranking_update: bool = True
    no_retention_update: bool = True
    no_scheduler_update: bool = True
    no_study_cycle_update: bool = True
    no_curriculum_graph_update: bool = True
    no_adaptive_tuning_update: bool = True
    answer_key_publicly_exposed: bool = False
    gabarito_publicly_exposed: bool = False
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExplicitApplyDecisionSummary(BaseModel):
    summary_id: str
    decision_type: str = "mark_not_reviewed"
    decision_state: str = "decision_not_reviewed"
    reviewer_id: str | None = None
    reason: str = ""
    decision_recorded: bool = False
    approved_for_future_runtime_mutation_review: bool = False
    denied: bool = False
    revision_requested: bool = False
    blocked: bool = False
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExplicitApplyConfirmationSummary(BaseModel):
    summary_id: str
    runtime_policy_confirmed: bool = False
    explicit_apply_approval_confirmed: bool = False
    audit_confirmed: bool = False
    rollback_plan_confirmed: bool = False
    human_review_confirmed: bool = False
    public_answer_key_absence_confirmed: bool = False
    all_confirmations_satisfied: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class ExplicitApplyIntentApproval(BaseModel):
    approval_id: str
    source_intent_decision_id: str | None = None
    source_intent_id: str | None = None
    intent_type: str = "unknown"
    proposed_surface: str = "unknown"
    source_apply_decision: str = "intent_not_reviewed"
    source_applied: bool = False
    explicitly_approved: bool = False
    approved_for_future_runtime_mutation_review: bool = False
    approved_for_apply_now: bool = False
    applied: bool = False
    approval_state: str = "intent_not_reviewed"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExplicitApplySurfaceApproval(BaseModel):
    approval_id: str
    source_surface_decision_id: str | None = None
    source_diff_id: str | None = None
    surface_type: str = "unknown"
    source_apply_decision: str = "surface_not_reviewed"
    source_applied: bool = False
    explicitly_approved: bool = False
    approved_for_future_runtime_mutation_review: bool = False
    approved_for_apply_now: bool = False
    applied: bool = False
    approval_state: str = "surface_not_reviewed"
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExplicitApplyAuditEntry(BaseModel):
    audit_id: str
    event_type: str
    actor_user_id: str | None = None
    message: str
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class ExplicitApplyBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ExplicitApplyValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class ExplicitApplyWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoExplicitRuntimeProgressApply(BaseModel):
    explicit_apply_id: str
    user_id: str | None = None
    source_apply_shell_id: str
    source_application_id: str
    source_runtime_guardrail_id: str
    source_integrated_result_id: str | None = None
    source_score_result_id: str | None = None
    source_progress_guardrail_id: str | None = None
    source_attempt_session_id: str | None = None
    source_simulado_blueprint_id: str | None = None
    decision_status: str = "explicit_apply_not_reviewed"
    readiness_state: str = "explicit_apply_needs_review"
    decision_summary: ExplicitApplyDecisionSummary
    confirmation_summary: ExplicitApplyConfirmationSummary
    intent_approvals: list[ExplicitApplyIntentApproval] = Field(default_factory=list)
    surface_approvals: list[ExplicitApplySurfaceApproval] = Field(default_factory=list)
    audit_trail: list[ExplicitApplyAuditEntry] = Field(default_factory=list)
    blockers: list[ExplicitApplyBlocker] = Field(default_factory=list)
    validation_findings: list[ExplicitApplyValidationFinding] = Field(default_factory=list)
    warnings: list[ExplicitApplyWarning] = Field(default_factory=list)
    explicit_apply_recorded: bool = False
    explicit_apply_approved: bool = False
    apply_request_accepted: bool = False
    apply_ready_for_runtime_mutation: bool = False
    runtime_application_enabled: bool = False
    runtime_application_applied: bool = False
    progress_mutation_enabled: bool = False
    progress_mutation_applied: bool = False
    ranking_update_enabled: bool = False
    ranking_update_applied: bool = False
    retention_update_enabled: bool = False
    retention_update_applied: bool = False
    scheduler_update_enabled: bool = False
    scheduler_update_applied: bool = False
    study_cycle_update_enabled: bool = False
    study_cycle_update_applied: bool = False
    curriculum_graph_update_enabled: bool = False
    curriculum_graph_update_applied: bool = False
    adaptive_tuning_enabled: bool = False
    adaptive_tuning_applied: bool = False
    no_runtime_application: bool = True
    no_progress_mutation: bool = True
    no_ranking_update: bool = True
    no_retention_update: bool = True
    no_scheduler_update: bool = True
    no_study_cycle_update: bool = True
    no_curriculum_graph_update: bool = True
    no_adaptive_tuning_update: bool = True
    no_final_pedagogical_update_event: bool = True
    answer_key_publicly_exposed: bool = False
    gabarito_publicly_exposed: bool = False
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeMutationValidationSummary(BaseModel):
    summary_id: str
    source_explicit_apply_present: bool = False
    explicit_apply_recorded: bool = False
    explicit_apply_approved: bool = False
    approved_for_future_runtime_mutation_review: bool = False
    approved_for_apply_now: bool = False
    apply_ready_for_runtime_mutation: bool = False
    confirmations_satisfied: bool = False
    proposed_delta_count: int = 0
    proposed_surface_update_count: int = 0
    rollback_plan_available: bool = False
    transaction_valid_for_commit: bool = False
    transaction_commit_ready: bool = False
    unsafe_public_answer_key_exposure_detected: bool = False
    unsafe_gabarito_exposure_detected: bool = False
    metadata: dict[str, object] = Field(default_factory=dict)


class ProposedProgressDelta(BaseModel):
    delta_id: str
    source_intent_approval_id: str | None = None
    target_type: str = "unknown"
    target_id: str | None = None
    topic_id: str | None = None
    subtopic_id: str | None = None
    microtopic_id: str | None = None
    subject_id: str | None = None
    delta_kind: str = "unknown"
    before_snapshot_available: bool = False
    after_snapshot_available: bool = False
    proposed_before_summary: dict[str, object] = Field(default_factory=dict)
    proposed_after_summary: dict[str, object] = Field(default_factory=dict)
    proposed_delta_value: float | None = None
    confidence: float = 0.0
    applied: bool = False
    commit_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class ProposedRuntimeSurfaceUpdate(BaseModel):
    update_id: str
    source_surface_approval_id: str | None = None
    surface_type: str = "unknown"
    surface_name: str = "unknown"
    update_kind: str = "unknown"
    target_ref: str | None = None
    before_snapshot_available: bool = False
    after_snapshot_available: bool = False
    proposed_before_summary: dict[str, object] = Field(default_factory=dict)
    proposed_after_summary: dict[str, object] = Field(default_factory=dict)
    applied: bool = False
    commit_allowed: bool = False
    blockers: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeMutationRollbackPlan(BaseModel):
    rollback_plan_id: str
    rollback_required: bool = True
    rollback_available: bool = False
    rollback_verified: bool = False
    rollback_summary: str = ""
    rollback_steps_count: int = 0
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeMutationAuditEntry(BaseModel):
    audit_id: str
    event_type: str
    actor_user_id: str | None = None
    message: str
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeMutationBlocker(BaseModel):
    blocker_id: str
    code: str
    severity: str = "blocked"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeMutationValidationFinding(BaseModel):
    finding_id: str
    code: str
    severity: str = "info"
    message: str
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class RuntimeMutationWarning(BaseModel):
    code: str
    message: str
    severity: str = "warning"
    related_artifact_type: str | None = None
    related_artifact_id: str | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class SimuladoRuntimeProgressMutationTransaction(BaseModel):
    mutation_transaction_id: str
    user_id: str | None = None
    source_explicit_apply_id: str
    source_apply_shell_id: str
    source_application_id: str
    source_runtime_guardrail_id: str
    source_integrated_result_id: str | None = None
    source_score_result_id: str | None = None
    source_progress_guardrail_id: str | None = None
    source_attempt_session_id: str | None = None
    source_simulado_blueprint_id: str | None = None
    mutation_mode: str = "proposal_only"
    mutation_status: str = "mutation_blocked"
    readiness_state: str = "mutation_needs_review"
    validation_summary: RuntimeMutationValidationSummary
    proposed_progress_deltas: list[ProposedProgressDelta] = Field(default_factory=list)
    proposed_surface_updates: list[ProposedRuntimeSurfaceUpdate] = Field(default_factory=list)
    rollback_plan: RuntimeMutationRollbackPlan
    audit_trail: list[RuntimeMutationAuditEntry] = Field(default_factory=list)
    blockers: list[RuntimeMutationBlocker] = Field(default_factory=list)
    validation_findings: list[RuntimeMutationValidationFinding] = Field(default_factory=list)
    warnings: list[RuntimeMutationWarning] = Field(default_factory=list)
    mutation_transaction_created: bool = True
    mutation_valid_for_commit: bool = False
    mutation_commit_ready: bool = False
    mutation_committed: bool = False
    runtime_application_enabled: bool = False
    runtime_application_applied: bool = False
    progress_mutation_enabled: bool = False
    progress_mutation_applied: bool = False
    ranking_update_enabled: bool = False
    ranking_update_applied: bool = False
    retention_update_enabled: bool = False
    retention_update_applied: bool = False
    scheduler_update_enabled: bool = False
    scheduler_update_applied: bool = False
    study_cycle_update_enabled: bool = False
    study_cycle_update_applied: bool = False
    curriculum_graph_update_enabled: bool = False
    curriculum_graph_update_applied: bool = False
    adaptive_tuning_enabled: bool = False
    adaptive_tuning_applied: bool = False
    no_runtime_application: bool = True
    no_progress_mutation: bool = True
    no_ranking_update: bool = True
    no_retention_update: bool = True
    no_scheduler_update: bool = True
    no_study_cycle_update: bool = True
    no_curriculum_graph_update: bool = True
    no_adaptive_tuning_update: bool = True
    no_final_pedagogical_update_event: bool = True
    answer_key_publicly_exposed: bool = False
    gabarito_publicly_exposed: bool = False
    generated_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class DocumentPipelineEvent(BaseModel):
    event_id: str
    document_id: str
    user_id: str | None = None
    stage: str
    status: str
    message: str = ""
    created_at: datetime = Field(default_factory=utc_now)
    metadata: dict[str, object] = Field(default_factory=dict)


class DocumentExtractionResult(BaseModel):
    document_id: str
    user_id: str | None = None
    source_type: str = MaterialSourceType.USER_UPLOAD.value
    text: str | None = None
    text_length: int = 0
    page_count: int = 0
    extraction_method: str = ""
    extraction_status: str = DocumentIngestionStatus.UPLOADED.value
    warnings: list[str] = Field(default_factory=list)
    errors: list[DocumentProcessingError] = Field(default_factory=list)
    metadata: dict[str, object] = Field(default_factory=dict)


class DocumentChunk(BaseModel):
    chunk_id: str
    document_id: str
    user_id: str | None = None
    chunk_index: int = 0
    text: str
    text_length: int = 0
    token_estimate: int = 0
    section_id: str | None = None
    page_start: int | None = None
    page_end: int | None = None
    metadata: dict[str, object] = Field(default_factory=dict)


class DocumentSection(BaseModel):
    section_id: str
    document_id: str
    user_id: str | None = None
    title: str
    level: int = 1
    order_index: int = 0
    start_chunk_index: int = 0
    end_chunk_index: int = 0
    metadata: dict[str, object] = Field(default_factory=dict)


class DocumentPipelineState(BaseModel):
    document_id: str
    user_id: str | None = None
    current_stage: str = DocumentIngestionStatus.UPLOADED.value
    stages_completed: list[str] = Field(default_factory=list)
    extraction_status: str = DocumentIngestionStatus.UPLOADED.value
    chunking_status: str = "not_started"
    sectioning_status: str = "not_started"
    metadata_status: str = "not_ready"
    error_count: int = 0
    last_error: DocumentProcessingError | None = None
    created_at: datetime = Field(default_factory=utc_now)
    updated_at: datetime = Field(default_factory=utc_now)
    pipeline_version: str = "document-pipeline-v1"
    text_length: int = 0
    chunk_count: int = 0
    section_count: int = 0


class AnswerSubmission(BaseModel):
    question_id: str
    document_id: str
    topic_id: str
    microtopic_id: str | None = None
    pedagogical_mode: str | None = None
    selected_answer: str
    is_correct: bool
    error_type: str | ErrorType | None = None
    created_at: datetime = Field(default_factory=utc_now)


class TopicLearningState(BaseModel):
    topic_id: str
    attempts: int = 0
    correct_attempts: int = 0
    incorrect_attempts: int = 0
    total_questions: int = 0
    correct_answers: int = 0
    recent_errors: int = 0
    error_distribution: dict[str, int] = Field(
        default_factory=lambda: {
            "conceptual": 0,
            "attention": 0,
            "interpretation": 0,
            "memory": 0,
        }
    )
    streak_correct: int = 0
    current_difficulty: int = 1
    first_seen_at: datetime | None = None
    last_seen_at: datetime | None = None
    last_correct_at: datetime | None = None
    last_error_at: datetime | None = None
    last_error_type: str | ErrorType | None = None


class ItemState(BaseModel):
    question_id: str
    topic_id: str
    seen_count: int = 0
    correct_count: int = 0
    incorrect_count: int = 0
    difficulty_level: int = 1
    last_seen_at: datetime | None = None
    last_result: str | None = None
    similarity_group: str | None = None
    last_error_type: str | ErrorType | None = None


class MicroTopicPerformance(BaseModel):
    topic_id: str | None = None
    total_questions: int = 0
    correct_answers: int = 0
    recent_errors: int = 0
    error_distribution: dict[str, int] = Field(
        default_factory=lambda: {
            "conceptual": 0,
            "attention": 0,
            "interpretation": 0,
            "memory": 0,
        }
    )
    last_seen_at: datetime | None = None
    last_reviewed_at: datetime | None = None
    last_correct_at: datetime | None = None
    last_incorrect_at: datetime | None = None
    consecutive_correct: int = 0
    consecutive_incorrect: int = 0


class InterventionHistory(BaseModel):
    pedagogical_mode: str
    total_attempts: int = 0
    successful_attempts: int = 0
    failed_attempts: int = 0
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    last_intervention_at: datetime | None = None
    last_outcome: str = PedagogicalOutcome.NEUTRAL.value
    confidence: float = 0.5


class PedagogicalMemory(BaseModel):
    microtopic_id: str | None = None
    topic_id: str | None = None
    last_pedagogical_mode: str | None = None
    recent_effectiveness: str = PedagogicalOutcome.NEUTRAL.value
    consecutive_successes: int = 0
    consecutive_failures: int = 0
    last_intervention_at: datetime | None = None
    stabilization_level: float = 0.0
    escalation_level: float = 0.0
    retrieval_success_trend: float = 0.5
    resurfacing_cycles: int = 0
    successful_resurfacing_cycles: int = 0
    fatigue_exposure: float = 0.0
    recovery_count: int = 0
    last_stabilized_at: datetime | None = None
    intervention_history: dict[str, InterventionHistory] = Field(default_factory=dict)


class LearningPlanEntry(BaseModel):
    document_id: str
    document_title: str
    topic_id: str
    topic_title: str
    topic_content: str | None = None
    question_ids: list[str] = Field(default_factory=list)
    priority_score: float
    recommended_difficulty: int = 1
    reasons: list[str] = Field(default_factory=list)
    score_breakdown: dict[str, float] = Field(default_factory=dict)
    item_reasons: dict[str, list[str]] = Field(default_factory=dict)
    performance_data: dict[str, object] = Field(default_factory=dict)
    dominant_error_type: str | None = None
    curriculum_role: str | None = None
    review_intensity: str | None = None
    study_strategy: str | None = None
    study_blocks: list[StudyBlock] = Field(default_factory=list)


class LearningPlan(BaseModel):
    title: str
    generated_at: datetime = Field(default_factory=utc_now)
    entries: list[LearningPlanEntry] = Field(default_factory=list)


class CurriculumWindow(BaseModel):
    role: str
    topic_ids: list[str] = Field(default_factory=list)


class CurriculumPhase(BaseModel):
    phase_number: int
    active_window: CurriculumWindow
    cumulative_window: CurriculumWindow


class CurriculumProgress(BaseModel):
    total_topics: int
    active_window_size: int
    active_topic_ids: list[str] = Field(default_factory=list)
    cumulative_topic_ids: list[str] = Field(default_factory=list)


class MicrotopicSessionCandidate(BaseModel):
    microtopic_id: str
    microtopic_title: str
    microtopic_content: str
    topic_id: str
    topic_title: str
    curriculum_role: str
    review_intensity: str
    microtopic_priority: float
    selection_reason: str
    difficulty_weight: float = 1.0
    resurfacing_signal: float = 0.0
    weakness_signal: float = 0.0
    composition_score: float = 0.0
    composition_breakdown: dict[str, float] = Field(default_factory=dict)
    topic_position: int = 0
    candidate_position: int = 0


class ReviewPayload(BaseModel):
    title: str
    documents_considered: list[str]
    summaries: list[str]
    questions: list[GeneratedQuestion]


class BlockReview(BaseModel):
    title: str
    document_ids: list[str]
    summaries: list[str]
    questions: list[GeneratedQuestion]


class ProgressState(BaseModel):
    total_errors: int = 0
    weak_topics: dict[str, int] = Field(default_factory=dict)
    error_buckets: dict[ErrorType, int] = Field(default_factory=dict)
    topic_learning_states: dict[str, TopicLearningState] = Field(default_factory=dict)
    item_states: dict[str, ItemState] = Field(default_factory=dict)
    microtopic_performance: dict[str, MicroTopicPerformance] = Field(default_factory=dict)
    pedagogical_memory: dict[str, PedagogicalMemory] = Field(default_factory=dict)
