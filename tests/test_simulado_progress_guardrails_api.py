import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_progress_guardrails import api_readonly_fixture


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


def prepare_score_result(repository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    score_result = fixture.score_result
    assert score_result is not None
    return score_result


def test_simulado_progress_guardrail_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    score_result = prepare_score_result(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail")
    build = owner.post(f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail/build")
    loaded = owner.get(f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail")
    progress_guardrail_id = build.json()["progress_guardrail_id"]
    by_id = owner.get(f"/api/simulado-progress-guardrail/{progress_guardrail_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_score_result_id"] == score_result.score_result_id
    assert loaded.json()["progress_mutation_enabled"] is False
    assert loaded.json()["ranking_mutation_enabled"] is False
    assert loaded.json()["retention_mutation_enabled"] is False
    assert loaded.json()["scheduler_mutation_enabled"] is False
    assert loaded.json()["study_cycle_mutation_enabled"] is False
    assert loaded.json()["curriculum_graph_mutation_enabled"] is False
    assert loaded.json()["adaptive_tuning_enabled"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-progress-guardrail/{progress_guardrail_id}").status_code == 401


def test_simulado_progress_guardrail_build_is_deterministic_for_same_source(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    score_result = prepare_score_result(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail/build"
    )
    second = owner.post(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail/build"
    )
    listed = repository.list_user_simulado_progress_guardrails(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_progress_guardrail(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    score_result = prepare_score_result(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail/build"
    )
    assert build.status_code == 200
    progress_guardrail_id = build.json()["progress_guardrail_id"]

    assert other.post(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail"
    ).status_code == 404
    assert other.get(f"/api/simulado-progress-guardrail/{progress_guardrail_id}").status_code == 404


def test_get_progress_guardrail_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    score_result = prepare_score_result(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail")
    before = repository.get_simulado_score_result_by_id(
        score_result.score_result_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail/build"
    )
    loaded = owner.get(f"/api/simulado-score-result/{score_result.score_result_id}/progress-guardrail")
    after = repository.get_simulado_score_result_by_id(
        score_result.score_result_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after is not None
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
