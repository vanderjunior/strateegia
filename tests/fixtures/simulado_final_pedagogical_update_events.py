from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from app.domain.models import (
    SimuladoControlledRuntimeCommitExecution,
    SimuladoFinalPedagogicalUpdateEvent,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_final_pedagogical_update_event import (
    SimuladoFinalPedagogicalUpdateEventService,
)
from tests.fixtures.simulado_controlled_runtime_commit_executions import (
    SimuladoControlledRuntimeCommitExecutionFixture,
    api_readonly_fixture as _api_readonly_fixture,
    build_controlled_runtime_commit_execution,
    execution_allowed_now_false_fixture as _execution_allowed_now_false_fixture,
    execution_disabled_fixture as _execution_disabled_fixture,
    mixed_controlled_execution_fixture as _mixed_controlled_execution_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    public_answer_key_exposure_forbidden_fixture as _unsafe_source_fixture,
)


@dataclass
class SimuladoFinalPedagogicalUpdateEventFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoFinalPedagogicalUpdateEventService
    user_id: str


@dataclass
class SimuladoFinalPedagogicalUpdateEventFixture:
    context: SimuladoFinalPedagogicalUpdateEventFixtureContext
    controlled_execution_fixture: SimuladoControlledRuntimeCommitExecutionFixture | None
    controlled_execution: SimuladoControlledRuntimeCommitExecution | None
    missing_controlled_execution_id: str | None = None


@dataclass(frozen=True)
class FinalPedagogicalUpdateEventSourceSnapshot:
    controlled_execution: dict[str, object] | None
    execution_plan: dict[str, object] | None
    execution_approval: dict[str, object] | None
    execution_guardrail: dict[str, object] | None
    progress: dict[str, object]
    final_event_count: int


def _wrap_fixture(
    controlled_execution_fixture: SimuladoControlledRuntimeCommitExecutionFixture,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    controlled_execution = build_controlled_runtime_commit_execution(controlled_execution_fixture)
    assert controlled_execution is not None
    return SimuladoFinalPedagogicalUpdateEventFixture(
        context=SimuladoFinalPedagogicalUpdateEventFixtureContext(
            repository=controlled_execution_fixture.context.repository,
            service=SimuladoFinalPedagogicalUpdateEventService(
                controlled_execution_fixture.context.repository
            ),
            user_id=controlled_execution_fixture.context.user_id,
        ),
        controlled_execution_fixture=controlled_execution_fixture,
        controlled_execution=controlled_execution,
    )


def _persist_controlled_execution(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    fixture.context.repository.save_simulado_controlled_runtime_commit_execution(
        controlled_execution,
        user_id=fixture.context.user_id,
    )
    return fixture


def _mark_not_dry_run(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    controlled_execution.execution_mode = "non_dry_run_execution"
    return _persist_controlled_execution(fixture)


def _mark_execution_started(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    controlled_execution.execution_started = True
    return _persist_controlled_execution(fixture)


def _mark_commit_executed(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    controlled_execution.commit_executed = True
    return _persist_controlled_execution(fixture)


def _mark_mutation_committed(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    controlled_execution.mutation_committed = True
    return _persist_controlled_execution(fixture)


def _mark_runtime_application_detected(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    controlled_execution.runtime_application_enabled = True
    controlled_execution.runtime_application_applied = True
    return _persist_controlled_execution(fixture)


def _mark_progress_mutation_detected(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    controlled_execution.progress_mutation_enabled = True
    controlled_execution.progress_mutation_applied = True
    return _persist_controlled_execution(fixture)


def _mark_final_event_apply_disabled(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    controlled_execution.metadata["final_event_apply_disabled"] = True
    return _persist_controlled_execution(fixture)


def _mark_unsafe_public_exposure(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    controlled_execution.answer_key_publicly_exposed = True
    controlled_execution.gabarito_publicly_exposed = True
    return _persist_controlled_execution(fixture)


def build_final_pedagogical_update_event(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> SimuladoFinalPedagogicalUpdateEvent | None:
    source_id = fixture.missing_controlled_execution_id
    if fixture.controlled_execution is not None:
        source_id = fixture.controlled_execution.controlled_execution_id
    assert source_id is not None
    return fixture.context.service.build_final_event(
        source_controlled_execution_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_controlled_execution_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    controlled_execution_fixture = _execution_allowed_now_false_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    return SimuladoFinalPedagogicalUpdateEventFixture(
        context=SimuladoFinalPedagogicalUpdateEventFixtureContext(
            repository=controlled_execution_fixture.context.repository,
            service=SimuladoFinalPedagogicalUpdateEventService(
                controlled_execution_fixture.context.repository
            ),
            user_id=user_id,
        ),
        controlled_execution_fixture=None,
        controlled_execution=None,
        missing_controlled_execution_id="simulado-controlled-execution:missing",
    )


def controlled_execution_not_dry_run_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _mark_not_dry_run(
        _wrap_fixture(
            _execution_allowed_now_false_fixture(
                tmp_path,
                user_id=user_id,
                repository=repository,
            )
        )
    )


def controlled_execution_started_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _mark_execution_started(
        _wrap_fixture(
            _execution_allowed_now_false_fixture(
                tmp_path,
                user_id=user_id,
                repository=repository,
            )
        )
    )


def commit_executed_detected_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _mark_commit_executed(
        _wrap_fixture(
            _execution_allowed_now_false_fixture(
                tmp_path,
                user_id=user_id,
                repository=repository,
            )
        )
    )


def mutation_committed_detected_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _mark_mutation_committed(
        _wrap_fixture(
            _execution_allowed_now_false_fixture(
                tmp_path,
                user_id=user_id,
                repository=repository,
            )
        )
    )


def runtime_application_detected_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _mark_runtime_application_detected(
        _wrap_fixture(
            _execution_allowed_now_false_fixture(
                tmp_path,
                user_id=user_id,
                repository=repository,
            )
        )
    )


def progress_mutation_detected_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _mark_progress_mutation_detected(
        _wrap_fixture(
            _execution_allowed_now_false_fixture(
                tmp_path,
                user_id=user_id,
                repository=repository,
            )
        )
    )


def final_event_apply_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _mark_final_event_apply_disabled(
        _wrap_fixture(
            _execution_allowed_now_false_fixture(
                tmp_path,
                user_id=user_id,
                repository=repository,
            )
        )
    )


def public_answer_key_exposure_forbidden_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _mark_unsafe_public_exposure(
        _wrap_fixture(_unsafe_source_fixture(tmp_path, user_id=user_id, repository=repository))
    )


def final_event_summary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _wrap_fixture(
        _api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def proposed_progress_updates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def proposed_ranking_updates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def proposed_retention_updates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def proposed_scheduler_updates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def proposed_study_cycle_updates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def proposed_curriculum_graph_updates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def proposed_adaptive_tuning_updates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def final_event_audit_trail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_application_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _wrap_fixture(
        _no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def user_scope_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return final_event_summary_fixture(tmp_path, user_id=user_id, repository=repository)


def mixed_final_event_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _wrap_fixture(
        _mixed_controlled_execution_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def execution_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalPedagogicalUpdateEventFixture:
    return _wrap_fixture(
        _execution_disabled_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def capture_final_event_source_snapshot(
    fixture: SimuladoFinalPedagogicalUpdateEventFixture,
) -> FinalPedagogicalUpdateEventSourceSnapshot:
    controlled_execution = fixture.controlled_execution
    assert controlled_execution is not None
    repository = fixture.context.repository
    user_id = fixture.context.user_id

    stored_controlled_execution = repository.get_simulado_controlled_runtime_commit_execution_by_id(
        controlled_execution.controlled_execution_id,
        user_id=user_id,
    )
    stored_execution_plan = repository.get_simulado_runtime_commit_execution_plan_by_id(
        controlled_execution.source_execution_plan_id,
        user_id=user_id,
    )
    stored_execution_approval = repository.get_simulado_explicit_commit_execution_approval_by_id(
        controlled_execution.source_execution_approval_id,
        user_id=user_id,
    )
    stored_execution_guardrail = repository.get_simulado_controlled_commit_execution_guardrail_by_id(
        controlled_execution.source_execution_guardrail_id,
        user_id=user_id,
    )

    return FinalPedagogicalUpdateEventSourceSnapshot(
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
        final_event_count=len(
            repository.list_user_simulado_final_pedagogical_update_events(user_id=user_id)
        ),
    )


def stabilization_fixture_builders() -> dict[
    str,
    Callable[..., SimuladoFinalPedagogicalUpdateEventFixture],
]:
    return {
        "missing_controlled_execution": missing_controlled_execution_fixture,
        "controlled_execution_not_dry_run": controlled_execution_not_dry_run_fixture,
        "controlled_execution_started": controlled_execution_started_fixture,
        "commit_executed_detected": commit_executed_detected_fixture,
        "mutation_committed_detected": mutation_committed_detected_fixture,
        "runtime_application_detected": runtime_application_detected_fixture,
        "progress_mutation_detected": progress_mutation_detected_fixture,
        "final_event_apply_disabled": final_event_apply_disabled_fixture,
        "public_answer_key_exposure_forbidden": (
            public_answer_key_exposure_forbidden_fixture
        ),
        "final_event_summary": final_event_summary_fixture,
        "proposed_progress_updates": proposed_progress_updates_fixture,
        "proposed_ranking_updates": proposed_ranking_updates_fixture,
        "proposed_retention_updates": proposed_retention_updates_fixture,
        "proposed_scheduler_updates": proposed_scheduler_updates_fixture,
        "proposed_study_cycle_updates": proposed_study_cycle_updates_fixture,
        "proposed_curriculum_graph_updates": proposed_curriculum_graph_updates_fixture,
        "proposed_adaptive_tuning_updates": proposed_adaptive_tuning_updates_fixture,
        "final_event_audit_trail": final_event_audit_trail_fixture,
        "no_public_key_gabarito_safety": no_public_key_gabarito_safety_fixture,
        "no_runtime_application": no_runtime_application_fixture,
        "no_runtime_mutation": no_runtime_mutation_fixture,
        "idempotency": idempotency_fixture,
        "api_readonly": api_readonly_fixture,
        "user_scope": user_scope_fixture,
        "mixed_final_event": mixed_final_event_fixture,
        "execution_disabled": execution_disabled_fixture,
    }
