import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_final_approvals import (
    build_approval_artifact,
    explicit_approve_for_future_execution_review_fixture,
    no_decision_payload_fixture,
    single_decision_payload,
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


def prepare_approval_artifact(repository, tmp_path, user_id: str):
    fixture = explicit_approve_for_future_execution_review_fixture(
        tmp_path, user_id=user_id, repository=repository
    )
    payload = single_decision_payload(
        fixture,
        decision_type="approve_for_future_execution_review",
        reason="Approved for future execution review only.",
    )
    artifact = build_approval_artifact(fixture, decision_payload=payload)
    assert artifact is not None
    return artifact


def test_simulado_execution_shell_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    approval_artifact = prepare_approval_artifact(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell")
    build = owner.post(f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell/build")
    loaded = owner.get(f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell")
    execution_shell_id = build.json()["execution_shell_id"]
    by_id = owner.get(f"/api/simulado-execution-shell/{execution_shell_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_final_approval_artifact_id"] == approval_artifact.approval_artifact_id
    assert loaded.json()["execution_shell_active"] is False
    assert loaded.json()["execution_started"] is False
    assert loaded.json()["attempt_created"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-execution-shell/{execution_shell_id}").status_code == 401


def test_simulado_execution_shell_build_is_deterministic_and_does_not_duplicate(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    approval_artifact = prepare_approval_artifact(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell/build")
    second = owner.post(f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell/build")
    listed = repository.list_user_simulado_execution_shells(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_simulado_execution_shell(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    approval_artifact = prepare_approval_artifact(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell/build")
    assert build.status_code == 200
    execution_shell_id = build.json()["execution_shell_id"]

    assert other.post(
        f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell"
    ).status_code == 404
    assert other.get(f"/api/simulado-execution-shell/{execution_shell_id}").status_code == 404


def test_get_execution_shell_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    fixture = no_decision_payload_fixture(tmp_path / "owner", user_id=owner_user_id, repository=repository)
    approval_artifact = build_approval_artifact(fixture)
    assert approval_artifact is not None

    missing = owner.get(f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell")
    before = repository.get_simulado_final_approval_artifact_by_id(
        approval_artifact.approval_artifact_id,
        user_id=owner_user_id,
    )
    build = owner.post(f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell/build")
    loaded = owner.get(f"/api/simulado-final-approval/{approval_artifact.approval_artifact_id}/execution-shell")
    after = repository.get_simulado_final_approval_artifact_by_id(
        approval_artifact.approval_artifact_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after is not None
    assert before.model_dump(mode="json") == after.model_dump(mode="json")

