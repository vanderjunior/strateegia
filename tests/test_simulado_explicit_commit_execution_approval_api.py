import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_explicit_commit_execution_approvals import (
    api_readonly_fixture,
    approve_all_payload,
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


def prepare_execution_guardrail(repository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    execution_guardrail = fixture.execution_guardrail
    assert execution_guardrail is not None
    return execution_guardrail


def test_explicit_commit_execution_approval_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    execution_guardrail = prepare_execution_guardrail(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval"
    )
    build = owner.post(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval/build",
        json=approve_all_payload(),
    )
    loaded = owner.get(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval"
    )
    execution_approval_id = build.json()["execution_approval_id"]
    by_id = owner.get(f"/api/simulado-explicit-execution-approval/{execution_approval_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert (
        loaded.json()["source_execution_guardrail_id"]
        == execution_guardrail.execution_guardrail_id
    )
    assert loaded.json()["explicit_execution_approval_recorded"] is True
    assert loaded.json()["approved_for_execution_now"] is False
    assert loaded.json()["commit_execution_allowed"] is False
    assert loaded.json()["commit_execution_started"] is False
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
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval/build",
        json=approve_all_payload(),
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-explicit-execution-approval/{execution_approval_id}"
    ).status_code == 401


def test_explicit_commit_execution_approval_build_is_deterministic_for_same_payload_and_replaces_for_new_payload(
    tmp_path,
):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    execution_guardrail = prepare_execution_guardrail(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval/build",
        json=approve_payload(),
    )
    second = owner.post(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval/build",
        json=approve_payload(),
    )
    replaced = owner.post(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval/build",
        json=deny_payload(),
    )
    listed = repository.list_user_simulado_explicit_commit_execution_approvals(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert replaced.status_code == 200
    assert first.json() == second.json()
    assert first.json()["execution_approval_id"] != replaced.json()["execution_approval_id"]
    assert replaced.json()["decision_summary"]["decision_type"] == "deny_execution"
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_explicit_commit_execution_approval(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    execution_guardrail = prepare_execution_guardrail(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval/build",
        json=approve_all_payload(),
    )
    assert build.status_code == 200
    execution_approval_id = build.json()["execution_approval_id"]

    assert other.post(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval/build",
        json=approve_all_payload(),
    ).status_code == 404
    assert other.get(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-explicit-execution-approval/{execution_approval_id}"
    ).status_code == 404


def test_get_explicit_commit_execution_approval_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    execution_guardrail = prepare_execution_guardrail(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval"
    )
    before_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        execution_guardrail.execution_guardrail_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval/build",
        json=approve_all_payload(),
    )
    loaded = owner.get(
        f"/api/simulado-commit-execution-guardrail/{execution_guardrail.execution_guardrail_id}/explicit-execution-approval"
    )
    after_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        execution_guardrail.execution_guardrail_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_guardrail is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_guardrail is not None
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
