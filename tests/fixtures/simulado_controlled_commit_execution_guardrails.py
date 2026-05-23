from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoControlledRuntimeCommitExecutionGuardrail,
    SimuladoRuntimeMutationCommitTransaction,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_commit_execution_guardrail import (
    SimuladoControlledRuntimeCommitExecutionGuardrailService,
)
from tests.fixtures.simulado_runtime_mutation_commit_transactions import (
    SimuladoRuntimeMutationCommitTransactionFixture,
    api_readonly_fixture as _api_readonly_fixture,
    approved_for_future_only_fixture as _approved_for_future_only_fixture,
    build_runtime_mutation_commit_transaction,
    explicit_commit_not_approved_fixture as _explicit_commit_not_approved_fixture,
    mixed_commit_transaction_fixture as _mixed_commit_transaction_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    public_answer_key_exposure_forbidden_fixture as _unsafe_source_fixture,
)


@dataclass
class SimuladoControlledCommitExecutionGuardrailFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoControlledRuntimeCommitExecutionGuardrailService
    user_id: str


@dataclass
class SimuladoControlledCommitExecutionGuardrailFixture:
    context: SimuladoControlledCommitExecutionGuardrailFixtureContext
    commit_transaction_fixture: SimuladoRuntimeMutationCommitTransactionFixture | None
    commit_transaction: SimuladoRuntimeMutationCommitTransaction | None
    missing_commit_transaction_id: str | None = None


def _wrap_fixture(
    commit_transaction_fixture: SimuladoRuntimeMutationCommitTransactionFixture,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    commit_transaction = build_runtime_mutation_commit_transaction(commit_transaction_fixture)
    assert commit_transaction is not None
    return SimuladoControlledCommitExecutionGuardrailFixture(
        context=SimuladoControlledCommitExecutionGuardrailFixtureContext(
            repository=commit_transaction_fixture.context.repository,
            service=SimuladoControlledRuntimeCommitExecutionGuardrailService(
                commit_transaction_fixture.context.repository
            ),
            user_id=commit_transaction_fixture.context.user_id,
        ),
        commit_transaction_fixture=commit_transaction_fixture,
        commit_transaction=commit_transaction,
    )


def _persist_commit_transaction(
    fixture: SimuladoControlledCommitExecutionGuardrailFixture,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    commit_transaction = fixture.commit_transaction
    assert commit_transaction is not None
    fixture.context.repository.save_simulado_runtime_mutation_commit_transaction(
        commit_transaction,
        user_id=fixture.context.user_id,
    )
    return fixture


def build_controlled_commit_execution_guardrail(
    fixture: SimuladoControlledCommitExecutionGuardrailFixture,
) -> SimuladoControlledRuntimeCommitExecutionGuardrail | None:
    source_id = fixture.missing_commit_transaction_id
    if fixture.commit_transaction is not None:
        source_id = fixture.commit_transaction.commit_transaction_id
    assert source_id is not None
    return fixture.context.service.build_execution_guardrail(
        source_commit_transaction_id=source_id,
        user_id=fixture.context.user_id,
    )


def _make_execution_review_candidate(
    fixture: SimuladoControlledCommitExecutionGuardrailFixture,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    commit_transaction = fixture.commit_transaction
    assert commit_transaction is not None
    commit_transaction.commit_transaction_mode = "dry_run_commit_transaction"
    commit_transaction.commit_transaction_status = "commit_ready_for_future_execution_review"
    commit_transaction.commit_transaction_valid_for_execution = True
    commit_transaction.commit_execution_ready = True
    commit_transaction.rollback_execution_plan.rollback_available = True
    commit_transaction.rollback_execution_plan.rollback_verified = True
    commit_transaction.rollback_execution_plan.rollback_execution_ready = True
    for item in commit_transaction.planned_progress_commits:
        item.execution_allowed = True
        item.blockers = [
            blocker for blocker in item.blockers if blocker != "planned_commit_blocked_by_execution_not_allowed"
        ]
    for item in commit_transaction.planned_surface_commits:
        item.execution_allowed = True
        item.blockers = [
            blocker for blocker in item.blockers if blocker != "surface_commit_blocked_by_execution_not_allowed"
        ]
    metadata = commit_transaction.metadata
    metadata["execution_guardrail_audit_confirmation_present"] = True
    metadata["execution_guardrail_runtime_surface_confirmation_present"] = True
    metadata["execution_guardrail_public_answer_key_absence_confirmation_present"] = True
    metadata["execution_guardrail_human_review_confirmation_present"] = True
    metadata["execution_guardrail_rollback_execution_confirmation_present"] = True
    return _persist_commit_transaction(fixture)


def missing_commit_transaction_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    transaction_fixture = _approved_for_future_only_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoControlledCommitExecutionGuardrailFixture(
        context=SimuladoControlledCommitExecutionGuardrailFixtureContext(
            repository=transaction_fixture.context.repository,
            service=SimuladoControlledRuntimeCommitExecutionGuardrailService(
                transaction_fixture.context.repository
            ),
            user_id=user_id,
        ),
        commit_transaction_fixture=None,
        commit_transaction=None,
        missing_commit_transaction_id="simulado-commit-transaction:missing",
    )


def transaction_plan_only_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return _wrap_fixture(_approved_for_future_only_fixture(tmp_path, user_id=user_id, repository=repository))


def transaction_not_plan_only_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    fixture = transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)
    commit_transaction = fixture.commit_transaction
    assert commit_transaction is not None
    commit_transaction.commit_transaction_mode = "execution_requested"
    return _persist_commit_transaction(fixture)


def transaction_already_executed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    fixture = transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)
    commit_transaction = fixture.commit_transaction
    assert commit_transaction is not None
    commit_transaction.commit_executed = True
    commit_transaction.commit_transaction_status = "committed"
    return _persist_commit_transaction(fixture)


def commit_transaction_not_valid_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def transaction_not_valid_for_execution_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return commit_transaction_not_valid_fixture(tmp_path, user_id=user_id, repository=repository)


def commit_execution_not_ready_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    fixture = transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)
    commit_transaction = fixture.commit_transaction
    assert commit_transaction is not None
    commit_transaction.commit_transaction_valid_for_execution = True
    commit_transaction.commit_execution_ready = False
    return _persist_commit_transaction(fixture)


