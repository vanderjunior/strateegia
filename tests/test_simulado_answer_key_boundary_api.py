import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_correction_shell import SimuladoCorrectionShellService
from tests.fixtures.simulado_answer_submissions import (
    build_answer_submission,
    selected_option_submission_fixture,
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


def prepare_correction_shell(repository, tmp_path, user_id: str):
    fixture = selected_option_submission_fixture(tmp_path, user_id=user_id, repository=repository)
    submission = build_answer_submission(fixture)
    assert submission is not None
    result = SimuladoCorrectionShellService(repository).build_correction_shell(
        submission.answer_submission_id,
        user_id=user_id,
    )
    assert result is not None
    return result


def test_simulado_answer_key_boundary_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    correction_shell = prepare_correction_shell(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary")
    build = owner.post(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary/build"
    )
    loaded = owner.get(f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary")
    boundary_id = build.json()["answer_key_boundary_id"]
    by_id = owner.get(f"/api/simulado-answer-key-boundary/{boundary_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_correction_shell_id"] == correction_shell.correction_shell_id
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-answer-key-boundary/{boundary_id}").status_code == 401


def test_simulado_answer_key_boundary_build_is_deterministic_for_same_source(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    correction_shell = prepare_correction_shell(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary/build"
    )
    second = owner.post(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary/build"
    )
    listed = repository.list_user_simulado_answer_key_boundaries(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_simulado_answer_key_boundary(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    correction_shell = prepare_correction_shell(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary/build"
    )
    assert build.status_code == 200
    boundary_id = build.json()["answer_key_boundary_id"]

    assert other.post(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary"
    ).status_code == 404
    assert other.get(f"/api/simulado-answer-key-boundary/{boundary_id}").status_code == 404


def test_get_answer_key_boundary_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    correction_shell = prepare_correction_shell(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary")
    before = repository.get_simulado_correction_shell_by_id(
        correction_shell.correction_shell_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary/build"
    )
    loaded = owner.get(f"/api/simulado-correction-shell/{correction_shell.correction_shell_id}/answer-key-boundary")
    after = repository.get_simulado_correction_shell_by_id(
        correction_shell.correction_shell_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after is not None
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
