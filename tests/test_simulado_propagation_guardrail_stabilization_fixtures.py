import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_propagation_guardrail import SimuladoPropagationGuardrailService
from tests.fixtures.simulado_propagation_guardrails import (
    api_readonly_fixture,
    audit_trail_shape_fixture,
    build_propagation_guardrail,
    candidate_adaptive_tuning_targets_shape_fixture,
    candidate_curriculum_graph_targets_shape_fixture,
    candidate_ranking_targets_shape_fixture,
    candidate_retention_targets_shape_fixture,
    candidate_scheduler_targets_shape_fixture,
    candidate_study_cycle_targets_shape_fixture,
    capture_propagation_guardrail_source_snapshot,
    final_event_globally_applied_fixture,
    mixed_guardrail_fixture,
    missing_applied_event_ledger_fixture,
    no_leakage_fixture,
    no_propagation_fixture,
    no_runtime_update_fixture,
    public_answer_key_exposure_forbidden_fixture,
    propagation_disabled_fixture,
    readiness_summary_shape_fixture,
    safe_source_ledger_fixture,
    source_ledger_blocked_fixture,
    source_ledger_deduplication_missing_fixture,
    source_ledger_not_recorded_fixture,
    source_ledger_not_replay_safe_fixture,
    source_ledger_propagation_state_unsafe_fixture,
    source_ledger_summary_shape_fixture,
    source_ledger_zero_event_records_fixture,
    source_progress_mutation_detected_fixture,
    stabilization_fixture_builders,
    surface_risk_summary_shape_fixture,
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
SURFACES = {
    "ranking": "ranking_signal_candidate",
    "retention": "retention_signal_candidate",
    "scheduler": "scheduler_signal_candidate",
    "study_cycle": "study_cycle_signal_candidate",
    "curriculum_graph": "curriculum_graph_signal_candidate",
    "adaptive_tuning": "adaptive_tuning_signal_candidate",
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
    assert result.propagation_allowed_now is False
    assert result.propagation_applied is False
    assert result.ranking_propagation_allowed is False
    assert result.retention_propagation_allowed is False
    assert result.scheduler_propagation_allowed is False
    assert result.study_cycle_propagation_allowed is False
    assert result.curriculum_graph_propagation_allowed is False
    assert result.adaptive_tuning_propagation_allowed is False
    assert result.no_propagation is True
    assert result.no_new_progress_apply is True
    assert result.no_ranking_update is True
    assert result.no_retention_update is True
    assert result.no_scheduler_update is True
    assert result.no_study_cycle_update is True
    assert result.no_curriculum_graph_update is True
    assert result.no_adaptive_tuning_update is True
    assert result.final_event_applied_globally is False
    assert result.existing_progress_aggregate_mutated is False
    assert result.global_progress_mutation_applied is False
    for candidate_group in (
        result.candidate_ranking_targets,
        result.candidate_retention_targets,
        result.candidate_scheduler_targets,
        result.candidate_study_cycle_targets,
        result.candidate_curriculum_graph_targets,
        result.candidate_adaptive_tuning_targets,
    ):
        for candidate in candidate_group:
            assert candidate.propagation_allowed is False
            assert candidate.propagated is False


def _assert_no_runtime_updates(result) -> None:
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
    assert result.no_commit_execution is True
    assert result.no_mutation_commit is True
    assert result.no_runtime_application_beyond_minimal_ledger is True
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


def test_propagation_guardrail_stabilization_fixtures_are_deterministic_and_json_safe(
    tmp_path,
):
    builders = stabilization_fixture_builders()

    assert "safe_source_ledger" in builders
    assert "mixed_guardrail" in builders
    assert "no_leakage" in builders

    for name, builder in builders.items():
        fixture = builder(tmp_path / name)
        assert fixture.context.user_id
        assert fixture.context.service is not None
        if fixture.applied_event_ledger is not None:
            payload = fixture.applied_event_ledger.model_dump(mode="json")
            dumped = json.dumps(payload, ensure_ascii=True)
            assert "password_hash" not in dumped
            assert "data:image" not in dumped
            assert "raw_runtime_block" not in dumped
            assert len(dumped) < 200000


def test_propagation_guardrail_stabilization_covers_source_ledger_scenarios(tmp_path):
    scenarios = [
        (source_ledger_blocked_fixture, "blocked_by_source_ledger_not_recorded"),
        (source_ledger_not_recorded_fixture, "blocked_by_source_ledger_not_recorded"),
        (source_ledger_zero_event_records_fixture, "blocked_by_no_source_event_records"),
        (source_ledger_not_replay_safe_fixture, "blocked_by_source_ledger_not_replay_safe"),
        (
            source_ledger_deduplication_missing_fixture,
            "blocked_by_source_ledger_deduplication_missing",
        ),
        (
            source_ledger_propagation_state_unsafe_fixture,
            "blocked_by_source_ledger_propagation_state_unsafe",
        ),
        (
            final_event_globally_applied_fixture,
            "blocked_by_final_event_already_globally_applied",
        ),
        (
            source_progress_mutation_detected_fixture,
            "blocked_by_source_progress_mutation_detected",
        ),
        (
            public_answer_key_exposure_forbidden_fixture,
            "blocked_by_public_answer_key_exposure_forbidden",
        ),
        (propagation_disabled_fixture, "blocked_by_propagation_disabled"),
        (mixed_guardrail_fixture, "blocked_by_source_ledger_propagation_state_unsafe"),
    ]

    missing = missing_applied_event_ledger_fixture(tmp_path / "missing")
    assert build_propagation_guardrail(missing) is None
    assert missing.context.repository.list_user_simulado_propagation_guardrails(
        user_id=missing.context.user_id
    ) == []

    for index, (builder, expected_readiness) in enumerate(scenarios):
        result = build_propagation_guardrail(builder(tmp_path / f"scenario-{index}"))
        assert result is not None
        assert result.propagation_guardrail_created is True
        assert result.readiness_state == expected_readiness
        assert result.propagation_allowed_now is False
        assert result.propagation_applied is False
        assert result.propagation_ready_for_future_review is False
        _assert_no_propagation(result)
        _assert_no_runtime_updates(result)


def test_propagation_guardrail_stabilization_covers_safe_source_summaries_targets_risk_and_audit(
    tmp_path,
):
    safe = build_propagation_guardrail(safe_source_ledger_fixture(tmp_path / "safe"))
    readiness = build_propagation_guardrail(
        readiness_summary_shape_fixture(tmp_path / "readiness")
    )
    source_summary = build_propagation_guardrail(
        source_ledger_summary_shape_fixture(tmp_path / "source-summary")
    )
    ranking = build_propagation_guardrail(
        candidate_ranking_targets_shape_fixture(tmp_path / "ranking")
    )
    retention = build_propagation_guardrail(
        candidate_retention_targets_shape_fixture(tmp_path / "retention")
    )
    scheduler = build_propagation_guardrail(
        candidate_scheduler_targets_shape_fixture(tmp_path / "scheduler")
    )
    study_cycle = build_propagation_guardrail(
        candidate_study_cycle_targets_shape_fixture(tmp_path / "study-cycle")
    )
    graph = build_propagation_guardrail(
        candidate_curriculum_graph_targets_shape_fixture(tmp_path / "graph")
    )
    adaptive = build_propagation_guardrail(
        candidate_adaptive_tuning_targets_shape_fixture(tmp_path / "adaptive")
    )
    risk = build_propagation_guardrail(
        surface_risk_summary_shape_fixture(tmp_path / "risk")
    )
    audit = build_propagation_guardrail(audit_trail_shape_fixture(tmp_path / "audit"))

    assert safe is not None
    assert safe.propagation_guardrail_created is True
    assert safe.source_ledger_present is True
    assert safe.source_ledger_recorded is True
    assert safe.source_ledger_event_count > 0
    assert safe.source_ledger_replay_safe is True
    assert safe.source_ledger_deduplication_enforced is True
    assert safe.source_ledger_no_propagation is True
    assert safe.propagation_allowed_now is False
    assert safe.propagation_applied is False
    assert safe.propagation_ready_for_future_review is True
    _assert_no_propagation(safe)
    _assert_no_runtime_updates(safe)
    _assert_no_leakage(safe.model_dump(mode="json"))

    assert readiness is not None
    assert readiness.readiness_summary.source_ledger_present is True
    assert readiness.readiness_summary.source_ledger_recorded is True
    assert readiness.readiness_summary.source_ledger_event_count == readiness.source_ledger_event_count
    assert readiness.readiness_summary.source_ledger_replay_safe is True
    assert readiness.readiness_summary.source_ledger_deduplication_enforced is True
    assert readiness.readiness_summary.source_ledger_no_propagation is True
    assert readiness.readiness_summary.source_final_event_applied_globally is False
    assert readiness.readiness_summary.source_global_progress_mutation_applied is False
    assert readiness.readiness_summary.propagation_allowed_now is False
    assert readiness.readiness_summary.blocked_surface_count == 6
    assert readiness.readiness_summary.unsafe_public_answer_key_exposure_detected is False
    assert readiness.readiness_summary.unsafe_gabarito_exposure_detected is False

    assert source_summary is not None
    assert source_summary.source_ledger_summary.source_apply_present is True
    assert source_summary.source_ledger_summary.source_apply_applied is True
    assert source_summary.source_ledger_summary.ledger_event_count == source_summary.source_ledger_event_count
    assert source_summary.source_ledger_summary.replay_safe is True
    assert source_summary.source_ledger_summary.deduplication_enforced is True
    assert source_summary.source_ledger_summary.no_propagation is True
    assert source_summary.source_ledger_summary.final_event_applied_globally is False
    assert source_summary.source_ledger_summary.global_progress_mutation_applied is False
    assert source_summary.source_ledger_summary.existing_progress_aggregate_mutated is False

    target_expectations = [
        (ranking.candidate_ranking_targets, "ranking"),
        (retention.candidate_retention_targets, "retention"),
        (scheduler.candidate_scheduler_targets, "scheduler"),
        (study_cycle.candidate_study_cycle_targets, "study_cycle"),
        (graph.candidate_curriculum_graph_targets, "curriculum_graph"),
        (adaptive.candidate_adaptive_tuning_targets, "adaptive_tuning"),
    ]
    for candidates, surface in target_expectations:
        assert len(candidates) == safe.source_ledger_event_count
        for candidate in candidates:
            assert candidate.propagation_surface == surface
            assert candidate.propagation_kind == SURFACES[surface]
            assert candidate.candidate is True
            assert candidate.propagation_allowed is False
            assert candidate.propagated is False
            assert isinstance(candidate.bounded_signal_summary, dict)
            assert len(candidate.bounded_signal_summary) <= 4
            dumped = json.dumps(candidate.model_dump(mode="json"), ensure_ascii=True)
            assert "raw_runtime_block" not in dumped
            assert "answer_key" not in dumped
            assert "gabarito" not in dumped
            assert "ranking_update_payload" not in dumped
            assert "retention_update_payload" not in dumped
            assert "scheduler_update_payload" not in dumped
            assert "study_cycle_update_payload" not in dumped
            assert "curriculum_graph_update_payload" not in dumped

    assert risk is not None
    assert risk.surface_risk_summary.candidate_surface_count == len(SURFACES)
    assert risk.surface_risk_summary.blocked_surface_count == len(SURFACES)
    assert risk.surface_risk_summary.ranking_candidate_count == safe.source_ledger_event_count
    assert risk.surface_risk_summary.retention_candidate_count == safe.source_ledger_event_count
    assert risk.surface_risk_summary.scheduler_candidate_count == safe.source_ledger_event_count
    assert risk.surface_risk_summary.study_cycle_candidate_count == safe.source_ledger_event_count
    assert risk.surface_risk_summary.curriculum_graph_candidate_count == safe.source_ledger_event_count
    assert risk.surface_risk_summary.adaptive_tuning_candidate_count == safe.source_ledger_event_count
    assert risk.surface_risk_summary.propagation_allowed_surface_count == 0
    assert risk.surface_risk_summary.propagated_surface_count == 0
    assert risk.surface_risk_summary.no_propagation is True

    assert audit is not None
    audit_events = {entry.event_type for entry in audit.audit_trail}
    assert "propagation_guardrail_created" in audit_events
    assert "source_applied_event_ledger_evaluated" in audit_events
    assert "propagation_ready_for_future_review" in audit_events
    assert "no_propagation" in audit_events
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


def test_propagation_guardrail_stabilization_preserves_sources_and_is_idempotent(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = no_propagation_fixture(tmp_path / "no-propagation", repository=repository)
    source_ledger = fixture.applied_event_ledger
    assert source_ledger is not None

    before = capture_propagation_guardrail_source_snapshot(fixture)
    first = build_propagation_guardrail(fixture)
    middle = capture_propagation_guardrail_source_snapshot(fixture)
    second = build_propagation_guardrail(fixture)
    loaded = SimuladoPropagationGuardrailService(repository).get_propagation_guardrail(
        source_ledger.applied_event_ledger_id,
        user_id=fixture.context.user_id,
    )
    loaded_by_id = SimuladoPropagationGuardrailService(repository).get_propagation_guardrail_by_id(
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

    no_updates = build_propagation_guardrail(
        no_runtime_update_fixture(tmp_path / "no-runtime-update")
    )
    assert no_updates is not None
    _assert_no_propagation(no_updates)
    _assert_no_runtime_updates(no_updates)


def test_propagation_guardrail_stabilization_api_owner_only_read_only_and_persistent(
    tmp_path,
):
    owner, other, anonymous, repository = _create_clients(tmp_path)
    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")

    blocked_fixture = source_ledger_blocked_fixture(
        tmp_path / "blocked",
        user_id=owner_user_id,
        repository=repository,
    )
    safe_fixture = api_readonly_fixture(
        tmp_path / "safe",
        user_id=owner_user_id,
        repository=repository,
    )
    assert blocked_fixture.applied_event_ledger is not None
    assert safe_fixture.applied_event_ledger is not None
    blocked_ledger_id = blocked_fixture.applied_event_ledger.applied_event_ledger_id
    safe_ledger_id = safe_fixture.applied_event_ledger.applied_event_ledger_id

    missing = owner.get(
        f"/api/simulado-applied-event-ledger/{safe_ledger_id}/propagation-guardrail"
    )
    blocked_first = owner.post(
        f"/api/simulado-applied-event-ledger/{blocked_ledger_id}/propagation-guardrail/build"
    )
    blocked_second = owner.post(
        f"/api/simulado-applied-event-ledger/{blocked_ledger_id}/propagation-guardrail/build"
    )
    before_safe = repository.get_simulado_applied_event_ledger_by_id(
        safe_ledger_id,
        user_id=owner_user_id,
    )
    safe_first = owner.post(
        f"/api/simulado-applied-event-ledger/{safe_ledger_id}/propagation-guardrail/build"
    )
    safe_second = owner.post(
        f"/api/simulado-applied-event-ledger/{safe_ledger_id}/propagation-guardrail/build"
    )
    by_source = owner.get(
        f"/api/simulado-applied-event-ledger/{safe_ledger_id}/propagation-guardrail"
    )
    guardrail_id = safe_first.json()["propagation_guardrail_id"]
    by_id = owner.get(f"/api/simulado-propagation-guardrail/{guardrail_id}")
    after_safe = repository.get_simulado_applied_event_ledger_by_id(
        safe_ledger_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert blocked_first.status_code == 200
    assert blocked_second.status_code == 200
    assert blocked_first.json() == blocked_second.json()
    assert blocked_first.json()["propagation_allowed_now"] is False
    assert blocked_first.json()["propagation_applied"] is False

    assert before_safe is not None
    assert safe_first.status_code == 200
    assert safe_second.status_code == 200
    assert safe_first.json() == safe_second.json()
    assert by_source.status_code == 200
    assert by_id.status_code == 200
    assert after_safe is not None
    assert before_safe.model_dump(mode="json") == after_safe.model_dump(mode="json")

    listed = repository.list_user_simulado_propagation_guardrails(user_id=owner_user_id)
    expected_count = len({blocked_ledger_id, safe_ledger_id})
    assert len(listed) == expected_count
    assert repository.get_simulado_propagation_guardrail(
        safe_ledger_id,
        user_id=owner_user_id,
    ) is not None
    assert repository.get_simulado_propagation_guardrail_by_id(
        guardrail_id,
        user_id=owner_user_id,
    ) is not None

    assert anonymous.post(
        f"/api/simulado-applied-event-ledger/{safe_ledger_id}/propagation-guardrail/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-applied-event-ledger/{safe_ledger_id}/propagation-guardrail"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-propagation-guardrail/{guardrail_id}").status_code == 401

    assert other.post(
        f"/api/simulado-applied-event-ledger/{safe_ledger_id}/propagation-guardrail/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-applied-event-ledger/{safe_ledger_id}/propagation-guardrail"
    ).status_code == 404
    assert other.get(f"/api/simulado-propagation-guardrail/{guardrail_id}").status_code == 404


def test_propagation_guardrail_stabilization_prevents_leakage_in_service_and_api_payloads(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = no_leakage_fixture(tmp_path / "service", repository=repository)
    result = build_propagation_guardrail(fixture)
    assert result is not None
    _assert_no_leakage(result.model_dump(mode="json"))

    owner, _, _, api_repository = _create_clients(tmp_path / "api")
    owner_user_id = _register_and_login(owner, "owner")
    api_fixture = user_scope_fixture(
        tmp_path / "api-fixture",
        user_id=owner_user_id,
        repository=api_repository,
    )
    assert api_fixture.applied_event_ledger is not None
    response = owner.post(
        f"/api/simulado-applied-event-ledger/{api_fixture.applied_event_ledger.applied_event_ledger_id}/propagation-guardrail/build"
    )
    assert response.status_code == 200
    payload = response.json()
    assert payload["answer_key_publicly_exposed"] is False
    assert payload["gabarito_publicly_exposed"] is False
    _assert_no_leakage(payload)
