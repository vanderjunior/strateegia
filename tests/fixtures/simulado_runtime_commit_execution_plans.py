from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoExplicitRuntimeCommitExecutionApproval,
    SimuladoRuntimeCommitExecutionPlan,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_commit_execution_plan import (
    SimuladoRuntimeCommitExecutionPlanService,
)
from tests.fixtures.simulado_explicit_commit_execution_approvals import (
    SimuladoExplicitCommitExecutionApprovalFixture,
    api_readonly_fixture as _api_readonly_fixture,
    approve_all_payload,
    approve_payload,
    approve_with_all_confirmations_fixture as _approve_with_all_confirmations_fixture,
    approve_without_confirmations_fixture as _approve_without_confirmations_fixture,
    block_execution_fixture as _block_execution_fixture,
    block_payload,
    build_explicit_commit_execution_approval,
    deny_execution_fixture as _deny_execution_fixture,
    deny_payload,
    explicit_execution_approval_source_fixture as _explicit_execution_approval_source_fixture,
    mark_not_reviewed_fixture as _mark_not_reviewed_fixture,
    mark_not_reviewed_payload,
    mixed_approval_fixture as _mixed_approval_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    request_revision_fixture as _request_revision_fixture,
    request_revision_payload,
    unsafe_source_fixture as _unsafe_source_fixture,
)


@dataclass
class SimuladoRuntimeCommitExecutionPlanFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoRuntimeCommitExecutionPlanService
    user_id: str


@dataclass
class SimuladoRuntimeCommitExecutionPlanFixture:
    context: SimuladoRuntimeCommitExecutionPlanFixtureContext
    execution_approval_fixture: SimuladoExplicitCommitExecutionApprovalFixture | None
    execution_approval: SimuladoExplicitRuntimeCommitExecutionApproval | None
    missing_execution_approval_id: str | None = None


