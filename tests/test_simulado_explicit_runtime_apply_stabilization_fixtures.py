import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_explicit_runtime_apply import (
    SimuladoExplicitRuntimeProgressApplyService,
)
from tests.fixtures.simulado_explicit_runtime_applies import (
    api_readonly_fixture,
    approve_payload,
    approve_with_all_confirmations_fixture,
    approve_without_confirmations_fixture,
    block_decision_fixture,
    block_payload,
    build_explicit_runtime_apply,
    confirmation_summary_shape_fixture,
    deny_decision_fixture,
    deny_payload,
    different_payload_behavior_fixture,
    intent_approvals_shape_fixture,
    mark_not_reviewed_decision_fixture,
    mark_not_reviewed_payload,
    missing_controlled_apply_shell_fixture,
    mixed_decision_fixture,
    no_decision_payload_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    payload_idempotency_fixture,
    request_revision_decision_fixture,
    request_revision_payload,
    surface_approvals_shape_fixture,
    unsafe_source_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_EXPLICIT_KEYS = {
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
    "runtime_application_event",
    "final_pedagogical_update_event",
}

ALLOWED_INTENT_TYPES = {
    "progress_update_candidate",
    "ranking_update_candidate",
    "retention_update_candidate",
    "scheduler_update_candidate",
    "study_cycle_update_candidate",
    "curriculum_graph_update_candidate",
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


def _approve_all_payload() -> dict[str, object]:
    return approve_payload(
        runtime_policy_confirmed=True,
        explicit_apply_approval_confirmed=True,
        audit_confirmed=True,
        rollback_plan_confirmed=True,
        human_review_confirmed=True,
        public_answer_key_absence_confirmed=True,
    )


def _assert_no_runtime_mutation_flags(result) -> None:
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


def _assert_no_leakage(result) -> None:
    dumped_payload = result.model_dump(mode="json")
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
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


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


def _prepare_client_shell(repository: JsonStudyRepository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    shell = fixture.controlled_apply_shell
    assert shell is not None
    return shell


def test_explicit_runtime_apply_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    missing = missing_controlled_apply_shell_fixture(tmp_path / "missing")
    no_payload = no_decision_payload_fixture(tmp_path / "no-payload")
    approve_all = approve_with_all_confirmations_fixture(tmp_path / "approve-all")
    mixed = mixed_decision_fixture(tmp_path / "mixed")

    assert missing.missing_apply_shell_id == "simulado-controlled-apply-shell:missing"
    assert no_payload.controlled_apply_shell is not None
    assert approve_all.controlled_apply_shell is not None
    assert mixed.controlled_apply_shell is not None
    assert json.dumps(approve_payload(), ensure_ascii=True)
    assert json.dumps(_approve_all_payload(), ensure_ascii=True)


def test_explicit_runtime_apply_stabilization_covers_missing_and_decision_payload_scenarios(tmp_path):
    missing = build_explicit_runtime_apply(missing_controlled_apply_shell_fixture(tmp_path / "missing"))
    no_payload = build_explicit_runtime_apply(no_decision_payload_fixture(tmp_path / "no-payload"))
    approve_missing = build_explicit_runtime_apply(
        approve_without_confirmations_fixture(tmp_path / "approve-missing"),
        decision_payload=approve_payload(),
    )
    approve_all = build_explicit_runtime_apply(
        approve_with_all_confirmations_fixture(tmp_path / "approve-all"),
        decision_payload=_approve_all_payload(),
    )
    denied = build_explicit_runtime_apply(
        deny_decision_fixture(tmp_path / "deny"),
        decision_payload=deny_payload(),
    )
    revision = build_explicit_runtime_apply(
        request_revision_decision_fixture(tmp_path / "revision"),
        decision_payload=request_revision_payload(),
    )
    blocked = build_explicit_runtime_apply(
        block_decision_fixture(tmp_path / "block"),
        decision_payload=block_payload(),
    )
    not_reviewed = build_explicit_runtime_apply(
        mark_not_reviewed_decision_fixture(tmp_path / "not-reviewed"),
        decision_payload=mark_not_reviewed_payload(),
    )

    assert missing is None

    assert no_payload is not None
    assert no_payload.explicit_apply_recorded is False
    assert no_payload.explicit_apply_approved is False
    assert no_payload.decision_status in {"explicit_apply_not_reviewed", "explicit_apply_blocked"}
    _assert_no_runtime_mutation_flags(no_payload)

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
    _assert_no_runtime_mutation_flags(approve_missing)

    assert approve_all is not None
    assert approve_all.explicit_apply_recorded is True
    assert approve_all.explicit_apply_approved is True
    assert approve_all.decision_status == "explicit_apply_approved_for_future_runtime_mutation_review"
    assert approve_all.decision_summary.approved_for_future_runtime_mutation_review is True
    assert approve_all.apply_ready_for_runtime_mutation is False
    _assert_no_runtime_mutation_flags(approve_all)

    assert denied is not None
    assert denied.decision_summary.denied is True
    assert denied.explicit_apply_approved is False
    _assert_no_runtime_mutation_flags(denied)

    assert revision is not None
    assert revision.decision_summary.revision_requested is True
    assert revision.explicit_apply_approved is False
    _assert_no_runtime_mutation_flags(revision)

    assert blocked is not None
    assert blocked.decision_summary.blocked is True
    assert blocked.explicit_apply_approved is False
    _assert_no_runtime_mutation_flags(blocked)

    assert not_reviewed is not None
    assert not_reviewed.explicit_apply_recorded is True
    assert not_reviewed.explicit_apply_approved is False
    assert not_reviewed.decision_status == "explicit_apply_not_reviewed"
    _assert_no_runtime_mutation_flags(not_reviewed)


def test_explicit_runtime_apply_stabilization_confirms_confirmation_intent_surface_and_audit_shapes(tmp_path):
    default_result = build_explicit_runtime_apply(
        confirmation_summary_shape_fixture(tmp_path / "default"),
        decision_payload=approve_payload(),
    )
    approved_result = build_explicit_runtime_apply(
        intent_approvals_shape_fixture(tmp_path / "approved"),
        decision_payload=_approve_all_payload(),
    )
    surface_result = build_explicit_runtime_apply(
        surface_approvals_shape_fixture(tmp_path / "surface"),
        decision_payload=_approve_all_payload(),
    )

    assert default_result is not None
    assert default_result.confirmation_summary.runtime_policy_confirmed is False
    assert default_result.confirmation_summary.explicit_apply_approval_confirmed is False
    assert default_result.confirmation_summary.audit_confirmed is False
    assert default_result.confirmation_summary.rollback_plan_confirmed is False
    assert default_result.confirmation_summary.human_review_confirmed is False
    assert default_result.confirmation_summary.public_answer_key_absence_confirmed is False
    assert default_result.confirmation_summary.all_confirmations_satisfied is False
    assert "confirmations_missing" in {item.event_type for item in default_result.audit_trail}

    assert approved_result is not None
    assert approved_result.confirmation_summary.all_confirmations_satisfied is True
    for approval in approved_result.intent_approvals:
        assert approval.intent_type in ALLOWED_INTENT_TYPES
        assert approval.proposed_surface in ALLOWED_SURFACE_TYPES
        assert approval.applied is False
        assert approval.approved_for_apply_now is False
        assert approval.approved_for_future_runtime_mutation_review is True
        assert approval.approval_state == "intent_approved_for_future_runtime_mutation_review"
    audit_events = {item.event_type for item in approved_result.audit_trail}
    assert "explicit_apply_created" in audit_events
    assert "explicit_apply_decision_recorded" in audit_events
    assert "explicit_apply_approved_for_future_runtime_mutation_review" in audit_events
    assert "no_runtime_application" in audit_events
    assert "no_final_pedagogical_update_event" in audit_events

    assert surface_result is not None
    for approval in surface_result.surface_approvals:
        assert approval.surface_type in ALLOWED_SURFACE_TYPES
        assert approval.applied is False
        assert approval.approved_for_apply_now is False
        assert approval.approved_for_future_runtime_mutation_review is True
        assert approval.approval_state == "surface_approved_for_future_runtime_mutation_review"


def test_explicit_runtime_apply_stabilization_preserves_blocked_source_and_no_leakage(tmp_path):
    mixed = build_explicit_runtime_apply(
        mixed_decision_fixture(tmp_path / "mixed"),
        decision_payload=approve_payload(),
    )
    safe = build_explicit_runtime_apply(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe"),
        decision_payload=approve_payload(),
    )
    unsafe = build_explicit_runtime_apply(
        unsafe_source_fixture(tmp_path / "unsafe"),
        decision_payload=_approve_all_payload(),
    )

    assert mixed is not None
    assert mixed.blockers
    assert mixed.readiness_state in {
        "blocked_by_preconditions_not_satisfied",
        "blocked_by_intents_not_ready",
        "blocked_by_surfaces_not_ready",
        "blocked_by_apply_shell_not_ready",
        "blocked_by_public_answer_key_exposure_forbidden",
    }
    _assert_no_runtime_mutation_flags(mixed)

    assert safe is not None
    _assert_no_leakage(safe)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    _assert_no_leakage(unsafe)


def test_explicit_runtime_apply_stabilization_preserves_idempotency_and_different_payload_determinism(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = SimuladoExplicitRuntimeProgressApplyService(repository)
    stable_fixture = payload_idempotency_fixture(tmp_path / "stable", repository=repository)
    source_shell = stable_fixture.controlled_apply_shell
    assert source_shell is not None

    first = build_explicit_runtime_apply(stable_fixture, decision_payload=approve_payload())
    second = build_explicit_runtime_apply(stable_fixture, decision_payload=approve_payload())
    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")

    by_source = service.get_explicit_apply(source_shell.apply_shell_id, user_id=stable_fixture.context.user_id)
    by_id = service.get_explicit_apply_by_id(first.explicit_apply_id, user_id=stable_fixture.context.user_id)
    listed = repository.list_user_simulado_explicit_runtime_applies(user_id=stable_fixture.context.user_id)
    assert by_source is not None
    assert by_id is not None
    assert by_source.model_dump(mode="json") == first.model_dump(mode="json")
    assert by_id.model_dump(mode="json") == first.model_dump(mode="json")
    assert len(listed) == 1

    different_fixture = different_payload_behavior_fixture(tmp_path / "different", repository=repository)
    different_shell = different_fixture.controlled_apply_shell
    assert different_shell is not None
    approved = build_explicit_runtime_apply(different_fixture, decision_payload=approve_payload())
    denied = build_explicit_runtime_apply(different_fixture, decision_payload=deny_payload())
    latest = service.get_explicit_apply(different_shell.apply_shell_id, user_id=different_fixture.context.user_id)
    approved_by_id = service.get_explicit_apply_by_id(
        approved.explicit_apply_id,
        user_id=different_fixture.context.user_id,
    )
    denied_by_id = service.get_explicit_apply_by_id(
        denied.explicit_apply_id,
        user_id=different_fixture.context.user_id,
    )

    assert approved is not None
    assert denied is not None
    assert approved.explicit_apply_id != denied.explicit_apply_id
    assert approved.decision_summary.decision_type == "approve_for_future_runtime_mutation_review"
    assert denied.decision_summary.decision_type == "deny_apply"
    assert latest is not None
    assert latest.explicit_apply_id == denied.explicit_apply_id
    assert approved_by_id is None
    assert denied_by_id is not None
    assert denied_by_id.model_dump(mode="json") == denied.model_dump(mode="json")


def test_explicit_runtime_apply_stabilization_api_owner_scope_and_read_only_behavior(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    owner = TestClient(app)
    other = TestClient(app)
    anonymous = TestClient(app)

    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    shell = _prepare_client_shell(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply")
    before_shell = repository.get_simulado_controlled_apply_shell_by_id(
        shell.apply_shell_id,
        user_id=owner_user_id,
    )
    build = owner.post(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply/build",
        json=approve_payload(),
    )
    loaded = owner.get(f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply")
    explicit_apply_id = build.json()["explicit_apply_id"]
    by_id = owner.get(f"/api/simulado-explicit-apply/{explicit_apply_id}")
    after_shell = repository.get_simulado_controlled_apply_shell_by_id(
        shell.apply_shell_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json() == by_id.json()
    assert before_shell is not None
    assert after_shell is not None
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")

    assert anonymous.post(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply/build",
        json=approve_payload(),
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-explicit-apply/{explicit_apply_id}").status_code == 401

    assert other.post(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply/build",
        json=approve_payload(),
    ).status_code == 404
    assert other.get(
        f"/api/simulado-controlled-apply-shell/{shell.apply_shell_id}/explicit-apply"
    ).status_code == 404
    assert other.get(f"/api/simulado-explicit-apply/{explicit_apply_id}").status_code == 404


def test_explicit_runtime_apply_stabilization_preserves_runtime_and_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = no_runtime_application_fixture(tmp_path / "runtime", repository=repository)
    source_shell = fixture.controlled_apply_shell
    assert source_shell is not None

    before_shell = repository.get_simulado_controlled_apply_shell_by_id(
        source_shell.apply_shell_id,
        user_id=fixture.context.user_id,
    )
    before_application = repository.get_simulado_runtime_progress_application_by_id(
        source_shell.source_application_id,
        user_id=fixture.context.user_id,
    )
    before_runtime_guardrail = repository.get_simulado_runtime_guardrail_by_id(
        source_shell.source_runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_integrated = repository.get_simulado_integrated_result_by_id(
        source_shell.source_integrated_result_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    result = build_explicit_runtime_apply(fixture, decision_payload=approve_payload())
    assert result is not None
    _assert_no_runtime_mutation_flags(result)

    after_shell = repository.get_simulado_controlled_apply_shell_by_id(
        source_shell.apply_shell_id,
        user_id=fixture.context.user_id,
    )
    after_application = repository.get_simulado_runtime_progress_application_by_id(
        source_shell.source_application_id,
        user_id=fixture.context.user_id,
    )
    after_runtime_guardrail = repository.get_simulado_runtime_guardrail_by_id(
        source_shell.source_runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_integrated = repository.get_simulado_integrated_result_by_id(
        source_shell.source_integrated_result_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)

    assert before_shell is not None
    assert before_application is not None
    assert before_runtime_guardrail is not None
    assert before_integrated is not None
    assert after_shell is not None
    assert after_application is not None
    assert after_runtime_guardrail is not None
    assert after_integrated is not None
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
    assert before_application.model_dump(mode="json") == after_application.model_dump(mode="json")
    assert before_runtime_guardrail.model_dump(mode="json") == after_runtime_guardrail.model_dump(mode="json")
    assert before_integrated.model_dump(mode="json") == after_integrated.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
