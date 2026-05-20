import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_answer_key_boundary import SimuladoAnswerKeyBoundaryService
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


def prepare_answer_key_boundary(repository, tmp_path, user_id: str):
    fixture = selected_option_submission_fixture(tmp_path, user_id=user_id, repository=repository)
    submission = build_answer_submission(fixture)
    assert submission is not None
    correction_shell = SimuladoCorrectionShellService(repository).build_correction_shell(
        submission.answer_submission_id,
        user_id=user_id,
    )
    assert correction_shell is not None
    boundary = SimuladoAnswerKeyBoundaryService(repository).build_answer_key_boundary(
        correction_shell.correction_shell_id,
        user_id=user_id,
    )
    assert boundary is not None
    return boundary


def test_simulado_correction_result_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    boundary = prepare_answer_key_boundary(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result")
    build = owner.post(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result/build"
    )
    loaded = owner.get(f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result")
    correction_result_id = build.json()["correction_result_id"]
    by_id = owner.get(f"/api/simulado-correction-result/{correction_result_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_answer_key_boundary_id"] == boundary.answer_key_boundary_id
    assert loaded.json()["scoring_enabled"] is False
    assert loaded.json()["progress_mutation_enabled"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-correction-result/{correction_result_id}").status_code == 401


def test_simulado_correction_result_build_is_deterministic_for_same_source(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    boundary = prepare_answer_key_boundary(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result/build"
    )
    second = owner.post(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result/build"
    )
    listed = repository.list_user_simulado_correction_results(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_simulado_correction_result(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    boundary = prepare_answer_key_boundary(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result/build"
    )
    assert build.status_code == 200
    correction_result_id = build.json()["correction_result_id"]

    assert other.post(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result"
    ).status_code == 404
    assert other.get(f"/api/simulado-correction-result/{correction_result_id}").status_code == 404


def test_get_correction_result_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    boundary = prepare_answer_key_boundary(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result")
    before = repository.get_simulado_answer_key_boundary_by_id(
        boundary.answer_key_boundary_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result/build"
    )
    loaded = owner.get(f"/api/simulado-answer-key-boundary/{boundary.answer_key_boundary_id}/correction-result")
    after = repository.get_simulado_answer_key_boundary_by_id(
        boundary.answer_key_boundary_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after is not None
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
