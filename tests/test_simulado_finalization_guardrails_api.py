import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_attempt_shells import build_attempt_shell, non_executable_assembly_fixture


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


def prepare_attempt_shell(repository, tmp_path, user_id: str) -> str:
    fixture = non_executable_assembly_fixture(tmp_path, user_id=user_id, repository=repository)
    shell = build_attempt_shell(fixture)
    assert shell is not None
    return shell.attempt_shell_id


def test_simulado_finalization_guardrail_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    attempt_shell_id = prepare_attempt_shell(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail")
    build = owner.post(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build")
    loaded = owner.get(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail")
    finalization_guardrail_id = build.json()["finalization_guardrail_id"]
    by_id = owner.get(f"/api/simulado-finalization-guardrail/{finalization_guardrail_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_attempt_shell_id"] == attempt_shell_id
    assert loaded.json()["approval_required"] is True
    assert loaded.json()["execution_enabled"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail").status_code == 401
    assert anonymous.get(f"/api/simulado-finalization-guardrail/{finalization_guardrail_id}").status_code == 401


def test_simulado_finalization_guardrail_build_is_deterministic_and_does_not_duplicate(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    attempt_shell_id = prepare_attempt_shell(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build")
    second = owner.post(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build")
    listed = repository.list_user_simulado_finalization_guardrails(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_simulado_finalization_guardrail(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    attempt_shell_id = prepare_attempt_shell(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build")
    assert build.status_code == 200
    finalization_guardrail_id = build.json()["finalization_guardrail_id"]

    assert other.post(
        f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build"
    ).status_code == 404
    assert other.get(f"/api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail").status_code == 404
    assert other.get(f"/api/simulado-finalization-guardrail/{finalization_guardrail_id}").status_code == 404
