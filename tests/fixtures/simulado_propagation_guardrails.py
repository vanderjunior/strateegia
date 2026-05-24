from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoAppliedEventLedger,
    SimuladoPropagationGuardrail,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_applied_event_ledger import SimuladoAppliedEventLedgerService
from app.services.simulado_propagation_guardrail import SimuladoPropagationGuardrailService
from tests.fixtures.simulado_applied_event_ledgers import (
    AppliedEventLedgerSourceSnapshot,
    SimuladoAppliedEventLedgerFixture,
    blocked_source_apply_fixture as _blocked_source_apply_fixture,
    capture_applied_event_ledger_source_snapshot,
    invalid_idempotency_fixture as _invalid_idempotency_fixture,
    no_source_applied_entries_fixture as _no_source_applied_entries_fixture,
    successful_source_apply_fixture as _successful_source_apply_fixture,
    unsafe_public_exposure_fixture as _unsafe_public_exposure_fixture,
)


@dataclass
class SimuladoPropagationGuardrailFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoPropagationGuardrailService
    user_id: str


@dataclass
class SimuladoPropagationGuardrailFixture:
    context: SimuladoPropagationGuardrailFixtureContext
    applied_event_ledger_fixture: SimuladoAppliedEventLedgerFixture | None
    applied_event_ledger: SimuladoAppliedEventLedger | None
    missing_applied_event_ledger_id: str | None = None


@dataclass(frozen=True)
class PropagationGuardrailSourceSnapshot:
    applied_event_ledger: dict[str, object] | None
    minimal_apply: dict[str, object] | None
    runtime_apply_policy: dict[str, object] | None
    final_event: dict[str, object] | None
    controlled_execution: dict[str, object] | None
    execution_plan: dict[str, object] | None
    progress: dict[str, object]
    applied_event_ledger_count: int
    propagation_guardrail_count: int


def _wrap_fixture(
    applied_event_ledger_fixture: SimuladoAppliedEventLedgerFixture,
) -> SimuladoPropagationGuardrailFixture:
    service = SimuladoAppliedEventLedgerService(applied_event_ledger_fixture.context.repository)
    minimal_apply = applied_event_ledger_fixture.minimal_apply
    assert minimal_apply is not None
    applied_event_ledger = service.build_applied_event_ledger(
        minimal_apply.minimal_progress_ledger_apply_id,
        user_id=applied_event_ledger_fixture.context.user_id,
    )
    assert applied_event_ledger is not None
    return SimuladoPropagationGuardrailFixture(
        context=SimuladoPropagationGuardrailFixtureContext(
            repository=applied_event_ledger_fixture.context.repository,
            service=SimuladoPropagationGuardrailService(
                applied_event_ledger_fixture.context.repository
            ),
            user_id=applied_event_ledger_fixture.context.user_id,
        ),
        applied_event_ledger_fixture=applied_event_ledger_fixture,
        applied_event_ledger=applied_event_ledger,
    )


def _persist_applied_event_ledger(
    fixture: SimuladoPropagationGuardrailFixture,
) -> SimuladoPropagationGuardrailFixture:
    applied_event_ledger = fixture.applied_event_ledger
    assert applied_event_ledger is not None
    fixture.context.repository.save_simulado_applied_event_ledger(
        applied_event_ledger,
        user_id=fixture.context.user_id,
    )
    return fixture


def _mark_source_not_replay_safe(
    fixture: SimuladoPropagationGuardrailFixture,
) -> SimuladoPropagationGuardrailFixture:
    ledger = fixture.applied_event_ledger
    assert ledger is not None
    ledger.replay_safe = False
    ledger.replay_returns_existing_ledger = False
    ledger.ledger_summary.replay_safe = False
    ledger.replay_safety_record.replay_safe = False
    ledger.replay_safety_record.replay_returns_existing_ledger = False
    ledger.replay_safety_record.same_source_same_key_idempotent = False
    return _persist_applied_event_ledger(fixture)


def _mark_source_missing_deduplication(
    fixture: SimuladoPropagationGuardrailFixture,
) -> SimuladoPropagationGuardrailFixture:
    ledger = fixture.applied_event_ledger
    assert ledger is not None
    ledger.deduplication_enforced = False
    ledger.ledger_summary.deduplication_enforced = False
    ledger.deduplication_record.deduplication_enforced = False
    return _persist_applied_event_ledger(fixture)


def _clear_source_event_records_keep_recorded(
    fixture: SimuladoPropagationGuardrailFixture,
) -> SimuladoPropagationGuardrailFixture:
    ledger = fixture.applied_event_ledger
    assert ledger is not None
    ledger.ledger_event_recorded = True
    ledger.ledger_event_count = 0
    ledger.applied_event_records = []
    ledger.ledger_status = "ledger_recorded"
    ledger.readiness_state = "applied_event_ledger_recorded"
    ledger.ledger_summary.ledger_event_count = 0
    return _persist_applied_event_ledger(fixture)


def _mark_source_propagation_state_unsafe(
    fixture: SimuladoPropagationGuardrailFixture,
) -> SimuladoPropagationGuardrailFixture:
    ledger = fixture.applied_event_ledger
    assert ledger is not None
    ledger.no_propagation = False
    return _persist_applied_event_ledger(fixture)


