from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoRuntimeApplicationGuardrail,
    SimuladoRuntimeProgressApplication,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_runtime_progress_application import (
    SimuladoRuntimeProgressApplicationService,
)
from tests.fixtures.simulado_runtime_application_guardrails import (
    SimuladoRuntimeApplicationGuardrailFixture,
    api_readonly_fixture as _api_readonly_fixture,
    build_runtime_guardrail,
    incomplete_integrated_chain_fixture as _incomplete_integrated_chain_fixture,
    incomplete_score_fixture as _incomplete_score_fixture,
    missing_runtime_policy_fixture as _missing_runtime_policy_fixture,
    mixed_runtime_guardrail_fixture as _mixed_runtime_guardrail_fixture,
    no_public_key_gabarito_safety_fixture as _no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture as _no_runtime_application_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    progress_guardrail_not_eligible_fixture as _progress_guardrail_not_eligible_fixture,
    runtime_mutation_disabled_fixture as _runtime_mutation_disabled_fixture,
)


@dataclass
class SimuladoRuntimeProgressApplicationFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoRuntimeProgressApplicationService
    user_id: str


@dataclass
class SimuladoRuntimeProgressApplicationFixture:
    context: SimuladoRuntimeProgressApplicationFixtureContext
    runtime_guardrail_fixture: SimuladoRuntimeApplicationGuardrailFixture | None
    runtime_guardrail: SimuladoRuntimeApplicationGuardrail | None
    missing_runtime_guardrail_id: str | None = None


def _wrap_fixture(
    runtime_guardrail_fixture: SimuladoRuntimeApplicationGuardrailFixture,
) -> SimuladoRuntimeProgressApplicationFixture:
    runtime_guardrail = build_runtime_guardrail(runtime_guardrail_fixture)
    assert runtime_guardrail is not None
    return SimuladoRuntimeProgressApplicationFixture(
        context=SimuladoRuntimeProgressApplicationFixtureContext(
            repository=runtime_guardrail_fixture.context.repository,
            service=SimuladoRuntimeProgressApplicationService(runtime_guardrail_fixture.context.repository),
            user_id=runtime_guardrail_fixture.context.user_id,
        ),
        runtime_guardrail_fixture=runtime_guardrail_fixture,
        runtime_guardrail=runtime_guardrail,
    )


def _persist_runtime_guardrail(
    fixture: SimuladoRuntimeProgressApplicationFixture,
) -> SimuladoRuntimeProgressApplicationFixture:
    runtime_guardrail = fixture.runtime_guardrail
    assert runtime_guardrail is not None
    fixture.context.repository.save_simulado_runtime_guardrail(
        runtime_guardrail,
        user_id=fixture.context.user_id,
    )
    return fixture


