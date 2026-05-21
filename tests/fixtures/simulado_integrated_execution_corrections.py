from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoAnswerKeyBoundary,
    SimuladoAnswerSubmission,
    SimuladoAttemptSession,
    SimuladoCorrectionResult,
    SimuladoCorrectionShell,
    SimuladoIntegratedExecutionCorrection,
    SimuladoProgressMutationGuardrail,
    SimuladoScoreResult,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_integrated_execution_correction import (
    SimuladoIntegratedExecutionCorrectionService,
)
from tests.fixtures.simulado_answer_key_boundaries import (
    build_answer_key_boundary,
    selected_option_boundary_fixture as _selected_option_boundary_fixture,
)
from tests.fixtures.simulado_answer_submissions import (
    build_answer_submission,
    selected_option_submission_fixture as _selected_option_submission_fixture,
)
from tests.fixtures.simulado_attempt_sessions import (
    build_attempt_session,
    prepared_items_non_submittable_fixture as _prepared_items_non_submittable_fixture,
    user_scope_fixture as _attempt_user_scope_fixture,
)
from tests.fixtures.simulado_correction_results import (
    build_correction_result,
    mixed_correction_result_fixture as _mixed_correction_result_fixture,
    selected_option_correction_result_fixture as _selected_option_correction_result_fixture,
)
from tests.fixtures.simulado_correction_shells import (
    build_correction_shell,
    selected_option_correction_readiness_fixture as _selected_option_correction_readiness_fixture,
)
from tests.fixtures.simulado_progress_guardrails import (
    api_readonly_fixture as _progress_api_readonly_fixture,
    build_progress_guardrail,
    mixed_guardrail_fixture as _mixed_guardrail_fixture,
    no_scoreable_items_fixture as _no_scoreable_items_fixture,
)
from tests.fixtures.simulado_scoring_results import (
    build_score_result,
    selected_option_score_fixture as _selected_option_score_fixture,
)


@dataclass
class SimuladoIntegratedExecutionCorrectionFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoIntegratedExecutionCorrectionService
    user_id: str


@dataclass
class SimuladoIntegratedExecutionCorrectionFixture:
    context: SimuladoIntegratedExecutionCorrectionFixtureContext
    attempt_session: SimuladoAttemptSession | None
    answer_submission: SimuladoAnswerSubmission | None = None
    correction_shell: SimuladoCorrectionShell | None = None
    answer_key_boundary: SimuladoAnswerKeyBoundary | None = None
    correction_result: SimuladoCorrectionResult | None = None
    score_result: SimuladoScoreResult | None = None
    progress_guardrail: SimuladoProgressMutationGuardrail | None = None
    missing_attempt_session_id: str | None = None


def _context(repository: JsonStudyRepository, user_id: str) -> SimuladoIntegratedExecutionCorrectionFixtureContext:
    return SimuladoIntegratedExecutionCorrectionFixtureContext(
        repository=repository,
        service=SimuladoIntegratedExecutionCorrectionService(repository),
        user_id=user_id,
    )


def build_integrated_result(
    fixture: SimuladoIntegratedExecutionCorrectionFixture,
) -> SimuladoIntegratedExecutionCorrection | None:
    source_id = fixture.missing_attempt_session_id
    if fixture.attempt_session is not None:
        source_id = fixture.attempt_session.attempt_session_id
    assert source_id is not None
    return fixture.context.service.build_integrated_result(
        source_id,
        user_id=fixture.context.user_id,
    )


def missing_attempt_session_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    repository = repository or JsonStudyRepository(tmp_path / "study_data.json")
    return SimuladoIntegratedExecutionCorrectionFixture(
        context=_context(repository, user_id),
        attempt_session=None,
        missing_attempt_session_id="simulado-attempt-session:missing",
    )


def missing_answer_submission_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    attempt_fixture = _prepared_items_non_submittable_fixture(tmp_path, user_id=user_id, repository=repository)
    attempt_session = build_attempt_session(attempt_fixture)
    assert attempt_session is not None
    return SimuladoIntegratedExecutionCorrectionFixture(
        context=_context(attempt_fixture.context.repository, user_id),
        attempt_session=attempt_session,
    )


