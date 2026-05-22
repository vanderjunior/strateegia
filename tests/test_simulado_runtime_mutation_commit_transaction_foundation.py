import json

from app.services.simulado_runtime_mutation_commit_transaction import (
    SimuladoRuntimeMutationCommitTransactionService,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_mutation_commit_transactions import (
    api_readonly_fixture,
    approved_for_future_review_fixture,
    build_runtime_mutation_commit_transaction,
    commit_execution_disabled_fixture,
    commit_shell_not_pre_commit_only_fixture,
    confirmations_incomplete_fixture,
    delta_approvals_not_ready_fixture,
    explicit_commit_not_approved_fixture,
    missing_explicit_commit_fixture,
    missing_rollback_execution_plan_fixture,
    missing_source_mutation_transaction_fixture,
    mixed_commit_transaction_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_unavailable_fixture,
    rollback_unverified_fixture,
    surface_approvals_not_ready_fixture,
)


FORBIDDEN_COMMIT_TRANSACTION_KEYS = {
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


def test_runtime_mutation_commit_transaction_handles_missing_explicit_commit_safely(tmp_path):
    fixture = missing_explicit_commit_fixture(tmp_path)

    assert build_runtime_mutation_commit_transaction(fixture) is None
    assert fixture.context.repository.list_user_simulado_runtime_mutation_commit_transactions(
        user_id=fixture.context.user_id
    ) == []


def test_runtime_mutation_commit_transaction_builds_blocked_plan_from_explicit_commit_states(tmp_path):
    not_approved = build_runtime_mutation_commit_transaction(
        explicit_commit_not_approved_fixture(tmp_path / "not-approved")
    )
    approved_future = build_runtime_mutation_commit_transaction(
        approved_for_future_review_fixture(tmp_path / "approved-future")
    )
    confirmations_incomplete = build_runtime_mutation_commit_transaction(
        confirmations_incomplete_fixture(tmp_path / "confirmations-incomplete")
    )

    assert not_approved is not None
    assert not_approved.readiness_state == "blocked_by_explicit_commit_not_approved"
    assert not_approved.commit_transaction_valid_for_execution is False
    assert not_approved.commit_executed is False

    assert approved_future is not None
    assert approved_future.commit_transaction_created is True
    assert approved_future.commit_transaction_mode in {"commit_plan_only", "dry_run_commit_transaction"}
    assert approved_future.readiness_state == "blocked_by_commit_now_not_allowed"
    assert approved_future.commit_transaction_valid_for_execution is False
    assert approved_future.commit_execution_ready is False
    assert approved_future.commit_executed is False

    assert confirmations_incomplete is not None
    assert "blocked_by_confirmations_incomplete" in {item.code for item in confirmations_incomplete.blockers}
    assert confirmations_incomplete.commit_executed is False


def test_runtime_mutation_commit_transaction_handles_shell_source_rollback_and_approval_blockers(tmp_path):
    shell_blocked = build_runtime_mutation_commit_transaction(
        commit_shell_not_pre_commit_only_fixture(tmp_path / "shell")
    )
    missing_source = build_runtime_mutation_commit_transaction(
        missing_source_mutation_transaction_fixture(tmp_path / "missing-source")
    )
    missing_rollback = build_runtime_mutation_commit_transaction(
        missing_rollback_execution_plan_fixture(tmp_path / "missing-rollback")
    )
    rollback_unavailable = build_runtime_mutation_commit_transaction(
        rollback_unavailable_fixture(tmp_path / "rollback-unavailable")
    )
    rollback_unverified = build_runtime_mutation_commit_transaction(
        rollback_unverified_fixture(tmp_path / "rollback-unverified")
    )
    deltas_blocked = build_runtime_mutation_commit_transaction(
        delta_approvals_not_ready_fixture(tmp_path / "deltas")
    )
    surfaces_blocked = build_runtime_mutation_commit_transaction(
        surface_approvals_not_ready_fixture(tmp_path / "surfaces")
    )
    execution_disabled = build_runtime_mutation_commit_transaction(
        commit_execution_disabled_fixture(tmp_path / "disabled")
    )

    assert shell_blocked is not None
    assert shell_blocked.readiness_state == "blocked_by_commit_shell_not_pre_commit_only"

    assert missing_source is not None
    assert missing_source.readiness_state == "blocked_by_missing_source_mutation_transaction"

    assert missing_rollback is not None
    assert "blocked_by_missing_rollback_execution_plan" in {item.code for item in missing_rollback.blockers}

    assert rollback_unavailable is not None
    assert "blocked_by_rollback_not_available" in {item.code for item in rollback_unavailable.blockers}
    assert rollback_unavailable.rollback_execution_plan.rollback_required is True
    assert rollback_unavailable.rollback_execution_plan.rollback_available is False
    assert rollback_unavailable.rollback_execution_plan.rollback_verified is False
    assert rollback_unavailable.rollback_execution_plan.rollback_execution_ready is False

    assert rollback_unverified is not None
    assert "blocked_by_rollback_not_verified" in {item.code for item in rollback_unverified.blockers}
    assert rollback_unverified.rollback_execution_plan.rollback_required is True
    assert rollback_unverified.rollback_execution_plan.rollback_available is True
    assert rollback_unverified.rollback_execution_plan.rollback_verified is False
    assert rollback_unverified.rollback_execution_plan.rollback_execution_ready is False

    assert deltas_blocked is not None
    assert "blocked_by_delta_approvals_not_ready" in {item.code for item in deltas_blocked.blockers}

    assert surfaces_blocked is not None
    assert "blocked_by_surface_approvals_not_ready" in {item.code for item in surfaces_blocked.blockers}

    assert execution_disabled is not None
    assert execution_disabled.readiness_state == "blocked_by_commit_execution_disabled"
    assert execution_disabled.runtime_application_enabled is False
    assert execution_disabled.progress_mutation_enabled is False


def test_runtime_mutation_commit_transaction_builds_bounded_planned_commits_validation_and_audit(tmp_path):
    result = build_runtime_mutation_commit_transaction(
        approved_for_future_review_fixture(tmp_path / "approved")
    )
    mixed = build_runtime_mutation_commit_transaction(
        mixed_commit_transaction_fixture(tmp_path / "mixed")
    )

    assert result is not None
    assert result.validation_summary.source_explicit_commit_present is True
    assert result.validation_summary.explicit_commit_recorded is True
    assert result.validation_summary.explicit_commit_approved is True
    assert result.validation_summary.approved_for_future_mutation_commit_review is True
    assert result.validation_summary.approved_for_commit_now is False
    assert result.validation_summary.confirmations_satisfied is True
    assert result.validation_summary.source_commit_shell_present is True
    assert result.validation_summary.source_commit_shell_pre_commit_only is True
    assert result.validation_summary.source_mutation_transaction_present is True
    assert result.validation_summary.transaction_valid_for_execution is False
    assert result.validation_summary.transaction_execution_ready is False

    assert result.planned_progress_commits
    for planned in result.planned_progress_commits:
        assert planned.target_type in ALLOWED_TARGET_TYPES
        assert planned.delta_kind in ALLOWED_DELTA_KINDS
        assert planned.committed is False
        assert planned.execution_allowed is False

    assert result.planned_surface_commits
    for planned in result.planned_surface_commits:
        assert planned.surface_type in ALLOWED_SURFACE_TYPES
        assert planned.update_kind in ALLOWED_UPDATE_KINDS
        assert planned.committed is False
        assert planned.execution_allowed is False

    assert result.rollback_execution_plan.rollback_required is True
    assert result.rollback_execution_plan.rollback_execution_performed is False

    audit_events = {item.event_type for item in result.audit_trail}
    assert "commit_transaction_created" in audit_events
    assert "commit_plan_created" in audit_events
    assert "commit_transaction_blocked" in audit_events
    assert "commit_now_not_allowed" in audit_events
    assert "no_commit_execution" in audit_events
    assert "no_mutation_commit" in audit_events
    assert "no_runtime_application" in audit_events
    assert "no_progress_mutation" in audit_events
    assert "no_final_pedagogical_update_event" in audit_events

    assert mixed is not None
    assert mixed.blockers


def test_runtime_mutation_commit_transaction_preserves_no_leakage_no_commit_and_no_runtime_mutation(tmp_path):
    safe = build_runtime_mutation_commit_transaction(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe")
    )
    unsafe = build_runtime_mutation_commit_transaction(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )
    mutation = build_runtime_mutation_commit_transaction(
        no_runtime_mutation_fixture(tmp_path / "mutation")
    )

    assert safe is not None
    dumped_payload = safe.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_COMMIT_TRANSACTION_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    assert unsafe.answer_key_publicly_exposed is False
    assert unsafe.gabarito_publicly_exposed is False

    assert mutation is not None
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


def test_runtime_mutation_commit_transaction_is_deterministic_and_read_only_for_same_source(tmp_path):
    fixture = api_readonly_fixture(tmp_path)
    source_explicit_commit = fixture.explicit_commit
    assert source_explicit_commit is not None

    first = build_runtime_mutation_commit_transaction(fixture)
    second = build_runtime_mutation_commit_transaction(fixture)
    service = SimuladoRuntimeMutationCommitTransactionService(fixture.context.repository)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert service.get_commit_transaction(
        source_explicit_commit.explicit_commit_id,
        user_id=fixture.context.user_id,
    ) is not None
    assert service.get_commit_transaction_by_id(
        first.commit_transaction_id,
        user_id=fixture.context.user_id,
    ) is not None

    before_explicit_commit = fixture.context.repository.get_simulado_explicit_mutation_commit_by_id(
        source_explicit_commit.explicit_commit_id,
        user_id=fixture.context.user_id,
    )
    loaded = service.get_commit_transaction(
        source_explicit_commit.explicit_commit_id,
        user_id=fixture.context.user_id,
    )
    after_explicit_commit = fixture.context.repository.get_simulado_explicit_mutation_commit_by_id(
        source_explicit_commit.explicit_commit_id,
        user_id=fixture.context.user_id,
    )

    assert loaded is not None
    assert before_explicit_commit is not None
    assert after_explicit_commit is not None
    assert before_explicit_commit.model_dump(mode="json") == after_explicit_commit.model_dump(mode="json")
