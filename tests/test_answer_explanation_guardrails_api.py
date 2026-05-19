import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.question_drafts import ready_cebraspe_assertion_blueprint_fixture


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


def prepare_question_draft(repository, tmp_path, user_id: str) -> str:
    fixture = ready_cebraspe_assertion_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    draft_set = fixture.context.service.build_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=user_id,
    )
    return draft_set.drafts[0].draft_id


def test_answer_explanation_guardrail_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    draft_id = prepare_question_draft(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail")
    build = owner.post(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail/build")
    loaded = owner.get(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail")
    guardrail_id = build.json()["guardrail_id"]
    by_id = owner.get(f"/api/answer-explanation-guardrail/{guardrail_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_question_draft_id"] == draft_id
    assert loaded.json()["no_final_answer_key_generated"] is True
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail/build").status_code == 401
    assert anonymous.get(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail").status_code == 401
    assert anonymous.get(f"/api/answer-explanation-guardrail/{guardrail_id}").status_code == 401


def test_answer_explanation_guardrail_build_is_deterministic_and_does_not_duplicate(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    draft_id = prepare_question_draft(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail/build")
    second = owner.post(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail/build")
    listed = repository.list_user_answer_explanation_guardrails(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_answer_explanation_guardrail(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    draft_id = prepare_question_draft(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail/build")
    assert build.status_code == 200
    guardrail_id = build.json()["guardrail_id"]

    assert other.post(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail/build").status_code == 404
    assert other.get(f"/api/question-drafts/{draft_id}/answer-explanation-guardrail").status_code == 404
    assert other.get(f"/api/answer-explanation-guardrail/{guardrail_id}").status_code == 404
