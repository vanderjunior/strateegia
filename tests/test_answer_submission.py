from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.domain.models import AnswerSubmission, BoardStyle, Document, GeneratedQuestion, StudyStrategy, Topic
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.content_execution import execute_learning_plan
from app.services.learning_engine import LearningDecisionEngine


def build_document(*, title: str, topic_id: str, question_id: str, created_at: datetime) -> Document:
    topic = Topic(
        id=topic_id,
        title=title,
        content=(
            f"{title} exige precisao conceitual, leitura cuidadosa e atencao a excecoes. "
            f"{title} aparece em prova com comparacoes tecnicas e pegadinhas normativas."
        ),
        key_points=[f"Ponto central de {title}"],
        trap_points=[f"Pegadinha comum de {title}"],
        relevance_score=0.9,
        source_pages=[1],
    )
    document = Document.create(
        title=title,
        source_filename=f"{title}.pdf",
        board=BoardStyle.CEBRASPE,
        exam_context="Marinha",
        source_excerpt=f"Trecho de {title}",
        topics=[topic],
        summaries=[],
        questions=[
            GeneratedQuestion(
                id=question_id,
                document_id="placeholder",
                topic_id=topic_id,
                style="certo_errado",
                stem=f"Julgue o item sobre {title}.",
                options=["Certo", "Errado"],
                correct_answer="Certo",
                explanation=f"Explicacao de {title}",
                difficulty_level=1,
            )
        ],
    )
    document.created_at = created_at
    document.questions[0].document_id = document.id
    return document


def create_client(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), repository


def test_submit_answer_records_correct_flow(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 10, 0, tzinfo=timezone.utc)
    document = build_document(
        title="Imunidades",
        topic_id="topic-1",
        question_id="q-1",
        created_at=now - timedelta(days=1),
    )
    repository.save_document(document)

    response = client.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-1",
            "question_id": "q-1",
            "microtopic_id": "micro-1",
            "user_answer": True,
            "correct_answer": True,
        },
    )

    progress = repository.load_progress()
    topic_state = progress.topic_learning_states["topic-1"]
    microtopic_state = progress.microtopic_performance["micro-1"]

    assert response.status_code == 200
    assert response.json() == {"correct": True, "message": "Answer recorded"}
    assert topic_state.total_questions == 1
    assert topic_state.correct_answers == 1
    assert topic_state.recent_errors == 0
    assert microtopic_state.total_questions == 1
    assert microtopic_state.correct_answers == 1
    assert microtopic_state.recent_errors == 0


def test_submit_answer_records_incorrect_flow_with_error_type(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 10, 30, tzinfo=timezone.utc)
    document = build_document(
        title="Lancamento",
        topic_id="topic-1",
        question_id="q-1",
        created_at=now - timedelta(days=2),
    )
    repository.save_document(document)

    response = client.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-1",
            "question_id": "q-1",
            "microtopic_id": "micro-1",
            "user_answer": False,
            "correct_answer": True,
            "error_type": "conceptual",
        },
    )

    progress = repository.load_progress()
    topic_state = progress.topic_learning_states["topic-1"]
    microtopic_state = progress.microtopic_performance["micro-1"]

    assert response.status_code == 200
    assert response.json()["correct"] is False
    assert topic_state.total_questions == 1
    assert topic_state.correct_answers == 0
    assert topic_state.recent_errors == 1
    assert topic_state.error_distribution["conceptual"] == 1
    assert microtopic_state.total_questions == 1
    assert microtopic_state.correct_answers == 0
    assert microtopic_state.recent_errors == 1
    assert microtopic_state.error_distribution["conceptual"] == 1


def test_submit_answer_rejects_incorrect_flow_without_error_type(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 11, 0, tzinfo=timezone.utc)
    document = build_document(
        title="Competencia",
        topic_id="topic-1",
        question_id="q-1",
        created_at=now - timedelta(days=1),
    )
    repository.save_document(document)

    response = client.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-1",
            "question_id": "q-1",
            "microtopic_id": "micro-1",
            "user_answer": False,
            "correct_answer": True,
        },
    )

    assert response.status_code == 400
    assert "error_type" in response.json()["detail"]
    assert repository.load_progress().topic_learning_states == {}


def test_submit_answer_persists_multiple_submissions_correctly(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 11, 30, tzinfo=timezone.utc)
    document = build_document(
        title="Obrigacao",
        topic_id="topic-1",
        question_id="q-1",
        created_at=now - timedelta(days=2),
    )
    repository.save_document(document)

    client.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-1",
            "question_id": "q-1",
            "microtopic_id": "micro-1",
            "user_answer": False,
            "correct_answer": True,
            "error_type": "interpretation",
        },
    )
    client.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-1",
            "question_id": "q-1",
            "microtopic_id": "micro-1",
            "user_answer": True,
            "correct_answer": True,
        },
    )
    client.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-1",
            "question_id": "q-1",
            "microtopic_id": "micro-1",
            "user_answer": False,
            "correct_answer": True,
            "error_type": "interpretation",
        },
    )

    progress = repository.load_progress()
    topic_state = progress.topic_learning_states["topic-1"]
    microtopic_state = progress.microtopic_performance["micro-1"]

    assert topic_state.total_questions == 3
    assert topic_state.correct_answers == 1
    assert topic_state.recent_errors == 1
    assert topic_state.error_distribution["interpretation"] == 2
    assert microtopic_state.total_questions == 3
    assert microtopic_state.correct_answers == 1
    assert microtopic_state.recent_errors == 1
    assert microtopic_state.error_distribution["interpretation"] == 2


