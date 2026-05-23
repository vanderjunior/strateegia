import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
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
    block_execution_fixture,
    block_payload,
    build_explicit_commit_execution_approval,
    confirmation_summary_shape_fixture,
    deny_execution_fixture,
    deny_payload,
    different_payload_behavior_fixture,
    mark_not_reviewed_fixture,
    mark_not_reviewed_payload,
    missing_execution_guardrail_fixture,
    mixed_approval_fixture,
    no_commit_execution_fixture,
    no_decision_payload_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    payload_idempotency_fixture,
    progress_execution_approvals_shape_fixture,
    request_revision_fixture,
    request_revision_payload,
    surface_execution_approvals_shape_fixture,
    unsafe_source_fixture,
    user_scope_fixture,
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


def _assert_no_runtime_mutation_flags(result) -> None:
    assert result.approved_for_execution_now is False
    assert result.commit_execution_allowed is False
    assert result.commit_execution_started is False
    assert result.commit_executed is False
    assert result.mutation_committed is False
    assert result.commit_transaction_valid_for_execution is False
    assert result.commit_execution_ready is False
    assert result.no_commit_execution is True
    assert result.no_commit_execution_event_created is True
    assert result.no_mutation_commit is True
    assert result.no_mutation_commit_event_created is True
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
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


def _assert_no_leakage(result) -> None:
    dumped_payload = result.model_dump(mode="json")
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


def _prepare_execution_guardrail(repository: JsonStudyRepository, tmp_path, user_id: str):
    fixture = user_scope_fixture(tmp_path, user_id=user_id, repository=repository)
    execution_guardrail = fixture.execution_guardrail
    assert execution_guardrail is not None
    return execution_guardrail


def test_explicit_commit_execution_approval_stabilization_fixtures_are_deterministic_and_json_safe(
    tmp_path,
):
    missing = missing_execution_guardrail_fixture(tmp_path / "missing")
    no_payload = no_decision_payload_fixture(tmp_path / "no-payload")
    payload_idempotent = payload_idempotency_fixture(tmp_path / "idempotent")
    mixed = mixed_approval_fixture(tmp_path / "mixed")

    assert missing.missing_execution_guardrail_id == "simulado-commit-execution-guardrail:missing"
    assert no_payload.execution_guardrail is not None
    assert payload_idempotent.execution_guardrail is not None
    assert mixed.execution_guardrail is not None
    assert json.dumps({"fixture": "explicit-commit-execution-approval"}, ensure_ascii=True)


def test_explicit_commit_execution_approval_stabilization_covers_decision_payloads_and_blockers(
    tmp_path,
):
    missing = build_explicit_commit_execution_approval(
        missing_execution_guardrail_fixture(tmp_path / "missing")
    )
    no_payload = build_explicit_commit_execution_approval(
        no_decision_payload_fixture(tmp_path / "no-payload")
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
        deny_execution_fixture(tmp_path / "deny"),
        decision_payload=deny_payload(),
    )
    revision = build_explicit_commit_execution_approval(
        request_revision_fixture(tmp_path / "revision"),
        decision_payload=request_revision_payload(),
    )
    blocked = build_explicit_commit_execution_approval(
        block_execution_fixture(tmp_path / "block"),
        decision_payload=block_payload(),
    )
    not_reviewed = build_explicit_commit_execution_approval(
        mark_not_reviewed_fixture(tmp_path / "not-reviewed"),
        decision_payload=mark_not_reviewed_payload(),
    )
    unsafe = build_explicit_commit_execution_approval(
        unsafe_source_fixture(tmp_path / "unsafe"),
        decision_payload=approve_all_payload(),
    )

    assert missing is None

    assert no_payload is not None
    assert no_payload.explicit_execution_approval_recorded is False
    assert no_payload.explicit_execution_approved is False
    assert no_payload.decision_status in {
        "explicit_execution_approval_not_reviewed",
        "explicit_execution_approval_blocked",
    }
    _assert_no_runtime_mutation_flags(no_payload)

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
    _assert_no_runtime_mutation_flags(approve_missing)

    assert approve_all is not None
    assert approve_all.explicit_execution_approval_recorded is True
    assert approve_all.explicit_execution_approved is True
    assert approve_all.approved_for_future_commit_execution_review is True
    assert approve_all.approved_for_execution_now is False
    assert approve_all.decision_status == "explicit_execution_approved_for_future_commit_execution_review"
    _assert_no_runtime_mutation_flags(approve_all)

    assert denied is not None
    assert denied.decision_summary.denied is True
    assert denied.explicit_execution_approved is False
    _assert_no_runtime_mutation_flags(denied)

    assert revision is not None
    assert revision.decision_summary.revision_requested is True
    assert revision.explicit_execution_approved is False
    _assert_no_runtime_mutation_flags(revision)

    assert blocked is not None
    assert blocked.decision_summary.blocked is True
    assert blocked.explicit_execution_approved is False
    _assert_no_runtime_mutation_flags(blocked)

    assert not_reviewed is not None
    assert not_reviewed.explicit_execution_approval_recorded is True
    assert not_reviewed.explicit_execution_approved is False
    assert not_reviewed.decision_status == "explicit_execution_approval_not_reviewed"
    _assert_no_runtime_mutation_flags(not_reviewed)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    _assert_no_runtime_mutation_flags(unsafe)


