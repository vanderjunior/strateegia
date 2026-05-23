from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoFinalPedagogicalUpdateEvent,
    SimuladoRuntimeApplyPolicy,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_apply_policy import SimuladoRuntimeApplyPolicyService
from tests.fixtures.simulado_final_pedagogical_update_events import (
    SimuladoFinalPedagogicalUpdateEventFixture,
    SimuladoFinalPedagogicalUpdateEventFixtureContext,
    api_readonly_fixture as _api_readonly_final_event_fixture,
    build_final_pedagogical_update_event,
    final_event_summary_fixture as _final_event_summary_fixture,
    public_answer_key_exposure_forbidden_fixture as _unsafe_final_event_fixture,
)


@dataclass
class SimuladoRuntimeApplyPolicyFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoRuntimeApplyPolicyService
    user_id: str


@dataclass
class SimuladoRuntimeApplyPolicyFixture:
    context: SimuladoRuntimeApplyPolicyFixtureContext
    final_event_fixture: SimuladoFinalPedagogicalUpdateEventFixture | None
    final_event: SimuladoFinalPedagogicalUpdateEvent | None
    missing_final_event_id: str | None = None


@dataclass(frozen=True)
class RuntimeApplyPolicySourceSnapshot:
    final_event: dict[str, object] | None
    controlled_execution: dict[str, object] | None
    execution_plan: dict[str, object] | None
    execution_approval: dict[str, object] | None
    execution_guardrail: dict[str, object] | None
    progress: dict[str, object]
    runtime_apply_policy_count: int


def _build_final_event(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoFinalPedagogicalUpdateEvent:
    result = build_final_pedagogical_update_event(fixture)
    assert result is not None
    return result


def _wrap_fixture(
    final_event_fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoRuntimeApplyPolicyFixture:
    final_event = _build_final_event(final_event_fixture)
    return SimuladoRuntimeApplyPolicyFixture(
        context=SimuladoRuntimeApplyPolicyFixtureContext(
            repository=final_event_fixture.context.repository,
            service=SimuladoRuntimeApplyPolicyService(final_event_fixture.context.repository),
            user_id=final_event_fixture.context.user_id,
        ),
        final_event_fixture=final_event_fixture,
        final_event=final_event,
    )


def _persist_final_event(
    fixture: SimuladoRuntimeApplyPolicyFixture,
) -> SimuladoRuntimeApplyPolicyFixture:
    final_event = fixture.final_event
    assert final_event is not None
    fixture.context.repository.save_simulado_final_pedagogical_update_event(
        final_event,
        user_id=fixture.context.user_id,
    )
    return fixture


def _set_policy_inputs(
    fixture: SimuladoRuntimeApplyPolicyFixture,
    **inputs: object,
) -> SimuladoRuntimeApplyPolicyFixture:
    final_event = fixture.final_event
    assert final_event is not None
    metadata = dict(final_event.metadata)
    policy_inputs = dict(metadata.get("runtime_apply_policy_inputs", {}))
    policy_inputs.update(inputs)
    metadata["runtime_apply_policy_inputs"] = policy_inputs
    final_event.metadata = metadata
    return _persist_final_event(fixture)


def _mark_not_proposal_only(
    fixture: SimuladoRuntimeApplyPolicyFixture,
) -> SimuladoRuntimeApplyPolicyFixture:
    final_event = fixture.final_event
    assert final_event is not None
    final_event.final_event_mode = "non_proposal_event"
    final_event.final_event_status = "final_event_needs_review"
    return _persist_final_event(fixture)


def _mark_already_applied(
    fixture: SimuladoRuntimeApplyPolicyFixture,
) -> SimuladoRuntimeApplyPolicyFixture:
    final_event = fixture.final_event
    assert final_event is not None
    final_event.final_pedagogical_update_event_applied = True
    final_event.final_event_status = "applied"
    return _persist_final_event(fixture)


def build_runtime_apply_policy(
    fixture: SimuladoRuntimeApplyPolicyFixture,
) -> SimuladoRuntimeApplyPolicy | None:
    source_id = fixture.missing_final_event_id
    if fixture.final_event is not None:
        source_id = fixture.final_event.final_event_id
    assert source_id is not None
    return fixture.context.service.build_runtime_apply_policy(
        source_final_event_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_final_event_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    final_event_fixture = _api_readonly_final_event_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    return SimuladoRuntimeApplyPolicyFixture(
        context=SimuladoRuntimeApplyPolicyFixtureContext(
            repository=final_event_fixture.context.repository,
            service=SimuladoRuntimeApplyPolicyService(final_event_fixture.context.repository),
            user_id=user_id,
        ),
        final_event_fixture=None,
        final_event=None,
        missing_final_event_id="simulado-final-pedagogical-event:missing",
    )


def final_event_not_proposal_only_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return _mark_not_proposal_only(
        _wrap_fixture(_final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository))
    )


def final_event_already_applied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return _mark_already_applied(
        _wrap_fixture(_final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository))
    )


def feature_flag_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return _wrap_fixture(_final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository))


