from datetime import datetime, timedelta, timezone

from app.domain.models import (
    AnswerSubmission,
    BoardStyle,
    Document,
    ErrorType,
    GeneratedQuestion,
    LearningPlanEntry,
    StudyBlock,
    StudyStrategy,
    Topic,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.learning_engine import (
    aggregate_topic_priority,
    build_study_blocks,
    compute_microtopic_priority,
    LearningDecisionEngine,
    compute_dynamic_priority,
    get_dominant_error_type,
    resolve_study_strategy,
)
from app.services.reviews import ReviewService


def build_document(*, title: str, topic_id: str, question_id: str, created_at: datetime) -> Document:
    topic = Topic(
        id=topic_id,
        title=title,
        content=(
            f"{title} possui regras, excecoes e comparacoes importantes para prova. "
            f"{title} exige precisao conceitual e atencao a pegadinhas recorrentes."
        ),
        key_points=[f"Ponto-chave de {title}"],
        trap_points=[f"Pegadinha classica de {title}"],
        relevance_score=0.8,
        source_pages=[1],
    )
    question = GeneratedQuestion(
        id=question_id,
        document_id="placeholder",
        topic_id=topic_id,
        style="multiple_choice",
        stem=f"Questao sobre {title}",
        options=["A", "B", "C", "D"],
        correct_answer="A",
        explanation=f"Explicacao de {title}",
        difficulty_level=1,
    )
    document = Document.create(
        title=title,
        source_filename=f"{title}.pdf",
        board=BoardStyle.FGV,
        exam_context="Receita Federal",
        source_excerpt=f"Trecho de {title}",
        topics=[topic],
        summaries=[],
        questions=[question],
    )
    document.created_at = created_at
    document.questions[0].document_id = document.id
    return document


def build_plan_entry(
    *,
    topic_id: str,
    raw_priority: float,
    normalized_priority: float,
    question_id: str | None = None,
    dominant_error_type: str | None = None,
    study_strategy: str | None = None,
) -> LearningPlanEntry:
    qid = question_id or f"{topic_id}-q1"
    return LearningPlanEntry(
        document_id=f"doc-{topic_id}",
        document_title=f"Doc {topic_id}",
        topic_id=topic_id,
        topic_title=f"Topico {topic_id}",
        question_ids=[qid],
        priority_score=normalized_priority,
        recommended_difficulty=1,
        reasons=[],
        score_breakdown={
            "raw_priority": raw_priority,
            "normalized_priority": normalized_priority,
        },
        item_reasons={qid: []},
        dominant_error_type=dominant_error_type,
        study_strategy=study_strategy,
    )


def test_repository_tracks_topic_and_item_learning_state(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    current_time = datetime(2026, 4, 24, 12, 0, tzinfo=timezone.utc)

    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id="doc-1",
            topic_id="topic-1",
            selected_answer="B",
            is_correct=False,
            error_type=ErrorType.CONCEPT_CONFUSION,
            created_at=current_time,
        )
    )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id="doc-1",
            topic_id="topic-1",
            selected_answer="A",
            is_correct=True,
            error_type=None,
            created_at=current_time + timedelta(hours=6),
        )
    )

    progress = repository.load_progress()
    topic_state = progress.topic_learning_states["topic-1"]
    item_state = progress.item_states["q-1"]

    assert topic_state.attempts == 2
    assert topic_state.incorrect_attempts == 1
    assert topic_state.correct_attempts == 1
    assert topic_state.last_seen_at == current_time + timedelta(hours=6)
    assert item_state.seen_count == 2
    assert item_state.incorrect_count == 1
    assert item_state.correct_count == 1
    assert topic_state.total_questions == 2
    assert topic_state.correct_answers == 1
    assert topic_state.recent_errors == 0


def test_compute_dynamic_priority_prioritizes_weak_topics():
    weak_topic = {
        "total_questions": 10,
        "correct_answers": 2,
        "recent_errors": 3,
    }
    strong_topic = {
        "total_questions": 10,
        "correct_answers": 9,
        "recent_errors": 0,
    }

    weak_priority = compute_dynamic_priority(weak_topic)
    strong_priority = compute_dynamic_priority(strong_topic)

    assert weak_priority > strong_priority


def test_compute_dynamic_priority_deprioritizes_strong_topics():
    strong_topic = {
        "total_questions": 20,
        "correct_answers": 18,
        "recent_errors": 0,
    }

    priority = compute_dynamic_priority(strong_topic)

    assert priority < 0.2


def test_compute_dynamic_priority_boosts_new_topics():
    new_topic = {
        "total_questions": 0,
        "correct_answers": 0,
        "recent_errors": 0,
    }
    seen_topic = {
        "total_questions": 5,
        "correct_answers": 4,
        "recent_errors": 0,
    }

    assert compute_dynamic_priority(new_topic) > compute_dynamic_priority(seen_topic)


def test_compute_dynamic_priority_increases_with_recent_errors():
    calmer_topic = {
        "total_questions": 10,
        "correct_answers": 5,
        "recent_errors": 1,
    }
    unstable_topic = {
        "total_questions": 10,
        "correct_answers": 5,
        "recent_errors": 3,
    }

    assert compute_dynamic_priority(unstable_topic) > compute_dynamic_priority(calmer_topic)


def test_compute_dynamic_priority_handles_missing_fields_safely():
    priority = compute_dynamic_priority({})

    assert isinstance(priority, float)
    assert priority >= 0.0


def test_compute_microtopic_priority_prioritizes_weak_microtopics():
    weak_microtopic = {
        "total_questions": 6,
        "correct_answers": 1,
        "recent_errors": 2,
        "error_distribution": {"conceptual": 2},
    }
    strong_microtopic = {
        "total_questions": 6,
        "correct_answers": 5,
        "recent_errors": 0,
        "error_distribution": {"conceptual": 0},
    }

    assert compute_microtopic_priority(weak_microtopic) > compute_microtopic_priority(strong_microtopic)


def test_aggregate_topic_priority_reflects_mixed_strong_and_weak_microtopics():
    topic_priority = 0.8
    microtopic_scores = [1.5, 0.2, 0.1]

    aggregated = aggregate_topic_priority(topic_priority, microtopic_scores)

    assert aggregated > topic_priority


def test_aggregate_topic_priority_handles_missing_microtopics():
    assert aggregate_topic_priority(0.7, []) == 0.7


def test_aggregate_topic_priority_reduces_pressure_for_mastered_microtopics():
    topic_priority = 0.8

    aggregated = aggregate_topic_priority(topic_priority, [0.05, 0.08, 0.1])

    assert aggregated < topic_priority
    assert aggregated >= topic_priority * 0.75


def test_aggregate_topic_priority_keeps_sparse_microtopic_signal_bounded():
    topic_priority = 0.8

    aggregated = aggregate_topic_priority(topic_priority, [2.4])

    assert aggregated > topic_priority
    assert aggregated <= topic_priority * 1.15


