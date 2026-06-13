import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository


ALLOWED_EVENT_KEYS = {
    "event_id",
    "event_type",
    "target_type",
    "target_id",
    "created_at",
    "source",
}

ALLOWED_SUMMARY_KEYS = {
    "progress_status",
    "opened_blocks_count",
    "studied_blocks_count",
    "prepared_materials_count",
    "studied_materials_count",
    "review_due",
    "review_basis",
    "reviewed_questions_count",
    "weak_topics_count",
    "source",
}

FORBIDDEN_RESPONSE_TERMS = (
    "RAW-PROGRESS-SHOULD-NOT-LEAK",
    "extracted_text",
    "chunk body",
    "section body",
    "storage_path",
    "/Users/",
    "C:\\",
    "token",
    "cookie",
    "studyflow_session",
    "password_hash",
    "answer_key",
    "gabarito",
    "correct_answer",
    "correct_alternative",
    "score",
    "correction",
    "answer payload",
    "progress internal trace",
)

FORBIDDEN_WORDING = (
    "progresso atualizado",
    "você concluiu",
    "concluído",
    "acertos/erros oficiais",
)


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


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


def post_progress_event(
    client: TestClient,
    *,
    event_type: str,
    target_type: str,
    target_id: str,
    idempotency_key: str | None = None,
):
    payload = {
        "event_type": event_type,
        "target_type": target_type,
        "target_id": target_id,
    }
    if idempotency_key is not None:
        payload["idempotency_key"] = idempotency_key
    return client.post("/api/study/progress/events", json=payload)


def upload_material(
    client: TestClient,
    *,
    filename: str,
    content: bytes,
    material_type: str = "study_material",
) -> dict[str, object]:
    uploaded = client.post(
        "/api/materials/upload",
        files={"file": (filename, BytesIO(content), "text/markdown")},
        data={"material_type": material_type},
    )
    assert uploaded.status_code == 201
    return uploaded.json()


def upload_and_prepare_study_material(client: TestClient, index: int) -> str:
    uploaded = upload_material(
        client,
        filename=f"progress-aula-{index}.md",
        content=(
            f"# Aula {index}\n\n"
            "RAW-PROGRESS-SHOULD-NOT-LEAK\n\n"
            "Conteudo seguro para estudo."
        ).encode("utf-8"),
    )
    document_id = uploaded["metadata"]["document_id"]
    prepared = client.post(f"/api/materials/{document_id}/study/prepare")
    assert prepared.status_code == 200
    return str(document_id)


def assert_no_forbidden_terms(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=False)
    lowered = dumped.lower()
    for term in FORBIDDEN_RESPONSE_TERMS:
        assert term not in dumped
    for term in FORBIDDEN_WORDING:
        assert term not in lowered


