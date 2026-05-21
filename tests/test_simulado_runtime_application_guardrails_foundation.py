import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_application_guardrails import (
    SimuladoRuntimeApplicationGuardrailsService,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_application_guardrails import (
    affected_runtime_surfaces_fixture,
    build_runtime_guardrail,
    candidate_mutation_intents_fixture,
    idempotency_fixture,
    incomplete_correction_fixture,
    incomplete_integrated_chain_fixture,
    incomplete_score_fixture,
    missing_integrated_result_fixture,
    missing_progress_guardrail_fixture,
    missing_runtime_policy_fixture,
    missing_score_result_fixture,
    mixed_runtime_guardrail_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture,
    progress_guardrail_not_eligible_fixture,
    runtime_mutation_disabled_fixture,
    safety_assessment_fixture,
)


FORBIDDEN_RUNTIME_GUARDRAIL_KEYS = {
    "correct_answer",
    "correct_option",
    "answer_key",
    "answer_key_value",
    "final_answer_key_content",
    "gabarito",
    "gabarito_final",
    "correctness",
    "is_correct",
    "runtime_application_event",
    "final_pedagogical_update_event",
}


def test_simulado_runtime_application_guardrails_handles_missing_integrated_result_safely(tmp_path):
    fixture = missing_integrated_result_fixture(tmp_path)

    assert build_runtime_guardrail(fixture) is None
    assert fixture.context.repository.list_user_simulado_runtime_guardrails(user_id=fixture.context.user_id) == []


def test_simulado_runtime_application_guardrails_blocks_incomplete_chain_or_missing_dependencies(tmp_path):
    incomplete = build_runtime_guardrail(incomplete_integrated_chain_fixture(tmp_path / "incomplete"))
    missing_score = build_runtime_guardrail(missing_score_result_fixture(tmp_path / "missing-score"))
    missing_guardrail = build_runtime_guardrail(missing_progress_guardrail_fixture(tmp_path / "missing-guardrail"))
    missing_policy = build_runtime_guardrail(missing_runtime_policy_fixture(tmp_path / "missing-policy"))

    assert incomplete is not None
    assert incomplete.readiness_state == "blocked_by_incomplete_integrated_chain"
    assert incomplete.eligibility.eligible_for_future_runtime_application is False
    assert "blocked_by_incomplete_integrated_chain" in {item.code for item in incomplete.blockers}

    assert missing_score is not None
    assert "blocked_by_missing_score_result" in {item.code for item in missing_score.blockers}

    assert missing_guardrail is not None
    assert "blocked_by_missing_progress_guardrail" in {item.code for item in missing_guardrail.blockers}

    assert missing_policy is not None
    assert missing_policy.safety_assessment.runtime_policy_available is False
    assert "blocked_by_runtime_policy_missing" in {item.code for item in missing_policy.blockers}


def test_simulado_runtime_application_guardrails_blocks_incomplete_score_or_not_eligible_progress_guardrail(tmp_path):
    incomplete_score = build_runtime_guardrail(incomplete_score_fixture(tmp_path / "score"))
    incomplete_correction = build_runtime_guardrail(incomplete_correction_fixture(tmp_path / "correction"))
    not_eligible = build_runtime_guardrail(progress_guardrail_not_eligible_fixture(tmp_path / "not-eligible"))

    assert incomplete_score is not None
    assert "blocked_by_incomplete_score" in {item.code for item in incomplete_score.blockers}
    assert incomplete_score.safety_assessment.score_complete is False

    assert incomplete_correction is not None
    assert incomplete_correction.safety_assessment.integrated_chain_complete is True
    assert incomplete_correction.eligibility.requires_complete_score is True

    assert not_eligible is not None
    assert "blocked_by_progress_guardrail_not_eligible" in {item.code for item in not_eligible.blockers}
    assert not_eligible.safety_assessment.progress_guardrail_eligible is False


def test_simulado_runtime_application_guardrails_preserve_candidate_intents_surfaces_and_safety_assessment(tmp_path):
    intents = build_runtime_guardrail(candidate_mutation_intents_fixture(tmp_path / "intents"))
    surfaces = build_runtime_guardrail(affected_runtime_surfaces_fixture(tmp_path / "surfaces"))
    safety = build_runtime_guardrail(safety_assessment_fixture(tmp_path / "safety"))

    assert intents is not None
    assert intents.candidate_mutation_intents
    for item in intents.candidate_mutation_intents:
        assert item.intent_type in {
            "progress_update_candidate",
            "ranking_update_candidate",
            "retention_update_candidate",
            "scheduler_update_candidate",
            "study_cycle_update_candidate",
            "curriculum_graph_update_candidate",
            "unknown",
        }
        assert item.proposed_surface in {
            "progress",
            "ranking",
            "retention",
            "scheduler",
            "study_cycle",
            "curriculum_graph",
            "adaptive_tuning",
            "unknown",
        }
        assert item.application_applied is False
        assert item.future_application_allowed is False

    assert surfaces is not None
    assert surfaces.affected_runtime_surfaces
    for surface in surfaces.affected_runtime_surfaces:
        assert surface.surface_type in {
            "progress",
            "ranking",
            "retention",
            "scheduler",
            "study_cycle",
            "curriculum_graph",
            "adaptive_tuning",
            "unknown",
        }
        assert surface.update_applied is False

    assert safety is not None
    assert safety.safety_assessment.integrated_chain_complete is True
    assert safety.safety_assessment.score_result_present is True
    assert safety.safety_assessment.progress_guardrail_present is True
    assert safety.safety_assessment.runtime_policy_available is False
    assert safety.safety_assessment.enough_data_for_future_application is False


def test_simulado_runtime_application_guardrails_preserve_no_public_answer_key_and_no_runtime_mutation(tmp_path):
    result = build_runtime_guardrail(no_public_key_gabarito_safety_fixture(tmp_path))
    runtime = build_runtime_guardrail(runtime_mutation_disabled_fixture(tmp_path / "runtime"))
    assert result is not None
    assert runtime is not None

    dumped_payload = result.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)

    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False
    assert runtime.runtime_application_enabled is False
    assert runtime.runtime_application_applied is False
    assert runtime.progress_mutation_enabled is False
    assert runtime.progress_mutation_applied is False
    assert runtime.ranking_update_enabled is False
    assert runtime.ranking_update_applied is False
    assert runtime.retention_update_enabled is False
    assert runtime.retention_update_applied is False
    assert runtime.scheduler_update_enabled is False
    assert runtime.scheduler_update_applied is False
    assert runtime.study_cycle_update_enabled is False
    assert runtime.study_cycle_update_applied is False
    assert runtime.curriculum_graph_update_enabled is False
    assert runtime.curriculum_graph_update_applied is False
    assert runtime.adaptive_tuning_enabled is False
    assert runtime.adaptive_tuning_applied is False
    assert runtime.no_runtime_application is True
    assert runtime.no_progress_mutation is True
    assert runtime.no_ranking_update is True
    assert runtime.no_retention_update is True
    assert runtime.no_scheduler_update is True
    assert runtime.no_study_cycle_update is True
    assert runtime.no_curriculum_graph_update is True
    assert runtime.no_adaptive_tuning_update is True
    for key in FORBIDDEN_RUNTIME_GUARDRAIL_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped


