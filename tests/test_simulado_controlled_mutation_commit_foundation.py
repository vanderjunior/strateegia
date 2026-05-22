import json

from app.services.simulado_controlled_mutation_commit import (
    SimuladoControlledRuntimeMutationCommitService,
)
from tests.fixtures.simulado_controlled_mutation_commit_shells import (
    api_readonly_fixture,
    audit_confirmation_missing_fixture,
    build_controlled_mutation_commit_shell,
    commit_policy_missing_fixture,
    deltas_not_commit_allowed_fixture,
    explicit_apply_not_approved_fixture,
    explicit_commit_approval_missing_fixture,
    mixed_commit_shell_fixture,
    missing_mutation_transaction_fixture,
    mutation_commit_not_ready_fixture,
    mutation_not_valid_for_commit_fixture,
    no_runtime_mutation_fixture,
    rollback_not_available_fixture,
    rollback_not_verified_fixture,
    runtime_mutation_disabled_fixture,
    surfaces_not_commit_allowed_fixture,
    transaction_already_committed_fixture,
    transaction_not_proposal_only_fixture,
    transaction_proposal_only_fixture,
    unsafe_source_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_COMMIT_SHELL_KEYS = {
    "correct_answer",
    "correct_option",
    "answer_key",
    "answer_key_value",
    "final_answer_key_content",
    "gabarito",
    "gabarito_final",
    "correctness",
    "is_correct",
    "mutation_commit_event",
    "runtime_application_event",
    "final_pedagogical_update_event",
}


def test_controlled_mutation_commit_shell_handles_missing_mutation_transaction_safely(tmp_path):
    fixture = missing_mutation_transaction_fixture(tmp_path)

    assert build_controlled_mutation_commit_shell(fixture) is None
    assert fixture.context.repository.list_user_simulado_controlled_mutation_commit_shells(
        user_id=fixture.context.user_id
    ) == []


def test_controlled_mutation_commit_shell_blocks_invalid_source_transaction_states(tmp_path):
    proposal_only = build_controlled_mutation_commit_shell(transaction_proposal_only_fixture(tmp_path / "proposal"))
    not_proposal = build_controlled_mutation_commit_shell(
        transaction_not_proposal_only_fixture(tmp_path / "not-proposal")
    )
    already_committed = build_controlled_mutation_commit_shell(
        transaction_already_committed_fixture(tmp_path / "already-committed")
    )
    mutation_invalid = build_controlled_mutation_commit_shell(
        mutation_not_valid_for_commit_fixture(tmp_path / "mutation-invalid")
    )
    mutation_not_ready = build_controlled_mutation_commit_shell(
        mutation_commit_not_ready_fixture(tmp_path / "mutation-not-ready")
    )
    rollback_missing = build_controlled_mutation_commit_shell(
        rollback_not_available_fixture(tmp_path / "rollback-missing")
    )
    rollback_unverified = build_controlled_mutation_commit_shell(
        rollback_not_verified_fixture(tmp_path / "rollback-unverified")
    )
    deltas_blocked = build_controlled_mutation_commit_shell(
        deltas_not_commit_allowed_fixture(tmp_path / "deltas")
    )
    surfaces_blocked = build_controlled_mutation_commit_shell(
        surfaces_not_commit_allowed_fixture(tmp_path / "surfaces")
    )
    commit_policy_missing = build_controlled_mutation_commit_shell(
        commit_policy_missing_fixture(tmp_path / "policy")
    )
    explicit_commit_missing = build_controlled_mutation_commit_shell(
        explicit_commit_approval_missing_fixture(tmp_path / "explicit-commit")
    )
    audit_missing = build_controlled_mutation_commit_shell(
        audit_confirmation_missing_fixture(tmp_path / "audit")
    )
    runtime_disabled = build_controlled_mutation_commit_shell(
        runtime_mutation_disabled_fixture(tmp_path / "runtime-disabled")
    )
    unsafe = build_controlled_mutation_commit_shell(unsafe_source_fixture(tmp_path / "unsafe"))
    explicit_not_approved = build_controlled_mutation_commit_shell(
        explicit_apply_not_approved_fixture(tmp_path / "explicit-not-approved")
    )

    assert proposal_only is not None
    assert proposal_only.commit_mode in {"pre_commit_shell", "controlled_commit_shell"}
    assert proposal_only.commit_status in {"commit_blocked", "commit_shell_created_not_committed"}
    assert proposal_only.commit_shell_created is True
    assert proposal_only.commit_request_accepted is False
    assert proposal_only.commit_preconditions_satisfied is False
    assert proposal_only.commit_ready_for_execution is False
    assert proposal_only.mutation_committed is False

    assert not_proposal is not None
    assert not_proposal.readiness_state == "blocked_by_transaction_not_proposal_only"

    assert already_committed is not None
    assert already_committed.readiness_state == "blocked_by_transaction_already_committed"

    assert mutation_invalid is not None
    assert mutation_invalid.readiness_state == "blocked_by_mutation_not_valid_for_commit"

    assert mutation_not_ready is not None
    assert mutation_not_ready.readiness_state == "blocked_by_mutation_commit_not_ready"

    assert rollback_missing is not None
    assert rollback_missing.readiness_state == "blocked_by_rollback_not_available"

    assert rollback_unverified is not None
    assert rollback_unverified.readiness_state == "blocked_by_rollback_not_verified"

    assert deltas_blocked is not None
    assert deltas_blocked.readiness_state == "blocked_by_deltas_not_commit_allowed"

    assert surfaces_blocked is not None
    assert surfaces_blocked.readiness_state == "blocked_by_surfaces_not_commit_allowed"

    assert commit_policy_missing is not None
    assert commit_policy_missing.readiness_state == "blocked_by_commit_policy_missing"

    assert explicit_commit_missing is not None
    assert explicit_commit_missing.readiness_state == "blocked_by_explicit_commit_approval_missing"

    assert audit_missing is not None
    assert audit_missing.readiness_state == "blocked_by_audit_confirmation_missing"

    assert runtime_disabled is not None
    assert runtime_disabled.readiness_state == "blocked_by_runtime_mutation_disabled"

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"

    assert explicit_not_approved is not None
    assert explicit_not_approved.readiness_state == "blocked_by_mutation_not_valid_for_commit"


def test_controlled_mutation_commit_shell_preserves_decisions_audit_requirements_and_no_public_answer_key(tmp_path):
    proposal_only = build_controlled_mutation_commit_shell(transaction_proposal_only_fixture(tmp_path / "proposal"))
    mixed = build_controlled_mutation_commit_shell(mixed_commit_shell_fixture(tmp_path / "mixed"))

    assert proposal_only is not None
    assert proposal_only.rollback_readiness.rollback_required is True
    assert proposal_only.rollback_readiness.rollback_available is False
    assert proposal_only.rollback_readiness.rollback_verified is False
    assert proposal_only.rollback_readiness.rollback_ready_for_commit is False

    assert proposal_only.delta_commit_decisions
    for decision in proposal_only.delta_commit_decisions:
        assert decision.target_type in {
            "user_progress",
            "topic_progress",
            "subtopic_progress",
            "microtopic_progress",
            "subject_progress",
            "unknown",
        }
        assert decision.delta_kind in {
            "mastery_delta",
            "completion_delta",
            "accuracy_delta",
            "review_signal_delta",
            "confidence_delta",
            "unknown",
        }
        assert decision.committed is False
        assert decision.commit_decision == "delta_rejected_pre_commit"

    assert proposal_only.surface_commit_decisions
    for decision in proposal_only.surface_commit_decisions:
        assert decision.surface_type in {
            "progress",
            "ranking",
            "retention",
            "scheduler",
            "study_cycle",
            "curriculum_graph",
            "adaptive_tuning",
            "unknown",
        }
        assert decision.update_kind in {
            "progress_delta",
            "ranking_signal",
            "retention_signal",
            "scheduler_signal",
            "study_cycle_signal",
            "curriculum_graph_signal",
            "adaptive_tuning_signal",
            "unknown",
        }
        assert decision.committed is False
        assert decision.commit_decision == "surface_rejected_pre_commit"

    requirement_types = {item.requirement_type for item in proposal_only.audit_requirements}
    assert requirement_types == {
        "commit_policy_confirmation",
        "explicit_commit_approval",
        "audit_confirmation",
        "rollback_verification_confirmation",
        "public_answer_key_absence_confirmation",
        "human_review_confirmation",
    }
    for item in proposal_only.audit_requirements:
        assert item.required is True
        assert item.satisfied is False

    audit_events = {item.event_type for item in proposal_only.audit_trail}
    assert "commit_shell_created" in audit_events
    assert "commit_blocked" in audit_events
    assert "mutation_not_valid_for_commit" in audit_events
    assert "mutation_commit_not_ready" in audit_events
    assert "rollback_not_available" in audit_events
    assert "no_runtime_application" in audit_events
    assert "no_progress_mutation" in audit_events
    assert "no_final_pedagogical_update_event" in audit_events

    dumped_payload = proposal_only.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_COMMIT_SHELL_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped

    assert mixed is not None
    assert mixed.blockers


def test_controlled_mutation_commit_shell_preserves_no_runtime_application_and_no_runtime_mutation(tmp_path):
    result = build_controlled_mutation_commit_shell(no_runtime_mutation_fixture(tmp_path))
    assert result is not None

    assert result.mutation_valid_for_commit is False
    assert result.mutation_commit_ready is False
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
    assert result.no_runtime_application is True
    assert result.no_progress_mutation is True
    assert result.no_ranking_update is True
    assert result.no_retention_update is True
    assert result.no_scheduler_update is True
    assert result.no_study_cycle_update is True
    assert result.no_curriculum_graph_update is True
    assert result.no_adaptive_tuning_update is True
    assert result.no_final_pedagogical_update_event is True


def test_controlled_mutation_commit_shell_is_idempotent_and_does_not_mutate_sources(tmp_path):
    fixture = api_readonly_fixture(tmp_path)
    result = build_controlled_mutation_commit_shell(fixture)
    assert result is not None
    transaction = fixture.mutation_transaction
    assert transaction is not None
    service = SimuladoControlledRuntimeMutationCommitService(fixture.context.repository)

    before_transaction = fixture.context.repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        transaction.mutation_transaction_id,
        user_id=fixture.context.user_id,
    )
    before_explicit = fixture.context.repository.get_simulado_explicit_runtime_apply_by_id(
        transaction.source_explicit_apply_id,
        user_id=fixture.context.user_id,
    )
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_commit_shell(transaction.mutation_transaction_id, user_id=fixture.context.user_id)
    second = service.build_commit_shell(transaction.mutation_transaction_id, user_id=fixture.context.user_id)
    by_source = fixture.context.repository.get_simulado_controlled_mutation_commit_shell(
        transaction.mutation_transaction_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_controlled_mutation_commit_shell_by_id(
        result.commit_shell_id,
        user_id=fixture.context.user_id,
    )

    after_transaction = fixture.context.repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        transaction.mutation_transaction_id,
        user_id=fixture.context.user_id,
    )
    after_explicit = fixture.context.repository.get_simulado_explicit_runtime_apply_by_id(
        transaction.source_explicit_apply_id,
        user_id=fixture.context.user_id,
    )
    after_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    assert before_transaction is not None
    assert before_explicit is not None
    assert first is not None
    assert second is not None
    assert by_source is not None
    assert by_id is not None
    assert after_transaction is not None
    assert after_explicit is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert result.model_dump(mode="json") == by_source.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_transaction.model_dump(mode="json") == after_transaction.model_dump(mode="json")
    assert before_explicit.model_dump(mode="json") == after_explicit.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
