import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_integrated_execution_corrections import api_readonly_fixture


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
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    attempt_session = fixture.attempt_session
    assert attempt_session is not None
    return attempt_session


def test_simulado_integrated_execution_correction_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    attempt_session = prepare_attempt_session(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result")
    build = owner.post(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result/build")
    loaded = owner.get(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result")
    integrated_result_id = build.json()["integrated_result_id"]
    by_id = owner.get(f"/api/simulado-integrated-result/{integrated_result_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_attempt_session_id"] == attempt_session.attempt_session_id
    assert loaded.json()["progress_mutation_applied"] is False
    assert loaded.json()["ranking_update_applied"] is False
    assert loaded.json()["retention_update_applied"] is False
    assert loaded.json()["scheduler_update_applied"] is False
    assert loaded.json()["study_cycle_update_applied"] is False
    assert loaded.json()["curriculum_graph_update_applied"] is False
    assert loaded.json()["adaptive_tuning_applied"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-integrated-result/{integrated_result_id}").status_code == 401


def test_simulado_integrated_execution_correction_build_is_deterministic_for_same_source(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    attempt_session = prepare_attempt_session(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result/build"
    )
    second = owner.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result/build"
    )
    listed = repository.list_user_simulado_integrated_results(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_integrated_execution_correction(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    attempt_session = prepare_attempt_session(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result/build"
    )
    assert build.status_code == 200
    integrated_result_id = build.json()["integrated_result_id"]

    assert other.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result"
    ).status_code == 404
    assert other.get(f"/api/simulado-integrated-result/{integrated_result_id}").status_code == 404


def test_get_integrated_execution_correction_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    attempt_session = prepare_attempt_session(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result")
    before_attempt = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result/build"
    )
    loaded = owner.get(f"/api/simulado-attempt-session/{attempt_session.attempt_session_id}/integrated-result")
    after_attempt = repository.get_simulado_attempt_session_by_id(
        attempt_session.attempt_session_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_attempt is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_attempt is not None
    assert before_attempt.model_dump(mode="json") == after_attempt.model_dump(mode="json")
