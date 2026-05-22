from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoExplicitRuntimeMutationCommit,
    SimuladoRuntimeMutationCommitTransaction,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_mutation_commit_transaction import (
    SimuladoRuntimeMutationCommitTransactionService,
)
from tests.fixtures.simulado_explicit_mutation_commits import (
    SimuladoExplicitMutationCommitFixture,
    api_readonly_fixture as _api_readonly_fixture,
    approve_all_payload,
    approve_payload,
    build_explicit_mutation_commit,
    deny_payload,
    explicit_commit_source_fixture,
    mixed_decision_fixture as _mixed_decision_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    unsafe_source_fixture as _unsafe_source_fixture,
)


@dataclass
class SimuladoRuntimeMutationCommitTransactionFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoRuntimeMutationCommitTransactionService
    user_id: str


@dataclass
class SimuladoRuntimeMutationCommitTransactionFixture:
    context: SimuladoRuntimeMutationCommitTransactionFixtureContext
    explicit_commit_fixture: SimuladoExplicitMutationCommitFixture | None
    explicit_commit: SimuladoExplicitRuntimeMutationCommit | None
    missing_explicit_commit_id: str | None = None


def _wrap_fixture(
    explicit_commit_fixture: SimuladoExplicitMutationCommitFixture,
    *,
    decision_payload: dict[str, object] | None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    explicit_commit = build_explicit_mutation_commit(
        explicit_commit_fixture,
        decision_payload=decision_payload,
    )
    assert explicit_commit is not None
    return SimuladoRuntimeMutationCommitTransactionFixture(
        context=SimuladoRuntimeMutationCommitTransactionFixtureContext(
            repository=explicit_commit_fixture.context.repository,
            service=SimuladoRuntimeMutationCommitTransactionService(
                explicit_commit_fixture.context.repository
            ),
            user_id=explicit_commit_fixture.context.user_id,
        ),
        explicit_commit_fixture=explicit_commit_fixture,
        explicit_commit=explicit_commit,
    )


def _persist_explicit_commit(
    fixture: SimuladoRuntimeMutationCommitTransactionFixture,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    explicit_commit = fixture.explicit_commit
    assert explicit_commit is not None
    fixture.context.repository.save_simulado_explicit_mutation_commit(
        explicit_commit,
        user_id=fixture.context.user_id,
    )
    return fixture


def build_runtime_mutation_commit_transaction(
    fixture: SimuladoRuntimeMutationCommitTransactionFixture,
) -> SimuladoRuntimeMutationCommitTransaction | None:
    source_id = fixture.missing_explicit_commit_id
    if fixture.explicit_commit is not None:
        source_id = fixture.explicit_commit.explicit_commit_id
    assert source_id is not None
    return fixture.context.service.build_commit_transaction(
        source_explicit_commit_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_explicit_commit_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    explicit_fixture = explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoRuntimeMutationCommitTransactionFixture(
        context=SimuladoRuntimeMutationCommitTransactionFixtureContext(
            repository=explicit_fixture.context.repository,
            service=SimuladoRuntimeMutationCommitTransactionService(explicit_fixture.context.repository),
            user_id=user_id,
        ),
        explicit_commit_fixture=None,
        explicit_commit=None,
        missing_explicit_commit_id="simulado-explicit-commit:missing",
    )


def explicit_commit_not_approved_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return _wrap_fixture(
        explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=deny_payload(),
    )


def approved_for_future_review_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return _wrap_fixture(
        explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )


def confirmations_incomplete_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return _wrap_fixture(
        explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_payload(),
    )


def commit_shell_not_pre_commit_only_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    fixture = approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    shell_fixture = fixture.explicit_commit_fixture
    assert shell_fixture is not None
    shell = shell_fixture.controlled_commit_shell
    assert shell is not None
    shell.commit_mode = "live_commit_requested"
    shell.commit_status = "committed_like_state_forbidden"
    shell_fixture.context.repository.save_simulado_controlled_mutation_commit_shell(
        shell,
        user_id=user_id,
    )
    return fixture


def missing_source_mutation_transaction_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    fixture = approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    explicit_commit = fixture.explicit_commit
    assert explicit_commit is not None
    explicit_commit.source_mutation_transaction_id = "simulado-runtime-progress-mutation:missing"
    return _persist_explicit_commit(fixture)


def missing_rollback_execution_plan_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    fixture = approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.context.repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        fixture.explicit_commit.source_mutation_transaction_id,
        user_id=user_id,
    )
    assert transaction is not None
    transaction.rollback_plan.rollback_plan_id = ""
    transaction.rollback_plan.rollback_steps_count = 0
    fixture.context.repository.save_simulado_runtime_progress_mutation_transaction(
        transaction,
        user_id=user_id,
    )
    return fixture


def rollback_unavailable_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    fixture = approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.context.repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        fixture.explicit_commit.source_mutation_transaction_id,
        user_id=user_id,
    )
    assert transaction is not None
    transaction.rollback_plan.rollback_available = False
    transaction.rollback_plan.rollback_verified = False
    fixture.context.repository.save_simulado_runtime_progress_mutation_transaction(
        transaction,
        user_id=user_id,
    )
    return fixture


def rollback_unverified_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    fixture = approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    transaction = fixture.context.repository.get_simulado_runtime_progress_mutation_transaction_by_id(
        fixture.explicit_commit.source_mutation_transaction_id,
        user_id=user_id,
    )
    assert transaction is not None
    transaction.rollback_plan.rollback_available = True
    transaction.rollback_plan.rollback_verified = False
    fixture.context.repository.save_simulado_runtime_progress_mutation_transaction(
        transaction,
        user_id=user_id,
    )
    return fixture


def delta_approvals_not_ready_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    fixture = approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    explicit_commit = fixture.explicit_commit
    assert explicit_commit is not None
    for approval in explicit_commit.delta_approvals:
        approval.approved_for_future_mutation_commit_review = False
        approval.explicitly_approved = False
        approval.approval_state = "delta_blocked"
    return _persist_explicit_commit(fixture)


def surface_approvals_not_ready_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    fixture = approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    explicit_commit = fixture.explicit_commit
    assert explicit_commit is not None
    for approval in explicit_commit.surface_approvals:
        approval.approved_for_future_mutation_commit_review = False
        approval.explicitly_approved = False
        approval.approval_state = "surface_blocked"
    return _persist_explicit_commit(fixture)


def commit_execution_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    fixture = approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    explicit_commit = fixture.explicit_commit
    assert explicit_commit is not None
    explicit_commit.metadata["force_commit_execution_disabled"] = True
    return _persist_explicit_commit(fixture)


def public_answer_key_exposure_forbidden_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return unsafe_source_fixture(tmp_path, user_id=user_id, repository=repository)


def unsafe_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return _wrap_fixture(
        _unsafe_source_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )


def mixed_commit_transaction_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return _wrap_fixture(
        _mixed_decision_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_payload(),
    )


def planned_progress_commits_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def planned_surface_commits_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def rollback_execution_plan_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_trail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def no_commit_execution_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_application_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return _wrap_fixture(
        _no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return _wrap_fixture(
        _api_readonly_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )


def user_scope_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeMutationCommitTransactionFixture:
    return api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