def test_simulado_runtime_application_guardrails_is_idempotent_and_does_not_mutate_sources(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    result = build_runtime_guardrail(fixture)
    assert result is not None
    integrated_result = fixture.integrated_result
    assert integrated_result is not None
    service = SimuladoRuntimeApplicationGuardrailsService(fixture.context.repository)

    before_integrated = fixture.context.repository.get_simulado_integrated_result_by_id(
        integrated_result.integrated_result_id,
        user_id=fixture.context.user_id,
    )
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_runtime_guardrail(integrated_result.integrated_result_id, user_id=fixture.context.user_id)
    second = service.build_runtime_guardrail(integrated_result.integrated_result_id, user_id=fixture.context.user_id)

    by_source = fixture.context.repository.get_simulado_runtime_guardrail(
        integrated_result.integrated_result_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_runtime_guardrail_by_id(
        result.runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_runtime_guardrails(user_id=fixture.context.user_id)

    after_integrated = fixture.context.repository.get_simulado_integrated_result_by_id(
        integrated_result.integrated_result_id,
        user_id=fixture.context.user_id,
    )
    after_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

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


def test_simulado_runtime_application_guardrails_preserve_runtime_safety_metadata(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = no_runtime_mutation_fixture(tmp_path, repository=repository)
    result = build_runtime_guardrail(fixture)
    assert result is not None
    assert result.metadata.get("llm_used") is False
    assert result.metadata.get("external_calls_used") is False


def test_simulado_runtime_application_guardrails_cover_mixed_runtime_blockers(tmp_path):
    result = build_runtime_guardrail(mixed_runtime_guardrail_fixture(tmp_path))
    assert result is not None
    blocker_codes = {item.code for item in result.blockers}
    assert "blocked_by_runtime_policy_missing" in blocker_codes
    assert "blocked_by_runtime_mutation_disabled" in blocker_codes
    assert "blocked_by_progress_guardrail_not_eligible" in blocker_codes
