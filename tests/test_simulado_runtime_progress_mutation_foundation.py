import json

from app.services.simulado_runtime_progress_mutation import (
    SimuladoRuntimeProgressMutationService,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_progress_mutations import (
    api_readonly_fixture,
    approved_for_future_review_fixture,
    build_runtime_progress_mutation_transaction,
    confirmations_incomplete_fixture,
    explicit_apply_not_approved_fixture,
    intents_not_approved_fixture,
    missing_explicit_apply_fixture,
    mixed_mutation_fixture,
    no_runtime_mutation_fixture,
    runtime_mutation_disabled_fixture,
    surfaces_not_approved_fixture,
    unsafe_source_fixture,
)


FORBIDDEN_MUTATION_KEYS = {
    "correct_answer",
    "correct_option",
    "answer_key",
    "answer_key_value",
    "final_answer_key_content",
    "gabarito",
    "gabarito_final",
    "correctness",
    "is_correct",
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


def test_runtime_progress_mutation_handles_missing_explicit_apply_safely(tmp_path):
    fixture = missing_explicit_apply_fixture(tmp_path)

    assert build_runtime_progress_mutation_transaction(fixture) is None
    assert fixture.context.repository.list_user_simulado_runtime_progress_mutation_transactions(
        user_id=fixture.context.user_id
    ) == []


def test_runtime_progress_mutation_builds_blocked_proposal_from_explicit_apply_states(tmp_path):
    not_approved = build_runtime_progress_mutation_transaction(
        explicit_apply_not_approved_fixture(tmp_path / "not-approved")
    )
    approved_future = build_runtime_progress_mutation_transaction(
        approved_for_future_review_fixture(tmp_path / "approved-future")
    )
    confirmations_incomplete = build_runtime_progress_mutation_transaction(
        confirmations_incomplete_fixture(tmp_path / "confirmations-incomplete")
    )

    assert not_approved is not None
    assert not_approved.readiness_state == "blocked_by_explicit_apply_not_approved"
    assert not_approved.mutation_valid_for_commit is False
    assert not_approved.mutation_committed is False

    assert approved_future is not None
    assert approved_future.mutation_transaction_created is True
    assert approved_future.mutation_mode in {"proposal_only", "dry_run_transaction"}
    assert approved_future.readiness_state == "blocked_by_apply_now_not_allowed"
    assert approved_future.mutation_valid_for_commit is False
    assert approved_future.mutation_commit_ready is False
    assert approved_future.mutation_committed is False

    assert confirmations_incomplete is not None
    assert "blocked_by_confirmations_incomplete" in {item.code for item in confirmations_incomplete.blockers}
    assert confirmations_incomplete.mutation_committed is False


def test_runtime_progress_mutation_handles_rollback_approval_and_surface_blockers_conservatively(tmp_path):
    intents_blocked = build_runtime_progress_mutation_transaction(
        intents_not_approved_fixture(tmp_path / "intents")
    )
    surfaces_blocked = build_runtime_progress_mutation_transaction(
        surfaces_not_approved_fixture(tmp_path / "surfaces")
    )
    mutation_disabled = build_runtime_progress_mutation_transaction(
        runtime_mutation_disabled_fixture(tmp_path / "disabled")
    )

    assert intents_blocked is not None
    assert "blocked_by_missing_rollback_plan" in {item.code for item in intents_blocked.blockers}
    assert "blocked_by_intents_not_approved" in {item.code for item in intents_blocked.blockers}
    assert intents_blocked.rollback_plan.rollback_required is True
    assert intents_blocked.rollback_plan.rollback_available is False
    assert intents_blocked.rollback_plan.rollback_verified is False

    assert surfaces_blocked is not None
    assert "blocked_by_surfaces_not_approved" in {item.code for item in surfaces_blocked.blockers}

    assert mutation_disabled is not None
    assert mutation_disabled.readiness_state == "blocked_by_runtime_mutation_disabled"
    assert mutation_disabled.runtime_application_enabled is False
    assert mutation_disabled.progress_mutation_enabled is False


def test_runtime_progress_mutation_produces_bounded_deltas_surface_updates_and_audit_trail(tmp_path):
    result = build_runtime_progress_mutation_transaction(
        approved_for_future_review_fixture(tmp_path / "approved")
    )
    mixed = build_runtime_progress_mutation_transaction(
        mixed_mutation_fixture(tmp_path / "mixed")
    )

    assert result is not None
    assert result.validation_summary.source_explicit_apply_present is True
    assert result.validation_summary.explicit_apply_recorded is True
    assert result.validation_summary.explicit_apply_approved is True
    assert result.validation_summary.approved_for_future_runtime_mutation_review is True
    assert result.validation_summary.approved_for_apply_now is False
    assert result.validation_summary.apply_ready_for_runtime_mutation is False
    assert result.validation_summary.confirmations_satisfied is True
    assert result.validation_summary.rollback_plan_available is False
    assert result.validation_summary.transaction_valid_for_commit is False
    assert result.validation_summary.transaction_commit_ready is False

    assert result.proposed_progress_deltas
    for delta in result.proposed_progress_deltas:
        assert delta.target_type in ALLOWED_TARGET_TYPES
        assert delta.delta_kind in ALLOWED_DELTA_KINDS
        assert delta.applied is False
        assert delta.commit_allowed is False

    assert result.proposed_surface_updates
    for update in result.proposed_surface_updates:
        assert update.surface_type in ALLOWED_SURFACE_TYPES
        assert update.update_kind in ALLOWED_UPDATE_KINDS
        assert update.applied is False
        assert update.commit_allowed is False

    audit_events = {item.event_type for item in result.audit_trail}
    assert "mutation_transaction_created" in audit_events
    assert "mutation_transaction_blocked" in audit_events
    assert "mutation_proposal_created" in audit_events
    assert "rollback_plan_missing" in audit_events
    assert "no_runtime_application" in audit_events
    assert "no_progress_mutation" in audit_events
    assert "no_final_pedagogical_update_event" in audit_events

    assert mixed is not None
    assert mixed.blockers


def test_runtime_progress_mutation_preserves_no_public_answer_key_no_runtime_application_and_no_runtime_mutation(tmp_path):
    safe = build_runtime_progress_mutation_transaction(
        approved_for_future_review_fixture(tmp_path / "safe")
    )
    unsafe = build_runtime_progress_mutation_transaction(
        unsafe_source_fixture(tmp_path / "unsafe")
    )
    mutation = build_runtime_progress_mutation_transaction(
        no_runtime_mutation_fixture(tmp_path / "mutation")
    )

    assert safe is not None
    dumped_payload = safe.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_MUTATION_KEYS:
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
    assert mutation.no_runtime_application is True
    assert mutation.no_progress_mutation is True
    assert mutation.no_ranking_update is True
    assert mutation.no_retention_update is True
    assert mutation.no_scheduler_update is True
    assert mutation.no_study_cycle_update is True
    assert mutation.no_curriculum_graph_update is True
    assert mutation.no_adaptive_tuning_update is True
    assert mutation.no_final_pedagogical_update_event is True


def test_runtime_progress_mutation_is_deterministic_and_read_only_for_same_source(tmp_path):
    fixture = api_readonly_fixture(tmp_path)
    source_explicit_apply = fixture.explicit_apply
    assert source_explicit_apply is not None

    first = build_runtime_progress_mutation_transaction(fixture)
    second = build_runtime_progress_mutation_transaction(fixture)
    service = SimuladoRuntimeProgressMutationService(fixture.context.repository)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert service.get_mutation_transaction(
        source_explicit_apply.explicit_apply_id,
        user_id=fixture.context.user_id,
    ).model_dump(mode="json") == first.model_dump(mode="json")
    assert service.get_mutation_transaction_by_id(
        first.mutation_transaction_id,
        user_id=fixture.context.user_id,
    ).model_dump(mode="json") == first.model_dump(mode="json")
