import json

from app.services.simulado_explicit_runtime_apply import (
    SimuladoExplicitRuntimeProgressApplyService,
)
from tests.fixtures.simulado_explicit_runtime_applies import (
    api_readonly_fixture,
    approve_payload,
    block_payload,
    build_explicit_runtime_apply,
    deny_payload,
    explicit_apply_source_fixture,
    idempotency_fixture,
    mark_not_reviewed_payload,
    missing_controlled_apply_shell_fixture,
    mixed_explicit_apply_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    request_revision_payload,
    unsafe_source_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_EXPLICIT_KEYS = {
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


def test_explicit_runtime_apply_handles_missing_controlled_apply_shell_safely(tmp_path):
    fixture = missing_controlled_apply_shell_fixture(tmp_path)

    assert build_explicit_runtime_apply(fixture) is None
    assert fixture.context.repository.list_user_simulado_explicit_runtime_applies(
        user_id=fixture.context.user_id
    ) == []


def test_explicit_runtime_apply_handles_default_and_approve_decisions_conservatively(tmp_path):
    no_payload = build_explicit_runtime_apply(explicit_apply_source_fixture(tmp_path / "no-payload"))
    approve_missing = build_explicit_runtime_apply(
        explicit_apply_source_fixture(tmp_path / "approve-missing"),
        decision_payload=approve_payload(),
    )
    approve_all = build_explicit_runtime_apply(
        explicit_apply_source_fixture(tmp_path / "approve-all"),
        decision_payload=approve_payload(
            runtime_policy_confirmed=True,
            explicit_apply_approval_confirmed=True,
            audit_confirmed=True,
            rollback_plan_confirmed=True,
            human_review_confirmed=True,
            public_answer_key_absence_confirmed=True,
        ),
    )

    assert no_payload is not None
    assert no_payload.explicit_apply_recorded is False
    assert no_payload.explicit_apply_approved is False
    assert no_payload.decision_status in {"explicit_apply_not_reviewed", "explicit_apply_blocked"}
    assert no_payload.runtime_application_applied is False

    assert approve_missing is not None
    assert approve_missing.explicit_apply_recorded is True
    assert approve_missing.explicit_apply_approved is False
    assert {
        "blocked_by_runtime_policy_not_confirmed",
        "blocked_by_explicit_apply_approval_not_confirmed",
        "blocked_by_audit_not_confirmed",
        "blocked_by_rollback_plan_not_confirmed",
        "blocked_by_human_review_not_confirmed",
    }.issubset({item.code for item in approve_missing.blockers})
    assert approve_missing.runtime_application_applied is False

    assert approve_all is not None
    assert approve_all.explicit_apply_recorded is True
    assert approve_all.explicit_apply_approved is True
    assert approve_all.decision_status == "explicit_apply_approved_for_future_runtime_mutation_review"
    assert approve_all.decision_summary.approved_for_future_runtime_mutation_review is True
    assert approve_all.apply_ready_for_runtime_mutation is False
    assert approve_all.runtime_application_applied is False


def test_explicit_runtime_apply_supports_deny_revision_block_and_not_reviewed_decisions(tmp_path):
    denied = build_explicit_runtime_apply(
        explicit_apply_source_fixture(tmp_path / "denied"),
        decision_payload=deny_payload(),
    )
    revision = build_explicit_runtime_apply(
        explicit_apply_source_fixture(tmp_path / "revision"),
        decision_payload=request_revision_payload(),
    )
    blocked = build_explicit_runtime_apply(
        explicit_apply_source_fixture(tmp_path / "blocked"),
        decision_payload=block_payload(),
    )
    not_reviewed = build_explicit_runtime_apply(
        explicit_apply_source_fixture(tmp_path / "not-reviewed"),
        decision_payload=mark_not_reviewed_payload(),
    )

    assert denied is not None
    assert denied.explicit_apply_recorded is True
    assert denied.explicit_apply_approved is False
    assert denied.decision_status == "explicit_apply_blocked"

    assert revision is not None
    assert revision.explicit_apply_recorded is True
    assert revision.explicit_apply_approved is False
    assert revision.decision_status == "explicit_apply_needs_revision"

    assert blocked is not None
    assert blocked.explicit_apply_recorded is True
    assert blocked.explicit_apply_approved is False
    assert blocked.decision_status == "explicit_apply_blocked"

    assert not_reviewed is not None
    assert not_reviewed.explicit_apply_recorded is True
    assert not_reviewed.explicit_apply_approved is False
    assert not_reviewed.decision_status == "explicit_apply_not_reviewed"


def test_explicit_runtime_apply_preserves_confirmations_approvals_and_audit_trail(tmp_path):
    approve_all = build_explicit_runtime_apply(
        explicit_apply_source_fixture(tmp_path / "approve-all"),
        decision_payload=approve_payload(
            runtime_policy_confirmed=True,
            explicit_apply_approval_confirmed=True,
            audit_confirmed=True,
            rollback_plan_confirmed=True,
            human_review_confirmed=True,
            public_answer_key_absence_confirmed=True,
        ),
    )
    mixed = build_explicit_runtime_apply(
        mixed_explicit_apply_fixture(tmp_path / "mixed"),
        decision_payload=approve_payload(),
    )

    assert approve_all is not None
    assert approve_all.confirmation_summary.runtime_policy_confirmed is True
    assert approve_all.confirmation_summary.explicit_apply_approval_confirmed is True
    assert approve_all.confirmation_summary.audit_confirmed is True
    assert approve_all.confirmation_summary.rollback_plan_confirmed is True
    assert approve_all.confirmation_summary.human_review_confirmed is True
    assert approve_all.confirmation_summary.public_answer_key_absence_confirmed is True
    assert approve_all.confirmation_summary.all_confirmations_satisfied is True

    assert approve_all.intent_approvals
    for approval in approve_all.intent_approvals:
        assert approval.intent_type in {
            "progress_update_candidate",
            "ranking_update_candidate",
            "retention_update_candidate",
            "scheduler_update_candidate",
            "study_cycle_update_candidate",
            "curriculum_graph_update_candidate",
            "unknown",
        }
        assert approval.proposed_surface in {
            "progress",
            "ranking",
            "retention",
            "scheduler",
            "study_cycle",
            "curriculum_graph",
            "adaptive_tuning",
            "unknown",
        }
        assert approval.applied is False
        assert approval.approved_for_apply_now is False
        assert approval.approved_for_future_runtime_mutation_review is True

    assert approve_all.surface_approvals
    for approval in approve_all.surface_approvals:
        assert approval.surface_type in {
            "progress",
            "ranking",
            "retention",
            "scheduler",
            "study_cycle",
            "curriculum_graph",
            "adaptive_tuning",
            "unknown",
        }
        assert approval.applied is False
        assert approval.approved_for_apply_now is False
        assert approval.approved_for_future_runtime_mutation_review is True

    audit_events = {item.event_type for item in approve_all.audit_trail}
    assert "explicit_apply_created" in audit_events
    assert "explicit_apply_decision_recorded" in audit_events
    assert "explicit_apply_approved_for_future_runtime_mutation_review" in audit_events
    assert "no_runtime_application" in audit_events
    assert "no_final_pedagogical_update_event" in audit_events

    assert mixed is not None
    assert "confirmations_missing" in {item.event_type for item in mixed.audit_trail}


def test_explicit_runtime_apply_preserves_no_public_answer_key_no_runtime_application_and_no_runtime_mutation(tmp_path):
    safe = build_explicit_runtime_apply(
        explicit_apply_source_fixture(tmp_path / "safe"),
        decision_payload=approve_payload(),
    )
    unsafe = build_explicit_runtime_apply(
        unsafe_source_fixture(tmp_path / "unsafe"),
        decision_payload=approve_payload(
            runtime_policy_confirmed=True,
            explicit_apply_approval_confirmed=True,
            audit_confirmed=True,
            rollback_plan_confirmed=True,
            human_review_confirmed=True,
            public_answer_key_absence_confirmed=True,
        ),
    )
    mutation = build_explicit_runtime_apply(
        no_runtime_mutation_fixture(tmp_path / "mutation"),
        decision_payload=approve_payload(),
    )

    assert safe is not None
    dumped_payload = safe.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_EXPLICIT_KEYS:
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


def test_explicit_runtime_apply_is_idempotent_and_does_not_mutate_sources(tmp_path):
    fixture = idempotency_fixture(tmp_path)
    source_shell = fixture.controlled_apply_shell
    assert source_shell is not None
    service = SimuladoExplicitRuntimeProgressApplyService(fixture.context.repository)
    payload = approve_payload(
        runtime_policy_confirmed=True,
        explicit_apply_approval_confirmed=True,
        audit_confirmed=True,
        rollback_plan_confirmed=True,
        human_review_confirmed=True,
        public_answer_key_absence_confirmed=True,
    )

    before_shell = fixture.context.repository.get_simulado_controlled_apply_shell_by_id(
        source_shell.apply_shell_id,
        user_id=fixture.context.user_id,
    )
    before_application = fixture.context.repository.get_simulado_runtime_progress_application_by_id(
        source_shell.source_application_id,
        user_id=fixture.context.user_id,
    )
    before_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    first = service.build_explicit_apply(
        source_apply_shell_id=source_shell.apply_shell_id,
        decision_payload=payload,
        user_id=fixture.context.user_id,
    )
    second = service.build_explicit_apply(
        source_apply_shell_id=source_shell.apply_shell_id,
        decision_payload=payload,
        user_id=fixture.context.user_id,
    )
    different = service.build_explicit_apply(
        source_apply_shell_id=source_shell.apply_shell_id,
        decision_payload=deny_payload(),
        user_id=fixture.context.user_id,
    )
    loaded = service.get_explicit_apply(
        source_shell.apply_shell_id,
        user_id=fixture.context.user_id,
    )
    assert first is not None
    assert second is not None
    assert different is not None
    by_id = service.get_explicit_apply_by_id(different.explicit_apply_id, user_id=fixture.context.user_id)
    listed = fixture.context.repository.list_user_simulado_explicit_runtime_applies(
        user_id=fixture.context.user_id
    )

    after_shell = fixture.context.repository.get_simulado_controlled_apply_shell_by_id(
        source_shell.apply_shell_id,
        user_id=fixture.context.user_id,
    )
    after_application = fixture.context.repository.get_simulado_runtime_progress_application_by_id(
        source_shell.source_application_id,
        user_id=fixture.context.user_id,
    )
    after_progress = fixture.context.repository.load_progress(user_id=fixture.context.user_id)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.explicit_apply_id != different.explicit_apply_id
    assert loaded is not None
    assert loaded.model_dump(mode="json") == different.model_dump(mode="json")
    assert by_id is not None
    assert by_id.model_dump(mode="json") == different.model_dump(mode="json")
    assert len(listed) == 1
    assert before_shell is not None and after_shell is not None
    assert before_application is not None and after_application is not None
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
    assert before_application.model_dump(mode="json") == after_application.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
