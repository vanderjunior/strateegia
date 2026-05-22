from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoControlledRuntimeMutationCommitShell,
    SimuladoRuntimeProgressMutationTransaction,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_mutation_commit import (
    SimuladoControlledRuntimeMutationCommitService,
)
from tests.fixtures.simulado_runtime_progress_mutations import (
    SimuladoRuntimeProgressMutationFixture,
    api_readonly_fixture as _api_readonly_fixture,
    approved_for_future_only_fixture as _approved_for_future_only_fixture,
    build_runtime_progress_mutation_transaction,
    explicit_apply_not_approved_fixture as _explicit_apply_not_approved_fixture,
    mixed_mutation_fixture as _mixed_mutation_fixture,
    missing_explicit_apply_fixture as _missing_explicit_apply_fixture,
    runtime_mutation_disabled_fixture as _runtime_mutation_disabled_fixture,
    unsafe_source_fixture as _unsafe_source_fixture,
)


@dataclass
class SimuladoControlledMutationCommitShellFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoControlledRuntimeMutationCommitService
    user_id: str


@dataclass
class SimuladoControlledMutationCommitShellFixture:
    context: SimuladoControlledMutationCommitShellFixtureContext
    mutation_fixture: SimuladoRuntimeProgressMutationFixture | None
    mutation_transaction: SimuladoRuntimeProgressMutationTransaction | None
    missing_mutation_transaction_id: str | None = None


def _wrap_fixture(
    mutation_fixture: SimuladoRuntimeProgressMutationFixture,
) -> SimuladoControlledMutationCommitShellFixture:
    mutation_transaction = build_runtime_progress_mutation_transaction(mutation_fixture)
    assert mutation_transaction is not None
    return SimuladoControlledMutationCommitShellFixture(
        context=SimuladoControlledMutationCommitShellFixtureContext(
            repository=mutation_fixture.context.repository,
            service=SimuladoControlledRuntimeMutationCommitService(
                mutation_fixture.context.repository
            ),
            user_id=mutation_fixture.context.user_id,
        ),
        mutation_fixture=mutation_fixture,
        mutation_transaction=mutation_transaction,
    )


def _persist_transaction(
    fixture: SimuladoControlledMutationCommitShellFixture,
) -> SimuladoControlledMutationCommitShellFixture:
    transaction = fixture.mutation_transaction
    assert transaction is not None
    fixture.context.repository.save_simulado_runtime_progress_mutation_transaction(
        transaction,
        user_id=fixture.context.user_id,
    )
    return fixture


def _enable_future_commit_candidate(
    transaction: SimuladoRuntimeProgressMutationTransaction,
    *,
    commit_policy_present: bool = True,
    explicit_commit_approval_present: bool = True,
    audit_confirmation_present: bool = True,
) -> None:
    transaction.mutation_valid_for_commit = True
    transaction.mutation_commit_ready = True
    transaction.rollback_plan.rollback_available = True
    transaction.rollback_plan.rollback_verified = True
    for delta in transaction.proposed_progress_deltas:
        delta.commit_allowed = True
        delta.blockers = [item for item in delta.blockers if item != "delta_blocked_by_commit_not_allowed"]
    for update in transaction.proposed_surface_updates:
        update.commit_allowed = True
        update.blockers = [
            item for item in update.blockers if item != "surface_update_blocked_by_commit_not_allowed"
        ]
    transaction.metadata["controlled_commit_policy_present"] = commit_policy_present
    transaction.metadata["controlled_commit_explicit_commit_approval_present"] = (
        explicit_commit_approval_present
    )
    transaction.metadata["controlled_commit_audit_confirmation_present"] = audit_confirmation_present


def build_controlled_mutation_commit_shell(
    fixture: SimuladoControlledMutationCommitShellFixture,
) -> SimuladoControlledRuntimeMutationCommitShell | None:
    source_id = fixture.missing_mutation_transaction_id
    if fixture.mutation_transaction is not None:
        source_id = fixture.mutation_transaction.mutation_transaction_id
    assert source_id is not None
    return fixture.context.service.build_commit_shell(
        source_mutation_transaction_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_mutation_transaction_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    mutation_fixture = _missing_explicit_apply_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoControlledMutationCommitShellFixture(
        context=SimuladoControlledMutationCommitShellFixtureContext(
            repository=mutation_fixture.context.repository,
            service=SimuladoControlledRuntimeMutationCommitService(mutation_fixture.context.repository),
            user_id=user_id,
        ),
        mutation_fixture=None,
        mutation_transaction=None,
        missing_mutation_transaction_id="simulado-progress-mutation:missing",
    )


def transaction_proposal_only_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return _wrap_fixture(_approved_for_future_only_fixture(tmp_path, user_id=user_id, repository=repository))


def transaction_not_proposal_only_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.mutation_transaction
    assert transaction is not None
    transaction.mutation_mode = "live_commit_requested"
    return _persist_transaction(fixture)


def transaction_already_committed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.mutation_transaction
    assert transaction is not None
    transaction.mutation_committed = True
    transaction.mutation_status = "mutation_committed"
    return _persist_transaction(fixture)


def mutation_not_valid_for_commit_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)