def test_aggregate_topic_priority_prevents_one_extreme_microtopic_from_dominating():
    topic_priority = 0.8

    aggregated = aggregate_topic_priority(topic_priority, [6.0, 0.05, 0.02, 0.01])

    assert aggregated <= topic_priority * 1.25


def test_aggregate_topic_priority_balanced_microtopics_remain_stable():
    topic_priority = 0.8

    aggregated = aggregate_topic_priority(topic_priority, [0.75, 0.8, 0.82])

    assert abs(aggregated - topic_priority) < 0.08


def test_repository_stores_error_classification_distribution(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 26, 12, 0, tzinfo=timezone.utc)

    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id="doc-1",
            topic_id="topic-1",
            selected_answer="B",
            is_correct=False,
            error_type="conceptual",
            created_at=now,
        )
    )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-2",
            document_id="doc-1",
            topic_id="topic-1",
            selected_answer="C",
            is_correct=False,
            error_type=ErrorType.INTERPRETATION,
            created_at=now + timedelta(hours=1),
        )
    )

    progress = repository.load_progress()
    distribution = progress.topic_learning_states["topic-1"].error_distribution

    assert distribution["conceptual"] == 1
    assert distribution["interpretation"] == 1
    assert distribution["attention"] == 0
    assert distribution["memory"] == 0


def test_compute_dynamic_priority_weights_error_types_differently():
    conceptual_heavy = {
        "total_questions": 10,
        "correct_answers": 5,
        "recent_errors": 2,
        "error_distribution": {
            "conceptual": 2,
            "attention": 0,
            "interpretation": 0,
            "memory": 0,
        },
    }
    attention_heavy = {
        "total_questions": 10,
        "correct_answers": 5,
        "recent_errors": 2,
        "error_distribution": {
            "conceptual": 0,
            "attention": 2,
            "interpretation": 0,
            "memory": 0,
        },
    }

    assert compute_dynamic_priority(conceptual_heavy) > compute_dynamic_priority(attention_heavy)


def test_get_dominant_error_type_detects_most_frequent_error():
    performance_data = {
        "error_distribution": {
            "conceptual": 1,
            "attention": 2,
            "interpretation": 4,
            "memory": 3,
        }
    }

    assert get_dominant_error_type(performance_data) == "interpretation"


def test_get_dominant_error_type_handles_missing_distribution():
    assert get_dominant_error_type({}) is None


def test_compute_dynamic_priority_uses_mixed_error_distribution():
    mixed = {
        "total_questions": 12,
        "correct_answers": 6,
        "recent_errors": 2,
        "error_distribution": {
            "conceptual": 1,
            "attention": 1,
            "interpretation": 2,
            "memory": 1,
        },
    }
    no_distribution = {
        "total_questions": 12,
        "correct_answers": 6,
        "recent_errors": 2,
    }

    assert compute_dynamic_priority(mixed) > compute_dynamic_priority(no_distribution)


def test_resolve_study_strategy_maps_each_error_type():
    assert (
        resolve_study_strategy(
            build_plan_entry(
                topic_id="conceptual",
                raw_priority=0.8,
                normalized_priority=0.8,
                dominant_error_type="conceptual",
            )
        )
        == StudyStrategy.THEORY_REVIEW
    )
    assert (
        resolve_study_strategy(
            build_plan_entry(
                topic_id="interpretation",
                raw_priority=0.8,
                normalized_priority=0.8,
                dominant_error_type="interpretation",
            )
        )
        == StudyStrategy.QUESTIONS
    )
    assert (
        resolve_study_strategy(
            build_plan_entry(
                topic_id="memory",
                raw_priority=0.8,
                normalized_priority=0.8,
                dominant_error_type="memory",
            )
        )
        == StudyStrategy.MIXED
    )
    assert (
        resolve_study_strategy(
            build_plan_entry(
                topic_id="attention",
                raw_priority=0.8,
                normalized_priority=0.8,
                dominant_error_type="attention",
            )
        )
        == StudyStrategy.QUICK_REVIEW
    )


def test_resolve_study_strategy_falls_back_to_mixed_when_error_type_is_missing():
    entry = build_plan_entry(topic_id="fallback", raw_priority=0.6, normalized_priority=0.6)

    assert resolve_study_strategy(entry) == StudyStrategy.MIXED


def test_resolve_study_strategy_is_stable_across_priority_ranges():
    high_priority = build_plan_entry(
        topic_id="high",
        raw_priority=0.9,
        normalized_priority=0.9,
        dominant_error_type="interpretation",
    )
    medium_priority = build_plan_entry(
        topic_id="medium",
        raw_priority=0.6,
        normalized_priority=0.6,
        dominant_error_type="interpretation",
    )
    low_priority = build_plan_entry(
        topic_id="low",
        raw_priority=0.2,
        normalized_priority=0.2,
        dominant_error_type="interpretation",
    )

    assert resolve_study_strategy(high_priority) == StudyStrategy.QUESTIONS
    assert resolve_study_strategy(medium_priority) == StudyStrategy.QUESTIONS
    assert resolve_study_strategy(low_priority) == StudyStrategy.QUESTIONS


def test_build_study_blocks_for_theory_review_uses_summary_and_questions():
    entry = build_plan_entry(
        topic_id="theory",
        raw_priority=0.8,
        normalized_priority=0.8,
        study_strategy=StudyStrategy.THEORY_REVIEW,
    )

    blocks = build_study_blocks(entry)

    assert [block.type for block in blocks] == ["summary", "questions"]
    assert blocks[0].depth == "deep"
    assert blocks[1].quantity == 5


def test_build_study_blocks_for_questions_strategy_uses_only_questions():
    entry = build_plan_entry(
        topic_id="questions",
        raw_priority=0.6,
        normalized_priority=0.6,
        study_strategy=StudyStrategy.QUESTIONS,
    )

    blocks = build_study_blocks(entry)

    assert len(blocks) == 1
    assert blocks[0].type == "questions"
    assert blocks[0].quantity == 4


def test_build_study_blocks_for_mixed_strategy_uses_light_summary_and_questions():
    entry = build_plan_entry(
        topic_id="mixed",
        raw_priority=0.3,
        normalized_priority=0.3,
        study_strategy=StudyStrategy.MIXED,
    )

    blocks = build_study_blocks(entry)

    assert [block.type for block in blocks] == ["summary", "questions"]
    assert blocks[0].depth == "light"
    assert blocks[1].quantity == 2


def test_build_study_blocks_for_quick_review_keeps_execution_light():
    entry = build_plan_entry(
        topic_id="quick",
        raw_priority=0.2,
        normalized_priority=0.2,
        study_strategy=StudyStrategy.QUICK_REVIEW,
    )

    blocks = build_study_blocks(entry)

    assert len(blocks) == 1
    assert blocks[0] == StudyBlock(type="summary", topic_id="quick", depth="light")


