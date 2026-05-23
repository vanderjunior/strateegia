import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_apply_policy import SimuladoRuntimeApplyPolicyService
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_apply_policies import (
    apply_scope_not_allowed_fixture,
    audit_requirement_missing_fixture,
    build_runtime_apply_policy,
    capture_runtime_apply_policy_source_snapshot,
    environment_not_safe_fixture,
    feature_flag_disabled_fixture,
    final_event_already_applied_fixture,
    final_event_not_proposal_only_fixture,
    human_review_requirement_missing_fixture,
    idempotency_requirement_missing_fixture,
    missing_final_event_fixture,
    policy_summary_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_requirement_missing_fixture,
    runtime_apply_not_allowed_now_fixture,
)


FORBIDDEN_RUNTIME_POLICY_KEYS = {
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
    "applied_final_pedagogical_update_event",
    "applied_progress_ledger_entry",
    "commit_execution_event",
    "mutation_commit_event",
    "runtime_application_event",
}


def _assert_no_runtime_apply_or_mutation(result) -> None:
    assert result.runtime_apply_policy_created is True
    assert result.runtime_apply_policy_mode in {"policy_gate_only", "feature_flag_gate_only"}
    assert result.runtime_apply_policy_status in {
        "apply_blocked",
        "apply_not_enabled",
        "policy_needs_review",
        "ready_for_future_minimal_apply_review",
    }
    assert result.runtime_apply_allowed_now is False
    assert result.final_event_apply_allowed is False
    assert result.final_event_applied is False
    assert result.final_event_application_started is False
    assert result.final_event_application_completed is False
    assert result.minimal_progress_ledger_apply_allowed is False
    assert result.ranking_apply_allowed is False
    assert result.retention_apply_allowed is False
    assert result.scheduler_apply_allowed is False
    assert result.study_cycle_apply_allowed is False
    assert result.curriculum_graph_apply_allowed is False
    assert result.adaptive_tuning_apply_allowed is False
    assert result.runtime_application_enabled is False
    assert result.runtime_application_applied is False
    assert result.progress_mutation_enabled is False
    assert result.progress_mutation_applied is False
    assert result.ranking_update_enabled is False
    assert result.ranking_update_applied is False
    assert result.retention_update_enabled is False
    assert result.retention_update_applied is False
    assert result.scheduler_update_enabled is False
    assert result.scheduler_update_applied is False
    assert result.study_cycle_update_enabled is False
    assert result.study_cycle_update_applied is False
    assert result.curriculum_graph_update_enabled is False
    assert result.curriculum_graph_update_applied is False
    assert result.adaptive_tuning_enabled is False
    assert result.adaptive_tuning_applied is False
    assert result.commit_executed is False
    assert result.mutation_committed is False
    assert result.no_commit_execution is True
    assert result.no_commit_execution_event_created is True
    assert result.no_mutation_commit is True
    assert result.no_mutation_commit_event_created is True
    assert result.no_runtime_application is True
    assert result.no_progress_mutation is True
    assert result.no_ranking_update is True
    assert result.no_retention_update is True
    assert result.no_scheduler_update is True
    assert result.no_study_cycle_update is True
    assert result.no_curriculum_graph_update is True
    assert result.no_adaptive_tuning_update is True
    assert result.no_applied_final_pedagogical_update_event is True
    assert result.no_applied_progress_ledger_entry is True
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


