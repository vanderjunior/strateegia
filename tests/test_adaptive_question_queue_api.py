from __future__ import annotations

import json
from io import BytesIO
from urllib.parse import quote

from fastapi.testclient import TestClient

import app.api.routes as routes
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


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


def source_for(index: int) -> bytes:
    return (
        f"# Tema {index}\n\n"
        f"O conceito {index} consiste em atividade administrativa que limita direitos "
        "para proteger a finalidade publica e produzir efeitos imediatos."
    ).encode("utf-8")


def upload_and_prepare(client: TestClient, index: int) -> str:
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (f"tema-{index}.md", BytesIO(source_for(index)), "text/markdown")},
        data={"material_type": "study_material"},
    )
    assert uploaded.status_code == 201
    document_id = str(uploaded.json()["metadata"]["document_id"])
    prepared = client.post(f"/api/materials/{document_id}/study/prepare")
    assert prepared.status_code == 200
    return document_id


def block_id_for_material(client: TestClient, material_id: str) -> str:
    blocks = client.get("/api/study/blocks")
    assert blocks.status_code == 200
    for block in blocks.json()["items"]:
        if block["material_id"] == material_id:
            return str(block["block_id"])
    raise AssertionError(f"missing block for {material_id}")


def prepare_blocks(client: TestClient, count: int) -> list[str]:
    material_ids = [upload_and_prepare(client, index) for index in range(1, count + 1)]
    return [block_id_for_material(client, material_id) for material_id in material_ids]


def internal_question(repository: JsonStudyRepository, user_id: str, block_id: str) -> dict[str, object]:
    _detail, _status, questions = routes._internal_fixation_question_candidates(
        repository,
        user_id,
        block_id,
    )
    return next(question for question in questions if question.get("_validation_state") == "validated")


def queue_path(block_id: str, *, limit: int = 5) -> str:
    return f"/api/study/blocks/{quote(block_id, safe='')}/questions/next?limit={limit}"


def review_path(block_id: str, question_id: str) -> str:
    return (
        f"/api/study/blocks/{quote(block_id, safe='')}"
        f"/questions/{quote(question_id, safe='')}/answer/review"
    )


def mark_studied(client: TestClient, block_id: str) -> None:
    response = client.post(
        "/api/study/progress/events",
        json={
            "event_type": "block_marked_studied",
            "target_type": "block",
            "target_id": block_id,
            "idempotency_key": f"studied:{block_id}",
        },
    )
    assert response.status_code == 200


def answer_for(question: dict[str, object], *, correct: bool = True) -> str:
    correct_answer = str(question["_correct_answer"])
    if correct:
        return correct_answer
    return next(
        str(alternative["id"])
        for alternative in question["alternatives"]
        if alternative["id"] != correct_answer
    )


def submit_answer(
    client: TestClient,
    block_id: str,
    question: dict[str, object],
    *,
    key: str,
    correct: bool = True,
) -> dict[str, object]:
    response = client.post(
        review_path(block_id, str(question["question_id"])),
        json={
            "answer": answer_for(question, correct=correct),
            "answer_format": "choice",
            "response_context": "study_block",
            "idempotency_key": key,
        },
    )
    assert response.status_code == 200
    return response.json()


def question_ids(payload: dict[str, object]) -> list[str]:
    return [str(item["question_id"]) for item in payload["items"]]


