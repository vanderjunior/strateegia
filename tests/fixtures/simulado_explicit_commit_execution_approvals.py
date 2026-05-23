from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoControlledRuntimeCommitExecutionGuardrail,
    SimuladoExplicitRuntimeCommitExecutionApproval,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_explicit_commit_execution_approval import (
    SimuladoExplicitRuntimeCommitExecutionApprovalService,
)
from tests.fixtures.simulado_controlled_commit_execution_guardrails import (
    SimuladoControlledCommitExecutionGuardrailFixture,
    api_readonly_fixture as _api_readonly_fixture,
    build_controlled_commit_execution_guardrail,
    mixed_execution_guardrail_fixture as _mixed_execution_guardrail_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    public_answer_key_exposure_forbidden_fixture as _unsafe_source_fixture,
)


@dataclass
class SimuladoExplicitCommitExecutionApprovalFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoExplicitRuntimeCommitExecutionApprovalService
    user_id: str


@dataclass
class SimuladoExplicitCommitExecutionApprovalFixture:
    context: SimuladoExplicitCommitExecutionApprovalFixtureContext
    execution_guardrail_fixture: SimuladoControlledCommitExecutionGuardrailFixture | None
    execution_guardrail: SimuladoControlledRuntimeCommitExecutionGuardrail | None
    missing_execution_guardrail_id: str | None = None


def approve_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Approved for future controlled commit execution review.",
    final_execution_approval_confirmed: bool = False,
    rollback_execution_confirmed: bool = False,
    audit_confirmed: bool = False,
    runtime_surface_confirmed: bool = False,
    public_answer_key_absence_confirmed: bool = False,
    human_review_confirmed: bool = False,
) -> dict[str, object]:
    return {
        "decision_type": "approve_for_future_commit_execution_review",
        "reviewer_id": reviewer_id,
        "reason": reason,
        "confirmations": {
            "final_execution_approval_confirmed": final_execution_approval_confirmed,
            "rollback_execution_confirmed": rollback_execution_confirmed,
            "audit_confirmed": audit_confirmed,
            "runtime_surface_confirmed": runtime_surface_confirmed,
            "public_answer_key_absence_confirmed": public_answer_key_absence_confirmed,
            "human_review_confirmed": human_review_confirmed,
        },
    }


def deny_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Execution denied pending future review.",
) -> dict[str, object]:
    return {
        "decision_type": "deny_execution",
        "reviewer_id": reviewer_id,
        "reason": reason,
    }


def request_revision_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Revision requested before any future execution review.",
) -> dict[str, object]:
    return {
        "decision_type": "request_revision",
        "reviewer_id": reviewer_id,
        "reason": reason,
    }


def block_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Execution blocked for future review.",
) -> dict[str, object]:
    return {
        "decision_type": "block_execution",
        "reviewer_id": reviewer_id,
        "reason": reason,
    }


def mark_not_reviewed_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Not reviewed yet.",
) -> dict[str, object]:
    return {
        "decision_type": "mark_not_reviewed",
        "reviewer_id": reviewer_id,
        "reason": reason,
    }


def approve_all_payload() -> dict[str, object]:
    return approve_payload(
        final_execution_approval_confirmed=True,
        rollback_execution_confirmed=True,
        audit_confirmed=True,
        runtime_surface_confirmed=True,
        public_answer_key_absence_confirmed=True,
        human_review_confirmed=True,
    )


