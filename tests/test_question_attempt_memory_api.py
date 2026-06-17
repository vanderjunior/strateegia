from __future__ import annotations

import json
from io import BytesIO
from urllib.parse import quote

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


SOURCE = (
    b"# Poder de policia\n\n"
    b"O poder de policia consiste em atividade administrativa que limita direitos "
    b"para proteger a finalidade publica e produzir efeitos imediatos."
)


def create_client(tmp_path):
    data_path = tmp_path / "study_data.json"
    repository = JsonStudyRepository(data_path)
    return TestClient(create_app(repository=repository)), repository, data_path


def register_and_login(client: TestClient, username: str) -> dict[str, object]:
    registered = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "senha-segura-123",
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    )
    assert registered.status_code == 201
    logged_in = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert logged_in.status_code == 200
    return registered.json()


def prepare_question(client: TestClient, repository: JsonStudyRepository, user_id: str):
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": ("aula.md", BytesIO(SOURCE), "text/markdown")},
        data={"material_type": "study_material"},
    )
    assert uploaded.status_code == 201
    document_id = uploaded.json()["metadata"]["document_id"]
    prepared = client.post(f"/api/materials/{document_id}/study/prepare")
    assert prepared.status_code == 200
    blocks = client.get("/api/study/blocks")
    assert blocks.status_code == 200
    block_id = str(blocks.json()["items"][0]["block_id"])
    _, _, internal_questions = routes._internal_fixation_question_candidates(
        repository,
        user_id,
        block_id,
    )
    question = next(item for item in internal_questions if item.get("_validation_state") == "validated")
    return block_id, question


def review_path(block_id: str, question_id: str) -> str:
    return (
        f"/api/study/blocks/{quote(block_id, safe='')}"
        f"/questions/{quote(question_id, safe='')}/answer/review"
    )


def history_path(block_id: str, question_id: str) -> str:
    return (
        f"/api/study/blocks/{quote(block_id, safe='')}"
        f"/questions/{quote(question_id, safe='')}/attempts"
    )


def submit(
    client: TestClient,
    block_id: str,
    question_id: str,
    *,
    answer: str,
    key: str,
    context: str = "study_block",
):
    return client.post(
        review_path(block_id, question_id),
        json={
            "answer": answer,
            "answer_format": "choice",
            "response_context": context,
            "idempotency_key": key,
        },
    )


