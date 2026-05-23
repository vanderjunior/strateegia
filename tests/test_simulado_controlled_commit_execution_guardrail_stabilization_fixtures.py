import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
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
    execution_guardrail_mode_status_fixture,
    final_execution_approval_missing_fixture,
    idempotency_fixture,
    missing_commit_transaction_fixture,
    mixed_execution_guardrail_fixture,
    no_commit_execution_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    planned_progress_commits_not_executable_fixture,
    planned_surface_commits_not_executable_fixture,
    progress_commit_execution_checks_shape_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_not_ready_fixture,
    rollback_readiness_shape_fixture,
    runtime_surface_risk_summary_fixture,
    surface_commit_execution_checks_shape_fixture,
    transaction_already_executed_fixture,
    transaction_not_plan_only_fixture,
    transaction_not_valid_for_execution_fixture,
    transaction_plan_only_fixture,
    user_scope_fixture,
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


def _assert_no_runtime_mutation_flags(result) -> None:
    assert result.execution_guardrail_created is True
    assert result.execution_guardrail_mode in {
        "execution_guardrail_only",
        "controlled_execution_readiness",
    }
    assert result.execution_guardrail_status != "executed"
    assert result.commit_execution_allowed is False
    assert result.commit_execution_started is False
    assert result.commit_executed is False
    assert result.mutation_committed is False
    assert result.commit_transaction_valid_for_execution is False
    assert result.commit_execution_ready is False
    assert result.no_commit_execution is True
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
    for key in FORBIDDEN_GUARDRAIL_KEYS:
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


def _prepare_commit_transaction(repository: JsonStudyRepository, tmp_path, user_id: str):
    fixture = user_scope_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.commit_transaction
    assert transaction is not None
    return transaction


def test_controlled_commit_execution_guardrail_stabilization_fixtures_are_deterministic_and_json_safe(tmp_path):
    missing = missing_commit_transaction_fixture(tmp_path / "missing")
    plan_only = transaction_plan_only_fixture(tmp_path / "plan-only")
    mode_status = execution_guardrail_mode_status_fixture(tmp_path / "mode-status")
    mixed = mixed_execution_guardrail_fixture(tmp_path / "mixed")

    assert missing.missing_commit_transaction_id == "simulado-commit-transaction:missing"
    assert plan_only.commit_transaction is not None
    assert mode_status.commit_transaction is not None
    assert mixed.commit_transaction is not None
    assert json.dumps({"fixture": "controlled-commit-execution-guardrail"}, ensure_ascii=True)


