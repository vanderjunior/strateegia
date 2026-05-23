import json

from app.services.simulado_controlled_runtime_commit_execution import (
    SimuladoControlledRuntimeCommitExecutionService,
)
from tests.fixtures.simulado_controlled_runtime_commit_executions import (
    audit_verification_failed_fixture,
    audit_verification_records_fixture,
    build_controlled_runtime_commit_execution,
    dry_run_execution_summary_fixture,
    execution_allowed_now_false_fixture,
    execution_disabled_fixture,
    execution_plan_not_approved_fixture,
    execution_plan_not_ready_fixture,
    idempotency_fixture,
    mixed_controlled_execution_fixture,
    missing_execution_plan_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    phase_execution_records_fixture,
    phases_not_executable_fixture,
    progress_step_execution_records_fixture,
    progress_steps_not_executable_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_verification_failed_fixture,
    rollback_verification_records_fixture,
    surface_step_execution_records_fixture,
    surface_steps_not_executable_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_CONTROLLED_EXECUTION_KEYS = {
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
    "final_pedagogical_update_event",
}


def test_controlled_runtime_commit_execution_handles_missing_execution_plan_safely(tmp_path):
    fixture = missing_execution_plan_fixture(tmp_path)

    assert build_controlled_runtime_commit_execution(fixture) is None
    assert fixture.context.repository.list_user_simulado_controlled_runtime_commit_executions(
        user_id=fixture.context.user_id
    ) == []


def test_controlled_runtime_commit_execution_blocks_invalid_plan_states_conservatively(tmp_path):
    not_ready = build_controlled_runtime_commit_execution(
        execution_plan_not_ready_fixture(tmp_path / "not-ready")
    )
    not_approved = build_controlled_runtime_commit_execution(
        execution_plan_not_approved_fixture(tmp_path / "not-approved")
    )
    execution_now = build_controlled_runtime_commit_execution(
        execution_allowed_now_false_fixture(tmp_path / "execution-now")
    )
    phases = build_controlled_runtime_commit_execution(
        phases_not_executable_fixture(tmp_path / "phases")
    )
    progress = build_controlled_runtime_commit_execution(
        progress_steps_not_executable_fixture(tmp_path / "progress")
    )
    surface = build_controlled_runtime_commit_execution(
        surface_steps_not_executable_fixture(tmp_path / "surface")
    )
    rollback = build_controlled_runtime_commit_execution(
        rollback_verification_failed_fixture(tmp_path / "rollback")
    )
    audit = build_controlled_runtime_commit_execution(
        audit_verification_failed_fixture(tmp_path / "audit")
    )
    disabled = build_controlled_runtime_commit_execution(
        execution_disabled_fixture(tmp_path / "disabled")
    )
    unsafe = build_controlled_runtime_commit_execution(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )

    assert not_ready is not None
    assert not_ready.readiness_state == "blocked_by_execution_plan_not_ready"
    assert not_ready.execution_started is False
    assert not_ready.commit_executed is False

    assert not_approved is not None
    assert not_approved.readiness_state == "blocked_by_execution_plan_not_ready"

    assert execution_now is not None
    assert execution_now.readiness_state == "blocked_by_execution_allowed_now_false"
    assert execution_now.execution_allowed_now is False

    assert phases is not None
    assert phases.readiness_state == "blocked_by_phases_not_executable"

    assert progress is not None
    assert progress.readiness_state == "blocked_by_progress_steps_not_executable"

    assert surface is not None
    assert surface.readiness_state == "blocked_by_surface_steps_not_executable"

    assert rollback is not None
    assert rollback.readiness_state == "blocked_by_rollback_verification_failed"

    assert audit is not None
    assert audit.readiness_state == "blocked_by_audit_verification_failed"

    assert disabled is not None
    assert disabled.readiness_state == "blocked_by_execution_disabled"

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"


def test_controlled_runtime_commit_execution_builds_bounded_dry_run_records_and_summary(tmp_path):
    summary = build_controlled_runtime_commit_execution(
        dry_run_execution_summary_fixture(tmp_path / "summary")
    )
    phase_records = build_controlled_runtime_commit_execution(
        phase_execution_records_fixture(tmp_path / "phases")
    )
    progress_records = build_controlled_runtime_commit_execution(
        progress_step_execution_records_fixture(tmp_path / "progress")
    )
    surface_records = build_controlled_runtime_commit_execution(
        surface_step_execution_records_fixture(tmp_path / "surface")
    )
    rollback_records = build_controlled_runtime_commit_execution(
        rollback_verification_records_fixture(tmp_path / "rollback")
    )
    audit_records = build_controlled_runtime_commit_execution(
        audit_verification_records_fixture(tmp_path / "audit")
    )

    assert summary is not None
    assert summary.execution_summary.source_plan_present is True
    assert summary.execution_summary.source_execution_allowed_now is False
    assert summary.execution_summary.real_execution_performed is False
    assert summary.execution_summary.mutation_commit_performed is False
    assert summary.execution_summary.runtime_application_performed is False

    assert phase_records is not None
    phase_types = [item.phase_type for item in phase_records.phase_execution_records]
    assert phase_types == [
        "preflight_validation",
        "rollback_checkpoint_validation",
        "progress_step_review",
        "surface_step_review",
        "audit_checkpoint_review",
        "final_execution_review",
    ]
    for index, item in enumerate(phase_records.phase_execution_records, start=1):
        assert item.phase_order == index
        assert item.evaluated is True
        assert item.execution_allowed is False
        assert item.executed is False

    assert progress_records is not None
    for item in progress_records.progress_step_execution_records:
        assert item.target_type in {
            "user_progress",
            "topic_progress",
            "subtopic_progress",
            "microtopic_progress",
            "subject_progress",
            "unknown",
        }
        assert item.delta_kind in {
            "mastery_delta",
            "completion_delta",
            "accuracy_delta",
            "review_signal_delta",
            "confidence_delta",
            "unknown",
        }
        assert item.evaluated is True
        assert item.execution_allowed is False
        assert item.executed is False

    assert surface_records is not None
    for item in surface_records.surface_step_execution_records:
        assert item.surface_type in {
            "progress",
            "ranking",
            "retention",
            "scheduler",
            "study_cycle",
            "curriculum_graph",
            "adaptive_tuning",
            "unknown",
        }
        assert item.update_kind in {
            "progress_delta",
            "ranking_signal",
            "retention_signal",
            "scheduler_signal",
            "study_cycle_signal",
            "curriculum_graph_signal",
            "adaptive_tuning_signal",
            "unknown",
        }
        assert item.evaluated is True
        assert item.execution_allowed is False
        assert item.executed is False

    assert rollback_records is not None
    for item in rollback_records.rollback_verification_records:
        assert item.evaluated is True
        assert item.execution_allowed is False
        assert item.executed is False

    assert audit_records is not None
    for item in audit_records.audit_verification_records:
        assert item.evaluated is True
        assert item.execution_allowed is False
        assert item.executed is False


def test_controlled_runtime_commit_execution_preserves_no_leakage_no_execution_and_no_runtime_mutation(
    tmp_path,
):
    safe = build_controlled_runtime_commit_execution(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe")
    )
    no_runtime_application = build_controlled_runtime_commit_execution(
        no_runtime_application_fixture(tmp_path / "no-runtime-application")
    )
    no_runtime_mutation = build_controlled_runtime_commit_execution(
        no_runtime_mutation_fixture(tmp_path / "no-runtime-mutation")
    )
    mixed = build_controlled_runtime_commit_execution(
        mixed_controlled_execution_fixture(tmp_path / "mixed")
    )

    assert safe is not None
    dumped_payload = safe.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_CONTROLLED_EXECUTION_KEYS:
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
    assert no_runtime_mutation.execution_started is False
    assert no_runtime_mutation.execution_completed is False
    assert no_runtime_mutation.execution_succeeded is False
    assert no_runtime_mutation.execution_failed is False
    assert no_runtime_mutation.execution_allowed_now is False
    assert no_runtime_mutation.commit_execution_allowed is False
    assert no_runtime_mutation.commit_execution_started is False
    assert no_runtime_mutation.commit_executed is False
    assert no_runtime_mutation.mutation_committed is False
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
    assert no_runtime_mutation.no_final_pedagogical_update_event is True
    assert no_runtime_mutation.final_pedagogical_update_event_created is False

    assert mixed is not None
    assert mixed.blockers
    assert mixed.audit_trail


def test_controlled_runtime_commit_execution_is_idempotent_and_does_not_mutate_sources(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    result = build_controlled_runtime_commit_execution(fixture)
    assert result is not None
    execution_plan = fixture.execution_plan
    assert execution_plan is not None
    service = SimuladoControlledRuntimeCommitExecutionService(fixture.context.repository)

    before_plan = fixture.context.repository.get_simulado_runtime_commit_execution_plan_by_id(
        execution_plan.execution_plan_id,
        user_id=fixture.context.user_id,
    )
    before_approval = fixture.context.repository.get_simulado_explicit_commit_execution_approval_by_id(
        execution_plan.source_execution_approval_id,
        user_id=fixture.context.user_id,
    )
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_controlled_execution(
        execution_plan.execution_plan_id,
        user_id=fixture.context.user_id,
    )
    second = service.build_controlled_execution(
        execution_plan.execution_plan_id,
        user_id=fixture.context.user_id,
    )
    by_source = fixture.context.repository.get_simulado_controlled_runtime_commit_execution(
        execution_plan.execution_plan_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_controlled_runtime_commit_execution_by_id(
        result.controlled_execution_id,
        user_id=fixture.context.user_id,
    )
    listed = fixture.context.repository.list_user_simulado_controlled_runtime_commit_executions(
        user_id=fixture.context.user_id
    )

    after_plan = fixture.context.repository.get_simulado_runtime_commit_execution_plan_by_id(
        execution_plan.execution_plan_id,
        user_id=fixture.context.user_id,
    )
    after_approval = fixture.context.repository.get_simulado_explicit_commit_execution_approval_by_id(
        execution_plan.source_execution_approval_id,
        user_id=fixture.context.user_id,
    )
    after_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    assert first is not None
    assert second is not None
    assert by_source is not None
    assert by_id is not None
    assert len(listed) == 1
    assert result.model_dump(mode="json") == first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source.model_dump(mode="json") == result.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == result.model_dump(mode="json")
    assert before_plan is not None and after_plan is not None
    assert before_approval is not None and after_approval is not None
    assert before_plan.model_dump(mode="json") == after_plan.model_dump(mode="json")
    assert before_approval.model_dump(mode="json") == after_approval.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
