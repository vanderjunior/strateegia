import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_minimal_progress_ledger_apply import (
    SimuladoMinimalProgressLedgerApplyService,
)
from tests.fixtures.simulado_minimal_progress_ledger_applies import (
    allowed_minimal_progress_ledger_apply_fixture,
    audit_requirement_unsatisfied_fixture,
    build_minimal_progress_ledger_apply,
    capture_minimal_progress_ledger_apply_source_snapshot,
    environment_unsafe_fixture,
    human_review_requirement_unsatisfied_fixture,
    idempotency_fixture,
    idempotency_requirement_unsatisfied_fixture,
    minimal_progress_ledger_scope_not_allowed_fixture,
    missing_runtime_apply_policy_fixture,
    no_proposed_progress_updates_fixture,
    policy_feature_flag_disabled_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_requirement_unsatisfied_fixture,
    runtime_apply_not_allowed_now_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_KEYS = {
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
}


def _assert_no_propagation(result) -> None:
    assert result.final_event_applied_globally is False
    assert result.existing_progress_aggregate_mutated is False
    assert result.global_progress_mutation_applied is False
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
    assert result.runtime_application_enabled is False
    assert result.runtime_application_applied is False
    assert result.commit_executed is False
    assert result.mutation_committed is False
    assert result.no_global_progress_mutation is True
    assert result.no_existing_progress_aggregate_mutation is True
    assert result.no_ranking_update is True
    assert result.no_retention_update is True
    assert result.no_scheduler_update is True
    assert result.no_study_cycle_update is True
    assert result.no_curriculum_graph_update is True
    assert result.no_adaptive_tuning_update is True
    assert result.no_commit_execution is True
    assert result.no_mutation_commit is True
    assert result.no_runtime_application_beyond_minimal_ledger is True
    assert result.no_public_answer_key_exposure is True
    assert result.no_public_gabarito_exposure is True
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


def _assert_no_leakage(result) -> None:
    payload = result.model_dump(mode="json")
    dumped = json.dumps(payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(payload)
    for key in FORBIDDEN_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped


def test_minimal_progress_ledger_apply_handles_missing_runtime_apply_policy_safely(tmp_path):
    fixture = missing_runtime_apply_policy_fixture(tmp_path)

    assert build_minimal_progress_ledger_apply(fixture) is None
    assert fixture.context.repository.list_user_simulado_minimal_progress_ledger_applies(
        user_id=fixture.context.user_id
    ) == []


def test_minimal_progress_ledger_apply_blocks_disallowed_policy_and_source_states(tmp_path):
    feature_flag_disabled = build_minimal_progress_ledger_apply(
        policy_feature_flag_disabled_fixture(tmp_path / "feature-flag-disabled")
    )
    not_allowed_now = build_minimal_progress_ledger_apply(
        runtime_apply_not_allowed_now_fixture(tmp_path / "not-allowed-now")
    )
    scope_blocked = build_minimal_progress_ledger_apply(
        minimal_progress_ledger_scope_not_allowed_fixture(tmp_path / "scope-blocked")
    )
    idempotency_blocked = build_minimal_progress_ledger_apply(
        idempotency_requirement_unsatisfied_fixture(tmp_path / "idempotency")
    )
    rollback_blocked = build_minimal_progress_ledger_apply(
        rollback_requirement_unsatisfied_fixture(tmp_path / "rollback")
    )
    audit_blocked = build_minimal_progress_ledger_apply(
        audit_requirement_unsatisfied_fixture(tmp_path / "audit")
    )
    human_review_blocked = build_minimal_progress_ledger_apply(
        human_review_requirement_unsatisfied_fixture(tmp_path / "human-review")
    )
    environment_blocked = build_minimal_progress_ledger_apply(
        environment_unsafe_fixture(tmp_path / "environment")
    )
    unsafe_exposure = build_minimal_progress_ledger_apply(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )
    no_progress_updates = build_minimal_progress_ledger_apply(
        no_proposed_progress_updates_fixture(tmp_path / "no-progress-updates")
    )

    assert feature_flag_disabled is not None
    assert (
        feature_flag_disabled.readiness_state == "blocked_by_policy_feature_flag_disabled"
    )
    assert feature_flag_disabled.minimal_progress_ledger_apply_applied is False
    _assert_no_propagation(feature_flag_disabled)

    assert not_allowed_now is not None
    assert not_allowed_now.readiness_state == "blocked_by_runtime_apply_not_allowed_now"
    assert not_allowed_now.minimal_progress_ledger_apply_applied is False

    assert scope_blocked is not None
    assert (
        scope_blocked.readiness_state
        == "blocked_by_minimal_progress_ledger_scope_not_allowed"
    )

    assert idempotency_blocked is not None
    assert (
        idempotency_blocked.readiness_state
        == "blocked_by_idempotency_requirement_unsatisfied"
    )

    assert rollback_blocked is not None
    assert rollback_blocked.readiness_state == "blocked_by_rollback_requirement_unsatisfied"

    assert audit_blocked is not None
    assert audit_blocked.readiness_state == "blocked_by_audit_requirement_unsatisfied"

    assert human_review_blocked is not None
    assert (
        human_review_blocked.readiness_state
        == "blocked_by_human_review_requirement_unsatisfied"
    )

    assert environment_blocked is not None
    assert environment_blocked.readiness_state == "blocked_by_environment_not_safe_for_apply"

    assert unsafe_exposure is not None
    assert (
        unsafe_exposure.readiness_state
        == "blocked_by_public_answer_key_exposure_forbidden"
    )
    _assert_no_leakage(unsafe_exposure)

    assert no_progress_updates is not None
    assert no_progress_updates.readiness_state == "blocked_by_no_proposed_progress_updates"
    assert no_progress_updates.applied_progress_ledger_entry_count == 0


def test_minimal_progress_ledger_apply_creates_isolated_applied_ledger_entries_when_policy_allows(
    tmp_path,
):
    fixture = allowed_minimal_progress_ledger_apply_fixture(tmp_path)
    result = build_minimal_progress_ledger_apply(fixture)

    assert result is not None
    assert result.apply_mode == "minimal_progress_ledger_apply"
    assert result.apply_status == "minimal_ledger_apply_applied"
    assert result.readiness_state == "minimal_progress_ledger_apply_applied"
    assert result.minimal_progress_ledger_apply_created is True
    assert result.minimal_progress_ledger_apply_allowed is True
    assert result.minimal_progress_ledger_apply_applied is True
    assert result.applied_progress_ledger_entry_created is True
    assert result.applied_progress_ledger_entry_count > 0
    assert result.final_event_applied_to_minimal_ledger is True
    assert result.final_event_applied_globally is False
    assert result.idempotency_key_required is True
    assert result.idempotency_key_present is True
    assert result.idempotency_key_valid is True
    assert result.idempotency_key_recorded is True
    assert result.rollback_required is True
    assert result.rollback_reference_created is True
    assert result.rollback_executed is False
    assert result.apply_summary.ledger_apply_successful is True
    assert result.apply_summary.applied_ledger_entry_count == len(result.applied_ledger_entries)
    assert result.apply_summary.proposed_progress_update_count >= len(result.applied_ledger_entries)
    for entry in result.applied_ledger_entries:
        assert entry.user_id == fixture.context.user_id
        assert entry.source_final_event_id == result.source_final_event_id
        assert entry.source_policy_id == result.source_runtime_apply_policy_id
        assert entry.applied is True
        assert entry.applied_scope == "minimal_progress_ledger"
        assert entry.target_type in {
            "simulado_attempt",
            "simulado_score",
            "simulado_completion",
            "topic_signal",
            "unknown",
        }
        assert isinstance(entry.bounded_delta_summary, dict)
    event_types = {item.event_type for item in result.audit_trail}
    assert "minimal_progress_ledger_apply_created" in event_types
    assert "minimal_progress_ledger_apply_applied" in event_types
    assert "applied_progress_ledger_entry_created" in event_types
    assert "no_global_progress_mutation" in event_types
    assert "no_ranking_update" in event_types
    _assert_no_propagation(result)
    _assert_no_leakage(result)


def test_minimal_progress_ledger_apply_is_idempotent_and_preserves_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = idempotency_fixture(tmp_path, repository=repository)
    service = SimuladoMinimalProgressLedgerApplyService(repository)
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None

    before = capture_minimal_progress_ledger_apply_source_snapshot(fixture)
    first = build_minimal_progress_ledger_apply(fixture)
    middle = capture_minimal_progress_ledger_apply_source_snapshot(fixture)
    second = build_minimal_progress_ledger_apply(fixture)
    loaded = service.get_minimal_progress_ledger_apply(
        runtime_apply_policy.runtime_apply_policy_id,
        user_id=fixture.context.user_id,
    )
    loaded_by_id = service.get_minimal_progress_ledger_apply_by_id(
        first.minimal_progress_ledger_apply_id if first is not None else "missing",
        user_id=fixture.context.user_id,
    )
    after = capture_minimal_progress_ledger_apply_source_snapshot(fixture)

    assert first is not None
    assert second is not None
    assert loaded is not None
    assert loaded_by_id is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert loaded.model_dump(mode="json") == loaded_by_id.model_dump(mode="json")
    assert before.final_event == middle.final_event == after.final_event
    assert before.controlled_execution == middle.controlled_execution == after.controlled_execution
    assert before.execution_plan == middle.execution_plan == after.execution_plan
    assert before.execution_approval == middle.execution_approval == after.execution_approval
    assert before.execution_guardrail == middle.execution_guardrail == after.execution_guardrail
    assert before.runtime_apply_policy == middle.runtime_apply_policy == after.runtime_apply_policy
    assert before.progress == middle.progress == after.progress
    assert before.minimal_progress_ledger_apply_count == 0
    assert middle.minimal_progress_ledger_apply_count == 1
    assert after.minimal_progress_ledger_apply_count == 1
