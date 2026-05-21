from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoIntegratedExecutionCorrection,
    SimuladoRuntimeApplicationGuardrail,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_application_guardrails import (
    SimuladoRuntimeApplicationGuardrailsService,
)
from tests.fixtures.simulado_integrated_execution_corrections import (
    SimuladoIntegratedExecutionCorrectionFixture,
    api_readonly_fixture as _api_readonly_fixture,
    build_integrated_result,
    complete_chain_readonly_fixture as _complete_chain_readonly_fixture,
    incomplete_correction_fixture as _incomplete_correction_fixture,
    incomplete_score_fixture as _incomplete_score_fixture,
    missing_answer_submission_fixture as _missing_answer_submission_fixture,
    missing_score_result_fixture as _missing_score_result_fixture,
    missing_progress_guardrail_fixture as _missing_progress_guardrail_fixture,
    mixed_blockers_fixture as _mixed_blockers_fixture,
    no_public_key_gabarito_safety_fixture as _no_public_key_gabarito_safety_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    progress_guardrail_not_eligible_fixture as _progress_guardrail_not_eligible_fixture,
)


@dataclass
class SimuladoRuntimeApplicationGuardrailFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoRuntimeApplicationGuardrailsService
    user_id: str


@dataclass
class SimuladoRuntimeApplicationGuardrailFixture:
    context: SimuladoRuntimeApplicationGuardrailFixtureContext
    integrated_fixture: SimuladoIntegratedExecutionCorrectionFixture | None
    integrated_result: SimuladoIntegratedExecutionCorrection | None
    missing_integrated_result_id: str | None = None


def _wrap_fixture(
    integrated_fixture: SimuladoIntegratedExecutionCorrectionFixture,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    integrated_result = build_integrated_result(integrated_fixture)
    assert integrated_result is not None
    return SimuladoRuntimeApplicationGuardrailFixture(
        context=SimuladoRuntimeApplicationGuardrailFixtureContext(
            repository=integrated_fixture.context.repository,
            service=SimuladoRuntimeApplicationGuardrailsService(integrated_fixture.context.repository),
            user_id=integrated_fixture.context.user_id,
        ),
        integrated_fixture=integrated_fixture,
        integrated_result=integrated_result,
    )


def build_runtime_guardrail(
    fixture: SimuladoRuntimeApplicationGuardrailFixture,
) -> SimuladoRuntimeApplicationGuardrail | None:
    source_id = fixture.missing_integrated_result_id
    if fixture.integrated_result is not None:
        source_id = fixture.integrated_result.integrated_result_id
    assert source_id is not None
    return fixture.context.service.build_runtime_guardrail(
        source_id,
        user_id=fixture.context.user_id,
    )


def missing_integrated_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    integrated_fixture = _missing_answer_submission_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoRuntimeApplicationGuardrailFixture(
        context=SimuladoRuntimeApplicationGuardrailFixtureContext(
            repository=integrated_fixture.context.repository,
            service=SimuladoRuntimeApplicationGuardrailsService(integrated_fixture.context.repository),
            user_id=user_id,
        ),
        integrated_fixture=None,
        integrated_result=None,
        missing_integrated_result_id="simulado-integrated-result:missing",
    )


def incomplete_integrated_chain_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_missing_answer_submission_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_score_result_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_missing_score_result_fixture(tmp_path, user_id=user_id, repository=repository))


def incomplete_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_incomplete_score_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_progress_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_missing_progress_guardrail_fixture(tmp_path, user_id=user_id, repository=repository))


def progress_guardrail_not_eligible_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_progress_guardrail_not_eligible_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_runtime_policy_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_complete_chain_readonly_fixture(tmp_path, user_id=user_id, repository=repository))


def runtime_mutation_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository))


def candidate_mutation_intents_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_complete_chain_readonly_fixture(tmp_path, user_id=user_id, repository=repository))


def affected_runtime_surfaces_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_complete_chain_readonly_fixture(tmp_path, user_id=user_id, repository=repository))


def safety_assessment_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_complete_chain_readonly_fixture(tmp_path, user_id=user_id, repository=repository))


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_no_public_key_gabarito_safety_fixture(tmp_path, user_id=user_id, repository=repository))


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository))


def candidate_mutation_intent_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return candidate_mutation_intents_fixture(tmp_path, user_id=user_id, repository=repository)


def affected_runtime_surface_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return affected_runtime_surfaces_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_application_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository)


def mixed_runtime_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_mixed_blockers_fixture(tmp_path, user_id=user_id, repository=repository))


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_complete_chain_readonly_fixture(tmp_path, user_id=user_id, repository=repository))


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoRuntimeApplicationGuardrailFixture, SimuladoRuntimeApplicationGuardrailFixture]:
    owner_fixture = _complete_chain_readonly_fixture(tmp_path / "owner", user_id="user-a", repository=repository)
    other_fixture = _complete_chain_readonly_fixture(tmp_path / "other", user_id="user-b", repository=repository)
    return _wrap_fixture(owner_fixture), _wrap_fixture(other_fixture)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_api_readonly_fixture(tmp_path, user_id=user_id, repository=repository))


def incomplete_correction_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeApplicationGuardrailFixture:
    return _wrap_fixture(_incomplete_correction_fixture(tmp_path, user_id=user_id, repository=repository))
