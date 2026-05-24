import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from tests.fixtures.simulado_controlled_propagation_applies import (
    api_readonly_fixture,
    audit_trail_shape_fixture,
    build_controlled_propagation_apply,
    capture_controlled_propagation_apply_source_snapshot,
    controlled_propagation_entries_shape_fixture,
    idempotency_record_shape_fixture,
    idempotency_requirement_unsatisfied_fixture,
    ledger_only_apply_fixture,
    missing_propagation_guardrail_fixture,
    mixed_controlled_apply_fixture,
    no_global_progress_mutation_fixture,
    no_leakage_fixture,
    no_runtime_surface_apply_fixture,
    replay_behavior_fixture,
    rollback_record_shape_fixture,
    safe_source_guardrail_fixture,
    source_guardrail_blocked_fixture,
    source_guardrail_no_candidate_targets_fixture,
    source_guardrail_not_ready_for_future_review_fixture,
    source_guardrail_public_exposure_forbidden_fixture,
    source_guardrail_state_unsafe_fixture,
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
    "raw_runtime_block",
    "ranking_update_payload",
    "retention_update_payload",
    "scheduler_update_payload",
    "study_cycle_update_payload",
    "curriculum_graph_update_payload",
    "adaptive_tuning_payload",
    "review_schedule_entry_payload",
}
SURFACES = {
    "ranking",
    "retention",
    "scheduler",
    "study_cycle",
    "curriculum_graph",
    "adaptive_tuning",
}


def _assert_json_safe(result) -> None:
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


def _assert_no_runtime_surface_apply(result) -> None:
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


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> str:
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


def test_controlled_propagation_stabilization_fixtures_are_deterministic_and_json_safe(
    tmp_path,
):
    builders = stabilization_fixture_builders()
    assert "safe_source_guardrail_fixture" in builders
    assert "mixed_controlled_apply_fixture" in builders
    fixture = no_leakage_fixture(tmp_path / "no-leakage")
    first = build_controlled_propagation_apply(fixture)
    second = build_controlled_propagation_apply(fixture)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    _assert_json_safe(first)


def test_controlled_propagation_stabilization_covers_blocked_guardrail_scenarios(
    tmp_path,
):
    missing = missing_propagation_guardrail_fixture(tmp_path / "missing")
    blocked = source_guardrail_blocked_fixture(tmp_path / "blocked")
    not_ready = source_guardrail_not_ready_for_future_review_fixture(tmp_path / "not-ready")
    unsafe_state = source_guardrail_state_unsafe_fixture(tmp_path / "unsafe-state")
    no_targets = source_guardrail_no_candidate_targets_fixture(tmp_path / "no-targets")
    idempotency_unsatisfied = idempotency_requirement_unsatisfied_fixture(
        tmp_path / "idempotency"
    )
    rollback_unsatisfied = rollback_record_shape_fixture(tmp_path / "rollback-source")
    rollback_unsatisfied.propagation_guardrail.metadata[
        "controlled_propagation_apply_rollback_unsatisfied"
    ] = True
    rollback_unsatisfied.context.repository.save_simulado_propagation_guardrail(
        rollback_unsatisfied.propagation_guardrail,
        user_id=rollback_unsatisfied.context.user_id,
    )
    unsafe_public = source_guardrail_public_exposure_forbidden_fixture(
        tmp_path / "public-exposure"
    )

    assert build_controlled_propagation_apply(missing) is None
    assert missing.context.repository.list_user_simulado_controlled_propagation_applies(
        user_id=missing.context.user_id
    ) == []

    cases = {
        "blocked_by_guardrail_not_ready_for_future_review": build_controlled_propagation_apply(
            blocked
        ),
        "blocked_by_source_guardrail_state_unsafe": build_controlled_propagation_apply(
            unsafe_state
        ),
        "blocked_by_no_candidate_propagation_targets": build_controlled_propagation_apply(
            no_targets
        ),
        "blocked_by_idempotency_requirement_unsatisfied": build_controlled_propagation_apply(
            idempotency_unsatisfied
        ),
        "blocked_by_rollback_requirement_unsatisfied": build_controlled_propagation_apply(
            rollback_unsatisfied
        ),
        "blocked_by_public_answer_key_exposure_forbidden": build_controlled_propagation_apply(
            unsafe_public
        ),
    }

    not_ready_result = build_controlled_propagation_apply(not_ready)
    assert not_ready_result is not None
    assert (
        not_ready_result.readiness_state
        == "blocked_by_guardrail_not_ready_for_future_review"
    )

    for expected_code, result in cases.items():
        assert result is not None
        assert result.controlled_propagation_apply_created is True
        assert result.readiness_state == expected_code
        assert result.controlled_propagation_ledger_recorded is False
        assert result.controlled_propagation_entry_created is False
        assert result.controlled_propagation_entry_count == 0
        _assert_no_runtime_surface_apply(result)
        for entry in result.controlled_propagation_entries:
            assert entry.applied_to_runtime_surface is False


