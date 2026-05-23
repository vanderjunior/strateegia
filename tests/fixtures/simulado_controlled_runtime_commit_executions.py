from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoControlledRuntimeCommitExecution,
    SimuladoRuntimeCommitExecutionPlan,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_runtime_commit_execution import (
    SimuladoControlledRuntimeCommitExecutionService,
)
from tests.fixtures.simulado_runtime_commit_execution_plans import (
    SimuladoRuntimeCommitExecutionPlanFixture,
    api_readonly_fixture as _api_readonly_fixture,
    approval_not_approved_fixture as _approval_not_approved_fixture,
    approved_for_future_review_fixture as _approved_for_future_review_fixture,
    build_runtime_commit_execution_plan,
    execution_disabled_fixture as _execution_disabled_fixture,
    execution_now_not_allowed_fixture as _execution_now_not_allowed_fixture,
    mixed_execution_plan_fixture as _mixed_execution_plan_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    public_answer_key_exposure_forbidden_fixture as _unsafe_source_fixture,
    rollback_checkpoints_incomplete_fixture as _rollback_checkpoints_incomplete_fixture,
    audit_checkpoints_incomplete_fixture as _audit_checkpoints_incomplete_fixture,
)


@dataclass
class SimuladoControlledRuntimeCommitExecutionFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoControlledRuntimeCommitExecutionService
    user_id: str


@dataclass
class SimuladoControlledRuntimeCommitExecutionFixture:
    context: SimuladoControlledRuntimeCommitExecutionFixtureContext
    execution_plan_fixture: SimuladoRuntimeCommitExecutionPlanFixture | None
    execution_plan: SimuladoRuntimeCommitExecutionPlan | None
    missing_execution_plan_id: str | None = None