def test_submit_answer_response_structure_is_stable(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 12, 0, tzinfo=timezone.utc)
    document = build_document(
        title="Fiscalizacao",
        topic_id="topic-1",
        question_id="q-1",
        created_at=now - timedelta(days=1),
    )
    repository.save_document(document)

    response = client.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-1",
            "question_id": "q-1",
            "microtopic_id": "micro-1",
            "user_answer": True,
            "correct_answer": True,
        },
    )

    assert set(response.json()) == {"correct", "message"}
    assert response.json()["message"] == "Answer recorded"


def test_full_feedback_loop_updates_priority_and_strategy(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 12, 30, tzinfo=timezone.utc)
    document = build_document(
        title="Imunidades",
        topic_id="topic-1",
        question_id="q-1",
        created_at=now - timedelta(days=2),
    )
    repository.save_document(document)
    engine = LearningDecisionEngine(repository, now_provider=lambda: now)

    initial_plan = engine.build_review_plan(title="Sessao 1", max_questions=2)
    initial_entry = initial_plan.entries[0]
    executed = execute_learning_plan(initial_plan.entries)

    assert executed
    assert initial_entry.dominant_error_type is None
    assert initial_entry.study_strategy == StudyStrategy.MIXED

    response = client.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-1",
            "question_id": "q-1",
            "microtopic_id": "micro-1",
            "user_answer": False,
            "correct_answer": True,
            "error_type": "conceptual",
        },
    )

    updated_plan = engine.build_review_plan(title="Sessao 2", max_questions=2)
    updated_entry = updated_plan.entries[0]

    assert response.status_code == 200
    assert updated_entry.score_breakdown["dynamic_priority"] > initial_entry.score_breakdown["dynamic_priority"]
    assert updated_entry.dominant_error_type == "conceptual"
    assert updated_entry.study_strategy == StudyStrategy.THEORY_REVIEW


def test_repository_loads_old_json_without_microtopic_performance(tmp_path):
    repository_path = tmp_path / "study_data.json"
    repository_path.write_text(
        """
        {
          "documents": [],
          "answers": [],
          "progress": {
            "total_errors": 0,
            "weak_topics": {},
            "error_buckets": {},
            "topic_learning_states": {},
            "item_states": {}
          }
        }
        """.strip(),
        encoding="utf-8",
    )

    repository = JsonStudyRepository(repository_path)
    progress = repository.load_progress()

    assert progress.microtopic_performance == {}


def test_repository_tracks_microtopics_independently_from_topics(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 5, 5, 13, 0, tzinfo=timezone.utc)

    repository.register_answer(
        topic_id="topic-1",
        question_id="q-1",
        microtopic_id="micro-a",
        is_correct=False,
        error_type="memory",
    )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-2",
            document_id="doc-1",
            topic_id="topic-1",
            microtopic_id="micro-b",
            selected_answer="C",
            is_correct=True,
            created_at=now,
        )
    )

    progress = repository.load_progress()

    assert progress.topic_learning_states["topic-1"].total_questions == 2
    assert progress.microtopic_performance["micro-a"].total_questions == 1
    assert progress.microtopic_performance["micro-a"].recent_errors == 1
    assert progress.microtopic_performance["micro-b"].total_questions == 1
    assert progress.microtopic_performance["micro-b"].correct_answers == 1


def test_microtopic_temporal_persistence_updates_feedback_timestamps_and_streaks(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 13, 30, tzinfo=timezone.utc)
    document = build_document(
        title="Balizamento",
        topic_id="topic-1",
        question_id="q-1",
        created_at=now - timedelta(days=1),
    )
    repository.save_document(document)

    client.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-1",
            "question_id": "q-1",
            "microtopic_id": "micro-time",
            "user_answer": False,
            "correct_answer": True,
            "error_type": "conceptual",
        },
    )
    client.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-1",
            "question_id": "q-1",
            "microtopic_id": "micro-time",
            "user_answer": True,
            "correct_answer": True,
        },
    )

    microtopic = repository.load_progress().microtopic_performance["micro-time"]

    assert microtopic.last_reviewed_at is not None
    assert microtopic.last_correct_at is not None
    assert microtopic.last_incorrect_at is not None
    assert microtopic.consecutive_correct == 1
    assert microtopic.consecutive_incorrect == 0


def test_repository_loads_old_microtopic_json_without_temporal_fields(tmp_path):
    repository_path = tmp_path / "study_data.json"
    repository_path.write_text(
        """
        {
          "documents": [],
          "answers": [],
          "progress": {
            "total_errors": 0,
            "weak_topics": {},
            "error_buckets": {},
            "topic_learning_states": {},
            "item_states": {},
            "microtopic_performance": {
              "micro-old": {
                "topic_id": "topic-1",
                "total_questions": 2,
                "correct_answers": 1,
                "recent_errors": 1,
                "error_distribution": {
                  "conceptual": 1
                }
              }
            }
          }
        }
        """.strip(),
        encoding="utf-8",
    )

    repository = JsonStudyRepository(repository_path)
    microtopic = repository.load_progress().microtopic_performance["micro-old"]

    assert microtopic.last_reviewed_at is None
    assert microtopic.consecutive_correct == 0
    assert microtopic.consecutive_incorrect == 0
