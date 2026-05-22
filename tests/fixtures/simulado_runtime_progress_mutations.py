from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoExplicitRuntimeProgressApply,
    SimuladoRuntimeProgressMutationTransaction,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_progress_mutation import (
    SimuladoRuntimeProgressMutationService,
)
from tests.fixtures.simulado_explicit_runtime_applies import (
    SimuladoExplicitRuntimeApplyFixture,
    api_readonly_fixture as _api_readonly_fixture,
    approve_payload,
    build_explicit_runtime_apply,
    deny_payload,
    explicit_apply_source_fixture,
    mixed_decision_fixture as _mixed_decision_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    unsafe_source_fixture as _unsafe_source_fixture,
)


def approve_all_payload() -> dict[str, object]:
    return approve_payload(
        runtime_policy_confirmed=True,
        explicit_apply_approval_confirmed=True,
        audit_confirmed=True,
        rollback_plan_confirmed=True,
        human_review_confirmed=True,
        public_answer_key_absence_confirmed=True,
    )


@dataclass
class SimuladoRuntimeProgressMutationFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoRuntimeProgressMutationService
    user_id: str


@dataclass
class SimuladoRuntimeProgressMutationFixture:
    context: SimuladoRuntimeProgressMutationFixtureContext
    explicit_apply_fixture: SimuladoExplicitRuntimeApplyFixture | None
    explicit_apply: SimuladoExplicitRuntimeProgressApply | None
    missing_explicit_apply_id: str | None = None


def _wrap_fixture(
    explicit_apply_fixture: SimuladoExplicitRuntimeApplyFixture,
    *,
    decision_payload: dict[str, object] | None,
) -> SimuladoRuntimeProgressMutationFixture:
    explicit_apply = build_explicit_runtime_apply(
        explicit_apply_fixture,
        decision_payload=decision_payload,
    )
    assert explicit_apply is not None
    return SimuladoRuntimeProgressMutationFixture(
        context=SimuladoRuntimeProgressMutationFixtureContext(
            repository=explicit_apply_fixture.context.repository,
            service=SimuladoRuntimeProgressMutationService(explicit_apply_fixture.context.repository),
            user_id=explicit_apply_fixture.context.user_id,
        ),
        explicit_apply_fixture=explicit_apply_fixture,
        explicit_apply=explicit_apply,
    )


def _persist_explicit_apply(
    fixture: SimuladoRuntimeProgressMutationFixture,
) -> SimuladoRuntimeProgressMutationFixture:
    explicit_apply = fixture.explicit_apply
    assert explicit_apply is not None
    fixture.context.repository.save_simulado_explicit_runtime_apply(
        explicit_apply,
        user_id=fixture.context.user_id,
    )
    return fixture


def build_runtime_progress_mutation_transaction(
    fixture: SimuladoRuntimeProgressMutationFixture,
) -> SimuladoRuntimeProgressMutationTransaction | None:
    source_id = fixture.missing_explicit_apply_id
    if fixture.explicit_apply is not None:
        source_id = fixture.explicit_apply.explicit_apply_id
    assert source_id is not None
    return fixture.context.service.build_mutation_transaction(
        source_explicit_apply_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_explicit_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressMutationFixture:
    explicit_fixture = explicit_apply_source_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoRuntimeProgressMutationFixture(
        context=SimuladoRuntimeProgressMutationFixtureContext(
            repository=explicit_fixture.context.repository,
            service=SimuladoRuntimeProgressMutationService(explicit_fixture.context.repository),
            user_id=user_id,
        ),
        explicit_apply_fixture=None,
        explicit_apply=None,
        missing_explicit_apply_id="simulado-explicit-apply:missing",
    )


def explicit_apply_not_approved_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressMutationFixture:
    return _wrap_fixture(
        explicit_apply_source_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=deny_payload(),
    )


def approved_for_future_review_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressMutationFixture:
    return _wrap_fixture(
        explicit_apply_source_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )


def confirmations_incomplete_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressMutationFixture:
    return _wrap_fixture(
        explicit_apply_source_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_payload(),
    )


def intents_not_approved_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressMutationFixture:
    fixture = approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    explicit_apply = fixture.explicit_apply
    assert explicit_apply is not None
    for approval in explicit_apply.intent_approvals:
        approval.approved_for_future_runtime_mutation_review = False
        approval.explicitly_approved = False
        approval.approval_state = "intent_blocked"
    return _persist_explicit_apply(fixture)


def surfaces_not_approved_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressMutationFixture:
    fixture = approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    explicit_apply = fixture.explicit_apply
    assert explicit_apply is not None
    for approval in explicit_apply.surface_approvals:
        approval.approved_for_future_runtime_mutation_review = False
        approval.explicitly_approved = False
        approval.approval_state = "surface_blocked"
    return _persist_explicit_apply(fixture)


def runtime_mutation_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressMutationFixture:
    fixture = approved_for_future_review_fixture(tmp_path, user_id=user_id, repository=repository)
    explicit_apply = fixture.explicit_apply
    assert explicit_apply is not None
    explicit_apply.metadata["force_runtime_mutation_disabled"] = True
    return _persist_explicit_apply(fixture)


def unsafe_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressMutationFixture:
    return _wrap_fixture(
        _unsafe_source_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )


def mixed_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressMutationFixture:
    return _wrap_fixture(
        _mixed_decision_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_payload(),
    )


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressMutationFixture:
    return _wrap_fixture(
        _no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressMutationFixture:
    return _wrap_fixture(
        _api_readonly_fixture(tmp_path, user_id=user_id, repository=repository),
        decision_payload=approve_all_payload(),
    )
