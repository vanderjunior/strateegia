import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_final_pedagogical_update_event import (
    SimuladoFinalPedagogicalUpdateEventService,
)
from tests.fixtures.simulado_final_pedagogical_update_events import (
    api_readonly_fixture,
    build_final_pedagogical_update_event,
    capture_final_event_source_snapshot,
    commit_executed_detected_fixture,
    controlled_execution_not_dry_run_fixture,
    controlled_execution_started_fixture,
    execution_disabled_fixture,
    final_event_apply_disabled_fixture,
    final_event_audit_trail_fixture,
    final_event_summary_fixture,
    idempotency_fixture,
    missing_controlled_execution_fixture,
    mixed_final_event_fixture,
    mutation_committed_detected_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    progress_mutation_detected_fixture,
    proposed_adaptive_tuning_updates_fixture,
    proposed_curriculum_graph_updates_fixture,
    proposed_progress_updates_fixture,
    proposed_ranking_updates_fixture,
    proposed_retention_updates_fixture,
    proposed_scheduler_updates_fixture,
    proposed_study_cycle_updates_fixture,
    public_answer_key_exposure_forbidden_fixture,
    runtime_application_detected_fixture,
    stabilization_fixture_builders,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_FINAL_EVENT_KEYS = {
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
    "commit_execution_event",
    "mutation_commit_event",
    "runtime_application_event",
    "applied_final_pedagogical_update_event",
    "raw_runtime_block",
}

ALLOWED_FINAL_EVENT_MODES = {"event_proposal_only", "dry_run_final_event"}
ALLOWED_PROPOSED_UPDATE_KINDS = {
    "progress": "progress_delta_proposal",
    "ranking": "ranking_signal_proposal",
    "retention": "retention_signal_proposal",
    "scheduler": "scheduler_signal_proposal",
    "study_cycle": "study_cycle_signal_proposal",
    "curriculum_graph": "curriculum_graph_signal_proposal",
    "adaptive_tuning": "adaptive_tuning_signal_proposal",
}

ALLOWED_AUDIT_EVENTS = {
    "final_pedagogical_update_event_created",
    "final_event_proposal_created",
    "final_event_blocked",
    "final_event_not_applied",
    "no_commit_execution",
    "no_mutation_commit",
    "no_runtime_application",
    "no_progress_mutation",
    "no_ranking_update",
    "no_retention_update",
    "no_scheduler_update",
    "no_study_cycle_update",
    "no_curriculum_graph_update",
    "no_adaptive_tuning_update",
    "no_applied_final_pedagogical_update_event",
}


def _assert_no_apply_or_runtime_mutation_flags(result) -> None:
    assert result.final_event_mode in ALLOWED_FINAL_EVENT_MODES
    assert result.final_event_status != "applied"
    assert result.final_pedagogical_update_event_created is True
    assert result.final_pedagogical_update_event_applied is False
    assert result.final_pedagogical_update_event_apply_allowed is False
    assert result.final_pedagogical_update_event_application_started is False
    assert result.final_pedagogical_update_event_application_completed is False
    assert result.controlled_execution_dry_run_only is True
    assert result.execution_started is False
    assert result.commit_executed is False
    assert result.mutation_committed is False
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
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


def _assert_no_leakage(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(payload)
    for key in FORBIDDEN_FINAL_EVENT_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "/uploads/" not in dumped
    assert "data:image" not in dumped
    assert "final_question_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys


def _assert_proposed_update_entries(entries, *, surface: str) -> None:
    assert entries
    for item in entries:
        assert item.update_surface == surface
        assert item.update_kind == ALLOWED_PROPOSED_UPDATE_KINDS[surface]
        assert item.proposed is True
        assert item.applied is False
        assert item.apply_allowed is False
        assert item.source_record_id
        assert item.bounded_summary
        assert "raw_runtime_block" not in json.dumps(item.model_dump(mode="json"), ensure_ascii=True)


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


def _prepare_controlled_execution(repository: JsonStudyRepository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    return controlled_execution


def test_final_pedagogical_update_event_stabilization_fixtures_are_deterministic_and_json_safe(
    tmp_path,
):
    builders = stabilization_fixture_builders()

    for name, builder in builders.items():
        fixture = builder(tmp_path / name)
        mirror = builder(tmp_path / f"{name}-mirror")

        assert json.dumps({"fixture": name}, ensure_ascii=True)
        assert fixture.context.user_id == "user-a"
        if fixture.controlled_execution is None:
            assert mirror.controlled_execution is None
            assert fixture.missing_controlled_execution_id == mirror.missing_controlled_execution_id
            continue

        assert mirror.controlled_execution is not None
        assert (
            fixture.controlled_execution.controlled_execution_id
            == mirror.controlled_execution.controlled_execution_id
        )
        assert fixture.controlled_execution.user_id == fixture.context.user_id


def test_final_pedagogical_update_event_stabilization_covers_source_scenarios_and_blockers(
    tmp_path,
):
    missing = build_final_pedagogical_update_event(missing_controlled_execution_fixture(tmp_path / "missing"))
    not_dry_run = build_final_pedagogical_update_event(
        controlled_execution_not_dry_run_fixture(tmp_path / "not-dry-run")
    )
    started = build_final_pedagogical_update_event(
        controlled_execution_started_fixture(tmp_path / "started")
    )
    commit_executed = build_final_pedagogical_update_event(
        commit_executed_detected_fixture(tmp_path / "commit-executed")
    )
    mutation_committed = build_final_pedagogical_update_event(
        mutation_committed_detected_fixture(tmp_path / "mutation-committed")
    )
    runtime_detected = build_final_pedagogical_update_event(
        runtime_application_detected_fixture(tmp_path / "runtime-detected")
    )
    progress_detected = build_final_pedagogical_update_event(
        progress_mutation_detected_fixture(tmp_path / "progress-detected")
    )
    apply_disabled = build_final_pedagogical_update_event(
        final_event_apply_disabled_fixture(tmp_path / "apply-disabled")
    )
    execution_disabled = build_final_pedagogical_update_event(
        execution_disabled_fixture(tmp_path / "execution-disabled")
    )
    unsafe = build_final_pedagogical_update_event(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )

    assert missing is None

    assert not_dry_run is not None
    assert not_dry_run.readiness_state == "blocked_by_controlled_execution_not_dry_run"
    _assert_no_apply_or_runtime_mutation_flags(not_dry_run)

    assert started is not None
    assert started.readiness_state == "blocked_by_controlled_execution_started"
    _assert_no_apply_or_runtime_mutation_flags(started)

    assert commit_executed is not None
    assert commit_executed.readiness_state == "blocked_by_commit_executed"
    _assert_no_apply_or_runtime_mutation_flags(commit_executed)

    assert mutation_committed is not None
    assert mutation_committed.readiness_state == "blocked_by_mutation_committed"
    _assert_no_apply_or_runtime_mutation_flags(mutation_committed)

    assert runtime_detected is not None
    assert runtime_detected.readiness_state == "blocked_by_runtime_application_detected"
    _assert_no_apply_or_runtime_mutation_flags(runtime_detected)

    assert progress_detected is not None
    assert progress_detected.readiness_state == "blocked_by_progress_mutation_detected"
    _assert_no_apply_or_runtime_mutation_flags(progress_detected)

    assert apply_disabled is not None
    assert apply_disabled.readiness_state == "blocked_by_final_event_apply_disabled"
    _assert_no_apply_or_runtime_mutation_flags(apply_disabled)

    assert execution_disabled is not None
    assert execution_disabled.readiness_state == "blocked_by_final_event_apply_disabled"
    _assert_no_apply_or_runtime_mutation_flags(execution_disabled)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    assert unsafe.event_summary.unsafe_public_answer_key_exposure_detected is True
    assert unsafe.event_summary.unsafe_gabarito_exposure_detected is True
    _assert_no_apply_or_runtime_mutation_flags(unsafe)
    _assert_no_leakage(unsafe.model_dump(mode="json"))


def test_final_pedagogical_update_event_stabilization_covers_summary_proposed_updates_and_audit(
    tmp_path,
):
    summary = build_final_pedagogical_update_event(final_event_summary_fixture(tmp_path / "summary"))
    progress = build_final_pedagogical_update_event(
        proposed_progress_updates_fixture(tmp_path / "progress")
    )
    ranking = build_final_pedagogical_update_event(
        proposed_ranking_updates_fixture(tmp_path / "ranking")
    )
    retention = build_final_pedagogical_update_event(
        proposed_retention_updates_fixture(tmp_path / "retention")
    )
    scheduler = build_final_pedagogical_update_event(
        proposed_scheduler_updates_fixture(tmp_path / "scheduler")
    )
    study_cycle = build_final_pedagogical_update_event(
        proposed_study_cycle_updates_fixture(tmp_path / "study-cycle")
    )
    curriculum_graph = build_final_pedagogical_update_event(
        proposed_curriculum_graph_updates_fixture(tmp_path / "curriculum-graph")
    )
    adaptive_tuning = build_final_pedagogical_update_event(
        proposed_adaptive_tuning_updates_fixture(tmp_path / "adaptive-tuning")
    )
    audit_trail = build_final_pedagogical_update_event(
        final_event_audit_trail_fixture(tmp_path / "audit-trail")
    )

    assert summary is not None
    assert summary.event_summary.source_controlled_execution_present is True
    assert summary.event_summary.source_controlled_execution_dry_run is True
    assert summary.event_summary.source_execution_started is False
    assert summary.event_summary.source_commit_executed is False
    assert summary.event_summary.source_mutation_committed is False
    assert summary.event_summary.source_runtime_application_performed is False
    assert summary.event_summary.source_real_execution_performed is False
    assert summary.event_summary.proposed_progress_update_count == len(
        summary.proposed_progress_updates
    )
    assert summary.event_summary.proposed_ranking_update_count == len(
        summary.proposed_ranking_updates
    )
    assert summary.event_summary.proposed_retention_update_count == len(
        summary.proposed_retention_updates
    )
    assert summary.event_summary.proposed_scheduler_update_count == len(
        summary.proposed_scheduler_updates
    )
    assert summary.event_summary.proposed_study_cycle_update_count == len(
        summary.proposed_study_cycle_updates
    )
    assert summary.event_summary.proposed_curriculum_graph_update_count == len(
        summary.proposed_curriculum_graph_updates
    )
    assert summary.event_summary.proposed_adaptive_tuning_update_count == len(
        summary.proposed_adaptive_tuning_updates
    )
    assert summary.event_summary.final_event_apply_allowed is False
    assert summary.event_summary.final_event_applied is False
    _assert_no_apply_or_runtime_mutation_flags(summary)

    assert progress is not None
    _assert_proposed_update_entries(progress.proposed_progress_updates, surface="progress")

    assert ranking is not None
    _assert_proposed_update_entries(ranking.proposed_ranking_updates, surface="ranking")

    assert retention is not None
    _assert_proposed_update_entries(retention.proposed_retention_updates, surface="retention")

    assert scheduler is not None
    _assert_proposed_update_entries(scheduler.proposed_scheduler_updates, surface="scheduler")

    assert study_cycle is not None
    _assert_proposed_update_entries(
        study_cycle.proposed_study_cycle_updates,
        surface="study_cycle",
    )

    assert curriculum_graph is not None
    _assert_proposed_update_entries(
        curriculum_graph.proposed_curriculum_graph_updates,
        surface="curriculum_graph",
    )

    assert adaptive_tuning is not None
    _assert_proposed_update_entries(
        adaptive_tuning.proposed_adaptive_tuning_updates,
        surface="adaptive_tuning",
    )

    assert audit_trail is not None
    assert ALLOWED_AUDIT_EVENTS.issubset({item.event_type for item in audit_trail.audit_trail})
    _assert_no_apply_or_runtime_mutation_flags(audit_trail)


def test_final_pedagogical_update_event_stabilization_preserves_no_leakage_and_runtime_state(
    tmp_path,
):
    safe = build_final_pedagogical_update_event(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe")
    )
    no_runtime_application = build_final_pedagogical_update_event(
        no_runtime_application_fixture(tmp_path / "no-runtime-application")
    )
    no_runtime_mutation = build_final_pedagogical_update_event(
        no_runtime_mutation_fixture(tmp_path / "no-runtime-mutation")
    )
    mixed = build_final_pedagogical_update_event(mixed_final_event_fixture(tmp_path / "mixed"))

    assert safe is not None
    _assert_no_apply_or_runtime_mutation_flags(safe)
    _assert_no_leakage(safe.model_dump(mode="json"))

    assert no_runtime_application is not None
    assert no_runtime_application.runtime_application_enabled is False
    assert no_runtime_application.runtime_application_applied is False
    _assert_no_apply_or_runtime_mutation_flags(no_runtime_application)

    assert no_runtime_mutation is not None
    _assert_no_apply_or_runtime_mutation_flags(no_runtime_mutation)

    assert mixed is not None
    assert mixed.blockers
    assert mixed.validation_findings
    assert mixed.warnings
    assert {warning.code for warning in mixed.warnings} >= {
        "final_event_proposal_only",
        "final_event_contains_blockers",
    }
    _assert_no_apply_or_runtime_mutation_flags(mixed)
    _assert_no_leakage(mixed.model_dump(mode="json"))


def test_final_pedagogical_update_event_stabilization_persistence_idempotency_and_source_preservation(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = idempotency_fixture(tmp_path / "idempotent", repository=repository)
    service = SimuladoFinalPedagogicalUpdateEventService(repository)
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None

    before = capture_final_event_source_snapshot(fixture)
    first = build_final_pedagogical_update_event(fixture)
    after_first = capture_final_event_source_snapshot(fixture)
    second = build_final_pedagogical_update_event(fixture)
    loaded = service.get_final_event(
        controlled_execution.controlled_execution_id,
        user_id=fixture.context.user_id,
    )
    loaded_by_id = service.get_final_event_by_id(
        first.final_event_id if first is not None else "missing",
        user_id=fixture.context.user_id,
    )
    after_second = capture_final_event_source_snapshot(fixture)

    assert first is not None
    assert second is not None
    assert loaded is not None
    assert loaded_by_id is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.model_dump(mode="json") == loaded.model_dump(mode="json")
    assert first.model_dump(mode="json") == loaded_by_id.model_dump(mode="json")
    assert before.controlled_execution == after_second.controlled_execution
    assert before.execution_plan == after_second.execution_plan
    assert before.execution_approval == after_second.execution_approval
    assert before.execution_guardrail == after_second.execution_guardrail
    assert before.progress == after_second.progress
    assert before.final_event_count == 0
    assert after_first.final_event_count == 1
    assert after_second.final_event_count == 1


def test_final_pedagogical_update_event_stabilization_api_owner_scope_and_read_only_behavior(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    owner = TestClient(app)
    other = TestClient(app)
    anonymous = TestClient(app)

    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    controlled_execution = _prepare_controlled_execution(
        repository,
        tmp_path / "owner",
        owner_user_id,
    )

    missing = owner.get(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event"
    )
    before_controlled = repository.get_simulado_controlled_runtime_commit_execution_by_id(
        controlled_execution.controlled_execution_id,
        user_id=owner_user_id,
    )
    first_build = owner.post(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event/build"
    )
    second_build = owner.post(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event/build"
    )
    loaded = owner.get(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event"
    )
    final_event_id = first_build.json()["final_event_id"]
    by_id = owner.get(f"/api/simulado-final-pedagogical-event/{final_event_id}")
    after_controlled = repository.get_simulado_controlled_runtime_commit_execution_by_id(
        controlled_execution.controlled_execution_id,
        user_id=owner_user_id,
    )
    listed = repository.list_user_simulado_final_pedagogical_update_events(user_id=owner_user_id)

    assert missing.status_code == 404
    assert first_build.status_code == 200
    assert second_build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert first_build.json() == second_build.json() == loaded.json() == by_id.json()
    assert len(listed) == 1
    assert before_controlled is not None
    assert after_controlled is not None
    assert before_controlled.model_dump(mode="json") == after_controlled.model_dump(mode="json")

    response_payload = loaded.json()
    _assert_no_leakage(response_payload)
    assert response_payload["source_controlled_execution_id"] == controlled_execution.controlled_execution_id
    assert response_payload["final_pedagogical_update_event_created"] is True
    assert response_payload["final_pedagogical_update_event_applied"] is False
    assert response_payload["final_pedagogical_update_event_apply_allowed"] is False
    assert response_payload["execution_started"] is False
    assert response_payload["commit_executed"] is False
    assert response_payload["mutation_committed"] is False
    assert response_payload["runtime_application_enabled"] is False
    assert response_payload["runtime_application_applied"] is False
    assert response_payload["progress_mutation_enabled"] is False
    assert response_payload["progress_mutation_applied"] is False
    assert response_payload["answer_key_publicly_exposed"] is False
    assert response_payload["gabarito_publicly_exposed"] is False

    assert anonymous.post(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-final-pedagogical-event/{final_event_id}"
    ).status_code == 401

    assert other.post(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-controlled-execution/{controlled_execution.controlled_execution_id}/final-pedagogical-event"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-final-pedagogical-event/{final_event_id}"
    ).status_code == 404
