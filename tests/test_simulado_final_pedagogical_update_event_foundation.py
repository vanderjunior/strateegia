import json

from app.services.simulado_final_pedagogical_update_event import (
    SimuladoFinalPedagogicalUpdateEventService,
)
from tests.fixtures.simulado_final_pedagogical_update_events import (
    api_readonly_fixture,
    build_final_pedagogical_update_event,
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
}


def test_final_pedagogical_update_event_handles_missing_controlled_execution_safely(tmp_path):
    fixture = missing_controlled_execution_fixture(tmp_path)

    assert build_final_pedagogical_update_event(fixture) is None
    assert fixture.context.repository.list_user_simulado_final_pedagogical_update_events(
        user_id=fixture.context.user_id
    ) == []


def test_final_pedagogical_update_event_blocks_invalid_source_states_conservatively(tmp_path):
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
        runtime_application_detected_fixture(tmp_path / "runtime-application")
    )
    progress_detected = build_final_pedagogical_update_event(
        progress_mutation_detected_fixture(tmp_path / "progress-mutation")
    )
    apply_disabled = build_final_pedagogical_update_event(
        final_event_apply_disabled_fixture(tmp_path / "apply-disabled")
    )
    disabled = build_final_pedagogical_update_event(
        execution_disabled_fixture(tmp_path / "execution-disabled")
    )
    unsafe = build_final_pedagogical_update_event(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )

    assert not_dry_run is not None
    assert not_dry_run.readiness_state == "blocked_by_controlled_execution_not_dry_run"
    assert not_dry_run.final_pedagogical_update_event_applied is False

    assert started is not None
    assert started.readiness_state == "blocked_by_controlled_execution_started"

    assert commit_executed is not None
    assert commit_executed.readiness_state == "blocked_by_commit_executed"

    assert mutation_committed is not None
    assert mutation_committed.readiness_state == "blocked_by_mutation_committed"

    assert runtime_detected is not None
    assert runtime_detected.readiness_state == "blocked_by_runtime_application_detected"

    assert progress_detected is not None
    assert progress_detected.readiness_state == "blocked_by_progress_mutation_detected"

    assert apply_disabled is not None
    assert apply_disabled.readiness_state == "blocked_by_final_event_apply_disabled"
    assert apply_disabled.final_pedagogical_update_event_apply_allowed is False

    assert disabled is not None
    assert disabled.readiness_state == "blocked_by_final_event_apply_disabled"

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"


def test_final_pedagogical_update_event_builds_bounded_summary_updates_and_audit_trail(tmp_path):
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
    assert summary.event_summary.final_event_apply_allowed is False
    assert summary.event_summary.final_event_applied is False

    assert progress is not None
    assert progress.proposed_progress_updates
    for item in progress.proposed_progress_updates:
        assert item.proposed is True
        assert item.applied is False
        assert item.apply_allowed is False

    assert ranking is not None
    for item in ranking.proposed_ranking_updates:
        assert item.proposed is True
        assert item.applied is False
        assert item.apply_allowed is False

    assert retention is not None
    for item in retention.proposed_retention_updates:
        assert item.proposed is True
        assert item.applied is False
        assert item.apply_allowed is False

    assert scheduler is not None
    for item in scheduler.proposed_scheduler_updates:
        assert item.proposed is True
        assert item.applied is False
        assert item.apply_allowed is False

    assert study_cycle is not None
    for item in study_cycle.proposed_study_cycle_updates:
        assert item.proposed is True
        assert item.applied is False
        assert item.apply_allowed is False

    assert curriculum_graph is not None
    for item in curriculum_graph.proposed_curriculum_graph_updates:
        assert item.proposed is True
        assert item.applied is False
        assert item.apply_allowed is False

    assert adaptive_tuning is not None
    for item in adaptive_tuning.proposed_adaptive_tuning_updates:
        assert item.proposed is True
        assert item.applied is False
        assert item.apply_allowed is False

    assert audit_trail is not None
    assert {
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
    }.issubset({item.event_type for item in audit_trail.audit_trail})


