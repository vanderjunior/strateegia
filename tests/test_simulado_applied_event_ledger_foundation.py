import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_applied_event_ledger import SimuladoAppliedEventLedgerService
from tests.fixtures.simulado_applied_event_ledgers import (
    blocked_source_apply_fixture,
    build_applied_event_ledger,
    capture_applied_event_ledger_source_snapshot,
    idempotency_replay_fixture,
    invalid_idempotency_fixture,
    missing_idempotency_fixture,
    missing_minimal_progress_ledger_apply_fixture,
    no_source_applied_entries_fixture,
    successful_source_apply_fixture,
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


def _assert_no_propagation(result) -> None:
    assert result.no_propagation is True
    assert result.no_new_progress_apply is True
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
    assert "final_question_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys
    assert "ranking_update_payload" not in dumped_keys
    assert "scheduler_update_payload" not in dumped_keys


def test_applied_event_ledger_handles_missing_or_blocked_source_apply_safely(tmp_path):
    missing = missing_minimal_progress_ledger_apply_fixture(tmp_path / "missing")
    blocked = blocked_source_apply_fixture(tmp_path / "blocked")
    no_entries = no_source_applied_entries_fixture(tmp_path / "no-entries")
    missing_idem = missing_idempotency_fixture(tmp_path / "missing-idem")
    invalid_idem = invalid_idempotency_fixture(tmp_path / "invalid-idem")
    unsafe = unsafe_public_exposure_fixture(tmp_path / "unsafe")

    assert build_applied_event_ledger(missing) is None
    assert missing.context.repository.list_user_simulado_applied_event_ledgers(
        user_id=missing.context.user_id
    ) == []

    blocked_result = build_applied_event_ledger(blocked)
    no_entries_result = build_applied_event_ledger(no_entries)
    missing_idem_result = build_applied_event_ledger(missing_idem)
    invalid_idem_result = build_applied_event_ledger(invalid_idem)
    unsafe_result = build_applied_event_ledger(unsafe)

    assert blocked_result is not None
    assert blocked_result.readiness_state == "blocked_by_source_apply_not_applied"
    assert blocked_result.applied_event_ledger_created is True
    assert blocked_result.ledger_event_recorded is False
    assert blocked_result.ledger_event_count == 0
    _assert_no_propagation(blocked_result)

    assert no_entries_result is not None
    assert no_entries_result.readiness_state == "blocked_by_no_source_applied_entries"
    assert no_entries_result.ledger_event_recorded is False
    assert no_entries_result.ledger_event_count == 0

    assert missing_idem_result is not None
    assert missing_idem_result.readiness_state == "blocked_by_idempotency_key_missing"
    assert missing_idem_result.ledger_event_recorded is False

    assert invalid_idem_result is not None
    assert invalid_idem_result.readiness_state == "blocked_by_idempotency_key_invalid"
    assert invalid_idem_result.ledger_event_recorded is False

    assert unsafe_result is not None
    assert unsafe_result.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    assert unsafe_result.ledger_event_recorded is False
    _assert_no_leakage(unsafe_result)


def test_applied_event_ledger_records_successful_source_apply_without_new_progress_apply(tmp_path):
    fixture = successful_source_apply_fixture(tmp_path)
    result = build_applied_event_ledger(fixture)

    assert result is not None
    assert result.ledger_mode == "applied_event_ledger"
    assert result.ledger_status == "ledger_recorded"
    assert result.readiness_state == "applied_event_ledger_recorded"
    assert result.applied_event_ledger_created is True
    assert result.ledger_event_recorded is True
    assert result.ledger_event_count > 0
    assert result.source_minimal_progress_ledger_apply_present is True
    assert result.source_minimal_progress_ledger_apply_applied is True
    assert result.source_applied_progress_ledger_entry_count > 0
    assert result.idempotency_key_required is True
    assert result.idempotency_key_present is True
    assert result.idempotency_key_valid is True
    assert result.idempotency_key_recorded is True
    assert result.deduplication_enforced is True
    assert result.duplicate_event_detected is False
    assert result.duplicate_source_apply_detected is False
    assert result.replay_safe is True
    assert result.replay_returns_existing_ledger is True
    assert result.rollback_required is True
    assert result.rollback_reference_preserved is True
    assert result.rollback_executed is False
    assert result.minimal_progress_ledger_apply_applied is True
    assert result.applied_progress_ledger_entry_created is True
    assert result.final_event_applied_to_minimal_ledger is True
    assert result.final_event_applied_globally is False
    _assert_no_propagation(result)
    _assert_no_leakage(result)

    assert result.ledger_summary.source_apply_present is True
    assert result.ledger_summary.source_apply_applied is True
    assert result.ledger_summary.ledger_event_count == len(result.applied_event_records)
    assert result.ledger_summary.idempotency_satisfied is True
    assert result.ledger_summary.deduplication_enforced is True
    assert result.ledger_summary.replay_safe is True

    for record in result.applied_event_records:
        assert record.user_id == fixture.context.user_id
        assert record.source_minimal_progress_ledger_apply_id == result.source_minimal_progress_ledger_apply_id
        assert record.source_runtime_apply_policy_id == result.source_runtime_apply_policy_id
        assert record.source_final_event_id == result.source_final_event_id
        assert record.source_applied_progress_ledger_entry_id
        assert record.event_scope == "minimal_progress_ledger"
        assert record.recorded is True
        assert record.applied_elsewhere is False
        assert isinstance(record.bounded_event_summary, dict)


def test_applied_event_ledger_is_idempotent_and_preserves_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = idempotency_replay_fixture(tmp_path, repository=repository)
    service = SimuladoAppliedEventLedgerService(repository)
    source_apply = fixture.minimal_apply
    assert source_apply is not None

    before = capture_applied_event_ledger_source_snapshot(fixture)
    first = build_applied_event_ledger(fixture)
    middle = capture_applied_event_ledger_source_snapshot(fixture)
    second = build_applied_event_ledger(fixture)
    loaded = service.get_applied_event_ledger(
        source_apply.minimal_progress_ledger_apply_id,
        user_id=fixture.context.user_id,
    )
    loaded_by_id = service.get_applied_event_ledger_by_id(
        first.applied_event_ledger_id if first is not None else "missing",
        user_id=fixture.context.user_id,
    )
    after = capture_applied_event_ledger_source_snapshot(fixture)

    assert first is not None
    assert second is not None
    assert loaded is not None
    assert loaded_by_id is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert loaded.model_dump(mode="json") == loaded_by_id.model_dump(mode="json")
    assert first.replay_safe is True
    assert first.replay_count == 0
    assert first.replay_returns_existing_ledger is True
    assert first.duplicate_event_detected is False
    assert first.deduplication_record.event_count_after_deduplication == len(first.applied_event_records)
    assert before.minimal_apply == middle.minimal_apply == after.minimal_apply
    assert before.runtime_apply_policy == middle.runtime_apply_policy == after.runtime_apply_policy
    assert before.final_event == middle.final_event == after.final_event
    assert before.controlled_execution == middle.controlled_execution == after.controlled_execution
    assert before.execution_plan == middle.execution_plan == after.execution_plan
    assert before.progress == middle.progress == after.progress
    assert before.minimal_progress_ledger_apply_count == 1
    assert before.applied_event_ledger_count == 0
    assert middle.applied_event_ledger_count == 1
    assert after.applied_event_ledger_count == 1
