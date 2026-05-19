import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_question_assembly import (
    MAX_DRAFT_COMMAND_PREVIEW_LENGTH,
    MAX_DRAFT_STEM_PREVIEW_LENGTH,
    MAX_SAFE_SNIPPET_LENGTH,
)
from tests.fixtures.simulado_question_assemblies import (
    ambiguous_source_candidate_fixture,
    assembly_json_keys,
    blocked_guardrail_candidate_fixture,
    bounded_summary_fixture,
    build_assembly,
    idempotency_fixture,
    material_gap_candidate_fixture,
    missing_draft_candidate_fixture,
    missing_guardrail_candidate_fixture,
    missing_source_candidate_fixture,
    mixed_assembly_fixture,
    no_candidates_fixture,
    no_final_content_safety_fixture,
    non_reviewed_draft_candidate_fixture,
    ocr_blocked_candidate_fixture,
    ready_for_review_candidate_fixture,
    unsupported_format_candidate_fixture,
    user_scope_fixture,
)


FORBIDDEN_EXECUTION_KEYS = {
    "final_question",
    "executable_question",
    "final_answer_key",
    "correct_option",
    "correct_answer",
    "gabarito",
    "gabarito_final",
    "final_explanation",
    "correction_rule",
    "auto_correction",
    "score_rule",
    "scoring_result",
    "student_attempt",
    "answer_submission",
    "simulado_result",
    "executable_simulado",
    "exam_session",
    "attempt_id",
    "submission_id",
    "score",
    "grade",
}


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


def assert_no_leakage(serialized: str) -> None:
    assert "password_hash" not in serialized
    assert "studyflow_session" not in serialized
    assert "/Users/" not in serialized
    assert "/private/" not in serialized
    assert "/uploads/" not in serialized
    assert "data:image" not in serialized
    assert "raw_runtime_block" not in serialized


