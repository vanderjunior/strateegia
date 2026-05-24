import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_controlled_propagation_applies import (
    safe_source_guardrail_fixture,
    source_guardrail_blocked_fixture,
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


def prepare_guardrail(repository, tmp_path, user_id: str, *, safe: bool):
    fixture_builder = safe_source_guardrail_fixture if safe else source_guardrail_blocked_fixture
    fixture = fixture_builder(tmp_path, user_id=user_id, repository=repository)
    assert fixture.propagation_guardrail is not None
    return fixture.propagation_guardrail


def test_controlled_propagation_apply_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    guardrail = prepare_guardrail(repository, tmp_path / "owner", owner_user_id, safe=False)

    missing = owner.get(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply"
    )
    build = owner.post(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply/build"
    )
    loaded = owner.get(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply"
    )
    apply_id = build.json()["controlled_propagation_apply_id"]
    by_id = owner.get(f"/api/simulado-controlled-propagation-apply/{apply_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_propagation_guardrail_id"] == guardrail.propagation_guardrail_id
    assert loaded.json()["controlled_propagation_apply_created"] is True
    assert loaded.json()["controlled_propagation_ledger_recorded"] is False
    assert loaded.json()["controlled_propagation_entry_count"] == 0
    assert loaded.json()["final_event_applied_globally"] is False
    assert loaded.json()["existing_progress_aggregate_mutated"] is False
    assert loaded.json()["global_progress_mutation_applied"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped

    assert anonymous.post(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-controlled-propagation-apply/{apply_id}"
    ).status_code == 401


def test_controlled_propagation_apply_build_is_idempotent_for_same_source_guardrail(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    guardrail = prepare_guardrail(repository, tmp_path / "owner", owner_user_id, safe=True)

    first = owner.post(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply/build"
    )
    second = owner.post(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply/build"
    )
    listed = repository.list_user_simulado_controlled_propagation_applies(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_controlled_propagation_apply(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    guardrail = prepare_guardrail(repository, tmp_path / "owner", owner_user_id, safe=True)
    build = owner.post(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply/build"
    )
    assert build.status_code == 200
    apply_id = build.json()["controlled_propagation_apply_id"]

    assert other.post(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-controlled-propagation-apply/{apply_id}"
    ).status_code == 404


def test_get_controlled_propagation_apply_is_read_only_and_missing_source_does_not_build(
    tmp_path,
):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    fixture = safe_source_guardrail_fixture(
        tmp_path / "owner",
        user_id=owner_user_id,
        repository=repository,
    )
    guardrail = fixture.propagation_guardrail
    assert guardrail is not None

    missing = owner.get(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply"
    )
    before_guardrail = repository.get_simulado_propagation_guardrail_by_id(
        guardrail.propagation_guardrail_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply/build"
    )
    loaded = owner.get(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply"
    )
    after_guardrail = repository.get_simulado_propagation_guardrail_by_id(
        guardrail.propagation_guardrail_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_guardrail is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_guardrail is not None
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