def runtime_apply_not_allowed_now_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return _set_policy_inputs(
        _wrap_fixture(_final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)),
        runtime_apply_feature_flag_enabled=True,
        apply_window_open=False,
    )


def idempotency_requirement_missing_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return _set_policy_inputs(
        _wrap_fixture(_final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)),
        runtime_apply_feature_flag_enabled=True,
        apply_window_open=True,
    )


def rollback_requirement_missing_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return _set_policy_inputs(
        idempotency_requirement_missing_fixture(tmp_path, user_id=user_id, repository=repository),
        idempotency_key_present=True,
        idempotency_key_valid=True,
    )


def audit_requirement_missing_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return _set_policy_inputs(
        rollback_requirement_missing_fixture(tmp_path, user_id=user_id, repository=repository),
        rollback_plan_present=True,
        rollback_verified=True,
    )


def human_review_requirement_missing_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return _set_policy_inputs(
        audit_requirement_missing_fixture(tmp_path, user_id=user_id, repository=repository),
        audit_confirmation_present=True,
    )


def environment_not_safe_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return _set_policy_inputs(
        human_review_requirement_missing_fixture(tmp_path, user_id=user_id, repository=repository),
        human_review_present=True,
    )


def apply_scope_not_allowed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return _set_policy_inputs(
        environment_not_safe_fixture(tmp_path, user_id=user_id, repository=repository),
        environment_safe_for_apply=True,
        write_mode_allowed=True,
    )


def public_answer_key_exposure_forbidden_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return _wrap_fixture(_unsafe_final_event_fixture(tmp_path, user_id=user_id, repository=repository))


def policy_summary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplyPolicyFixture:
    return feature_flag_disabled_fixture(tmp_path, user_id=user_id, repository=repository)


def capture_runtime_apply_policy_source_snapshot(
    fixture: SimuladoRuntimeApplyPolicyFixture,
) -> RuntimeApplyPolicySourceSnapshot:
    final_event = fixture.final_event
    assert final_event is not None
    repository = fixture.context.repository
    user_id = fixture.context.user_id

    stored_final_event = repository.get_simulado_final_pedagogical_update_event_by_id(
        final_event.final_event_id,
        user_id=user_id,
    )
    stored_controlled_execution = repository.get_simulado_controlled_runtime_commit_execution_by_id(
        final_event.source_controlled_execution_id,
        user_id=user_id,
    )
    stored_execution_plan = repository.get_simulado_runtime_commit_execution_plan_by_id(
        final_event.source_execution_plan_id,
        user_id=user_id,
    )
    stored_execution_approval = repository.get_simulado_explicit_commit_execution_approval_by_id(
        final_event.source_execution_approval_id,
        user_id=user_id,
    )
    stored_execution_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        final_event.source_execution_guardrail_id,
        user_id=user_id,
    )

    return RuntimeApplyPolicySourceSnapshot(
        final_event=None if stored_final_event is None else stored_final_event.model_dump(mode="json"),
        controlled_execution=(
            None
            if stored_controlled_execution is None
            else stored_controlled_execution.model_dump(mode="json")
        ),
        execution_plan=(
            None if stored_execution_plan is None else stored_execution_plan.model_dump(mode="json")
        ),
        execution_approval=(
            None
            if stored_execution_approval is None
            else stored_execution_approval.model_dump(mode="json")
        ),
        execution_guardrail=(
            None
            if stored_execution_guardrail is None
            else stored_execution_guardrail.model_dump(mode="json")
        ),
        progress=repository.load_progress(user_id=user_id).model_dump(mode="json"),
        runtime_apply_policy_count=len(
            repository.list_user_simulado_runtime_apply_policies(user_id=user_id)
        ),
    )
