from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.domain.models import BoardStyle, Document, GeneratedQuestion, Topic
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


def build_document(*, title: str, topic_id: str, question_id: str, created_at: datetime) -> Document:
    topic = Topic(
        id=topic_id,
        title=title,
        content=(
            f"{title} exige precisao normativa e comparacoes tecnicas. "
            f"{title} aparece em prova com excecoes, pegadinhas e termos absolutos."
        ),
        key_points=[f"Ponto central de {title}"],
        trap_points=[f"Pegadinha comum de {title}"],
        relevance_score=0.85,
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
                stem=f"Julgue item sobre {title}.",
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


def start_basic_session(client: TestClient):
    response = client.post("/api/session/start", json={"title": "Sessao", "max_questions": 2})
    assert response.status_code == 200
    return response.json()


def answer_current_question(client: TestClient, session_id: str, question: dict, *, correct: bool = True):
    user_answer = question["correct_answer"] if correct else (not question["correct_answer"])
    payload = {
        "question_id": question["question_id"],
        "user_answer": user_answer,
        "correct_answer": question["correct_answer"],
    }
    if not correct:
        payload["error_type"] = "conceptual"
    return client.post(f"/api/session/{session_id}/answer", json=payload)


def test_session_creation_returns_session_id(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 14, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Imunidades",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )

    payload = start_basic_session(client)

    assert payload["session_id"]
    assert payload["first_block"]["type"] == "summary"


def test_session_current_returns_first_block(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 14, 30, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Lancamento",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )

    started = start_basic_session(client)
    current = client.get(f"/api/session/{started['session_id']}/current")

    assert current.status_code == 200
    assert current.json() == started["first_block"]


def test_session_flows_sequentially_from_summary_to_question(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 15, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Competencia",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=2),
        )
    )

    started = start_basic_session(client)
    advanced = client.post(f"/api/session/{started['session_id']}/answer")

    assert advanced.status_code == 200
    assert advanced.json()["completed"] is False
    assert advanced.json()["next_block"]["type"] == "question"


def test_session_answer_submission_updates_progress_and_advances(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 15, 30, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Obrigacao",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=2),
        )
    )

    started = start_basic_session(client)
    question = client.post(f"/api/session/{started['session_id']}/answer").json()["next_block"]
    answered = client.post(
        f"/api/session/{started['session_id']}/answer",
        json={
            "question_id": question["question_id"],
            "user_answer": False,
            "correct_answer": True,
            "error_type": "conceptual",
        },
    )

    progress = repository.load_progress()

    assert answered.status_code == 200
    assert answered.json()["correct"] is False
    assert progress.topic_learning_states["topic-1"].error_distribution["conceptual"] == 1


def test_session_blocks_expose_pedagogical_metadata(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 15, 45, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Canal Restrito",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=2),
        )
    )

    started = start_basic_session(client)
    summary_block = started["first_block"]
    question_block = client.post(f"/api/session/{started['session_id']}/answer").json()["next_block"]

    assert "pedagogical_mode" in summary_block
    assert "intervention_reason" in summary_block
    assert "equilibrium_reason" in summary_block
    assert "cognitive_load" in summary_block
    assert "explanation_depth" in summary_block
    assert "retrieval_intensity" in summary_block
    assert "why_this_now" in summary_block
    assert "stabilization_stage" in summary_block
    assert "pedagogical_mode" in question_block
    assert "intervention_reason" in question_block
    assert "equilibrium_reason" in question_block
    assert "cognitive_load_score" in question_block
    assert "intervention_effectiveness" in question_block
    assert "pedagogical_confidence" in question_block
    assert "longitudinal_retention" in question_block