def _wrap_fixture(
    execution_approval_fixture: SimuladoExplicitCommitExecutionApprovalFixture,
    *,
    decision_payload: dict[str, object] | None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    execution_approval = build_explicit_commit_execution_approval(
        execution_approval_fixture,
        decision_payload=decision_payload,
    )
    assert execution_approval is not None
    return SimuladoRuntimeCommitExecutionPlanFixture(
        context=SimuladoRuntimeCommitExecutionPlanFixtureContext(
            repository=execution_approval_fixture.context.repository,
            service=SimuladoRuntimeCommitExecutionPlanService(
                execution_approval_fixture.context.repository
            ),
            user_id=execution_approval_fixture.context.user_id,
        ),
        execution_approval_fixture=execution_approval_fixture,
        execution_approval=execution_approval,
    )


def _persist_execution_approval(
    fixture: SimuladoRuntimeCommitExecutionPlanFixture,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    execution_approval = fixture.execution_approval
    assert execution_approval is not None
    fixture.context.repository.save_simulado_explicit_commit_execution_approval(
        execution_approval,
        user_id=fixture.context.user_id,
    )
    return fixture


def _update_progress_approvals(
    fixture: SimuladoRuntimeCommitExecutionPlanFixture,
    *,
    future_review_ready: bool,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    execution_approval = fixture.execution_approval
    assert execution_approval is not None
    for item in execution_approval.progress_execution_approvals:
        item.explicitly_approved = future_review_ready
        item.approved_for_future_commit_execution_review = future_review_ready
        item.approved_for_execution_now = False
        item.executed = False
        item.source_execution_allowed = future_review_ready
        item.source_executed = False
        item.approval_state = (
            "progress_execution_approved_for_future_commit_execution_review"
            if future_review_ready
            else "progress_execution_blocked"
        )
        if future_review_ready:
            item.blockers = [
                blocker for blocker in item.blockers if blocker != "progress_execution_blocked_by_source_check"
            ]
        else:
            if "progress_execution_blocked_by_source_check" not in item.blockers:
                item.blockers.append("progress_execution_blocked_by_source_check")
    return _persist_execution_approval(fixture)


def _update_surface_approvals(
    fixture: SimuladoRuntimeCommitExecutionPlanFixture,
    *,
    future_review_ready: bool,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    execution_approval = fixture.execution_approval
    assert execution_approval is not None
    for item in execution_approval.surface_execution_approvals:
        item.explicitly_approved = future_review_ready
        item.approved_for_future_commit_execution_review = future_review_ready
        item.approved_for_execution_now = False
        item.executed = False
        item.source_execution_allowed = future_review_ready
        item.source_executed = False
        item.approval_state = (
            "surface_execution_approved_for_future_commit_execution_review"
            if future_review_ready
            else "surface_execution_blocked"
        )
        if future_review_ready:
            item.blockers = [
                blocker for blocker in item.blockers if blocker != "surface_execution_blocked_by_source_check"
            ]
        else:
            if "surface_execution_blocked_by_source_check" not in item.blockers:
                item.blockers.append("surface_execution_blocked_by_source_check")
    return _persist_execution_approval(fixture)


def _mark_execution_disabled(
    fixture: SimuladoRuntimeCommitExecutionPlanFixture,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    execution_approval = fixture.execution_approval
    assert execution_approval is not None
    execution_approval.metadata["execution_disabled"] = True
    return _persist_execution_approval(fixture)


def build_runtime_commit_execution_plan(
    fixture: SimuladoRuntimeCommitExecutionPlanFixture,
) -> SimuladoRuntimeCommitExecutionPlan | None:
    source_id = fixture.missing_execution_approval_id
    if fixture.execution_approval is not None:
        source_id = fixture.execution_approval.execution_approval_id
    assert source_id is not None
    return fixture.context.service.build_execution_plan(
        source_execution_approval_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_explicit_execution_approval_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    execution_approval_fixture = _explicit_execution_approval_source_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    return SimuladoRuntimeCommitExecutionPlanFixture(
        context=SimuladoRuntimeCommitExecutionPlanFixtureContext(
            repository=execution_approval_fixture.context.repository,
            service=SimuladoRuntimeCommitExecutionPlanService(
                execution_approval_fixture.context.repository
            ),
            user_id=user_id,
        ),
        execution_approval_fixture=None,
        execution_approval=None,
        missing_execution_approval_id="simulado-explicit-execution-approval:missing",
    )


def execution_plan_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _wrap_fixture(
        _approve_with_all_confirmations_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )


def approval_not_approved_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _wrap_fixture(
        _deny_execution_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=deny_payload(),
    )


def approved_for_future_review_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return execution_plan_source_fixture(tmp_path, user_id=user_id, repository=repository)


def confirmations_incomplete_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _wrap_fixture(
        _approve_without_confirmations_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_payload(),
    )


def progress_approvals_not_ready_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _update_progress_approvals(
        approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository),
        future_review_ready=False,
    )


def surface_approvals_not_ready_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _update_surface_approvals(
        approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository),
        future_review_ready=False,
    )


def execution_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _mark_execution_disabled(
        approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def unsafe_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _wrap_fixture(
        _unsafe_source_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )


def plan_summary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def planned_progress_steps_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def planned_surface_steps_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def rollback_checkpoint_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_checkpoint_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _wrap_fixture(
        _no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )


def payload_idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _wrap_fixture(
        _api_readonly_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )


def user_scope_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)


def mixed_execution_plan_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _wrap_fixture(
        _mixed_approval_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_payload(),
    )


def request_revision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _wrap_fixture(
        _request_revision_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=request_revision_payload(),
    )


def block_execution_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _wrap_fixture(
        _block_execution_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=block_payload(),
    )


def mark_not_reviewed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeCommitExecutionPlanFixture:
    return _wrap_fixture(
        _mark_not_reviewed_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=mark_not_reviewed_payload(),
    )
