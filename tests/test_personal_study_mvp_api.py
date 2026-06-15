from __future__ import annotations

import json
from urllib.parse import quote

from fastapi.testclient import TestClient

from app.api import routes
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


def create_client(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), repository


def register_and_login(client: TestClient, username: str = "mvp-owner") -> dict[str, object]:
    response = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "senha-segura-123",
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    )
    assert response.status_code == 201
    login = client.post(
        "/api/auth/login",
        json={
            "username": username,
            "password": "senha-segura-123",
            "why_this_after_previous": "QA",
        },
    )
    assert login.status_code == 200
    return response.json()


def upload_material(client: TestClient, filename: str, content: bytes) -> str:
    response = client.post(
        "/api/materials/upload",
        files={"file": (filename, content, "text/markdown")},
        data={"material_type": "study_material"},
    )
    assert response.status_code == 201
    document_id = response.json()["metadata"]["document_id"]
    prepared = client.post(f"/api/materials/{document_id}/study/prepare")
    assert prepared.status_code == 200
    return document_id


def first_block(client: TestClient) -> dict[str, object]:
    response = client.get("/api/study/blocks")
    assert response.status_code == 200
    payload = response.json()
    assert payload["items"]
    return payload["items"][0]


def questions_path(block_id: str) -> str:
    return f"/api/study/blocks/{quote(block_id, safe='')}/questions"


def review_path(block_id: str, question_id: str) -> str:
    return (
        f"/api/study/blocks/{quote(block_id, safe='')}"
        f"/questions/{quote(question_id, safe='')}/answer/review"
    )


def post_review(client: TestClient, block_id: str, question_id: str, answer: str):
    return client.post(
        review_path(block_id, question_id),
        json={
            "answer": answer,
            "answer_format": "choice",
            "idempotency_key": f"qa:{question_id}:{answer}",
        },
    )


def public_questions(client: TestClient, block_id: str) -> list[dict[str, object]]:
    response = client.get(questions_path(block_id))
    assert response.status_code == 200
    return response.json()["items"]


def internal_question(repository: JsonStudyRepository, user_id: str, block_id: str, question_id: str) -> dict[str, object]:
    _, _, questions = routes._internal_fixation_question_candidates(repository, user_id, block_id)
    question = next(item for item in questions if item["question_id"] == question_id)
    assert question["_validation_state"] == "validated"
    assert question["_correct_answer"]
    assert question["_evidence"]
    return question


