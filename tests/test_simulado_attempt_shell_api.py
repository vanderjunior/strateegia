import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_question_assemblies import (
    build_assembly,
    ready_for_review_candidate_fixture,
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


def prepare_assembly(repository, tmp_path, user_id: str) -> str:
    fixture = ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    assembly = build_assembly(fixture)
    assert assembly is not None
    return assembly.assembly_id


def test_simulado_attempt_shell_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    assembly_id = prepare_assembly(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell")
    build = owner.post(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell/build")
    loaded = owner.get(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell")
    attempt_shell_id = build.json()["attempt_shell_id"]
    by_id = owner.get(f"/api/simulado-attempt-shell/{attempt_shell_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_assembly_id"] == assembly_id
    assert loaded.json()["execution_enabled"] is False
    assert loaded.json()["correction_enabled"] is False
    assert loaded.json()["scoring_enabled"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell/build").status_code == 401
    assert anonymous.get(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell").status_code == 401
    assert anonymous.get(f"/api/simulado-attempt-shell/{attempt_shell_id}").status_code == 401


def test_simulado_attempt_shell_build_is_deterministic_and_does_not_duplicate(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    assembly_id = prepare_assembly(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell/build")
    second = owner.post(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell/build")
    listed = repository.list_user_simulado_attempt_shells(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_simulado_attempt_shell(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    assembly_id = prepare_assembly(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell/build")
    assert build.status_code == 200
    attempt_shell_id = build.json()["attempt_shell_id"]

    assert other.post(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell/build").status_code == 404
    assert other.get(f"/api/simulado-question-assembly/{assembly_id}/attempt-shell").status_code == 404
    assert other.get(f"/api/simulado-attempt-shell/{attempt_shell_id}").status_code == 404
