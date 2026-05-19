import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_finalization_guardrails import (
    build_finalization_guardrail,
    non_final_assembly_fixture,
    ready_candidates_not_finalizable_fixture,
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


def prepare_finalization_guardrail(repository, tmp_path, user_id: str):
    fixture = ready_candidates_not_finalizable_fixture(tmp_path, user_id=user_id, repository=repository)
    guardrail = build_finalization_guardrail(fixture)
    assert guardrail is not None
    return guardrail


def test_simulado_final_approval_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    guardrail = prepare_finalization_guardrail(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-finalization-guardrail/{guardrail.finalization_guardrail_id}/final-approval")
    build = owner.post(
        f"/api/simulado-finalization-guardrail/{guardrail.finalization_guardrail_id}/final-approval/build",
        json={
            "decisions": [
                {
                    "source_candidate_id": guardrail.candidate_summaries[0].source_question_candidate_id,
                    "decision_type": "approve_for_future_execution_review",
                    "reason": "Approved for future execution review only.",
                }
            ]
        },
    )
    loaded = owner.get(f"/api/simulado-finalization-guardrail/{guardrail.finalization_guardrail_id}/final-approval")
    approval_artifact_id = build.json()["approval_artifact_id"]
    by_id = owner.get(f"/api/simulado-final-approval/{approval_artifact_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_finalization_guardrail_id"] == guardrail.finalization_guardrail_id
    assert loaded.json()["execution_enabled"] is False
    assert loaded.json()["human_approved"] is True
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(
        f"/api/simulado-finalization-guardrail/{guardrail.finalization_guardrail_id}/final-approval/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-finalization-guardrail/{guardrail.finalization_guardrail_id}/final-approval"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-final-approval/{approval_artifact_id}").status_code == 401


def test_simulado_final_approval_build_is_deterministic_for_same_decision_payload(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    guardrail = prepare_finalization_guardrail(repository, tmp_path / "owner", owner_user_id)

    payload = {
        "decisions": [
            {
                "source_candidate_id": guardrail.candidate_summaries[0].source_question_candidate_id,
                "decision_type": "mark_not_reviewed",
                "reason": "Still pending manual review.",
            }
        ]
    }
    first = owner.post(
        f"/api/simulado-finalization-guardrail/{guardrail.finalization_guardrail_id}/final-approval/build",
        json=payload,
    )
    second = owner.post(
        f"/api/simulado-finalization-guardrail/{guardrail.finalization_guardrail_id}/final-approval/build",
        json=payload,
    )
    listed = repository.list_user_simulado_final_approval_artifacts(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_simulado_final_approval_artifact(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    guardrail = prepare_finalization_guardrail(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(
        f"/api/simulado-finalization-guardrail/{guardrail.finalization_guardrail_id}/final-approval/build",
        json={
            "decisions": [
                {
                    "source_candidate_id": guardrail.candidate_summaries[0].source_question_candidate_id,
                    "decision_type": "approve_for_future_execution_review",
                    "reason": "Owner-only approval record.",
                }
            ]
        },
    )
    assert build.status_code == 200
    approval_artifact_id = build.json()["approval_artifact_id"]

    assert other.post(
        f"/api/simulado-finalization-guardrail/{guardrail.finalization_guardrail_id}/final-approval/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-finalization-guardrail/{guardrail.finalization_guardrail_id}/final-approval"
    ).status_code == 404
    assert other.get(f"/api/simulado-final-approval/{approval_artifact_id}").status_code == 404

