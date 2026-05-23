from __future__ import annotations

from dataclasses import dataclass

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