def build_runtime_progress_application(
    fixture: SimuladoRuntimeProgressApplicationFixture,
) -> SimuladoRuntimeProgressApplication | None:
    source_id = fixture.missing_runtime_guardrail_id
    if fixture.runtime_guardrail is not None:
        source_id = fixture.runtime_guardrail.runtime_guardrail_id
    assert source_id is not None
    return fixture.context.service.build_application(
        source_runtime_guardrail_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_runtime_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    runtime_guardrail_fixture = _missing_runtime_policy_fixture(tmp_path, user_id=user_id, repository=repository)
    return SimuladoRuntimeProgressApplicationFixture(
        context=SimuladoRuntimeProgressApplicationFixtureContext(
            repository=runtime_guardrail_fixture.context.repository,
            service=SimuladoRuntimeProgressApplicationService(runtime_guardrail_fixture.context.repository),
            user_id=user_id,
        ),
        runtime_guardrail_fixture=None,
        runtime_guardrail=None,
        missing_runtime_guardrail_id="simulado-runtime-guardrail:missing",
    )


def guardrail_not_eligible_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    fixture = _wrap_fixture(_progress_guardrail_not_eligible_fixture(tmp_path, user_id=user_id, repository=repository))
    assert fixture.runtime_guardrail is not None
    fixture.runtime_guardrail.readiness_state = "blocked_by_progress_guardrail_not_eligible"
    fixture.runtime_guardrail.safety_assessment.integrated_chain_complete = True
    fixture.runtime_guardrail.safety_assessment.score_result_present = True
    fixture.runtime_guardrail.safety_assessment.score_complete = True
    fixture.runtime_guardrail.safety_assessment.progress_guardrail_present = True
    fixture.runtime_guardrail.safety_assessment.progress_guardrail_eligible = False
    fixture.runtime_guardrail.eligibility.requires_complete_integrated_chain = False
    fixture.runtime_guardrail.eligibility.requires_complete_score = False
    fixture.runtime_guardrail.eligibility.requires_progress_guardrail_eligibility = True
    return _persist_runtime_guardrail(fixture)


def incomplete_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    return _wrap_fixture(_incomplete_integrated_chain_fixture(tmp_path, user_id=user_id, repository=repository))


def missing_runtime_policy_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    fixture = _wrap_fixture(_missing_runtime_policy_fixture(tmp_path, user_id=user_id, repository=repository))
    assert fixture.runtime_guardrail is not None
    fixture.runtime_guardrail.readiness_state = "runtime_application_needs_review"
    fixture.runtime_guardrail.safety_assessment.integrated_chain_complete = True
    fixture.runtime_guardrail.safety_assessment.score_result_present = True
    fixture.runtime_guardrail.safety_assessment.score_complete = True
    fixture.runtime_guardrail.safety_assessment.progress_guardrail_present = True
    fixture.runtime_guardrail.safety_assessment.progress_guardrail_eligible = True
    fixture.runtime_guardrail.eligibility.requires_progress_guardrail_eligibility = False
    fixture.runtime_guardrail.eligibility.requires_complete_integrated_chain = False
    fixture.runtime_guardrail.eligibility.requires_complete_score = False
    fixture.runtime_guardrail.metadata["force_runtime_policy_missing"] = True
    return _persist_runtime_guardrail(fixture)


def runtime_application_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    fixture = _wrap_fixture(_runtime_mutation_disabled_fixture(tmp_path, user_id=user_id, repository=repository))
    assert fixture.runtime_guardrail is not None
    fixture.runtime_guardrail.readiness_state = "runtime_application_needs_review"
    fixture.runtime_guardrail.safety_assessment.integrated_chain_complete = True
    fixture.runtime_guardrail.safety_assessment.score_result_present = True
    fixture.runtime_guardrail.safety_assessment.score_complete = True
    fixture.runtime_guardrail.safety_assessment.progress_guardrail_present = True
    fixture.runtime_guardrail.safety_assessment.runtime_policy_available = True
    fixture.runtime_guardrail.safety_assessment.progress_guardrail_eligible = True
    fixture.runtime_guardrail.eligibility.requires_progress_guardrail_eligibility = False
    fixture.runtime_guardrail.eligibility.requires_complete_integrated_chain = False
    fixture.runtime_guardrail.eligibility.requires_complete_score = False
    fixture.runtime_guardrail.metadata["force_runtime_application_disabled"] = True
    return _persist_runtime_guardrail(fixture)


def explicit_apply_not_allowed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    fixture = _wrap_fixture(_no_runtime_application_fixture(tmp_path, user_id=user_id, repository=repository))
    assert fixture.runtime_guardrail is not None
    fixture.runtime_guardrail.readiness_state = "runtime_application_needs_review"
    fixture.runtime_guardrail.safety_assessment.integrated_chain_complete = True
    fixture.runtime_guardrail.safety_assessment.score_result_present = True
    fixture.runtime_guardrail.safety_assessment.score_complete = True
    fixture.runtime_guardrail.safety_assessment.progress_guardrail_present = True
    fixture.runtime_guardrail.safety_assessment.runtime_policy_available = True
    fixture.runtime_guardrail.safety_assessment.progress_guardrail_eligible = True
    fixture.runtime_guardrail.eligibility.requires_progress_guardrail_eligibility = False
    fixture.runtime_guardrail.eligibility.requires_complete_integrated_chain = False
    fixture.runtime_guardrail.eligibility.requires_complete_score = False
    fixture.runtime_guardrail.metadata["force_explicit_apply_not_allowed"] = True
    return _persist_runtime_guardrail(fixture)


def planned_mutation_intents_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    return _wrap_fixture(_no_runtime_application_fixture(tmp_path, user_id=user_id, repository=repository))


def proposed_surface_diffs_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    return _wrap_fixture(_no_runtime_application_fixture(tmp_path, user_id=user_id, repository=repository))


def audit_trail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    return _wrap_fixture(_missing_runtime_policy_fixture(tmp_path, user_id=user_id, repository=repository))


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    return _wrap_fixture(_no_public_key_gabarito_safety_fixture(tmp_path, user_id=user_id, repository=repository))


def no_runtime_application_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    return _wrap_fixture(_no_runtime_application_fixture(tmp_path, user_id=user_id, repository=repository))


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    return _wrap_fixture(_no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository))


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    return _wrap_fixture(_no_runtime_application_fixture(tmp_path, user_id=user_id, repository=repository))


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoRuntimeProgressApplicationFixture, SimuladoRuntimeProgressApplicationFixture]:
    owner_fixture = _api_readonly_fixture(tmp_path / "owner", user_id="user-a", repository=repository)
    other_fixture = _api_readonly_fixture(tmp_path / "other", user_id="user-b", repository=repository)
    return _wrap_fixture(owner_fixture), _wrap_fixture(other_fixture)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    return _wrap_fixture(_api_readonly_fixture(tmp_path, user_id=user_id, repository=repository))


def mixed_runtime_progress_application_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    fixture = _wrap_fixture(_mixed_runtime_guardrail_fixture(tmp_path, user_id=user_id, repository=repository))
    assert fixture.runtime_guardrail is not None
    fixture.runtime_guardrail.metadata["force_runtime_application_disabled"] = True
    return _persist_runtime_guardrail(fixture)


def incomplete_score_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoRuntimeProgressApplicationFixture:
    return _wrap_fixture(_incomplete_score_fixture(tmp_path, user_id=user_id, repository=repository))
