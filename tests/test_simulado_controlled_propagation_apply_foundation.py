import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_propagation_apply import (
    SimuladoControlledPropagationApplyService,
)
from tests.fixtures.simulado_controlled_propagation_applies import (
    build_controlled_propagation_apply,
    capture_controlled_propagation_apply_source_snapshot,
    idempotency_replay_fixture,
    missing_propagation_guardrail_fixture,
    no_candidate_targets_fixture,
    safe_source_guardrail_fixture,
    source_guardrail_blocked_fixture,
    source_guardrail_not_ready_fixture,
    source_guardrail_unsafe_state_fixture,
    unsafe_public_exposure_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_KEYS = {
    "correct_answer",
    "correct_option",
    "answer_key",
    "answer_key_value",
    "final_answer_key_content",
    "gabarito",
    "correctness",
    "is_correct",
    "raw_runtime_block",
}
SURFACES = {
    "ranking",
    "retention",
    "scheduler",
    "study_cycle",
    "curriculum_graph",
    "adaptive_tuning",
}


def _assert_no_runtime_mutation(result) -> None:
    assert result.no_direct_runtime_propagation is True
    assert result.no_new_progress_apply is True
    assert result.no_existing_progress_aggregate_mutation is True
    assert result.no_global_progress_mutation is True
    assert result.no_ranking_update is True
    assert result.no_retention_update is True
    assert result.no_scheduler_update is True
    assert result.no_study_cycle_update is True
    assert result.no_curriculum_graph_update is True
    assert result.no_adaptive_tuning_update is True
    assert result.final_event_applied_globally is False
    assert result.existing_progress_aggregate_mutated is False
    assert result.global_progress_mutation_applied is False
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
    assert result.runtime_application_enabled is False
    assert result.runtime_application_applied is False


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
    assert "ranking_update_payload" not in dumped_keys
    assert "scheduler_update_payload" not in dumped_keys
    assert "retention_update_payload" not in dumped_keys
    assert "study_cycle_update_payload" not in dumped_keys
    assert "curriculum_graph_update_payload" not in dumped_keys
    assert "adaptive_tuning_payload" not in dumped_keys


def test_controlled_propagation_apply_handles_missing_or_blocked_source_guardrail_safely(
    tmp_path,
):
    missing = missing_propagation_guardrail_fixture(tmp_path / "missing")
    blocked = source_guardrail_blocked_fixture(tmp_path / "blocked")
    not_ready = source_guardrail_not_ready_fixture(tmp_path / "not-ready")
    unsafe_state = source_guardrail_unsafe_state_fixture(tmp_path / "unsafe-state")
    no_targets = no_candidate_targets_fixture(tmp_path / "no-targets")
    unsafe = unsafe_public_exposure_fixture(tmp_path / "unsafe")

    assert build_controlled_propagation_apply(missing) is None
    assert missing.context.repository.list_user_simulado_controlled_propagation_applies(
        user_id=missing.context.user_id
    ) == []

    blocked_result = build_controlled_propagation_apply(blocked)
    not_ready_result = build_controlled_propagation_apply(not_ready)
    unsafe_state_result = build_controlled_propagation_apply(unsafe_state)
    no_targets_result = build_controlled_propagation_apply(no_targets)
    unsafe_result = build_controlled_propagation_apply(unsafe)

    assert blocked_result is not None
    assert (
        blocked_result.readiness_state
        == "blocked_by_guardrail_not_ready_for_future_review"
    )
    assert blocked_result.controlled_propagation_apply_created is True
    assert blocked_result.controlled_propagation_ledger_recorded is False
    assert blocked_result.controlled_propagation_entry_created is False
    assert blocked_result.controlled_propagation_entry_count == 0
    _assert_no_runtime_mutation(blocked_result)

    assert not_ready_result is not None
    assert (
        not_ready_result.readiness_state
        == "blocked_by_guardrail_not_ready_for_future_review"
    )
    assert not_ready_result.controlled_propagation_entry_count == 0

    assert unsafe_state_result is not None
    assert (
        unsafe_state_result.readiness_state
        == "blocked_by_source_guardrail_state_unsafe"
    )
    assert unsafe_state_result.controlled_propagation_entry_count == 0

    assert no_targets_result is not None
    assert (
        no_targets_result.readiness_state
        == "blocked_by_no_candidate_propagation_targets"
    )
    assert no_targets_result.controlled_propagation_entry_count == 0

    assert unsafe_result is not None
    assert (
        unsafe_result.readiness_state
        == "blocked_by_public_answer_key_exposure_forbidden"
    )
    assert unsafe_result.controlled_propagation_entry_count == 0
    _assert_no_leakage(unsafe_result)


def test_controlled_propagation_apply_records_safe_source_to_controlled_ledger_only(
    tmp_path,
):
    fixture = safe_source_guardrail_fixture(tmp_path)
    result = build_controlled_propagation_apply(fixture)

    assert result is not None
    assert result.apply_mode == "controlled_propagation_apply"
    assert result.apply_status == "controlled_propagation_ledger_recorded"
    assert result.readiness_state == "controlled_propagation_ledger_recorded"
    assert result.controlled_propagation_apply_created is True
    assert result.controlled_propagation_allowed is True
    assert result.controlled_propagation_applied is True
    assert result.controlled_propagation_ledger_recorded is True
    assert result.controlled_propagation_entry_created is True
    assert result.controlled_propagation_entry_count > 0
    assert result.source_guardrail_present is True
    assert result.source_guardrail_ready_for_future_review is True
    assert result.source_propagation_allowed_now is False
    assert result.source_propagation_applied is False
    assert result.source_candidate_target_count == result.controlled_propagation_entry_count
    assert result.idempotency_key_required is True
    assert result.idempotency_key_present is True
    assert result.idempotency_key_valid is True
    assert result.idempotency_key_recorded is True
    assert result.rollback_required is True
    assert result.rollback_reference_created is True
    assert result.rollback_executed is False
    _assert_no_runtime_mutation(result)
    _assert_no_leakage(result)

    assert result.apply_summary.source_guardrail_present is True
    assert result.apply_summary.source_candidate_target_count == result.source_candidate_target_count
    assert result.apply_summary.controlled_entry_count == result.controlled_propagation_entry_count
    assert result.apply_summary.controlled_propagation_ledger_recorded is True
    assert result.apply_summary.direct_runtime_propagation_performed is False

    assert result.source_guardrail_summary.propagation_ready_for_future_review is True
    assert result.source_guardrail_summary.propagation_allowed_now is False
    assert result.source_guardrail_summary.propagation_applied is False
    assert result.source_guardrail_summary.no_propagation is True
    assert result.source_guardrail_summary.no_runtime_updates is True

    seen_surfaces = {item.propagation_surface for item in result.controlled_propagation_entries}
    assert SURFACES.issubset(seen_surfaces)
    for item in result.controlled_propagation_entries:
        assert item.user_id == fixture.context.user_id
        assert item.source_propagation_guardrail_id == result.source_propagation_guardrail_id
        assert item.source_candidate_target_id
        assert item.source_event_record_id
        assert item.propagation_surface in SURFACES
        assert item.recorded is True
        assert item.applied_to_controlled_ledger is True
        assert item.applied_to_runtime_surface is False
        assert isinstance(item.bounded_propagation_summary, dict)

    audit_events = {entry.event_type for entry in result.audit_trail}
    assert "controlled_propagation_apply_created" in audit_events
    assert "source_propagation_guardrail_evaluated" in audit_events
    assert "controlled_propagation_ledger_recorded" in audit_events
    assert "no_direct_runtime_propagation" in audit_events
    assert "no_scheduler_update" in audit_events


def test_controlled_propagation_apply_is_idempotent_and_preserves_source_artifacts(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = idempotency_replay_fixture(tmp_path, repository=repository)
    service = SimuladoControlledPropagationApplyService(repository)
    source_guardrail = fixture.propagation_guardrail
    assert source_guardrail is not None

    before = capture_controlled_propagation_apply_source_snapshot(fixture)
    first = build_controlled_propagation_apply(fixture)
    middle = capture_controlled_propagation_apply_source_snapshot(fixture)
    second = build_controlled_propagation_apply(fixture)
    loaded = service.get_controlled_propagation_apply(
        source_guardrail.propagation_guardrail_id,
        user_id=fixture.context.user_id,
    )
    loaded_by_id = service.get_controlled_propagation_apply_by_id(
        first.controlled_propagation_apply_id if first is not None else "missing",
        user_id=fixture.context.user_id,
    )
    after = capture_controlled_propagation_apply_source_snapshot(fixture)

    assert first is not None
    assert second is not None
    assert loaded is not None
    assert loaded_by_id is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert loaded.model_dump(mode="json") == loaded_by_id.model_dump(mode="json")
    assert first.replay_returns_existing_apply is True
    assert first.duplicate_controlled_apply_detected is False
    assert before.propagation_guardrail == middle.propagation_guardrail == after.propagation_guardrail
    assert before.applied_event_ledger == middle.applied_event_ledger == after.applied_event_ledger
    assert before.minimal_apply == middle.minimal_apply == after.minimal_apply
    assert before.runtime_apply_policy == middle.runtime_apply_policy == after.runtime_apply_policy
    assert before.final_event == middle.final_event == after.final_event
    assert before.controlled_execution == middle.controlled_execution == after.controlled_execution
    assert before.execution_plan == middle.execution_plan == after.execution_plan
    assert before.progress == middle.progress == after.progress
    assert before.propagation_guardrail_count == 1
    assert before.controlled_propagation_apply_count == 0
    assert middle.controlled_propagation_apply_count == 1
    assert after.controlled_propagation_apply_count == 1
