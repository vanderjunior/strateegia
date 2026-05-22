import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_runtime_progress_applications import api_readonly_fixture


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


def prepare_runtime_guardrail(repository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    runtime_guardrail = fixture.runtime_guardrail
    assert runtime_guardrail is not None
    return runtime_guardrail


def test_runtime_progress_application_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    runtime_guardrail = prepare_runtime_guardrail(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application")
    build = owner.post(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application/build"
    )
    loaded = owner.get(f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application")
    application_id = build.json()["application_id"]
    by_id = owner.get(f"/api/simulado-progress-application/{application_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_runtime_guardrail_id"] == runtime_guardrail.runtime_guardrail_id
    assert loaded.json()["application_mode"] in {"dry_run", "planned_only"}
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
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-progress-application/{application_id}").status_code == 401


def test_runtime_progress_application_build_is_deterministic_for_same_source(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    runtime_guardrail = prepare_runtime_guardrail(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application/build"
    )
    second = owner.post(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application/build"
    )
    listed = repository.list_user_simulado_runtime_progress_applications(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_runtime_progress_application(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    runtime_guardrail = prepare_runtime_guardrail(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application/build"
    )
    assert build.status_code == 200
    application_id = build.json()["application_id"]

    assert other.post(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application"
    ).status_code == 404
    assert other.get(f"/api/simulado-progress-application/{application_id}").status_code == 404


def test_get_runtime_progress_application_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    runtime_guardrail = prepare_runtime_guardrail(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application")
    before_runtime_guardrail = repository.get_simulado_runtime_guardrail_by_id(
        runtime_guardrail.runtime_guardrail_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application/build"
    )
    loaded = owner.get(f"/api/simulado-runtime-guardrail/{runtime_guardrail.runtime_guardrail_id}/progress-application")
    after_runtime_guardrail = repository.get_simulado_runtime_guardrail_by_id(
        runtime_guardrail.runtime_guardrail_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before_runtime_guardrail is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after_runtime_guardrail is not None
    assert before_runtime_guardrail.model_dump(mode="json") == after_runtime_guardrail.model_dump(mode="json")
