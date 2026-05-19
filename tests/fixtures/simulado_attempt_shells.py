from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SimuladoQuestionAssembly
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_attempt_shell import SimuladoAttemptShellService
from tests.fixtures.simulado_question_assemblies import (
    assembly_json_keys,
    bounded_summary_fixture as _bounded_summary_fixture,
    build_assembly,
    mixed_assembly_fixture as _mixed_assembly_fixture,
    missing_guardrail_candidate_fixture as _missing_guardrail_candidate_fixture,
    no_candidates_fixture as _no_candidates_assembly_fixture,
    ready_for_review_candidate_fixture as _ready_for_review_candidate_fixture,
    unsupported_format_candidate_fixture as _unsupported_format_candidate_fixture,
    user_scope_fixture as _user_scope_fixture,
)


@dataclass
class SimuladoAttemptShellFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoAttemptShellService
    user_id: str


@dataclass
class SimuladoAttemptShellFixture:
    context: SimuladoAttemptShellFixtureContext
    assembly: SimuladoQuestionAssembly


def _wrap_fixture(assembly_fixture) -> SimuladoAttemptShellFixture:
    assembly = build_assembly(assembly_fixture)
    assert assembly is not None
    return SimuladoAttemptShellFixture(
        context=SimuladoAttemptShellFixtureContext(
            repository=assembly_fixture.context.repository,
            service=SimuladoAttemptShellService(assembly_fixture.context.repository),
            user_id=assembly_fixture.context.user_id,
        ),
        assembly=assembly,
    )


def build_attempt_shell(fixture: SimuladoAttemptShellFixture):
    return fixture.context.service.build_attempt_shell(
        fixture.assembly.assembly_id,
        user_id=fixture.context.user_id,
    )


def non_executable_assembly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def ready_candidates_not_executable_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def missing_final_questions_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def missing_final_answer_keys_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def missing_final_explanations_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def review_required_assembly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def zero_candidates_assembly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _no_candidates_assembly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def all_blocked_candidates_assembly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _missing_guardrail_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def mixed_ready_blocked_review_assembly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _mixed_assembly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def unsupported_candidate_assembly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _unsupported_format_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def no_attempt_submission_score_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def bounded_summary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _bounded_summary_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoAttemptShellFixture, SimuladoAttemptShellFixture]:
    owner_assembly_fixture, other_assembly_fixture = _user_scope_fixture(tmp_path, repository=repository)
    return _wrap_fixture(owner_assembly_fixture), _wrap_fixture(other_assembly_fixture)


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAttemptShellFixture:
    return _wrap_fixture(
        _ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    )
