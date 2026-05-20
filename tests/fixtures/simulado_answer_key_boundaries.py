from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SimuladoAnswerKeyBoundary, SimuladoCorrectionShell
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_answer_key_boundary import SimuladoAnswerKeyBoundaryService
from tests.fixtures.simulado_correction_shells import (
    SimuladoCorrectionShellFixture,
    blank_answer_correction_readiness_fixture as _blank_answer_correction_readiness_fixture,
    build_correction_shell,
    empty_answer_submission_fixture as _empty_answer_submission_fixture,
    invalid_submission_fixture as _invalid_submission_fixture,
    missing_answer_submission_fixture as _missing_answer_submission_fixture,
    missing_correction_rule_fixture as _missing_correction_rule_fixture,
    missing_final_answer_key_fixture as _missing_final_answer_key_fixture,
    missing_score_rule_fixture as _missing_score_rule_fixture,
    mixed_submission_readiness_fixture as _mixed_submission_readiness_fixture,
    selected_option_correction_readiness_fixture as _selected_option_correction_readiness_fixture,
    short_text_correction_readiness_fixture as _short_text_correction_readiness_fixture,
    true_false_correction_readiness_fixture as _true_false_correction_readiness_fixture,
    unsupported_answer_kind_fixture as _unsupported_answer_kind_fixture,
    user_scope_fixture as _user_scope_fixture,
)


@dataclass
class SimuladoAnswerKeyBoundaryFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoAnswerKeyBoundaryService
    user_id: str


@dataclass
class SimuladoAnswerKeyBoundaryFixture:
    context: SimuladoAnswerKeyBoundaryFixtureContext
    correction_shell_fixture: SimuladoCorrectionShellFixture | None
    correction_shell: SimuladoCorrectionShell | None
    missing_correction_shell_id: str | None = None


def _wrap_fixture(correction_shell_fixture: SimuladoCorrectionShellFixture) -> SimuladoAnswerKeyBoundaryFixture:
    correction_shell = build_correction_shell(correction_shell_fixture)
    assert correction_shell is not None
    return SimuladoAnswerKeyBoundaryFixture(
        context=SimuladoAnswerKeyBoundaryFixtureContext(
            repository=correction_shell_fixture.context.repository,
            service=SimuladoAnswerKeyBoundaryService(correction_shell_fixture.context.repository),
            user_id=correction_shell_fixture.context.user_id,
        ),
        correction_shell_fixture=correction_shell_fixture,
        correction_shell=correction_shell,
    )


def build_answer_key_boundary(
    fixture: SimuladoAnswerKeyBoundaryFixture,
) -> SimuladoAnswerKeyBoundary | None:
    source_id = fixture.missing_correction_shell_id
    if fixture.correction_shell is not None:
        source_id = fixture.correction_shell.correction_shell_id
    assert source_id is not None
    return fixture.context.service.build_answer_key_boundary(
        source_id,
        user_id=fixture.context.user_id,
    )


def missing_correction_shell_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    correction_shell_fixture = _missing_answer_submission_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoAnswerKeyBoundaryFixture(
        context=SimuladoAnswerKeyBoundaryFixtureContext(
            repository=correction_shell_fixture.context.repository,
            service=SimuladoAnswerKeyBoundaryService(correction_shell_fixture.context.repository),
            user_id=user_id,
        ),
        correction_shell_fixture=None,
        correction_shell=None,
        missing_correction_shell_id="simulado-correction-shell:missing",
    )


def empty_correction_shell_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_empty_answer_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def selected_option_boundary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_selected_option_correction_readiness_fixture(tmp_path, user_id=user_id, repository=repository))


def true_false_boundary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_true_false_correction_readiness_fixture(tmp_path, user_id=user_id, repository=repository))


def blank_answer_boundary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_blank_answer_correction_readiness_fixture(tmp_path, user_id=user_id, repository=repository))


def short_text_boundary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_short_text_correction_readiness_fixture(tmp_path, user_id=user_id, repository=repository))


def unsupported_answer_kind_boundary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_unsupported_answer_kind_fixture(tmp_path, user_id=user_id, repository=repository))


def invalid_submission_boundary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_invalid_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_internal_answer_key_reference_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_missing_final_answer_key_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_correction_rule_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_missing_correction_rule_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_score_rule_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_missing_score_rule_fixture(tmp_path, user_id=user_id, repository=repository))


def internal_reference_redacted_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_selected_option_correction_readiness_fixture(tmp_path, user_id=user_id, repository=repository))


def mixed_boundary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_mixed_submission_readiness_fixture(tmp_path, user_id=user_id, repository=repository))


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return mixed_boundary_fixture(tmp_path, user_id=user_id, repository=repository)


def no_correction_scoring_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return mixed_boundary_fixture(tmp_path, user_id=user_id, repository=repository)


def no_progress_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_selected_option_correction_readiness_fixture(tmp_path, user_id=user_id, repository=repository))


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_selected_option_correction_readiness_fixture(tmp_path, user_id=user_id, repository=repository))


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoAnswerKeyBoundaryFixture, SimuladoAnswerKeyBoundaryFixture]:
    owner_shell, other_shell = _user_scope_fixture(tmp_path, repository=repository)
    return _wrap_fixture(owner_shell), _wrap_fixture(other_shell)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAnswerKeyBoundaryFixture:
    return _wrap_fixture(_selected_option_correction_readiness_fixture(tmp_path, user_id=user_id, repository=repository))
