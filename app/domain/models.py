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


class PedagogicalProfile(BaseModel):
    pedagogical_mode: str
    intervention_reason: str
    explanation_depth: str
    retrieval_intensity: str
    reinforcement_level: str
    cognitive_load: str
    intervention_transition_reason: str | None = None
    stabilization_signal: float = 0.0
    escalation_signal: float = 0.0
    pedagogical_confidence: float = 0.5
    intervention_effectiveness: str = PedagogicalOutcome.NEUTRAL.value
    pedagogical_stability: str = "adaptive"
    adaptation_reasoning: list[str] = Field(default_factory=list)
    intervention_history_summary: dict[str, object] = Field(default_factory=dict)
    profile_breakdown: dict[str, float] = Field(default_factory=dict)


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
