import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_applied_event_ledgers import (
    blocked_source_apply_fixture,
    successful_source_apply_fixture,
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


def prepare_minimal_apply(repository, tmp_path, user_id: str, *, allowed: bool):
    fixture_builder = (
        successful_source_apply_fixture if allowed else blocked_source_apply_fixture
    )
    fixture = fixture_builder(tmp_path, user_id=user_id, repository=repository)
    assert fixture.minimal_apply is not None
    return fixture.minimal_apply


def test_applied_event_ledger_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    minimal_apply = prepare_minimal_apply(repository, tmp_path / "owner", owner_user_id, allowed=False)

    missing = owner.get(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger"
    )
    build = owner.post(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger/build"
    )
    loaded = owner.get(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger"
    )
    ledger_id = build.json()["applied_event_ledger_id"]
    by_id = owner.get(f"/api/simulado-applied-event-ledger/{ledger_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_minimal_progress_ledger_apply_id"] == minimal_apply.minimal_progress_ledger_apply_id
    assert loaded.json()["applied_event_ledger_created"] is True
    assert loaded.json()["ledger_event_recorded"] is False
    assert loaded.json()["ledger_event_count"] == 0
    assert loaded.json()["final_event_applied_globally"] is False
    assert loaded.json()["existing_progress_aggregate_mutated"] is False
    assert loaded.json()["global_progress_mutation_applied"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped

    assert anonymous.post(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-applied-event-ledger/{ledger_id}"
    ).status_code == 401


def test_applied_event_ledger_build_is_idempotent_for_same_source_apply(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    minimal_apply = prepare_minimal_apply(repository, tmp_path / "owner", owner_user_id, allowed=True)

    first = owner.post(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger/build"
    )
    second = owner.post(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger/build"
    )
    listed = repository.list_user_simulado_applied_event_ledgers(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_applied_event_ledger(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    minimal_apply = prepare_minimal_apply(repository, tmp_path / "owner", owner_user_id, allowed=True)
    build = owner.post(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger/build"
    )
    assert build.status_code == 200
    ledger_id = build.json()["applied_event_ledger_id"]

    assert other.post(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-applied-event-ledger/{ledger_id}"
    ).status_code == 404


def test_get_applied_event_ledger_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    fixture = successful_source_apply_fixture(
        tmp_path / "owner",
        user_id=owner_user_id,
        repository=repository,
    )
    minimal_apply = fixture.minimal_apply
    assert minimal_apply is not None

    missing = owner.get(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger"
    )
    before_apply = repository.get_simulado_minimal_progress_ledger_apply_by_id(
        minimal_apply.minimal_progress_ledger_apply_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger/build"
    )
    loaded = owner.get(
        f"/api/simulado-minimal-progress-ledger-apply/{minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger"
    )
    after_apply = repository.get_simulado_minimal_progress_ledger_apply_by_id(
        minimal_apply.minimal_progress_ledger_apply_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_apply is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_apply is not None
    assert before_apply.model_dump(mode="json") == after_apply.model_dump(mode="json")
