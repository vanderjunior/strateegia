from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.domain.models import (
    ProposedProgressUpdateEntry,
    SimuladoFinalPedagogicalUpdateEvent,
    SimuladoMinimalProgressLedgerApply,
    SimuladoRuntimeApplyPolicy,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_minimal_progress_ledger_apply import (
    SimuladoMinimalProgressLedgerApplyService,
)
from tests.fixtures.simulado_runtime_apply_policies import (
    SimuladoRuntimeApplyPolicyFixture,
    api_readonly_fixture as _api_readonly_policy_fixture,
    build_runtime_apply_policy,
    capture_runtime_apply_policy_source_snapshot,
    feature_flag_disabled_fixture as _feature_flag_disabled_fixture,
    public_answer_key_exposure_forbidden_fixture as _unsafe_policy_fixture,
    runtime_apply_not_allowed_now_fixture as _runtime_apply_not_allowed_now_fixture,
)


@dataclass
class SimuladoMinimalProgressLedgerApplyFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoMinimalProgressLedgerApplyService
    user_id: str


@dataclass
class SimuladoMinimalProgressLedgerApplyFixture:
    context: SimuladoMinimalProgressLedgerApplyFixtureContext
    runtime_apply_policy_fixture: SimuladoRuntimeApplyPolicyFixture | None
    runtime_apply_policy: SimuladoRuntimeApplyPolicy | None
    missing_runtime_apply_policy_id: str | None = None


@dataclass(frozen=True)
class MinimalProgressLedgerApplySourceSnapshot:
    final_event: dict[str, object] | None
    controlled_execution: dict[str, object] | None
    execution_plan: dict[str, object] | None
    execution_approval: dict[str, object] | None
    execution_guardrail: dict[str, object] | None
    runtime_apply_policy: dict[str, object] | None
    progress: dict[str, object]
    minimal_progress_ledger_apply_count: int


def _wrap_fixture(
    runtime_apply_policy_fixture: SimuladoRuntimeApplyPolicyFixture,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    runtime_apply_policy = build_runtime_apply_policy(runtime_apply_policy_fixture)
    assert runtime_apply_policy is not None
    return SimuladoMinimalProgressLedgerApplyFixture(
        context=SimuladoMinimalProgressLedgerApplyFixtureContext(
            repository=runtime_apply_policy_fixture.context.repository,
            service=SimuladoMinimalProgressLedgerApplyService(
                runtime_apply_policy_fixture.context.repository
            ),
            user_id=runtime_apply_policy_fixture.context.user_id,
        ),
        runtime_apply_policy_fixture=runtime_apply_policy_fixture,
        runtime_apply_policy=runtime_apply_policy,
    )


def _persist_policy(
    fixture: SimuladoMinimalProgressLedgerApplyFixture,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    fixture.context.repository.save_simulado_runtime_apply_policy(
        runtime_apply_policy,
        user_id=fixture.context.user_id,
    )
    return fixture


def _persist_final_event(
    fixture: SimuladoMinimalProgressLedgerApplyFixture,
    final_event: SimuladoFinalPedagogicalUpdateEvent,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    fixture.context.repository.save_simulado_final_pedagogical_update_event(
        final_event,
        user_id=fixture.context.user_id,
    )
    return fixture


def _get_final_event(
    fixture: SimuladoMinimalProgressLedgerApplyFixture,
) -> SimuladoFinalPedagogicalUpdateEvent:
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    final_event = fixture.context.repository.get_simulado_final_pedagogical_update_event_by_id(
        runtime_apply_policy.source_final_event_id,
        user_id=fixture.context.user_id,
    )
    assert final_event is not None
    return final_event


def _ensure_progress_updates(
    fixture: SimuladoMinimalProgressLedgerApplyFixture,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    final_event = _get_final_event(fixture)
    if final_event.proposed_progress_updates:
        return fixture
    final_event.proposed_progress_updates.append(
        ProposedProgressUpdateEntry(
            entry_id=f"proposed-progress-update:synthetic:{final_event.final_event_id}",
            update_kind="progress_delta_proposal",
            source_record_id=f"synthetic-progress-record:{final_event.final_event_id}",
            target_type="simulado_attempt",
            target_id=final_event.source_attempt_session_id or final_event.final_event_id,
            proposed=True,
            applied=False,
            apply_allowed=False,
            bounded_summary={
                "target_type": "simulado_attempt",
                "delta_kind": "mastery_delta",
                "source": "synthetic_fixture",
            },
            blockers=[],
            warnings=[],
            metadata={},
        )
    )
    return _persist_final_event(fixture, final_event)


def _set_allowed_policy(
    fixture: SimuladoMinimalProgressLedgerApplyFixture,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    runtime_apply_policy.runtime_apply_policy_status = "ready_for_future_minimal_apply_review"
    runtime_apply_policy.readiness_state = "minimal_progress_ledger_apply_ready"
    runtime_apply_policy.runtime_apply_feature_flag_enabled = True
    runtime_apply_policy.runtime_apply_allowed_now = True
    runtime_apply_policy.minimal_progress_ledger_apply_allowed = True
    runtime_apply_policy.policy_summary.apply_feature_flag_enabled = True
    runtime_apply_policy.policy_summary.apply_allowed_now = True
    runtime_apply_policy.policy_summary.minimal_progress_ledger_scope_allowed = True
    runtime_apply_policy.feature_flag_snapshot.feature_flag_enabled = True
    runtime_apply_policy.apply_scope_policy.minimal_progress_ledger_apply_allowed = True
    runtime_apply_policy.apply_scope_policy.allowed_surfaces = ["minimal_progress_ledger"]
    runtime_apply_policy.apply_scope_policy.blocked_surfaces = [
        "ranking",
        "retention",
        "scheduler",
        "study_cycle",
        "curriculum_graph",
        "adaptive_tuning",
    ]
    runtime_apply_policy.idempotency_requirement.idempotency_key_present = True
    runtime_apply_policy.idempotency_requirement.idempotency_key_valid = True
    runtime_apply_policy.idempotency_requirement.satisfied = True
    runtime_apply_policy.idempotency_requirement.blockers = []
    runtime_apply_policy.rollback_requirement.rollback_plan_present = True
    runtime_apply_policy.rollback_requirement.rollback_verified = True
    runtime_apply_policy.rollback_requirement.satisfied = True
    runtime_apply_policy.rollback_requirement.blockers = []
    runtime_apply_policy.audit_requirement.audit_confirmation_present = True
    runtime_apply_policy.audit_requirement.satisfied = True
    runtime_apply_policy.audit_requirement.blockers = []
    runtime_apply_policy.human_review_requirement.human_review_present = True
    runtime_apply_policy.human_review_requirement.satisfied = True
    runtime_apply_policy.human_review_requirement.blockers = []
    runtime_apply_policy.environment_safety_requirement.environment_safe_for_apply = True
    runtime_apply_policy.environment_safety_requirement.write_mode_allowed = True
    runtime_apply_policy.environment_safety_requirement.satisfied = True
    runtime_apply_policy.environment_safety_requirement.blockers = []
    runtime_apply_policy.metadata["minimal_progress_ledger_apply_idempotency_key"] = (
        f"minimal-progress-ledger:{runtime_apply_policy.runtime_apply_policy_id}"
    )
    _persist_policy(fixture)
    return _ensure_progress_updates(fixture)


def _clear_progress_updates(
    fixture: SimuladoMinimalProgressLedgerApplyFixture,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    final_event = _get_final_event(fixture)
    final_event.proposed_progress_updates = []
    return _persist_final_event(fixture, final_event)


def build_minimal_progress_ledger_apply(
    fixture: SimuladoMinimalProgressLedgerApplyFixture,
) -> SimuladoMinimalProgressLedgerApply | None:
    source_id = fixture.missing_runtime_apply_policy_id
    if fixture.runtime_apply_policy is not None:
        source_id = fixture.runtime_apply_policy.runtime_apply_policy_id
    assert source_id is not None
    return fixture.context.service.build_minimal_progress_ledger_apply(
        source_runtime_apply_policy_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_runtime_apply_policy_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    runtime_apply_policy_fixture = _api_readonly_policy_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    return SimuladoMinimalProgressLedgerApplyFixture(
        context=SimuladoMinimalProgressLedgerApplyFixtureContext(
            repository=runtime_apply_policy_fixture.context.repository,
            service=SimuladoMinimalProgressLedgerApplyService(
                runtime_apply_policy_fixture.context.repository
            ),
            user_id=user_id,
        ),
        runtime_apply_policy_fixture=None,
        runtime_apply_policy=None,
        missing_runtime_apply_policy_id="simulado-runtime-apply-policy:missing",
    )


def policy_feature_flag_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return _wrap_fixture(
        _feature_flag_disabled_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def runtime_apply_not_allowed_now_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return _wrap_fixture(
        _runtime_apply_not_allowed_now_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def minimal_progress_ledger_scope_not_allowed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    fixture = allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    runtime_apply_policy.minimal_progress_ledger_apply_allowed = False
    runtime_apply_policy.apply_scope_policy.minimal_progress_ledger_apply_allowed = False
    runtime_apply_policy.apply_scope_policy.allowed_surfaces = []
    runtime_apply_policy.apply_scope_policy.blocked_surfaces = [
        "minimal_progress_ledger",
        "ranking",
        "retention",
        "scheduler",
        "study_cycle",
        "curriculum_graph",
        "adaptive_tuning",
    ]
    runtime_apply_policy.policy_summary.minimal_progress_ledger_scope_allowed = False
    return _persist_policy(fixture)


def idempotency_requirement_unsatisfied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    fixture = allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    runtime_apply_policy.idempotency_requirement.idempotency_key_present = False
    runtime_apply_policy.idempotency_requirement.idempotency_key_valid = False
    runtime_apply_policy.idempotency_requirement.satisfied = False
    runtime_apply_policy.idempotency_requirement.blockers = [
        "blocked_by_idempotency_requirement_unsatisfied"
    ]
    return _persist_policy(fixture)


def rollback_requirement_unsatisfied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    fixture = allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    runtime_apply_policy.rollback_requirement.rollback_plan_present = False
    runtime_apply_policy.rollback_requirement.rollback_verified = False
    runtime_apply_policy.rollback_requirement.satisfied = False
    runtime_apply_policy.rollback_requirement.blockers = [
        "blocked_by_rollback_requirement_unsatisfied"
    ]
    return _persist_policy(fixture)


def audit_requirement_unsatisfied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    fixture = allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    runtime_apply_policy.audit_requirement.audit_confirmation_present = False
    runtime_apply_policy.audit_requirement.satisfied = False
    runtime_apply_policy.audit_requirement.blockers = [
        "blocked_by_audit_requirement_unsatisfied"
    ]
    return _persist_policy(fixture)


def human_review_requirement_unsatisfied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    fixture = allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    runtime_apply_policy.human_review_requirement.human_review_present = False
    runtime_apply_policy.human_review_requirement.satisfied = False
    runtime_apply_policy.human_review_requirement.blockers = [
        "blocked_by_human_review_requirement_unsatisfied"
    ]
    return _persist_policy(fixture)


def environment_unsafe_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    fixture = allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    runtime_apply_policy.environment_safety_requirement.environment_safe_for_apply = False
    runtime_apply_policy.environment_safety_requirement.write_mode_allowed = False
    runtime_apply_policy.environment_safety_requirement.satisfied = False
    runtime_apply_policy.environment_safety_requirement.blockers = [
        "blocked_by_environment_not_safe_for_apply"
    ]
    return _persist_policy(fixture)


def public_answer_key_exposure_forbidden_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return _wrap_fixture(
        _unsafe_policy_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def no_proposed_progress_updates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return _clear_progress_updates(
        allowed_minimal_progress_ledger_apply_fixture(
            tmp_path,
            user_id=user_id,
            repository=repository,
        )
    )


def allowed_minimal_progress_ledger_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return _set_allowed_policy(
        _wrap_fixture(
            _runtime_apply_not_allowed_now_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def idempotency_unsatisfied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return idempotency_requirement_unsatisfied_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def rollback_unsatisfied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return rollback_requirement_unsatisfied_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def audit_unsatisfied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return audit_requirement_unsatisfied_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def human_review_unsatisfied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return human_review_requirement_unsatisfied_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def allowed_policy_success_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def blocked_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return policy_feature_flag_disabled_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def applied_ledger_entries_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def idempotency_replay_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return idempotency_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def rollback_record_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def audit_trail_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def no_global_progress_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def no_existing_progress_aggregate_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def no_runtime_propagation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def no_leakage_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def user_scope_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    return allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def capture_minimal_progress_ledger_apply_source_snapshot(
    fixture: SimuladoMinimalProgressLedgerApplyFixture,
) -> MinimalProgressLedgerApplySourceSnapshot:
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    repository = fixture.context.repository
    user_id = fixture.context.user_id
    policy_snapshot = capture_runtime_apply_policy_source_snapshot(
        fixture.runtime_apply_policy_fixture
        if fixture.runtime_apply_policy_fixture is not None
        else _api_readonly_policy_fixture(
            repository.path.parent,
            user_id=user_id,
            repository=repository,
        )
    )
    stored_runtime_apply_policy = repository.get_simulado_runtime_apply_policy_by_id(
        runtime_apply_policy.runtime_apply_policy_id,
        user_id=user_id,
    )
    return MinimalProgressLedgerApplySourceSnapshot(
        final_event=policy_snapshot.final_event,
        controlled_execution=policy_snapshot.controlled_execution,
        execution_plan=policy_snapshot.execution_plan,
        execution_approval=policy_snapshot.execution_approval,
        execution_guardrail=policy_snapshot.execution_guardrail,
        runtime_apply_policy=(
            None
            if stored_runtime_apply_policy is None
            else stored_runtime_apply_policy.model_dump(mode="json")
        ),
        progress=repository.load_progress(user_id=user_id).model_dump(mode="json"),
        minimal_progress_ledger_apply_count=len(
            repository.list_user_simulado_minimal_progress_ledger_applies(user_id=user_id)
        ),
    )


def capture_minimal_apply_source_snapshot(
    fixture: SimuladoMinimalProgressLedgerApplyFixture,
) -> MinimalProgressLedgerApplySourceSnapshot:
    return capture_minimal_progress_ledger_apply_source_snapshot(fixture)


def mixed_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoMinimalProgressLedgerApplyFixture:
    fixture = allowed_minimal_progress_ledger_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    runtime_apply_policy = fixture.runtime_apply_policy
    assert runtime_apply_policy is not None
    runtime_apply_policy.idempotency_requirement.idempotency_key_present = False
    runtime_apply_policy.idempotency_requirement.idempotency_key_valid = False
    runtime_apply_policy.idempotency_requirement.satisfied = False
    runtime_apply_policy.idempotency_requirement.blockers = [
        "blocked_by_idempotency_requirement_unsatisfied"
    ]
    runtime_apply_policy.human_review_requirement.human_review_present = False
    runtime_apply_policy.human_review_requirement.satisfied = False
    runtime_apply_policy.human_review_requirement.blockers = [
        "blocked_by_human_review_requirement_unsatisfied"
    ]
    runtime_apply_policy.environment_safety_requirement.environment_safe_for_apply = False
    runtime_apply_policy.environment_safety_requirement.write_mode_allowed = False
    runtime_apply_policy.environment_safety_requirement.satisfied = False
    runtime_apply_policy.environment_safety_requirement.blockers = [
        "blocked_by_environment_not_safe_for_apply"
    ]
    _persist_policy(fixture)
    return _clear_progress_updates(fixture)


def stabilization_fixture_builders() -> dict[
    str,
    Callable[..., SimuladoMinimalProgressLedgerApplyFixture],
]:
    return {
        "missing_runtime_apply_policy": missing_runtime_apply_policy_fixture,
        "feature_flag_disabled": policy_feature_flag_disabled_fixture,
        "policy_feature_flag_disabled": policy_feature_flag_disabled_fixture,
        "runtime_apply_not_allowed_now": runtime_apply_not_allowed_now_fixture,
        "minimal_progress_ledger_scope_not_allowed": (
            minimal_progress_ledger_scope_not_allowed_fixture
        ),
        "idempotency_unsatisfied": idempotency_unsatisfied_fixture,
        "rollback_unsatisfied": rollback_unsatisfied_fixture,
        "audit_unsatisfied": audit_unsatisfied_fixture,
        "human_review_unsatisfied": human_review_unsatisfied_fixture,
        "environment_unsafe": environment_unsafe_fixture,
        "public_answer_key_exposure_forbidden": (
            public_answer_key_exposure_forbidden_fixture
        ),
        "no_proposed_progress_updates": no_proposed_progress_updates_fixture,
        "allowed_policy_success": allowed_policy_success_fixture,
        "blocked_apply": blocked_apply_fixture,
        "applied_ledger_entries_shape": applied_ledger_entries_shape_fixture,
        "idempotency_replay": idempotency_replay_fixture,
        "rollback_record_shape": rollback_record_shape_fixture,
        "audit_trail_shape": audit_trail_shape_fixture,
        "no_global_progress_mutation": no_global_progress_mutation_fixture,
        "no_existing_progress_aggregate_mutation": (
            no_existing_progress_aggregate_mutation_fixture
        ),
        "no_runtime_propagation": no_runtime_propagation_fixture,
        "no_leakage": no_leakage_fixture,
        "user_scope": user_scope_fixture,
        "api_readonly": api_readonly_fixture,
        "mixed_apply": mixed_apply_fixture,
    }