def _wrap_fixture(
    execution_plan_fixture: SimuladoRuntimeCommitExecutionPlanFixture,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    execution_plan = build_runtime_commit_execution_plan(execution_plan_fixture)
    assert execution_plan is not None
    return SimuladoControlledRuntimeCommitExecutionFixture(
        context=SimuladoControlledRuntimeCommitExecutionFixtureContext(
            repository=execution_plan_fixture.context.repository,
            service=SimuladoControlledRuntimeCommitExecutionService(
                execution_plan_fixture.context.repository
            ),
            user_id=execution_plan_fixture.context.user_id,
        ),
        execution_plan_fixture=execution_plan_fixture,
        execution_plan=execution_plan,
    )


def _persist_execution_plan(
    fixture: SimuladoControlledRuntimeCommitExecutionFixture,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    execution_plan = fixture.execution_plan
    assert execution_plan is not None
    fixture.context.repository.save_simulado_runtime_commit_execution_plan(
        execution_plan,
        user_id=fixture.context.user_id,
    )
    return fixture


def _mark_execution_plan_not_ready(
    fixture: SimuladoControlledRuntimeCommitExecutionFixture,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    execution_plan = fixture.execution_plan
    assert execution_plan is not None
    execution_plan.execution_plan_ready_for_future_execution_review = False
    execution_plan.execution_plan_status = "execution_plan_blocked"
    execution_plan.readiness_state = "execution_plan_needs_review"
    return _persist_execution_plan(fixture)


def _mark_phases_not_executable(
    fixture: SimuladoControlledRuntimeCommitExecutionFixture,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    execution_plan = fixture.execution_plan
    assert execution_plan is not None
    for item in execution_plan.planned_execution_phases:
        item.phase_status = "phase_blocked"
        item.execution_allowed = False
        item.executed = False
        if "phase_blocked_by_execution_not_allowed" not in item.blockers:
            item.blockers.append("phase_blocked_by_execution_not_allowed")
    return _persist_execution_plan(fixture)


def _mark_progress_steps_not_executable(
    fixture: SimuladoControlledRuntimeCommitExecutionFixture,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    execution_plan = fixture.execution_plan
    assert execution_plan is not None
    for item in execution_plan.planned_progress_steps:
        item.step_status = "step_blocked"
        item.execution_allowed = False
        item.executed = False
        if "progress_step_blocked_by_execution_not_allowed" not in item.blockers:
            item.blockers.append("progress_step_blocked_by_execution_not_allowed")
    return _persist_execution_plan(fixture)


def _mark_surface_steps_not_executable(
    fixture: SimuladoControlledRuntimeCommitExecutionFixture,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    execution_plan = fixture.execution_plan
    assert execution_plan is not None
    for item in execution_plan.planned_surface_steps:
        item.step_status = "step_blocked"
        item.execution_allowed = False
        item.executed = False
        if "surface_step_blocked_by_execution_not_allowed" not in item.blockers:
            item.blockers.append("surface_step_blocked_by_execution_not_allowed")
    return _persist_execution_plan(fixture)


def build_controlled_runtime_commit_execution(
    fixture: SimuladoControlledRuntimeCommitExecutionFixture,
) -> SimuladoControlledRuntimeCommitExecution | None:
    source_id = fixture.missing_execution_plan_id
    if fixture.execution_plan is not None:
        source_id = fixture.execution_plan.execution_plan_id
    assert source_id is not None
    return fixture.context.service.build_controlled_execution(
        source_execution_plan_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_execution_plan_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    execution_plan_fixture = _approved_for_future_review_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    return SimuladoControlledRuntimeCommitExecutionFixture(
        context=SimuladoControlledRuntimeCommitExecutionFixtureContext(
            repository=execution_plan_fixture.context.repository,
            service=SimuladoControlledRuntimeCommitExecutionService(
                execution_plan_fixture.context.repository
            ),
            user_id=user_id,
        ),
        execution_plan_fixture=None,
        execution_plan=None,
        missing_execution_plan_id="simulado-execution-plan:missing",
    )


def execution_plan_not_ready_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _mark_execution_plan_not_ready(
        _wrap_fixture(
            _approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def execution_allowed_now_false_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _wrap_fixture(
        _execution_now_not_allowed_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def phases_not_executable_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _mark_phases_not_executable(
        _wrap_fixture(
            _approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def progress_steps_not_executable_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _mark_progress_steps_not_executable(
        _wrap_fixture(
            _approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def surface_steps_not_executable_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _mark_surface_steps_not_executable(
        _wrap_fixture(
            _approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def rollback_verification_failed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _wrap_fixture(
        _rollback_checkpoints_incomplete_fixture(
            tmp_path,
            user_id=user_id,
            repository=repository,
        )
    )


def audit_verification_failed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _wrap_fixture(
        _audit_checkpoints_incomplete_fixture(
            tmp_path,
            user_id=user_id,
            repository=repository,
        )
    )


def execution_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _wrap_fixture(
        _execution_disabled_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def public_answer_key_exposure_forbidden_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _wrap_fixture(
        _unsafe_source_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def dry_run_execution_summary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return execution_allowed_now_false_fixture(tmp_path, user_id=user_id, repository=repository)


def phase_execution_records_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return execution_allowed_now_false_fixture(tmp_path, user_id=user_id, repository=repository)


def progress_step_execution_records_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return execution_allowed_now_false_fixture(tmp_path, user_id=user_id, repository=repository)


def surface_step_execution_records_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return execution_allowed_now_false_fixture(tmp_path, user_id=user_id, repository=repository)


def rollback_verification_records_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return rollback_verification_failed_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_verification_records_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return audit_verification_failed_fixture(tmp_path, user_id=user_id, repository=repository)


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return execution_allowed_now_false_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_application_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return execution_allowed_now_false_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _wrap_fixture(
        _no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return execution_allowed_now_false_fixture(tmp_path, user_id=user_id, repository=repository)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _wrap_fixture(
        _api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def user_scope_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)


def mixed_controlled_execution_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _wrap_fixture(
        _mixed_execution_plan_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def execution_plan_not_approved_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledRuntimeCommitExecutionFixture:
    return _wrap_fixture(
        _approval_not_approved_fixture(tmp_path, user_id=user_id, repository=repository)
    )