def assert_public_queue(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    assert payload["mode"] == "attempt_aware"
    assert payload["source"] == "user_scope"
    assert payload["items_count"] == len(payload["items"])
    assert "correct_answer" not in dumped
    assert "answer_key" not in dumped
    assert "rationale" not in dumped
    assert "priority" not in dumped
    assert "temporarily_mastered" not in dumped
    assert "storage_path" not in dumped
    assert "raw_text" not in dumped


def test_new_current_block_questions_are_returned_deterministically(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    [block_id] = prepare_blocks(client, 1)
    question = internal_question(repository, str(user["user_id"]), block_id)

    first = client.get(queue_path(block_id)).json()
    second = client.get(queue_path(block_id)).json()

    assert first == second
    assert first["queue_status"] == "ready"
    assert question_ids(first) == [str(question["question_id"])]
    assert_public_queue(first)


def test_incorrect_question_becomes_weak_after_one_intervening_attempt(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_a, block_b = prepare_blocks(client, 2)
    question_a = internal_question(repository, str(user["user_id"]), block_a)
    question_b = internal_question(repository, str(user["user_id"]), block_b)
    mark_studied(client, block_b)

    submit_answer(client, block_a, question_a, key="wrong-a", correct=False)
    immediate = client.get(queue_path(block_a)).json()
    submit_answer(client, block_b, question_b, key="intervening-b", correct=True)
    after_intervening = client.get(queue_path(block_a)).json()

    assert question_ids(immediate)[0] != str(question_a["question_id"])
    assert question_ids(after_intervening)[0] == str(question_a["question_id"])
    assert_public_queue(after_intervening)


def test_correct_once_is_reviewing_and_suppressed_until_three_later_attempts(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_a, block_b = prepare_blocks(client, 2)
    question_a = internal_question(repository, str(user["user_id"]), block_a)
    question_b = internal_question(repository, str(user["user_id"]), block_b)
    mark_studied(client, block_b)

    submit_answer(client, block_a, question_a, key="correct-a-1", correct=True)
    for index in range(2):
        submit_answer(client, block_b, question_b, key=f"later-b-{index}", correct=True)
    before_due = client.get(queue_path(block_a)).json()
    submit_answer(client, block_b, question_b, key="later-b-3", correct=True)
    due = client.get(queue_path(block_a)).json()

    assert str(question_a["question_id"]) not in question_ids(before_due)
    assert str(question_a["question_id"]) in question_ids(due)


def test_repeated_correct_is_temporarily_mastered_until_eight_later_attempts(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_a, block_b = prepare_blocks(client, 2)
    question_a = internal_question(repository, str(user["user_id"]), block_a)
    question_b = internal_question(repository, str(user["user_id"]), block_b)
    mark_studied(client, block_b)

    submit_answer(client, block_a, question_a, key="master-a-1", correct=True)
    submit_answer(client, block_b, question_b, key="later-before-master", correct=True)
    submit_answer(client, block_a, question_a, key="master-a-2", correct=True)
    for index in range(7):
        submit_answer(client, block_b, question_b, key=f"master-later-{index}", correct=True)
    before_due = client.get(queue_path(block_a)).json()
    submit_answer(client, block_b, question_b, key="master-later-8", correct=True)
    due = client.get(queue_path(block_a)).json()

    assert str(question_a["question_id"]) not in question_ids(before_due)
    assert str(question_a["question_id"]) in question_ids(due)


def test_ungraded_attempt_is_cautiously_eligible_after_one_later_attempt(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_a, block_b = prepare_blocks(client, 2)
    question_a = internal_question(repository, str(user["user_id"]), block_a)
    question_b = internal_question(repository, str(user["user_id"]), block_b)
    mark_studied(client, block_b)

    repository.record_study_question_attempt(
        user_id=str(user["user_id"]),
        question_id=str(question_a["question_id"]),
        selected_answer=answer_for(question_a),
        correctness_state="ungraded",
        block_id=block_a,
        material_id=str(question_a["_material_id"]),
        topic_id=None,
        topic_label=None,
        subtopic_id=None,
        subtopic_label=None,
        question_fingerprint=str(question_a["_fingerprint"]),
        question_generator_version=str(question_a["_generator_version"]),
        response_context="study_block",
        idempotency_key="manual-ungraded-a",
    )
    assert str(question_a["question_id"]) not in question_ids(client.get(queue_path(block_a)).json())
    submit_answer(client, block_b, question_b, key="later-after-ungraded", correct=True)

    payload = client.get(queue_path(block_a)).json()

    assert question_ids(payload)[0] == str(question_a["question_id"])
    assert_public_queue(payload)


def test_mixed_queue_is_bounded_deduplicated_and_prioritized(tmp_path):
    client, repository, _ = create_client(tmp_path)
    user = register_and_login(client, "owner")
    blocks = prepare_blocks(client, 6)
    questions = [internal_question(repository, str(user["user_id"]), block_id) for block_id in blocks]
    for block_id in blocks[1:]:
        mark_studied(client, block_id)

    submit_answer(client, blocks[1], questions[1], key="weak-one", correct=False)
    submit_answer(client, blocks[2], questions[2], key="intervene-one", correct=True)
    submit_answer(client, blocks[3], questions[3], key="reviewing-one", correct=True)
    for index in range(3):
        submit_answer(client, blocks[4], questions[4], key=f"reviewing-cooldown-{index}", correct=True)

    payload = client.get(queue_path(blocks[0], limit=5)).json()
    ids = question_ids(payload)

    assert len(ids) <= 5
    assert len(ids) == len(set(ids))
    assert ids[0] == str(questions[1]["question_id"])
    assert str(questions[0]["question_id"]) in ids
    assert any(block_id in question_id for block_id in blocks[1:] for question_id in ids)
    assert_public_queue(payload)


def test_owner_isolation_and_studied_historical_boundary(tmp_path):
    owner, repository, _ = create_client(tmp_path)
    other = TestClient(create_app(repository=repository))
    owner_user = register_and_login(owner, "owner")
    other_user = register_and_login(other, "other")
    owner_blocks = prepare_blocks(owner, 3)
    other_blocks = prepare_blocks(other, 1)
    owner_questions = [
        internal_question(repository, str(owner_user["user_id"]), block_id)
        for block_id in owner_blocks
    ]
    other_question = internal_question(repository, str(other_user["user_id"]), other_blocks[0])
    mark_studied(owner, owner_blocks[1])
    submit_answer(other, other_blocks[0], other_question, key="other-wrong", correct=False)

    payload = owner.get(queue_path(owner_blocks[0], limit=5)).json()
    ids = question_ids(payload)

    assert any(owner_blocks[1] in question_id for question_id in ids)
    assert all(owner_blocks[2] not in question_id for question_id in ids)
    assert all(other_blocks[0] not in question_id for question_id in ids)
    assert str(owner_questions[0]["question_id"]) in ids
    assert_public_queue(payload)


def test_queue_get_is_read_only_and_survives_repository_reload(tmp_path):
    client, repository, data_path = create_client(tmp_path)
    user = register_and_login(client, "owner")
    block_a, block_b = prepare_blocks(client, 2)
    question_a = internal_question(repository, str(user["user_id"]), block_a)
    question_b = internal_question(repository, str(user["user_id"]), block_b)
    mark_studied(client, block_b)
    submit_answer(client, block_a, question_a, key="reload-wrong-a", correct=False)
    submit_answer(client, block_b, question_b, key="reload-later-b", correct=True)
    before_attempts = repository.list_study_question_attempts(user_id=str(user["user_id"]))
    before_progress = repository.list_study_progress_events(user_id=str(user["user_id"]))

    first = client.get(queue_path(block_a)).json()
    second = client.get(queue_path(block_a)).json()
    reloaded_repository = JsonStudyRepository(data_path)
    reloaded_client = TestClient(create_app(repository=reloaded_repository))
    login = reloaded_client.post(
        "/api/auth/login",
        json={"username": "owner", "password": "senha-segura-123"},
    )
    assert login.status_code == 200
    after_reload = reloaded_client.get(queue_path(block_a)).json()

    assert first == second == after_reload
    assert repository.list_study_question_attempts(user_id=str(user["user_id"])) == before_attempts
    assert repository.list_study_progress_events(user_id=str(user["user_id"])) == before_progress
    assert reloaded_repository.get_study_question_attempt_states(user_id=str(user["user_id"])) == {}
    assert_public_queue(first)