def assert_bounded_event_payload(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_EVENT_KEYS
    assert payload["event_id"].startswith("study-progress-event:")
    assert payload["event_type"] in {
        "block_opened",
        "block_marked_studied",
        "question_reviewed",
        "review_opened",
        "review_completed",
    }
    assert payload["target_type"] in {"block", "question", "review"}
    assert isinstance(payload["target_id"], str)
    assert isinstance(payload["created_at"], str)
    assert payload["source"] == "user_scope"
    assert_no_forbidden_terms(payload)


def assert_bounded_summary_payload(payload: dict[str, object]) -> None:
    assert set(payload.keys()) == ALLOWED_SUMMARY_KEYS
    assert payload["progress_status"] in {"ready", "not_ready"}
    assert isinstance(payload["opened_blocks_count"], int)
    assert isinstance(payload["studied_blocks_count"], int)
    assert isinstance(payload["prepared_materials_count"], int)
    assert isinstance(payload["studied_materials_count"], int)
    assert isinstance(payload["review_due"], bool)
    assert payload["review_basis"] in {"prepared_materials", "studied_materials", "none"}
    assert isinstance(payload["reviewed_questions_count"], int)
    assert isinstance(payload["weak_topics_count"], int)
    assert payload["weak_topics_count"] == 0
    assert payload["source"] == "user_scope"
    assert_no_forbidden_terms(payload)


def test_progress_event_post_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = post_progress_event(
        anonymous,
        event_type="block_opened",
        target_type="block",
        target_id="study-block:material:doc:0",
    )

    assert response.status_code == 401


def test_progress_summary_requires_auth(tmp_path):
    _, _, anonymous, _ = create_clients(tmp_path)

    response = anonymous.get("/api/study/progress/summary")

    assert response.status_code == 401


def test_block_opened_event_is_bounded_and_does_not_count_as_studied(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = post_progress_event(
        owner,
        event_type="block_opened",
        target_type="block",
        target_id="study-block:material:doc-1:0",
    )
    summary = owner.get("/api/study/progress/summary").json()

    assert response.status_code == 200
    assert_bounded_event_payload(response.json())
    assert summary["opened_blocks_count"] == 1
    assert summary["studied_blocks_count"] == 0
    assert_bounded_summary_payload(summary)


def test_block_marked_studied_increments_studied_block_count(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = post_progress_event(
        owner,
        event_type="block_marked_studied",
        target_type="block",
        target_id="study-block:material:doc-1:0",
    )
    summary = owner.get("/api/study/progress/summary").json()

    assert response.status_code == 200
    assert_bounded_event_payload(response.json())
    assert summary["studied_blocks_count"] == 1
    assert summary["studied_materials_count"] == 0
    assert_bounded_summary_payload(summary)


def test_question_reviewed_event_is_bounded_without_score_or_correction(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    response = post_progress_event(
        owner,
        event_type="question_reviewed",
        target_type="question",
        target_id="question:study-block:material:doc-1:0:0",
    )
    summary = owner.get("/api/study/progress/summary").json()

    assert response.status_code == 200
    assert_bounded_event_payload(response.json())
    assert summary["reviewed_questions_count"] == 1
    assert_bounded_summary_payload(summary)


def test_progress_event_idempotency_returns_stable_event_without_duplicate_count(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    first = post_progress_event(
        owner,
        event_type="block_marked_studied",
        target_type="block",
        target_id="study-block:material:doc-1:0",
        idempotency_key="mark-study-block-doc-1",
    )
    second = post_progress_event(
        owner,
        event_type="block_marked_studied",
        target_type="block",
        target_id="study-block:material:doc-1:0",
        idempotency_key="mark-study-block-doc-1",
    )
    summary = owner.get("/api/study/progress/summary").json()

    assert first.status_code == 200
    assert second.status_code == 200
    assert second.json() == first.json()
    assert summary["studied_blocks_count"] == 1
    assert_bounded_summary_payload(summary)


def test_progress_events_are_user_scoped(tmp_path):
    owner, other, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")

    created = post_progress_event(
        owner,
        event_type="block_marked_studied",
        target_type="block",
        target_id="study-block:material:owner-doc:0",
    )
    other_summary = other.get("/api/study/progress/summary").json()

    assert created.status_code == 200
    assert other_summary["studied_blocks_count"] == 0
    assert other_summary["opened_blocks_count"] == 0
    assert_bounded_summary_payload(other_summary)


def test_progress_event_validation_rejects_missing_or_unknown_fields(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")

    assert owner.post(
        "/api/study/progress/events",
        json={"target_type": "block", "target_id": "study-block:material:doc:0"},
    ).status_code == 422
    assert owner.post(
        "/api/study/progress/events",
        json={"event_type": "block_opened", "target_type": "block"},
    ).status_code == 422
    assert post_progress_event(
        owner,
        event_type="automatic_completion",
        target_type="block",
        target_id="study-block:material:doc:0",
    ).status_code == 422
    assert post_progress_event(
        owner,
        event_type="block_opened",
        target_type="score",
        target_id="study-block:material:doc:0",
    ).status_code == 422
    assert post_progress_event(
        owner,
        event_type="question_reviewed",
        target_type="block",
        target_id="study-block:material:doc:0",
    ).status_code == 422
    assert owner.post(
        "/api/study/progress/events",
        json={
            "event_type": "question_reviewed",
            "target_type": "question",
            "target_id": "question-1",
            "answer": "A",
            "score": 1,
            "answer_key": "A",
            "gabarito": "A",
        },
    ).status_code == 422


def test_progress_summary_counts_prepared_study_materials_conservatively(tmp_path):
    owner, _, _, _ = create_clients(tmp_path)
    register_and_login(owner, "owner")
    for index in range(1, 4):
        upload_and_prepare_study_material(owner, index)
    upload_material(
        owner,
        filename="edital.md",
        content=b"# Edital\n\nNao conta como material estudado.",
        material_type="edital",
    )

    response = owner.get("/api/study/progress/summary")
    payload = response.json()

    assert response.status_code == 200
    assert payload["progress_status"] == "ready"
    assert payload["prepared_materials_count"] == 3
    assert payload["studied_materials_count"] == 0
    assert payload["review_due"] is True
    assert payload["review_basis"] == "prepared_materials"
    assert_bounded_summary_payload(payload)


def test_progress_responses_do_not_leak_private_fields_or_forbidden_wording(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    registered = register_and_login(owner, "owner")
    user_id = str(registered["user_id"])

    event_response = post_progress_event(
        owner,
        event_type="question_reviewed",
        target_type="question",
        target_id="question:bounded",
    )
    summary_response = owner.get("/api/study/progress/summary")
    progress_state = repository.load_progress(user_id=user_id).model_dump(mode="json")

    assert event_response.status_code == 200
    assert summary_response.status_code == 200
    assert progress_state["total_errors"] == 0
    assert progress_state["weak_topics"] == {}
    assert_bounded_event_payload(event_response.json())
    assert_bounded_summary_payload(summary_response.json())
