from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SimuladoAttemptSession, SimuladoExecutionShell
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_attempt_session import SimuladoAttemptSessionService
from tests.fixtures.simulado_execution_shells import (
    SimuladoExecutionShellFixture,
    approved_candidates_not_executable_fixture as _approved_candidates_not_executable_fixture,
    assembly_json_keys,
    bounded_summary_fixture as _bounded_summary_fixture,
    build_execution_shell,
    disabled_flags_fixture as _disabled_flags_fixture,
    idempotency_fixture as _idempotency_fixture,
    no_approved_candidates_fixture as _no_approved_candidates_fixture,
    no_attempt_submission_score_safety_fixture as _no_attempt_submission_score_safety_fixture,
    ordering_fixture as _ordering_fixture,
    user_scope_fixture as _user_scope_fixture,
)


@dataclass
class SimuladoAttemptSessionFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoAttemptSessionService
    user_id: str


@dataclass
class SimuladoAttemptSessionFixture:
    context: SimuladoAttemptSessionFixtureContext
    execution_shell_fixture: SimuladoExecutionShellFixture | None
    execution_shell: SimuladoExecutionShell | None
    missing_execution_shell_id: str | None = None


def _wrap_fixture(execution_shell_fixture: SimuladoExecutionShellFixture) -> SimuladoAttemptSessionFixture:
    execution_shell = build_execution_shell(execution_shell_fixture)
    assert execution_shell is not None
    return SimuladoAttemptSessionFixture(
        context=SimuladoAttemptSessionFixtureContext(
            repository=execution_shell_fixture.context.repository,
            service=SimuladoAttemptSessionService(execution_shell_fixture.context.repository),
            user_id=execution_shell_fixture.context.user_id,
        ),
        execution_shell_fixture=execution_shell_fixture,
        execution_shell=execution_shell,
    )


def build_attempt_session(
    fixture: SimuladoAttemptSessionFixture,
) -> SimuladoAttemptSession | None:
    source_id = fixture.missing_execution_shell_id
    if fixture.execution_shell is not None:
        source_id = fixture.execution_shell.execution_shell_id
    assert source_id is not None
    return fixture.context.service.build_attempt_session(
        source_id,
        user_id=fixture.context.user_id,
    )


def missing_execution_shell_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    repository = repository or JsonStudyRepository(tmp_path / "study_data.json")
    return SimuladoAttemptSessionFixture(
        context=SimuladoAttemptSessionFixtureContext(
            repository=repository,
            service=SimuladoAttemptSessionService(repository),
            user_id=user_id,
        ),
        execution_shell_fixture=None,
        execution_shell=None,
        missing_execution_shell_id="simulado-execution-shell:missing",
    )


def inactive_execution_shell_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    return _wrap_fixture(
        _approved_candidates_not_executable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def no_executable_candidates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    return _wrap_fixture(
        _no_approved_candidates_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def prepared_items_non_submittable_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    return _wrap_fixture(
        _approved_candidates_not_executable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def timing_placeholders_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    return _wrap_fixture(
        _approved_candidates_not_executable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def disabled_flags_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    return _wrap_fixture(
        _disabled_flags_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def no_answer_submission_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    return _wrap_fixture(
        _no_attempt_submission_score_safety_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def no_correction_scoring_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    return _wrap_fixture(
        _no_attempt_submission_score_safety_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def no_progress_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    return _wrap_fixture(
        _approved_candidates_not_executable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def ordering_stability_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    return _wrap_fixture(
        _ordering_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def bounded_summary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    return _wrap_fixture(
        _bounded_summary_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoAttemptSessionFixture, SimuladoAttemptSessionFixture]:
    owner_fixture, other_fixture = _user_scope_fixture(tmp_path, repository=repository)
    return _wrap_fixture(owner_fixture), _wrap_fixture(other_fixture)


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptSessionFixture:
    return _wrap_fixture(
        _idempotency_fixture(tmp_path, user_id=user_id, repository=repository)
    )
