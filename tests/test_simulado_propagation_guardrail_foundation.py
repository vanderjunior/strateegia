import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_propagation_guardrail import SimuladoPropagationGuardrailService
from tests.fixtures.simulado_propagation_guardrails import (
    blocked_source_ledger_fixture,
    build_propagation_guardrail,
    capture_propagation_guardrail_source_snapshot,
    final_event_globally_applied_fixture,
    missing_applied_event_ledger_fixture,
    source_ledger_missing_deduplication_fixture,
    source_ledger_not_replay_safe_fixture,
    source_ledger_propagation_state_unsafe_fixture,
    source_progress_mutation_detected_fixture,
    successful_source_ledger_fixture,
    unsafe_public_exposure_fixture,
    zero_source_event_records_fixture,
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
    "ranking": "ranking_signal_candidate",
    "retention": "retention_signal_candidate",
    "scheduler": "scheduler_signal_candidate",
    "study_cycle": "study_cycle_signal_candidate",
    "curriculum_graph": "curriculum_graph_signal_candidate",
    "adaptive_tuning": "adaptive_tuning_signal_candidate",
}


def _assert_no_propagation(result) -> None:
    assert result.propagation_allowed_now is False
    assert result.propagation_applied is False
    assert result.ranking_propagation_allowed is False
    assert result.ranking_update_enabled is False
    assert result.ranking_update_applied is False
    assert result.retention_propagation_allowed is False
    assert result.retention_update_enabled is False
    assert result.retention_update_applied is False
    assert result.scheduler_propagation_allowed is False
    assert result.scheduler_update_enabled is False
    assert result.scheduler_update_applied is False
    assert result.study_cycle_propagation_allowed is False
    assert result.study_cycle_update_enabled is False
    assert result.study_cycle_update_applied is False
    assert result.curriculum_graph_propagation_allowed is False
    assert result.curriculum_graph_update_enabled is False
    assert result.curriculum_graph_update_applied is False
    assert result.adaptive_tuning_propagation_allowed is False
    assert result.adaptive_tuning_enabled is False
    assert result.adaptive_tuning_applied is False
    assert result.no_new_progress_apply is True
    assert result.no_propagation is True
    assert result.no_ranking_update is True
    assert result.no_retention_update is True
    assert result.no_scheduler_update is True
    assert result.no_study_cycle_update is True
    assert result.no_curriculum_graph_update is True
    assert result.no_adaptive_tuning_update is True
    assert result.final_event_applied_globally is False
    assert result.existing_progress_aggregate_mutated is False
    assert result.global_progress_mutation_applied is False
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


def test_propagation_guardrail_handles_missing_or_blocked_source_ledger_safely(tmp_path):
    missing = missing_applied_event_ledger_fixture(tmp_path / "missing")
    blocked = blocked_source_ledger_fixture(tmp_path / "blocked")
    zero_events = zero_source_event_records_fixture(tmp_path / "zero-events")
    not_replay_safe = source_ledger_not_replay_safe_fixture(tmp_path / "replay-unsafe")
    missing_dedup = source_ledger_missing_deduplication_fixture(tmp_path / "dedup-missing")
    propagation_unsafe = source_ledger_propagation_state_unsafe_fixture(
        tmp_path / "propagation-unsafe"
    )
    final_event_global = final_event_globally_applied_fixture(tmp_path / "final-event-global")
    progress_mutation = source_progress_mutation_detected_fixture(tmp_path / "progress-mutation")
    unsafe = unsafe_public_exposure_fixture(tmp_path / "unsafe")

    assert build_propagation_guardrail(missing) is None
    assert missing.context.repository.list_user_simulado_propagation_guardrails(
        user_id=missing.context.user_id
    ) == []

    blocked_result = build_propagation_guardrail(blocked)
    zero_events_result = build_propagation_guardrail(zero_events)
    not_replay_safe_result = build_propagation_guardrail(not_replay_safe)
    missing_dedup_result = build_propagation_guardrail(missing_dedup)
    propagation_unsafe_result = build_propagation_guardrail(propagation_unsafe)
    final_event_global_result = build_propagation_guardrail(final_event_global)
    progress_mutation_result = build_propagation_guardrail(progress_mutation)
    unsafe_result = build_propagation_guardrail(unsafe)

    assert blocked_result is not None
    assert blocked_result.readiness_state == "blocked_by_source_ledger_not_recorded"
    assert blocked_result.propagation_guardrail_created is True
    assert blocked_result.propagation_applied is False
    _assert_no_propagation(blocked_result)

    assert zero_events_result is not None
    assert zero_events_result.readiness_state == "blocked_by_no_source_event_records"
    assert zero_events_result.propagation_applied is False

    assert not_replay_safe_result is not None
    assert not_replay_safe_result.readiness_state == "blocked_by_source_ledger_not_replay_safe"
    assert not_replay_safe_result.propagation_applied is False

    assert missing_dedup_result is not None
    assert (
        missing_dedup_result.readiness_state
        == "blocked_by_source_ledger_deduplication_missing"
    )
    assert missing_dedup_result.propagation_applied is False

    assert propagation_unsafe_result is not None
    assert (
        propagation_unsafe_result.readiness_state
        == "blocked_by_source_ledger_propagation_state_unsafe"
    )
    assert propagation_unsafe_result.propagation_applied is False

    assert final_event_global_result is not None
    assert (
        final_event_global_result.readiness_state
        == "blocked_by_final_event_already_globally_applied"
    )

    assert progress_mutation_result is not None
    assert (
        progress_mutation_result.readiness_state
        == "blocked_by_source_progress_mutation_detected"
    )

    assert unsafe_result is not None
    assert unsafe_result.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    _assert_no_leakage(unsafe_result)


