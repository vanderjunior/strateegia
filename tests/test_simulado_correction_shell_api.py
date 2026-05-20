import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_answer_submission import SimuladoAnswerSubmissionService
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
    login = client.post(
        "/api/auth/login",
        json={"username": username, "password": "senha-segura-123"},
    )
    assert login.status_code == 200
    return login.json()["user"]["user_id"]


def prepare_answer_submission(repository, tmp_path, user_id: str):
    fixture = selected_option_submission_fixture(tmp_path, user_id=user_id, repository=repository)
    submission = build_answer_submission(fixture)
    assert submission is not None
    return submission


def test_simulado_correction_shell_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    submission = prepare_answer_submission(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-answer-submission/{submission.answer_submission_id}/correction-shell")
    build = owner.post(
        f"/api/simulado-answer-submission/{submission.answer_submission_id}/correction-shell/build"
    )
    loaded = owner.get(f"/api/simulado-answer-submission/{submission.answer_submission_id}/correction-shell")
    correction_shell_id = build.json()["correction_shell_id"]
    by_id = owner.get(f"/api/simulado-correction-shell/{correction_shell_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_answer_submission_id"] == submission.answer_submission_id
    assert loaded.json()["correction_enabled"] is False
    assert loaded.json()["scoring_enabled"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-answer-submission/{submission.answer_submission_id}/correction-shell/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-answer-submission/{submission.answer_submission_id}/correction-shell"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-correction-shell/{correction_shell_id}").status_code == 401


def test_simulado_correction_shell_build_is_deterministic_and_read_only(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    submission = prepare_answer_submission(repository, tmp_path / "owner", owner_user_id)

    before_submission = repository.get_simulado_answer_submission_by_id(
        submission.answer_submission_id,
        user_id=owner_user_id,
    )
    before_attempt_session = repository.get_simulado_attempt_session_by_id(
        submission.source_attempt_session_id,
        user_id=owner_user_id,
    )

    first = owner.post(
        f"/api/simulado-answer-submission/{submission.answer_submission_id}/correction-shell/build"
    )
    second = owner.post(
        f"/api/simulado-answer-submission/{submission.answer_submission_id}/correction-shell/build"
    )
    loaded = owner.get(f"/api/simulado-answer-submission/{submission.answer_submission_id}/correction-shell")
    listed = repository.list_user_simulado_correction_shells(user_id=owner_user_id)

    after_submission = repository.get_simulado_answer_submission_by_id(
        submission.answer_submission_id,
        user_id=owner_user_id,
    )
    after_attempt_session = repository.get_simulado_attempt_session_by_id(
        submission.source_attempt_session_id,
        user_id=owner_user_id,
    )

    assert before_submission is not None
    assert before_attempt_session is not None
    assert first.status_code == 200
    assert second.status_code == 200
    assert loaded.status_code == 200
    assert first.json() == second.json() == loaded.json()
    assert len(listed) == 1
    assert after_submission is not None
    assert after_attempt_session is not None
    assert before_submission.model_dump(mode="json") == after_submission.model_dump(mode="json")
    assert before_attempt_session.model_dump(mode="json") == after_attempt_session.model_dump(mode="json")


def test_non_owner_cannot_access_other_user_simulado_correction_shell(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    submission = prepare_answer_submission(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-answer-submission/{submission.answer_submission_id}/correction-shell/build"
    )
    assert build.status_code == 200
    correction_shell_id = build.json()["correction_shell_id"]

    assert other.post(
        f"/api/simulado-answer-submission/{submission.answer_submission_id}/correction-shell/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-answer-submission/{submission.answer_submission_id}/correction-shell"
    ).status_code == 404
    assert other.get(f"/api/simulado-correction-shell/{correction_shell_id}").status_code == 404
