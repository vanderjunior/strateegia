import json

from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_commit_execution_plans import (
    approval_not_approved_fixture,
    approved_for_future_review_fixture,
    api_readonly_fixture,
    audit_checkpoint_fixture,
    build_runtime_commit_execution_plan,
    confirmations_incomplete_fixture,
    execution_disabled_fixture,
    mixed_execution_plan_fixture,
    missing_explicit_execution_approval_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture,
    payload_idempotency_fixture,
    plan_summary_fixture,
    planned_progress_steps_fixture,
    planned_surface_steps_fixture,
    progress_approvals_not_ready_fixture,
    rollback_checkpoint_fixture,
    surface_approvals_not_ready_fixture,
    unsafe_source_fixture,
)


FORBIDDEN_EXECUTION_PLAN_KEYS = {
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

ALLOWED_PHASE_TYPES = {
    "preflight_validation",
    "rollback_checkpoint_validation",
    "progress_step_review",
    "surface_step_review",
    "audit_checkpoint_review",
    "final_execution_review",
    "unknown",
}

ALLOWED_TARGET_TYPES = {
    "user_progress",
    "topic_progress",
    "subtopic_progress",
    "microtopic_progress",
    "subject_progress",
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

ALLOWED_SURFACE_TYPES = {
    "progress",
    "ranking",
    "retention",
    "scheduler",
    "study_cycle",
    "curriculum_graph",
    "adaptive_tuning",
    "unknown",
}

ALLOWED_UPDATE_KINDS = {
    "progress_delta",
    "ranking_signal",
    "retention_signal",
    "scheduler_signal",
    "study_cycle_signal",
    "curriculum_graph_signal",
    "adaptive_tuning_signal",
    "unknown",
}

ALLOWED_ROLLBACK_CHECKPOINT_TYPES = {
    "rollback_plan_available",
    "rollback_verified",
    "rollback_snapshot_reference_safe",
    "rollback_human_review",
    "unknown",
}

ALLOWED_AUDIT_CHECKPOINT_TYPES = {
    "final_execution_approval",
    "audit_confirmation",
    "runtime_surface_confirmation",
    "public_answer_key_absence_confirmation",
    "human_review_confirmation",
    "no_commit_execution_confirmation",
    "unknown",
}


def test_runtime_commit_execution_plan_handles_missing_explicit_execution_approval_safely(tmp_path):
    fixture = missing_explicit_execution_approval_fixture(tmp_path)

    assert build_runtime_commit_execution_plan(fixture) is None
    assert fixture.context.repository.list_user_simulado_runtime_commit_execution_plans(
        user_id=fixture.context.user_id
    ) == []


def test_runtime_commit_execution_plan_covers_approval_and_blocker_scenarios_conservatively(tmp_path):
    not_approved = build_runtime_commit_execution_plan(
        approval_not_approved_fixture(tmp_path / "not-approved")
    )
    approved = build_runtime_commit_execution_plan(
        approved_for_future_review_fixture(tmp_path / "approved")
    )
    confirmations_incomplete = build_runtime_commit_execution_plan(
        confirmations_incomplete_fixture(tmp_path / "confirmations")
    )
    progress_blocked = build_runtime_commit_execution_plan(
        progress_approvals_not_ready_fixture(tmp_path / "progress")
    )
    surface_blocked = build_runtime_commit_execution_plan(
        surface_approvals_not_ready_fixture(tmp_path / "surface")
    )
    execution_disabled = build_runtime_commit_execution_plan(
        execution_disabled_fixture(tmp_path / "disabled")
    )
    unsafe = build_runtime_commit_execution_plan(unsafe_source_fixture(tmp_path / "unsafe"))

    assert not_approved is not None
    assert not_approved.readiness_state == "blocked_by_execution_approval_not_approved"
    assert not_approved.execution_allowed_now is False
    assert not_approved.commit_executed is False

    assert approved is not None
    assert approved.execution_plan_created is True
    assert approved.execution_plan_mode in {"execution_plan_only", "dry_run_execution_plan"}
    assert approved.execution_allowed_now is False
    assert approved.execution_started is False
    assert approved.commit_execution_allowed is False
    assert approved.commit_execution_started is False
    assert approved.commit_executed is False
    assert approved.mutation_committed is False
    assert approved.execution_plan_ready_for_future_execution_review is True
    assert approved.readiness_state in {
        "blocked_by_execution_now_not_allowed",
        "ready_for_future_controlled_execution_review",
    }

    assert confirmations_incomplete is not None
    assert confirmations_incomplete.readiness_state == "blocked_by_confirmations_incomplete"

    assert progress_blocked is not None
    assert progress_blocked.readiness_state == "blocked_by_progress_approvals_not_ready"

    assert surface_blocked is not None
    assert surface_blocked.readiness_state == "blocked_by_surface_approvals_not_ready"

    assert execution_disabled is not None
    assert execution_disabled.readiness_state == "blocked_by_execution_disabled"

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    assert unsafe.answer_key_publicly_exposed is False
    assert unsafe.gabarito_publicly_exposed is False


def test_runtime_commit_execution_plan_builds_summary_phases_steps_and_checkpoints(tmp_path):
    summary = build_runtime_commit_execution_plan(plan_summary_fixture(tmp_path / "summary"))
    progress = build_runtime_commit_execution_plan(
        planned_progress_steps_fixture(tmp_path / "progress")
    )
    surface = build_runtime_commit_execution_plan(
        planned_surface_steps_fixture(tmp_path / "surface")
    )
    rollback = build_runtime_commit_execution_plan(
        rollback_checkpoint_fixture(tmp_path / "rollback")
    )
    audit = build_runtime_commit_execution_plan(audit_checkpoint_fixture(tmp_path / "audit"))

    assert summary is not None
    assert summary.plan_summary.source_approval_present is True
    assert summary.plan_summary.source_approval_recorded is True
    assert summary.plan_summary.source_approval_future_review_approved is True
    assert summary.plan_summary.source_approved_for_execution_now is False
    assert summary.plan_summary.plan_ready_for_future_execution_review is True
    assert summary.plan_summary.execution_allowed_now is False
    assert summary.plan_summary.progress_approval_count >= 1
    assert summary.plan_summary.surface_approval_count >= 1

    expected_phase_types = [
        "preflight_validation",
        "rollback_checkpoint_validation",
        "progress_step_review",
        "surface_step_review",
        "audit_checkpoint_review",
        "final_execution_review",
    ]
    assert [phase.phase_type for phase in summary.planned_execution_phases] == expected_phase_types
    for index, phase in enumerate(summary.planned_execution_phases, start=1):
        assert phase.phase_type in ALLOWED_PHASE_TYPES
        assert phase.phase_order == index
        assert phase.completed is False
        assert phase.execution_allowed is False
        assert phase.executed is False

    assert progress is not None
    for step in progress.planned_progress_steps:
        assert step.target_type in ALLOWED_TARGET_TYPES
        assert step.delta_kind in ALLOWED_DELTA_KINDS
        assert step.executed is False
        assert step.execution_allowed is False

    assert surface is not None
    for step in surface.planned_surface_steps:
        assert step.surface_type in ALLOWED_SURFACE_TYPES
        assert step.update_kind in ALLOWED_UPDATE_KINDS
        assert step.executed is False
        assert step.execution_allowed is False

    assert rollback is not None
    assert rollback.rollback_checkpoints
    for checkpoint in rollback.rollback_checkpoints:
        assert checkpoint.checkpoint_type in ALLOWED_ROLLBACK_CHECKPOINT_TYPES
        assert checkpoint.required is True
        assert checkpoint.completed is False
        assert checkpoint.execution_allowed is False

    assert audit is not None
    assert audit.audit_checkpoints
    for checkpoint in audit.audit_checkpoints:
        assert checkpoint.checkpoint_type in ALLOWED_AUDIT_CHECKPOINT_TYPES
        assert checkpoint.required is True
        assert checkpoint.completed is False
        assert checkpoint.execution_allowed is False


def test_runtime_commit_execution_plan_preserves_no_leakage_no_execution_and_no_runtime_mutation(
    tmp_path,
):
    safe = build_runtime_commit_execution_plan(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe")
    )
    mixed = build_runtime_commit_execution_plan(
        mixed_execution_plan_fixture(tmp_path / "mixed")
    )
    mutation = build_runtime_commit_execution_plan(
        no_runtime_mutation_fixture(tmp_path / "mutation")
    )

    assert safe is not None
    dumped_payload = safe.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_EXECUTION_PLAN_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped

    assert mixed is not None
    assert mixed.blockers

    assert mutation is not None
    assert mutation.execution_allowed_now is False
    assert mutation.execution_started is False
    assert mutation.commit_execution_allowed is False
    assert mutation.commit_execution_started is False
    assert mutation.commit_executed is False
    assert mutation.mutation_committed is False
    assert mutation.runtime_application_enabled is False
    assert mutation.runtime_application_applied is False
    assert mutation.progress_mutation_enabled is False
    assert mutation.progress_mutation_applied is False
    assert mutation.ranking_update_enabled is False
    assert mutation.ranking_update_applied is False
    assert mutation.retention_update_enabled is False
    assert mutation.retention_update_applied is False
    assert mutation.scheduler_update_enabled is False
    assert mutation.scheduler_update_applied is False
    assert mutation.study_cycle_update_enabled is False
    assert mutation.study_cycle_update_applied is False
    assert mutation.curriculum_graph_update_enabled is False
    assert mutation.curriculum_graph_update_applied is False
    assert mutation.adaptive_tuning_enabled is False
    assert mutation.adaptive_tuning_applied is False
    assert mutation.no_commit_execution is True
    assert mutation.no_commit_execution_event_created is True
    assert mutation.no_mutation_commit is True
    assert mutation.no_mutation_commit_event_created is True
    assert mutation.no_runtime_application is True
    assert mutation.no_progress_mutation is True
    assert mutation.no_ranking_update is True
    assert mutation.no_retention_update is True
    assert mutation.no_scheduler_update is True
    assert mutation.no_study_cycle_update is True
    assert mutation.no_curriculum_graph_update is True
    assert mutation.no_adaptive_tuning_update is True
    assert mutation.no_final_pedagogical_update_event is True


def test_runtime_commit_execution_plan_is_idempotent_for_same_source_execution_approval(tmp_path):
    fixture = payload_idempotency_fixture(tmp_path)

    first = build_runtime_commit_execution_plan(fixture)
    second = build_runtime_commit_execution_plan(fixture)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert fixture.context.repository.get_simulado_runtime_commit_execution_plan(
        first.source_execution_approval_id,
        user_id=fixture.context.user_id,
    ) is not None
    assert fixture.context.repository.get_simulado_runtime_commit_execution_plan_by_id(
        first.execution_plan_id,
        user_id=fixture.context.user_id,
    ) is not None