def test_propagation_guardrail_creates_candidate_targets_for_safe_source_ledger(tmp_path):
    fixture = successful_source_ledger_fixture(tmp_path)
    result = build_propagation_guardrail(fixture)

    assert result is not None
    assert result.guardrail_mode == "propagation_guardrail_only"
    assert result.guardrail_status == "propagation_ready_for_future_review"
    assert result.readiness_state == "propagation_ready_for_future_review"
    assert result.propagation_guardrail_created is True
    assert result.propagation_ready_for_future_review is True
    assert result.source_ledger_present is True
    assert result.source_ledger_recorded is True
    assert result.source_ledger_event_count > 0
    assert result.source_ledger_replay_safe is True
    assert result.source_ledger_deduplication_enforced is True
    assert result.source_ledger_no_propagation is True
    _assert_no_propagation(result)
    _assert_no_leakage(result)

    assert result.readiness_summary.source_ledger_present is True
    assert result.readiness_summary.source_ledger_recorded is True
    assert result.readiness_summary.source_ledger_event_count == result.source_ledger_event_count
    assert result.readiness_summary.source_ledger_replay_safe is True
    assert result.readiness_summary.source_ledger_deduplication_enforced is True
    assert result.readiness_summary.source_ledger_no_propagation is True
    assert result.readiness_summary.propagation_allowed_now is False
    assert result.readiness_summary.propagation_ready_for_future_review is True

    assert result.source_ledger_summary.summary_id
    assert result.source_ledger_summary.source_apply_present is True
    assert result.source_ledger_summary.source_apply_applied is True
    assert result.source_ledger_summary.ledger_event_count == result.source_ledger_event_count

    candidate_lists = {
        "ranking": result.candidate_ranking_targets,
        "retention": result.candidate_retention_targets,
        "scheduler": result.candidate_scheduler_targets,
        "study_cycle": result.candidate_study_cycle_targets,
        "curriculum_graph": result.candidate_curriculum_graph_targets,
        "adaptive_tuning": result.candidate_adaptive_tuning_targets,
    }
    expected_count = result.source_ledger_event_count
    for surface, expected_kind in SURFACES.items():
        candidates = candidate_lists[surface]
        assert len(candidates) == expected_count
        for candidate in candidates:
            assert candidate.candidate is True
            assert candidate.propagation_allowed is False
            assert candidate.propagated is False
            assert candidate.propagation_surface == surface
            assert candidate.propagation_kind == expected_kind
            assert candidate.source_event_record_id
            assert candidate.source_applied_ledger_entry_id
            assert isinstance(candidate.bounded_signal_summary, dict)

    risk = result.surface_risk_summary
    assert risk.candidate_surface_count == len(SURFACES)
    assert risk.blocked_surface_count == len(SURFACES)
    assert risk.ranking_candidate_count == expected_count
    assert risk.retention_candidate_count == expected_count
    assert risk.scheduler_candidate_count == expected_count
    assert risk.study_cycle_candidate_count == expected_count
    assert risk.curriculum_graph_candidate_count == expected_count
    assert risk.adaptive_tuning_candidate_count == expected_count
    assert risk.propagation_allowed_surface_count == 0
    assert risk.propagated_surface_count == 0
    assert risk.no_propagation is True

    audit_events = {entry.event_type for entry in result.audit_trail}
    assert "propagation_guardrail_created" in audit_events
    assert "propagation_ready_for_future_review" in audit_events
    assert "no_propagation" in audit_events
    assert "no_ranking_update" in audit_events
    assert "no_retention_update" in audit_events
    assert "no_scheduler_update" in audit_events
    assert "no_study_cycle_update" in audit_events
    assert "no_curriculum_graph_update" in audit_events
    assert "no_adaptive_tuning_update" in audit_events


def test_propagation_guardrail_is_idempotent_and_preserves_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = successful_source_ledger_fixture(tmp_path, repository=repository)
    service = SimuladoPropagationGuardrailService(repository)
    source_ledger = fixture.applied_event_ledger
    assert source_ledger is not None

    before = capture_propagation_guardrail_source_snapshot(fixture)
    first = build_propagation_guardrail(fixture)
    middle = capture_propagation_guardrail_source_snapshot(fixture)
    second = build_propagation_guardrail(fixture)
    loaded = service.get_propagation_guardrail(
        source_ledger.applied_event_ledger_id,
        user_id=fixture.context.user_id,
    )
    loaded_by_id = service.get_propagation_guardrail_by_id(
        first.propagation_guardrail_id if first is not None else "missing",
        user_id=fixture.context.user_id,
    )
    after = capture_propagation_guardrail_source_snapshot(fixture)

    assert first is not None
    assert second is not None
    assert loaded is not None
    assert loaded_by_id is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert loaded.model_dump(mode="json") == loaded_by_id.model_dump(mode="json")
    assert before.applied_event_ledger == middle.applied_event_ledger == after.applied_event_ledger
    assert before.minimal_apply == middle.minimal_apply == after.minimal_apply
    assert before.runtime_apply_policy == middle.runtime_apply_policy == after.runtime_apply_policy
    assert before.final_event == middle.final_event == after.final_event
    assert before.controlled_execution == middle.controlled_execution == after.controlled_execution
    assert before.execution_plan == middle.execution_plan == after.execution_plan
    assert before.progress == middle.progress == after.progress
    assert before.applied_event_ledger_count == 1
    assert before.propagation_guardrail_count == 0
    assert middle.propagation_guardrail_count == 1
    assert after.propagation_guardrail_count == 1
