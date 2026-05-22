import json

from app.services.simulado_controlled_commit_execution_guardrail import (
    SimuladoControlledRuntimeCommitExecutionGuardrailService,
)
from tests.fixtures.simulado_controlled_commit_execution_guardrails import (
    api_readonly_fixture,
    audit_requirements_shape_fixture,
    audit_requirements_unsatisfied_fixture,
    audit_trail_fixture,
    build_controlled_commit_execution_guardrail,
    commit_execution_disabled_fixture,
    commit_execution_not_ready_fixture,
    commit_transaction_not_valid_fixture,
    final_execution_approval_missing_fixture,
    idempotency_fixture,
    missing_commit_transaction_fixture,
    mixed_execution_guardrail_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture,
    planned_progress_commits_not_executable_fixture,
    planned_surface_commits_not_executable_fixture,
    progress_commit_checks_shape_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_execution_readiness_shape_fixture,
    rollback_not_ready_fixture,
    runtime_surface_risk_summary_fixture,
    surface_commit_checks_shape_fixture,
    transaction_already_executed_fixture,
    transaction_not_plan_only_fixture,
    transaction_plan_only_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_GUARDRAIL_KEYS = {
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


def test_controlled_commit_execution_guardrail_handles_missing_commit_transaction_safely(tmp_path):
    fixture = missing_commit_transaction_fixture(tmp_path)

    assert build_controlled_commit_execution_guardrail(fixture) is None
    assert fixture.context.repository.list_user_simulado_controlled_commit_execution_guardrails(
        user_id=fixture.context.user_id
    ) == []


def test_controlled_commit_execution_guardrail_blocks_invalid_commit_transaction_states(tmp_path):
    plan_only = build_controlled_commit_execution_guardrail(transaction_plan_only_fixture(tmp_path / "plan-only"))
    not_plan_only = build_controlled_commit_execution_guardrail(
        transaction_not_plan_only_fixture(tmp_path / "not-plan-only")
    )
    already_executed = build_controlled_commit_execution_guardrail(
        transaction_already_executed_fixture(tmp_path / "already-executed")
    )
    transaction_invalid = build_controlled_commit_execution_guardrail(
        commit_transaction_not_valid_fixture(tmp_path / "transaction-invalid")
    )
    execution_not_ready = build_controlled_commit_execution_guardrail(
        commit_execution_not_ready_fixture(tmp_path / "execution-not-ready")
    )
    rollback_not_ready = build_controlled_commit_execution_guardrail(
        rollback_not_ready_fixture(tmp_path / "rollback-not-ready")
    )
    progress_blocked = build_controlled_commit_execution_guardrail(
        planned_progress_commits_not_executable_fixture(tmp_path / "progress-blocked")
    )
    surface_blocked = build_controlled_commit_execution_guardrail(
        planned_surface_commits_not_executable_fixture(tmp_path / "surface-blocked")
    )
    audit_blocked = build_controlled_commit_execution_guardrail(
        audit_requirements_unsatisfied_fixture(tmp_path / "audit-blocked")
    )
    final_approval_missing = build_controlled_commit_execution_guardrail(
        final_execution_approval_missing_fixture(tmp_path / "final-approval-missing")
    )
    execution_disabled = build_controlled_commit_execution_guardrail(
        commit_execution_disabled_fixture(tmp_path / "execution-disabled")
    )
    unsafe = build_controlled_commit_execution_guardrail(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )

    assert plan_only is not None
    assert plan_only.execution_guardrail_mode in {"execution_guardrail_only", "controlled_execution_readiness"}
    assert plan_only.execution_guardrail_created is True
    assert plan_only.commit_execution_allowed is False
    assert plan_only.commit_execution_started is False
    assert plan_only.commit_executed is False
    assert plan_only.mutation_committed is False

    assert not_plan_only is not None
    assert not_plan_only.readiness_state == "blocked_by_transaction_not_plan_only"

    assert already_executed is not None
    assert already_executed.readiness_state == "blocked_by_transaction_already_executed"

    assert transaction_invalid is not None
    assert transaction_invalid.readiness_state == "blocked_by_commit_transaction_not_valid_for_execution"

    assert execution_not_ready is not None
    assert execution_not_ready.readiness_state == "blocked_by_commit_execution_not_ready"

    assert rollback_not_ready is not None
    assert rollback_not_ready.readiness_state == "blocked_by_rollback_not_ready"
    assert rollback_not_ready.rollback_readiness.rollback_execution_ready is False

    assert progress_blocked is not None
    assert progress_blocked.readiness_state == "blocked_by_progress_commits_not_executable"

    assert surface_blocked is not None
    assert surface_blocked.readiness_state == "blocked_by_surface_commits_not_executable"

    assert audit_blocked is not None
    assert audit_blocked.readiness_state == "blocked_by_audit_requirements_unsatisfied"

    assert final_approval_missing is not None
    assert final_approval_missing.readiness_state == "blocked_by_final_execution_approval_missing"

    assert execution_disabled is not None
    assert execution_disabled.readiness_state == "blocked_by_commit_execution_disabled"

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"


def test_controlled_commit_execution_guardrail_builds_bounded_checks_summaries_and_audit_requirements(tmp_path):
    progress = build_controlled_commit_execution_guardrail(
        progress_commit_checks_shape_fixture(tmp_path / "progress")
    )
    surface = build_controlled_commit_execution_guardrail(
        surface_commit_checks_shape_fixture(tmp_path / "surface")
    )
    rollback = build_controlled_commit_execution_guardrail(
        rollback_execution_readiness_shape_fixture(tmp_path / "rollback")
    )
    risk = build_controlled_commit_execution_guardrail(
        runtime_surface_risk_summary_fixture(tmp_path / "risk")
    )
    requirements = build_controlled_commit_execution_guardrail(
        audit_requirements_shape_fixture(tmp_path / "requirements")
    )
    audit = build_controlled_commit_execution_guardrail(
        audit_trail_fixture(tmp_path / "audit")
    )
    mixed = build_controlled_commit_execution_guardrail(
        mixed_execution_guardrail_fixture(tmp_path / "mixed")
    )

    assert progress is not None
    assert progress.readiness_summary.source_commit_transaction_present is True
    assert progress.readiness_summary.source_transaction_plan_only is True
    assert progress.readiness_summary.source_transaction_not_executed is True
    assert progress.readiness_summary.source_commit_transaction_valid_for_execution is False
    assert progress.readiness_summary.source_commit_execution_ready is False
    for item in progress.progress_commit_checks:
        assert item.target_type in ALLOWED_TARGET_TYPES
        assert item.delta_kind in ALLOWED_DELTA_KINDS
        assert item.executed is False
        assert item.execution_allowed is False

    assert surface is not None
    for item in surface.surface_commit_checks:
        assert item.surface_type in ALLOWED_SURFACE_TYPES
        assert item.update_kind in ALLOWED_UPDATE_KINDS
        assert item.executed is False
        assert item.execution_allowed is False

    assert rollback is not None
    assert rollback.rollback_readiness.rollback_required is True
    assert rollback.rollback_readiness.rollback_available is False
    assert rollback.rollback_readiness.rollback_verified is False
    assert rollback.rollback_readiness.rollback_execution_ready is False
    assert rollback.rollback_readiness.rollback_execution_performed is False

    assert risk is not None
    assert risk.runtime_surface_risk_summary.executable_surface_count == 0
    assert risk.runtime_surface_risk_summary.blocked_surface_count >= 0
    assert risk.runtime_surface_risk_summary.risky_surface_count >= 0

    assert requirements is not None
    requirement_types = {item.requirement_type for item in requirements.audit_requirements}
    assert requirement_types == {
        "final_execution_approval",
        "rollback_execution_confirmation",
        "audit_confirmation",
        "runtime_surface_confirmation",
        "public_answer_key_absence_confirmation",
        "human_review_confirmation",
    }
    for item in requirements.audit_requirements:
        assert item.required is True
        assert item.satisfied is False

    assert audit is not None
    events = {item.event_type for item in audit.audit_trail}
    assert "execution_guardrail_created" in events
    assert "execution_blocked" in events
    assert "commit_transaction_not_valid_for_execution" in events
    assert "commit_execution_not_ready" in events
    assert "rollback_not_ready" in events
    assert "progress_commits_not_executable" in events
    assert "surface_commits_not_executable" in events
    assert "audit_requirements_unsatisfied" in events
    assert "final_execution_approval_missing" in events
    assert "no_commit_execution" in events
    assert "no_mutation_commit" in events
    assert "no_runtime_application" in events
    assert "no_progress_mutation" in events
    assert "no_final_pedagogical_update_event" in events

    assert mixed is not None
    assert mixed.blockers


def test_controlled_commit_execution_guardrail_preserves_no_leakage_no_execution_and_no_runtime_mutation(tmp_path):
    safe = build_controlled_commit_execution_guardrail(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe")
    )
    mutation = build_controlled_commit_execution_guardrail(
        no_runtime_mutation_fixture(tmp_path / "mutation")
    )

    assert safe is not None
    dumped_payload = safe.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_GUARDRAIL_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped

    assert mutation is not None
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


def test_controlled_commit_execution_guardrail_is_deterministic_and_read_only_for_same_source(tmp_path):
    fixture = api_readonly_fixture(tmp_path)
    source_transaction = fixture.commit_transaction
    assert source_transaction is not None

    first = build_controlled_commit_execution_guardrail(fixture)
    second = build_controlled_commit_execution_guardrail(fixture)
    service = SimuladoControlledRuntimeCommitExecutionGuardrailService(fixture.context.repository)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert service.get_execution_guardrail(
        source_transaction.commit_transaction_id,
        user_id=fixture.context.user_id,
    ) is not None
    assert service.get_execution_guardrail_by_id(
        first.execution_guardrail_id,
        user_id=fixture.context.user_id,
    ) is not None

    before_transaction = fixture.context.repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        source_transaction.commit_transaction_id,
        user_id=fixture.context.user_id,
    )
    loaded = service.get_execution_guardrail(
        source_transaction.commit_transaction_id,
        user_id=fixture.context.user_id,
    )
    after_transaction = fixture.context.repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        source_transaction.commit_transaction_id,
        user_id=fixture.context.user_id,
    )
    assert loaded is not None
    assert before_transaction is not None
    assert after_transaction is not None
    assert before_transaction.model_dump(mode="json") == after_transaction.model_dump(mode="json")