def test_session_completion_returns_completed_true(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 16, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Fiscalizacao",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )

    started = start_basic_session(client)
    next_block = client.post(f"/api/session/{started['session_id']}/answer").json()["next_block"]
    while next_block["type"] == "question":
        response = answer_current_question(client, started["session_id"], next_block, correct=True)
        payload = response.json()
        if payload["completed"]:
            completed = response
            break
        next_block = payload["next_block"]
    else:
        completed = response

    assert completed.status_code == 200
    assert completed.json()["completed"] is True


def test_session_multiple_topics_preserves_summary_then_question_then_next_topic(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 16, 30, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Tema 1",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=3),
        )
    )
    repository.save_document(
        build_document(
            title="Tema 2",
            topic_id="topic-2",
            question_id="q-2",
            created_at=now - timedelta(days=1),
        )
    )

    started = client.post("/api/session/start", json={"title": "Sessao", "max_questions": 4}).json()
    first_summary = started["first_block"]
    first_question = client.post(f"/api/session/{started['session_id']}/answer").json()["next_block"]
    next_block = first_question
    while next_block["type"] == "question":
        payload = answer_current_question(
            client,
            started["session_id"],
            next_block,
            correct=True,
        ).json()
        next_block = payload.get("next_block")
        if next_block is None:
            break
    second_step = next_block

    assert first_summary["type"] == "summary"
    assert first_question["type"] == "question"
    assert second_step["type"] == "summary"
    assert second_step["topic_id"] != first_summary["topic_id"]


def test_session_invalid_session_id_returns_404(tmp_path):
    client, _ = create_client(tmp_path)

    current = client.get("/api/session/does-not-exist/current")
    answer = client.post("/api/session/does-not-exist/answer")

    assert current.status_code == 404
    assert answer.status_code == 404


def test_session_hybrid_flow_interleaves_question_microtopics_across_topics_deterministically(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 17, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="RIPAM",
            topic_id="topic-ripam",
            question_id="q-ripam",
            created_at=now - timedelta(days=2),
        )
    )
    repository.save_document(
        build_document(
            title="NORMAM",
            topic_id="topic-normam",
            question_id="q-normam",
            created_at=now - timedelta(days=1),
        )
    )

    started = client.post("/api/session/start", json={"title": "Sessao", "max_questions": 4}).json()
    sequence = [started["first_block"]]
    next_payload = client.post(f"/api/session/{started['session_id']}/answer").json()
    sequence.append(next_payload["next_block"])

    while True:
        current = sequence[-1]
        if current["type"] != "question":
            next_payload = client.post(f"/api/session/{started['session_id']}/answer").json()
        else:
            next_payload = answer_current_question(client, started["session_id"], current, correct=True).json()
        if next_payload.get("completed"):
            break
        sequence.append(next_payload["next_block"])

    question_blocks = [block for block in sequence if block["type"] == "question"]

    assert sequence[0]["type"] == "summary"
    assert question_blocks[0]["topic_id"] != question_blocks[1]["topic_id"]
    assert all(block.get("microtopic_id") for block in question_blocks)


def test_session_keeps_summary_before_first_question_of_each_topic(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 5, 17, 30, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Sinais Sonoros",
            topic_id="topic-sinais",
            question_id="q-sinais",
            created_at=now - timedelta(days=2),
        )
    )
    repository.save_document(
        build_document(
            title="Luzes",
            topic_id="topic-luzes",
            question_id="q-luzes",
            created_at=now - timedelta(days=1),
        )
    )

    started = client.post("/api/session/start", json={"title": "Sessao", "max_questions": 4}).json()
    blocks = [started["first_block"]]
    while True:
        current = blocks[-1]
        if current["type"] == "summary":
            payload = client.post(f"/api/session/{started['session_id']}/answer").json()
        else:
            payload = answer_current_question(client, started["session_id"], current, correct=True).json()
        if payload.get("completed"):
            break
        blocks.append(payload["next_block"])

    first_summary_index = {}
    first_question_index = {}
    for index, block in enumerate(blocks):
        if block["type"] == "summary":
            first_summary_index.setdefault(block["topic_id"], index)
        if block["type"] == "question":
            first_question_index.setdefault(block["topic_id"], index)

    for topic_id, question_index in first_question_index.items():
        assert first_summary_index[topic_id] < question_index
