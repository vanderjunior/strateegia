import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_apply_policy import SimuladoRuntimeApplyPolicyService
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_apply_policies import (
    api_readonly_fixture,
    apply_scope_not_allowed_fixture,
    apply_scope_policy_shape_fixture,
    audit_requirement_missing_fixture,
    audit_requirement_shape_fixture,
    build_runtime_apply_policy,
    capture_runtime_apply_policy_source_snapshot,
    environment_not_safe_fixture,
    environment_safety_requirement_shape_fixture,
    feature_flag_disabled_fixture,
    feature_flag_snapshot_shape_fixture,
    final_event_already_applied_fixture,
    final_event_not_proposal_only_fixture,
    human_review_requirement_missing_fixture,
    human_review_requirement_shape_fixture,
    idempotency_fixture,
    idempotency_requirement_missing_fixture,
    idempotency_requirement_shape_fixture,
    missing_final_event_fixture,
    mixed_policy_fixture,
    no_applied_final_event_fixture,
    no_applied_progress_ledger_entry_fixture,
    no_runtime_mutation_fixture,
    policy_audit_trail_fixture,
    policy_summary_shape_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_requirement_missing_fixture,
    rollback_requirement_shape_fixture,
    runtime_apply_not_allowed_now_fixture,
    stabilization_fixture_builders,
)


FORBIDDEN_RUNTIME_POLICY_KEYS = {
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
    "applied_final_pedagogical_update_event",
    "applied_progress_ledger_entry",
    "commit_execution_event",
    "mutation_commit_event",
    "runtime_application_event",
    "raw_runtime_block",
}

ALLOWED_RUNTIME_POLICY_MODES = {"policy_gate_only", "feature_flag_gate_only"}
ALLOWED_RUNTIME_POLICY_STATUSES = {
    "apply_blocked",
    "apply_not_enabled",
    "policy_needs_review",
    "runtime_apply_policy_created",
    "ready_for_future_minimal_apply_review",
}
ALLOWED_AUDIT_EVENTS = {
    "runtime_apply_policy_created",
    "runtime_apply_policy_evaluated",
    "runtime_apply_feature_flag_disabled",
    "runtime_apply_blocked",
    "idempotency_required",
    "rollback_required",
    "audit_required",
    "human_review_required",
    "environment_not_safe_for_apply",
    "no_applied_final_pedagogical_update_event",
    "no_applied_progress_ledger_entry",
    "no_runtime_application",
    "no_progress_mutation",
    "no_ranking_update",
    "no_retention_update",
    "no_scheduler_update",
    "no_study_cycle_update",
    "no_curriculum_graph_update",
    "no_adaptive_tuning_update",
}
EXPECTED_BLOCKED_SURFACES = {
    "minimal_progress_ledger",
    "ranking",
    "retention",
    "scheduler",
    "study_cycle",
    "curriculum_graph",
    "adaptive_tuning",
}


def _assert_no_apply_or_runtime_mutation_flags(result) -> None:
    assert result.runtime_apply_policy_created is True
    assert result.runtime_apply_policy_mode in ALLOWED_RUNTIME_POLICY_MODES
    assert result.runtime_apply_policy_status in ALLOWED_RUNTIME_POLICY_STATUSES
    assert result.runtime_apply_allowed_now is False
    assert result.final_event_apply_allowed is False
    assert result.final_event_applied is False
    assert result.final_event_application_started is False
    assert result.final_event_application_completed is False
    assert result.minimal_progress_ledger_apply_allowed is False
    assert result.ranking_apply_allowed is False
    assert result.retention_apply_allowed is False
    assert result.scheduler_apply_allowed is False
    assert result.study_cycle_apply_allowed is False
    assert result.curriculum_graph_apply_allowed is False
    assert result.adaptive_tuning_apply_allowed is False
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
    assert result.commit_executed is False
    assert result.mutation_committed is False
    assert result.no_commit_execution is True
    assert result.no_commit_execution_event_created is True
    assert result.no_mutation_commit is True
    assert result.no_mutation_commit_event_created is True
    assert result.no_runtime_application is True
    assert result.no_progress_mutation is True
    assert result.no_ranking_update is True
    assert result.no_retention_update is True
    assert result.no_scheduler_update is True
    assert result.no_study_cycle_update is True
    assert result.no_curriculum_graph_update is True
    assert result.no_adaptive_tuning_update is True
    assert result.no_applied_final_pedagogical_update_event is True
    assert result.no_applied_progress_ledger_entry is True
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