def test_controlled_propagation_stabilization_preserves_safe_ledger_only_behavior(
    tmp_path,
):
    fixture = safe_source_guardrail_fixture(tmp_path / "safe")
    result = build_controlled_propagation_apply(fixture)

    assert result is not None
    assert result.source_guardrail_present is True
    assert result.source_guardrail_ready_for_future_review is True
    assert result.source_propagation_allowed_now is False
    assert result.source_propagation_applied is False
    assert result.source_candidate_target_count > 0
    assert result.controlled_propagation_ledger_recorded is True
    assert result.controlled_propagation_entry_created is True
    assert result.controlled_propagation_entry_count > 0
    _assert_no_runtime_surface_apply(result)
    _assert_json_safe(result)

    seen_surfaces = set()
    for entry in result.controlled_propagation_entries:
        seen_surfaces.add(entry.propagation_surface)
        assert entry.recorded is True
        assert entry.applied_to_controlled_ledger is True
        assert entry.applied_to_runtime_surface is False
        assert entry.user_id == fixture.context.user_id
        assert entry.source_propagation_guardrail_id == result.source_propagation_guardrail_id
        assert entry.source_candidate_target_id
        assert entry.propagation_surface in SURFACES
        assert entry.propagation_kind
        assert entry.target_type
        assert isinstance(entry.bounded_propagation_summary, dict)
        assert "review_schedule_entry" not in json.dumps(
            entry.model_dump(mode="json"),
            ensure_ascii=True,
        )
    assert SURFACES.issubset(seen_surfaces)


