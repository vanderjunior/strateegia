from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoAppliedEventLedger,
    SimuladoMinimalProgressLedgerApply,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_applied_event_ledger import SimuladoAppliedEventLedgerService
from tests.fixtures.simulado_minimal_progress_ledger_applies import (
    SimuladoMinimalProgressLedgerApplyFixture,
    allowed_minimal_progress_ledger_apply_fixture as _allowed_apply_fixture,
    build_minimal_progress_ledger_apply,
    capture_minimal_progress_ledger_apply_source_snapshot,
    policy_feature_flag_disabled_fixture as _blocked_apply_source_fixture,
)


@dataclass
class SimuladoAppliedEventLedgerFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoAppliedEventLedgerService
    user_id: str


@dataclass
class SimuladoAppliedEventLedgerFixture:
    context: SimuladoAppliedEventLedgerFixtureContext
    minimal_apply_fixture: SimuladoMinimalProgressLedgerApplyFixture | None
    minimal_apply: SimuladoMinimalProgressLedgerApply | None
    missing_minimal_apply_id: str | None = None


@dataclass(frozen=True)
class AppliedEventLedgerSourceSnapshot:
    minimal_apply: dict[str, object] | None
    runtime_apply_policy: dict[str, object] | None
    final_event: dict[str, object] | None
    controlled_execution: dict[str, object] | None
    execution_plan: dict[str, object] | None
    progress: dict[str, object]
    minimal_progress_ledger_apply_count: int
    applied_event_ledger_count: int


def _wrap_fixture(
    minimal_apply_fixture: SimuladoMinimalProgressLedgerApplyFixture,
) -> SimuladoAppliedEventLedgerFixture:
    minimal_apply = build_minimal_progress_ledger_apply(minimal_apply_fixture)
    assert minimal_apply is not None
    return SimuladoAppliedEventLedgerFixture(
        context=SimuladoAppliedEventLedgerFixtureContext(
            repository=minimal_apply_fixture.context.repository,
            service=SimuladoAppliedEventLedgerService(minimal_apply_fixture.context.repository),
            user_id=minimal_apply_fixture.context.user_id,
        ),
        minimal_apply_fixture=minimal_apply_fixture,
        minimal_apply=minimal_apply,
    )


def _persist_minimal_apply(
    fixture: SimuladoAppliedEventLedgerFixture,
) -> SimuladoAppliedEventLedgerFixture:
    minimal_apply = fixture.minimal_apply
    assert minimal_apply is not None
    fixture.context.repository.save_simulado_minimal_progress_ledger_apply(
        minimal_apply,
        user_id=fixture.context.user_id,
    )
    return fixture


def _mark_source_not_applied(
    fixture: SimuladoAppliedEventLedgerFixture,
) -> SimuladoAppliedEventLedgerFixture:
    minimal_apply = fixture.minimal_apply
    assert minimal_apply is not None
    minimal_apply.apply_status = "apply_blocked"
    minimal_apply.readiness_state = "blocked_by_policy_feature_flag_disabled"
    minimal_apply.minimal_progress_ledger_apply_allowed = False
    minimal_apply.minimal_progress_ledger_apply_applied = False
    minimal_apply.applied_progress_ledger_entry_created = False
    minimal_apply.applied_progress_ledger_entry_count = 0
    minimal_apply.applied_ledger_entries = []
    minimal_apply.final_event_applied_to_minimal_ledger = False
    minimal_apply.idempotency_record.satisfied = False
    return _persist_minimal_apply(fixture)


def _clear_applied_entries(
    fixture: SimuladoAppliedEventLedgerFixture,
) -> SimuladoAppliedEventLedgerFixture:
    minimal_apply = fixture.minimal_apply
    assert minimal_apply is not None
    minimal_apply.applied_progress_ledger_entry_created = False
    minimal_apply.applied_progress_ledger_entry_count = 0
    minimal_apply.applied_ledger_entries = []
    return _persist_minimal_apply(fixture)


def _mark_missing_idempotency(
    fixture: SimuladoAppliedEventLedgerFixture,
) -> SimuladoAppliedEventLedgerFixture:
    minimal_apply = fixture.minimal_apply
    assert minimal_apply is not None
    minimal_apply.idempotency_key_required = True
    minimal_apply.idempotency_key_present = False
    minimal_apply.idempotency_key_valid = False
    minimal_apply.idempotency_key = None
    minimal_apply.idempotency_key_recorded = False
    minimal_apply.idempotency_record.idempotency_key_required = True
    minimal_apply.idempotency_record.idempotency_key_present = False
    minimal_apply.idempotency_record.idempotency_key_valid = False
    minimal_apply.idempotency_record.idempotency_key = None
    minimal_apply.idempotency_record.satisfied = False
    return _persist_minimal_apply(fixture)


def _mark_invalid_idempotency(
    fixture: SimuladoAppliedEventLedgerFixture,
) -> SimuladoAppliedEventLedgerFixture:
    minimal_apply = fixture.minimal_apply
    assert minimal_apply is not None
    minimal_apply.idempotency_key_required = True
    minimal_apply.idempotency_key_present = True
    minimal_apply.idempotency_key_valid = False
    minimal_apply.idempotency_key_recorded = False
    minimal_apply.idempotency_record.idempotency_key_required = True
    minimal_apply.idempotency_record.idempotency_key_present = True
    minimal_apply.idempotency_record.idempotency_key_valid = False
    minimal_apply.idempotency_record.satisfied = False
    return _persist_minimal_apply(fixture)


