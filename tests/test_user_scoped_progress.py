import json
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.domain.models import AnswerSubmission, BoardStyle, Document, GeneratedQuestion, Topic
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


def build_document(*, title: str, topic_id: str, question_id: str, created_at: datetime) -> Document:
    topic = Topic(
        id=topic_id,
        title=title,
        content=f"{title} exige leitura cuidadosa e precisao normativa.",
        key_points=[f"Ponto central de {title}"],
        trap_points=[f"Pegadinha comum de {title}"],
        relevance_score=0.8,
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


def create_app_and_repo(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return app, repository


def register_and_login(client: TestClient, username: str) -> dict[str, object]:
    register = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "senha-segura-123",
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    )
    assert register.status_code == 201
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert login.status_code == 200
    return register.json()


def test_repository_isolates_progress_between_users(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    now = datetime(2026, 5, 17, 10, 0, tzinfo=timezone.utc)

    repository.record_answer(
        AnswerSubmission(
            question_id="q-a",
            document_id="doc-a",
            topic_id="topic-a",
            microtopic_id="micro-a",
            selected_answer="false",
            is_correct=False,
            error_type="conceptual",
            created_at=now,
        ),
        user_id="user-a",
    )
    repository.record_answer(
        AnswerSubmission(
            question_id="q-b",
            document_id="doc-b",
            topic_id="topic-b",
            microtopic_id="micro-b",
            selected_answer="true",
            is_correct=True,
            created_at=now,
        ),
        user_id="user-b",
    )

    progress_a = repository.load_progress(user_id="user-a")
    progress_b = repository.load_progress(user_id="user-b")
    legacy_progress = repository.load_progress()

    assert progress_a.total_errors == 1
    assert "topic-a" in progress_a.topic_learning_states
    assert progress_b.total_errors == 0
    assert "topic-b" in progress_b.topic_learning_states
    assert legacy_progress.topic_learning_states == {}


def test_legacy_single_user_progress_loads_safely(tmp_path):
    path = tmp_path / "study_data.json"
    path.write_text(
        json.dumps(
            {
                "documents": [],
                "answers": [],
                "progress": {
                    "total_errors": 1,
                    "weak_topics": {"topic-legacy": 1},
                    "error_buckets": {"interpretation": 1},
                    "topic_learning_states": {},
                    "item_states": {},
                    "microtopic_performance": {},
                    "pedagogical_memory": {},
                },
            },
            ensure_ascii=True,
        ),
        encoding="utf-8",
    )

    repository = JsonStudyRepository(path)
    progress = repository.load_progress()

    assert progress.total_errors == 1
    assert progress.weak_topics["topic-legacy"] == 1


def test_answer_submission_updates_the_authenticated_user_progress(tmp_path):
    app, repository = create_app_and_repo(tmp_path)
    client_a = TestClient(app)
    client_b = TestClient(app)
    user_a = register_and_login(client_a, "alice")
    user_b = register_and_login(client_b, "bruno")
    now = datetime(2026, 5, 17, 11, 0, tzinfo=timezone.utc)

    doc_a = build_document(
        title="Alice Material",
        topic_id="topic-a",
        question_id="q-a",
        created_at=now - timedelta(days=1),
    )
    doc_b = build_document(
        title="Bruno Material",
        topic_id="topic-b",
        question_id="q-b",
        created_at=now - timedelta(days=1),
    )
    repository.save_document(doc_a, user_id=user_a["user_id"])
    repository.save_document(doc_b, user_id=user_b["user_id"])

    response_a = client_a.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-a",
            "question_id": "q-a",
            "microtopic_id": "micro-a",
            "user_answer": False,
            "correct_answer": True,
            "error_type": "conceptual",
        },
    )
    response_b = client_b.post(
        "/api/answers/submit",
        json={
            "topic_id": "topic-b",
            "question_id": "q-b",
            "microtopic_id": "micro-b",
            "user_answer": True,
            "correct_answer": True,
        },
    )

    progress_a = repository.load_progress(user_id=user_a["user_id"])
    progress_b = repository.load_progress(user_id=user_b["user_id"])

    assert response_a.status_code == 200
    assert response_b.status_code == 200
    assert progress_a.total_errors == 1
    assert progress_b.total_errors == 0
    assert "topic-a" in progress_a.topic_learning_states
    assert "topic-b" in progress_b.topic_learning_states


def test_session_start_uses_the_authenticated_user_documents(tmp_path):
    app, repository = create_app_and_repo(tmp_path)
    client_a = TestClient(app)
    client_b = TestClient(app)
    user_a = register_and_login(client_a, "carla")
    user_b = register_and_login(client_b, "diego")
    now = datetime(2026, 5, 17, 11, 30, tzinfo=timezone.utc)

    repository.save_document(
        build_document(
            title="Direito Maritimo",
            topic_id="topic-a",
            question_id="q-a",
            created_at=now - timedelta(days=2),
        ),
        user_id=user_a["user_id"],
    )
    repository.save_document(
        build_document(
            title="Navegacao",
            topic_id="topic-b",
            question_id="q-b",
            created_at=now - timedelta(days=2),
        ),
        user_id=user_b["user_id"],
    )

    started_a = client_a.post("/api/session/start", json={"title": "Sessao A", "max_questions": 2})
    started_b = client_b.post("/api/session/start", json={"title": "Sessao B", "max_questions": 2})

    assert started_a.status_code == 200
    assert started_b.status_code == 200
    assert started_a.json()["first_block"]["topic_id"] == "topic-a"
    assert started_b.json()["first_block"]["topic_id"] == "topic-b"
