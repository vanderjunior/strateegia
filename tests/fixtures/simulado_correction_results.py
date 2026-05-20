from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SimuladoAnswerKeyBoundary, SimuladoCorrectionResult
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_correction_result import SimuladoCorrectionResultService
from tests.fixtures.simulado_answer_key_boundaries import (
    SimuladoAnswerKeyBoundaryFixture,
    blank_answer_boundary_fixture as _blank_answer_boundary_fixture,
    build_answer_key_boundary,
    empty_correction_shell_fixture as _empty_correction_shell_fixture,
    invalid_submission_boundary_fixture as _invalid_submission_boundary_fixture,
    missing_correction_rule_fixture as _missing_correction_rule_fixture,
    missing_correction_shell_fixture as _missing_correction_shell_fixture,
    missing_internal_answer_key_reference_fixture as _missing_internal_answer_key_reference_fixture,
    missing_score_rule_fixture as _missing_score_rule_fixture,
    mixed_boundary_fixture as _mixed_boundary_fixture,
    no_public_key_gabarito_safety_fixture as _no_public_key_gabarito_safety_fixture,
    no_progress_mutation_fixture as _no_progress_mutation_fixture,
    selected_option_boundary_fixture as _selected_option_boundary_fixture,
    short_text_boundary_fixture as _short_text_boundary_fixture,
    true_false_boundary_fixture as _true_false_boundary_fixture,
    unsupported_answer_kind_boundary_fixture as _unsupported_answer_kind_boundary_fixture,
    user_scope_fixture as _user_scope_fixture,
)


@dataclass
class SimuladoCorrectionResultFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoCorrectionResultService
    user_id: str


@dataclass
class SimuladoCorrectionResultFixture:
    context: SimuladoCorrectionResultFixtureContext
    answer_key_boundary_fixture: SimuladoAnswerKeyBoundaryFixture | None
    answer_key_boundary: SimuladoAnswerKeyBoundary | None
    missing_answer_key_boundary_id: str | None = None


def _wrap_fixture(answer_key_boundary_fixture: SimuladoAnswerKeyBoundaryFixture) -> SimuladoCorrectionResultFixture:
    answer_key_boundary = build_answer_key_boundary(answer_key_boundary_fixture)
    assert answer_key_boundary is not None
    return SimuladoCorrectionResultFixture(
        context=SimuladoCorrectionResultFixtureContext(
            repository=answer_key_boundary_fixture.context.repository,
            service=SimuladoCorrectionResultService(answer_key_boundary_fixture.context.repository),
            user_id=answer_key_boundary_fixture.context.user_id,
        ),
        answer_key_boundary_fixture=answer_key_boundary_fixture,
        answer_key_boundary=answer_key_boundary,
    )


def build_correction_result(
    fixture: SimuladoCorrectionResultFixture,
) -> SimuladoCorrectionResult | None:
    source_id = fixture.missing_answer_key_boundary_id
    if fixture.answer_key_boundary is not None:
        source_id = fixture.answer_key_boundary.answer_key_boundary_id
    assert source_id is not None
    return fixture.context.service.build_correction_result(
        source_id,
        user_id=fixture.context.user_id,
    )


def missing_answer_key_boundary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    boundary_fixture = _missing_correction_shell_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoCorrectionResultFixture(
        context=SimuladoCorrectionResultFixtureContext(
            repository=boundary_fixture.context.repository,
            service=SimuladoCorrectionResultService(boundary_fixture.context.repository),
            user_id=user_id,
        ),
        answer_key_boundary_fixture=None,
        answer_key_boundary=None,
        missing_answer_key_boundary_id="simulado-answer-key-boundary:missing",
    )


def empty_answer_key_boundary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_empty_correction_shell_fixture(tmp_path, user_id=user_id, repository=repository))


def selected_option_correction_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_selected_option_boundary_fixture(tmp_path, user_id=user_id, repository=repository))


def true_false_correction_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_true_false_boundary_fixture(tmp_path, user_id=user_id, repository=repository))


def blank_answer_correction_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_blank_answer_boundary_fixture(tmp_path, user_id=user_id, repository=repository))


def short_text_correction_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_short_text_boundary_fixture(tmp_path, user_id=user_id, repository=repository))


def unsupported_answer_kind_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_unsupported_answer_kind_boundary_fixture(tmp_path, user_id=user_id, repository=repository))


def invalid_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_invalid_submission_boundary_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_internal_answer_key_reference_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(
        _missing_internal_answer_key_reference_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def missing_correction_rule_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_missing_correction_rule_fixture(tmp_path, user_id=user_id, repository=repository))


def mixed_correction_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_mixed_boundary_fixture(tmp_path, user_id=user_id, repository=repository))


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_no_public_key_gabarito_safety_fixture(tmp_path, user_id=user_id, repository=repository))


def no_scoring_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_mixed_boundary_fixture(tmp_path, user_id=user_id, repository=repository))


def no_progress_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_no_progress_mutation_fixture(tmp_path, user_id=user_id, repository=repository))


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_selected_option_boundary_fixture(tmp_path, user_id=user_id, repository=repository))


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoCorrectionResultFixture, SimuladoCorrectionResultFixture]:
    owner_boundary, other_boundary = _user_scope_fixture(tmp_path, repository=repository)
    return _wrap_fixture(owner_boundary), _wrap_fixture(other_boundary)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionResultFixture:
    return _wrap_fixture(_selected_option_boundary_fixture(tmp_path, user_id=user_id, repository=repository))