def _mark_unsafe_public_exposure(
    fixture: SimuladoAppliedEventLedgerFixture,
) -> SimuladoAppliedEventLedgerFixture:
    minimal_apply = fixture.minimal_apply
    assert minimal_apply is not None
    minimal_apply.answer_key_publicly_exposed = True
    minimal_apply.gabarito_publicly_exposed = True
    minimal_apply.no_public_answer_key_exposure = False
    minimal_apply.no_public_gabarito_exposure = False
    return _persist_minimal_apply(fixture)


def build_applied_event_ledger(
    fixture: SimuladoAppliedEventLedgerFixture,
) -> SimuladoAppliedEventLedger | None:
    source_id = fixture.missing_minimal_apply_id
    if fixture.minimal_apply is not None:
        source_id = fixture.minimal_apply.minimal_progress_ledger_apply_id
    assert source_id is not None
    return fixture.context.service.build_applied_event_ledger(
        source_minimal_progress_ledger_apply_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_minimal_progress_ledger_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAppliedEventLedgerFixture:
    minimal_apply_fixture = _blocked_apply_source_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    return SimuladoAppliedEventLedgerFixture(
        context=SimuladoAppliedEventLedgerFixtureContext(
            repository=minimal_apply_fixture.context.repository,
            service=SimuladoAppliedEventLedgerService(minimal_apply_fixture.context.repository),
            user_id=user_id,
        ),
        minimal_apply_fixture=None,
        minimal_apply=None,
        missing_minimal_apply_id="simulado-minimal-progress-ledger-apply:missing",
    )


def blocked_source_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAppliedEventLedgerFixture:
    return _mark_source_not_applied(
        _wrap_fixture(
            _blocked_apply_source_fixture(tmp_path, user_id=user_id, repository=repository)
        )
    )


def no_source_applied_entries_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAppliedEventLedgerFixture:
    return _clear_applied_entries(
        _wrap_fixture(_allowed_apply_fixture(tmp_path, user_id=user_id, repository=repository))
    )


def missing_idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAppliedEventLedgerFixture:
    return _mark_missing_idempotency(
        _wrap_fixture(_allowed_apply_fixture(tmp_path, user_id=user_id, repository=repository))
    )


def invalid_idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAppliedEventLedgerFixture:
    return _mark_invalid_idempotency(
        _wrap_fixture(_allowed_apply_fixture(tmp_path, user_id=user_id, repository=repository))
    )


def unsafe_public_exposure_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAppliedEventLedgerFixture:
    return _mark_unsafe_public_exposure(
        _wrap_fixture(_allowed_apply_fixture(tmp_path, user_id=user_id, repository=repository))
    )


def successful_source_apply_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAppliedEventLedgerFixture:
    return _wrap_fixture(_allowed_apply_fixture(tmp_path, user_id=user_id, repository=repository))


def idempotency_replay_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAppliedEventLedgerFixture:
    return successful_source_apply_fixture(tmp_path, user_id=user_id, repository=repository)


def user_scope_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAppliedEventLedgerFixture:
    return successful_source_apply_fixture(tmp_path, user_id=user_id, repository=repository)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAppliedEventLedgerFixture:
    return successful_source_apply_fixture(tmp_path, user_id=user_id, repository=repository)


def capture_applied_event_ledger_source_snapshot(
    fixture: SimuladoAppliedEventLedgerFixture,
) -> AppliedEventLedgerSourceSnapshot:
    minimal_apply = fixture.minimal_apply
    assert minimal_apply is not None
    repository = fixture.context.repository
    user_id = fixture.context.user_id
    minimal_snapshot = capture_minimal_progress_ledger_apply_source_snapshot(
        fixture.minimal_apply_fixture
        if fixture.minimal_apply_fixture is not None
        else _allowed_apply_fixture(repository.path.parent, user_id=user_id, repository=repository)
    )
    stored_minimal_apply = repository.get_simulado_minimal_progress_ledger_apply_by_id(
        minimal_apply.minimal_progress_ledger_apply_id,
        user_id=user_id,
    )
    return AppliedEventLedgerSourceSnapshot(
        minimal_apply=(
            None
            if stored_minimal_apply is None
            else stored_minimal_apply.model_dump(mode="json")
        ),
        runtime_apply_policy=minimal_snapshot.runtime_apply_policy,
        final_event=minimal_snapshot.final_event,
        controlled_execution=minimal_snapshot.controlled_execution,
        execution_plan=minimal_snapshot.execution_plan,
        progress=repository.load_progress(user_id=user_id).model_dump(mode="json"),
        minimal_progress_ledger_apply_count=minimal_snapshot.minimal_progress_ledger_apply_count,
        applied_event_ledger_count=len(
            repository.list_user_simulado_applied_event_ledgers(user_id=user_id)
        ),
    )
