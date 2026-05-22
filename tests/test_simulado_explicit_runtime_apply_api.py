import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_explicit_runtime_applies import (
    api_readonly_fixture,
    approve_payload,
    deny_payload,
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


def prepare_apply_shell(repository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    shell = fixture.controlled_apply_shell
    assert shell is not None
    return shell


def test_explicit_runtime_apply_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    shell = prepare_apply_shell(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply")
    build = owner.post(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply/build",
        json=approve_payload(),
    )
    loaded = owner.get(f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply")
    explicit_apply_id = build.json()["explicit_apply_id"]
    by_id = owner.get(f"/api/simulado-explicit-apply/{explicit_apply_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_apply_shell_id"] == shell.apply_shell_id
    assert loaded.json()["explicit_apply_recorded"] is True
    assert loaded.json()["runtime_application_enabled"] is False
    assert loaded.json()["runtime_application_applied"] is False
    assert loaded.json()["progress_mutation_enabled"] is False
    assert loaded.json()["progress_mutation_applied"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply/build",
        json=approve_payload(),
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-explicit-apply/{explicit_apply_id}").status_code == 401


def test_explicit_runtime_apply_build_is_deterministic_for_same_payload_and_isolated_for_different_payload(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    shell = prepare_apply_shell(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply/build",
        json=approve_payload(),
    )
    second = owner.post(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply/build",
        json=approve_payload(),
    )
    third = owner.post(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply/build",
        json=deny_payload(),
    )
    listed = repository.list_user_simulado_explicit_runtime_applies(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert third.status_code == 200
    assert first.json() == second.json()
    assert first.json()["explicit_apply_id"] != third.json()["explicit_apply_id"]
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_explicit_runtime_apply(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    shell = prepare_apply_shell(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply/build",
        json=approve_payload(),
    )
    assert build.status_code == 200
    explicit_apply_id = build.json()["explicit_apply_id"]

    assert other.post(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply/build",
        json=approve_payload(),
    ).status_code == 404
    assert other.get(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply"
    ).status_code == 404
    assert other.get(f"/api/simulado-explicit-apply/{explicit_apply_id}").status_code == 404


def test_get_explicit_runtime_apply_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    shell = prepare_apply_shell(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply")
    before_shell = repository.get_simulado_controlled_apply_shell_by_id(
        shell.apply_shell_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply/build",
        json=approve_payload(),
    )
    loaded = owner.get(f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply")
    after_shell = repository.get_simulado_controlled_apply_shell_by_id(
        shell.apply_shell_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_shell is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_shell is not None
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