def _mark_final_event_globally_applied(
    fixture: SimuladoPropagationGuardrailFixture,
) -> SimuladoPropagationGuardrailFixture:
    ledger = fixture.applied_event_ledger
    assert ledger is not None
    ledger.final_event_applied_globally = True
    return _persist_applied_event_ledger(fixture)


def _mark_source_progress_mutation_detected(
    fixture: SimuladoPropagationGuardrailFixture,
) -> SimuladoPropagationGuardrailFixture:
    ledger = fixture.applied_event_ledger
    assert ledger is not None
    ledger.existing_progress_aggregate_mutated = True
    ledger.global_progress_mutation_applied = True
    ledger.no_existing_progress_aggregate_mutation = False
    ledger.no_global_progress_mutation = False
    return _persist_applied_event_ledger(fixture)


def _mark_unsafe_public_exposure(
    fixture: SimuladoPropagationGuardrailFixture,
) -> SimuladoPropagationGuardrailFixture:
    ledger = fixture.applied_event_ledger
    assert ledger is not None
    ledger.answer_key_publicly_exposed = True
    ledger.gabarito_publicly_exposed = True
    ledger.no_public_answer_key_exposure = False
    ledger.no_public_gabarito_exposure = False
    return _persist_applied_event_ledger(fixture)


def build_propagation_guardrail(
    fixture: SimuladoPropagationGuardrailFixture,
) -> SimuladoPropagationGuardrail | None:
    source_id = fixture.missing_applied_event_ledger_id
    if fixture.applied_event_ledger is not None:
        source_id = fixture.applied_event_ledger.applied_event_ledger_id
    assert source_id is not None
    return fixture.context.service.build_propagation_guardrail(
        source_applied_event_ledger_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_applied_event_ledger_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoPropagationGuardrailFixture:
    source_fixture = _blocked_source_apply_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    return SimuladoPropagationGuardrailFixture(
        context=SimuladoPropagationGuardrailFixtureContext(
            repository=source_fixture.context.repository,
            service=SimuladoPropagationGuardrailService(source_fixture.context.repository),
            user_id=user_id,
        ),
        applied_event_ledger_fixture=None,
        applied_event_ledger=None,
        missing_applied_event_ledger_id="simulado-applied-event-ledger:missing",
    )


def blocked_source_ledger_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoPropagationGuardrailFixture:
    return _wrap_fixture(
        _blocked_source_apply_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def zero_source_event_records_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoPropagationGuardrailFixture:
    return _clear_source_event_records_keep_recorded(
        _wrap_fixture(
            _successful_source_apply_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def source_ledger_not_replay_safe_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoPropagationGuardrailFixture:
    return _mark_source_not_replay_safe(
        _wrap_fixture(
            _successful_source_apply_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def source_ledger_missing_deduplication_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoPropagationGuardrailFixture:
    return _mark_source_missing_deduplication(
        _wrap_fixture(
            _successful_source_apply_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def source_ledger_propagation_state_unsafe_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoPropagationGuardrailFixture:
    return _mark_source_propagation_state_unsafe(
        _wrap_fixture(
            _successful_source_apply_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def final_event_globally_applied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoPropagationGuardrailFixture:
    return _mark_final_event_globally_applied(
        _wrap_fixture(
            _successful_source_apply_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def source_progress_mutation_detected_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoPropagationGuardrailFixture:
    return _mark_source_progress_mutation_detected(
        _wrap_fixture(
            _successful_source_apply_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def unsafe_public_exposure_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoPropagationGuardrailFixture:
    return _mark_unsafe_public_exposure(
        _wrap_fixture(
            _unsafe_public_exposure_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def successful_source_ledger_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoPropagationGuardrailFixture:
    return _wrap_fixture(
        _successful_source_apply_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def invalid_idempotency_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoPropagationGuardrailFixture:
    return _wrap_fixture(
        _invalid_idempotency_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def capture_propagation_guardrail_source_snapshot(
    fixture: SimuladoPropagationGuardrailFixture,
) -> PropagationGuardrailSourceSnapshot:
    applied_event_ledger = fixture.applied_event_ledger
    assert applied_event_ledger is not None
    repository = fixture.context.repository
    user_id = fixture.context.user_id
    source_snapshot: AppliedEventLedgerSourceSnapshot = capture_applied_event_ledger_source_snapshot(
        fixture.applied_event_ledger_fixture
        if fixture.applied_event_ledger_fixture is not None
        else _wrap_fixture(
            _successful_source_apply_fixture(repository.path.parent, user_id=user_id, repository=repository)
        ).applied_event_ledger_fixture  # type: ignore[arg-type]
    )
    stored_ledger = repository.get_simulado_applied_event_ledger_by_id(
        applied_event_ledger.applied_event_ledger_id,
        user_id=user_id,
    )
    return PropagationGuardrailSourceSnapshot(
        applied_event_ledger=(
            None if stored_ledger is None else stored_ledger.model_dump(mode="json")
        ),
        minimal_apply=source_snapshot.minimal_apply,
        runtime_apply_policy=source_snapshot.runtime_apply_policy,
        final_event=source_snapshot.final_event,
        controlled_execution=source_snapshot.controlled_execution,
        execution_plan=source_snapshot.execution_plan,
        progress=repository.load_progress(user_id=user_id).model_dump(mode="json"),
        applied_event_ledger_count=source_snapshot.applied_event_ledger_count,
        propagation_guardrail_count=len(
            repository.list_user_simulado_propagation_guardrails(user_id=user_id)
        ),
    )
