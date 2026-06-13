import json

import pytest
from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.review_progress_qa_fixture import (
    QA_REVIEW_DEFAULT_PASSWORD,
    QA_REVIEW_FIXTURE_TAG,
    QA_REVIEW_USERNAME,
    seed_review_progress_browser_qa,
)


FORBIDDEN_TERMS = (
    "password_hash",
    "studyflow_session",
    "selected_answer",
    "answer payload",
    "answer_key",
    "gabarito",
    "correct_answer",
    "correct_alternative",
    "score",
    "correction",
    "storage_path",
    "/Users/",
    "C:\\",
    "internal trace",
)


def create_client(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), repository


def login_seeded_user(client: TestClient):
    response = client.post(
        "/api/auth/login",
        json={"username": QA_REVIEW_USERNAME, "password": QA_REVIEW_DEFAULT_PASSWORD},
    )
    assert response.status_code == 200
    assert response.json()["authenticated"] is True


def register_other_user(client: TestClient):
    registered = client.post(
        "/api/auth/register",
        json={
            "username": "other-fixture-user",
            "password": "senha-segura-123",
            "display_name": "Other Fixture User",
            "email": "other-fixture-user@example.com",
        },
    )
    assert registered.status_code == 201
    logged_in = client.post(
        "/api/auth/login",
        json={"username": "other-fixture-user", "password": "senha-segura-123"},
    )
    assert logged_in.status_code == 200


def dumped_payload(*payloads: object) -> str:
    return "\n".join(json.dumps(payload, ensure_ascii=False) for payload in payloads)


def assert_no_leakage(*payloads: object) -> None:
    dumped = dumped_payload(*payloads)
    lowered = dumped.lower()
    for term in FORBIDDEN_TERMS:
        assert term not in dumped
        assert term.lower() not in lowered


def qa_fixture_materials(repository: JsonStudyRepository, user_id: str):
    return [
        material
        for material in repository.list_uploaded_materials(user_id=user_id)
        if material.metadata.metadata.get("qa_fixture") == QA_REVIEW_FIXTURE_TAG
    ]


def test_review_progress_browser_qa_fixture_creates_expected_state(tmp_path):
    client, repository = create_client(tmp_path)

    result = seed_review_progress_browser_qa(repository)
    login_seeded_user(client)
    editais = client.get("/api/editais").json()
    blocks = client.get("/api/study/blocks").json()
    summary = client.get("/api/study/progress/summary").json()
    review = client.get("/api/study/review/next").json()

    assert editais["count"] == 1
    assert editais["items"][0]["analysis_status"] == "analyzed"
    assert editais["items"][0]["review_state"] == "ready_for_review"
    assert editais["items"][0]["topics_count"] == 3
    assert editais["items"][0]["subtopics_count"] == 3
    assert blocks["blocks_status"] == "ready"
    assert blocks["scope_status"] == "connected_to_edital"
    assert {item["block_id"] for item in blocks["items"]} == set(result.block_ids)
    assert {item["material_id"] for item in blocks["items"]} == set(result.material_ids)
    assert summary["prepared_materials_count"] >= 3
    assert summary["studied_materials_count"] >= 3
    assert summary["review_basis"] == "studied_materials"
    assert review["basis"] == "studied_materials"
    assert review["materials_count"] >= 3
    assert review["review_status"] in {"ready", "needs_review"}
    assert_no_leakage(result.safe_payload(), editais, blocks, summary, review)


def test_review_progress_browser_qa_fixture_is_idempotent(tmp_path):
    client, repository = create_client(tmp_path)

    first = seed_review_progress_browser_qa(repository)
    second = seed_review_progress_browser_qa(repository)
    login_seeded_user(client)
    summary = client.get("/api/study/progress/summary").json()
    review = client.get("/api/study/review/next").json()
    user = repository.get_user_by_username(QA_REVIEW_USERNAME)
    assert user is not None
    events = repository.list_study_progress_events(user_id=user.user_id)
    studied_events = [
        event
        for event in events
        if event.get("event_type") == "block_marked_studied"
        and str(event.get("idempotency_key", "")).startswith("qa-fixture:block_marked_studied:")
    ]

    assert first.material_ids == second.material_ids
    assert first.block_ids == second.block_ids
    assert first.progress_event_ids == second.progress_event_ids
    assert len(qa_fixture_materials(repository, user.user_id)) == 4
    assert len(studied_events) == 3
    assert summary["studied_materials_count"] == 3
    assert summary["review_basis"] == "studied_materials"
    assert review["basis"] == "studied_materials"
    assert_no_leakage(first.safe_payload(), second.safe_payload(), summary, review)


