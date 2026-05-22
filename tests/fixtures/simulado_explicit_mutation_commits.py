from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoControlledRuntimeMutationCommitShell,
    SimuladoExplicitRuntimeMutationCommit,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_explicit_mutation_commit import (
    SimuladoExplicitRuntimeMutationCommitService,
)
from tests.fixtures.simulado_controlled_mutation_commit_shells import (
    SimuladoControlledMutationCommitShellFixture,
    api_readonly_fixture as _api_readonly_fixture,
    build_controlled_mutation_commit_shell,
    mixed_commit_shell_fixture as _mixed_commit_shell_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    public_answer_key_exposure_forbidden_fixture as _unsafe_source_fixture,
)


@dataclass
class SimuladoExplicitMutationCommitFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoExplicitRuntimeMutationCommitService
    user_id: str


@dataclass
class SimuladoExplicitMutationCommitFixture:
    context: SimuladoExplicitMutationCommitFixtureContext
    controlled_commit_shell_fixture: SimuladoControlledMutationCommitShellFixture | None
    controlled_commit_shell: SimuladoControlledRuntimeMutationCommitShell | None
    missing_commit_shell_id: str | None = None


def approve_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Approved for future mutation commit review.",
    commit_policy_confirmed: bool = False,
    explicit_commit_approval_confirmed: bool = False,
    audit_confirmed: bool = False,
    rollback_verified_confirmed: bool = False,
    human_review_confirmed: bool = False,
    public_answer_key_absence_confirmed: bool = False,
) -> dict[str, object]:
    return {
        "decision_type": "approve_for_future_mutation_commit_review",
        "reviewer_id": reviewer_id,
        "reason": reason,
        "confirmations": {
            "commit_policy_confirmed": commit_policy_confirmed,
            "explicit_commit_approval_confirmed": explicit_commit_approval_confirmed,
            "audit_confirmed": audit_confirmed,
            "rollback_verified_confirmed": rollback_verified_confirmed,
            "human_review_confirmed": human_review_confirmed,
            "public_answer_key_absence_confirmed": public_answer_key_absence_confirmed,
        },
    }


def deny_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Denied pending future review.",
) -> dict[str, object]:
    return {
        "decision_type": "deny_commit",
        "reviewer_id": reviewer_id,
        "reason": reason,
    }


def request_revision_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Revision requested before any future commit review.",
) -> dict[str, object]:
    return {
        "decision_type": "request_revision",
        "reviewer_id": reviewer_id,
        "reason": reason,
    }


def block_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Commit blocked for future review.",
) -> dict[str, object]:
    return {
        "decision_type": "block_commit",
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
        commit_policy_confirmed=True,
        explicit_commit_approval_confirmed=True,
        audit_confirmed=True,
        rollback_verified_confirmed=True,
        human_review_confirmed=True,
        public_answer_key_absence_confirmed=True,
    )


def _wrap_fixture(
    controlled_commit_shell_fixture: SimuladoControlledMutationCommitShellFixture,
) -> SimuladoExplicitMutationCommitFixture:
    controlled_commit_shell = build_controlled_mutation_commit_shell(
        controlled_commit_shell_fixture
    )
    assert controlled_commit_shell is not None
    return SimuladoExplicitMutationCommitFixture(
        context=SimuladoExplicitMutationCommitFixtureContext(
            repository=controlled_commit_shell_fixture.context.repository,
            service=SimuladoExplicitRuntimeMutationCommitService(
                controlled_commit_shell_fixture.context.repository
            ),
            user_id=controlled_commit_shell_fixture.context.user_id,
        ),
        controlled_commit_shell_fixture=controlled_commit_shell_fixture,
        controlled_commit_shell=controlled_commit_shell,
    )


def _persist_commit_shell(
    fixture: SimuladoExplicitMutationCommitFixture,
) -> SimuladoExplicitMutationCommitFixture:
    controlled_commit_shell = fixture.controlled_commit_shell
    assert controlled_commit_shell is not None
    fixture.context.repository.save_simulado_controlled_mutation_commit_shell(
        controlled_commit_shell,
        user_id=fixture.context.user_id,
    )
    return fixture


def build_explicit_mutation_commit(
    fixture: SimuladoExplicitMutationCommitFixture,
    *,
    decision_payload: dict[str, object] | None = None,
) -> SimuladoExplicitRuntimeMutationCommit | None:
    source_id = fixture.missing_commit_shell_id
    if fixture.controlled_commit_shell is not None:
        source_id = fixture.controlled_commit_shell.commit_shell_id
    assert source_id is not None
    return fixture.context.service.build_explicit_commit(
        source_commit_shell_id=source_id,
        decision_payload=decision_payload,
        user_id=fixture.context.user_id,
    )


def missing_controlled_commit_shell_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    shell_fixture = _no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoExplicitMutationCommitFixture(
        context=SimuladoExplicitMutationCommitFixtureContext(
            repository=shell_fixture.context.repository,
            service=SimuladoExplicitRuntimeMutationCommitService(shell_fixture.context.repository),
            user_id=user_id,
        ),
        controlled_commit_shell_fixture=None,
        controlled_commit_shell=None,
        missing_commit_shell_id="simulado-mutation-commit-shell:missing",
    )


def explicit_commit_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return _wrap_fixture(_no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository))


def no_decision_payload_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def approve_without_confirmations_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def approve_with_all_confirmations_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def deny_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def request_revision_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def block_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def mark_not_reviewed_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def confirmation_summary_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def delta_approvals_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def surface_approvals_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_trail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def unsafe_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return _wrap_fixture(_unsafe_source_fixture(tmp_path, user_id=user_id, repository=repository))


def mixed_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return _wrap_fixture(_mixed_commit_shell_fixture(tmp_path, user_id=user_id, repository=repository))


def no_runtime_application_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def payload_idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def different_payload_behavior_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return explicit_commit_source_fixture(tmp_path, user_id=user_id, repository=repository)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitMutationCommitFixture:
    return _wrap_fixture(_api_readonly_fixture(tmp_path, user_id=user_id, repository=repository))