def test_build_study_blocks_falls_back_to_mixed_for_missing_strategy():
    entry = build_plan_entry(topic_id="fallback-blocks", raw_priority=0.5, normalized_priority=0.5)

    blocks = build_study_blocks(entry)

    assert [block.type for block in blocks] == ["summary", "questions"]
    assert blocks[0].depth == "light"
    assert blocks[1].quantity == 4


def test_build_study_blocks_priority_changes_intensity():
    high = build_plan_entry(
        topic_id="high",
        raw_priority=0.9,
        normalized_priority=0.9,
        study_strategy=StudyStrategy.THEORY_REVIEW,
    )
    medium = build_plan_entry(
        topic_id="medium",
        raw_priority=0.5,
        normalized_priority=0.5,
        study_strategy=StudyStrategy.THEORY_REVIEW,
    )
    low = build_plan_entry(
        topic_id="low",
        raw_priority=0.2,
        normalized_priority=0.2,
        study_strategy=StudyStrategy.THEORY_REVIEW,
    )

    high_blocks = build_study_blocks(high)
    medium_blocks = build_study_blocks(medium)
    low_blocks = build_study_blocks(low)

    assert high_blocks[0].depth == "deep"
    assert high_blocks[1].quantity == 5
    assert medium_blocks[0].depth == "medium"
    assert medium_blocks[1].quantity == 4
    assert low_blocks[0].depth == "light"
    assert low_blocks[1].quantity == 2


def test_build_study_blocks_uses_curriculum_review_intensity_when_present():
    active = build_plan_entry(
        topic_id="active",
        raw_priority=0.3,
        normalized_priority=0.3,
        study_strategy=StudyStrategy.THEORY_REVIEW,
    ).model_copy(update={"curriculum_role": "active", "review_intensity": "deep"})
    cumulative = build_plan_entry(
        topic_id="cumulative",
        raw_priority=0.9,
        normalized_priority=0.9,
        study_strategy=StudyStrategy.MIXED,
    ).model_copy(update={"curriculum_role": "cumulative", "review_intensity": "light"})

    active_blocks = build_study_blocks(active)
    cumulative_blocks = build_study_blocks(cumulative)

    assert active_blocks[0].depth == "deep"
    assert active_blocks[1].quantity == 5
    assert cumulative_blocks[0].depth == "light"
    assert cumulative_blocks[1].quantity == 2


def test_learning_engine_prioritizes_errored_topic_over_only_recent_position(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 24, 15, 0, tzinfo=timezone.utc)

    older = build_document(
        title="Imunidades",
        topic_id="topic-old",
        question_id="q-old",
        created_at=now - timedelta(days=6),
    )
    recent = build_document(
        title="Lancamento",
        topic_id="topic-recent",
        question_id="q-recent",
        created_at=now - timedelta(days=1),
    )
    newest = build_document(
        title="Fiscalizacao",
        topic_id="topic-new",
        question_id="q-new",
        created_at=now - timedelta(hours=3),
    )

    for document in [older, recent, newest]:
        repository.save_document(document)

    for offset in range(3):
        repository.record_answer(
            AnswerSubmission(
                question_id="q-old",
                document_id=older.id,
                topic_id="topic-old",
                selected_answer="B",
                is_correct=False,
                error_type=ErrorType.KNOWLEDGE_GAP,
                created_at=now - timedelta(hours=offset + 1),
            )
        )

    engine = LearningDecisionEngine(repository, now_provider=lambda: now)

    plan = engine.build_review_plan(title="Revisao diaria", max_questions=4)

    assert plan.entries
    assert plan.entries[0].topic_id == "topic-old"
    assert any("erro" in reason.lower() for reason in plan.entries[0].reasons)


def test_learning_engine_assigns_curriculum_role_and_intensity_by_recency(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 24, 15, 30, tzinfo=timezone.utc)

    documents = [
        build_document(
            title=f"Tema {index}",
            topic_id=f"topic-{index}",
            question_id=f"q-{index}",
            created_at=now - timedelta(days=5 - index),
        )
        for index in range(6)
    ]
    for document in documents:
        repository.save_document(document)

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Curriculo",
        max_questions=6,
    )

    by_topic = {entry.topic_id: entry for entry in plan.entries}

    assert by_topic["topic-5"].curriculum_role == "active"
    assert by_topic["topic-5"].review_intensity == "deep"
    assert by_topic["topic-1"].curriculum_role == "cumulative"
    assert by_topic["topic-1"].review_intensity == "light"


def test_learning_engine_reintensifies_weak_cumulative_topics_without_breaking_curriculum(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 24, 16, 0, tzinfo=timezone.utc)

    documents = [
        build_document(
            title=f"Tema {index}",
            topic_id=f"topic-{index}",
            question_id=f"q-{index}",
            created_at=now - timedelta(days=5 - index),
        )
        for index in range(6)
    ]
    for document in documents:
        repository.save_document(document)

    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id=documents[1].id,
            topic_id="topic-1",
            microtopic_id="topic-1:weak",
            selected_answer="B",
            is_correct=False,
            error_type=ErrorType.CONCEPT_CONFUSION,
            created_at=now - timedelta(hours=2),
        )
    )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id=documents[1].id,
            topic_id="topic-1",
            microtopic_id="topic-1:weak",
            selected_answer="B",
            is_correct=False,
            error_type=ErrorType.CONCEPT_CONFUSION,
            created_at=now - timedelta(hours=1),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Curriculo adaptativo",
        max_questions=6,
    )

    topic_entry = next(entry for entry in plan.entries if entry.topic_id == "topic-1")

    assert topic_entry.curriculum_role == "cumulative"
    assert topic_entry.review_intensity in {"medium", "deep"}


def test_learning_engine_uses_weak_microtopics_to_break_topic_level_ties(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 24, 16, 0, tzinfo=timezone.utc)

    topic_a = build_document(
        title="Tema A",
        topic_id="topic-a",
        question_id="q-a",
        created_at=now - timedelta(days=1),
    )
    topic_b = build_document(
        title="Tema B",
        topic_id="topic-b",
        question_id="q-b",
        created_at=now - timedelta(days=1),
    )
    repository.save_document(topic_a)
    repository.save_document(topic_b)

    for index, question_id in enumerate(["q-a", "q-a", "q-a", "q-a-2"]):
        repository.record_answer(
            AnswerSubmission(
                question_id=question_id,
                document_id=topic_a.id,
                topic_id="topic-a",
                microtopic_id="topic-a:weak" if index < 2 else "topic-a:stable",
                selected_answer="B" if index < 2 else "A",
                is_correct=index >= 2,
                error_type=ErrorType.CONCEPT_CONFUSION if index < 2 else None,
                created_at=now - timedelta(hours=4 - index),
            )
        )

    for index, question_id in enumerate(["q-b", "q-b", "q-b-2", "q-b-2"]):
        repository.record_answer(
            AnswerSubmission(
                question_id=question_id,
                document_id=topic_b.id,
                topic_id="topic-b",
                microtopic_id="topic-b:m1" if index < 2 else "topic-b:m2",
                selected_answer="B" if index % 2 == 0 else "A",
                is_correct=index % 2 == 1,
                error_type=ErrorType.CONCEPT_CONFUSION if index % 2 == 0 else None,
                created_at=now - timedelta(hours=4 - index),
            )
        )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Empate por topico",
        max_questions=4,
    )

    assert plan.entries[0].topic_id == "topic-a"
    assert (
        plan.entries[0].score_breakdown["microtopic_adjusted_priority"]
        > plan.entries[1].score_breakdown["microtopic_adjusted_priority"]
    )