def rollback_not_ready_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    fixture = transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)
    commit_transaction = fixture.commit_transaction
    assert commit_transaction is not None
    commit_transaction.commit_transaction_valid_for_execution = True
    commit_transaction.commit_execution_ready = True
    commit_transaction.rollback_execution_plan.rollback_available = False
    commit_transaction.rollback_execution_plan.rollback_verified = False
    commit_transaction.rollback_execution_plan.rollback_execution_ready = False
    return _persist_commit_transaction(fixture)


def planned_progress_commits_not_executable_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    fixture = transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)
    _make_execution_review_candidate(fixture)
    commit_transaction = fixture.commit_transaction
    assert commit_transaction is not None
    for item in commit_transaction.planned_progress_commits:
        item.execution_allowed = False
        if "planned_commit_blocked_by_execution_not_allowed" not in item.blockers:
            item.blockers.append("planned_commit_blocked_by_execution_not_allowed")
    return _persist_commit_transaction(fixture)


def planned_surface_commits_not_executable_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    fixture = transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)
    _make_execution_review_candidate(fixture)
    commit_transaction = fixture.commit_transaction
    assert commit_transaction is not None
    for item in commit_transaction.planned_surface_commits:
        item.execution_allowed = False
        if "surface_commit_blocked_by_execution_not_allowed" not in item.blockers:
            item.blockers.append("surface_commit_blocked_by_execution_not_allowed")
    return _persist_commit_transaction(fixture)


def audit_requirements_unsatisfied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    fixture = transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)
    _make_execution_review_candidate(fixture)
    commit_transaction = fixture.commit_transaction
    assert commit_transaction is not None
    metadata = commit_transaction.metadata
    metadata["execution_guardrail_audit_confirmation_present"] = False
    metadata["execution_guardrail_runtime_surface_confirmation_present"] = False
    metadata["execution_guardrail_public_answer_key_absence_confirmation_present"] = False
    metadata["execution_guardrail_human_review_confirmation_present"] = False
    metadata["execution_guardrail_rollback_execution_confirmation_present"] = False
    return _persist_commit_transaction(fixture)


def final_execution_approval_missing_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    fixture = transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)
    _make_execution_review_candidate(fixture)
    return fixture


def commit_execution_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    fixture = transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)
    _make_execution_review_candidate(fixture)
    commit_transaction = fixture.commit_transaction
    assert commit_transaction is not None
    commit_transaction.metadata["force_commit_execution_disabled"] = True
    return _persist_commit_transaction(fixture)


def public_answer_key_exposure_forbidden_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return _wrap_fixture(_unsafe_source_fixture(tmp_path, user_id=user_id, repository=repository))


def progress_commit_checks_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def progress_commit_execution_checks_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return progress_commit_checks_shape_fixture(tmp_path, user_id=user_id, repository=repository)


def surface_commit_checks_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def surface_commit_execution_checks_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return surface_commit_checks_shape_fixture(tmp_path, user_id=user_id, repository=repository)


def rollback_execution_readiness_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def rollback_readiness_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return rollback_execution_readiness_shape_fixture(tmp_path, user_id=user_id, repository=repository)


def runtime_surface_risk_summary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_requirements_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_trail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def execution_guardrail_mode_status_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def no_commit_execution_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_application_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return _wrap_fixture(_no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository))


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return transaction_plan_only_fixture(tmp_path, user_id=user_id, repository=repository)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return _wrap_fixture(_api_readonly_fixture(tmp_path, user_id=user_id, repository=repository))


def user_scope_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)


def mixed_execution_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledCommitExecutionGuardrailFixture:
    return _wrap_fixture(_mixed_commit_transaction_fixture(tmp_path, user_id=user_id, repository=repository))
