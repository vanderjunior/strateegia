import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_application_guardrails import (
    SimuladoRuntimeApplicationGuardrailsService,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_application_guardrails import (
    affected_runtime_surface_shape_fixture,
    api_readonly_fixture,
    build_runtime_guardrail,
    candidate_mutation_intent_shape_fixture,
    idempotency_fixture,
    incomplete_integrated_chain_fixture,
    incomplete_score_fixture,
    missing_integrated_result_fixture,
    missing_progress_guardrail_fixture,
    missing_runtime_policy_fixture,
    missing_score_result_fixture,
    mixed_runtime_guardrail_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    progress_guardrail_not_eligible_fixture,
    runtime_mutation_disabled_fixture,
    safety_assessment_fixture,
)


FORBIDDEN_RUNTIME_KEYS = {
    "password_hash",
    "studyflow_session",
    "correct_answer",
    "correct_option",
    "answer_key",
    "answer_key_value",
    "final_answer_key",
    "final_answer_key_content",
    "gabarito",
    "gabarito_final",
    "correctness",
    "is_correct",
    "raw_runtime_block",
    "final_question_content",
    "final_explanation_content",
    "runtime_application_event",
    "final_pedagogical_update_event",
    "application_completed",
}

ALLOWED_INTENT_TYPES = {
    "progress_update_candidate",
    "ranking_update_candidate",
    "retention_update_candidate",
    "scheduler_update_candidate",
    "study_cycle_update_candidate",
    "curriculum_graph_update_candidate",
    "unknown",
}

ALLOWED_SURFACES = {
    "progress",
    "ranking",
    "retention",
    "scheduler",
    "study_cycle",
    "curriculum_graph",
    "adaptive_tuning",
    "unknown",
}


def _create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def _register_and_login(client: TestClient, username: str) -> str:
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


def test_runtime_guardrail_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    fixtures = [
        missing_integrated_result_fixture(tmp_path / "missing"),
        incomplete_integrated_chain_fixture(tmp_path / "incomplete"),
        missing_score_result_fixture(tmp_path / "missing-score"),
        incomplete_score_fixture(tmp_path / "incomplete-score"),
        missing_progress_guardrail_fixture(tmp_path / "missing-guardrail"),
        progress_guardrail_not_eligible_fixture(tmp_path / "not-eligible"),
        missing_runtime_policy_fixture(tmp_path / "missing-policy"),
        runtime_mutation_disabled_fixture(tmp_path / "runtime-disabled"),
        mixed_runtime_guardrail_fixture(tmp_path / "mixed"),
    ]

    results = [build_runtime_guardrail(fixture) for fixture in fixtures]
    assert results[0] is None
    for result in results[1:]:
        assert result is not None
        dumped = result.model_dump(mode="json")
        dumped_text = json.dumps(dumped, ensure_ascii=True)
        assert dumped["metadata"]["build_method"] == "heuristic_simulado_runtime_application_guardrail_builder"
        assert dumped["metadata"]["llm_used"] is False
        assert dumped["metadata"]["external_calls_used"] is False
        assert "data:image" not in dumped_text
        assert "http://" not in dumped_text
        assert "https://" not in dumped_text
        assert "/Users/" not in dumped_text
        assert "/private/" not in dumped_text


def test_runtime_guardrail_stabilization_covers_missing_and_incomplete_inputs(tmp_path):
    missing = missing_integrated_result_fixture(tmp_path / "missing")
    incomplete = build_runtime_guardrail(incomplete_integrated_chain_fixture(tmp_path / "incomplete"))
    missing_score = build_runtime_guardrail(missing_score_result_fixture(tmp_path / "missing-score"))
    incomplete_score = build_runtime_guardrail(incomplete_score_fixture(tmp_path / "incomplete-score"))
    missing_guardrail = build_runtime_guardrail(missing_progress_guardrail_fixture(tmp_path / "missing-guardrail"))
    not_eligible = build_runtime_guardrail(progress_guardrail_not_eligible_fixture(tmp_path / "not-eligible"))
    missing_policy = build_runtime_guardrail(missing_runtime_policy_fixture(tmp_path / "missing-policy"))

    assert build_runtime_guardrail(missing) is None

    assert incomplete is not None
    assert incomplete.status == "runtime_application_guardrail_blocked"
    assert incomplete.readiness_state == "blocked_by_incomplete_integrated_chain"
    assert incomplete.eligibility.eligible_for_future_runtime_application is False
    assert "blocked_by_incomplete_integrated_chain" in {item.code for item in incomplete.blockers}

    assert missing_score is not None
    assert "blocked_by_missing_score_result" in {item.code for item in missing_score.blockers}

    assert incomplete_score is not None
    assert incomplete_score.safety_assessment.score_complete is False
    assert "blocked_by_incomplete_score" in {item.code for item in incomplete_score.blockers}

    assert missing_guardrail is not None
    assert missing_guardrail.safety_assessment.progress_guardrail_present is False
    assert "blocked_by_missing_progress_guardrail" in {item.code for item in missing_guardrail.blockers}

    assert not_eligible is not None
    assert not_eligible.safety_assessment.progress_guardrail_eligible is False
    assert "blocked_by_progress_guardrail_not_eligible" in {item.code for item in not_eligible.blockers}

    assert missing_policy is not None
    assert missing_policy.safety_assessment.runtime_policy_available is False
    assert "blocked_by_runtime_policy_missing" in {item.code for item in missing_policy.blockers}


def test_runtime_guardrail_stabilization_covers_disabled_mutation_flags_and_no_application(tmp_path):
    runtime_disabled = build_runtime_guardrail(runtime_mutation_disabled_fixture(tmp_path / "runtime-disabled"))
    no_application = build_runtime_guardrail(no_runtime_application_fixture(tmp_path / "no-application"))

    assert runtime_disabled is not None
    assert "blocked_by_runtime_mutation_disabled" in {item.code for item in runtime_disabled.blockers}
    assert runtime_disabled.runtime_application_enabled is False
    assert runtime_disabled.runtime_application_applied is False
    assert runtime_disabled.progress_mutation_enabled is False
    assert runtime_disabled.progress_mutation_applied is False
    assert runtime_disabled.ranking_update_enabled is False
    assert runtime_disabled.ranking_update_applied is False
    assert runtime_disabled.retention_update_enabled is False
    assert runtime_disabled.retention_update_applied is False
    assert runtime_disabled.scheduler_update_enabled is False
    assert runtime_disabled.scheduler_update_applied is False
    assert runtime_disabled.study_cycle_update_enabled is False
    assert runtime_disabled.study_cycle_update_applied is False
    assert runtime_disabled.curriculum_graph_update_enabled is False
    assert runtime_disabled.curriculum_graph_update_applied is False
    assert runtime_disabled.adaptive_tuning_enabled is False
    assert runtime_disabled.adaptive_tuning_applied is False
    assert runtime_disabled.no_runtime_application is True
    assert runtime_disabled.no_progress_mutation is True
    assert runtime_disabled.no_ranking_update is True
    assert runtime_disabled.no_retention_update is True
    assert runtime_disabled.no_scheduler_update is True
    assert runtime_disabled.no_study_cycle_update is True
    assert runtime_disabled.no_curriculum_graph_update is True
    assert runtime_disabled.no_adaptive_tuning_update is True

    assert no_application is not None
    assert no_application.runtime_application_enabled is False
    assert no_application.runtime_application_applied is False
    assert no_application.no_runtime_application is True


def test_runtime_guardrail_stabilization_preserves_candidate_intent_and_surface_shapes(tmp_path):
    intents = build_runtime_guardrail(candidate_mutation_intent_shape_fixture(tmp_path / "intents"))
    surfaces = build_runtime_guardrail(affected_runtime_surface_shape_fixture(tmp_path / "surfaces"))

    assert intents is not None
    assert intents.candidate_mutation_intents
    for item in intents.candidate_mutation_intents:
        assert item.intent_type in ALLOWED_INTENT_TYPES
        assert item.proposed_surface in ALLOWED_SURFACES
        assert item.future_application_allowed is False
        assert item.application_applied is False
        assert all(code in {
            "intent_blocked_by_incomplete_chain",
            "intent_blocked_by_incomplete_score",
            "intent_blocked_by_missing_progress_target",
            "intent_blocked_by_runtime_policy_missing",
            "intent_blocked_by_runtime_mutation_disabled",
        } for code in item.blockers)

    assert surfaces is not None
    assert surfaces.affected_runtime_surfaces
    for surface in surfaces.affected_runtime_surfaces:
        assert surface.surface_type in ALLOWED_SURFACES
        assert surface.update_applied is False
        assert surface.future_update_allowed is False


def test_runtime_guardrail_stabilization_preserves_safety_assessment_and_mixed_blockers(tmp_path):
    safety = build_runtime_guardrail(safety_assessment_fixture(tmp_path / "safety"))
    mixed = build_runtime_guardrail(mixed_runtime_guardrail_fixture(tmp_path / "mixed"))

    assert safety is not None
    assert safety.safety_assessment.integrated_chain_complete is True
    assert safety.safety_assessment.score_result_present is True
    assert safety.safety_assessment.score_complete in {False, True}
    assert safety.safety_assessment.progress_guardrail_present is True
    assert safety.safety_assessment.progress_guardrail_eligible in {False, True}
    assert safety.safety_assessment.runtime_policy_available is False
    assert safety.safety_assessment.public_answer_key_exposure_detected is False
    assert safety.safety_assessment.public_gabarito_exposure_detected is False
    assert safety.safety_assessment.enough_data_for_future_application is False

    assert mixed is not None
    blocker_codes = {item.code for item in mixed.blockers}
    assert "blocked_by_runtime_policy_missing" in blocker_codes
    assert "blocked_by_runtime_mutation_disabled" in blocker_codes
    assert len(mixed.warnings) >= 1


def test_runtime_guardrail_stabilization_preserves_no_public_answer_key_and_no_leakage(tmp_path):
    result = build_runtime_guardrail(no_public_key_gabarito_safety_fixture(tmp_path))
    assert result is not None

    dumped_payload = result.model_dump(mode="json")
    dumped_text = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)

    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False
    for key in FORBIDDEN_RUNTIME_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "studyflow_session" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text
    assert "data:image" not in dumped_text
    assert "raw_runtime_block" not in dumped_text