def _wrap_fixture(
    execution_guardrail_fixture: SimuladoControlledCommitExecutionGuardrailFixture,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    execution_guardrail = build_controlled_commit_execution_guardrail(
        execution_guardrail_fixture
    )
    assert execution_guardrail is not None
    return SimuladoExplicitCommitExecutionApprovalFixture(
        context=SimuladoExplicitCommitExecutionApprovalFixtureContext(
            repository=execution_guardrail_fixture.context.repository,
            service=SimuladoExplicitRuntimeCommitExecutionApprovalService(
                execution_guardrail_fixture.context.repository
            ),
            user_id=execution_guardrail_fixture.context.user_id,
        ),
        execution_guardrail_fixture=execution_guardrail_fixture,
        execution_guardrail=execution_guardrail,
    )


def _persist_execution_guardrail(
    fixture: SimuladoExplicitCommitExecutionApprovalFixture,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    execution_guardrail = fixture.execution_guardrail
    assert execution_guardrail is not None
    fixture.context.repository.save_simulado_controlled_commit_execution_guardrail(
        execution_guardrail,
        user_id=fixture.context.user_id,
    )
    return fixture


def _make_ready_for_future_execution_review(
    fixture: SimuladoExplicitCommitExecutionApprovalFixture,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    execution_guardrail = fixture.execution_guardrail
    assert execution_guardrail is not None
    execution_guardrail.execution_guardrail_status = "ready_for_future_execution_approval_review"
    execution_guardrail.readiness_state = "ready_for_future_execution_approval_review"
    execution_guardrail.readiness_summary.source_commit_transaction_present = True
    execution_guardrail.readiness_summary.source_transaction_plan_only = True
    execution_guardrail.readiness_summary.source_transaction_not_executed = True
    execution_guardrail.readiness_summary.source_commit_transaction_valid_for_execution = False
    execution_guardrail.readiness_summary.source_commit_execution_ready = False
    execution_guardrail.readiness_summary.execution_preconditions_satisfied = False
    execution_guardrail.transaction_safety_assessment.safe_for_future_execution_review = True
    execution_guardrail.rollback_readiness.rollback_required = True
    execution_guardrail.rollback_readiness.rollback_available = True
    execution_guardrail.rollback_readiness.rollback_verified = True
    execution_guardrail.rollback_readiness.rollback_execution_ready = False
    execution_guardrail.rollback_readiness.rollback_ready_for_future_execution_review = True
    for item in execution_guardrail.progress_commit_checks:
        item.source_execution_allowed = True
        item.execution_check_state = "progress_commit_ready_for_future_execution_review"
        item.execution_allowed = False
        item.executed = False
        item.blockers = [
            blocker
            for blocker in item.blockers
            if blocker != "progress_commit_blocked_by_execution_not_allowed"
        ]
    for item in execution_guardrail.surface_commit_checks:
        item.source_execution_allowed = True
        item.execution_check_state = "surface_commit_ready_for_future_execution_review"
        item.execution_allowed = False
        item.executed = False
        item.blockers = [
            blocker
            for blocker in item.blockers
            if blocker != "surface_commit_blocked_by_execution_not_allowed"
        ]
    return _persist_execution_guardrail(fixture)


def build_explicit_commit_execution_approval(
    fixture: SimuladoExplicitCommitExecutionApprovalFixture,
    *,
    decision_payload: dict[str, object] | None = None,
) -> SimuladoExplicitRuntimeCommitExecutionApproval | None:
    source_id = fixture.missing_execution_guardrail_id
    if fixture.execution_guardrail is not None:
        source_id = fixture.execution_guardrail.execution_guardrail_id
    assert source_id is not None
    return fixture.context.service.build_execution_approval(
        source_execution_guardrail_id=source_id,
        decision_payload=decision_payload,
        user_id=fixture.context.user_id,
    )


def missing_execution_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    guardrail_fixture = _no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoExplicitCommitExecutionApprovalFixture(
        context=SimuladoExplicitCommitExecutionApprovalFixtureContext(
            repository=guardrail_fixture.context.repository,
            service=SimuladoExplicitRuntimeCommitExecutionApprovalService(
                guardrail_fixture.context.repository
            ),
            user_id=user_id,
        ),
        execution_guardrail_fixture=None,
        execution_guardrail=None,
        missing_execution_guardrail_id="simulado-commit-execution-guardrail:missing",
    )


def explicit_execution_approval_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return _wrap_fixture(_no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository))


def no_decision_payload_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return explicit_execution_approval_source_fixture(tmp_path, user_id=user_id, repository=repository)


def approve_without_confirmations_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    fixture = explicit_execution_approval_source_fixture(tmp_path, user_id=user_id, repository=repository)
    return _make_ready_for_future_execution_review(fixture)


def approve_with_all_confirmations_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    fixture = explicit_execution_approval_source_fixture(tmp_path, user_id=user_id, repository=repository)
    return _make_ready_for_future_execution_review(fixture)


def deny_execution_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return explicit_execution_approval_source_fixture(tmp_path, user_id=user_id, repository=repository)


def request_revision_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return explicit_execution_approval_source_fixture(tmp_path, user_id=user_id, repository=repository)


def block_execution_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return explicit_execution_approval_source_fixture(tmp_path, user_id=user_id, repository=repository)


def mark_not_reviewed_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return explicit_execution_approval_source_fixture(tmp_path, user_id=user_id, repository=repository)


def confirmation_summary_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return approve_without_confirmations_fixture(tmp_path, user_id=user_id, repository=repository)


def progress_execution_approvals_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return approve_with_all_confirmations_fixture(tmp_path, user_id=user_id, repository=repository)


def surface_execution_approvals_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return approve_with_all_confirmations_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_trail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return approve_without_confirmations_fixture(tmp_path, user_id=user_id, repository=repository)


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return explicit_execution_approval_source_fixture(tmp_path, user_id=user_id, repository=repository)


def unsafe_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return _wrap_fixture(_unsafe_source_fixture(tmp_path, user_id=user_id, repository=repository))


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return _wrap_fixture(_no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository))


def payload_idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return approve_with_all_confirmations_fixture(tmp_path, user_id=user_id, repository=repository)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return _wrap_fixture(_api_readonly_fixture(tmp_path, user_id=user_id, repository=repository))


def user_scope_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)


def mixed_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitCommitExecutionApprovalFixture:
    return _wrap_fixture(_mixed_execution_guardrail_fixture(tmp_path, user_id=user_id, repository=repository))