def test_review_progress_browser_qa_fixture_removes_legacy_fixture_ids(tmp_path):
    client, repository = create_client(tmp_path)

    first = seed_review_progress_browser_qa(repository)
    user = repository.get_user_by_username(QA_REVIEW_USERNAME)
    assert user is not None
    legacy_document_id = "qa-review-progress-material-legacy"
    legacy_block_id = f"study-block:material:{legacy_document_id}:0"
    payload = repository._read()
    user_state = repository._ensure_user_state(payload, user.user_id)
    user_state["materials"].append(
        {
            "metadata": {
                "document_id": legacy_document_id,
                "user_id": user.user_id,
                "filename": "legacy.md",
                "original_filename": "legacy.md",
                "content_type": "text/markdown",
                "size_bytes": 1,
                "storage_path": "",
                "status": "metadata_ready",
                "extraction_status": "metadata_ready",
                "material_type": "study_material",
                "created_at": "2026-01-01T00:00:00+00:00",
                "updated_at": "2026-01-01T00:00:00+00:00",
                "metadata": {"qa_fixture": QA_REVIEW_FIXTURE_TAG},
            },
            "extracted_text": None,
        }
    )
    user_state["document_pipeline"]["states"][legacy_document_id] = {"document_id": legacy_document_id}
    user_state["document_pipeline"]["extraction_results"][legacy_document_id] = {"document_id": legacy_document_id}
    user_state["study_progress_events"]["events"]["legacy-event"] = {
        "event_id": "legacy-event",
        "event_type": "block_marked_studied",
        "target_type": "block",
        "target_id": legacy_block_id,
        "idempotency_key": f"qa-fixture:block_marked_studied:{legacy_block_id}",
        "created_at": "2026-01-01T00:00:00+00:00",
    }
    user_state["study_progress_events"]["idempotency"][
        f"qa-fixture:block_marked_studied:{legacy_block_id}"
    ] = "legacy-event"
    repository._write(payload)

    second = seed_review_progress_browser_qa(repository)
    login_seeded_user(client)
    summary = client.get("/api/study/progress/summary").json()
    blocks = client.get("/api/study/blocks").json()
    payload = repository._read()
    user_state = repository._ensure_user_state(payload, user.user_id)

    assert first.block_ids == second.block_ids
    assert legacy_document_id not in {material.metadata.document_id for material in qa_fixture_materials(repository, user.user_id)}
    assert legacy_document_id not in user_state["document_pipeline"]["states"]
    assert "legacy-event" not in user_state["study_progress_events"]["events"]
    assert f"qa-fixture:block_marked_studied:{legacy_block_id}" not in user_state["study_progress_events"]["idempotency"]
    assert len(qa_fixture_materials(repository, user.user_id)) == 4
    assert summary["studied_materials_count"] == 3
    assert summary["review_basis"] == "studied_materials"
    assert {item["block_id"] for item in blocks["items"]} == set(second.block_ids)
    assert_no_leakage(summary, blocks)


def test_review_progress_browser_qa_fixture_is_user_scoped(tmp_path):
    seeded_client, repository = create_client(tmp_path)
    other_client = TestClient(seeded_client.app)

    seed_review_progress_browser_qa(repository)
    login_seeded_user(seeded_client)
    register_other_user(other_client)
    seeded_summary = seeded_client.get("/api/study/progress/summary").json()
    other_summary = other_client.get("/api/study/progress/summary").json()
    other_review = other_client.get("/api/study/review/next").json()

    assert seeded_summary["review_basis"] == "studied_materials"
    assert other_summary["prepared_materials_count"] == 0
    assert other_summary["studied_materials_count"] == 0
    assert other_summary["review_basis"] == "none"
    assert other_review["basis"] == "prepared_materials"
    assert other_review["materials_count"] == 0
    assert_no_leakage(seeded_summary, other_summary, other_review)


def test_review_progress_browser_qa_fixture_is_disabled_in_production(tmp_path, monkeypatch):
    _, repository = create_client(tmp_path)
    monkeypatch.setenv("APP_ENV", "production")

    with pytest.raises(RuntimeError):
        seed_review_progress_browser_qa(repository)

    assert repository.get_user_by_username(QA_REVIEW_USERNAME) is None