def test_runtime_guardrail_stabilization_is_persistent_idempotent_and_non_mutating(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    repository = fixture.context.repository
    service = SimuladoRuntimeApplicationGuardrailsService(repository)
    result = build_runtime_guardrail(fixture)
    assert result is not None
    integrated_result = fixture.integrated_result
    assert integrated_result is not None

    before_integrated = repository.get_simulado_integrated_result_by_id(
        integrated_result.integrated_result_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_runtime_guardrail(integrated_result.integrated_result_id, user_id=fixture.context.user_id)
    second = service.build_runtime_guardrail(integrated_result.integrated_result_id, user_id=fixture.context.user_id)
    by_source = repository.get_simulado_runtime_guardrail(
        integrated_result.integrated_result_id,
        user_id=fixture.context.user_id,
    )
    by_id = repository.get_simulado_runtime_guardrail_by_id(
        result.runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    listed = repository.list_user_simulado_runtime_guardrails(user_id=fixture.context.user_id)

    after_integrated = repository.get_simulado_integrated_result_by_id(
        integrated_result.integrated_result_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)

    assert first is not None
    assert second is not None
    assert by_source is not None
    assert by_id is not None
    assert len(listed) == 1
    assert result.model_dump(mode="json") == first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source.model_dump(mode="json") == result.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == result.model_dump(mode="json")
    assert before_integrated is not None and after_integrated is not None
    assert before_integrated.model_dump(mode="json") == after_integrated.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")


def test_runtime_guardrail_stabilization_api_owner_only_and_read_only_behaviour(tmp_path):
    owner_client, other_client, anonymous_client, repository = _create_clients(tmp_path)
    owner_user_id = _register_and_login(owner_client, "owner")
    _register_and_login(other_client, "other")

    owner_fixture = api_readonly_fixture(tmp_path / "owner-fixture", user_id=owner_user_id, repository=repository)
    integrated_result = owner_fixture.integrated_result
    assert integrated_result is not None

    missing_get = owner_client.get(
        f"/api/simulado-integrated-result/{integrated_result.integrated_result_id}/runtime-guardrail"
    )
    before = repository.get_simulado_integrated_result_by_id(
        integrated_result.integrated_result_id,
        user_id=owner_user_id,
    )
    build = owner_client.post(
        f"/api/simulado-integrated-result/{integrated_result.integrated_result_id}/runtime-guardrail/build"
    )
    loaded = owner_client.get(
        f"/api/simulado-integrated-result/{integrated_result.integrated_result_id}/runtime-guardrail"
    )
    runtime_guardrail_id = build.json()["runtime_guardrail_id"]
    by_id = owner_client.get(f"/api/simulado-runtime-guardrail/{runtime_guardrail_id}")
    after = repository.get_simulado_integrated_result_by_id(
        integrated_result.integrated_result_id,
        user_id=owner_user_id,
    )

    assert missing_get.status_code == 404
    assert before is not None and after is not None
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
    assert anonymous_client.post(
        f"/api/simulado-integrated-result/{integrated_result.integrated_result_id}/runtime-guardrail/build"
    ).status_code == 401
    assert anonymous_client.get(
        f"/api/simulado-integrated-result/{integrated_result.integrated_result_id}/runtime-guardrail"
    ).status_code == 401
    assert other_client.post(
        f"/api/simulado-integrated-result/{integrated_result.integrated_result_id}/runtime-guardrail/build"
    ).status_code == 404
    assert other_client.get(
        f"/api/simulado-integrated-result/{integrated_result.integrated_result_id}/runtime-guardrail"
    ).status_code == 404
    assert other_client.get(f"/api/simulado-runtime-guardrail/{runtime_guardrail_id}").status_code == 404