def _assert_no_leakage(payload: dict[str, object]) -> None:
    dumped = json.dumps(payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(payload)
    for key in FORBIDDEN_RUNTIME_POLICY_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "/uploads/" not in dumped
    assert "data:image" not in dumped
    assert "final_question_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys
    assert "final_answer_key_content" not in dumped_keys


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


def _prepare_final_event(repository: JsonStudyRepository, tmp_path, user_id: str):
    fixture = api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    final_event = fixture.final_event
    assert final_event is not None
    return final_event


def test_runtime_apply_policy_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    builders = stabilization_fixture_builders()

    for name, builder in builders.items():
        fixture = builder(tmp_path / name)
        mirror = builder(tmp_path / f"{name}-mirror")

        assert json.dumps({"fixture": name}, ensure_ascii=True)
        assert fixture.context.user_id == "user-a"
        if fixture.final_event is None:
            assert mirror.final_event is None
            assert fixture.missing_final_event_id == mirror.missing_final_event_id
            continue

        assert mirror.final_event is not None
        assert fixture.final_event.final_event_id == mirror.final_event.final_event_id
        assert fixture.final_event.user_id == fixture.context.user_id


def test_runtime_apply_policy_stabilization_covers_source_scenarios_and_blockers(tmp_path):
    missing = build_runtime_apply_policy(missing_final_event_fixture(tmp_path / "missing"))
    not_proposal_only = build_runtime_apply_policy(
        final_event_not_proposal_only_fixture(tmp_path / "not-proposal")
    )
    already_applied = build_runtime_apply_policy(
        final_event_already_applied_fixture(tmp_path / "already-applied")
    )
    feature_flag_disabled = build_runtime_apply_policy(
        feature_flag_disabled_fixture(tmp_path / "feature-flag-disabled")
    )
    not_allowed_now = build_runtime_apply_policy(
        runtime_apply_not_allowed_now_fixture(tmp_path / "not-allowed-now")
    )
    idempotency_missing = build_runtime_apply_policy(
        idempotency_requirement_missing_fixture(tmp_path / "idempotency-missing")
    )
    rollback_missing = build_runtime_apply_policy(
        rollback_requirement_missing_fixture(tmp_path / "rollback-missing")
    )
    audit_missing = build_runtime_apply_policy(
        audit_requirement_missing_fixture(tmp_path / "audit-missing")
    )
    human_review_missing = build_runtime_apply_policy(
        human_review_requirement_missing_fixture(tmp_path / "human-review-missing")
    )
    environment_unsafe = build_runtime_apply_policy(
        environment_not_safe_fixture(tmp_path / "environment-unsafe")
    )
    apply_scope_blocked = build_runtime_apply_policy(
        apply_scope_not_allowed_fixture(tmp_path / "apply-scope-blocked")
    )
    unsafe = build_runtime_apply_policy(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )

    assert missing is None

    assert not_proposal_only is not None
    assert not_proposal_only.readiness_state == "blocked_by_final_event_not_proposal_only"
    _assert_no_apply_or_runtime_mutation_flags(not_proposal_only)

    assert already_applied is not None
    assert already_applied.readiness_state == "blocked_by_final_event_already_applied"
    _assert_no_apply_or_runtime_mutation_flags(already_applied)

    assert feature_flag_disabled is not None
    assert feature_flag_disabled.runtime_apply_feature_flag_enabled is False
    assert feature_flag_disabled.readiness_state == "blocked_by_runtime_apply_feature_flag_disabled"
    _assert_no_apply_or_runtime_mutation_flags(feature_flag_disabled)

    assert not_allowed_now is not None
    assert not_allowed_now.runtime_apply_feature_flag_enabled is True
    assert not_allowed_now.readiness_state == "blocked_by_runtime_apply_not_allowed_now"
    _assert_no_apply_or_runtime_mutation_flags(not_allowed_now)

    assert idempotency_missing is not None
    assert idempotency_missing.readiness_state == "blocked_by_idempotency_requirement_missing"
    _assert_no_apply_or_runtime_mutation_flags(idempotency_missing)

    assert rollback_missing is not None
    assert rollback_missing.readiness_state == "blocked_by_rollback_requirement_missing"
    _assert_no_apply_or_runtime_mutation_flags(rollback_missing)

    assert audit_missing is not None
    assert audit_missing.readiness_state == "blocked_by_audit_requirement_missing"
    _assert_no_apply_or_runtime_mutation_flags(audit_missing)

    assert human_review_missing is not None
    assert human_review_missing.readiness_state == "blocked_by_human_review_requirement_missing"
    _assert_no_apply_or_runtime_mutation_flags(human_review_missing)

    assert environment_unsafe is not None
    assert environment_unsafe.readiness_state == "blocked_by_environment_not_safe_for_apply"
    _assert_no_apply_or_runtime_mutation_flags(environment_unsafe)

    assert apply_scope_blocked is not None
    assert apply_scope_blocked.readiness_state == "blocked_by_apply_scope_not_allowed"
    _assert_no_apply_or_runtime_mutation_flags(apply_scope_blocked)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    assert unsafe.policy_summary.unsafe_public_answer_key_exposure_detected is True
    assert unsafe.policy_summary.unsafe_gabarito_exposure_detected is True
    _assert_no_apply_or_runtime_mutation_flags(unsafe)
    _assert_no_leakage(unsafe.model_dump(mode="json"))


def test_runtime_apply_policy_stabilization_covers_summary_scope_requirements_and_audit(tmp_path):
    summary = build_runtime_apply_policy(policy_summary_shape_fixture(tmp_path / "summary"))
    feature_flag = build_runtime_apply_policy(
        feature_flag_snapshot_shape_fixture(tmp_path / "feature-flag")
    )
    scope_policy = build_runtime_apply_policy(
        apply_scope_policy_shape_fixture(tmp_path / "scope-policy")
    )
    idempotency_requirement = build_runtime_apply_policy(
        idempotency_requirement_shape_fixture(tmp_path / "idempotency")
    )
    rollback_requirement = build_runtime_apply_policy(
        rollback_requirement_shape_fixture(tmp_path / "rollback")
    )
    audit_requirement = build_runtime_apply_policy(
        audit_requirement_shape_fixture(tmp_path / "audit")
    )
    human_review_requirement = build_runtime_apply_policy(
        human_review_requirement_shape_fixture(tmp_path / "human-review")
    )
    environment_requirement = build_runtime_apply_policy(
        environment_safety_requirement_shape_fixture(tmp_path / "environment")
    )
    audit_trail = build_runtime_apply_policy(policy_audit_trail_fixture(tmp_path / "audit-trail"))

    assert summary is not None
    assert summary.runtime_apply_policy_mode in ALLOWED_RUNTIME_POLICY_MODES
    assert summary.runtime_apply_policy_status in ALLOWED_RUNTIME_POLICY_STATUSES
    assert summary.runtime_apply_feature_flag_enabled is False
    assert summary.runtime_apply_allowed_now is False
    assert summary.final_event_apply_allowed is False
    assert summary.final_event_applied is False
    assert summary.policy_summary.source_final_event_present is True
    assert summary.policy_summary.source_final_event_created is True
    assert summary.policy_summary.source_final_event_applied is False
    assert summary.policy_summary.source_final_event_apply_allowed is False
    assert summary.policy_summary.source_event_proposal_only is True
    assert summary.policy_summary.apply_feature_flag_enabled is False
    assert summary.policy_summary.apply_allowed_now is False
    assert summary.policy_summary.idempotency_required is True
    assert summary.policy_summary.rollback_required is True
    assert summary.policy_summary.audit_required is True
    assert summary.policy_summary.human_review_required is True
    assert summary.policy_summary.environment_safe_for_apply is False
    assert summary.policy_summary.unsafe_public_answer_key_exposure_detected is False
    assert summary.policy_summary.unsafe_gabarito_exposure_detected is False
    _assert_no_apply_or_runtime_mutation_flags(summary)

    assert feature_flag is not None
    assert feature_flag.feature_flag_snapshot.feature_flag_name == "simulado_runtime_apply_enabled"
    assert feature_flag.feature_flag_snapshot.feature_flag_enabled is False
    assert feature_flag.feature_flag_snapshot.default_enabled is False
    assert feature_flag.feature_flag_snapshot.source == "foundation_default"
    assert feature_flag.feature_flag_snapshot.environment == "local_default"

    assert scope_policy is not None
    assert scope_policy.apply_scope_policy.allowed_surfaces == []
    assert set(scope_policy.apply_scope_policy.blocked_surfaces) == EXPECTED_BLOCKED_SURFACES
    assert scope_policy.apply_scope_policy.minimal_progress_ledger_apply_allowed is False
    assert scope_policy.apply_scope_policy.ranking_apply_allowed is False
    assert scope_policy.apply_scope_policy.retention_apply_allowed is False
    assert scope_policy.apply_scope_policy.scheduler_apply_allowed is False
    assert scope_policy.apply_scope_policy.study_cycle_apply_allowed is False
    assert scope_policy.apply_scope_policy.curriculum_graph_apply_allowed is False
    assert scope_policy.apply_scope_policy.adaptive_tuning_apply_allowed is False

    assert idempotency_requirement is not None
    assert idempotency_requirement.idempotency_requirement.idempotency_key_required is True
    assert idempotency_requirement.idempotency_requirement.idempotency_key_present is False
    assert idempotency_requirement.idempotency_requirement.idempotency_key_valid is False
    assert idempotency_requirement.idempotency_requirement.satisfied is False

    assert rollback_requirement is not None
    assert rollback_requirement.rollback_requirement.rollback_required is True
    assert rollback_requirement.rollback_requirement.rollback_plan_required is True
    assert rollback_requirement.rollback_requirement.rollback_plan_present is False
    assert rollback_requirement.rollback_requirement.rollback_verified is False
    assert rollback_requirement.rollback_requirement.satisfied is False

    assert audit_requirement is not None
    assert audit_requirement.audit_requirement.audit_required is True
    assert audit_requirement.audit_requirement.audit_confirmation_required is True
    assert audit_requirement.audit_requirement.audit_confirmation_present is False
    assert audit_requirement.audit_requirement.satisfied is False

    assert human_review_requirement is not None
    assert human_review_requirement.human_review_requirement.human_review_required is True
    assert human_review_requirement.human_review_requirement.human_review_present is False
    assert human_review_requirement.human_review_requirement.satisfied is False

    assert environment_requirement is not None
    assert environment_requirement.environment_safety_requirement.environment_safe_for_apply is False
    assert environment_requirement.environment_safety_requirement.write_mode_allowed is False
    assert environment_requirement.environment_safety_requirement.dry_run_only is True
    assert environment_requirement.environment_safety_requirement.external_services_disabled is True
    assert environment_requirement.environment_safety_requirement.satisfied is False

    assert audit_trail is not None
    assert ALLOWED_AUDIT_EVENTS.issubset({item.event_type for item in audit_trail.audit_trail})
    _assert_no_apply_or_runtime_mutation_flags(audit_trail)


def test_runtime_apply_policy_stabilization_preserves_no_leakage_and_runtime_state(tmp_path):
    no_applied_final_event = build_runtime_apply_policy(
        no_applied_final_event_fixture(tmp_path / "no-applied-final-event")
    )
    no_applied_progress_ledger = build_runtime_apply_policy(
        no_applied_progress_ledger_entry_fixture(tmp_path / "no-applied-ledger")
    )
    no_runtime_mutation = build_runtime_apply_policy(
        no_runtime_mutation_fixture(tmp_path / "no-runtime-mutation")
    )
    mixed = build_runtime_apply_policy(mixed_policy_fixture(tmp_path / "mixed"))

    assert no_applied_final_event is not None
    assert no_applied_final_event.final_event_apply_allowed is False
    assert no_applied_final_event.final_event_applied is False
    assert no_applied_final_event.final_event_application_started is False
    assert no_applied_final_event.final_event_application_completed is False
    assert no_applied_final_event.no_applied_final_pedagogical_update_event is True
    _assert_no_apply_or_runtime_mutation_flags(no_applied_final_event)

    assert no_applied_progress_ledger is not None
    assert no_applied_progress_ledger.minimal_progress_ledger_apply_allowed is False
    assert no_applied_progress_ledger.no_applied_progress_ledger_entry is True
    _assert_no_apply_or_runtime_mutation_flags(no_applied_progress_ledger)

    assert no_runtime_mutation is not None
    _assert_no_apply_or_runtime_mutation_flags(no_runtime_mutation)

    assert mixed is not None
    assert mixed.blockers
    assert mixed.validation_findings
    assert mixed.warnings
    assert {warning.code for warning in mixed.warnings} >= {
        "runtime_apply_policy_gate_only",
        "runtime_apply_policy_blocked",
    }
    _assert_no_apply_or_runtime_mutation_flags(mixed)
    _assert_no_leakage(mixed.model_dump(mode="json"))


def test_runtime_apply_policy_stabilization_persistence_idempotency_and_source_preservation(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = idempotency_fixture(tmp_path / "idempotent", repository=repository)
    service = SimuladoRuntimeApplyPolicyService(repository)
    final_event = fixture.final_event
    assert final_event is not None

    before = capture_runtime_apply_policy_source_snapshot(fixture)
    first = build_runtime_apply_policy(fixture)
    after_first = capture_runtime_apply_policy_source_snapshot(fixture)
    second = build_runtime_apply_policy(fixture)
    loaded = service.get_runtime_apply_policy(
        final_event.final_event_id,
        user_id=fixture.context.user_id,
    )
    loaded_by_id = service.get_runtime_apply_policy_by_id(
        first.runtime_apply_policy_id if first is not None else "missing",
        user_id=fixture.context.user_id,
    )
    after_second = capture_runtime_apply_policy_source_snapshot(fixture)

    assert first is not None
    assert second is not None
    assert loaded is not None
    assert loaded_by_id is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.model_dump(mode="json") == loaded.model_dump(mode="json")
    assert first.model_dump(mode="json") == loaded_by_id.model_dump(mode="json")
    assert before.final_event == after_second.final_event
    assert before.controlled_execution == after_second.controlled_execution
    assert before.execution_plan == after_second.execution_plan
    assert before.execution_approval == after_second.execution_approval
    assert before.execution_guardrail == after_second.execution_guardrail
    assert before.progress == after_second.progress
    assert before.runtime_apply_policy_count == 0
    assert after_first.runtime_apply_policy_count == 1
    assert after_second.runtime_apply_policy_count == 1


def test_runtime_apply_policy_stabilization_api_owner_scope_and_read_only_behavior(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    owner = TestClient(app)
    other = TestClient(app)
    anonymous = TestClient(app)

    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    final_event = _prepare_final_event(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy"
    )
    before_final_event = repository.get_simulado_final_pedagogical_update_event_by_id(
        final_event.final_event_id,
        user_id=owner_user_id,
    )
    first_build = owner.post(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy/build"
    )
    second_build = owner.post(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy/build"
    )
    loaded = owner.get(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy"
    )
    runtime_apply_policy_id = first_build.json()["runtime_apply_policy_id"]
    by_id = owner.get(f"/api/simulado-runtime-apply-policy/{runtime_apply_policy_id}")
    after_final_event = repository.get_simulado_final_pedagogical_update_event_by_id(
        final_event.final_event_id,
        user_id=owner_user_id,
    )
    listed = repository.list_user_simulado_runtime_apply_policies(user_id=owner_user_id)

    assert missing.status_code == 404
    assert first_build.status_code == 200
    assert second_build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert first_build.json() == second_build.json() == loaded.json() == by_id.json()
    assert len(listed) == 1
    assert before_final_event is not None
    assert after_final_event is not None
    assert before_final_event.model_dump(mode="json") == after_final_event.model_dump(mode="json")

    response_payload = loaded.json()
    _assert_no_leakage(response_payload)
    assert response_payload["source_final_event_id"] == final_event.final_event_id
    assert response_payload["runtime_apply_policy_created"] is True
    assert response_payload["runtime_apply_feature_flag_enabled"] is False
    assert response_payload["runtime_apply_allowed_now"] is False
    assert response_payload["final_event_apply_allowed"] is False
    assert response_payload["final_event_applied"] is False
    assert response_payload["minimal_progress_ledger_apply_allowed"] is False
    assert response_payload["runtime_application_enabled"] is False
    assert response_payload["runtime_application_applied"] is False
    assert response_payload["progress_mutation_enabled"] is False
    assert response_payload["progress_mutation_applied"] is False
    assert response_payload["answer_key_publicly_exposed"] is False
    assert response_payload["gabarito_publicly_exposed"] is False

    assert anonymous.post(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-runtime-apply-policy/{runtime_apply_policy_id}"
    ).status_code == 401

    assert other.post(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-final-pedagogical-event/{final_event.final_event_id}/runtime-apply-policy"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-runtime-apply-policy/{runtime_apply_policy_id}"
    ).status_code == 404