def mutation_commit_not_ready_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.mutation_transaction
    assert transaction is not None
    transaction.mutation_valid_for_commit = True
    transaction.mutation_commit_ready = False
    return _persist_transaction(fixture)


def rollback_not_available_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.mutation_transaction
    assert transaction is not None
    _enable_future_commit_candidate(transaction)
    transaction.rollback_plan.rollback_available = False
    transaction.rollback_plan.rollback_verified = False
    return _persist_transaction(fixture)


def rollback_not_verified_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.mutation_transaction
    assert transaction is not None
    _enable_future_commit_candidate(transaction)
    transaction.rollback_plan.rollback_available = True
    transaction.rollback_plan.rollback_verified = False
    return _persist_transaction(fixture)


def deltas_not_commit_allowed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.mutation_transaction
    assert transaction is not None
    _enable_future_commit_candidate(transaction)
    for delta in transaction.proposed_progress_deltas:
        delta.commit_allowed = False
        if "delta_blocked_by_commit_not_allowed" not in delta.blockers:
            delta.blockers.append("delta_blocked_by_commit_not_allowed")
    return _persist_transaction(fixture)


def surfaces_not_commit_allowed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.mutation_transaction
    assert transaction is not None
    _enable_future_commit_candidate(transaction)
    for update in transaction.proposed_surface_updates:
        update.commit_allowed = False
        if "surface_update_blocked_by_commit_not_allowed" not in update.blockers:
            update.blockers.append("surface_update_blocked_by_commit_not_allowed")
    return _persist_transaction(fixture)


def commit_policy_missing_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.mutation_transaction
    assert transaction is not None
    _enable_future_commit_candidate(
        transaction,
        commit_policy_present=False,
        explicit_commit_approval_present=True,
        audit_confirmation_present=True,
    )
    return _persist_transaction(fixture)


def explicit_commit_approval_missing_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.mutation_transaction
    assert transaction is not None
    _enable_future_commit_candidate(
        transaction,
        commit_policy_present=True,
        explicit_commit_approval_present=False,
        audit_confirmation_present=True,
    )
    return _persist_transaction(fixture)


def audit_confirmation_missing_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.mutation_transaction
    assert transaction is not None
    _enable_future_commit_candidate(
        transaction,
        commit_policy_present=True,
        explicit_commit_approval_present=True,
        audit_confirmation_present=False,
    )
    return _persist_transaction(fixture)


def runtime_mutation_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = _wrap_fixture(_runtime_mutation_disabled_fixture(tmp_path, user_id=user_id, repository=repository))
    transaction = fixture.mutation_transaction
    assert transaction is not None
    _enable_future_commit_candidate(transaction)
    transaction.metadata["force_runtime_mutation_disabled"] = True
    return _persist_transaction(fixture)


def unsafe_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = _wrap_fixture(_unsafe_source_fixture(tmp_path, user_id=user_id, repository=repository))
    transaction = fixture.mutation_transaction
    assert transaction is not None
    _enable_future_commit_candidate(transaction)
    return _persist_transaction(fixture)


def public_answer_key_exposure_forbidden_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return unsafe_source_fixture(tmp_path, user_id=user_id, repository=repository)


def explicit_apply_not_approved_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return _wrap_fixture(_explicit_apply_not_approved_fixture(tmp_path, user_id=user_id, repository=repository))


def mixed_commit_shell_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    fixture = _wrap_fixture(_mixed_mutation_fixture(tmp_path, user_id=user_id, repository=repository))
    transaction = fixture.mutation_transaction
    assert transaction is not None
    transaction.metadata["force_runtime_mutation_disabled"] = True
    return _persist_transaction(fixture)


def delta_commit_decision_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)


def surface_commit_decision_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)


def rollback_readiness_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_requirements_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_trail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)


def commit_mode_status_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)


def no_mutation_commit_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return transaction_proposal_only_fixture(tmp_path, user_id=user_id, repository=repository)


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)


def user_scope_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledMutationCommitShellFixture:
    return _wrap_fixture(_api_readonly_fixture(tmp_path, user_id=user_id, repository=repository))