def test_learning_engine_preserves_base_priority_when_microtopic_data_is_missing(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 24, 16, 30, tzinfo=timezone.utc)
    document = build_document(
        title="Tema Sem Micro",
        topic_id="topic-no-micro",
        question_id="q-1",
        created_at=now - timedelta(hours=2),
    )
    repository.save_document(document)

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Sem microdados",
        max_questions=2,
    )

    entry = plan.entries[0]

    assert entry.score_breakdown["microtopic_adjustment"] == 0.0
    assert (
        entry.score_breakdown["dynamic_priority"]
        == round(
            entry.score_breakdown["topic_dynamic_priority"]
            + entry.score_breakdown["curriculum_adjustment"],
            4,
        )
    )


def test_learning_engine_extreme_single_microtopic_does_not_overturn_stronger_base_topic(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 24, 17, 0, tzinfo=timezone.utc)

    stronger_base = build_document(
        title="Base Forte",
        topic_id="topic-strong-base",
        question_id="q-strong",
        created_at=now - timedelta(days=2),
    )
    weaker_base = build_document(
        title="Base Media",
        topic_id="topic-medium-base",
        question_id="q-medium",
        created_at=now - timedelta(days=1),
    )
    repository.save_document(stronger_base)
    repository.save_document(weaker_base)

    for offset in range(3):
        repository.record_answer(
            AnswerSubmission(
                question_id="q-strong",
                document_id=stronger_base.id,
                topic_id="topic-strong-base",
                microtopic_id="topic-strong-base:balanced",
                selected_answer="B",
                is_correct=False,
                error_type=ErrorType.INTERPRETATION,
                created_at=now - timedelta(hours=offset + 1),
            )
        )

    repository.record_answer(
        AnswerSubmission(
            question_id="q-medium",
            document_id=weaker_base.id,
            topic_id="topic-medium-base",
            microtopic_id="topic-medium-base:extreme",
            selected_answer="B",
            is_correct=False,
            error_type=ErrorType.CONCEPT_CONFUSION,
            created_at=now - timedelta(hours=1),
        )
    )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-medium-2",
            document_id=weaker_base.id,
            topic_id="topic-medium-base",
            microtopic_id="topic-medium-base:recovered",
            selected_answer="A",
            is_correct=True,
            error_type=None,
            created_at=now - timedelta(minutes=20),
        )
    )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-medium-3",
            document_id=weaker_base.id,
            topic_id="topic-medium-base",
            microtopic_id="topic-medium-base:extreme",
            selected_answer="B",
            is_correct=False,
            error_type=ErrorType.CONCEPT_CONFUSION,
            created_at=now - timedelta(minutes=5),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Oscilacao controlada",
        max_questions=4,
    )

    assert plan.entries[0].topic_id == "topic-strong-base"
    assert (
        plan.entries[1].score_breakdown["microtopic_adjusted_priority"]
        <= plan.entries[1].score_breakdown["topic_dynamic_priority"] * 1.25
    )


def test_learning_engine_applies_repetition_penalty_and_prefers_less_seen_item(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 24, 18, 0, tzinfo=timezone.utc)

    document = build_document(
        title="Obrigacao",
        topic_id="topic-1",
        question_id="q-1",
        created_at=now - timedelta(days=1),
    )
    alternate_question = GeneratedQuestion(
        id="q-2",
        document_id=document.id,
        topic_id="topic-1",
        style="multiple_choice",
        stem="Questao alternativa",
        options=["A", "B", "C", "D"],
        correct_answer="B",
        explanation="Explicacao alternativa",
        difficulty_level=2,
    )
    document.questions.append(alternate_question)
    repository.save_document(document)

    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id=document.id,
            topic_id="topic-1",
            selected_answer="A",
            is_correct=True,
            error_type=None,
            created_at=now - timedelta(hours=1),
        )
    )

    engine = LearningDecisionEngine(repository, now_provider=lambda: now)

    plan = engine.build_review_plan(title="Revisao diaria", max_questions=2)

    assert plan.entries[0].question_ids[0] == "q-2"


def test_learning_engine_increases_recommended_difficulty_after_correct_streak(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 24, 19, 0, tzinfo=timezone.utc)
    document = build_document(
        title="Credito Tributario",
        topic_id="topic-1",
        question_id="q-1",
        created_at=now - timedelta(days=2),
    )
    hard_question = GeneratedQuestion(
        id="q-hard",
        document_id=document.id,
        topic_id="topic-1",
        style="multiple_choice",
        stem="Questao comparativa dificil",
        options=["A", "B", "C", "D"],
        correct_answer="D",
        explanation="Explicacao dificil",
        difficulty_level=3,
    )
    document.questions.append(hard_question)
    repository.save_document(document)

    for offset in range(4):
        repository.record_answer(
            AnswerSubmission(
                question_id="q-1",
                document_id=document.id,
                topic_id="topic-1",
                selected_answer="A",
                is_correct=True,
                error_type=None,
                created_at=now - timedelta(days=4 - offset),
            )
        )

    engine = LearningDecisionEngine(repository, now_provider=lambda: now)

    plan = engine.build_review_plan(title="Revisao diaria", max_questions=2)

    assert plan.entries[0].recommended_difficulty >= 2


def test_review_service_uses_learning_engine_instead_of_position_only(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 24, 20, 0, tzinfo=timezone.utc)

    documents = [
        build_document(
            title="Tema Antigo Critico",
            topic_id="topic-critical",
            question_id="q-critical",
            created_at=now - timedelta(days=8),
        ),
        build_document(
            title="Tema Medio",
            topic_id="topic-middle",
            question_id="q-middle",
            created_at=now - timedelta(days=2),
        ),
        build_document(
            title="Tema Novo 1",
            topic_id="topic-new-1",
            question_id="q-new-1",
            created_at=now - timedelta(hours=8),
        ),
        build_document(
            title="Tema Novo 2",
            topic_id="topic-new-2",
            question_id="q-new-2",
            created_at=now - timedelta(hours=2),
        ),
    ]
    for document in documents:
        repository.save_document(document)

    repository.record_answer(
        AnswerSubmission(
            question_id="q-critical",
            document_id=documents[0].id,
            topic_id="topic-critical",
            selected_answer="C",
            is_correct=False,
            error_type=ErrorType.INTERPRETATION,
            created_at=now - timedelta(minutes=30),
        )
    )

    review = ReviewService(repository, now_provider=lambda: now).build_daily_review()

    assert any(question.id == "q-critical" for question in review.questions)
    assert "Tema Antigo Critico" in review.documents_considered


