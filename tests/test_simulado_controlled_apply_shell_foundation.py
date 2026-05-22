import json

from app.services.simulado_controlled_apply_shell import (
    SimuladoControlledRuntimeApplyShellService,
)
from tests.fixtures.simulado_controlled_apply_shells import (
    application_already_applied_fixture,
    application_not_planned_only_fixture,
    audit_confirmation_missing_fixture,
    build_controlled_apply_shell,
    explicit_apply_approval_missing_fixture,
    idempotency_fixture,
    incomplete_guardrail_fixture,
    intents_not_apply_allowed_fixture,
    missing_runtime_policy_fixture,
    missing_runtime_progress_application_fixture,
    mixed_controlled_apply_shell_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    runtime_application_disabled_fixture,
    source_application_planned_only_fixture,
    surfaces_not_apply_allowed_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_APPLY_SHELL_KEYS = {
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


def test_controlled_apply_shell_handles_missing_runtime_progress_application_safely(tmp_path):
    fixture = missing_runtime_progress_application_fixture(tmp_path)

    assert build_controlled_apply_shell(fixture) is None
    assert fixture.context.repository.list_user_simulado_controlled_apply_shells(
        user_id=fixture.context.user_id
    ) == []


def test_controlled_apply_shell_blocks_invalid_source_application_states(tmp_path):
    not_planned = build_controlled_apply_shell(application_not_planned_only_fixture(tmp_path / "not-planned"))
    already_applied = build_controlled_apply_shell(
        application_already_applied_fixture(tmp_path / "already-applied")
    )
    missing_policy = build_controlled_apply_shell(missing_runtime_policy_fixture(tmp_path / "missing-policy"))
    explicit_missing = build_controlled_apply_shell(
        explicit_apply_approval_missing_fixture(tmp_path / "explicit-missing")
    )
    audit_missing = build_controlled_apply_shell(
        audit_confirmation_missing_fixture(tmp_path / "audit-missing")
    )
    runtime_disabled = build_controlled_apply_shell(
        runtime_application_disabled_fixture(tmp_path / "runtime-disabled")
    )
    incomplete = build_controlled_apply_shell(incomplete_guardrail_fixture(tmp_path / "incomplete"))

    assert not_planned is not None
    assert not_planned.readiness_state == "blocked_by_application_not_planned_only"
    assert not_planned.apply_status == "apply_blocked"

    assert already_applied is not None
    assert already_applied.readiness_state == "blocked_by_application_already_applied"
    assert already_applied.apply_status == "apply_blocked"

    assert missing_policy is not None
    assert missing_policy.readiness_state == "blocked_by_runtime_policy_missing"
    assert missing_policy.apply_request_accepted is False

    assert explicit_missing is not None
    assert explicit_missing.readiness_state == "blocked_by_explicit_apply_approval_missing"
    assert explicit_missing.apply_request_accepted is False

    assert audit_missing is not None
    assert audit_missing.readiness_state == "blocked_by_audit_confirmation_missing"
    assert audit_missing.apply_preconditions_satisfied is False

    assert runtime_disabled is not None
    assert runtime_disabled.readiness_state == "blocked_by_runtime_application_disabled"

    assert incomplete is not None
    assert incomplete.readiness_state in {
        "blocked_by_application_not_planned_only",
        "blocked_by_runtime_policy_missing",
        "blocked_by_explicit_apply_approval_missing",
        "blocked_by_audit_confirmation_missing",
        "blocked_by_intents_not_apply_allowed",
        "blocked_by_surfaces_not_apply_allowed",
        "apply_shell_needs_review",
    }


def test_controlled_apply_shell_preserves_planned_only_shape_and_rejects_intents_and_surfaces(tmp_path):
    planned_only = build_controlled_apply_shell(source_application_planned_only_fixture(tmp_path / "planned-only"))
    intents = build_controlled_apply_shell(intents_not_apply_allowed_fixture(tmp_path / "intents"))
    surfaces = build_controlled_apply_shell(surfaces_not_apply_allowed_fixture(tmp_path / "surfaces"))

    assert planned_only is not None
    assert planned_only.application_mode in {"pre_apply_shell", "controlled_apply_shell"}
    assert planned_only.apply_status in {"apply_blocked", "apply_shell_created_not_applied"}
    assert planned_only.apply_shell_created is True
    assert planned_only.apply_request_accepted is False
    assert planned_only.apply_preconditions_satisfied is False
    assert planned_only.runtime_application_applied is False

    assert intents is not None
    assert intents.readiness_state == "blocked_by_intents_not_apply_allowed"
    assert intents.intent_decisions
    for decision in intents.intent_decisions:
        assert decision.intent_type in {
            "progress_update_candidate",
            "ranking_update_candidate",
            "retention_update_candidate",
            "scheduler_update_candidate",
            "study_cycle_update_candidate",
            "curriculum_graph_update_candidate",
            "unknown",
        }
        assert decision.proposed_surface in {
            "progress",
            "ranking",
            "retention",
            "scheduler",
            "study_cycle",
            "curriculum_graph",
            "adaptive_tuning",
            "unknown",
        }
        assert decision.applied is False
        assert decision.apply_decision == "intent_rejected_pre_apply"

    assert surfaces is not None
    assert surfaces.readiness_state == "blocked_by_surfaces_not_apply_allowed"
    assert surfaces.surface_decisions
    for decision in surfaces.surface_decisions:
        assert decision.surface_type in {
            "progress",
            "ranking",
            "retention",
            "scheduler",
            "study_cycle",
            "curriculum_graph",
            "adaptive_tuning",
            "unknown",
        }
        assert decision.applied is False
        assert decision.apply_decision == "surface_rejected_pre_apply"


def test_controlled_apply_shell_preserves_audit_requirements_and_no_public_answer_key(tmp_path):
    safe = build_controlled_apply_shell(no_public_key_gabarito_safety_fixture(tmp_path / "safe"))
    mixed = build_controlled_apply_shell(mixed_controlled_apply_shell_fixture(tmp_path / "mixed"))

    assert safe is not None
    requirement_types = {item.requirement_type for item in safe.audit_requirements}
    assert requirement_types == {
        "runtime_policy_confirmation",
        "explicit_apply_approval",
        "audit_confirmation",
        "public_answer_key_absence_confirmation",
        "rollback_plan_confirmation",
        "human_review_confirmation",
    }
    for item in safe.audit_requirements:
        assert item.required is True
        assert item.satisfied is False

    dumped_payload = safe.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    assert safe.answer_key_publicly_exposed is False
    assert safe.gabarito_publicly_exposed is False
    for key in FORBIDDEN_APPLY_SHELL_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped

    assert mixed is not None
    blocker_codes = {item.code for item in mixed.blockers}
    assert "blocked_by_runtime_policy_missing" in blocker_codes
    assert mixed.audit_trail
    assert "apply_shell_created" in {item.event_type for item in mixed.audit_trail}


def test_controlled_apply_shell_preserves_no_runtime_application_and_no_runtime_mutation(tmp_path):
    application = build_controlled_apply_shell(no_runtime_application_fixture(tmp_path / "application"))
    mutation = build_controlled_apply_shell(no_runtime_mutation_fixture(tmp_path / "mutation"))

    assert application is not None
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


def test_controlled_apply_shell_is_idempotent_and_does_not_mutate_sources(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    result = build_controlled_apply_shell(fixture)
    assert result is not None
    application = fixture.runtime_progress_application
    assert application is not None
    service = SimuladoControlledRuntimeApplyShellService(fixture.context.repository)

    before_application = fixture.context.repository.get_simulado_runtime_progress_application_by_id(
        application.application_id,
        user_id=fixture.context.user_id,
    )
    before_runtime_guardrail = fixture.context.repository.get_simulado_runtime_guardrail_by_id(
        application.source_runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_apply_shell(application.application_id, user_id=fixture.context.user_id)
    second = service.build_apply_shell(application.application_id, user_id=fixture.context.user_id)
    by_source = fixture.context.repository.get_simulado_controlled_apply_shell(
        application.application_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_controlled_apply_shell_by_id(
        result.apply_shell_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_controlled_apply_shells(
        user_id=fixture.context.user_id
    )

    after_application = fixture.context.repository.get_simulado_runtime_progress_application_by_id(
        application.application_id,
        user_id=fixture.context.user_id,
    )
    after_runtime_guardrail = fixture.context.repository.get_simulado_runtime_guardrail_by_id(
        application.source_runtime_guardrail_id,
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
    assert before_application is not None and after_application is not None
    assert before_runtime_guardrail is not None and after_runtime_guardrail is not None
    assert before_application.model_dump(mode="json") == after_application.model_dump(mode="json")
    assert before_runtime_guardrail.model_dump(mode="json") == after_runtime_guardrail.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
