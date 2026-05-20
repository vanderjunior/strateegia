import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_correction_results import build_correction_result
from tests.fixtures.simulado_scoring_results import api_readonly_fixture


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


def prepare_correction_result(repository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    correction_result = build_correction_result(fixture.correction_result_fixture)
    assert correction_result is not None
    return correction_result


def test_simulado_scoring_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    correction_result = prepare_correction_result(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score")
    build = owner.post(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score/build")
    loaded = owner.get(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score")
    score_result_id = build.json()["score_result_id"]
    by_id = owner.get(f"/api/simulado-score-result/{score_result_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_correction_result_id"] == correction_result.correction_result_id
    assert loaded.json()["progress_mutation_enabled"] is False
    assert loaded.json()["ranking_mutation_enabled"] is False
    assert loaded.json()["retention_mutation_enabled"] is False
    assert loaded.json()["scheduler_mutation_enabled"] is False
    assert loaded.json()["study_cycle_mutation_enabled"] is False
    assert loaded.json()["curriculum_graph_mutation_enabled"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-correction-result/{correction_result.correction_result_id}/score/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-correction-result/{correction_result.correction_result_id}/score"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-score-result/{score_result_id}").status_code == 401


def test_simulado_scoring_build_is_deterministic_for_same_source(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    correction_result = prepare_correction_result(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score/build")
    second = owner.post(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score/build")
    listed = repository.list_user_simulado_score_results(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_simulado_score_result(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    correction_result = prepare_correction_result(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score/build")
    assert build.status_code == 200
    score_result_id = build.json()["score_result_id"]

    assert other.post(
        f"/api/simulado-correction-result/{correction_result.correction_result_id}/score/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-correction-result/{correction_result.correction_result_id}/score"
    ).status_code == 404
    assert other.get(f"/api/simulado-score-result/{score_result_id}").status_code == 404


def test_get_score_result_is_read_only_and_missing_source_does_not_build(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    correction_result = prepare_correction_result(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score")
    before = repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=owner_user_id,
    )
    build = owner.post(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score/build")
    loaded = owner.get(f"/api/simulado-correction-result/{correction_result.correction_result_id}/score")
    after = repository.get_simulado_correction_result_by_id(
        correction_result.correction_result_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert before is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert after is not None
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