def test_learning_engine_normalizes_priority_scores_between_topics(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 10, 0, tzinfo=timezone.utc)

    documents = [
        build_document(
            title="Tema Forte",
            topic_id="topic-high",
            question_id="q-high",
            created_at=now - timedelta(days=5),
        ),
        build_document(
            title="Tema Medio",
            topic_id="topic-mid",
            question_id="q-mid",
            created_at=now - timedelta(days=2),
        ),
        build_document(
            title="Tema Fraco",
            topic_id="topic-low",
            question_id="q-low",
            created_at=now - timedelta(hours=8),
        ),
    ]
    for document in documents:
        repository.save_document(document)

    for offset in range(6):
        repository.record_answer(
            AnswerSubmission(
                question_id="q-high",
                document_id=documents[0].id,
                topic_id="topic-high",
                selected_answer="B",
                is_correct=False,
                error_type=ErrorType.KNOWLEDGE_GAP,
                created_at=now - timedelta(days=1, hours=offset),
            )
        )
    for offset in range(2):
        repository.record_answer(
            AnswerSubmission(
                question_id="q-mid",
                document_id=documents[1].id,
                topic_id="topic-mid",
                selected_answer="B",
                is_correct=False,
                error_type=ErrorType.INTERPRETATION,
                created_at=now - timedelta(days=2, hours=offset),
            )
        )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-low",
            document_id=documents[2].id,
            topic_id="topic-low",
            selected_answer="A",
            is_correct=True,
            error_type=None,
            created_at=now - timedelta(hours=3),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=4,
    )

    scores = {entry.topic_id: entry.priority_score for entry in plan.entries}

    assert all(0.0 <= score <= 1.0 for score in scores.values())
    assert "topic-low" not in scores
    assert scores["topic-high"] > scores["topic-mid"]
    assert scores["topic-high"] - scores["topic-mid"] < 0.6


def test_learning_engine_avoids_same_similarity_group_in_single_session(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 11, 0, tzinfo=timezone.utc)
    document = build_document(
        title="Tema Com Grupo",
        topic_id="topic-group",
        question_id="q-group-1",
        created_at=now - timedelta(days=1),
    )
    document.questions[0].similarity_group = "grupo-a"
    document.questions.append(
        GeneratedQuestion(
            id="q-group-2",
            document_id=document.id,
            topic_id="topic-group",
            style="multiple_choice",
            stem="Questao quase igual",
            options=["A", "B", "C", "D"],
            correct_answer="B",
            explanation="Explicacao",
            difficulty_level=1,
            similarity_group="grupo-a",
        )
    )
    document.questions.append(
        GeneratedQuestion(
            id="q-group-3",
            document_id=document.id,
            topic_id="topic-group",
            style="multiple_choice",
            stem="Questao diferente",
            options=["A", "B", "C", "D"],
            correct_answer="C",
            explanation="Explicacao",
            difficulty_level=2,
            similarity_group="grupo-b",
        )
    )
    repository.save_document(document)

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=3,
    )

    assert plan.entries
    assert plan.entries[0].question_ids == ["q-group-1", "q-group-3"]


def test_learning_engine_guarantees_topic_diversity_before_extra_same_topic_items(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 12, 0, tzinfo=timezone.utc)
    first = build_document(
        title="Tema 1",
        topic_id="topic-1",
        question_id="q-1a",
        created_at=now - timedelta(days=2),
    )
    first.questions.append(
        GeneratedQuestion(
            id="q-1b",
            document_id=first.id,
            topic_id="topic-1",
            style="multiple_choice",
            stem="Questao extra do tema 1",
            options=["A", "B", "C", "D"],
            correct_answer="A",
            explanation="Explicacao",
            difficulty_level=2,
            similarity_group="t1-b",
        )
    )
    second = build_document(
        title="Tema 2",
        topic_id="topic-2",
        question_id="q-2a",
        created_at=now - timedelta(days=1),
    )
    repository.save_document(first)
    repository.save_document(second)
    repository.record_answer(
        AnswerSubmission(
            question_id="q-1a",
            document_id=first.id,
            topic_id="topic-1",
            selected_answer="B",
            is_correct=False,
            error_type=ErrorType.KNOWLEDGE_GAP,
            created_at=now - timedelta(hours=18),
        )
    )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-2a",
            document_id=second.id,
            topic_id="topic-2",
            selected_answer="C",
            is_correct=False,
            error_type=ErrorType.INTERPRETATION,
            created_at=now - timedelta(hours=16),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=3,
    )

    assert [entry.topic_id for entry in plan.entries[:2]] == ["topic-1", "topic-2"]


def test_learning_engine_reduces_difficulty_after_interpretation_errors(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 13, 0, tzinfo=timezone.utc)
    document = build_document(
        title="Tema Interpretacao",
        topic_id="topic-1",
        question_id="q-base",
        created_at=now - timedelta(days=3),
    )
    document.questions.append(
        GeneratedQuestion(
            id="q-hard",
            document_id=document.id,
            topic_id="topic-1",
            style="multiple_choice",
            stem="Questao mais dificil",
            options=["A", "B", "C", "D"],
            correct_answer="D",
            explanation="Explicacao",
            difficulty_level=3,
            similarity_group="hard",
        )
    )
    repository.save_document(document)

    for offset in range(3):
        repository.record_answer(
            AnswerSubmission(
                question_id="q-hard",
                document_id=document.id,
                topic_id="topic-1",
                selected_answer="A",
                is_correct=False,
                error_type=ErrorType.INTERPRETATION,
                created_at=now - timedelta(hours=offset + 2),
            )
        )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=2,
    )

    assert plan.entries[0].recommended_difficulty == 1


def test_learning_engine_requires_consistent_success_over_time_for_higher_difficulty(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 14, 0, tzinfo=timezone.utc)
    document = build_document(
        title="Tema Consistencia",
        topic_id="topic-1",
        question_id="q-1",
        created_at=now - timedelta(days=10),
    )
    document.questions.append(
        GeneratedQuestion(
            id="q-advanced",
            document_id=document.id,
            topic_id="topic-1",
            style="multiple_choice",
            stem="Questao avancada",
            options=["A", "B", "C", "D"],
            correct_answer="C",
            explanation="Explicacao",
            difficulty_level=3,
            similarity_group="advanced",
        )
    )
    repository.save_document(document)

    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id=document.id,
            topic_id="topic-1",
            selected_answer="A",
            is_correct=True,
            error_type=None,
            created_at=now - timedelta(days=10),
        )
    )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id=document.id,
            topic_id="topic-1",
            selected_answer="A",
            is_correct=True,
            error_type=None,
            created_at=now - timedelta(minutes=20),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=2,
    )

    assert plan.entries[0].recommended_difficulty == 1


