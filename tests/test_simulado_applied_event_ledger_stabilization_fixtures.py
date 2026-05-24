import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_applied_event_ledger import SimuladoAppliedEventLedgerService
from tests.fixtures.simulado_applied_event_ledgers import (
    api_readonly_fixture,
    applied_event_records_shape_fixture,
    audit_trail_shape_fixture,
    build_applied_event_ledger,
    capture_applied_event_ledger_source_snapshot,
    deduplication_record_shape_fixture,
    idempotency_record_shape_fixture,
    mixed_ledger_fixture,
    missing_minimal_progress_ledger_apply_fixture,
    no_existing_progress_aggregate_mutation_fixture,
    no_global_progress_mutation_fixture,
    no_leakage_fixture,
    no_new_progress_apply_fixture,
    no_runtime_propagation_fixture,
    replay_safety_record_shape_fixture,
    rollback_reference_shape_fixture,
    source_apply_blocked_fixture,
    source_apply_invalid_idempotency_fixture,
    source_apply_missing_idempotency_fixture,
    source_apply_not_applied_fixture,
    source_apply_unsafe_public_exposure_fixture,
    source_apply_zero_entries_fixture,
    stabilization_fixture_builders,
    successful_source_apply_fixture,
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


def _assert_no_leakage(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(payload)
    for key in FORBIDDEN_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped
    assert "raw_document_body" not in dumped_keys
    assert "final_question_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys
    assert "ranking_update_payload" not in dumped_keys
    assert "retention_update_payload" not in dumped_keys
    assert "scheduler_update_payload" not in dumped_keys
    assert "study_cycle_update_payload" not in dumped_keys
    assert "curriculum_graph_update_payload" not in dumped_keys


def _assert_no_propagation(result) -> None:
    assert result.no_new_progress_apply is True
    assert result.no_propagation is True
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
    assert result.no_existing_progress_aggregate_mutation is True
    assert result.no_global_progress_mutation is True
    assert result.no_ranking_update is True
    assert result.no_retention_update is True
    assert result.no_scheduler_update is True
    assert result.no_study_cycle_update is True
    assert result.no_curriculum_graph_update is True
    assert result.no_adaptive_tuning_update is True


def _assert_runtime_controls_disabled(result) -> None:
    assert result.commit_executed is False
    assert result.mutation_committed is False
    assert result.runtime_application_enabled is False
    assert result.runtime_application_applied is False
    assert result.no_commit_execution is True
    assert result.no_mutation_commit is True
    assert result.no_runtime_application_beyond_minimal_ledger is True
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


def test_applied_event_ledger_stabilization_fixtures_are_deterministic_and_json_safe(
    tmp_path,
):
    builders = stabilization_fixture_builders()

    assert "successful_source_apply" in builders
    assert "mixed_ledger" in builders
    assert "no_leakage" in builders

    for name, builder in builders.items():
        fixture = builder(tmp_path / name)
        assert fixture.context.user_id
        assert fixture.context.service is not None
        if fixture.minimal_apply is not None:
            payload = fixture.minimal_apply.model_dump(mode="json")
            dumped = json.dumps(payload, ensure_ascii=True)
            assert "password_hash" not in dumped
            assert "data:image" not in dumped
            assert "raw_runtime_block" not in dumped
            assert len(dumped) < 200000


def test_applied_event_ledger_stabilization_covers_blocked_source_scenarios(tmp_path):
    scenarios = [
        (source_apply_blocked_fixture, "blocked_by_source_apply_not_applied"),
        (source_apply_not_applied_fixture, "blocked_by_source_apply_not_applied"),
        (source_apply_zero_entries_fixture, "blocked_by_no_source_applied_entries"),
        (
            source_apply_missing_idempotency_fixture,
            "blocked_by_idempotency_key_missing",
        ),
        (
            source_apply_invalid_idempotency_fixture,
            "blocked_by_idempotency_key_invalid",
        ),
        (
            source_apply_unsafe_public_exposure_fixture,
            "blocked_by_public_answer_key_exposure_forbidden",
        ),
        (mixed_ledger_fixture, "blocked_by_idempotency_key_invalid"),
    ]

    missing = missing_minimal_progress_ledger_apply_fixture(tmp_path / "missing")
    assert build_applied_event_ledger(missing) is None
    assert missing.context.repository.list_user_simulado_applied_event_ledgers(
        user_id=missing.context.user_id
    ) == []

    for index, (builder, expected_readiness) in enumerate(scenarios):
        result = build_applied_event_ledger(builder(tmp_path / f"scenario-{index}"))
        assert result is not None
        assert result.applied_event_ledger_created is True
        assert result.readiness_state == expected_readiness
        assert result.ledger_event_recorded is False
        assert result.ledger_event_count == 0
        _assert_no_propagation(result)
        _assert_runtime_controls_disabled(result)


def test_applied_event_ledger_stabilization_covers_success_record_shape_and_replay(tmp_path):
    success = build_applied_event_ledger(successful_source_apply_fixture(tmp_path / "success"))
    records_shape = build_applied_event_ledger(
        applied_event_records_shape_fixture(tmp_path / "records")
    )
    idempotency = build_applied_event_ledger(
        idempotency_record_shape_fixture(tmp_path / "idempotency")
    )
    deduplication = build_applied_event_ledger(
        deduplication_record_shape_fixture(tmp_path / "deduplication")
    )
    replay_fixture = replay_safety_record_shape_fixture(tmp_path / "replay")
    first_replay = build_applied_event_ledger(replay_fixture)
    second_replay = build_applied_event_ledger(replay_fixture)
    rollback = build_applied_event_ledger(
        rollback_reference_shape_fixture(tmp_path / "rollback")
    )
    audit = build_applied_event_ledger(audit_trail_shape_fixture(tmp_path / "audit"))

    assert success is not None
    assert success.applied_event_ledger_created is True
    assert success.ledger_event_recorded is True
    assert success.ledger_event_count > 0
    assert success.source_minimal_progress_ledger_apply_present is True
    assert success.source_minimal_progress_ledger_apply_applied is True
    assert success.source_applied_progress_ledger_entry_count > 0
    assert success.deduplication_enforced is True
    assert success.replay_safe is True
    _assert_no_propagation(success)
    _assert_runtime_controls_disabled(success)

    assert records_shape is not None
    for record in records_shape.applied_event_records:
        assert record.recorded is True
        assert record.event_scope == "minimal_progress_ledger"
        assert record.applied_elsewhere is False
        assert record.user_id == records_shape.user_id
        assert record.source_minimal_progress_ledger_apply_id
        assert record.source_runtime_apply_policy_id
        assert record.source_final_event_id
        assert record.source_applied_progress_ledger_entry_id
        assert record.event_type == "minimal_progress_ledger_apply_recorded"
        assert record.target_type in {
            "simulado_attempt",
            "simulado_score",
            "simulado_completion",
            "topic_signal",
            "unknown",
        }
        assert isinstance(record.bounded_event_summary, dict)
        assert len(record.bounded_event_summary) <= 4
        _assert_no_leakage(record.model_dump(mode="json"))

    assert idempotency is not None
    assert idempotency.idempotency_record.idempotency_key_required is True
    assert idempotency.idempotency_record.idempotency_key_present is True
    assert idempotency.idempotency_record.idempotency_key_valid is True
    assert idempotency.idempotency_record.idempotency_key == idempotency.idempotency_key
    assert (
        idempotency.idempotency_record.source_minimal_progress_ledger_apply_id
        == idempotency.source_minimal_progress_ledger_apply_id
    )
    assert (
        idempotency.idempotency_record.source_runtime_apply_policy_id
        == idempotency.source_runtime_apply_policy_id
    )
    assert idempotency.idempotency_record.satisfied is True

    assert deduplication is not None
    assert deduplication.deduplication_record.deduplication_enforced is True
    assert deduplication.deduplication_record.deduplication_key
    assert deduplication.deduplication_record.duplicate_source_apply_detected is False
    assert deduplication.deduplication_record.duplicate_event_detected is False
    assert deduplication.deduplication_record.previous_ledger_id is None
    assert (
        deduplication.deduplication_record.event_count_after_deduplication
        == len(deduplication.applied_event_records)
    )
    seen_source_entry_ids = {
        record.source_applied_progress_ledger_entry_id
        for record in deduplication.applied_event_records
    }
    assert len(seen_source_entry_ids) == len(deduplication.applied_event_records)

    assert first_replay is not None
    assert second_replay is not None
    assert first_replay.model_dump(mode="json") == second_replay.model_dump(mode="json")
    assert first_replay.replay_safe is True
    assert first_replay.replay_returns_existing_ledger is True
    assert first_replay.replay_safety_record.same_source_same_key_idempotent is True
    assert first_replay.replay_safety_record.no_duplicate_event_records is True
    assert first_replay.replay_count == 0

    assert rollback is not None
    assert rollback.rollback_reference.rollback_required is True
    assert rollback.rollback_reference.rollback_reference_preserved is True
    assert rollback.rollback_reference.rollback_scope == "minimal_progress_ledger"
    assert rollback.rollback_reference.rollback_executed is False
    assert isinstance(rollback.rollback_reference.rollback_summary, dict)

    assert audit is not None
    audit_events = {entry.event_type for entry in audit.audit_trail}
    assert "applied_event_ledger_created" in audit_events
    assert "applied_event_recorded" in audit_events
    assert "idempotency_key_recorded" in audit_events
    assert "deduplication_enforced" in audit_events
    assert "replay_safe" in audit_events
    assert "rollback_reference_preserved" in audit_events
    assert "no_new_progress_apply" in audit_events
    assert "no_global_progress_mutation" in audit_events
    assert "no_existing_progress_aggregate_mutation" in audit_events
    assert "no_ranking_update" in audit_events
    assert "no_retention_update" in audit_events
    assert "no_scheduler_update" in audit_events
    assert "no_study_cycle_update" in audit_events
    assert "no_curriculum_graph_update" in audit_events
    assert "no_adaptive_tuning_update" in audit_events
    assert "no_commit_execution" in audit_events
    assert "no_mutation_commit" in audit_events
    assert "no_runtime_application_beyond_minimal_ledger" in audit_events


def test_applied_event_ledger_stabilization_preserves_sources_and_prevents_new_apply(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = no_new_progress_apply_fixture(tmp_path / "no-new-apply", repository=repository)
    before = capture_applied_event_ledger_source_snapshot(fixture)
    result = build_applied_event_ledger(fixture)
    middle = capture_applied_event_ledger_source_snapshot(fixture)
    loaded = SimuladoAppliedEventLedgerService(repository).get_applied_event_ledger(
        result.source_minimal_progress_ledger_apply_id if result is not None else "missing",
        user_id=fixture.context.user_id,
    )
    after = capture_applied_event_ledger_source_snapshot(fixture)

    assert result is not None
    assert loaded is not None
    assert result.no_new_progress_apply is True
    assert before.minimal_apply == middle.minimal_apply == after.minimal_apply
    assert before.runtime_apply_policy == middle.runtime_apply_policy == after.runtime_apply_policy
    assert before.final_event == middle.final_event == after.final_event
    assert before.controlled_execution == middle.controlled_execution == after.controlled_execution
    assert before.execution_plan == middle.execution_plan == after.execution_plan
    assert before.progress == middle.progress == after.progress
    assert before.minimal_progress_ledger_apply_count == 1
    assert middle.minimal_progress_ledger_apply_count == 1
    assert after.minimal_progress_ledger_apply_count == 1
    assert before.applied_event_ledger_count == 0
    assert middle.applied_event_ledger_count == 1
    assert after.applied_event_ledger_count == 1

    no_global = build_applied_event_ledger(
        no_global_progress_mutation_fixture(tmp_path / "no-global")
    )
    no_existing = build_applied_event_ledger(
        no_existing_progress_aggregate_mutation_fixture(tmp_path / "no-existing")
    )
    no_runtime = build_applied_event_ledger(
        no_runtime_propagation_fixture(tmp_path / "no-runtime")
    )
    assert no_global is not None
    assert no_existing is not None
    assert no_runtime is not None
    for item in (result, no_global, no_existing, no_runtime):
        _assert_no_propagation(item)
        _assert_runtime_controls_disabled(item)
        assert item.final_event_applied_globally is False


def test_applied_event_ledger_stabilization_api_owner_only_read_only_and_persistent(
    tmp_path,
):
    owner, other, anonymous, repository = _create_clients(tmp_path)
    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")

    blocked_fixture = source_apply_blocked_fixture(
        tmp_path / "blocked",
        user_id=owner_user_id,
        repository=repository,
    )
    assert blocked_fixture.minimal_apply is not None
    blocked_apply_id = blocked_fixture.minimal_apply.minimal_progress_ledger_apply_id

    api_fixture = api_readonly_fixture(
        tmp_path / "readonly",
        user_id=owner_user_id,
        repository=repository,
    )
    assert api_fixture.minimal_apply is not None
    success_apply_id = api_fixture.minimal_apply.minimal_progress_ledger_apply_id

    missing = owner.get(
        f"/api/simulado-minimal-progress-ledger-apply/{success_apply_id}/applied-event-ledger"
    )
    blocked_first = owner.post(
        f"/api/simulado-minimal-progress-ledger-apply/{blocked_apply_id}/applied-event-ledger/build"
    )
    blocked_second = owner.post(
        f"/api/simulado-minimal-progress-ledger-apply/{blocked_apply_id}/applied-event-ledger/build"
    )
    before_success = repository.get_simulado_minimal_progress_ledger_apply_by_id(
        success_apply_id,
        user_id=owner_user_id,
    )
    success_first = owner.post(
        f"/api/simulado-minimal-progress-ledger-apply/{success_apply_id}/applied-event-ledger/build"
    )
    success_second = owner.post(
        f"/api/simulado-minimal-progress-ledger-apply/{success_apply_id}/applied-event-ledger/build"
    )
    by_source = owner.get(
        f"/api/simulado-minimal-progress-ledger-apply/{success_apply_id}/applied-event-ledger"
    )
    ledger_id = success_first.json()["applied_event_ledger_id"]
    by_id = owner.get(f"/api/simulado-applied-event-ledger/{ledger_id}")
    after_success = repository.get_simulado_minimal_progress_ledger_apply_by_id(
        success_apply_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert blocked_first.status_code == 200
    assert blocked_second.status_code == 200
    assert blocked_first.json() == blocked_second.json()
    assert blocked_first.json()["ledger_event_recorded"] is False
    assert blocked_first.json()["ledger_event_count"] == 0

    assert before_success is not None
    assert success_first.status_code == 200
    assert success_second.status_code == 200
    assert success_first.json() == success_second.json()
    assert by_source.status_code == 200
    assert by_id.status_code == 200
    assert after_success is not None
    assert before_success.model_dump(mode="json") == after_success.model_dump(mode="json")

    listed = repository.list_user_simulado_applied_event_ledgers(user_id=owner_user_id)
    expected_count = len({blocked_apply_id, success_apply_id})
    assert len(listed) == expected_count
    assert repository.get_simulado_applied_event_ledger(
        success_apply_id,
        user_id=owner_user_id,
    ) is not None
    assert repository.get_simulado_applied_event_ledger_by_id(
        ledger_id,
        user_id=owner_user_id,
    ) is not None

    assert anonymous.post(
        f"/api/simulado-minimal-progress-ledger-apply/{success_apply_id}/applied-event-ledger/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-minimal-progress-ledger-apply/{success_apply_id}/applied-event-ledger"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-applied-event-ledger/{ledger_id}").status_code == 401

    assert other.post(
        f"/api/simulado-minimal-progress-ledger-apply/{success_apply_id}/applied-event-ledger/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-minimal-progress-ledger-apply/{success_apply_id}/applied-event-ledger"
    ).status_code == 404
    assert other.get(f"/api/simulado-applied-event-ledger/{ledger_id}").status_code == 404


def test_applied_event_ledger_stabilization_prevents_leakage_in_service_and_api_payloads(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = no_leakage_fixture(tmp_path / "service", repository=repository)
    result = build_applied_event_ledger(fixture)
    assert result is not None
    _assert_no_leakage(result.model_dump(mode="json"))

    owner, _, _, api_repository = _create_clients(tmp_path / "api")
    owner_user_id = _register_and_login(owner, "owner")
    api_fixture = successful_source_apply_fixture(
        tmp_path / "api-fixture",
        user_id=owner_user_id,
        repository=api_repository,
    )
    assert api_fixture.minimal_apply is not None
    response = owner.post(
        f"/api/simulado-minimal-progress-ledger-apply/{api_fixture.minimal_apply.minimal_progress_ledger_apply_id}/applied-event-ledger/build"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer_key_publicly_exposed"] is False
    assert payload["gabarito_publicly_exposed"] is False
    _assert_no_leakage(payload)