def test_explicit_commit_execution_approval_stabilization_covers_confirmation_approvals_audit_and_safety(
    tmp_path,
):
    confirmation = build_explicit_commit_execution_approval(
        confirmation_summary_shape_fixture(tmp_path / "confirmation"),
        decision_payload=approve_payload(),
    )
    progress = build_explicit_commit_execution_approval(
        progress_execution_approvals_shape_fixture(tmp_path / "progress"),
        decision_payload=approve_all_payload(),
    )
    surface = build_explicit_commit_execution_approval(
        surface_execution_approvals_shape_fixture(tmp_path / "surface"),
        decision_payload=approve_all_payload(),
    )
    audit = build_explicit_commit_execution_approval(
        audit_trail_fixture(tmp_path / "audit"),
        decision_payload=approve_payload(),
    )
    mixed = build_explicit_commit_execution_approval(
        mixed_approval_fixture(tmp_path / "mixed"),
        decision_payload=approve_payload(),
    )
    safe = build_explicit_commit_execution_approval(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe"),
        decision_payload=approve_all_payload(),
    )
    no_commit = build_explicit_commit_execution_approval(
        no_commit_execution_fixture(tmp_path / "no-commit"),
        decision_payload=approve_all_payload(),
    )
    no_runtime_application = build_explicit_commit_execution_approval(
        no_runtime_application_fixture(tmp_path / "no-runtime-application"),
        decision_payload=approve_all_payload(),
    )
    mutation = build_explicit_commit_execution_approval(
        no_runtime_mutation_fixture(tmp_path / "mutation"),
        decision_payload=approve_all_payload(),
    )

    assert confirmation is not None
    assert confirmation.confirmation_summary.final_execution_approval_confirmed is False
    assert confirmation.confirmation_summary.rollback_execution_confirmed is False
    assert confirmation.confirmation_summary.audit_confirmed is False
    assert confirmation.confirmation_summary.runtime_surface_confirmed is False
    assert confirmation.confirmation_summary.public_answer_key_absence_confirmed is False
    assert confirmation.confirmation_summary.human_review_confirmed is False
    assert confirmation.confirmation_summary.all_confirmations_satisfied is False

    assert progress is not None
    assert progress.confirmation_summary.all_confirmations_satisfied is True
    for item in progress.progress_execution_approvals:
        assert item.target_type in ALLOWED_TARGET_TYPES
        assert item.delta_kind in ALLOWED_DELTA_KINDS
        assert item.executed is False
        assert item.approved_for_execution_now is False
        assert item.approved_for_future_commit_execution_review is True
        assert item.approval_state == "progress_execution_approved_for_future_commit_execution_review"

    assert surface is not None
    for item in surface.surface_execution_approvals:
        assert item.surface_type in ALLOWED_SURFACE_TYPES
        assert item.update_kind in ALLOWED_UPDATE_KINDS
        assert item.executed is False
        assert item.approved_for_execution_now is False
        assert item.approved_for_future_commit_execution_review is True
        assert item.approval_state == "surface_execution_approved_for_future_commit_execution_review"

    assert audit is not None
    events = {item.event_type for item in audit.audit_trail}
    assert "explicit_execution_approval_created" in events
    assert "explicit_execution_decision_recorded" in events
    assert "confirmations_missing" in events
    assert "no_commit_execution" in events
    assert "no_mutation_commit" in events
    assert "no_runtime_application" in events
    assert "no_progress_mutation" in events
    assert "no_final_pedagogical_update_event" in events

    assert mixed is not None
    assert mixed.blockers
    assert mixed.warnings
    _assert_no_runtime_mutation_flags(mixed)

    assert safe is not None
    _assert_no_leakage(safe)

    assert no_commit is not None
    assert no_commit.commit_execution_allowed is False
    assert no_commit.commit_execution_started is False
    assert no_commit.commit_executed is False
    assert no_commit.no_commit_execution is True
    assert no_commit.no_commit_execution_event_created is True
    _assert_no_runtime_mutation_flags(no_commit)

    assert no_runtime_application is not None
    assert no_runtime_application.runtime_application_enabled is False
    assert no_runtime_application.runtime_application_applied is False
    assert no_runtime_application.no_runtime_application is True
    _assert_no_runtime_mutation_flags(no_runtime_application)

    assert mutation is not None
    assert mutation.mutation_committed is False
    assert mutation.no_mutation_commit is True
    assert mutation.no_mutation_commit_event_created is True
    _assert_no_runtime_mutation_flags(mutation)
    _assert_no_leakage(mutation)


