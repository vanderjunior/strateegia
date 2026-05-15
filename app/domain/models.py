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
