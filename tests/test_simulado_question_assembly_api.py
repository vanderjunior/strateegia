import json

from fastapi.testclient import TestClient

from app.domain.models import SimuladoBlueprint, SimuladoBlueprintRationale, SimuladoQuestionSlot
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.answer_explanation_guardrails import AnswerExplanationGuardrailService
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


def prepare_simulado_chain(repository, tmp_path, user_id: str) -> str:
    fixture = ready_cebraspe_assertion_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    slot_blueprint = fixture.blueprint_set.slot_blueprints[0]
    repository.save_simulado_blueprint(
        SimuladoBlueprint(
            blueprint_id=fixture.blueprint_set.source_simulado_blueprint_id,
            graph_id=f"graph:{fixture.blueprint_set.source_simulado_blueprint_id}",
            cycle_id=f"cycle:{fixture.blueprint_set.source_simulado_blueprint_id}",
            exam_profile_id=f"exam-profile:{slot_blueprint.board_id or 'unknown'}",
            user_id=user_id,
            exam_board=slot_blueprint.board_id,
            exam_family=slot_blueprint.exam_family,
            format_type=slot_blueprint.format_type,
            question_slots=[
                SimuladoQuestionSlot(
                    slot_id=slot_blueprint.source_question_slot_id,
                    section_id="section:primary",
                    order_index=0,
                    target_subject_id=slot_blueprint.target_subject_id,
                    target_topic_id=slot_blueprint.target_topic_id,
                    target_subtopic_ids=list(slot_blueprint.target_subtopic_ids),
                    format_type=slot_blueprint.format_type,
                    cognitive_demand=slot_blueprint.cognitive_demand,
                    difficulty_hint=slot_blueprint.difficulty_hint,
                    generation_style=slot_blueprint.question_kind,
                    source_evidence_ids=[item.evidence_id for item in slot_blueprint.source_evidence],
                    required_coverage_state="covered",
                    readiness_state="ready_for_review",
                    confidence=0.8,
                    reasoning="fixture simulado question slot",
                )
            ],
            rationale=SimuladoBlueprintRationale(
                summary="fixture simulado blueprint for question assembly API",
                source_graph_id=f"graph:{fixture.blueprint_set.source_simulado_blueprint_id}",
                source_cycle_id=f"cycle:{fixture.blueprint_set.source_simulado_blueprint_id}",
                source_exam_profile_id=f"exam-profile:{slot_blueprint.board_id or 'unknown'}",
                confidence=0.8,
            ),
            metadata={"fixture": True},
        ),
        user_id=user_id,
    )
    draft_set = fixture.context.service.build_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=user_id,
    )
    AnswerExplanationGuardrailService(repository).build_guardrail(
        draft_set.drafts[0].draft_id,
        user_id=user_id,
    )
    return fixture.blueprint_set.source_simulado_blueprint_id


def test_simulado_question_assembly_endpoints_work_for_owner_and_are_json_safe(tmp_path):
    owner, _, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    blueprint_id = prepare_simulado_chain(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-blueprint/{blueprint_id}/question-assembly")
    build = owner.post(f"/api/simulado-blueprint/{blueprint_id}/question-assembly/build")
    loaded = owner.get(f"/api/simulado-blueprint/{blueprint_id}/question-assembly")
    assembly_id = build.json()["assembly_id"]
    by_id = owner.get(f"/api/simulado-question-assembly/{assembly_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json()["source_simulado_blueprint_id"] == blueprint_id
    assert loaded.json()["not_executable"] is True
    dumped = json.dumps(by_id.json(), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped
    assert anonymous.post(f"/api/simulado-blueprint/{blueprint_id}/question-assembly/build").status_code == 401
    assert anonymous.get(f"/api/simulado-blueprint/{blueprint_id}/question-assembly").status_code == 401
    assert anonymous.get(f"/api/simulado-question-assembly/{assembly_id}").status_code == 401


def test_simulado_question_assembly_build_is_deterministic_and_does_not_duplicate(tmp_path):
    owner, _, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    blueprint_id = prepare_simulado_chain(repository, tmp_path / "owner", owner_user_id)

    first = owner.post(f"/api/simulado-blueprint/{blueprint_id}/question-assembly/build")
    second = owner.post(f"/api/simulado-blueprint/{blueprint_id}/question-assembly/build")
    listed = repository.list_user_simulado_question_assemblies(user_id=owner_user_id)

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json() == second.json()
    assert len(listed) == 1


def test_non_owner_cannot_access_other_user_simulado_question_assembly(tmp_path):
    owner, other, _, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    blueprint_id = prepare_simulado_chain(repository, tmp_path / "owner", owner_user_id)
    build = owner.post(f"/api/simulado-blueprint/{blueprint_id}/question-assembly/build")
    assert build.status_code == 200
    assembly_id = build.json()["assembly_id"]

    assert other.post(f"/api/simulado-blueprint/{blueprint_id}/question-assembly/build").status_code == 404
    assert other.get(f"/api/simulado-blueprint/{blueprint_id}/question-assembly").status_code == 404
    assert other.get(f"/api/simulado-question-assembly/{assembly_id}").status_code == 404
