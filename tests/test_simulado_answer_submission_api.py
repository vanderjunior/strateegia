import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_attempt_sessions import (
    build_attempt_session,
    prepared_items_non_submittable_fixture,
)


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> str:
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
    return logged_in.json()["user"]["user_id"]


def prepare_attempt_session(repository, tmp_path, user_id: str):
    fixture = prepared_items_non_submittable_fixture(
        tmp_path, user_id=user_id, repository=repository
    )
    result = build_attempt_session(fixture)
    assert result is not None
    return result


def test_simulado_answer_submission_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    attempt_session = prepare_attempt_session(repository, tmp_path / "owner", owner_user_id)
    item_id = attempt_session.items[0].item_id

    missing = owner.get(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission")
    build = owner.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission/build",
        json={
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "A",
                }
            ]
        },
    )
    loaded = owner.get(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission")
    answer_submission_id = build.json()["answer_submission_id"]
    by_id = owner.get(f"/api/simulado-answer-submission/{answer_submission_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_attempt_session_id"] == attempt_session.attempt_session_id
    assert loaded.json()["correction_enabled"] is False
    assert loaded.json()["scoring_enabled"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-answer-submission/{answer_submission_id}").status_code == 401


def test_simulado_answer_submission_build_is_deterministic_for_same_payload(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    attempt_session = prepare_attempt_session(repository, tmp_path / "owner", owner_user_id)
    item_id = attempt_session.items[0].item_id

    payload = {
        "answers": [
            {
                "source_session_item_id": item_id,
                "answer_kind": "selected_option",
                "submitted_value": "A",
            }
        ]
    }
    first = owner.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission/build",
        json=payload,
    )
    second = owner.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission/build",
        json=payload,
    )
    listed = repository.list_user_simulado_answer_submissions(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_simulado_answer_submission(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    attempt_session = prepare_attempt_session(repository, tmp_path / "owner", owner_user_id)
    item_id = attempt_session.items[0].item_id
    build = owner.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission/build",
        json={
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "A",
                }
            ]
        },
    )
    assert build.status_code == 200
    answer_submission_id = build.json()["answer_submission_id"]

    assert other.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission/build",
        json={"answers": []},
    ).status_code == 404
    assert other.get(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission"
    ).status_code == 404
    assert other.get(f"/api/simulado-answer-submission/{answer_submission_id}").status_code == 404


def test_get_answer_submission_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    attempt_session = prepare_attempt_session(repository, tmp_path / "owner", owner_user_id)
    item_id = attempt_session.items[0].item_id

    missing = owner.get(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission")
    before = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission/build",
        json={
            "answers": [
                {
                    "source_session_item_id": item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "A",
                }
            ]
        },
    )
    loaded = owner.get(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/answer-submission")
    after = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after is not None
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
