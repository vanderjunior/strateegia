import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_commit_execution_plan import (
    SimuladoRuntimeCommitExecutionPlanService,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys
from tests.fixtures.simulado_runtime_commit_execution_plans import (
    api_readonly_fixture,
    approval_approved_for_future_review_fixture,
    approval_not_approved_fixture,
    audit_checkpoints_incomplete_fixture,
    audit_checkpoints_shape_fixture,
    build_runtime_commit_execution_plan,
    confirmations_incomplete_fixture,
    execution_disabled_fixture,
    execution_now_not_allowed_fixture,
    execution_plan_mode_status_fixture,
    execution_plan_summary_shape_fixture,
    idempotency_fixture,
    missing_execution_approval_fixture,
    mixed_execution_plan_fixture,
    no_commit_execution_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    planned_phases_shape_fixture,
    planned_progress_steps_shape_fixture,
    planned_surface_steps_shape_fixture,
    progress_approvals_not_ready_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_checkpoints_incomplete_fixture,
    rollback_checkpoints_shape_fixture,
    surface_approvals_not_ready_fixture,
    user_scope_fixture,
)


FORBIDDEN_EXECUTION_PLAN_KEYS = {
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

ALLOWED_PHASE_TYPES = {
    "preflight_validation",
    "rollback_checkpoint_validation",
    "progress_step_review",
    "surface_step_review",
    "audit_checkpoint_review",
    "final_execution_review",
    "unknown",
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

ALLOWED_ROLLBACK_CHECKPOINT_TYPES = {
    "rollback_plan_available",
    "rollback_verified",
    "rollback_snapshot_reference_safe",
    "rollback_human_review",
    "unknown",
}

ALLOWED_AUDIT_CHECKPOINT_TYPES = {
    "final_execution_approval",
    "audit_confirmation",
    "runtime_surface_confirmation",
    "public_answer_key_absence_confirmation",
    "human_review_confirmation",
    "no_commit_execution_confirmation",
    "unknown",
}


def _assert_no_runtime_mutation_flags(result) -> None:
    assert result.execution_plan_created is True
    assert result.execution_plan_mode in {"execution_plan_only", "dry_run_execution_plan"}
    assert result.execution_plan_status != "executed"
    assert result.execution_allowed_now is False
    assert result.execution_started is False
    assert result.commit_execution_allowed is False
    assert result.commit_execution_started is False
    assert result.commit_executed is False
    assert result.mutation_committed is False
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
    for key in FORBIDDEN_EXECUTION_PLAN_KEYS:
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


def _prepare_execution_approval(repository: JsonStudyRepository, tmp_path, user_id: str):
    fixture = user_scope_fixture(tmp_path, user_id=user_id, repository=repository)
    execution_approval = fixture.execution_approval
    assert execution_approval is not None
    return execution_approval


def test_runtime_commit_execution_plan_stabilization_fixtures_are_deterministic_and_json_safe(
    tmp_path,
):
    missing = missing_execution_approval_fixture(tmp_path / "missing")
    approved = approval_approved_for_future_review_fixture(tmp_path / "approved")
    mode_status = execution_plan_mode_status_fixture(tmp_path / "mode-status")
    mixed = mixed_execution_plan_fixture(tmp_path / "mixed")

    assert missing.missing_execution_approval_id == "simulado-explicit-execution-approval:missing"
    assert approved.execution_approval is not None
    assert mode_status.execution_approval is not None
    assert mixed.execution_approval is not None
    assert json.dumps({"fixture": "runtime-commit-execution-plan"}, ensure_ascii=True)


def test_runtime_commit_execution_plan_stabilization_covers_source_scenarios_and_blockers(tmp_path):
    missing = build_runtime_commit_execution_plan(
        missing_execution_approval_fixture(tmp_path / "missing")
    )
    not_approved = build_runtime_commit_execution_plan(
        approval_not_approved_fixture(tmp_path / "not-approved")
    )
    approved = build_runtime_commit_execution_plan(
        approval_approved_for_future_review_fixture(tmp_path / "approved")
    )
    execution_now = build_runtime_commit_execution_plan(
        execution_now_not_allowed_fixture(tmp_path / "execution-now")
    )
    confirmations = build_runtime_commit_execution_plan(
        confirmations_incomplete_fixture(tmp_path / "confirmations")
    )
    progress = build_runtime_commit_execution_plan(
        progress_approvals_not_ready_fixture(tmp_path / "progress")
    )
    surface = build_runtime_commit_execution_plan(
        surface_approvals_not_ready_fixture(tmp_path / "surface")
    )
    rollback = build_runtime_commit_execution_plan(
        rollback_checkpoints_incomplete_fixture(tmp_path / "rollback")
    )
    audit = build_runtime_commit_execution_plan(
        audit_checkpoints_incomplete_fixture(tmp_path / "audit")
    )
    disabled = build_runtime_commit_execution_plan(
        execution_disabled_fixture(tmp_path / "disabled")
    )
    unsafe = build_runtime_commit_execution_plan(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )

    assert missing is None

    assert not_approved is not None
    assert not_approved.readiness_state == "blocked_by_execution_approval_not_approved"
    _assert_no_runtime_mutation_flags(not_approved)

    assert approved is not None
    assert approved.plan_summary.source_approval_future_review_approved is True
    assert approved.plan_summary.source_approved_for_execution_now is False
    assert approved.execution_plan_created is True
    _assert_no_runtime_mutation_flags(approved)

    assert execution_now is not None
    assert execution_now.plan_summary.source_approved_for_execution_now is False
    assert execution_now.execution_allowed_now is False
    assert all(
        "execution_now_not_allowed" in " ".join(step.blockers)
        for step in execution_now.planned_progress_steps + execution_now.planned_surface_steps
    )
    _assert_no_runtime_mutation_flags(execution_now)

    assert confirmations is not None
    assert confirmations.readiness_state == "blocked_by_confirmations_incomplete"
    _assert_no_runtime_mutation_flags(confirmations)

    assert progress is not None
    assert progress.readiness_state == "blocked_by_progress_approvals_not_ready"
    assert all(step.step_status == "step_blocked" for step in progress.planned_progress_steps)
    _assert_no_runtime_mutation_flags(progress)

    assert surface is not None
    assert surface.readiness_state == "blocked_by_surface_approvals_not_ready"
    assert all(step.step_status == "step_blocked" for step in surface.planned_surface_steps)
    _assert_no_runtime_mutation_flags(surface)

    assert rollback is not None
    assert rollback.readiness_state == "blocked_by_rollback_checkpoints_incomplete"
    _assert_no_runtime_mutation_flags(rollback)

    assert audit is not None
    assert audit.readiness_state == "blocked_by_audit_checkpoints_incomplete"
    _assert_no_runtime_mutation_flags(audit)

    assert disabled is not None
    assert disabled.readiness_state == "blocked_by_execution_disabled"
    _assert_no_runtime_mutation_flags(disabled)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    _assert_no_runtime_mutation_flags(unsafe)


def test_runtime_commit_execution_plan_stabilization_covers_summary_shapes_safety_and_idempotency(
    tmp_path,
):
    summary = build_runtime_commit_execution_plan(
        execution_plan_summary_shape_fixture(tmp_path / "summary")
    )
    phases = build_runtime_commit_execution_plan(
        planned_phases_shape_fixture(tmp_path / "phases")
    )
    progress = build_runtime_commit_execution_plan(
        planned_progress_steps_shape_fixture(tmp_path / "progress")
    )
    surface = build_runtime_commit_execution_plan(
        planned_surface_steps_shape_fixture(tmp_path / "surface")
    )
    rollback = build_runtime_commit_execution_plan(
        rollback_checkpoints_shape_fixture(tmp_path / "rollback")
    )
    audit = build_runtime_commit_execution_plan(
        audit_checkpoints_shape_fixture(tmp_path / "audit")
    )
    mode_status = build_runtime_commit_execution_plan(
        execution_plan_mode_status_fixture(tmp_path / "mode-status")
    )
    mixed = build_runtime_commit_execution_plan(
        mixed_execution_plan_fixture(tmp_path / "mixed")
    )
    safe = build_runtime_commit_execution_plan(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe")
    )
    no_commit = build_runtime_commit_execution_plan(
        no_commit_execution_fixture(tmp_path / "no-commit")
    )
    no_runtime_application = build_runtime_commit_execution_plan(
        no_runtime_application_fixture(tmp_path / "no-runtime-application")
    )
    no_runtime_mutation = build_runtime_commit_execution_plan(
        no_runtime_mutation_fixture(tmp_path / "no-runtime-mutation")
    )
    fixture = idempotency_fixture(tmp_path / "idempotent")
    first = build_runtime_commit_execution_plan(fixture)
    second = build_runtime_commit_execution_plan(fixture)

    assert summary is not None
    assert summary.plan_summary.source_approval_present is True
    assert summary.plan_summary.source_approval_recorded is True
    assert summary.plan_summary.source_approval_future_review_approved is True
    assert summary.plan_summary.source_approved_for_execution_now is False
    assert summary.plan_summary.execution_allowed_now is False
    _assert_no_runtime_mutation_flags(summary)

    assert phases is not None
    expected_phase_types = [
        "preflight_validation",
        "rollback_checkpoint_validation",
        "progress_step_review",
        "surface_step_review",
        "audit_checkpoint_review",
        "final_execution_review",
    ]
    assert [item.phase_type for item in phases.planned_execution_phases] == expected_phase_types
    for index, item in enumerate(phases.planned_execution_phases, start=1):
        assert item.phase_type in ALLOWED_PHASE_TYPES
        assert item.phase_order == index
        assert item.completed is False
        assert item.execution_allowed is False
        assert item.executed is False

    assert progress is not None
    for item in progress.planned_progress_steps:
        assert item.target_type in ALLOWED_TARGET_TYPES
        assert item.delta_kind in ALLOWED_DELTA_KINDS
        assert item.executed is False
        assert item.execution_allowed is False

    assert surface is not None
    for item in surface.planned_surface_steps:
        assert item.surface_type in ALLOWED_SURFACE_TYPES
        assert item.update_kind in ALLOWED_UPDATE_KINDS
        assert item.executed is False
        assert item.execution_allowed is False

    assert rollback is not None
    for item in rollback.rollback_checkpoints:
        assert item.checkpoint_type in ALLOWED_ROLLBACK_CHECKPOINT_TYPES
        assert item.required is True
        assert item.completed is False
        assert item.execution_allowed is False

    assert audit is not None
    for item in audit.audit_checkpoints:
        assert item.checkpoint_type in ALLOWED_AUDIT_CHECKPOINT_TYPES
        assert item.required is True
        assert item.completed is False
        assert item.execution_allowed is False

    assert mode_status is not None
    assert mode_status.execution_plan_mode in {"execution_plan_only", "dry_run_execution_plan"}
    assert mode_status.execution_plan_status != "executed"
    assert mode_status.execution_allowed_now is False
    assert mode_status.execution_started is False
    assert mode_status.commit_executed is False
    assert mode_status.mutation_committed is False

    assert mixed is not None
    assert mixed.blockers
    assert mixed.warnings

    assert safe is not None
    _assert_no_leakage(safe)

    assert no_commit is not None
    assert no_commit.no_commit_execution is True
    assert no_commit.no_commit_execution_event_created is True

    assert no_runtime_application is not None
    assert no_runtime_application.runtime_application_enabled is False
    assert no_runtime_application.runtime_application_applied is False
    assert no_runtime_application.no_runtime_application is True

    assert no_runtime_mutation is not None
    _assert_no_runtime_mutation_flags(no_runtime_mutation)

    assert first is not None
    assert second is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert fixture.context.repository.get_simulado_runtime_commit_execution_plan(
        first.source_execution_approval_id,
        user_id=fixture.context.user_id,
    ) is not None
    assert fixture.context.repository.get_simulado_runtime_commit_execution_plan_by_id(
        first.execution_plan_id,
        user_id=fixture.context.user_id,
    ) is not None


def test_runtime_commit_execution_plan_stabilization_preserves_api_scope_read_only_and_source_artifacts(
    tmp_path,
):
    owner = TestClient(create_app(repository=JsonStudyRepository(tmp_path / "study_data.json")))
    other = TestClient(owner.app)
    anonymous = TestClient(owner.app)
    repository = owner.app.state.repository

    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    execution_approval = _prepare_execution_approval(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(
        f"/api/simulado-explicit-execution-approval/{execution_approval.execution_approval_id}/execution-plan"
    )
    before_approval = repository.get_simulado_explicit_commit_execution_approval_by_id(
        execution_approval.execution_approval_id,
        user_id=owner_user_id,
    )
    before_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        execution_approval.source_execution_guardrail_id,
        user_id=owner_user_id,
    )
    before_transaction = repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        execution_approval.source_commit_transaction_id,
        user_id=owner_user_id,
    )
    before_explicit_commit = repository.get_simulado_explicit_mutation_commit_by_id(
        execution_approval.source_explicit_commit_id,
        user_id=owner_user_id,
    )
    before_shell = repository.get_simulado_controlled_mutation_commit_shell_by_id(
        execution_approval.source_commit_shell_id,
        user_id=owner_user_id,
    )
    before_mutation_transaction = repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        execution_approval.source_mutation_transaction_id,
        user_id=owner_user_id,
    )
    before_explicit_apply = repository.get_simulado_explicit_runtime_apply_by_id(
        execution_approval.source_explicit_apply_id,
        user_id=owner_user_id,
    )
    before_apply_shell = repository.get_simulado_controlled_apply_shell_by_id(
        execution_approval.source_apply_shell_id,
        user_id=owner_user_id,
    )
    before_application = repository.get_simulado_runtime_progress_application_by_id(
        execution_approval.source_application_id,
        user_id=owner_user_id,
    )
    before_progress = repository.load_progress(user_id=owner_user_id)

    build = owner.post(
        f"/api/simulado-explicit-execution-approval/{execution_approval.execution_approval_id}/execution-plan/build"
    )
    loaded = owner.get(
        f"/api/simulado-explicit-execution-approval/{execution_approval.execution_approval_id}/execution-plan"
    )
    execution_plan_id = build.json()["execution_plan_id"]
    by_id = owner.get(f"/api/simulado-execution-plan/{execution_plan_id}")

    service = SimuladoRuntimeCommitExecutionPlanService(repository)
    loaded_service = service.get_execution_plan(
        execution_approval.execution_approval_id,
        user_id=owner_user_id,
    )
    by_id_service = service.get_execution_plan_by_id(
        execution_plan_id,
        user_id=owner_user_id,
    )

    after_approval = repository.get_simulado_explicit_commit_execution_approval_by_id(
        execution_approval.execution_approval_id,
        user_id=owner_user_id,
    )
    after_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        execution_approval.source_execution_guardrail_id,
        user_id=owner_user_id,
    )
    after_transaction = repository.get_simulado_runtime_mutation_commit_transaction_by_id(
        execution_approval.source_commit_transaction_id,
        user_id=owner_user_id,
    )
    after_explicit_commit = repository.get_simulado_explicit_mutation_commit_by_id(
        execution_approval.source_explicit_commit_id,
        user_id=owner_user_id,
    )
    after_shell = repository.get_simulado_controlled_mutation_commit_shell_by_id(
        execution_approval.source_commit_shell_id,
        user_id=owner_user_id,
    )
    after_mutation_transaction = repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        execution_approval.source_mutation_transaction_id,
        user_id=owner_user_id,
    )
    after_explicit_apply = repository.get_simulado_explicit_runtime_apply_by_id(
        execution_approval.source_explicit_apply_id,
        user_id=owner_user_id,
    )
    after_apply_shell = repository.get_simulado_controlled_apply_shell_by_id(
        execution_approval.source_apply_shell_id,
        user_id=owner_user_id,
    )
    after_application = repository.get_simulado_runtime_progress_application_by_id(
        execution_approval.source_application_id,
        user_id=owner_user_id,
    )
    after_progress = repository.load_progress(user_id=owner_user_id)

    assert missing.status_code == 404
    assert build.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert loaded.json() == by_id.json()
    assert loaded_service is not None
    assert by_id_service is not None
    assert loaded.json()["source_execution_approval_id"] == execution_approval.execution_approval_id
    assert loaded.json()["execution_allowed_now"] is False
    assert loaded.json()["commit_execution_allowed"] is False
    assert loaded.json()["commit_executed"] is False
    assert loaded.json()["mutation_committed"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False

    assert anonymous.post(
        f"/api/simulado-explicit-execution-approval/{execution_approval.execution_approval_id}/execution-plan/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-explicit-execution-approval/{execution_approval.execution_approval_id}/execution-plan"
    ).status_code == 401
    assert anonymous.get(f"/api/simulado-execution-plan/{execution_plan_id}").status_code == 401
    assert other.post(
        f"/api/simulado-explicit-execution-approval/{execution_approval.execution_approval_id}/execution-plan/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-explicit-execution-approval/{execution_approval.execution_approval_id}/execution-plan"
    ).status_code == 404
    assert other.get(f"/api/simulado-execution-plan/{execution_plan_id}").status_code == 404

    assert before_approval is not None
    assert before_guardrail is not None
    assert before_transaction is not None
    assert before_explicit_commit is not None
    assert before_shell is not None
    assert before_mutation_transaction is not None
    assert before_explicit_apply is not None
    assert before_apply_shell is not None
    assert before_application is not None
    assert after_approval is not None
    assert after_guardrail is not None
    assert after_transaction is not None
    assert after_explicit_commit is not None
    assert after_shell is not None
    assert after_mutation_transaction is not None
    assert after_explicit_apply is not None
    assert after_apply_shell is not None
    assert after_application is not None
    assert before_approval.model_dump(mode="json") == after_approval.model_dump(mode="json")
    assert before_guardrail.model_dump(mode="json") == after_guardrail.model_dump(mode="json")
    assert before_transaction.model_dump(mode="json") == after_transaction.model_dump(mode="json")
    assert before_explicit_commit.model_dump(mode="json") == after_explicit_commit.model_dump(mode="json")
    assert before_shell.model_dump(mode="json") == after_shell.model_dump(mode="json")
    assert (
        before_mutation_transaction.model_dump(mode="json")
        == after_mutation_transaction.model_dump(mode="json")
    )
    assert before_explicit_apply.model_dump(mode="json") == after_explicit_apply.model_dump(mode="json")
    assert before_apply_shell.model_dump(mode="json") == after_apply_shell.model_dump(mode="json")
    assert before_application.model_dump(mode="json") == after_application.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
