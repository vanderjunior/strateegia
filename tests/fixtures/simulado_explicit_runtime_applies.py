from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoControlledRuntimeApplyShell,
    SimuladoExplicitRuntimeProgressApply,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_explicit_runtime_apply import (
    SimuladoExplicitRuntimeProgressApplyService,
)
from tests.fixtures.simulado_controlled_apply_shells import (
    SimuladoControlledApplyShellFixture,
    api_readonly_fixture as _api_readonly_fixture,
    build_controlled_apply_shell,
    mixed_shell_fixture as _mixed_shell_fixture,
    no_public_key_gabarito_safety_fixture as _no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture as _no_runtime_application_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
)


@dataclass
class SimuladoExplicitRuntimeApplyFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoExplicitRuntimeProgressApplyService
    user_id: str


@dataclass
class SimuladoExplicitRuntimeApplyFixture:
    context: SimuladoExplicitRuntimeApplyFixtureContext
    controlled_apply_shell_fixture: SimuladoControlledApplyShellFixture | None
    controlled_apply_shell: SimuladoControlledRuntimeApplyShell | None
    missing_apply_shell_id: str | None = None


def approve_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Approved for future runtime mutation review.",
    runtime_policy_confirmed: bool = False,
    explicit_apply_approval_confirmed: bool = False,
    audit_confirmed: bool = False,
    rollback_plan_confirmed: bool = False,
    human_review_confirmed: bool = False,
    public_answer_key_absence_confirmed: bool = False,
) -> dict[str, object]:
    return {
        "decision_type": "approve_for_future_runtime_mutation_review",
        "reviewer_id": reviewer_id,
        "reason": reason,
        "confirmations": {
            "runtime_policy_confirmed": runtime_policy_confirmed,
            "explicit_apply_approval_confirmed": explicit_apply_approval_confirmed,
            "audit_confirmed": audit_confirmed,
            "rollback_plan_confirmed": rollback_plan_confirmed,
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
        "decision_type": "deny_apply",
        "reviewer_id": reviewer_id,
        "reason": reason,
    }


def request_revision_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Revision requested before future review.",
) -> dict[str, object]:
    return {
        "decision_type": "request_revision",
        "reviewer_id": reviewer_id,
        "reason": reason,
    }


def block_payload(
    *,
    reviewer_id: str = "reviewer-user",
    reason: str = "Apply blocked for future review.",
) -> dict[str, object]:
    return {
        "decision_type": "block_apply",
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


def _wrap_fixture(
    controlled_apply_shell_fixture: SimuladoControlledApplyShellFixture,
) -> SimuladoExplicitRuntimeApplyFixture:
    controlled_apply_shell = build_controlled_apply_shell(controlled_apply_shell_fixture)
    assert controlled_apply_shell is not None
    return SimuladoExplicitRuntimeApplyFixture(
        context=SimuladoExplicitRuntimeApplyFixtureContext(
            repository=controlled_apply_shell_fixture.context.repository,
            service=SimuladoExplicitRuntimeProgressApplyService(
                controlled_apply_shell_fixture.context.repository
            ),
            user_id=controlled_apply_shell_fixture.context.user_id,
        ),
        controlled_apply_shell_fixture=controlled_apply_shell_fixture,
        controlled_apply_shell=controlled_apply_shell,
    )


def _persist_controlled_shell(
    fixture: SimuladoExplicitRuntimeApplyFixture,
) -> SimuladoExplicitRuntimeApplyFixture:
    controlled_apply_shell = fixture.controlled_apply_shell
    assert controlled_apply_shell is not None
    fixture.context.repository.save_simulado_controlled_apply_shell(
        controlled_apply_shell,
        user_id=fixture.context.user_id,
    )
    return fixture


def build_explicit_runtime_apply(
    fixture: SimuladoExplicitRuntimeApplyFixture,
    *,
    decision_payload: dict[str, object] | None = None,
) -> SimuladoExplicitRuntimeProgressApply | None:
    source_id = fixture.missing_apply_shell_id
    if fixture.controlled_apply_shell is not None:
        source_id = fixture.controlled_apply_shell.apply_shell_id
    assert source_id is not None
    return fixture.context.service.build_explicit_apply(
        source_apply_shell_id=source_id,
        decision_payload=decision_payload,
        user_id=fixture.context.user_id,
    )


def missing_controlled_apply_shell_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitRuntimeApplyFixture:
    shell_fixture = _no_runtime_application_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoExplicitRuntimeApplyFixture(
        context=SimuladoExplicitRuntimeApplyFixtureContext(
            repository=shell_fixture.context.repository,
            service=SimuladoExplicitRuntimeProgressApplyService(shell_fixture.context.repository),
            user_id=user_id,
        ),
        controlled_apply_shell_fixture=None,
        controlled_apply_shell=None,
        missing_apply_shell_id="simulado-controlled-apply-shell:missing",
    )


def explicit_apply_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitRuntimeApplyFixture:
    return _wrap_fixture(_no_runtime_application_fixture(tmp_path, user_id=user_id, repository=repository))


def unsafe_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitRuntimeApplyFixture:
    fixture = _wrap_fixture(
        _no_public_key_gabarito_safety_fixture(tmp_path, user_id=user_id, repository=repository)
    )
    controlled_apply_shell = fixture.controlled_apply_shell
    assert controlled_apply_shell is not None
    controlled_apply_shell.answer_key_publicly_exposed = True
    controlled_apply_shell.gabarito_publicly_exposed = True
    return _persist_controlled_shell(fixture)


def mixed_explicit_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitRuntimeApplyFixture:
    return _wrap_fixture(_mixed_shell_fixture(tmp_path, user_id=user_id, repository=repository))


def no_runtime_application_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitRuntimeApplyFixture:
    return explicit_apply_source_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitRuntimeApplyFixture:
    return _wrap_fixture(_no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository))


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitRuntimeApplyFixture:
    return explicit_apply_source_fixture(tmp_path, user_id=user_id, repository=repository)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExplicitRuntimeApplyFixture:
    return explicit_apply_source_fixture(tmp_path, user_id=user_id, repository=repository)

