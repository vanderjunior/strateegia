from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SimuladoProgressMutationGuardrail, SimuladoScoreResult
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_progress_guardrails import SimuladoProgressGuardrailsService
from tests.fixtures.simulado_scoring_results import (
    SimuladoScoreResultFixture,
    api_readonly_fixture as _api_readonly_fixture,
    blank_answer_score_fixture as _blank_answer_score_fixture,
    blocked_records_fixture as _blocked_records_fixture,
    build_score_result,
    empty_correction_result_fixture as _empty_correction_result_fixture,
    invalid_submission_fixture as _invalid_submission_fixture,
    missing_correction_result_fixture as _missing_correction_result_fixture,
    missing_score_policy_fixture as _missing_score_policy_fixture,
    mixed_score_result_fixture as _mixed_score_result_fixture,
    no_public_key_gabarito_safety_fixture as _no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    no_scoreable_records_fixture as _no_scoreable_records_fixture,
    safe_policy_snapshot_fixture as _safe_policy_snapshot_fixture,
    score_summary_fixture as _score_summary_fixture,
    unsupported_answer_kind_fixture as _unsupported_answer_kind_fixture,
    user_scope_fixture as _user_scope_fixture,
)


@dataclass
class SimuladoProgressGuardrailFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoProgressGuardrailsService
    user_id: str


@dataclass
class SimuladoProgressGuardrailFixture:
    context: SimuladoProgressGuardrailFixtureContext
    score_result_fixture: SimuladoScoreResultFixture | None
    score_result: SimuladoScoreResult | None
    missing_score_result_id: str | None = None


def _wrap_fixture(score_result_fixture: SimuladoScoreResultFixture) -> SimuladoProgressGuardrailFixture:
    score_result = build_score_result(score_result_fixture)
    assert score_result is not None
    return SimuladoProgressGuardrailFixture(
        context=SimuladoProgressGuardrailFixtureContext(
            repository=score_result_fixture.context.repository,
            service=SimuladoProgressGuardrailsService(score_result_fixture.context.repository),
            user_id=score_result_fixture.context.user_id,
        ),
        score_result_fixture=score_result_fixture,
        score_result=score_result,
    )


def build_progress_guardrail(
    fixture: SimuladoProgressGuardrailFixture,
) -> SimuladoProgressMutationGuardrail | None:
    source_id = fixture.missing_score_result_id
    if fixture.score_result is not None:
        source_id = fixture.score_result.score_result_id
    assert source_id is not None
    return fixture.context.service.build_progress_guardrail(
        source_id,
        user_id=fixture.context.user_id,
    )


def missing_score_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    score_fixture = _missing_correction_result_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoProgressGuardrailFixture(
        context=SimuladoProgressGuardrailFixtureContext(
            repository=score_fixture.context.repository,
            service=SimuladoProgressGuardrailsService(score_fixture.context.repository),
            user_id=user_id,
        ),
        score_result_fixture=None,
        score_result=None,
        missing_score_result_id="simulado-score-result:missing",
    )


def empty_score_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_empty_correction_result_fixture(tmp_path, user_id=user_id, repository=repository))


def no_scoreable_items_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_no_scoreable_records_fixture(tmp_path, user_id=user_id, repository=repository))


def blocked_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_blocked_records_fixture(tmp_path, user_id=user_id, repository=repository))


def blank_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_blank_answer_score_fixture(tmp_path, user_id=user_id, repository=repository))


def unsupported_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_unsupported_answer_kind_fixture(tmp_path, user_id=user_id, repository=repository))


def invalid_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_invalid_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_score_policy_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_missing_score_policy_fixture(tmp_path, user_id=user_id, repository=repository))


def safe_policy_snapshot_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_safe_policy_snapshot_fixture(tmp_path, user_id=user_id, repository=repository))


def mixed_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_mixed_score_result_fixture(tmp_path, user_id=user_id, repository=repository))


def score_summary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_score_summary_fixture(tmp_path, user_id=user_id, repository=repository))


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_no_public_key_gabarito_safety_fixture(tmp_path, user_id=user_id, repository=repository))


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository))


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_no_scoreable_records_fixture(tmp_path, user_id=user_id, repository=repository))


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoProgressGuardrailFixture, SimuladoProgressGuardrailFixture]:
    owner_score, other_score = _user_scope_fixture(tmp_path, repository=repository)
    return _wrap_fixture(owner_score), _wrap_fixture(other_score)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoProgressGuardrailFixture:
    return _wrap_fixture(_api_readonly_fixture(tmp_path, user_id=user_id, repository=repository))
