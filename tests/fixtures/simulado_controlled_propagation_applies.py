from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.domain.models import (
    SimuladoControlledPropagationApply,
    SimuladoPropagationGuardrail,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_propagation_apply import (
    SimuladoControlledPropagationApplyService,
)
from app.services.simulado_propagation_guardrail import SimuladoPropagationGuardrailService
from tests.fixtures.simulado_propagation_guardrails import (
    PropagationGuardrailSourceSnapshot,
    SimuladoPropagationGuardrailFixture,
    blocked_source_ledger_fixture as _blocked_source_ledger_fixture,
    build_propagation_guardrail,
    capture_propagation_guardrail_source_snapshot as _capture_propagation_guardrail_source_snapshot,
    successful_source_ledger_fixture as _successful_source_ledger_fixture,
    unsafe_public_exposure_fixture as _unsafe_public_exposure_fixture,
)


@dataclass
class SimuladoControlledPropagationApplyFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoControlledPropagationApplyService
    user_id: str


@dataclass
class SimuladoControlledPropagationApplyFixture:
    context: SimuladoControlledPropagationApplyFixtureContext
    propagation_guardrail_fixture: SimuladoPropagationGuardrailFixture | None
    propagation_guardrail: SimuladoPropagationGuardrail | None
    missing_propagation_guardrail_id: str | None = None


@dataclass(frozen=True)
class ControlledPropagationApplySourceSnapshot:
    propagation_guardrail: dict[str, object] | None
    applied_event_ledger: dict[str, object] | None
    minimal_apply: dict[str, object] | None
    runtime_apply_policy: dict[str, object] | None
    final_event: dict[str, object] | None
    controlled_execution: dict[str, object] | None
    execution_plan: dict[str, object] | None
    progress: dict[str, object]
    propagation_guardrail_count: int
    controlled_propagation_apply_count: int


def _wrap_fixture(
    propagation_guardrail_fixture: SimuladoPropagationGuardrailFixture,
) -> SimuladoControlledPropagationApplyFixture:
    guardrail = build_propagation_guardrail(propagation_guardrail_fixture)
    assert guardrail is not None
    return SimuladoControlledPropagationApplyFixture(
        context=SimuladoControlledPropagationApplyFixtureContext(
            repository=propagation_guardrail_fixture.context.repository,
            service=SimuladoControlledPropagationApplyService(
                propagation_guardrail_fixture.context.repository
            ),
            user_id=propagation_guardrail_fixture.context.user_id,
        ),
        propagation_guardrail_fixture=propagation_guardrail_fixture,
        propagation_guardrail=guardrail,
    )


def _persist_guardrail(
    fixture: SimuladoControlledPropagationApplyFixture,
) -> SimuladoControlledPropagationApplyFixture:
    guardrail = fixture.propagation_guardrail
    assert guardrail is not None
    fixture.context.repository.save_simulado_propagation_guardrail(
        guardrail,
        user_id=fixture.context.user_id,
    )
    return fixture


def _mark_source_guardrail_state_unsafe(
    fixture: SimuladoControlledPropagationApplyFixture,
) -> SimuladoControlledPropagationApplyFixture:
    guardrail = fixture.propagation_guardrail
    assert guardrail is not None
    guardrail.propagation_allowed_now = True
    guardrail.propagation_applied = True
    return _persist_guardrail(fixture)


def _clear_candidate_targets(
    fixture: SimuladoControlledPropagationApplyFixture,
) -> SimuladoControlledPropagationApplyFixture:
    guardrail = fixture.propagation_guardrail
    assert guardrail is not None
    guardrail.candidate_ranking_targets = []
    guardrail.candidate_retention_targets = []
    guardrail.candidate_scheduler_targets = []
    guardrail.candidate_study_cycle_targets = []
    guardrail.candidate_curriculum_graph_targets = []
    guardrail.candidate_adaptive_tuning_targets = []
    guardrail.readiness_summary.ranking_candidate_count = 0
    guardrail.readiness_summary.retention_candidate_count = 0
    guardrail.readiness_summary.scheduler_candidate_count = 0
    guardrail.readiness_summary.study_cycle_candidate_count = 0
    guardrail.readiness_summary.curriculum_graph_candidate_count = 0
    guardrail.readiness_summary.adaptive_tuning_candidate_count = 0
    guardrail.surface_risk_summary.candidate_surface_count = 0
    guardrail.surface_risk_summary.ranking_candidate_count = 0
    guardrail.surface_risk_summary.retention_candidate_count = 0
    guardrail.surface_risk_summary.scheduler_candidate_count = 0
    guardrail.surface_risk_summary.study_cycle_candidate_count = 0
    guardrail.surface_risk_summary.curriculum_graph_candidate_count = 0
    guardrail.surface_risk_summary.adaptive_tuning_candidate_count = 0
    return _persist_guardrail(fixture)


def _mark_unsafe_public_exposure(
    fixture: SimuladoControlledPropagationApplyFixture,
) -> SimuladoControlledPropagationApplyFixture:
    guardrail = fixture.propagation_guardrail
    assert guardrail is not None
    guardrail.answer_key_publicly_exposed = True
    guardrail.gabarito_publicly_exposed = True
    guardrail.no_public_answer_key_exposure = False
    guardrail.no_public_gabarito_exposure = False
    return _persist_guardrail(fixture)


def _mark_idempotency_requirement_unsatisfied(
    fixture: SimuladoControlledPropagationApplyFixture,
) -> SimuladoControlledPropagationApplyFixture:
    guardrail = fixture.propagation_guardrail
    assert guardrail is not None
    guardrail.metadata["controlled_propagation_apply_idempotency_unsatisfied"] = True
    return _persist_guardrail(fixture)


def _mark_rollback_requirement_unsatisfied(
    fixture: SimuladoControlledPropagationApplyFixture,
) -> SimuladoControlledPropagationApplyFixture:
    guardrail = fixture.propagation_guardrail
    assert guardrail is not None
    guardrail.metadata["controlled_propagation_apply_rollback_unsatisfied"] = True
    return _persist_guardrail(fixture)


def build_controlled_propagation_apply(
    fixture: SimuladoControlledPropagationApplyFixture,
) -> SimuladoControlledPropagationApply | None:
    source_id = fixture.missing_propagation_guardrail_id
    if fixture.propagation_guardrail is not None:
        source_id = fixture.propagation_guardrail.propagation_guardrail_id
    assert source_id is not None
    return fixture.context.service.build_controlled_propagation_apply(
        source_propagation_guardrail_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_propagation_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    source_fixture = _blocked_source_ledger_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    return SimuladoControlledPropagationApplyFixture(
        context=SimuladoControlledPropagationApplyFixtureContext(
            repository=source_fixture.context.repository,
            service=SimuladoControlledPropagationApplyService(
                source_fixture.context.repository
            ),
            user_id=user_id,
        ),
        propagation_guardrail_fixture=None,
        propagation_guardrail=None,
        missing_propagation_guardrail_id="simulado-propagation-guardrail:missing",
    )


def source_guardrail_blocked_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return _wrap_fixture(
        _blocked_source_ledger_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def source_guardrail_not_ready_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return source_guardrail_blocked_fixture(tmp_path, user_id=user_id, repository=repository)


def source_guardrail_unsafe_state_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return _mark_source_guardrail_state_unsafe(
        _wrap_fixture(
            _successful_source_ledger_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def source_guardrail_state_unsafe_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return source_guardrail_unsafe_state_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def source_guardrail_not_ready_for_future_review_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return source_guardrail_not_ready_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def no_candidate_targets_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return _clear_candidate_targets(
        _wrap_fixture(
            _successful_source_ledger_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def source_guardrail_no_candidate_targets_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return no_candidate_targets_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def unsafe_public_exposure_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return _mark_unsafe_public_exposure(
        _wrap_fixture(
            _unsafe_public_exposure_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def source_guardrail_public_exposure_forbidden_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return unsafe_public_exposure_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def successful_source_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return _wrap_fixture(
        _successful_source_ledger_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def safe_source_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return successful_source_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def controlled_entry_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return safe_source_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def controlled_propagation_entries_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return controlled_entry_shape_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def idempotency_record_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return safe_source_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def replay_behavior_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return idempotency_replay_fixture(tmp_path, user_id=user_id, repository=repository)


def rollback_record_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return safe_source_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_trail_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return safe_source_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def no_direct_runtime_propagation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return safe_source_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def ledger_only_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return no_direct_runtime_propagation_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def no_runtime_surface_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return no_direct_runtime_propagation_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def no_runtime_update_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return safe_source_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def no_ranking_update_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return no_runtime_update_fixture(tmp_path, user_id=user_id, repository=repository)


def no_retention_update_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return no_runtime_update_fixture(tmp_path, user_id=user_id, repository=repository)


def no_scheduler_update_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return no_runtime_update_fixture(tmp_path, user_id=user_id, repository=repository)


def no_study_cycle_update_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return no_runtime_update_fixture(tmp_path, user_id=user_id, repository=repository)


def no_curriculum_graph_update_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return no_runtime_update_fixture(tmp_path, user_id=user_id, repository=repository)


def no_adaptive_tuning_update_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return no_runtime_update_fixture(tmp_path, user_id=user_id, repository=repository)


def no_new_progress_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return no_direct_runtime_propagation_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def no_global_progress_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return no_direct_runtime_propagation_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )


def no_leakage_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return safe_source_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def idempotency_replay_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return safe_source_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def idempotency_requirement_unsatisfied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return _mark_idempotency_requirement_unsatisfied(
        _wrap_fixture(
            _successful_source_ledger_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def rollback_requirement_unsatisfied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return _mark_rollback_requirement_unsatisfied(
        _wrap_fixture(
            _successful_source_ledger_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def user_scope_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return safe_source_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledPropagationApplyFixture:
    return safe_source_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def mixed_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> dict[str, SimuladoControlledPropagationApplyFixture]:
    return {
        "blocked": source_guardrail_blocked_fixture(
            tmp_path / "blocked",
            user_id=user_id,
            repository=repository,
        ),
        "safe": safe_source_guardrail_fixture(
            tmp_path / "safe",
            user_id=user_id,
            repository=repository,
        ),
        "unsafe_state": source_guardrail_unsafe_state_fixture(
            tmp_path / "unsafe-state",
            user_id=user_id,
            repository=repository,
        ),
    }


def mixed_controlled_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> dict[str, SimuladoControlledPropagationApplyFixture]:
    return mixed_apply_fixture(tmp_path, user_id=user_id, repository=repository)


def capture_controlled_propagation_apply_source_snapshot(
    fixture: SimuladoControlledPropagationApplyFixture,
) -> ControlledPropagationApplySourceSnapshot:
    repository = fixture.context.repository
    user_id = fixture.context.user_id
    guardrail = fixture.propagation_guardrail
    propagation_guardrail = None
    applied_event_ledger = None
    minimal_apply = None
    runtime_apply_policy = None
    final_event = None
    controlled_execution = None
    execution_plan = None
    if guardrail is not None:
        propagation_guardrail_model = repository.get_simulado_propagation_guardrail_by_id(
            guardrail.propagation_guardrail_id,
            user_id=user_id,
        )
        if propagation_guardrail_model is not None:
            propagation_guardrail = propagation_guardrail_model.model_dump(mode="json")
        applied_event_ledger_model = repository.get_simulado_applied_event_ledger_by_id(
            guardrail.source_applied_event_ledger_id,
            user_id=user_id,
        )
        if applied_event_ledger_model is not None:
            applied_event_ledger = applied_event_ledger_model.model_dump(mode="json")
        minimal_apply_model = repository.get_simulado_minimal_progress_ledger_apply_by_id(
            guardrail.source_minimal_progress_ledger_apply_id,
            user_id=user_id,
        )
        if minimal_apply_model is not None:
            minimal_apply = minimal_apply_model.model_dump(mode="json")
        runtime_apply_policy_model = repository.get_simulado_runtime_apply_policy_by_id(
            guardrail.source_runtime_apply_policy_id,
            user_id=user_id,
        )
        if runtime_apply_policy_model is not None:
            runtime_apply_policy = runtime_apply_policy_model.model_dump(mode="json")
        final_event_model = repository.get_simulado_final_pedagogical_update_event_by_id(
            guardrail.source_final_event_id,
            user_id=user_id,
        )
        if final_event_model is not None:
            final_event = final_event_model.model_dump(mode="json")
        controlled_execution_model = (
            repository.get_simulado_controlled_runtime_commit_execution_by_id(
                guardrail.source_controlled_execution_id,
                user_id=user_id,
            )
        )
        if controlled_execution_model is not None:
            controlled_execution = controlled_execution_model.model_dump(mode="json")
        execution_plan_model = repository.get_simulado_runtime_commit_execution_plan_by_id(
            guardrail.source_execution_plan_id,
            user_id=user_id,
        )
        if execution_plan_model is not None:
            execution_plan = execution_plan_model.model_dump(mode="json")

    return ControlledPropagationApplySourceSnapshot(
        propagation_guardrail=propagation_guardrail,
        applied_event_ledger=applied_event_ledger,
        minimal_apply=minimal_apply,
        runtime_apply_policy=runtime_apply_policy,
        final_event=final_event,
        controlled_execution=controlled_execution,
        execution_plan=execution_plan,
        progress=repository.load_progress(user_id=user_id).model_dump(mode="json"),
        propagation_guardrail_count=len(
            repository.list_user_simulado_propagation_guardrails(user_id=user_id)
        ),
        controlled_propagation_apply_count=len(
            repository.list_user_simulado_controlled_propagation_applies(user_id=user_id)
        ),
    )


def capture_propagation_guardrail_source_snapshot(
    fixture: SimuladoControlledPropagationApplyFixture,
) -> PropagationGuardrailSourceSnapshot:
    guardrail_fixture = fixture.propagation_guardrail_fixture
    assert guardrail_fixture is not None
    return _capture_propagation_guardrail_source_snapshot(guardrail_fixture)


def stabilization_fixture_builders() -> dict[str, Callable[..., object]]:
    return {
        "missing_propagation_guardrail_fixture": missing_propagation_guardrail_fixture,
        "source_guardrail_blocked_fixture": source_guardrail_blocked_fixture,
        "source_guardrail_not_ready_fixture": source_guardrail_not_ready_fixture,
        "source_guardrail_state_unsafe_fixture": source_guardrail_state_unsafe_fixture,
        "source_guardrail_not_ready_for_future_review_fixture": (
            source_guardrail_not_ready_for_future_review_fixture
        ),
        "source_guardrail_no_candidate_targets_fixture": (
            source_guardrail_no_candidate_targets_fixture
        ),
        "source_guardrail_public_exposure_forbidden_fixture": (
            source_guardrail_public_exposure_forbidden_fixture
        ),
        "source_guardrail_unsafe_state_fixture": source_guardrail_unsafe_state_fixture,
        "no_candidate_targets_fixture": no_candidate_targets_fixture,
        "idempotency_requirement_unsatisfied_fixture": (
            idempotency_requirement_unsatisfied_fixture
        ),
        "rollback_requirement_unsatisfied_fixture": (
            rollback_requirement_unsatisfied_fixture
        ),
        "unsafe_public_exposure_fixture": unsafe_public_exposure_fixture,
        "safe_source_guardrail_fixture": safe_source_guardrail_fixture,
        "controlled_entry_shape_fixture": controlled_entry_shape_fixture,
        "controlled_propagation_entries_shape_fixture": (
            controlled_propagation_entries_shape_fixture
        ),
        "idempotency_record_shape_fixture": idempotency_record_shape_fixture,
        "replay_behavior_fixture": replay_behavior_fixture,
        "rollback_record_shape_fixture": rollback_record_shape_fixture,
        "audit_trail_shape_fixture": audit_trail_shape_fixture,
        "ledger_only_apply_fixture": ledger_only_apply_fixture,
        "no_direct_runtime_propagation_fixture": no_direct_runtime_propagation_fixture,
        "no_runtime_surface_apply_fixture": no_runtime_surface_apply_fixture,
        "no_runtime_update_fixture": no_runtime_update_fixture,
        "no_ranking_update_fixture": no_ranking_update_fixture,
        "no_retention_update_fixture": no_retention_update_fixture,
        "no_scheduler_update_fixture": no_scheduler_update_fixture,
        "no_study_cycle_update_fixture": no_study_cycle_update_fixture,
        "no_curriculum_graph_update_fixture": no_curriculum_graph_update_fixture,
        "no_adaptive_tuning_update_fixture": no_adaptive_tuning_update_fixture,
        "no_new_progress_apply_fixture": no_new_progress_apply_fixture,
        "no_global_progress_mutation_fixture": no_global_progress_mutation_fixture,
        "no_leakage_fixture": no_leakage_fixture,
        "idempotency_replay_fixture": idempotency_replay_fixture,
        "user_scope_fixture": user_scope_fixture,
        "api_readonly_fixture": api_readonly_fixture,
        "mixed_apply_fixture": mixed_apply_fixture,
        "mixed_controlled_apply_fixture": mixed_controlled_apply_fixture,
    }