def test_controlled_commit_execution_guardrail_stabilization_covers_transaction_scenarios_and_blockers(tmp_path):
    missing = build_controlled_commit_execution_guardrail(
        missing_commit_transaction_fixture(tmp_path / "missing")
    )
    plan_only = build_controlled_commit_execution_guardrail(
        transaction_plan_only_fixture(tmp_path / "plan-only")
    )
    not_plan_only = build_controlled_commit_execution_guardrail(
        transaction_not_plan_only_fixture(tmp_path / "not-plan-only")
    )
    already_executed = build_controlled_commit_execution_guardrail(
        transaction_already_executed_fixture(tmp_path / "already-executed")
    )
    invalid = build_controlled_commit_execution_guardrail(
        transaction_not_valid_for_execution_fixture(tmp_path / "invalid")
    )
    execution_not_ready = build_controlled_commit_execution_guardrail(
        commit_execution_not_ready_fixture(tmp_path / "execution-not-ready")
    )
    rollback = build_controlled_commit_execution_guardrail(
        rollback_not_ready_fixture(tmp_path / "rollback")
    )
    progress = build_controlled_commit_execution_guardrail(
        planned_progress_commits_not_executable_fixture(tmp_path / "progress")
    )
    surface = build_controlled_commit_execution_guardrail(
        planned_surface_commits_not_executable_fixture(tmp_path / "surface")
    )
    audit = build_controlled_commit_execution_guardrail(
        audit_requirements_unsatisfied_fixture(tmp_path / "audit")
    )
    final_approval = build_controlled_commit_execution_guardrail(
        final_execution_approval_missing_fixture(tmp_path / "final-approval")
    )
    disabled = build_controlled_commit_execution_guardrail(
        commit_execution_disabled_fixture(tmp_path / "disabled")
    )
    unsafe = build_controlled_commit_execution_guardrail(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )

    assert missing is None

    assert plan_only is not None
    assert plan_only.readiness_summary.source_commit_transaction_present is True
    assert plan_only.readiness_summary.source_transaction_plan_only is True
    assert plan_only.readiness_summary.source_transaction_not_executed is True
    _assert_no_runtime_mutation_flags(plan_only)

    assert not_plan_only is not None
    assert not_plan_only.readiness_state == "blocked_by_transaction_not_plan_only"
    _assert_no_runtime_mutation_flags(not_plan_only)

    assert already_executed is not None
    assert already_executed.readiness_state == "blocked_by_transaction_already_executed"
    _assert_no_runtime_mutation_flags(already_executed)

    assert invalid is not None
    assert invalid.readiness_state == "blocked_by_commit_transaction_not_valid_for_execution"
    _assert_no_runtime_mutation_flags(invalid)

    assert execution_not_ready is not None
    assert execution_not_ready.readiness_state == "blocked_by_commit_execution_not_ready"
    _assert_no_runtime_mutation_flags(execution_not_ready)

    assert rollback is not None
    assert rollback.readiness_state == "blocked_by_rollback_not_ready"
    assert rollback.rollback_readiness.rollback_execution_ready is False
    _assert_no_runtime_mutation_flags(rollback)

    assert progress is not None
    assert progress.readiness_state == "blocked_by_progress_commits_not_executable"
    _assert_no_runtime_mutation_flags(progress)

    assert surface is not None
    assert surface.readiness_state == "blocked_by_surface_commits_not_executable"
    _assert_no_runtime_mutation_flags(surface)

    assert audit is not None
    assert audit.readiness_state == "blocked_by_audit_requirements_unsatisfied"
    for item in audit.audit_requirements:
        assert item.required is True
        assert item.satisfied is False
    _assert_no_runtime_mutation_flags(audit)

    assert final_approval is not None
    assert final_approval.readiness_state == "blocked_by_final_execution_approval_missing"
    _assert_no_runtime_mutation_flags(final_approval)

    assert disabled is not None
    assert disabled.readiness_state == "blocked_by_commit_execution_disabled"
    _assert_no_runtime_mutation_flags(disabled)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    _assert_no_runtime_mutation_flags(unsafe)


def test_controlled_commit_execution_guardrail_stabilization_covers_checks_summaries_audit_and_safety(
    tmp_path,
):
    progress = build_controlled_commit_execution_guardrail(
        progress_commit_execution_checks_shape_fixture(tmp_path / "progress")
    )
    surface = build_controlled_commit_execution_guardrail(
        surface_commit_execution_checks_shape_fixture(tmp_path / "surface")
    )
    risk = build_controlled_commit_execution_guardrail(
        runtime_surface_risk_summary_fixture(tmp_path / "risk")
    )
    rollback = build_controlled_commit_execution_guardrail(
        rollback_readiness_shape_fixture(tmp_path / "rollback")
    )
    requirements = build_controlled_commit_execution_guardrail(
        audit_requirements_shape_fixture(tmp_path / "requirements")
    )
    audit = build_controlled_commit_execution_guardrail(
        audit_trail_fixture(tmp_path / "audit")
    )
    mode_status = build_controlled_commit_execution_guardrail(
        execution_guardrail_mode_status_fixture(tmp_path / "mode-status")
    )
    mixed = build_controlled_commit_execution_guardrail(
        mixed_execution_guardrail_fixture(tmp_path / "mixed")
    )
    safe = build_controlled_commit_execution_guardrail(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe")
    )
    no_commit = build_controlled_commit_execution_guardrail(
        no_commit_execution_fixture(tmp_path / "no-commit")
    )
    no_runtime_application = build_controlled_commit_execution_guardrail(
        no_runtime_application_fixture(tmp_path / "no-runtime-application")
    )
    mutation = build_controlled_commit_execution_guardrail(
        no_runtime_mutation_fixture(tmp_path / "mutation")
    )

    assert progress is not None
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

    assert risk is not None
    assert risk.runtime_surface_risk_summary.executable_surface_count == 0
    assert risk.runtime_surface_risk_summary.blocked_surface_count >= 0
    assert risk.runtime_surface_risk_summary.risky_surface_count >= 0

    assert rollback is not None
    assert rollback.rollback_readiness.rollback_required is True
    assert rollback.rollback_readiness.rollback_available is False
    assert rollback.rollback_readiness.rollback_verified is False
    assert rollback.rollback_readiness.rollback_execution_ready is False
    assert rollback.rollback_readiness.rollback_execution_performed is False

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

    assert mode_status is not None
    assert mode_status.execution_guardrail_mode in {
        "execution_guardrail_only",
        "controlled_execution_readiness",
    }
    assert mode_status.execution_guardrail_status != "executed"
    _assert_no_runtime_mutation_flags(mode_status)

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