def test_simulado_question_assembly_fixtures_are_deterministic_and_json_safe(tmp_path):
    first = ready_for_review_candidate_fixture(tmp_path / "first")
    second = ready_for_review_candidate_fixture(tmp_path / "second")

    assert first.blueprint_set.blueprint_set_id == second.blueprint_set.blueprint_set_id
    assert first.simulado_blueprint.blueprint_id == second.simulado_blueprint.blueprint_id
    assert first.draft_set is not None
    assert second.draft_set is not None
    assert first.draft_set.draft_set_id == second.draft_set.draft_set_id
    json.dumps(first.simulado_blueprint.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(build_assembly(first).model_dump(mode="json"), ensure_ascii=True)


def test_ready_missing_and_blocked_candidate_fixtures_cover_expected_states(tmp_path):
    ready = build_assembly(ready_for_review_candidate_fixture(tmp_path / "ready"))
    missing_draft = build_assembly(missing_draft_candidate_fixture(tmp_path / "missing-draft"))
    missing_guardrail = build_assembly(missing_guardrail_candidate_fixture(tmp_path / "missing-guardrail"))
    blocked_guardrail = build_assembly(blocked_guardrail_candidate_fixture(tmp_path / "blocked-guardrail"))
    non_reviewed = build_assembly(non_reviewed_draft_candidate_fixture(tmp_path / "non-reviewed"))

    assert ready is not None
    assert ready.candidates[0].readiness_state == "candidate_ready_for_review"
    assert ready.candidates[0].source_question_draft_id is not None
    assert ready.candidates[0].source_guardrail_id is not None
    assert ready.candidates[0].source_evidence_summary.primary_source_available is True
    assert ready.candidates[0].requires_human_review is True
    assert ready.candidates[0].not_executable is True
    assert ready.candidates[0].not_scoreable is True

    assert missing_draft is not None
    assert missing_draft.candidates[0].readiness_state == "candidate_blocked_by_missing_draft"
    assert missing_draft.ready_for_review_count == 0

    assert missing_guardrail is not None
    assert missing_guardrail.candidates[0].readiness_state == "candidate_blocked_by_missing_guardrail"
    assert missing_guardrail.ready_for_review_count == 0

    assert blocked_guardrail is not None
    assert blocked_guardrail.candidates[0].readiness_state == "candidate_blocked_by_unfinalized_answer"
    assert blocked_guardrail.candidates[0].guardrail_summary.no_final_answer_key_generated is True
    assert blocked_guardrail.candidates[0].guardrail_summary.no_final_explanation_generated is True

    assert non_reviewed is not None
    assert non_reviewed.candidates[0].readiness_state == "candidate_blocked_by_non_reviewed_draft"


def test_ocr_material_source_and_unsupported_fixtures_preserve_blockers(tmp_path):
    unsupported = build_assembly(unsupported_format_candidate_fixture(tmp_path / "unsupported"))
    ocr = build_assembly(ocr_blocked_candidate_fixture(tmp_path / "ocr"))
    material = build_assembly(material_gap_candidate_fixture(tmp_path / "material"))
    ambiguous = build_assembly(ambiguous_source_candidate_fixture(tmp_path / "ambiguous"))
    missing_source = build_assembly(missing_source_candidate_fixture(tmp_path / "missing-source"))

    assert unsupported is not None
    assert unsupported.candidates[0].readiness_state == "candidate_blocked_by_unsupported_format"

    assert ocr is not None
    assert ocr.candidates[0].readiness_state == "candidate_blocked_by_ocr"
    assert ocr.candidates[0].not_executable is True
    assert ocr.candidates[0].not_scoreable is True

    assert material is not None
    assert material.candidates[0].readiness_state == "candidate_blocked_by_material_gap"
    assert material.candidates[0].not_executable is True
    assert material.candidates[0].not_scoreable is True

    assert ambiguous is not None
    assert ambiguous.candidates[0].readiness_state in {
        "candidate_needs_review",
        "candidate_blocked_by_source_issue",
    }
    assert ambiguous.ready_for_review_count == 0

    assert missing_source is not None
    assert missing_source.candidates[0].readiness_state == "candidate_blocked_by_source_issue"
    assert missing_source.candidates[0].source_evidence_summary.missing_source is True


def test_mixed_assembly_and_no_candidates_fixtures_keep_counts_stable(tmp_path):
    mixed = build_assembly(mixed_assembly_fixture(tmp_path / "mixed"))
    no_candidates = build_assembly(no_candidates_fixture(tmp_path / "none"))

    assert mixed is not None
    states = [item.readiness_state for item in mixed.candidates]
    assert states.count("candidate_ready_for_review") == 1
    assert states.count("candidate_blocked_by_missing_draft") == 1
    assert states.count("candidate_blocked_by_missing_guardrail") == 1
    assert states.count("candidate_blocked_by_unfinalized_answer") == 1
    assert states.count("candidate_blocked_by_unsupported_format") == 1
    assert states.count("candidate_needs_review") == 1
    assert mixed.total_candidates == 6
    assert mixed.ready_for_review_count == 1
    assert mixed.blocked_count == 4
    assert mixed.needs_review_count == 1
    assert mixed.readiness_state in {"assembly_partially_blocked", "assembly_needs_review"}

    assert no_candidates is not None
    assert no_candidates.readiness_state == "assembly_no_candidates"
    assert no_candidates.total_candidates == 0
    assert no_candidates.candidates == []


def test_no_execution_no_scoring_and_bounded_summary_safeguards_hold(tmp_path):
    safety = build_assembly(no_final_content_safety_fixture(tmp_path / "safety"))
    bounded = build_assembly(bounded_summary_fixture(tmp_path / "bounded"))
    assert safety is not None
    assert bounded is not None

    dumped = safety.model_dump(mode="json")
    dumped_text = json.dumps(dumped, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped)
    candidate = bounded.candidates[0]

    assert safety.requires_human_review is True
    assert safety.not_executable is True
    assert safety.not_scoreable is True
    assert safety.no_student_attempts_enabled is True
    assert safety.no_progress_mutation is True
    assert safety.no_final_questions_created is True
    assert safety.no_final_answer_keys_created is True
    assert safety.no_final_explanations_created is True
    for key in FORBIDDEN_EXECUTION_KEYS:
        assert key not in dumped_keys

    assert candidate.draft_summary.draft_stem_preview is not None
    assert candidate.draft_summary.draft_command_preview is not None
    assert len(candidate.draft_summary.draft_stem_preview) <= MAX_DRAFT_STEM_PREVIEW_LENGTH
    assert len(candidate.draft_summary.draft_command_preview) <= MAX_DRAFT_COMMAND_PREVIEW_LENGTH
    assert candidate.source_evidence_summary.safe_snippets
    assert all(len(item) <= MAX_SAFE_SNIPPET_LENGTH for item in candidate.source_evidence_summary.safe_snippets)
    assert candidate.source_evidence_summary.safe_snippets[0].endswith("…")
    assert_no_leakage(dumped_text)


def test_assembly_persistence_and_idempotency_are_stable(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    first = build_assembly(fixture)
    second = build_assembly(fixture)
    assert first is not None
    assert second is not None

    by_source = fixture.context.repository.get_simulado_question_assembly(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_question_assembly_by_id(
        first.assembly_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_question_assemblies(user_id=fixture.context.user_id)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1


def test_assembly_api_owner_only_read_only_and_user_scope_are_preserved(tmp_path):
    owner, other, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")

    owner_fixture, _ = user_scope_fixture(tmp_path / "scope", repository=repository)
    owner_fixture = ready_for_review_candidate_fixture(
        tmp_path / "owner-api",
        user_id=owner_user_id,
        repository=repository,
    )
    blueprint_id = owner_fixture.blueprint_set.source_simulado_blueprint_id

    missing = owner.get(f"/api/simulado-blueprint/{blueprint_id}/question-assembly")
    before_list = repository.list_user_simulado_question_assemblies(user_id=owner_user_id)
    build = owner.post(f"/api/simulado-blueprint/{blueprint_id}/question-assembly/build")
    assembly_id = build.json()["assembly_id"]
    after_build_list = repository.list_user_simulado_question_assemblies(user_id=owner_user_id)
    loaded = owner.get(f"/api/simulado-blueprint/{blueprint_id}/question-assembly")
    by_id = owner.get(f"/api/simulado-question-assembly/{assembly_id}")
    after_get_list = repository.list_user_simulado_question_assemblies(user_id=owner_user_id)
    dumped = json.dumps(by_id.json(), ensure_ascii=True)

    assert missing.status_code == 404
    assert before_list == []
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert len(after_build_list) == 1
    assert len(after_get_list) == 1
    assert loaded.json() == by_id.json()
    assert owner.post(f"/api/simulado-blueprint/{blueprint_id}/question-assembly/build").json() == build.json()
    assert anonymous.post(f"/api/simulado-blueprint/{blueprint_id}/question-assembly/build").status_code == 401
    assert anonymous.get(f"/api/simulado-blueprint/{blueprint_id}/question-assembly").status_code == 401
    assert anonymous.get(f"/api/simulado-question-assembly/{assembly_id}").status_code == 401
    assert other.post(f"/api/simulado-blueprint/{blueprint_id}/question-assembly/build").status_code == 404
    assert other.get(f"/api/simulado-blueprint/{blueprint_id}/question-assembly").status_code == 404
    assert other.get(f"/api/simulado-question-assembly/{assembly_id}").status_code == 404
    assert_no_leakage(dumped)


def test_assembly_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    fixture = ready_for_review_candidate_fixture(tmp_path)
    before_simulado = fixture.context.repository.get_simulado_blueprint_by_id(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    before_qgb = fixture.context.repository.get_question_generation_blueprint(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )
    assert fixture.draft_set is not None
    assert fixture.guardrails
    before_draft_set = fixture.context.repository.get_question_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )
    before_guardrail = fixture.context.repository.get_answer_explanation_guardrail(
        fixture.draft_set.drafts[0].draft_id,
        user_id=fixture.context.user_id,
    )

    built = build_assembly(fixture)
    assert built is not None
    loaded = fixture.context.assembly_service.get_assembly(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.assembly_service.get_assembly_by_id(
        built.assembly_id,
        user_id=fixture.context.user_id,
    )
    after_simulado = fixture.context.repository.get_simulado_blueprint_by_id(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    after_qgb = fixture.context.repository.get_question_generation_blueprint(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )
    after_draft_set = fixture.context.repository.get_question_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )
    after_guardrail = fixture.context.repository.get_answer_explanation_guardrail(
        fixture.draft_set.drafts[0].draft_id,
        user_id=fixture.context.user_id,
    )

    assert loaded is not None
    assert by_id is not None
    assert built.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_simulado is not None and after_simulado is not None
    assert before_qgb is not None and after_qgb is not None
    assert before_draft_set is not None and after_draft_set is not None
    assert before_guardrail is not None and after_guardrail is not None
    assert before_simulado.model_dump(mode="json") == after_simulado.model_dump(mode="json")
    assert before_qgb.model_dump(mode="json") == after_qgb.model_dump(mode="json")
    assert before_draft_set.model_dump(mode="json") == after_draft_set.model_dump(mode="json")
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
