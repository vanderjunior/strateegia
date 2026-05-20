from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SimuladoCorrectionResult, SimuladoScoreResult
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_scoring import SimuladoScoringService
from tests.fixtures.simulado_correction_results import (
    SimuladoCorrectionResultFixture,
    api_readonly_fixture as _api_readonly_fixture,
    blank_answer_correction_result_fixture as _blank_answer_correction_result_fixture,
    build_correction_result,
    empty_answer_key_boundary_fixture as _empty_answer_key_boundary_fixture,
    invalid_submission_fixture as _invalid_submission_fixture,
    missing_answer_key_boundary_fixture as _missing_answer_key_boundary_fixture,
    missing_correction_rule_fixture as _missing_correction_rule_fixture,
    missing_internal_answer_key_reference_fixture as _missing_internal_answer_key_reference_fixture,
    mixed_correction_result_fixture as _mixed_correction_result_fixture,
    no_progress_mutation_fixture as _no_progress_mutation_fixture,
    no_public_key_gabarito_safety_fixture as _no_public_key_gabarito_safety_fixture,
    no_scoring_safety_fixture as _no_scoring_safety_fixture,
    selected_option_correction_result_fixture as _selected_option_correction_result_fixture,
    short_text_correction_result_fixture as _short_text_correction_result_fixture,
    true_false_correction_result_fixture as _true_false_correction_result_fixture,
    unsupported_answer_kind_fixture as _unsupported_answer_kind_fixture,
    user_scope_fixture as _user_scope_fixture,
)


@dataclass
class SimuladoScoreResultFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoScoringService
    user_id: str


@dataclass
class SimuladoScoreResultFixture:
    context: SimuladoScoreResultFixtureContext
    correction_result_fixture: SimuladoCorrectionResultFixture | None
    correction_result: SimuladoCorrectionResult | None
    missing_correction_result_id: str | None = None


def _wrap_fixture(correction_result_fixture: SimuladoCorrectionResultFixture) -> SimuladoScoreResultFixture:
    correction_result = build_correction_result(correction_result_fixture)
    assert correction_result is not None
    return SimuladoScoreResultFixture(
        context=SimuladoScoreResultFixtureContext(
            repository=correction_result_fixture.context.repository,
            service=SimuladoScoringService(correction_result_fixture.context.repository),
            user_id=correction_result_fixture.context.user_id,
        ),
        correction_result_fixture=correction_result_fixture,
        correction_result=correction_result,
    )


def build_score_result(
    fixture: SimuladoScoreResultFixture,
) -> SimuladoScoreResult | None:
    source_id = fixture.missing_correction_result_id
    if fixture.correction_result is not None:
        source_id = fixture.correction_result.correction_result_id
    assert source_id is not None
    return fixture.context.service.build_score_result(
        source_id,
        user_id=fixture.context.user_id,
    )


def missing_correction_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    result_fixture = _missing_answer_key_boundary_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoScoreResultFixture(
        context=SimuladoScoreResultFixtureContext(
            repository=result_fixture.context.repository,
            service=SimuladoScoringService(result_fixture.context.repository),
            user_id=user_id,
        ),
        correction_result_fixture=None,
        correction_result=None,
        missing_correction_result_id="simulado-correction-result:missing",
    )


def empty_correction_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_empty_answer_key_boundary_fixture(tmp_path, user_id=user_id, repository=repository))


def selected_option_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_selected_option_correction_result_fixture(tmp_path, user_id=user_id, repository=repository))


def true_false_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_true_false_correction_result_fixture(tmp_path, user_id=user_id, repository=repository))


def blank_answer_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_blank_answer_correction_result_fixture(tmp_path, user_id=user_id, repository=repository))


def short_text_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_short_text_correction_result_fixture(tmp_path, user_id=user_id, repository=repository))


def unsupported_answer_kind_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_unsupported_answer_kind_fixture(tmp_path, user_id=user_id, repository=repository))


def invalid_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_invalid_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_internal_answer_key_reference_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(
        _missing_internal_answer_key_reference_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def missing_correction_rule_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_missing_correction_rule_fixture(tmp_path, user_id=user_id, repository=repository))


def mixed_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_mixed_correction_result_fixture(tmp_path, user_id=user_id, repository=repository))


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_no_public_key_gabarito_safety_fixture(tmp_path, user_id=user_id, repository=repository))


def no_scoring_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_no_scoring_safety_fixture(tmp_path, user_id=user_id, repository=repository))


def no_progress_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_no_progress_mutation_fixture(tmp_path, user_id=user_id, repository=repository))


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_selected_option_correction_result_fixture(tmp_path, user_id=user_id, repository=repository))


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoScoreResultFixture, SimuladoScoreResultFixture]:
    owner_result, other_result = _user_scope_fixture(tmp_path, repository=repository)
    return _wrap_fixture(owner_result), _wrap_fixture(other_result)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoScoreResultFixture:
    return _wrap_fixture(_api_readonly_fixture(tmp_path, user_id=user_id, repository=repository))
