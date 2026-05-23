import json

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_runtime_commit_execution import (
    SimuladoControlledRuntimeCommitExecutionService,
)
from tests.fixtures.simulado_controlled_runtime_commit_executions import (
    api_readonly_fixture,
    audit_verification_failed_fixture,
    audit_verification_records_shape_fixture,
    build_controlled_runtime_commit_execution,
    dry_run_audit_trail_fixture,
    dry_run_summary_shape_fixture,
    execution_allowed_now_false_fixture,
    execution_disabled_fixture,
    execution_mode_status_fixture,
    execution_plan_not_ready_fixture,
    idempotency_fixture,
    missing_execution_plan_fixture,
    mixed_controlled_execution_fixture,
    no_commit_execution_fixture,
    no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture,
    no_runtime_mutation_fixture,
    phase_execution_records_shape_fixture,
    phases_not_executable_fixture,
    progress_step_execution_records_shape_fixture,
    progress_steps_not_executable_fixture,
    public_answer_key_exposure_forbidden_fixture,
    rollback_verification_failed_fixture,
    rollback_verification_records_shape_fixture,
    surface_step_execution_records_shape_fixture,
    surface_steps_not_executable_fixture,
    user_scope_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


FORBIDDEN_CONTROLLED_EXECUTION_KEYS = {
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

ALLOWED_AUDIT_EVENTS = {
    "controlled_execution_created",
    "execution_blocked",
    "no_commit_execution",
    "no_mutation_commit",
    "no_runtime_application",
    "no_progress_mutation",
    "no_final_pedagogical_update_event",
}


def _assert_no_runtime_mutation_flags(result) -> None:
    assert result.controlled_execution_created is True
    assert result.execution_mode in {
        "controlled_execution_dry_run",
        "execution_preview_only",
    }
    assert result.execution_status != "executed"
    assert result.execution_started is False
    assert result.execution_completed is False
    assert result.execution_succeeded is False
    assert result.execution_failed is False
    assert result.execution_allowed_now is False
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
    assert result.final_pedagogical_update_event_created is False
    assert result.answer_key_publicly_exposed is False
    assert result.gabarito_publicly_exposed is False


def _assert_no_leakage(result) -> None:
    dumped_payload = result.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)
    for key in FORBIDDEN_CONTROLLED_EXECUTION_KEYS:
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


def _prepare_execution_plan(repository: JsonStudyRepository, tmp_path, user_id: str):
    fixture = user_scope_fixture(tmp_path, user_id=user_id, repository=repository)
    execution_plan = fixture.execution_plan
    assert execution_plan is not None
    return execution_plan


def test_controlled_runtime_commit_execution_stabilization_fixtures_are_deterministic_and_json_safe(
    tmp_path,
):
    missing = missing_execution_plan_fixture(tmp_path / "missing")
    not_ready = execution_plan_not_ready_fixture(tmp_path / "not-ready")
    mode_status = execution_mode_status_fixture(tmp_path / "mode-status")
    mixed = mixed_controlled_execution_fixture(tmp_path / "mixed")

    assert missing.missing_execution_plan_id == "simulado-execution-plan:missing"
    assert not_ready.execution_plan is not None
    assert mode_status.execution_plan is not None
    assert mixed.execution_plan is not None
    assert json.dumps({"fixture": "controlled-runtime-commit-execution"}, ensure_ascii=True)


def test_controlled_runtime_commit_execution_stabilization_covers_source_scenarios_and_blockers(
    tmp_path,
):
    missing = build_controlled_runtime_commit_execution(
        missing_execution_plan_fixture(tmp_path / "missing")
    )
    not_ready = build_controlled_runtime_commit_execution(
        execution_plan_not_ready_fixture(tmp_path / "not-ready")
    )
    execution_now = build_controlled_runtime_commit_execution(
        execution_allowed_now_false_fixture(tmp_path / "execution-now")
    )
    phases = build_controlled_runtime_commit_execution(
        phases_not_executable_fixture(tmp_path / "phases")
    )
    progress = build_controlled_runtime_commit_execution(
        progress_steps_not_executable_fixture(tmp_path / "progress")
    )
    surface = build_controlled_runtime_commit_execution(
        surface_steps_not_executable_fixture(tmp_path / "surface")
    )
    rollback = build_controlled_runtime_commit_execution(
        rollback_verification_failed_fixture(tmp_path / "rollback")
    )
    audit = build_controlled_runtime_commit_execution(
        audit_verification_failed_fixture(tmp_path / "audit")
    )
    disabled = build_controlled_runtime_commit_execution(
        execution_disabled_fixture(tmp_path / "disabled")
    )
    unsafe = build_controlled_runtime_commit_execution(
        public_answer_key_exposure_forbidden_fixture(tmp_path / "unsafe")
    )

    assert missing is None

    assert not_ready is not None
    assert not_ready.readiness_state == "blocked_by_execution_plan_not_ready"
    _assert_no_runtime_mutation_flags(not_ready)

    assert execution_now is not None
    assert execution_now.readiness_state == "blocked_by_execution_allowed_now_false"
    _assert_no_runtime_mutation_flags(execution_now)

    assert phases is not None
    assert phases.readiness_state == "blocked_by_phases_not_executable"
    assert any(item.blocked for item in phases.phase_execution_records)
    _assert_no_runtime_mutation_flags(phases)

    assert progress is not None
    assert progress.readiness_state == "blocked_by_progress_steps_not_executable"
    assert any(item.blocked for item in progress.progress_step_execution_records)
    _assert_no_runtime_mutation_flags(progress)

    assert surface is not None
    assert surface.readiness_state == "blocked_by_surface_steps_not_executable"
    assert any(item.blocked for item in surface.surface_step_execution_records)
    _assert_no_runtime_mutation_flags(surface)

    assert rollback is not None
    assert rollback.readiness_state == "blocked_by_rollback_verification_failed"
    assert any(item.blocked for item in rollback.rollback_verification_records)
    _assert_no_runtime_mutation_flags(rollback)

    assert audit is not None
    assert audit.readiness_state == "blocked_by_audit_verification_failed"
    assert any(item.blocked for item in audit.audit_verification_records)
    _assert_no_runtime_mutation_flags(audit)

    assert disabled is not None
    assert disabled.readiness_state == "blocked_by_execution_disabled"
    _assert_no_runtime_mutation_flags(disabled)

    assert unsafe is not None
    assert unsafe.readiness_state == "blocked_by_public_answer_key_exposure_forbidden"
    _assert_no_runtime_mutation_flags(unsafe)


def test_controlled_runtime_commit_execution_stabilization_covers_dry_run_records_and_audit_trail(
    tmp_path,
):
    summary = build_controlled_runtime_commit_execution(
        dry_run_summary_shape_fixture(tmp_path / "summary")
    )
    phases = build_controlled_runtime_commit_execution(
        phase_execution_records_shape_fixture(tmp_path / "phases")
    )
    progress = build_controlled_runtime_commit_execution(
        progress_step_execution_records_shape_fixture(tmp_path / "progress")
    )
    surface = build_controlled_runtime_commit_execution(
        surface_step_execution_records_shape_fixture(tmp_path / "surface")
    )
    rollback = build_controlled_runtime_commit_execution(
        rollback_verification_records_shape_fixture(tmp_path / "rollback")
    )
    audit = build_controlled_runtime_commit_execution(
        audit_verification_records_shape_fixture(tmp_path / "audit")
    )
    audit_trail = build_controlled_runtime_commit_execution(
        dry_run_audit_trail_fixture(tmp_path / "audit-trail")
    )
    mode_status = build_controlled_runtime_commit_execution(
        execution_mode_status_fixture(tmp_path / "mode-status")
    )

    assert summary is not None
    assert summary.execution_summary.source_plan_present is True
    assert summary.execution_summary.real_execution_performed is False
    assert summary.execution_summary.mutation_commit_performed is False
    assert summary.execution_summary.runtime_application_performed is False
    _assert_no_runtime_mutation_flags(summary)

    assert phases is not None
    assert [item.phase_type for item in phases.phase_execution_records] == [
        "preflight_validation",
        "rollback_checkpoint_validation",
        "progress_step_review",
        "surface_step_review",
        "audit_checkpoint_review",
        "final_execution_review",
    ]
    for index, item in enumerate(phases.phase_execution_records, start=1):
        assert item.phase_type in ALLOWED_PHASE_TYPES
        assert item.phase_order == index
        assert item.evaluated is True
        assert item.execution_allowed is False
        assert item.executed is False

    assert progress is not None
    for item in progress.progress_step_execution_records:
        assert item.target_type in ALLOWED_TARGET_TYPES
        assert item.delta_kind in ALLOWED_DELTA_KINDS
        assert item.evaluated is True
        assert item.execution_allowed is False
        assert item.executed is False

    assert surface is not None
    for item in surface.surface_step_execution_records:
        assert item.surface_type in ALLOWED_SURFACE_TYPES
        assert item.update_kind in ALLOWED_UPDATE_KINDS
        assert item.evaluated is True
        assert item.execution_allowed is False
        assert item.executed is False

    assert rollback is not None
    for item in rollback.rollback_verification_records:
        assert item.evaluated is True
        assert item.execution_allowed is False
        assert item.executed is False

    assert audit is not None
    for item in audit.audit_verification_records:
        assert item.evaluated is True
        assert item.execution_allowed is False
        assert item.executed is False

    assert audit_trail is not None
    assert ALLOWED_AUDIT_EVENTS.issubset({item.event_type for item in audit_trail.audit_trail})

    assert mode_status is not None
    assert mode_status.execution_mode in {
        "controlled_execution_dry_run",
        "execution_preview_only",
    }
    assert mode_status.execution_status != "executed"
    _assert_no_runtime_mutation_flags(mode_status)


def test_controlled_runtime_commit_execution_stabilization_preserves_no_leakage_and_runtime_state(
    tmp_path,
):
    safe = build_controlled_runtime_commit_execution(
        no_public_key_gabarito_safety_fixture(tmp_path / "safe")
    )
    no_commit = build_controlled_runtime_commit_execution(
        no_commit_execution_fixture(tmp_path / "no-commit")
    )
    no_runtime_application = build_controlled_runtime_commit_execution(
        no_runtime_application_fixture(tmp_path / "no-runtime-application")
    )
    no_runtime_mutation = build_controlled_runtime_commit_execution(
        no_runtime_mutation_fixture(tmp_path / "no-runtime-mutation")
    )
    mixed = build_controlled_runtime_commit_execution(
        mixed_controlled_execution_fixture(tmp_path / "mixed")
    )

    assert safe is not None
    _assert_no_leakage(safe)
    _assert_no_runtime_mutation_flags(safe)

    assert no_commit is not None
    assert no_commit.no_commit_execution is True
    assert no_commit.no_commit_execution_event_created is True
    _assert_no_runtime_mutation_flags(no_commit)

    assert no_runtime_application is not None
    assert no_runtime_application.runtime_application_enabled is False
    assert no_runtime_application.runtime_application_applied is False
    _assert_no_runtime_mutation_flags(no_runtime_application)

    assert no_runtime_mutation is not None
    _assert_no_runtime_mutation_flags(no_runtime_mutation)

    assert mixed is not None
    assert mixed.blockers
    assert mixed.warnings
    _assert_no_runtime_mutation_flags(mixed)


def test_controlled_runtime_commit_execution_stabilization_persistence_and_read_only_behavior(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = idempotency_fixture(tmp_path / "idempotent", repository=repository)
    service = SimuladoControlledRuntimeCommitExecutionService(repository)
    source_execution_plan = fixture.execution_plan
    assert source_execution_plan is not None

    first = build_controlled_runtime_commit_execution(fixture)
    second = build_controlled_runtime_commit_execution(fixture)
    assert first is not None
    assert second is not None

    by_source = repository.get_simulado_controlled_runtime_commit_execution(
        source_execution_plan.execution_plan_id,
        user_id=fixture.context.user_id,
    )
    by_id = repository.get_simulado_controlled_runtime_commit_execution_by_id(
        first.controlled_execution_id,
        user_id=fixture.context.user_id,
    )
    listed = repository.list_user_simulado_controlled_runtime_commit_executions(
        user_id=fixture.context.user_id
    )

    before_plan = repository.get_simulado_runtime_commit_execution_plan_by_id(
        source_execution_plan.execution_plan_id,
        user_id=fixture.context.user_id,
    )
    loaded = service.get_controlled_execution(
        source_execution_plan.execution_plan_id,
        user_id=fixture.context.user_id,
    )
    loaded_by_id = service.get_controlled_execution_by_id(
        first.controlled_execution_id,
        user_id=fixture.context.user_id,
    )
    after_plan = repository.get_simulado_runtime_commit_execution_plan_by_id(
        source_execution_plan.execution_plan_id,
        user_id=fixture.context.user_id,
    )

    assert by_source is not None
    assert by_id is not None
    assert loaded is not None
    assert loaded_by_id is not None
    assert before_plan is not None
    assert after_plan is not None
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.model_dump(mode="json") == by_source.model_dump(mode="json")
    assert first.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert first.model_dump(mode="json") == loaded.model_dump(mode="json")
    assert first.model_dump(mode="json") == loaded_by_id.model_dump(mode="json")
    assert before_plan.model_dump(mode="json") == after_plan.model_dump(mode="json")
    assert len(listed) == 1


def test_controlled_runtime_commit_execution_stabilization_api_owner_scope_and_read_only(
    tmp_path,
):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    owner = TestClient(app)
    other = TestClient(app)
    anonymous = TestClient(app)

    owner_user_id = _register_and_login(owner, "owner")
    _register_and_login(other, "other")
    execution_plan = _prepare_execution_plan(repository, tmp_path / "owner", owner_user_id)

    missing = owner.get(
        f"/api/simulado-execution-plan/{execution_plan.execution_plan_id}/controlled-execution"
    )
    before_plan = repository.get_simulado_runtime_commit_execution_plan_by_id(
        execution_plan.execution_plan_id,
        user_id=owner_user_id,
    )
    built = owner.post(
        f"/api/simulado-execution-plan/{execution_plan.execution_plan_id}/controlled-execution/build"
    )
    loaded = owner.get(
        f"/api/simulado-execution-plan/{execution_plan.execution_plan_id}/controlled-execution"
    )
    controlled_execution_id = built.json()["controlled_execution_id"]
    by_id = owner.get(f"/api/simulado-controlled-execution/{controlled_execution_id}")
    after_plan = repository.get_simulado_runtime_commit_execution_plan_by_id(
        execution_plan.execution_plan_id,
        user_id=owner_user_id,
    )

    assert missing.status_code == 404
    assert built.status_code == 200
    assert loaded.status_code == 200
    assert by_id.status_code == 200
    assert before_plan is not None
    assert after_plan is not None
    assert before_plan.model_dump(mode="json") == after_plan.model_dump(mode="json")
    assert loaded.json()["source_execution_plan_id"] == execution_plan.execution_plan_id
    assert loaded.json()["execution_started"] is False
    assert loaded.json()["execution_completed"] is False
    assert loaded.json()["commit_executed"] is False
    assert loaded.json()["mutation_committed"] is False
    assert loaded.json()["answer_key_publicly_exposed"] is False
    assert loaded.json()["gabarito_publicly_exposed"] is False

    assert anonymous.post(
        f"/api/simulado-execution-plan/{execution_plan.execution_plan_id}/controlled-execution/build"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-execution-plan/{execution_plan.execution_plan_id}/controlled-execution"
    ).status_code == 401
    assert anonymous.get(
        f"/api/simulado-controlled-execution/{controlled_execution_id}"
    ).status_code == 401

    assert other.post(
        f"/api/simulado-execution-plan/{execution_plan.execution_plan_id}/controlled-execution/build"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-execution-plan/{execution_plan.execution_plan_id}/controlled-execution"
    ).status_code == 404
    assert other.get(
        f"/api/simulado-controlled-execution/{controlled_execution_id}"
    ).status_code == 404