def test_learning_plan_exposes_detailed_score_breakdown_and_item_reasons(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 15, 0, tzinfo=timezone.utc)
    document = build_document(
        title="Tema Explicavel",
        topic_id="topic-1",
        question_id="q-1",
        created_at=now - timedelta(days=4),
    )
    document.questions.append(
        GeneratedQuestion(
            id="q-2",
            document_id=document.id,
            topic_id="topic-1",
            style="multiple_choice",
            stem="Questao 2",
            options=["A", "B", "C", "D"],
            correct_answer="B",
            explanation="Explicacao",
            difficulty_level=2,
            similarity_group="b",
        )
    )
    repository.save_document(document)
    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id=document.id,
            topic_id="topic-1",
            selected_answer="D",
            is_correct=False,
            error_type=ErrorType.CONCEPT_CONFUSION,
            created_at=now - timedelta(hours=2),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=2,
    )

    entry = plan.entries[0]
    assert "error_pressure" in entry.score_breakdown
    assert "normalized_priority" in entry.score_breakdown
    assert entry.item_reasons
    assert "q-2" in entry.item_reasons
    assert any("repet" in reason.lower() or "novo" in reason.lower() for reason in entry.item_reasons["q-2"])
    assert entry.study_strategy is not None


def test_learning_plan_entry_receives_strategy_from_dominant_error_type(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 15, 30, tzinfo=timezone.utc)
    document = build_document(
        title="Tema Conceitual",
        topic_id="topic-conceptual",
        question_id="q-1",
        created_at=now - timedelta(days=2),
    )
    repository.save_document(document)
    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id=document.id,
            topic_id="topic-conceptual",
            selected_answer="D",
            is_correct=False,
            error_type="conceptual",
            created_at=now - timedelta(hours=3),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=2,
    )

    assert plan.entries
    assert plan.entries[0].dominant_error_type == "conceptual"
    assert plan.entries[0].study_strategy == StudyStrategy.THEORY_REVIEW
    assert [block.type for block in plan.entries[0].study_blocks] == ["summary", "questions"]


def test_learning_engine_builds_full_plan_with_strategy_per_topic(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 15, 45, tzinfo=timezone.utc)

    conceptual_doc = build_document(
        title="Tema Conceitual",
        topic_id="topic-conceptual",
        question_id="q-conceptual",
        created_at=now - timedelta(days=3),
    )
    attention_doc = build_document(
        title="Tema Atencao",
        topic_id="topic-attention",
        question_id="q-attention",
        created_at=now - timedelta(days=1),
    )
    repository.save_document(conceptual_doc)
    repository.save_document(attention_doc)

    repository.record_answer(
        AnswerSubmission(
            question_id="q-conceptual",
            document_id=conceptual_doc.id,
            topic_id="topic-conceptual",
            selected_answer="B",
            is_correct=False,
            error_type="conceptual",
            created_at=now - timedelta(hours=8),
        )
    )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-attention",
            document_id=attention_doc.id,
            topic_id="topic-attention",
            selected_answer="C",
            is_correct=False,
            error_type="attention",
            created_at=now - timedelta(hours=6),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=4,
    )

    strategies = {entry.topic_id: entry.study_strategy for entry in plan.entries}

    assert strategies["topic-conceptual"] == StudyStrategy.THEORY_REVIEW
    assert strategies["topic-attention"] == StudyStrategy.QUICK_REVIEW


def test_learning_plan_entry_receives_study_blocks(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 15, 50, tzinfo=timezone.utc)
    document = build_document(
        title="Tema Interpretacao",
        topic_id="topic-interpretation",
        question_id="q-1",
        created_at=now - timedelta(days=2),
    )
    repository.save_document(document)
    repository.record_answer(
        AnswerSubmission(
            question_id="q-1",
            document_id=document.id,
            topic_id="topic-interpretation",
            selected_answer="D",
            is_correct=False,
            error_type="interpretation",
            created_at=now - timedelta(hours=4),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=2,
    )

    entry = plan.entries[0]
    assert entry.study_strategy == StudyStrategy.QUESTIONS
    assert len(entry.study_blocks) == 1
    assert entry.study_blocks[0].type == "questions"
    assert entry.study_blocks[0].quantity >= 1


def test_learning_engine_builds_full_plan_with_blocks_per_topic(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 16, 0, tzinfo=timezone.utc)

    conceptual_doc = build_document(
        title="Tema Conceitual",
        topic_id="topic-conceptual",
        question_id="q-conceptual",
        created_at=now - timedelta(days=3),
    )
    memory_doc = build_document(
        title="Tema Memoria",
        topic_id="topic-memory",
        question_id="q-memory",
        created_at=now - timedelta(days=1),
    )
    repository.save_document(conceptual_doc)
    repository.save_document(memory_doc)

    repository.record_answer(
        AnswerSubmission(
            question_id="q-conceptual",
            document_id=conceptual_doc.id,
            topic_id="topic-conceptual",
            selected_answer="B",
            is_correct=False,
            error_type="conceptual",
            created_at=now - timedelta(hours=8),
        )
    )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-memory",
            document_id=memory_doc.id,
            topic_id="topic-memory",
            selected_answer="C",
            is_correct=False,
            error_type="memory",
            created_at=now - timedelta(hours=6),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=4,
    )

    blocks_by_topic = {entry.topic_id: entry.study_blocks for entry in plan.entries}

    assert [block.type for block in blocks_by_topic["topic-conceptual"]] == ["summary", "questions"]
    assert [block.type for block in blocks_by_topic["topic-memory"]] == ["summary", "questions"]


def test_learning_engine_does_not_fill_session_with_near_zero_priority_topics(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 16, 0, tzinfo=timezone.utc)

    documents = [
        build_document(
            title="Fraqueza Forte 1",
            topic_id="focus-1",
            question_id="q-focus-1",
            created_at=now - timedelta(days=6),
        ),
        build_document(
            title="Fraqueza Forte 2",
            topic_id="focus-2",
            question_id="q-focus-2",
            created_at=now - timedelta(days=2),
        ),
        build_document(
            title="Tema Residual",
            topic_id="low-1",
            question_id="q-low-1",
            created_at=now - timedelta(hours=5),
        ),
    ]
    for document in documents:
        repository.save_document(document)

    for hours in [2, 6, 12, 18]:
        repository.record_answer(
            AnswerSubmission(
                question_id="q-focus-1",
                document_id=documents[0].id,
                topic_id="focus-1",
                selected_answer="C",
                is_correct=False,
                error_type=ErrorType.KNOWLEDGE_GAP,
                created_at=now - timedelta(hours=hours),
            )
        )
    for hours in [4, 10]:
        repository.record_answer(
            AnswerSubmission(
                question_id="q-focus-2",
                document_id=documents[1].id,
                topic_id="focus-2",
                selected_answer="D",
                is_correct=False,
                error_type=ErrorType.INTERPRETATION,
                created_at=now - timedelta(hours=hours),
            )
        )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-low-1",
            document_id=documents[2].id,
            topic_id="low-1",
            selected_answer="A",
            is_correct=True,
            error_type=None,
            created_at=now - timedelta(hours=1),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=5,
    )

    assert len(plan.entries) == 2
    assert {entry.topic_id for entry in plan.entries} == {"focus-1", "focus-2"}
    assert all(entry.priority_score >= 0.25 for entry in plan.entries)


