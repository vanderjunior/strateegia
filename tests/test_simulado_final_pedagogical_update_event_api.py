import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_final_pedagogical_update_events import (
    api_readonly_fixture,
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


def prepare_controlled_execution(repository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    return controlled_execution


def test_final_pedagogical_update_event_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    controlled_execution = prepare_controlled_execution(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event"
    )
    build = owner.post(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event/build"
    )
    loaded = owner.get(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event"
    )
    final_event_id = build.json()["final_event_id"]
    by_id = owner.get(f"/api/simulado-final-pedagogical-event/{final_event_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_controlled_execution_id"] == controlled_execution.controlled_execution_id
    assert loaded.json()["final_pedagogical_update_event_created"] is True
    assert loaded.json()["final_pedagogical_update_event_applied"] is False
    assert loaded.json()["final_pedagogical_update_event_apply_allowed"] is False
    assert loaded.json()["execution_started"] is False
    assert loaded.json()["commit_executed"] is False
    assert loaded.json()["mutation_committed"] is False
    assert loaded.json()["runtime_application_enabled"] is False
    assert loaded.json()["progress_mutation_enabled"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-final-pedagogical-event/{final_event_id}"
    ).status_code == 401


def test_final_pedagogical_update_event_build_is_deterministic_for_same_source_controlled_execution(
    tmp_path,
):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    controlled_execution = prepare_controlled_execution(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event/build"
    )
    second = owner.post(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event/build"
    )
    listed = repository.list_user_simulado_final_pedagogical_update_events(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_final_pedagogical_update_event(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    controlled_execution = prepare_controlled_execution(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event/build"
    )
    assert build.status_code == 200
    final_event_id = build.json()["final_event_id"]

    assert other.post(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-final-pedagogical-event/{final_event_id}"
    ).status_code == 404


def test_get_final_pedagogical_update_event_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    controlled_execution = prepare_controlled_execution(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event"
    )
    before_controlled = repository.get_simulado_controlled_runtime_commit_execution_by_id(
        controlled_execution.controlled_execution_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event/build"
    )
    loaded = owner.get(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event"
    )
    after_controlled = repository.get_simulado_controlled_runtime_commit_execution_by_id(
        controlled_execution.controlled_execution_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_controlled is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_controlled is not None
    assert before_controlled.model_dump(mode="json") == after_controlled.model_dump(mode="json")