def test_attempt_is_persisted_with_server_derived_correctness(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_id, question = prepare_question(client, repository, str(user["user_id"]))
    correct_answer = str(question["_correct_answer"])

    response = submit(
        client,
        block_id,
        str(question["question_id"]),
        answer=correct_answer,
        key="attempt-correct-1",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["result"] == "correct"
    assert payload["attempt"] == {
        "attempt_id": payload["attempt"]["attempt_id"],
        "question_id": str(question["question_id"]),
        "selected_answer": correct_answer,
        "correctness_state": "correct",
        "attempted_at": payload["attempt"]["attempted_at"],
        "attempt_number": 1,
        "response_context": "study_block",
        "persisted": True,
    }
    stored = repository.list_study_question_attempts(user_id=str(user["user_id"]))
    assert len(stored) == 1
    assert stored[0]["user_id"] == user["user_id"]
    assert stored[0]["question_fingerprint"] == question["_fingerprint"]
    assert stored[0]["question_generator_version"] == question["_generator_version"]
    assert stored[0]["correctness_state"] == "correct"
    assert "correct_answer" not in payload
    assert "correct_answer" not in payload["attempt"]
    assert repository.get_study_question_attempt_states(user_id=str(user["user_id"])) == {}
    assert repository.list_study_weak_topic_signals(user_id=str(user["user_id"])) == {}


def test_exact_retry_is_stable_and_conflicting_reuse_is_rejected(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_id, question = prepare_question(client, repository, str(user["user_id"]))
    alternatives = [str(item["id"]) for item in question["alternatives"]]
    first_answer, conflicting_answer = alternatives[:2]

    first = submit(
        client,
        block_id,
        str(question["question_id"]),
        answer=first_answer,
        key="attempt-retry-1",
    )
    retry = submit(
        client,
        block_id,
        str(question["question_id"]),
        answer=first_answer,
        key="attempt-retry-1",
    )
    conflict = submit(
        client,
        block_id,
        str(question["question_id"]),
        answer=conflicting_answer,
        key="attempt-retry-1",
    )
    context_conflict = submit(
        client,
        block_id,
        str(question["question_id"]),
        answer=first_answer,
        key="attempt-retry-1",
        context="reinforcement",
    )

    assert first.status_code == 200
    assert retry.status_code == 200
    assert retry.json() == first.json()
    assert conflict.status_code == 409
    assert context_conflict.status_code == 409
    assert "feedback" not in conflict.json()
    attempts = repository.list_study_question_attempts(user_id=str(user["user_id"]))
    assert len(attempts) == 1
    assert attempts[0]["selected_answer"] == first_answer


def test_new_key_allows_a_legitimate_later_attempt(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_id, question = prepare_question(client, repository, str(user["user_id"]))
    answer = str(question["alternatives"][0]["id"])

    first = submit(
        client,
        block_id,
        str(question["question_id"]),
        answer=answer,
        key="attempt-later-1",
    )
    second = submit(
        client,
        block_id,
        str(question["question_id"]),
        answer=answer,
        key="attempt-later-2",
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["attempt"]["attempt_number"] == 1
    assert second.json()["attempt"]["attempt_number"] == 2
    assert first.json()["attempt"]["attempt_id"] != second.json()["attempt"]["attempt_id"]


def test_invalid_answer_or_client_correctness_fields_do_not_persist(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_id, question = prepare_question(client, repository, str(user["user_id"]))
    path = review_path(block_id, str(question["question_id"]))

    invalid_answer = client.post(
        path,
        json={
            "answer": "Z",
            "answer_format": "choice",
            "response_context": "study_block",
            "idempotency_key": "attempt-invalid-answer",
        },
    )
    injected = client.post(
        path,
        json={
            "answer": str(question["alternatives"][0]["id"]),
            "answer_format": "choice",
            "response_context": "study_block",
            "idempotency_key": "attempt-injected",
            "correctness": "correct",
            "correct_answer": "A",
            "score": 10,
            "mastery": "mastered",
            "next_eligible_at": "2099-01-01T00:00:00Z",
            "rationale": "client supplied",
            "validation_state": "validated",
        },
    )

    assert invalid_answer.status_code == 422
    assert injected.status_code == 422
    assert repository.list_study_question_attempts(user_id=str(user["user_id"])) == []


def test_attempt_history_is_owner_scoped_bounded_and_survives_reload(tmp_path):
    owner, repository, data_path = create_client(tmp_path)
    other = TestClient(create_app(repository=repository))
    user = register_and_login(owner, "owner")
    register_and_login(other, "other")
    block_id, question = prepare_question(owner, repository, str(user["user_id"]))
    question_id = str(question["question_id"])
    answer = str(question["alternatives"][0]["id"])

    submitted = submit(
        owner,
        block_id,
        question_id,
        answer=answer,
        key="attempt-persisted-1",
    )
    assert submitted.status_code == 200

    history = owner.get(history_path(block_id, question_id))
    foreign_history = other.get(history_path(block_id, question_id))
    assert history.status_code == 200
    assert history.json()["items_count"] == 1
    assert history.json()["items"][0]["attempt_id"] == submitted.json()["attempt"]["attempt_id"]
    assert "idempotency_key" not in history.json()["items"][0]
    assert foreign_history.status_code == 404

    reloaded_repository = JsonStudyRepository(data_path)
    reloaded = TestClient(create_app(repository=reloaded_repository))
    logged_in = reloaded.post(
        "/api/auth/login",
        json={"username": "owner", "password": "senha-segura-123"},
    )
    assert logged_in.status_code == 200
    retry = submit(
        reloaded,
        block_id,
        question_id,
        answer=answer,
        key="attempt-persisted-1",
    )
    reloaded_history = reloaded.get(history_path(block_id, question_id))
    assert retry.status_code == 200
    assert retry.json()["attempt"]["attempt_id"] == submitted.json()["attempt"]["attempt_id"]
    assert reloaded_history.status_code == 200
    assert reloaded_history.json()["items_count"] == 1


def test_attempt_history_returns_only_the_latest_twenty_in_stable_order(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_id, question = prepare_question(client, repository, str(user["user_id"]))
    question_id = str(question["question_id"])
    answer = str(question["alternatives"][0]["id"])

    for number in range(1, 23):
        response = submit(
            client,
            block_id,
            question_id,
            answer=answer,
            key=f"attempt-bounded-{number}",
        )
        assert response.status_code == 200

    history = client.get(history_path(block_id, question_id))

    assert history.status_code == 200
    payload = history.json()
    assert payload["items_count"] == 20
    assert [item["attempt_number"] for item in payload["items"]] == list(range(3, 23))


def test_question_and_study_reads_do_not_create_attempts(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_id, question = prepare_question(client, repository, str(user["user_id"]))

    assert client.get(f"/api/study/blocks/{quote(block_id, safe='')}").status_code == 200
    assert client.get(f"/api/study/blocks/{quote(block_id, safe='')}/questions").status_code == 200
    assert client.get("/api/study/blocks").status_code == 200
    assert client.get("/api/study/progress/summary").status_code == 200
    assert client.get("/api/study/review/next").status_code == 200
    assert client.get(history_path(block_id, str(question["question_id"]))).status_code == 200
    assert repository.list_study_question_attempts(user_id=str(user["user_id"])) == []


def test_non_validated_resolvable_question_is_persisted_as_ungraded(tmp_path, monkeypatch):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_id, validated = prepare_question(client, repository, str(user["user_id"]))
    ungraded = {
        **validated,
        "question_id": f"{validated['question_id']}:ungraded",
        "_validation_state": "needs_review",
        "_correct_answer": None,
    }
    original = routes._internal_fixation_question_candidates

    def candidates(repo, owner_id, requested_block_id):
        detail, status, _items = original(repo, owner_id, requested_block_id)
        return detail, status, [ungraded]

    monkeypatch.setattr(routes, "_internal_fixation_question_candidates", candidates)
    answer = str(ungraded["alternatives"][0]["id"])

    response = submit(
        client,
        block_id,
        str(ungraded["question_id"]),
        answer=answer,
        key="attempt-ungraded-1",
    )

    assert response.status_code == 200
    assert response.json()["result"] == "ungraded"
    assert response.json()["attempt"]["correctness_state"] == "ungraded"
    attempts = repository.list_study_question_attempts(user_id=str(user["user_id"]))
    assert len(attempts) == 1
    assert attempts[0]["correctness_state"] == "ungraded"


def test_malformed_persisted_attempt_is_hidden_and_idempotency_fails_closed(tmp_path):
    client, repository, data_path = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_id, question = prepare_question(client, repository, str(user["user_id"]))
    question_id = str(question["question_id"])
    answer = str(question["alternatives"][0]["id"])
    submitted = submit(
        client,
        block_id,
        question_id,
        answer=answer,
        key="attempt-malformed-1",
    )
    assert submitted.status_code == 200

    payload = json.loads(data_path.read_text(encoding="utf-8"))
    user_attempts = payload["user_data"][str(user["user_id"])]["study_question_attempts"]
    attempt_id = submitted.json()["attempt"]["attempt_id"]
    user_attempts["attempts"][attempt_id].pop("selected_answer")
    data_path.write_text(json.dumps(payload), encoding="utf-8")

    reloaded = JsonStudyRepository(data_path)
    reloaded_client = TestClient(create_app(repository=reloaded))
    logged_in = reloaded_client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "senha-segura-123"},
    )
    assert logged_in.status_code == 200
    history = reloaded_client.get(history_path(block_id, question_id))
    retry = submit(
        reloaded_client,
        block_id,
        question_id,
        answer=answer,
        key="attempt-malformed-1",
    )

    assert history.status_code == 200
    assert history.json()["items"] == []
    assert retry.status_code == 409