def _assert_no_leakage(result) -> None:
    payload = result.model_dump(mode="json")
    dumped = json.dumps(payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(payload)
    for key in FORBIDDEN_RUNTIME_POLICY_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped
    assert "final_question_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys


def test_runtime_apply_policy_handles_missing_final_event_safely(tmp_path):
    fixture = missing_final_event_fixture(tmp_path)

    assert build_runtime_apply_policy(fixture) is None
    assert fixture.context.repository.list_user_simulado_runtime_apply_policies(
        user_id=fixture.context.user_id
    ) == []


def test_runtime_apply_policy_blocks_invalid_source_and_policy_states_conservatively(tmp_path):
    not_proposal_only = build_runtime_apply_policy(
        final_event_not_proposal_only_fixture(tmp_path / "not-proposal")
    )
    already_applied = build_runtime_apply_policy(
        final_event_already_applied_fixture(tmp_path / "already-applied")
    )
    feature_flag_disabled = build_runtime_apply_policy(
        feature_flag_disabled_fixture(tmp_path / "feature-flag-disabled")
    )
    not_allowed_now = build_runtime_apply_policy(
        runtime_apply_not_allowed_now_fixture(tmp_path / "not-allowed-now")
    )
    idempotency_missing = build_runtime_apply_policy(
        idempotency_requirement_missing_fixture(tmp_path / "idempotency-missing")
    )
    rollback_missing = build_runtime_apply_policy(
        rollback_requirement_missing_fixture(tmp_path / "rollback-missing")
    )
    audit_missing = build_runtime_apply_policy(
        audit_requirement_missing_fixture(tmp_path / "audit-missing")
    )
    human_review_missing = build_runtime_apply_policy(
        human_review_requirement_missing_fixture(tmp_path / "human-review-missing")
    )
    environment_unsafe = build_runtime_apply_policy(
        environment_not_safe_fixture(tmp_path / "environment-unsafe")
    )
    apply_scope_blocked = build_runtime_apply_policy(
        apply_scope_not_allowed_fixture(tmp_path / "apply-scope-blocked")
    )
    unsafe = build_runtime_apply_policy(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )

    assert not_proposal_only is not None
    assert not_proposal_only.readiness_state == "blocked_by_final_event_not_proposal_only"
    _assert_no_runtime_apply_or_mutation(not_proposal_only)

    assert already_applied is not None
    assert already_applied.readiness_state == "blocked_by_final_event_already_applied"
    _assert_no_runtime_apply_or_mutation(already_applied)

    assert feature_flag_disabled is not None
    assert feature_flag_disabled.runtime_apply_feature_flag_enabled is False
    assert feature_flag_disabled.readiness_state == "blocked_by_runtime_apply_feature_flag_disabled"
    _assert_no_runtime_apply_or_mutation(feature_flag_disabled)

    assert not_allowed_now is not None
    assert not_allowed_now.runtime_apply_feature_flag_enabled is True
    assert not_allowed_now.readiness_state == "blocked_by_runtime_apply_not_allowed_now"
    _assert_no_runtime_apply_or_mutation(not_allowed_now)

    assert idempotency_missing is not None
    assert idempotency_missing.readiness_state == "blocked_by_idempotency_requirement_missing"
    assert idempotency_missing.idempotency_requirement.idempotency_key_required is True
    _assert_no_runtime_apply_or_mutation(idempotency_missing)

    assert rollback_missing is not None
    assert rollback_missing.readiness_state == "blocked_by_rollback_requirement_missing"
    _assert_no_runtime_apply_or_mutation(rollback_missing)

    assert audit_missing is not None
    assert audit_missing.readiness_state == "blocked_by_audit_requirement_missing"
    _assert_no_runtime_apply_or_mutation(audit_missing)

    assert human_review_missing is not None
    assert human_review_missing.readiness_state == "blocked_by_human_review_requirement_missing"
    _assert_no_runtime_apply_or_mutation(human_review_missing)

    assert environment_unsafe is not None
    assert environment_unsafe.readiness_state == "blocked_by_environment_not_safe_for_apply"
    _assert_no_runtime_apply_or_mutation(environment_unsafe)

    assert apply_scope_blocked is not None
    assert apply_scope_blocked.readiness_state == "blocked_by_apply_scope_not_allowed"
    _assert_no_runtime_apply_or_mutation(apply_scope_blocked)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    _assert_no_runtime_apply_or_mutation(unsafe)
    _assert_no_leakage(unsafe)


def test_runtime_apply_policy_builds_bounded_summary_scope_requirements_and_audit(tmp_path):
    result = build_runtime_apply_policy(policy_summary_fixture(tmp_path))

    assert result is not None
    assert result.policy_summary.source_final_event_present is True
    assert result.policy_summary.source_final_event_created is True
    assert result.policy_summary.source_final_event_applied is False
    assert result.policy_summary.source_final_event_apply_allowed is False
    assert result.policy_summary.source_event_proposal_only is True
    assert result.policy_summary.apply_feature_flag_enabled is False
    assert result.policy_summary.apply_allowed_now is False
    assert result.policy_summary.minimal_progress_ledger_scope_allowed is False
    assert result.policy_summary.ranking_scope_allowed is False
    assert result.policy_summary.retention_scope_allowed is False
    assert result.policy_summary.scheduler_scope_allowed is False
    assert result.policy_summary.study_cycle_scope_allowed is False
    assert result.policy_summary.curriculum_graph_scope_allowed is False
    assert result.policy_summary.adaptive_tuning_scope_allowed is False
    assert result.policy_summary.idempotency_required is True
    assert result.policy_summary.rollback_required is True
    assert result.policy_summary.audit_required is True
    assert result.policy_summary.human_review_required is True
    assert result.policy_summary.environment_safe_for_apply is False
    assert result.policy_summary.unsafe_public_answer_key_exposure_detected is False
    assert result.policy_summary.unsafe_gabarito_exposure_detected is False

    assert result.feature_flag_snapshot.feature_flag_name == "simulado_runtime_apply_enabled"
    assert result.feature_flag_snapshot.feature_flag_enabled is False
    assert result.feature_flag_snapshot.default_enabled is False

    assert result.apply_scope_policy.allowed_surfaces == []
    assert set(result.apply_scope_policy.blocked_surfaces) == {
        "minimal_progress_ledger",
        "ranking",
        "retention",
        "scheduler",
        "study_cycle",
        "curriculum_graph",
        "adaptive_tuning",
    }
    assert result.apply_scope_policy.minimal_progress_ledger_apply_allowed is False
    assert result.apply_scope_policy.ranking_apply_allowed is False
    assert result.apply_scope_policy.retention_apply_allowed is False
    assert result.apply_scope_policy.scheduler_apply_allowed is False
    assert result.apply_scope_policy.study_cycle_apply_allowed is False
    assert result.apply_scope_policy.curriculum_graph_apply_allowed is False
    assert result.apply_scope_policy.adaptive_tuning_apply_allowed is False

    assert result.idempotency_requirement.idempotency_key_required is True
    assert result.idempotency_requirement.idempotency_key_present is False
    assert result.idempotency_requirement.idempotency_key_valid is False
    assert result.idempotency_requirement.satisfied is False

    assert result.rollback_requirement.rollback_required is True
    assert result.rollback_requirement.rollback_plan_required is True
    assert result.rollback_requirement.rollback_plan_present is False
    assert result.rollback_requirement.rollback_verified is False
    assert result.rollback_requirement.satisfied is False

    assert result.audit_requirement.audit_required is True
    assert result.audit_requirement.audit_confirmation_required is True
    assert result.audit_requirement.audit_confirmation_present is False
    assert result.audit_requirement.satisfied is False

    assert result.human_review_requirement.human_review_required is True
    assert result.human_review_requirement.human_review_present is False
    assert result.human_review_requirement.satisfied is False

    assert result.environment_safety_requirement.environment_safe_for_apply is False
    assert result.environment_safety_requirement.write_mode_allowed is False
    assert result.environment_safety_requirement.dry_run_only is True
    assert result.environment_safety_requirement.external_services_disabled is True
    assert result.environment_safety_requirement.satisfied is False

    assert {
        "runtime_apply_policy_created",
        "runtime_apply_policy_evaluated",
        "runtime_apply_feature_flag_disabled",
        "runtime_apply_blocked",
        "idempotency_required",
        "rollback_required",
        "audit_required",
        "human_review_required",
        "environment_not_safe_for_apply",
        "no_applied_final_pedagogical_update_event",
        "no_applied_progress_ledger_entry",
        "no_runtime_application",
        "no_progress_mutation",
        "no_ranking_update",
        "no_retention_update",
        "no_scheduler_update",
        "no_study_cycle_update",
        "no_curriculum_graph_update",
        "no_adaptive_tuning_update",
    }.issubset({item.event_type for item in result.audit_trail})
    _assert_no_runtime_apply_or_mutation(result)


def test_runtime_apply_policy_preserves_no_leakage_and_no_runtime_mutation(tmp_path):
    result = build_runtime_apply_policy(policy_summary_fixture(tmp_path))

    assert result is not None
    _assert_no_runtime_apply_or_mutation(result)
    _assert_no_leakage(result)


def test_runtime_apply_policy_persists_deterministically_and_preserves_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = policy_summary_fixture(tmp_path / "idempotent", repository=repository)
    service = SimuladoRuntimeApplyPolicyService(repository)
    final_event = fixture.final_event
    assert final_event is not None

    before = capture_runtime_apply_policy_source_snapshot(fixture)
    first = build_runtime_apply_policy(fixture)
    middle = capture_runtime_apply_policy_source_snapshot(fixture)
    second = build_runtime_apply_policy(fixture)
    loaded = service.get_runtime_apply_policy(
        final_event.final_event_id,
        user_id=fixture.context.user_id,
    )
    loaded_by_id = service.get_runtime_apply_policy_by_id(
        first.runtime_apply_policy_id if first is not None else "missing",
        user_id=fixture.context.user_id,
    )
    after = capture_runtime_apply_policy_source_snapshot(fixture)

    assert first is not None
    assert second is not None
    assert loaded is not None
    assert loaded_by_id is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.model_dump(mode="json") == loaded.model_dump(mode="json")
    assert first.model_dump(mode="json") == loaded_by_id.model_dump(mode="json")
    assert before.final_event == after.final_event
    assert before.controlled_execution == after.controlled_execution
    assert before.execution_plan == after.execution_plan
    assert before.execution_approval == after.execution_approval
    assert before.execution_guardrail == after.execution_guardrail
    assert before.progress == after.progress
    assert before.runtime_apply_policy_count == 0
    assert middle.runtime_apply_policy_count == 1
    assert after.runtime_apply_policy_count == 1
