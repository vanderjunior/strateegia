import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_final_pedagogical_update_events import (
    api_readonly_fixture as final_event_api_fixture,
    build_final_pedagogical_update_event,
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


def prepare_final_event(repository, tmp_path, user_id: str):
    fixture = final_event_api_fixture(tmp_path, user_id=user_id, repository=repository)
    final_event = build_final_pedagogical_update_event(fixture)
    assert final_event is not None
    return final_event


def test_runtime_apply_policy_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    final_event = prepare_final_event(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy"
    )
    build = owner.post(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy/build"
    )
    loaded = owner.get(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy"
    )
    runtime_apply_policy_id = build.json()["runtime_apply_policy_id"]
    by_id = owner.get(f"/api/simulado-runtime-apply-policy/{runtime_apply_policy_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_final_event_id"] == final_event.final_event_id
    assert loaded.json()["runtime_apply_policy_created"] is True
    assert loaded.json()["runtime_apply_feature_flag_enabled"] is False
    assert loaded.json()["runtime_apply_allowed_now"] is False
    assert loaded.json()["final_event_apply_allowed"] is False
    assert loaded.json()["final_event_applied"] is False
    assert loaded.json()["minimal_progress_ledger_apply_allowed"] is False
    assert loaded.json()["runtime_application_enabled"] is False
    assert loaded.json()["progress_mutation_enabled"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped

    assert anonymous.post(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-runtime-apply-policy/{runtime_apply_policy_id}"
    ).status_code == 401


def test_runtime_apply_policy_build_is_deterministic_for_same_source_final_event(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    final_event = prepare_final_event(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy/build"
    )
    second = owner.post(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy/build"
    )
    listed = repository.list_user_simulado_runtime_apply_policies(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_runtime_apply_policy(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    final_event = prepare_final_event(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy/build"
    )
    assert build.status_code == 200
    runtime_apply_policy_id = build.json()["runtime_apply_policy_id"]

    assert other.post(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-runtime-apply-policy/{runtime_apply_policy_id}"
    ).status_code == 404


def test_get_runtime_apply_policy_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    final_event = prepare_final_event(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy"
    )
    before_final_event = repository.get_simulado_final_pedagogical_update_event_by_id(
        final_event.final_event_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy/build"
    )
    loaded = owner.get(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy"
    )
    after_final_event = repository.get_simulado_final_pedagogical_update_event_by_id(
        final_event.final_event_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_final_event is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_final_event is not None
    assert before_final_event.model_dump(mode="json") == after_final_event.model_dump(mode="json")