def test_controlled_commit_execution_guardrail_stabilization_is_idempotent_owner_only_and_read_only(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = idempotency_fixture(tmp_path / "idempotent", repository=repository)
    source_transaction = fixture.commit_transaction
    assert source_transaction is not None
    first = build_controlled_commit_execution_guardrail(fixture)
    second = build_controlled_commit_execution_guardrail(fixture)
    service = SimuladoControlledRuntimeCommitExecutionGuardrailService(repository)

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
    assert len(
        repository.list_user_simulado_controlled_commit_execution_guardrails(
            user_id=fixture.context.user_id
        )
    ) == 1

    before_transaction = repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        source_transaction.commit_transaction_id,
        user_id=fixture.context.user_id,
    )
    loaded = service.get_execution_guardrail(
        source_transaction.commit_transaction_id,
        user_id=fixture.context.user_id,
    )
    after_transaction = repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        source_transaction.commit_transaction_id,
        user_id=fixture.context.user_id,
    )
    assert loaded is not None
    assert before_transaction is not None
    assert after_transaction is not None
    assert before_transaction.model_dump(mode="json") == after_transaction.model_dump(mode="json")

    owner = TestClient(create_app(repository=repository))
    other = TestClient(create_app(repository=repository))
    anonymous = TestClient(create_app(repository=repository))
    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    transaction = _prepare_commit_transaction(repository, tmp_path / "owner-scope", owner_user_id)

    missing = owner.get(
        f"/api/simulado-commit-transaction/{transaction.commit_transaction_id}/execution-guardrail"
    )
    build = owner.post(
        f"/api/simulado-commit-transaction/{transaction.commit_transaction_id}/execution-guardrail/build"
    )
    loaded_owner = owner.get(
        f"/api/simulado-commit-transaction/{transaction.commit_transaction_id}/execution-guardrail"
    )
    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded_owner.status_code == 200

    guardrail_id = build.json()["execution_guardrail_id"]
    assert other.post(
        f"/api/simulado-commit-transaction/{transaction.commit_transaction_id}/execution-guardrail/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-commit-transaction/{transaction.commit_transaction_id}/execution-guardrail"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-commit-execution-guardrail/{guardrail_id}"
    ).status_code == 404
    assert anonymous.post(
        f"/api/simulado-commit-transaction/{transaction.commit_transaction_id}/execution-guardrail/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-commit-transaction/{transaction.commit_transaction_id}/execution-guardrail"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-commit-execution-guardrail/{guardrail_id}"
    ).status_code == 401

    before_owner_transaction = repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        transaction.commit_transaction_id,
        user_id=owner_user_id,
    )
    reread = owner.get(
        f"/api/simulado-commit-transaction/{transaction.commit_transaction_id}/execution-guardrail"
    )
    after_owner_transaction = repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        transaction.commit_transaction_id,
        user_id=owner_user_id,
    )
    assert reread.status_code == 200
    assert before_owner_transaction is not None
    assert after_owner_transaction is not None
    assert (
        before_owner_transaction.model_dump(mode="json")
        == after_owner_transaction.model_dump(mode="json")
    )