def test_final_pedagogical_update_event_preserves_no_leakage_and_no_runtime_mutation(tmp_path):
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
    dumped_payload = safe.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_FINAL_EVENT_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped

    assert no_runtime_application is not None
    assert no_runtime_application.runtime_application_enabled is False
    assert no_runtime_application.runtime_application_applied is False
    assert no_runtime_application.no_runtime_application is True

    assert no_runtime_mutation is not None
    assert no_runtime_mutation.final_pedagogical_update_event_created is True
    assert no_runtime_mutation.final_pedagogical_update_event_applied is False
    assert no_runtime_mutation.final_pedagogical_update_event_apply_allowed is False
    assert no_runtime_mutation.final_pedagogical_update_event_application_started is False
    assert no_runtime_mutation.final_pedagogical_update_event_application_completed is False
    assert no_runtime_mutation.execution_started is False
    assert no_runtime_mutation.commit_executed is False
    assert no_runtime_mutation.mutation_committed is False
    assert no_runtime_mutation.runtime_application_enabled is False
    assert no_runtime_mutation.runtime_application_applied is False
    assert no_runtime_mutation.progress_mutation_enabled is False
    assert no_runtime_mutation.progress_mutation_applied is False
    assert no_runtime_mutation.ranking_update_enabled is False
    assert no_runtime_mutation.ranking_update_applied is False
    assert no_runtime_mutation.retention_update_enabled is False
    assert no_runtime_mutation.retention_update_applied is False
    assert no_runtime_mutation.scheduler_update_enabled is False
    assert no_runtime_mutation.scheduler_update_applied is False
    assert no_runtime_mutation.study_cycle_update_enabled is False
    assert no_runtime_mutation.study_cycle_update_applied is False
    assert no_runtime_mutation.curriculum_graph_update_enabled is False
    assert no_runtime_mutation.curriculum_graph_update_applied is False
    assert no_runtime_mutation.adaptive_tuning_enabled is False
    assert no_runtime_mutation.adaptive_tuning_applied is False
    assert no_runtime_mutation.no_commit_execution is True
    assert no_runtime_mutation.no_commit_execution_event_created is True
    assert no_runtime_mutation.no_mutation_commit is True
    assert no_runtime_mutation.no_mutation_commit_event_created is True
    assert no_runtime_mutation.no_runtime_application is True
    assert no_runtime_mutation.no_progress_mutation is True
    assert no_runtime_mutation.no_ranking_update is True
    assert no_runtime_mutation.no_retention_update is True
    assert no_runtime_mutation.no_scheduler_update is True
    assert no_runtime_mutation.no_study_cycle_update is True
    assert no_runtime_mutation.no_curriculum_graph_update is True
    assert no_runtime_mutation.no_adaptive_tuning_update is True
    assert no_runtime_mutation.no_applied_final_pedagogical_update_event is True
    assert no_runtime_mutation.answer_key_publicly_exposed is False
    assert no_runtime_mutation.gabarito_publicly_exposed is False

    assert mixed is not None
    assert mixed.blockers
    assert mixed.audit_trail


def test_final_pedagogical_update_event_is_idempotent_and_does_not_mutate_sources(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    result = build_final_pedagogical_update_event(fixture)
    assert result is not None
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    service = SimuladoFinalPedagogicalUpdateEventService(fixture.context.repository)

    before_controlled = fixture.context.repository.get_simulado_controlled_runtime_commit_execution_by_id(
        controlled_execution.controlled_execution_id,
        user_id=fixture.context.user_id,
    )
    before_plan = fixture.context.repository.get_simulado_runtime_commit_execution_plan_by_id(
        controlled_execution.source_execution_plan_id,
        user_id=fixture.context.user_id,
    )

    loaded = service.get_final_event(
        controlled_execution.controlled_execution_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_final_event_by_id(
        result.final_event_id,
        user_id=fixture.context.user_id,
    )
    second = build_final_pedagogical_update_event(fixture)

    after_controlled = fixture.context.repository.get_simulado_controlled_runtime_commit_execution_by_id(
        controlled_execution.controlled_execution_id,
        user_id=fixture.context.user_id,
    )
    after_plan = fixture.context.repository.get_simulado_runtime_commit_execution_plan_by_id(
        controlled_execution.source_execution_plan_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_final_pedagogical_update_events(
        user_id=fixture.context.user_id,
    )

    assert loaded is not None
    assert by_id is not None
    assert second is not None
    assert before_controlled is not None
    assert before_plan is not None
    assert after_controlled is not None
    assert after_plan is not None
    assert result.model_dump(mode="json") == loaded.model_dump(mode="json")
    assert result.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert result.model_dump(mode="json") == second.model_dump(mode="json")
    assert before_controlled.model_dump(mode="json") == after_controlled.model_dump(mode="json")
    assert before_plan.model_dump(mode="json") == after_plan.model_dump(mode="json")
    assert len(listed) == 1