def assert_no_private_question_fields(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    for term in (
        "_correct_answer",
        "_evidence",
        "_validation_state",
        "answer_key",
        "gabarito",
        "correct_answer",
        "storage_path",
        "password_hash",
        "token",
    ):
        assert term not in dumped


def test_grounded_summary_and_validated_questions_are_source_backed(tmp_path):
    client, repository = create_client(tmp_path)
    user = register_and_login(client)
    document_id = upload_material(
        client,
        "atos.md",
        (
            b"# Atos administrativos\n\n"
            b"Atos administrativos produzem efeitos juridicos imediatos e devem observar finalidade publica. "
            b"A competencia indica quem pode praticar o ato administrativo. "
            b"O motivo apresenta os fatos e fundamentos que justificam o ato."
        ),
    )

    summary = client.get(f"/api/materials/{document_id}/study/summary").json()
    assert summary["items"][0]["summary"] != "Resumo em preparação para esta seção."
    assert "Atos administrativos produzem efeitos juridicos" in summary["items"][0]["summary"]
    assert summary["items"][0]["key_points"]

    block = first_block(client)
    questions = public_questions(client, str(block["block_id"]))
    assert questions
    assert all(item["type"] == "multiple_choice" for item in questions)
    assert all(len(item["alternatives"]) == 5 for item in questions)
    assert_no_private_question_fields({"items": questions})

    internal = internal_question(repository, user["user_id"], str(block["block_id"]), str(questions[0]["question_id"]))
    assert internal["_correct_answer"] in {alternative["id"] for alternative in questions[0]["alternatives"]}


def test_persisted_attempt_correctness_and_idempotency(tmp_path):
    client, repository = create_client(tmp_path)
    user = register_and_login(client)
    upload_material(
        client,
        "competencia.md",
        (
            b"# Competencia\n\n"
            b"A competencia indica quem pode praticar o ato administrativo. "
            b"A finalidade publica orienta o uso do ato administrativo."
        ),
    )
    block = first_block(client)
    question = public_questions(client, str(block["block_id"]))[0]
    internal = internal_question(repository, user["user_id"], str(block["block_id"]), str(question["question_id"]))

    first = post_review(client, str(block["block_id"]), str(question["question_id"]), str(internal["_correct_answer"]))
    second = post_review(client, str(block["block_id"]), str(question["question_id"]), str(internal["_correct_answer"]))

    assert first.status_code == 200
    assert first.json()["result"] == "correct"
    assert second.json() == first.json()
    attempts = repository.list_study_question_attempts(user_id=user["user_id"])
    assert len(attempts) == 1
    assert attempts[0]["selected_answer"] == internal["_correct_answer"]
    states = repository.get_study_question_attempt_states(user_id=user["user_id"])
    assert states[str(question["question_id"])]["current_bucket"] == "reviewing"


def test_incorrect_attempt_becomes_weak_and_prioritized(tmp_path):
    client, repository = create_client(tmp_path)
    user = register_and_login(client)
    upload_material(
        client,
        "motivo.md",
        (
            b"# Motivo\n\n"
            b"O motivo apresenta os fatos e fundamentos que justificam o ato. "
            b"A forma organiza a exteriorizacao do ato administrativo. "
            b"O objeto representa o efeito juridico produzido pelo ato."
        ),
    )
    block = first_block(client)
    question = public_questions(client, str(block["block_id"]))[0]
    internal = internal_question(repository, user["user_id"], str(block["block_id"]), str(question["question_id"]))
    wrong_answer = next(
        alternative["id"]
        for alternative in question["alternatives"]
        if alternative["id"] != internal["_correct_answer"]
    )

    response = post_review(client, str(block["block_id"]), str(question["question_id"]), wrong_answer)
    assert response.status_code == 200
    assert response.json()["result"] == "incorrect"
    assert repository.list_study_weak_topic_signals(user_id=user["user_id"])

    next_questions = public_questions(client, str(block["block_id"]))
    assert next_questions[0]["question_id"] == question["question_id"]


def test_correct_attempt_is_temporarily_suppressed_when_other_questions_exist(tmp_path):
    client, repository = create_client(tmp_path)
    user = register_and_login(client)
    upload_material(
        client,
        "forma.md",
        (
            b"# Forma\n\n"
            b"A forma organiza a exteriorizacao do ato administrativo. "
            b"O objeto representa o efeito juridico produzido pelo ato. "
            b"A competencia indica quem pode praticar o ato administrativo."
        ),
    )
    block = first_block(client)
    questions = public_questions(client, str(block["block_id"]))
    assert len(questions) >= 2
    first_question = questions[0]
    internal = internal_question(repository, user["user_id"], str(block["block_id"]), str(first_question["question_id"]))

    response = post_review(client, str(block["block_id"]), str(first_question["question_id"]), str(internal["_correct_answer"]))
    assert response.status_code == 200
    assert response.json()["result"] == "correct"

    next_questions = public_questions(client, str(block["block_id"]))
    assert next_questions[0]["question_id"] != first_question["question_id"]


def test_cumulative_review_reports_real_weak_topic_signals(tmp_path):
    client, repository = create_client(tmp_path)
    user = register_and_login(client)
    for index in range(3):
        upload_material(
            client,
            f"material-{index}.md",
            (
                f"# Tema {index}\n\n"
                f"O tema {index} possui uma regra principal para revisar. "
                f"A regra {index} deve ser comparada com as excecoes do material."
            ).encode("utf-8"),
        )
    blocks = client.get("/api/study/blocks").json()["items"]
    first = blocks[0]
    question = public_questions(client, str(first["block_id"]))[0]
    internal = internal_question(repository, user["user_id"], str(first["block_id"]), str(question["question_id"]))
    wrong_answer = next(
        alternative["id"]
        for alternative in question["alternatives"]
        if alternative["id"] != internal["_correct_answer"]
    )
    assert post_review(client, str(first["block_id"]), str(question["question_id"]), wrong_answer).status_code == 200

    for block in blocks:
        response = client.post(
            "/api/study/progress/events",
            json={
                "event_type": "block_marked_studied",
                "target_type": "block",
                "target_id": block["block_id"],
                "idempotency_key": f"qa:block:{block['block_id']}",
            },
        )
        assert response.status_code == 200

    progress = client.get("/api/study/progress/summary").json()
    review = client.get("/api/study/review/next").json()
    assert progress["studied_materials_count"] >= 3
    assert progress["weak_topics_count"] >= 1
    assert review["basis"] == "studied_materials"
    assert review["reinforcement"]["weak_topics_count"] >= 1
