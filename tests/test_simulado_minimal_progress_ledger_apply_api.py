import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_minimal_progress_ledger_applies import (
    allowed_minimal_progress_ledger_apply_fixture,
    build_minimal_progress_ledger_apply,
    policy_feature_flag_disabled_fixture,
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


def prepare_policy(repository, tmp_path, user_id: str, *, allowed: bool):
    fixture_builder = (
        allowed_minimal_progress_ledger_apply_fixture
        if allowed
        else policy_feature_flag_disabled_fixture
    )
    fixture = fixture_builder(tmp_path, user_id=user_id, repository=repository)
    assert fixture.runtime_apply_policy is not None
    return fixture.runtime_apply_policy


def test_minimal_progress_ledger_apply_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    policy = prepare_policy(repository, tmp_path / "owner", owner_user_id, allowed=False)

    missing = owner.get(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply"
    )
    build = owner.post(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
    )
    loaded = owner.get(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply"
    )
    apply_id = build.json()["minimal_progress_ledger_apply_id"]
    by_id = owner.get(f"/api/simulado-minimal-progress-ledger-apply/{apply_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_runtime_apply_policy_id"] == policy.runtime_apply_policy_id
    assert loaded.json()["minimal_progress_ledger_apply_created"] is True
    assert loaded.json()["minimal_progress_ledger_apply_applied"] is False
    assert loaded.json()["existing_progress_aggregate_mutated"] is False
    assert loaded.json()["global_progress_mutation_applied"] is False
    assert loaded.json()["ranking_update_applied"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped

    assert anonymous.post(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-minimal-progress-ledger-apply/{apply_id}"
    ).status_code == 401


def test_minimal_progress_ledger_apply_build_is_idempotent_for_same_source_policy(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    policy = prepare_policy(repository, tmp_path / "owner", owner_user_id, allowed=True)

    first = owner.post(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
    )
    second = owner.post(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
    )
    listed = repository.list_user_simulado_minimal_progress_ledger_applies(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_minimal_progress_ledger_apply(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    policy = prepare_policy(repository, tmp_path / "owner", owner_user_id, allowed=True)
    build = owner.post(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
    )
    assert build.status_code == 200
    apply_id = build.json()["minimal_progress_ledger_apply_id"]

    assert other.post(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-minimal-progress-ledger-apply/{apply_id}"
    ).status_code == 404


def test_get_minimal_progress_ledger_apply_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    fixture = allowed_minimal_progress_ledger_apply_fixture(
        tmp_path / "owner",
        user_id=owner_user_id,
        repository=repository,
    )
    policy = fixture.runtime_apply_policy
    assert policy is not None

    missing = owner.get(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply"
    )
    before_policy = repository.get_simulado_runtime_apply_policy_by_id(
        policy.runtime_apply_policy_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
    )
    loaded = owner.get(
        f"/api/simulado-runtime-apply-policy/{policy.runtime_apply_policy_id}/minimal-progress-ledger-apply"
    )
    after_policy = repository.get_simulado_runtime_apply_policy_by_id(
        policy.runtime_apply_policy_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_policy is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_policy is not None
    assert before_policy.model_dump(mode="json") == after_policy.model_dump(mode="json")
