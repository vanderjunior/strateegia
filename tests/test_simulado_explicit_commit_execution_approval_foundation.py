import json

from app.services.simulado_explicit_commit_execution_approval import (
    SimuladoExplicitRuntimeCommitExecutionApprovalService,
)
from tests.fixtures.simulado_explicit_commit_execution_approvals import (
    api_readonly_fixture,
    approve_all_payload,
    approve_payload,
    approve_with_all_confirmations_fixture,
    approve_without_confirmations_fixture,
    audit_trail_fixture,
    block_execution_decision_fixture,
    block_payload,
    build_explicit_commit_execution_approval,
    confirmation_summary_shape_fixture,
    deny_execution_decision_fixture,
    deny_payload,
    explicit_execution_approval_source_fixture,
    mark_not_reviewed_decision_fixture,
    mark_not_reviewed_payload,
    missing_execution_guardrail_fixture,
    mixed_decision_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture,
    payload_idempotency_fixture,
    progress_execution_approvals_shape_fixture,
    request_revision_decision_fixture,
    request_revision_payload,
    surface_execution_approvals_shape_fixture,
    unsafe_source_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_EXPLICIT_EXECUTION_APPROVAL_KEYS = {
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


def test_explicit_commit_execution_approval_handles_missing_execution_guardrail_safely(tmp_path):
    fixture = missing_execution_guardrail_fixture(tmp_path)

    assert build_explicit_commit_execution_approval(fixture) is None
    assert fixture.context.repository.list_user_simulado_explicit_commit_execution_approvals(
        user_id=fixture.context.user_id
    ) == []


def test_explicit_commit_execution_approval_covers_decision_payload_scenarios_conservatively(tmp_path):
    no_payload = build_explicit_commit_execution_approval(
        no_public_key_gabarito_safety_fixture(tmp_path / "no-payload")
    )
    approve_missing = build_explicit_commit_execution_approval(
        approve_without_confirmations_fixture(tmp_path / "approve-missing"),
        decision_payload=approve_payload(),
    )
    approve_all = build_explicit_commit_execution_approval(
        approve_with_all_confirmations_fixture(tmp_path / "approve-all"),
        decision_payload=approve_all_payload(),
    )
    denied = build_explicit_commit_execution_approval(
        deny_execution_decision_fixture(tmp_path / "deny"),
        decision_payload=deny_payload(),
    )
    revision = build_explicit_commit_execution_approval(
        request_revision_decision_fixture(tmp_path / "revision"),
        decision_payload=request_revision_payload(),
    )
    blocked = build_explicit_commit_execution_approval(
        block_execution_decision_fixture(tmp_path / "block"),
        decision_payload=block_payload(),
    )
    not_reviewed = build_explicit_commit_execution_approval(
        mark_not_reviewed_decision_fixture(tmp_path / "not-reviewed"),
        decision_payload=mark_not_reviewed_payload(),
    )

    assert no_payload is not None
    assert no_payload.explicit_execution_approval_recorded is False
    assert no_payload.explicit_execution_approved is False
    assert no_payload.decision_status in {
        "explicit_execution_approval_not_reviewed",
        "explicit_execution_approval_blocked",
    }

    assert approve_missing is not None
    assert approve_missing.explicit_execution_approval_recorded is True
    assert approve_missing.explicit_execution_approved is False
    assert {
        "blocked_by_final_execution_approval_not_confirmed",
        "blocked_by_rollback_execution_not_confirmed",
        "blocked_by_audit_not_confirmed",
        "blocked_by_runtime_surface_not_confirmed",
        "blocked_by_human_review_not_confirmed",
    }.issubset({item.code for item in approve_missing.blockers})

    assert approve_all is not None
    assert approve_all.explicit_execution_approval_recorded is True
    assert approve_all.explicit_execution_approved is True
    assert approve_all.approved_for_future_commit_execution_review is True
    assert approve_all.approved_for_execution_now is False
    assert (
        approve_all.decision_status
        == "explicit_execution_approved_for_future_commit_execution_review"
    )
    assert approve_all.commit_execution_allowed is False
    assert approve_all.commit_execution_started is False
    assert approve_all.commit_executed is False
    assert approve_all.mutation_committed is False

    assert denied is not None
    assert denied.decision_summary.denied is True
    assert denied.explicit_execution_approved is False

    assert revision is not None
    assert revision.decision_summary.revision_requested is True
    assert revision.explicit_execution_approved is False

    assert blocked is not None
    assert blocked.decision_summary.blocked is True
    assert blocked.explicit_execution_approved is False

    assert not_reviewed is not None
    assert not_reviewed.explicit_execution_approval_recorded is True
    assert not_reviewed.explicit_execution_approved is False
    assert not_reviewed.decision_status == "explicit_execution_approval_not_reviewed"


def test_explicit_commit_execution_approval_builds_confirmation_progress_surface_and_audit_shapes(
    tmp_path,
):
    default_result = build_explicit_commit_execution_approval(
        confirmation_summary_shape_fixture(tmp_path / "default"),
        decision_payload=approve_payload(),
    )
    approved_result = build_explicit_commit_execution_approval(
        progress_execution_approvals_shape_fixture(tmp_path / "approved"),
        decision_payload=approve_all_payload(),
    )
    surface_result = build_explicit_commit_execution_approval(
        surface_execution_approvals_shape_fixture(tmp_path / "surface"),
        decision_payload=approve_all_payload(),
    )
    audit_result = build_explicit_commit_execution_approval(
        audit_trail_fixture(tmp_path / "audit"),
        decision_payload=approve_payload(),
    )

    assert default_result is not None
    assert default_result.confirmation_summary.final_execution_approval_confirmed is False
    assert default_result.confirmation_summary.rollback_execution_confirmed is False
    assert default_result.confirmation_summary.audit_confirmed is False
    assert default_result.confirmation_summary.runtime_surface_confirmed is False
    assert default_result.confirmation_summary.public_answer_key_absence_confirmed is False
    assert default_result.confirmation_summary.human_review_confirmed is False
    assert default_result.confirmation_summary.all_confirmations_satisfied is False
    assert "confirmations_missing" in {item.event_type for item in default_result.audit_trail}

    assert approved_result is not None
    assert approved_result.confirmation_summary.all_confirmations_satisfied is True
    for approval in approved_result.progress_execution_approvals:
        assert approval.target_type in ALLOWED_TARGET_TYPES
        assert approval.delta_kind in ALLOWED_DELTA_KINDS
        assert approval.executed is False
        assert approval.approved_for_execution_now is False
        assert approval.approved_for_future_commit_execution_review is True
        assert (
            approval.approval_state
            == "progress_execution_approved_for_future_commit_execution_review"
        )
    audit_events = {item.event_type for item in approved_result.audit_trail}
    assert "explicit_execution_approval_created" in audit_events
    assert "explicit_execution_decision_recorded" in audit_events
    assert "explicit_execution_approved_for_future_commit_execution_review" in audit_events
    assert "no_commit_execution" in audit_events
    assert "no_mutation_commit" in audit_events
    assert "no_runtime_application" in audit_events
    assert "no_final_pedagogical_update_event" in audit_events

    assert surface_result is not None
    for approval in surface_result.surface_execution_approvals:
        assert approval.surface_type in ALLOWED_SURFACE_TYPES
        assert approval.update_kind in ALLOWED_UPDATE_KINDS
        assert approval.executed is False
        assert approval.approved_for_execution_now is False
        assert approval.approved_for_future_commit_execution_review is True
        assert (
            approval.approval_state
            == "surface_execution_approved_for_future_commit_execution_review"
        )

    assert audit_result is not None
    audit_events = {item.event_type for item in audit_result.audit_trail}
    assert "explicit_execution_approval_created" in audit_events
    assert "explicit_execution_decision_recorded" in audit_events
    assert "confirmations_missing" in audit_events
    assert "no_commit_execution" in audit_events
    assert "no_progress_mutation" in audit_events


def test_explicit_commit_execution_approval_preserves_no_leakage_no_execution_and_no_runtime_mutation(
    tmp_path,
):
    mixed = build_explicit_commit_execution_approval(
        mixed_decision_fixture(tmp_path / "mixed"),
        decision_payload=approve_payload(),
    )
    safe = build_explicit_commit_execution_approval(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe"),
        decision_payload=approve_all_payload(),
    )
    unsafe = build_explicit_commit_execution_approval(
        unsafe_source_fixture(tmp_path / "unsafe"),
        decision_payload=approve_all_payload(),
    )
    mutation = build_explicit_commit_execution_approval(
        no_runtime_mutation_fixture(tmp_path / "mutation"),
        decision_payload=approve_all_payload(),
    )

    assert mixed is not None
    assert mixed.blockers

    assert safe is not None
    dumped_payload = safe.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_EXPLICIT_EXECUTION_APPROVAL_KEYS:
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
    assert mutation.approved_for_execution_now is False
    assert mutation.commit_execution_allowed is False
    assert mutation.commit_execution_started is False
    assert mutation.commit_executed is False
    assert mutation.mutation_committed is False
    assert mutation.commit_transaction_valid_for_execution is False
    assert mutation.commit_execution_ready is False
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


def test_explicit_commit_execution_approval_is_idempotent_for_same_payload_and_replaces_for_new_payload(
    tmp_path,
):
    fixture = payload_idempotency_fixture(tmp_path)
    execution_guardrail = fixture.execution_guardrail
    assert execution_guardrail is not None

    first = build_explicit_commit_execution_approval(
        fixture,
        decision_payload=approve_all_payload(),
    )
    second = build_explicit_commit_execution_approval(
        fixture,
        decision_payload=approve_all_payload(),
    )
    denied = build_explicit_commit_execution_approval(
        fixture,
        decision_payload=deny_payload(),
    )
    service = SimuladoExplicitRuntimeCommitExecutionApprovalService(fixture.context.repository)

    assert first is not None
    assert second is not None
    assert denied is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.execution_approval_id != denied.execution_approval_id
    latest = service.get_execution_approval(
        execution_guardrail.execution_guardrail_id,
        user_id=fixture.context.user_id,
    )
    assert latest is not None
    assert latest.execution_approval_id == denied.execution_approval_id
    assert latest.decision_summary.decision_type == "deny_execution"
    assert service.get_execution_approval_by_id(
        denied.execution_approval_id,
        user_id=fixture.context.user_id,
    ) is not None
    assert service.get_execution_approval_by_id(
        first.execution_approval_id,
        user_id=fixture.context.user_id,
    ) is None
