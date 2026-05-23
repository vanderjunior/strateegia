import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_minimal_progress_ledger_apply import (
    SimuladoMinimalProgressLedgerApplyService,
)
from tests.fixtures.simulado_minimal_progress_ledger_applies import (
    allowed_policy_success_fixture,
    applied_ledger_entries_shape_fixture,
    api_readonly_fixture,
    audit_trail_shape_fixture,
    build_minimal_progress_ledger_apply,
    capture_minimal_apply_source_snapshot,
    idempotency_replay_fixture,
    mixed_apply_fixture,
    missing_runtime_apply_policy_fixture,
    no_existing_progress_aggregate_mutation_fixture,
    no_global_progress_mutation_fixture,
    no_leakage_fixture,
    no_proposed_progress_updates_fixture,
    no_runtime_propagation_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_record_shape_fixture,
    stabilization_fixture_builders,
    user_scope_fixture,
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
ALLOWED_TARGET_TYPES = {
    "simulado_attempt",
    "simulado_score",
    "simulado_completion",
    "topic_signal",
    "unknown",
}
ALLOWED_DELTA_KINDS = {
    "mastery_delta",
    "completion_delta",
    "accuracy_delta",
    "review_signal_delta",
    "confidence_delta",
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


def _assert_no_global_or_propagated_mutation(result) -> None:
    assert result.final_event_applied_globally is False
    assert result.existing_progress_aggregate_mutated is False
    assert result.global_progress_mutation_applied is False
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
    assert result.no_existing_progress_aggregate_mutation is True
    assert result.no_global_progress_mutation is True
    assert result.no_ranking_update is True
    assert result.no_retention_update is True
    assert result.no_scheduler_update is True
    assert result.no_study_cycle_update is True
    assert result.no_curriculum_graph_update is True
    assert result.no_adaptive_tuning_update is True


def _assert_runtime_controls_still_disabled(result) -> None:
    assert result.commit_executed is False
    assert result.mutation_committed is False
    assert result.runtime_application_enabled is False
    assert result.runtime_application_applied is False
    assert result.no_commit_execution is True
    assert result.no_mutation_commit is True
    assert result.no_runtime_application_beyond_minimal_ledger is True
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


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
    assert "final_question_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys
    assert "raw_document_body" not in dumped_keys
    assert "ranking_update_payload" not in dumped_keys
    assert "scheduler_update_payload" not in dumped_keys
    assert "retention_update_payload" not in dumped_keys
    assert "study_cycle_update_payload" not in dumped_keys
    assert "curriculum_graph_update_payload" not in dumped_keys


def test_minimal_progress_ledger_apply_stabilization_fixtures_are_deterministic_and_json_safe(
    tmp_path,
):
    builders = stabilization_fixture_builders()

    assert "allowed_policy_success" in builders
    assert "mixed_apply" in builders
    assert "no_leakage" in builders

    for name, builder in builders.items():
        fixture = builder(tmp_path / name)
        assert fixture.context.user_id
        assert fixture.context.service is not None
        if fixture.runtime_apply_policy is not None:
            payload = fixture.runtime_apply_policy.model_dump(mode="json")
            dumped = json.dumps(payload, ensure_ascii=True)
            assert "password_hash" not in dumped
            assert "data:image" not in dumped
            assert "raw_runtime_block" not in dumped
            assert len(dumped) < 200000


def test_minimal_progress_ledger_apply_stabilization_covers_blocked_policy_scenarios(tmp_path):
    scenarios = [
        ("feature_flag_disabled", "blocked_by_policy_feature_flag_disabled"),
        ("runtime_apply_not_allowed_now", "blocked_by_runtime_apply_not_allowed_now"),
        (
            "minimal_progress_ledger_scope_not_allowed",
            "blocked_by_minimal_progress_ledger_scope_not_allowed",
        ),
        ("idempotency_unsatisfied", "blocked_by_idempotency_requirement_unsatisfied"),
        ("rollback_unsatisfied", "blocked_by_rollback_requirement_unsatisfied"),
        ("audit_unsatisfied", "blocked_by_audit_requirement_unsatisfied"),
        (
            "human_review_unsatisfied",
            "blocked_by_human_review_requirement_unsatisfied",
        ),
        ("environment_unsafe", "blocked_by_environment_not_safe_for_apply"),
        (
            "public_answer_key_exposure_forbidden",
            "blocked_by_public_answer_key_exposure_forbidden",
        ),
        ("no_proposed_progress_updates", "blocked_by_no_proposed_progress_updates"),
    ]
    builders = stabilization_fixture_builders()

    assert build_minimal_progress_ledger_apply(missing_runtime_apply_policy_fixture(tmp_path / "missing")) is None

    for name, expected_code in scenarios:
        result = build_minimal_progress_ledger_apply(builders[name](tmp_path / name))
        assert result is not None
        assert result.minimal_progress_ledger_apply_created is True
        assert result.readiness_state == expected_code
        assert result.minimal_progress_ledger_apply_applied is False
        assert result.applied_progress_ledger_entry_created is False
        assert result.applied_progress_ledger_entry_count == 0
        assert result.final_event_applied_to_minimal_ledger is False
        assert result.final_event_applied_globally is False
        _assert_no_global_or_propagated_mutation(result)
        _assert_runtime_controls_still_disabled(result)


def test_minimal_progress_ledger_apply_stabilization_covers_success_entries_idempotency_rollback_and_audit(
    tmp_path,
):
    success = build_minimal_progress_ledger_apply(
        allowed_policy_success_fixture(tmp_path / "success")
    )
    entries_shape = build_minimal_progress_ledger_apply(
        applied_ledger_entries_shape_fixture(tmp_path / "entries")
    )
    replay_fixture = idempotency_replay_fixture(tmp_path / "replay")
    first_replay = build_minimal_progress_ledger_apply(replay_fixture)
    second_replay = build_minimal_progress_ledger_apply(replay_fixture)
    rollback = build_minimal_progress_ledger_apply(
        rollback_record_shape_fixture(tmp_path / "rollback")
    )
    audit = build_minimal_progress_ledger_apply(audit_trail_shape_fixture(tmp_path / "audit"))
    mixed = build_minimal_progress_ledger_apply(mixed_apply_fixture(tmp_path / "mixed"))

    assert success is not None
    assert success.minimal_progress_ledger_apply_created is True
    assert success.minimal_progress_ledger_apply_allowed is True
    assert success.minimal_progress_ledger_apply_applied is True
    assert success.applied_progress_ledger_entry_created is True
    assert success.applied_progress_ledger_entry_count > 0
    assert success.final_event_applied_to_minimal_ledger is True
    assert success.final_event_applied_globally is False
    _assert_no_global_or_propagated_mutation(success)
    _assert_runtime_controls_still_disabled(success)

    assert entries_shape is not None
    for entry in entries_shape.applied_ledger_entries:
        assert entry.applied is True
        assert entry.applied_scope == "minimal_progress_ledger"
        assert entry.user_id == entries_shape.user_id
        assert entry.source_final_event_id
        assert entry.source_policy_id == entries_shape.source_runtime_apply_policy_id
        assert entry.source_proposed_update_id
        assert entry.entry_type == "applied_progress_ledger_entry"
        assert entry.target_type in ALLOWED_TARGET_TYPES
        assert entry.delta_kind in ALLOWED_DELTA_KINDS
        assert isinstance(entry.bounded_delta_summary, dict)
        assert len(entry.bounded_delta_summary) <= 4
        dumped = json.dumps(entry.model_dump(mode="json"), ensure_ascii=True)
        assert "raw_runtime_block" not in dumped
        assert "answer_key" not in dumped
        assert "gabarito" not in dumped

    assert first_replay is not None
    assert second_replay is not None
    assert first_replay.model_dump(mode="json") == second_replay.model_dump(mode="json")
    assert first_replay.duplicate_apply_detected is False
    assert second_replay.duplicate_apply_detected is False
    assert first_replay.idempotency_record.duplicate_apply_detected is False
    assert second_replay.idempotency_record.previous_apply_id is None
    assert first_replay.applied_progress_ledger_entry_count == second_replay.applied_progress_ledger_entry_count

    assert rollback is not None
    assert rollback.rollback_required is True
    assert rollback.rollback_reference_created is True
    assert rollback.rollback_record.rollback_scope == "minimal_progress_ledger"
    assert rollback.rollback_executed is False
    assert isinstance(rollback.rollback_record.rollback_summary, dict)
    assert "snapshot" not in json.dumps(rollback.rollback_record.model_dump(mode="json"), ensure_ascii=True)

    assert audit is not None
    audit_events = {item.event_type for item in audit.audit_trail}
    assert "minimal_progress_ledger_apply_created" in audit_events
    assert "minimal_progress_ledger_apply_applied" in audit_events
    assert "idempotency_key_recorded" in audit_events
    assert "rollback_reference_created" in audit_events
    assert "no_global_progress_mutation" in audit_events
    assert "no_existing_progress_aggregate_mutation" in audit_events
    assert "no_ranking_update" in audit_events
    assert "no_retention_update" in audit_events
    assert "no_scheduler_update" in audit_events
    assert "no_study_cycle_update" in audit_events
    assert "no_curriculum_graph_update" in audit_events
    assert "no_adaptive_tuning_update" in audit_events
    assert "no_runtime_application_beyond_minimal_ledger" in audit_events

    assert mixed is not None
    assert mixed.readiness_state == "blocked_by_idempotency_requirement_unsatisfied"
    assert mixed.minimal_progress_ledger_apply_applied is False


def test_minimal_progress_ledger_apply_stabilization_preserves_sources_runtime_state_and_no_leakage(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    no_global = no_global_progress_mutation_fixture(
        tmp_path / "no-global",
        repository=repository,
    )
    no_existing = no_existing_progress_aggregate_mutation_fixture(
        tmp_path / "no-existing",
        repository=repository,
    )
    no_propagation = no_runtime_propagation_fixture(
        tmp_path / "no-propagation",
        repository=repository,
    )
    no_leakage = no_leakage_fixture(
        tmp_path / "no-leakage",
        repository=repository,
    )
    unsafe = public_answer_key_exposure_forbidden_fixture(
        tmp_path / "unsafe",
        repository=repository,
    )

    before = capture_minimal_apply_source_snapshot(no_global)
    result = build_minimal_progress_ledger_apply(no_global)
    after = capture_minimal_apply_source_snapshot(no_global)
    existing = build_minimal_progress_ledger_apply(no_existing)
    propagation = build_minimal_progress_ledger_apply(no_propagation)
    leakage = build_minimal_progress_ledger_apply(no_leakage)
    unsafe_result = build_minimal_progress_ledger_apply(unsafe)

    assert result is not None
    assert existing is not None
    assert propagation is not None
    assert leakage is not None
    assert unsafe_result is not None
    assert before.final_event == after.final_event
    assert before.controlled_execution == after.controlled_execution
    assert before.execution_plan == after.execution_plan
    assert before.execution_approval == after.execution_approval
    assert before.execution_guardrail == after.execution_guardrail
    assert before.runtime_apply_policy == after.runtime_apply_policy
    assert before.progress == after.progress
    assert before.minimal_progress_ledger_apply_count == 0
    assert after.minimal_progress_ledger_apply_count == 1

    assert result.existing_progress_aggregate_mutated is False
    assert result.global_progress_mutation_applied is False
    assert result.no_existing_progress_aggregate_mutation is True
    assert result.no_global_progress_mutation is True
    assert existing.existing_progress_aggregate_mutated is False
    assert propagation.ranking_update_applied is False
    assert propagation.retention_update_applied is False
    assert propagation.scheduler_update_applied is False
    assert propagation.study_cycle_update_applied is False
    assert propagation.curriculum_graph_update_applied is False
    assert propagation.adaptive_tuning_applied is False

    _assert_no_leakage(leakage.model_dump(mode="json"))
    _assert_no_leakage(unsafe_result.model_dump(mode="json"))


def test_minimal_progress_ledger_apply_stabilization_persistence_and_api_owner_scope_read_only_behavior(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = api_readonly_fixture(tmp_path / "fixture", repository=repository)
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    service = SimuladoMinimalProgressLedgerApplyService(repository)

    first = build_minimal_progress_ledger_apply(fixture)
    second = build_minimal_progress_ledger_apply(fixture)
    loaded = service.get_minimal_progress_ledger_apply(
        runtime_apply_policy.runtime_apply_policy_id,
        user_id=fixture.context.user_id,
    )
    loaded_by_id = service.get_minimal_progress_ledger_apply_by_id(
        first.minimal_progress_ledger_apply_id if first is not None else "missing",
        user_id=fixture.context.user_id,
    )

    assert first is not None
    assert second is not None
    assert loaded is not None
    assert loaded_by_id is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert loaded.model_dump(mode="json") == loaded_by_id.model_dump(mode="json")
    assert len(repository.list_user_simulado_minimal_progress_ledger_applies(user_id=fixture.context.user_id)) == 1
    _assert_no_leakage(loaded.model_dump(mode="json"))

    owner, other, anonymous, api_repository = _create_clients(tmp_path / "api")
    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    api_fixture = user_scope_fixture(
        tmp_path / "api-fixture",
        user_id=owner_user_id,
        repository=api_repository,
    )
    owner_policy = api_fixture.runtime_apply_policy
    assert owner_policy is not None

    missing = owner.get(
        f"/api/simulado-runtime-apply-policy/{owner_policy.runtime_apply_policy_id}/minimal-progress-ledger-apply"
    )
    before_policy = api_repository.get_simulado_runtime_apply_policy_by_id(
        owner_policy.runtime_apply_policy_id,
        user_id=owner_user_id,
    )
    before_final_event = api_repository.get_simulado_final_pedagogical_update_event_by_id(
        owner_policy.source_final_event_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-runtime-apply-policy/{owner_policy.runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
    )
    loaded_by_source = owner.get(
        f"/api/simulado-runtime-apply-policy/{owner_policy.runtime_apply_policy_id}/minimal-progress-ledger-apply"
    )
    apply_id = build.json()["minimal_progress_ledger_apply_id"]
    by_id = owner.get(f"/api/simulado-minimal-progress-ledger-apply/{apply_id}")
    after_policy = api_repository.get_simulado_runtime_apply_policy_by_id(
        owner_policy.runtime_apply_policy_id,
        user_id=owner_user_id,
    )
    after_final_event = api_repository.get_simulado_final_pedagogical_update_event_by_id(
        owner_policy.source_final_event_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded_by_source.status_code == 200
    assert by_id.status_code == 200
    assert build.json() == loaded_by_source.json() == by_id.json()
    assert before_policy is not None
    assert after_policy is not None
    assert before_final_event is not None
    assert after_final_event is not None
    assert before_policy.model_dump(mode="json") == after_policy.model_dump(mode="json")
    assert before_final_event.model_dump(mode="json") == after_final_event.model_dump(mode="json")
    assert len(
        api_repository.list_user_simulado_minimal_progress_ledger_applies(
            user_id=owner_user_id
        )
    ) == 1
    _assert_no_leakage(build.json())

    assert owner.post(
        f"/api/simulado-runtime-apply-policy/{owner_policy.runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
    ).json() == build.json()
    assert anonymous.post(
        f"/api/simulado-runtime-apply-policy/{owner_policy.runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-runtime-apply-policy/{owner_policy.runtime_apply_policy_id}/minimal-progress-ledger-apply"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-minimal-progress-ledger-apply/{apply_id}"
    ).status_code == 401
    assert other.post(
        f"/api/simulado-runtime-apply-policy/{owner_policy.runtime_apply_policy_id}/minimal-progress-ledger-apply/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-runtime-apply-policy/{owner_policy.runtime_apply_policy_id}/minimal-progress-ledger-apply"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-minimal-progress-ledger-apply/{apply_id}"
    ).status_code == 404