def test_controlled_propagation_stabilization_covers_idempotency_replay_rollback_and_audit(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = replay_behavior_fixture(tmp_path / "replay", repository=repository)
    result = build_controlled_propagation_apply(fixture)
    again = build_controlled_propagation_apply(fixture)

    assert result is not None
    assert again is not None
    assert result.model_dump(mode="json") == again.model_dump(mode="json")
    assert result.idempotency_key_required is True
    assert result.idempotency_key_present is True
    assert result.idempotency_key_valid is True
    assert result.idempotency_key
    assert result.idempotency_record.source_propagation_guardrail_id == result.source_propagation_guardrail_id
    assert result.idempotency_record.replay_returns_existing_apply is True
    assert result.idempotency_record.satisfied is True
    assert result.duplicate_controlled_apply_detected is False
    assert result.replay_returns_existing_apply is True
    assert result.rollback_required is True
    assert result.rollback_scope == "controlled_propagation_ledger"
    assert result.rollback_executed is False
    assert isinstance(result.rollback_record.rollback_summary, dict)
    assert len(
        repository.list_user_simulado_controlled_propagation_applies(
            user_id=fixture.context.user_id
        )
    ) == 1

    audit_events = {entry.event_type for entry in result.audit_trail}
    assert "controlled_propagation_apply_created" in audit_events
    assert "source_propagation_guardrail_evaluated" in audit_events
    assert "controlled_propagation_ledger_recorded" in audit_events
    assert "controlled_propagation_entry_recorded" in audit_events
    assert "idempotency_key_recorded" in audit_events
    assert "rollback_reference_created" in audit_events
    assert "no_direct_runtime_propagation" in audit_events
    assert "no_scheduler_update" in audit_events
    assert "no_runtime_application_beyond_minimal_ledger" in audit_events

    unique_target_keys = {
        (item.propagation_surface, item.source_candidate_target_id)
        for item in result.controlled_propagation_entries
    }
    assert len(unique_target_keys) == result.controlled_propagation_entry_count


def test_controlled_propagation_stabilization_preserves_sources_and_get_is_read_only(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = api_readonly_fixture(tmp_path / "readonly", repository=repository)
    before = capture_controlled_propagation_apply_source_snapshot(fixture)
    result = build_controlled_propagation_apply(fixture)
    middle = capture_controlled_propagation_apply_source_snapshot(fixture)
    result_again = build_controlled_propagation_apply(fixture)
    after = capture_controlled_propagation_apply_source_snapshot(fixture)

    assert result is not None
    assert result_again is not None
    assert before.propagation_guardrail == middle.propagation_guardrail == after.propagation_guardrail
    assert before.applied_event_ledger == middle.applied_event_ledger == after.applied_event_ledger
    assert before.minimal_apply == middle.minimal_apply == after.minimal_apply
    assert before.runtime_apply_policy == middle.runtime_apply_policy == after.runtime_apply_policy
    assert before.final_event == middle.final_event == after.final_event
    assert before.controlled_execution == middle.controlled_execution == after.controlled_execution
    assert before.execution_plan == middle.execution_plan == after.execution_plan
    assert before.progress == middle.progress == after.progress
    assert before.controlled_propagation_apply_count == 0
    assert middle.controlled_propagation_apply_count == 1
    assert after.controlled_propagation_apply_count == 1


def test_controlled_propagation_stabilization_owner_only_api_is_read_only_and_idempotent(
    tmp_path,
):
    owner, other, anonymous, repository = create_clients(tmp_path)
    owner_user_id = register_and_login(owner, "owner")
    register_and_login(other, "other")
    fixture = user_scope_fixture(tmp_path / "owner", user_id=owner_user_id, repository=repository)
    guardrail = fixture.propagation_guardrail
    assert guardrail is not None

    missing = owner.get(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply"
    )
    build = owner.post(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply/build"
    )
    replay = owner.post(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply/build"
    )
    loaded = owner.get(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply"
    )
    apply_id = build.json()["controlled_propagation_apply_id"]
    by_id = owner.get(f"/api/simulado-controlled-propagation-apply/{apply_id}")

    assert missing.status_code == 404
    assert build.status_code == 200
    assert replay.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert build.json() == replay.json() == loaded.json() == by_id.json()

    assert other.post(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply"
    ).status_code == 404
    assert other.get(f"/api/simulado-controlled-propagation-apply/{apply_id}").status_code == 404
    assert anonymous.post(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-propagation-guardrail/{guardrail.propagation_guardrail_id}/controlled-propagation-apply"
    ).status_code == 401

    _assert_json_safe(result=type("Obj", (), {"model_dump": lambda self, mode="json": build.json()})())


def test_controlled_propagation_stabilization_mixed_fixture_remains_small_and_source_aware(
    tmp_path,
):
    mixed = mixed_controlled_apply_fixture(tmp_path / "mixed")
    assert set(mixed) == {"blocked", "safe", "unsafe_state"}
    blocked = build_controlled_propagation_apply(mixed["blocked"])
    safe = build_controlled_propagation_apply(mixed["safe"])
    unsafe = build_controlled_propagation_apply(mixed["unsafe_state"])

    assert blocked is not None
    assert safe is not None
    assert unsafe is not None
    assert blocked.controlled_propagation_entry_count == 0
    assert safe.controlled_propagation_entry_count > 0
    assert unsafe.controlled_propagation_entry_count == 0
