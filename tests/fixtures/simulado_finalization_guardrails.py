from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SimuladoAttemptShell, SimuladoFinalizationGuardrail, SimuladoQuestionAssembly
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_finalization_guardrails import SimuladoFinalizationGuardrailsService
from tests.fixtures.simulado_attempt_shells import (
    SimuladoAttemptShellFixture,
    all_blocked_candidates_assembly_fixture as _all_blocked_candidates_assembly_fixture,
    assembly_json_keys,
    bounded_summary_fixture as _bounded_summary_fixture,
    build_attempt_shell,
    idempotency_fixture as _idempotency_fixture,
    mixed_ready_blocked_review_assembly_fixture as _mixed_ready_blocked_review_assembly_fixture,
    missing_final_answer_keys_fixture as _missing_final_answer_keys_fixture,
    missing_final_explanations_fixture as _missing_final_explanations_fixture,
    missing_final_questions_fixture as _missing_final_questions_fixture,
    non_executable_assembly_fixture as _non_executable_assembly_fixture,
    ready_candidates_not_executable_fixture as _ready_candidates_not_executable_fixture,
    review_required_assembly_fixture as _review_required_assembly_fixture,
    unsupported_candidate_assembly_fixture as _unsupported_candidate_assembly_fixture,
    user_scope_fixture as _user_scope_fixture,
    zero_candidates_assembly_fixture as _zero_candidates_assembly_fixture,
)


@dataclass
class SimuladoFinalizationGuardrailFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoFinalizationGuardrailsService
    user_id: str


@dataclass
class SimuladoFinalizationGuardrailFixture:
    context: SimuladoFinalizationGuardrailFixtureContext
    assembly: SimuladoQuestionAssembly
    attempt_shell: SimuladoAttemptShell


def _wrap_fixture(attempt_shell_fixture: SimuladoAttemptShellFixture) -> SimuladoFinalizationGuardrailFixture:
    attempt_shell = build_attempt_shell(attempt_shell_fixture)
    assert attempt_shell is not None
    return SimuladoFinalizationGuardrailFixture(
        context=SimuladoFinalizationGuardrailFixtureContext(
            repository=attempt_shell_fixture.context.repository,
            service=SimuladoFinalizationGuardrailsService(attempt_shell_fixture.context.repository),
            user_id=attempt_shell_fixture.context.user_id,
        ),
        assembly=attempt_shell_fixture.assembly,
        attempt_shell=attempt_shell,
    )


def build_finalization_guardrail(
    fixture: SimuladoFinalizationGuardrailFixture,
) -> SimuladoFinalizationGuardrail | None:
    return fixture.context.service.build_guardrail(
        fixture.attempt_shell.attempt_shell_id,
        user_id=fixture.context.user_id,
    )


def non_final_assembly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _non_executable_assembly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def attempt_shell_not_executable_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _non_executable_assembly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def ready_candidates_not_finalizable_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _ready_candidates_not_executable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def missing_final_questions_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _missing_final_questions_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def missing_final_answer_keys_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _missing_final_answer_keys_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def missing_final_explanations_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _missing_final_explanations_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def human_review_required_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _review_required_assembly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def zero_candidates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _zero_candidates_assembly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def all_blocked_candidates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _all_blocked_candidates_assembly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def mixed_ready_blocked_review_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _mixed_ready_blocked_review_assembly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def unsupported_format_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _unsupported_candidate_assembly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def no_approval_finalization_execution_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _ready_candidates_not_executable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def bounded_summary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _bounded_summary_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoFinalizationGuardrailFixture, SimuladoFinalizationGuardrailFixture]:
    owner_fixture, other_fixture = _user_scope_fixture(tmp_path, repository=repository)
    return _wrap_fixture(owner_fixture), _wrap_fixture(other_fixture)


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalizationGuardrailFixture:
    return _wrap_fixture(
        _idempotency_fixture(tmp_path, user_id=user_id, repository=repository)
    )
