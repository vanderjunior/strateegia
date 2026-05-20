from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SimuladoAnswerSubmission, SimuladoCorrectionShell
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_answer_submission import SimuladoAnswerSubmissionService
from app.services.simulado_correction_shell import SimuladoCorrectionShellService
from tests.fixtures.simulado_answer_submissions import (
    SimuladoAnswerSubmissionFixture,
    SimuladoAnswerSubmissionFixtureContext,
    blank_submission_fixture as _blank_submission_fixture,
    build_answer_submission,
    empty_submission_fixture as _empty_submission_fixture,
    missing_attempt_session_fixture as _missing_attempt_session_fixture,
    partial_submission_fixture as _partial_submission_fixture,
    selected_option_submission_fixture as _selected_option_submission_fixture,
    short_text_submission_fixture as _short_text_submission_fixture,
    true_false_submission_fixture as _true_false_submission_fixture,
    unsupported_answer_kind_fixture as _unsupported_answer_kind_fixture,
    unknown_item_fixture as _unknown_item_fixture,
)
from tests.fixtures.simulado_attempt_sessions import ordering_stability_fixture


@dataclass
class SimuladoCorrectionShellFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoCorrectionShellService
    user_id: str


@dataclass
class SimuladoCorrectionShellFixture:
    context: SimuladoCorrectionShellFixtureContext
    answer_submission_fixture: SimuladoAnswerSubmissionFixture | None
    answer_submission: SimuladoAnswerSubmission | None
    missing_answer_submission_id: str | None = None


def _wrap_fixture(answer_submission_fixture: SimuladoAnswerSubmissionFixture) -> SimuladoCorrectionShellFixture:
    answer_submission = build_answer_submission(answer_submission_fixture)
    assert answer_submission is not None
    return SimuladoCorrectionShellFixture(
        context=SimuladoCorrectionShellFixtureContext(
            repository=answer_submission_fixture.context.repository,
            service=SimuladoCorrectionShellService(answer_submission_fixture.context.repository),
            user_id=answer_submission_fixture.context.user_id,
        ),
        answer_submission_fixture=answer_submission_fixture,
        answer_submission=answer_submission,
    )


def build_correction_shell(
    fixture: SimuladoCorrectionShellFixture,
) -> SimuladoCorrectionShell | None:
    source_id = fixture.missing_answer_submission_id
    if fixture.answer_submission is not None:
        source_id = fixture.answer_submission.answer_submission_id
    assert source_id is not None
    return fixture.context.service.build_correction_shell(
        source_id,
        user_id=fixture.context.user_id,
    )


def missing_answer_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    answer_fixture = _missing_attempt_session_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoCorrectionShellFixture(
        context=SimuladoCorrectionShellFixtureContext(
            repository=answer_fixture.context.repository,
            service=SimuladoCorrectionShellService(answer_fixture.context.repository),
            user_id=user_id,
        ),
        answer_submission_fixture=None,
        answer_submission=None,
        missing_answer_submission_id="simulado-answer-submission:missing",
    )


def empty_answer_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_empty_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def selected_option_correction_readiness_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_selected_option_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def true_false_correction_readiness_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_true_false_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def blank_answer_correction_readiness_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_blank_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def short_text_correction_readiness_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_short_text_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def unsupported_answer_kind_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_unsupported_answer_kind_fixture(tmp_path, user_id=user_id, repository=repository))


def invalid_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_unknown_item_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_final_answer_key_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_selected_option_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_correction_rule_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_selected_option_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_score_rule_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_selected_option_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def mixed_submission_readiness_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    attempt_fixture = ordering_stability_fixture(tmp_path, user_id=user_id, repository=repository)
    assert attempt_fixture is not None
    attempt_session = attempt_fixture.context.service.build_attempt_session(
        attempt_fixture.execution_shell.execution_shell_id,
        user_id=attempt_fixture.context.user_id,
    )
    assert attempt_session is not None
    answer_fixture = SimuladoAnswerSubmissionFixture(
        context=SimuladoAnswerSubmissionFixtureContext(
            repository=attempt_fixture.context.repository,
            service=SimuladoAnswerSubmissionService(attempt_fixture.context.repository),
            user_id=attempt_fixture.context.user_id,
        ),
        attempt_session_fixture=attempt_fixture,
        attempt_session=attempt_session,
        submission_payload={
            "answers": [
                {
                    "source_session_item_id": attempt_session.items[0].item_id,
                    "answer_kind": "selected_option",
                    "submitted_value": "A",
                },
                {
                    "source_session_item_id": attempt_session.items[1].item_id,
                    "answer_kind": "true_false_value",
                    "submitted_value": "C",
                },
                {
                    "source_session_item_id": attempt_session.items[2].item_id,
                    "answer_kind": "blank",
                },
                {
                    "source_session_item_id": attempt_session.items[3].item_id,
                    "answer_kind": "unsupported_kind",
                    "submitted_value": "X",
                },
                {
                    "source_session_item_id": "unknown-item",
                    "answer_kind": "selected_option",
                    "submitted_value": "D",
                },
            ]
        },
    )
    return _wrap_fixture(answer_fixture)


def no_answer_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return mixed_submission_readiness_fixture(tmp_path, user_id=user_id, repository=repository)


def no_correction_scoring_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return mixed_submission_readiness_fixture(tmp_path, user_id=user_id, repository=repository)


def no_progress_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_selected_option_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_selected_option_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoCorrectionShellFixture, SimuladoCorrectionShellFixture]:
    owner = _wrap_fixture(_selected_option_submission_fixture(tmp_path / "owner", user_id="user-a", repository=repository))
    other = _wrap_fixture(_selected_option_submission_fixture(tmp_path / "other", user_id="user-b", repository=owner.context.repository))
    return owner, other


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoCorrectionShellFixture:
    return _wrap_fixture(_selected_option_submission_fixture(tmp_path, user_id=user_id, repository=repository))