def test_explicit_commit_execution_approval_stabilization_is_idempotent_owner_only_and_read_only(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = payload_idempotency_fixture(tmp_path / "idempotent", repository=repository)
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
    changed = build_explicit_commit_execution_approval(
        different_payload_behavior_fixture(tmp_path / "changed", repository=repository),
        decision_payload=deny_payload(),
    )
    service = SimuladoExplicitRuntimeCommitExecutionApprovalService(repository)

    assert first is not None
    assert second is not None
    assert changed is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.execution_approval_id != changed.execution_approval_id
    latest = service.get_execution_approval(
        execution_guardrail.execution_guardrail_id,
        user_id=fixture.context.user_id,
    )
    assert latest is not None
    assert latest.execution_approval_id == changed.execution_approval_id
    assert latest.decision_summary.decision_type == "deny_execution"
    assert service.get_execution_approval_by_id(
        changed.execution_approval_id,
        user_id=fixture.context.user_id,
    ) is not None
    assert service.get_execution_approval_by_id(
        first.execution_approval_id,
        user_id=fixture.context.user_id,
    ) is None
    assert len(
        repository.list_user_simulado_explicit_commit_execution_approvals(
            user_id=fixture.context.user_id
        )
    ) == 1

    before_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        execution_guardrail.execution_guardrail_id,
        user_id=fixture.context.user_id,
    )
    reread = service.get_execution_approval(
        execution_guardrail.execution_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        execution_guardrail.execution_guardrail_id,
        user_id=fixture.context.user_id,
    )
    assert reread is not None
    assert before_guardrail is not None
    assert after_guardrail is not None
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")

    owner = TestClient(create_app(repository=repository))
    other = TestClient(create_app(repository=repository))
    anonymous = TestClient(create_app(repository=repository))
    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    owner_guardrail = _prepare_execution_guardrail(repository, tmp_path / "owner-scope", owner_user_id)

    missing = owner.get(
        f"/api/simulado-commit-execution-guardrail/{owner_guardrail.execution_guardrail_id}/explicit-execution-approval"
    )
    build = owner.post(
        f"/api/simulado-commit-execution-guardrail/{owner_guardrail.execution_guardrail_id}/explicit-execution-approval/build",
        json=approve_all_payload(),
    )
    loaded_owner = owner.get(
        f"/api/simulado-commit-execution-guardrail/{owner_guardrail.execution_guardrail_id}/explicit-execution-approval"
    )
    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded_owner.status_code == 200

    execution_approval_id = build.json()["execution_approval_id"]
    assert other.post(
        f"/api/simulado-commit-execution-guardrail/{owner_guardrail.execution_guardrail_id}/explicit-execution-approval/build",
        json=approve_all_payload(),
    ).status_code == 404
    assert other.get(
        f"/api/simulado-commit-execution-guardrail/{owner_guardrail.execution_guardrail_id}/explicit-execution-approval"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-explicit-execution-approval/{execution_approval_id}"
    ).status_code == 404
    assert anonymous.post(
        f"/api/simulado-commit-execution-guardrail/{owner_guardrail.execution_guardrail_id}/explicit-execution-approval/build",
        json=approve_all_payload(),
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-commit-execution-guardrail/{owner_guardrail.execution_guardrail_id}/explicit-execution-approval"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-explicit-execution-approval/{execution_approval_id}"
    ).status_code == 401

    before_owner_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        owner_guardrail.execution_guardrail_id,
        user_id=owner_user_id,
    )
    reread_owner = owner.get(
        f"/api/simulado-commit-execution-guardrail/{owner_guardrail.execution_guardrail_id}/explicit-execution-approval"
    )
    after_owner_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        owner_guardrail.execution_guardrail_id,
        user_id=owner_user_id,
    )
    assert reread_owner.status_code == 200
    assert before_owner_guardrail is not None
    assert after_owner_guardrail is not None
    assert before_owner_guardrail.model_dump(mode="json") == after_owner_guardrail.model_dump(mode="json")