def test_learning_engine_keeps_diversity_when_scores_are_balanced(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 17, 0, tzinfo=timezone.utc)

    documents = [
        build_document(
            title="Tema Balanceado 1",
            topic_id="balanced-1",
            question_id="q-balanced-1",
            created_at=now - timedelta(days=4),
        ),
        build_document(
            title="Tema Balanceado 2",
            topic_id="balanced-2",
            question_id="q-balanced-2",
            created_at=now - timedelta(days=2),
        ),
        build_document(
            title="Tema Balanceado 3",
            topic_id="balanced-3",
            question_id="q-balanced-3",
            created_at=now - timedelta(days=1),
        ),
    ]
    for document in documents:
        repository.save_document(document)

    attempts = [
        ("q-balanced-1", documents[0].id, "balanced-1", ErrorType.KNOWLEDGE_GAP, now - timedelta(hours=30)),
        ("q-balanced-1", documents[0].id, "balanced-1", ErrorType.KNOWLEDGE_GAP, now - timedelta(hours=22)),
        ("q-balanced-1", documents[0].id, "balanced-1", ErrorType.KNOWLEDGE_GAP, now - timedelta(hours=16)),
        ("q-balanced-1", documents[0].id, "balanced-1", ErrorType.KNOWLEDGE_GAP, now - timedelta(hours=14)),
        ("q-balanced-1", documents[0].id, "balanced-1", ErrorType.KNOWLEDGE_GAP, now - timedelta(hours=13)),
        ("q-balanced-2", documents[1].id, "balanced-2", ErrorType.INTERPRETATION, now - timedelta(hours=28)),
        ("q-balanced-2", documents[1].id, "balanced-2", ErrorType.INTERPRETATION, now - timedelta(hours=20)),
        ("q-balanced-2", documents[1].id, "balanced-2", ErrorType.INTERPRETATION, now - timedelta(hours=15)),
        ("q-balanced-2", documents[1].id, "balanced-2", ErrorType.INTERPRETATION, now - timedelta(hours=13)),
        ("q-balanced-3", documents[2].id, "balanced-3", ErrorType.DISTRACTION, now - timedelta(hours=26)),
        ("q-balanced-3", documents[2].id, "balanced-3", ErrorType.DISTRACTION, now - timedelta(hours=18)),
        ("q-balanced-3", documents[2].id, "balanced-3", ErrorType.DISTRACTION, now - timedelta(hours=12)),
        ("q-balanced-3", documents[2].id, "balanced-3", ErrorType.DISTRACTION, now - timedelta(hours=10)),
    ]
    for question_id, document_id, topic_id, error_type, created_at in attempts:
        repository.record_answer(
            AnswerSubmission(
                question_id=question_id,
                document_id=document_id,
                topic_id=topic_id,
                selected_answer="B",
                is_correct=False,
                error_type=error_type,
                created_at=created_at,
            )
        )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=5,
    )

    assert len(plan.entries) == 3
    assert {entry.topic_id for entry in plan.entries} == {
        "balanced-1",
        "balanced-2",
        "balanced-3",
    }
    assert all(
        entry.score_breakdown["normalized_priority"] >= 0.15
        for entry in plan.entries
    )


def test_learning_engine_excludes_topics_below_minimum_normalized_priority(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 4, 25, 18, 30, tzinfo=timezone.utc)

    documents = [
        build_document(
            title="Topico Forte",
            topic_id="strong",
            question_id="q-strong",
            created_at=now - timedelta(days=4),
        ),
        build_document(
            title="Topico Medio",
            topic_id="medium",
            question_id="q-medium",
            created_at=now - timedelta(days=2),
        ),
        build_document(
            title="Topico Irrelevante",
            topic_id="irrelevant",
            question_id="q-irrelevant",
            created_at=now - timedelta(hours=4),
        ),
    ]
    for document in documents:
        repository.save_document(document)

    for hours in [3, 8, 16, 24]:
        repository.record_answer(
            AnswerSubmission(
                question_id="q-strong",
                document_id=documents[0].id,
                topic_id="strong",
                selected_answer="B",
                is_correct=False,
                error_type=ErrorType.KNOWLEDGE_GAP,
                created_at=now - timedelta(hours=hours),
            )
        )
    for hours in [6, 18]:
        repository.record_answer(
            AnswerSubmission(
                question_id="q-medium",
                document_id=documents[1].id,
                topic_id="medium",
                selected_answer="C",
                is_correct=False,
                error_type=ErrorType.INTERPRETATION,
                created_at=now - timedelta(hours=hours),
            )
        )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-irrelevant",
            document_id=documents[2].id,
            topic_id="irrelevant",
            selected_answer="A",
            is_correct=True,
            error_type=None,
            created_at=now - timedelta(hours=1),
        )
    )

    plan = LearningDecisionEngine(repository, now_provider=lambda: now).build_review_plan(
        title="Revisao diaria",
        max_questions=5,
    )

    assert {entry.topic_id for entry in plan.entries} == {"strong", "medium"}
    assert all(
        entry.score_breakdown["normalized_priority"] >= 0.15
        for entry in plan.entries
    )


