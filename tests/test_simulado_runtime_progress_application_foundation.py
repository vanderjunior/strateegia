import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_progress_application import (
    SimuladoRuntimeProgressApplicationService,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_progress_applications import (
    audit_trail_fixture,
    build_runtime_progress_application,
    explicit_apply_not_allowed_fixture,
    guardrail_not_eligible_fixture,
    idempotency_fixture,
    incomplete_guardrail_fixture,
    incomplete_score_fixture,
    missing_runtime_guardrail_fixture,
    missing_runtime_policy_fixture,
    mixed_runtime_progress_application_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    planned_mutation_intents_fixture,
    proposed_surface_diffs_fixture,
    runtime_application_disabled_fixture,
)


FORBIDDEN_APPLICATION_KEYS = {
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


def test_runtime_progress_application_handles_missing_runtime_guardrail_safely(tmp_path):
    fixture = missing_runtime_guardrail_fixture(tmp_path)

    assert build_runtime_progress_application(fixture) is None
    assert fixture.context.repository.list_user_simulado_runtime_progress_applications(
        user_id=fixture.context.user_id
    ) == []


def test_runtime_progress_application_blocks_non_ready_guardrails(tmp_path):
    not_eligible = build_runtime_progress_application(guardrail_not_eligible_fixture(tmp_path / "not-eligible"))
    incomplete = build_runtime_progress_application(incomplete_guardrail_fixture(tmp_path / "incomplete"))
    missing_policy = build_runtime_progress_application(missing_runtime_policy_fixture(tmp_path / "missing-policy"))
    disabled = build_runtime_progress_application(runtime_application_disabled_fixture(tmp_path / "disabled"))
    explicit_blocked = build_runtime_progress_application(
        explicit_apply_not_allowed_fixture(tmp_path / "explicit-blocked")
    )
    incomplete_score = build_runtime_progress_application(incomplete_score_fixture(tmp_path / "incomplete-score"))

    assert not_eligible is not None
    assert not_eligible.application_status == "application_blocked"
    assert not_eligible.readiness_state == "blocked_by_guardrail_not_eligible"
    assert not_eligible.plan.can_apply_now is False
    assert "blocked_by_guardrail_not_eligible" in {item.code for item in not_eligible.blockers}

    assert incomplete is not None
    assert incomplete.readiness_state == "blocked_by_incomplete_guardrail"
    assert "blocked_by_incomplete_guardrail" in {item.code for item in incomplete.blockers}

    assert missing_policy is not None
    assert missing_policy.readiness_state == "blocked_by_runtime_policy_missing"
    assert "blocked_by_runtime_policy_missing" in {item.code for item in missing_policy.blockers}

    assert disabled is not None
    assert disabled.readiness_state == "blocked_by_runtime_application_disabled"
    assert "blocked_by_runtime_application_disabled" in {item.code for item in disabled.blockers}

    assert explicit_blocked is not None
    assert explicit_blocked.readiness_state in {
        "blocked_by_explicit_apply_not_allowed",
        "blocked_by_audit_confirmation_missing",
    }
    assert explicit_blocked.plan.can_apply_now is False

    assert incomplete_score is not None
    assert incomplete_score.plan.requires_complete_guardrail in {False, True}
    assert incomplete_score.readiness_state in {
        "blocked_by_incomplete_guardrail",
        "blocked_by_guardrail_not_eligible",
        "blocked_by_runtime_policy_missing",
    }


def test_runtime_progress_application_preserves_planned_intents_and_surface_diffs(tmp_path):
    intents = build_runtime_progress_application(planned_mutation_intents_fixture(tmp_path / "intents"))
    diffs = build_runtime_progress_application(proposed_surface_diffs_fixture(tmp_path / "diffs"))

    assert intents is not None
    assert intents.planned_mutation_intents
    for item in intents.planned_mutation_intents:
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
        assert item.planned is True
        assert item.applied is False
        assert item.apply_allowed is False

    assert diffs is not None
    assert diffs.proposed_surface_diffs
    for diff in diffs.proposed_surface_diffs:
        assert diff.surface_type in {
            "progress",
            "ranking",
            "retention",
            "scheduler",
            "study_cycle",
            "curriculum_graph",
            "adaptive_tuning",
            "unknown",
        }
        assert diff.applied is False
        assert diff.apply_allowed is False
        assert diff.diff_status in {"diff_planned_not_applied", "diff_blocked", "diff_needs_review"}


def test_runtime_progress_application_preserves_audit_trail_and_no_public_answer_key(tmp_path):
    audit = build_runtime_progress_application(audit_trail_fixture(tmp_path / "audit"))
    safe = build_runtime_progress_application(no_public_key_gabarito_safety_fixture(tmp_path / "safe"))

    assert audit is not None
    assert audit.audit_trail
    event_types = {item.event_type for item in audit.audit_trail}
    assert "application_plan_created" in event_types
    assert any(code in event_types for code in {"application_blocked", "runtime_policy_missing", "no_runtime_application"})

    assert safe is not None
    dumped_payload = safe.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    assert safe.answer_key_publicly_exposed is False
    assert safe.gabarito_publicly_exposed is False
    for key in FORBIDDEN_APPLICATION_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped


def test_runtime_progress_application_preserves_no_runtime_application_and_no_runtime_mutation(tmp_path):
    application = build_runtime_progress_application(no_runtime_application_fixture(tmp_path / "application"))
    mutation = build_runtime_progress_application(no_runtime_mutation_fixture(tmp_path / "mutation"))

    assert application is not None
    assert application.application_mode in {"dry_run", "planned_only"}
    assert application.application_status in {
        "application_planned_not_applied",
        "application_blocked",
        "application_needs_review",
    }
    assert application.runtime_application_enabled is False
    assert application.runtime_application_applied is False
    assert application.no_runtime_application is True

    assert mutation is not None
    assert mutation.progress_mutation_enabled is False
    assert mutation.progress_mutation_applied is False
    assert mutation.ranking_update_enabled is False
    assert mutation.ranking_update_applied is False
    assert mutation.retention_update_enabled is False
    assert mutation.retention_update_applied is False
    assert mutation.scheduler_update_enabled is False
    assert mutation.scheduler_update_applied is False
    assert mutation.study_cycle_update_enabled is False
    assert mutation.study_cycle_update_applied is False
    assert mutation.curriculum_graph_update_enabled is False
    assert mutation.curriculum_graph_update_applied is False
    assert mutation.adaptive_tuning_enabled is False
    assert mutation.adaptive_tuning_applied is False
    assert mutation.no_progress_mutation is True
    assert mutation.no_ranking_update is True
    assert mutation.no_retention_update is True
    assert mutation.no_scheduler_update is True
    assert mutation.no_study_cycle_update is True
    assert mutation.no_curriculum_graph_update is True
    assert mutation.no_adaptive_tuning_update is True


def test_runtime_progress_application_is_idempotent_and_does_not_mutate_sources(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    result = build_runtime_progress_application(fixture)
    assert result is not None
    runtime_guardrail = fixture.runtime_guardrail
    assert runtime_guardrail is not None
    service = SimuladoRuntimeProgressApplicationService(fixture.context.repository)

    before_runtime_guardrail = fixture.context.repository.get_simulado_runtime_guardrail_by_id(
        runtime_guardrail.runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_integrated = fixture.context.repository.get_simulado_integrated_result_by_id(
        runtime_guardrail.source_integrated_result_id,
        user_id=fixture.context.user_id,
    )
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_application(runtime_guardrail.runtime_guardrail_id, user_id=fixture.context.user_id)
    second = service.build_application(runtime_guardrail.runtime_guardrail_id, user_id=fixture.context.user_id)
    by_source = fixture.context.repository.get_simulado_runtime_progress_application(
        runtime_guardrail.runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_runtime_progress_application_by_id(
        result.application_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_runtime_progress_applications(
        user_id=fixture.context.user_id
    )

    after_runtime_guardrail = fixture.context.repository.get_simulado_runtime_guardrail_by_id(
        runtime_guardrail.runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_integrated = fixture.context.repository.get_simulado_integrated_result_by_id(
        runtime_guardrail.source_integrated_result_id,
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
    assert before_runtime_guardrail is not None and after_runtime_guardrail is not None
    assert before_integrated is not None and after_integrated is not None
    assert before_runtime_guardrail.model_dump(mode="json") == after_runtime_guardrail.model_dump(mode="json")
    assert before_integrated.model_dump(mode="json") == after_integrated.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")


def test_runtime_progress_application_preserves_runtime_safety_metadata(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = no_runtime_mutation_fixture(tmp_path, repository=repository)
    result = build_runtime_progress_application(fixture)
    assert result is not None
    assert result.metadata.get("llm_used") is False
    assert result.metadata.get("external_calls_used") is False


def test_runtime_progress_application_covers_mixed_blockers(tmp_path):
    result = build_runtime_progress_application(mixed_runtime_progress_application_fixture(tmp_path))
    assert result is not None
    blocker_codes = {item.code for item in result.blockers}
    assert "blocked_by_runtime_policy_missing" in blocker_codes
    assert "blocked_by_runtime_application_disabled" in blocker_codes
    assert len(result.warnings) >= 1