def missing_correction_shell_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    submission_fixture = _selected_option_submission_fixture(tmp_path, user_id=user_id, repository=repository)
    answer_submission = build_answer_submission(submission_fixture)
    assert answer_submission is not None
    return SimuladoIntegratedExecutionCorrectionFixture(
        context=_context(submission_fixture.context.repository, user_id),
        attempt_session=submission_fixture.attempt_session,
        answer_submission=answer_submission,
    )


def missing_answer_key_boundary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    shell_fixture = _selected_option_correction_readiness_fixture(tmp_path, user_id=user_id, repository=repository)
    correction_shell = build_correction_shell(shell_fixture)
    assert correction_shell is not None
    answer_submission_fixture = shell_fixture.answer_submission_fixture
    assert answer_submission_fixture is not None
    return SimuladoIntegratedExecutionCorrectionFixture(
        context=_context(shell_fixture.context.repository, user_id),
        attempt_session=answer_submission_fixture.attempt_session,
        answer_submission=shell_fixture.answer_submission,
        correction_shell=correction_shell,
    )


def missing_correction_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    boundary_fixture = _selected_option_boundary_fixture(tmp_path, user_id=user_id, repository=repository)
    answer_key_boundary = build_answer_key_boundary(boundary_fixture)
    assert answer_key_boundary is not None
    shell_fixture = boundary_fixture.correction_shell_fixture
    assert shell_fixture is not None
    submission_fixture = shell_fixture.answer_submission_fixture
    assert submission_fixture is not None
    return SimuladoIntegratedExecutionCorrectionFixture(
        context=_context(boundary_fixture.context.repository, user_id),
        attempt_session=submission_fixture.attempt_session,
        answer_submission=shell_fixture.answer_submission,
        correction_shell=boundary_fixture.correction_shell,
        answer_key_boundary=answer_key_boundary,
    )


def missing_score_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    correction_fixture = _selected_option_correction_result_fixture(tmp_path, user_id=user_id, repository=repository)
    correction_result = build_correction_result(correction_fixture)
    assert correction_result is not None
    boundary_fixture = correction_fixture.answer_key_boundary_fixture
    assert boundary_fixture is not None
    shell_fixture = boundary_fixture.correction_shell_fixture
    assert shell_fixture is not None
    submission_fixture = shell_fixture.answer_submission_fixture
    assert submission_fixture is not None
    return SimuladoIntegratedExecutionCorrectionFixture(
        context=_context(correction_fixture.context.repository, user_id),
        attempt_session=submission_fixture.attempt_session,
        answer_submission=shell_fixture.answer_submission,
        correction_shell=boundary_fixture.correction_shell,
        answer_key_boundary=correction_fixture.answer_key_boundary,
        correction_result=correction_result,
    )


def missing_progress_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    score_fixture = _selected_option_score_fixture(tmp_path, user_id=user_id, repository=repository)
    score_result = build_score_result(score_fixture)
    assert score_result is not None
    correction_fixture = score_fixture.correction_result_fixture
    assert correction_fixture is not None
    boundary_fixture = correction_fixture.answer_key_boundary_fixture
    assert boundary_fixture is not None
    shell_fixture = boundary_fixture.correction_shell_fixture
    assert shell_fixture is not None
    submission_fixture = shell_fixture.answer_submission_fixture
    assert submission_fixture is not None
    return SimuladoIntegratedExecutionCorrectionFixture(
        context=_context(score_fixture.context.repository, user_id),
        attempt_session=submission_fixture.attempt_session,
        answer_submission=shell_fixture.answer_submission,
        correction_shell=boundary_fixture.correction_shell,
        answer_key_boundary=correction_fixture.answer_key_boundary,
        correction_result=score_fixture.correction_result,
        score_result=score_result,
    )


def complete_chain_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    guardrail_fixture = _progress_api_readonly_fixture(tmp_path, user_id=user_id, repository=repository)
    progress_guardrail = build_progress_guardrail(guardrail_fixture)
    assert progress_guardrail is not None
    score_fixture = guardrail_fixture.score_result_fixture
    assert score_fixture is not None
    correction_fixture = score_fixture.correction_result_fixture
    assert correction_fixture is not None
    boundary_fixture = correction_fixture.answer_key_boundary_fixture
    assert boundary_fixture is not None
    shell_fixture = boundary_fixture.correction_shell_fixture
    assert shell_fixture is not None
    submission_fixture = shell_fixture.answer_submission_fixture
    assert submission_fixture is not None
    return SimuladoIntegratedExecutionCorrectionFixture(
        context=_context(guardrail_fixture.context.repository, user_id),
        attempt_session=submission_fixture.attempt_session,
        answer_submission=shell_fixture.answer_submission,
        correction_shell=boundary_fixture.correction_shell,
        answer_key_boundary=correction_fixture.answer_key_boundary,
        correction_result=score_fixture.correction_result,
        score_result=guardrail_fixture.score_result,
        progress_guardrail=progress_guardrail,
    )