def test_trim_entries_stops_selection_on_abrupt_consecutive_raw_priority_drop(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    engine = LearningDecisionEngine(repository)

    entries = [
        build_plan_entry(topic_id="t1", raw_priority=0.90, normalized_priority=1.0),
        build_plan_entry(topic_id="t2", raw_priority=0.75, normalized_priority=0.72),
        build_plan_entry(topic_id="t3", raw_priority=0.30, normalized_priority=0.18),
    ]

    trimmed = engine._trim_entries(entries, max_questions=5)

    assert [entry.topic_id for entry in trimmed] == ["t1", "t2"]


def test_trim_entries_keeps_selection_when_consecutive_drop_is_balanced(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    engine = LearningDecisionEngine(repository)

    entries = [
        build_plan_entry(topic_id="t1", raw_priority=0.90, normalized_priority=1.0),
        build_plan_entry(topic_id="t2", raw_priority=0.72, normalized_priority=0.74),
        build_plan_entry(topic_id="t3", raw_priority=0.55, normalized_priority=0.42),
    ]

    trimmed = engine._trim_entries(entries, max_questions=5)

    assert [entry.topic_id for entry in trimmed] == ["t1", "t2", "t3"]


def test_trim_entries_keeps_moderately_relevant_candidate_even_after_local_drop(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    engine = LearningDecisionEngine(repository)

    entries = [
        build_plan_entry(topic_id="t1", raw_priority=0.90, normalized_priority=1.0),
        build_plan_entry(topic_id="t2", raw_priority=0.70, normalized_priority=0.74),
        build_plan_entry(topic_id="t3", raw_priority=0.37, normalized_priority=0.41),
    ]

    trimmed = engine._trim_entries(entries, max_questions=5)

    assert [entry.topic_id for entry in trimmed] == ["t1", "t2", "t3"]


def test_trim_entries_cuts_weak_tail_when_local_drop_and_top_relevance_are_both_low(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    engine = LearningDecisionEngine(repository)

    entries = [
        build_plan_entry(topic_id="t1", raw_priority=0.90, normalized_priority=1.0),
        build_plan_entry(topic_id="t2", raw_priority=0.72, normalized_priority=0.77),
        build_plan_entry(topic_id="t3", raw_priority=0.30, normalized_priority=0.2),
    ]

    trimmed = engine._trim_entries(entries, max_questions=5)

    assert [entry.topic_id for entry in trimmed] == ["t1", "t2"]


def test_trim_entries_keeps_uniform_distribution_without_premature_stop(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    engine = LearningDecisionEngine(repository)

    entries = [
        build_plan_entry(topic_id="t1", raw_priority=0.82, normalized_priority=1.0),
        build_plan_entry(topic_id="t2", raw_priority=0.74, normalized_priority=0.86),
        build_plan_entry(topic_id="t3", raw_priority=0.66, normalized_priority=0.71),
    ]

    trimmed = engine._trim_entries(entries, max_questions=5)

    assert [entry.topic_id for entry in trimmed] == ["t1", "t2", "t3"]


def test_trim_entries_case_moderate_candidate_must_remain(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    engine = LearningDecisionEngine(repository)

    entries = [
        build_plan_entry(topic_id="A", raw_priority=0.65, normalized_priority=1.0),
        build_plan_entry(topic_id="B", raw_priority=0.35, normalized_priority=0.56),
        build_plan_entry(topic_id="C", raw_priority=0.23, normalized_priority=0.28),
    ]

    trimmed = engine._trim_entries(entries, max_questions=5)

    assert [entry.topic_id for entry in trimmed] == ["A", "B"]


def test_trim_entries_case_weak_tail_must_be_cut(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    engine = LearningDecisionEngine(repository)

    entries = [
        build_plan_entry(topic_id="A", raw_priority=0.70, normalized_priority=1.0),
        build_plan_entry(topic_id="B", raw_priority=0.50, normalized_priority=0.67),
        build_plan_entry(topic_id="C", raw_priority=0.10, normalized_priority=0.0),
    ]

    trimmed = engine._trim_entries(entries, max_questions=5)

    assert [entry.topic_id for entry in trimmed] == ["A", "B"]


def test_trim_entries_case_uniform_distribution_has_no_cut(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    engine = LearningDecisionEngine(repository)

    entries = [
        build_plan_entry(topic_id="A", raw_priority=0.50, normalized_priority=1.0),
        build_plan_entry(topic_id="B", raw_priority=0.45, normalized_priority=0.63),
        build_plan_entry(topic_id="C", raw_priority=0.42, normalized_priority=0.41),
    ]

    trimmed = engine._trim_entries(entries, max_questions=5)

    assert [entry.topic_id for entry in trimmed] == ["A", "B", "C"]


def test_trim_entries_case_strong_drop_advanced_user_keeps_only_top(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    engine = LearningDecisionEngine(repository)

    entries = [
        build_plan_entry(topic_id="Top", raw_priority=0.85, normalized_priority=1.0),
        build_plan_entry(topic_id="Mid", raw_priority=0.16, normalized_priority=0.12),
        build_plan_entry(topic_id="Low", raw_priority=0.07, normalized_priority=0.0),
    ]

    trimmed = engine._trim_entries(entries, max_questions=5)

    assert [entry.topic_id for entry in trimmed] == ["Top"]


def test_build_study_blocks_propagates_pedagogical_memory_to_runtime_blocks():
    entry = LearningPlanEntry(
        document_id="doc-1",
        document_title="Doc 1",
        topic_id="topic-1",
        topic_title="Topic 1",
        topic_content="Conceito: regra.\n\nAplicacao: caso pratico.",
        question_ids=["q-1"],
        priority_score=0.8,
        recommended_difficulty=1,
        reasons=[],
        score_breakdown={"raw_priority": 0.8, "normalized_priority": 0.8},
        item_reasons={"q-1": []},
        curriculum_role="active",
        review_intensity="deep",
        study_strategy=StudyStrategy.MIXED.value,
        performance_data={
            "microtopic_performance": {
                "micro-1": {"total_questions": 1, "correct_answers": 0, "recent_errors": 1}
            },
                "pedagogical_memory": {
                    "micro-1": {
                        "microtopic_id": "micro-1",
                        "topic_id": "topic-1",
                        "last_pedagogical_mode": "active_recall",
                        "recent_effectiveness": "ineffective",
                        "resurfacing_cycles": 2,
                    }
                },
            },
        )

    blocks = build_study_blocks(entry)

    assert blocks
    assert all("micro-1" in block.pedagogical_memory for block in blocks)


def test_build_study_blocks_preserves_longitudinal_memory_fields():
    entry = LearningPlanEntry(
        document_id="doc-2",
        document_title="Doc 2",
        topic_id="topic-2",
        topic_title="Topic 2",
        topic_content="Conceito: regra.\n\nAplicacao: caso.",
        question_ids=["q-2"],
        priority_score=0.6,
        recommended_difficulty=1,
        reasons=[],
        score_breakdown={"raw_priority": 0.6, "normalized_priority": 0.6},
        item_reasons={"q-2": []},
        curriculum_role="cumulative",
        review_intensity="light",
        study_strategy=StudyStrategy.QUICK_REVIEW.value,
        performance_data={
            "pedagogical_memory": {
                "micro-2": {
                    "microtopic_id": "micro-2",
                    "topic_id": "topic-2",
                    "stabilization_level": 0.7,
                    "fatigue_exposure": 0.25,
                    "resurfacing_cycles": 4,
                    "successful_resurfacing_cycles": 3,
                }
            },
        },
    )

    block = build_study_blocks(entry)[0]

    assert block.pedagogical_memory["micro-2"]["stabilization_level"] == 0.7
    assert block.pedagogical_memory["micro-2"]["fatigue_exposure"] == 0.25
