import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_propagation_guardrails import (
    blocked_source_ledger_fixture,
    successful_source_ledger_fixture,
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


def prepare_applied_event_ledger(repository, tmp_path, user_id: str, *, blocked: bool):
    fixture_builder = blocked_source_ledger_fixture if blocked else successful_source_ledger_fixture
    fixture = fixture_builder(tmp_path, user_id=user_id, repository=repository)
    assert fixture.applied_event_ledger is not None
    return fixture.applied_event_ledger


def test_propagation_guardrail_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    source_ledger = prepare_applied_event_ledger(
        repository,
        tmp_path / "owner",
        owner_user_id,
        blocked=True,
    )

    missing = owner.get(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail"
    )
    build = owner.post(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail/build"
    )
    loaded = owner.get(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail"
    )
    guardrail_id = build.json()["propagation_guardrail_id"]
    by_id = owner.get(f"/api/simulado-propagation-guardrail/{guardrail_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_applied_event_ledger_id"] == source_ledger.applied_event_ledger_id
    assert loaded.json()["propagation_guardrail_created"] is True
    assert loaded.json()["propagation_allowed_now"] is False
    assert loaded.json()["propagation_applied"] is False
    assert loaded.json()["final_event_applied_globally"] is False
    assert loaded.json()["existing_progress_aggregate_mutated"] is False
    assert loaded.json()["global_progress_mutation_applied"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped

    assert anonymous.post(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-propagation-guardrail/{guardrail_id}").status_code == 401


def test_propagation_guardrail_build_is_idempotent_for_same_source_ledger(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    source_ledger = prepare_applied_event_ledger(
        repository,
        tmp_path / "owner",
        owner_user_id,
        blocked=False,
    )

    first = owner.post(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail/build"
    )
    second = owner.post(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail/build"
    )
    listed = repository.list_user_simulado_propagation_guardrails(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_propagation_guardrail(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    source_ledger = prepare_applied_event_ledger(
        repository,
        tmp_path / "owner",
        owner_user_id,
        blocked=False,
    )
    build = owner.post(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail/build"
    )
    assert build.status_code == 200
    guardrail_id = build.json()["propagation_guardrail_id"]

    assert other.post(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail"
    ).status_code == 404
    assert other.get(f"/api/simulado-propagation-guardrail/{guardrail_id}").status_code == 404


def test_get_propagation_guardrail_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    fixture = successful_source_ledger_fixture(
        tmp_path / "owner",
        user_id=owner_user_id,
        repository=repository,
    )
    source_ledger = fixture.applied_event_ledger
    assert source_ledger is not None

    missing = owner.get(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail"
    )
    before_ledger = repository.get_simulado_applied_event_ledger_by_id(
        source_ledger.applied_event_ledger_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail/build"
    )
    loaded = owner.get(
        f"/api/simulado-applied-event-ledger/{source_ledger.applied_event_ledger_id}/propagation-guardrail"
    )
    after_ledger = repository.get_simulado_applied_event_ledger_by_id(
        source_ledger.applied_event_ledger_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_ledger is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_ledger is not None
    assert before_ledger.model_dump(mode="json") == after_ledger.model_dump(mode="json")