def complete_chain_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def incomplete_correction_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def incomplete_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def progress_guardrail_not_eligible_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def runtime_mutation_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def chain_summary_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def execution_summary_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def correction_summary_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def score_summary_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def progress_guardrail_summary_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def no_scoreable_items_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    guardrail_fixture = _no_scoreable_items_fixture(tmp_path, user_id=user_id, repository=repository)
    progress_guardrail = build_progress_guardrail(guardrail_fixture)
    assert progress_guardrail is not None
    score_fixture = guardrail_fixture.score_result_fixture
    assert score_fixture is not None
    correction_fixture = score_fixture.correction_result_fixture
    assert correction_fixture is not None
    boundary_fixture = correction_fixture.answer_key_boundary_fixture
    assert boundary_fixture is not None
    shell_fixture = boundary_fixture.correction_shell_fixture
    assert shell_fixture is not None
    submission_fixture = shell_fixture.answer_submission_fixture
    assert submission_fixture is not None
    return SimuladoIntegratedExecutionCorrectionFixture(
        context=_context(guardrail_fixture.context.repository, user_id),
        attempt_session=submission_fixture.attempt_session,
        answer_submission=shell_fixture.answer_submission,
        correction_shell=boundary_fixture.correction_shell,
        answer_key_boundary=correction_fixture.answer_key_boundary,
        correction_result=score_fixture.correction_result,
        score_result=guardrail_fixture.score_result,
        progress_guardrail=progress_guardrail,
    )


def mixed_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    guardrail_fixture = _mixed_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)
    progress_guardrail = build_progress_guardrail(guardrail_fixture)
    assert progress_guardrail is not None
    score_fixture = guardrail_fixture.score_result_fixture
    assert score_fixture is not None
    correction_fixture = score_fixture.correction_result_fixture
    assert correction_fixture is not None
    boundary_fixture = correction_fixture.answer_key_boundary_fixture
    assert boundary_fixture is not None
    shell_fixture = boundary_fixture.correction_shell_fixture
    assert shell_fixture is not None
    submission_fixture = shell_fixture.answer_submission_fixture
    assert submission_fixture is not None
    return SimuladoIntegratedExecutionCorrectionFixture(
        context=_context(guardrail_fixture.context.repository, user_id),
        attempt_session=submission_fixture.attempt_session,
        answer_submission=shell_fixture.answer_submission,
        correction_shell=boundary_fixture.correction_shell,
        answer_key_boundary=correction_fixture.answer_key_boundary,
        correction_result=score_fixture.correction_result,
        score_result=guardrail_fixture.score_result,
        progress_guardrail=progress_guardrail,
    )


def mixed_blockers_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return mixed_guardrail_fixture(tmp_path, user_id=user_id, repository=repository)


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoIntegratedExecutionCorrectionFixture, SimuladoIntegratedExecutionCorrectionFixture]:
    owner_attempt, other_attempt = _attempt_user_scope_fixture(tmp_path, repository=repository)
    owner_attempt_session = build_attempt_session(owner_attempt)
    other_attempt_session = build_attempt_session(other_attempt)
    assert owner_attempt_session is not None
    assert other_attempt_session is not None
    return (
        SimuladoIntegratedExecutionCorrectionFixture(
            context=_context(owner_attempt.context.repository, owner_attempt.context.user_id),
            attempt_session=owner_attempt_session,
        ),
        SimuladoIntegratedExecutionCorrectionFixture(
            context=_context(other_attempt.context.repository, other_attempt.context.user_id),
            attempt_session=other_attempt_session,
        ),
    )


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoIntegratedExecutionCorrectionFixture:
    return complete_chain_fixture(tmp_path, user_id=user_id, repository=repository)
