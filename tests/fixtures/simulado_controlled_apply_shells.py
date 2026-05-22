from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    SimuladoControlledRuntimeApplyShell,
    SimuladoRuntimeProgressApplication,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_apply_shell import (
    SimuladoControlledRuntimeApplyShellService,
)
from tests.fixtures.simulado_runtime_progress_applications import (
    SimuladoRuntimeProgressApplicationFixture,
    api_readonly_fixture as _api_readonly_fixture,
    audit_confirmation_missing_fixture as _audit_confirmation_missing_fixture,
    build_runtime_progress_application,
    explicit_apply_blocked_fixture as _explicit_apply_blocked_fixture,
    incomplete_guardrail_fixture as _incomplete_guardrail_fixture,
    missing_runtime_guardrail_fixture as _missing_runtime_progress_application_fixture,
    missing_runtime_policy_fixture as _missing_runtime_policy_fixture,
    mixed_application_fixture as _mixed_application_fixture,
    no_public_key_gabarito_safety_fixture as _no_public_key_gabarito_safety_fixture,
    no_runtime_application_fixture as _no_runtime_application_fixture,
    no_runtime_mutation_fixture as _no_runtime_mutation_fixture,
    planned_mutation_intents_fixture as _planned_mutation_intents_fixture,
    proposed_surface_diffs_fixture as _proposed_surface_diffs_fixture,
    runtime_application_disabled_fixture as _runtime_application_disabled_fixture,
)


@dataclass
class SimuladoControlledApplyShellFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoControlledRuntimeApplyShellService
    user_id: str


@dataclass
class SimuladoControlledApplyShellFixture:
    context: SimuladoControlledApplyShellFixtureContext
    runtime_progress_application_fixture: SimuladoRuntimeProgressApplicationFixture | None
    runtime_progress_application: SimuladoRuntimeProgressApplication | None
    missing_application_id: str | None = None


def _wrap_fixture(
    runtime_progress_application_fixture: SimuladoRuntimeProgressApplicationFixture,
) -> SimuladoControlledApplyShellFixture:
    application = build_runtime_progress_application(runtime_progress_application_fixture)
    assert application is not None
    return SimuladoControlledApplyShellFixture(
        context=SimuladoControlledApplyShellFixtureContext(
            repository=runtime_progress_application_fixture.context.repository,
            service=SimuladoControlledRuntimeApplyShellService(
                runtime_progress_application_fixture.context.repository
            ),
            user_id=runtime_progress_application_fixture.context.user_id,
        ),
        runtime_progress_application_fixture=runtime_progress_application_fixture,
        runtime_progress_application=application,
    )


def _persist_application(
    fixture: SimuladoControlledApplyShellFixture,
) -> SimuladoControlledApplyShellFixture:
    application = fixture.runtime_progress_application
    assert application is not None
    fixture.context.repository.save_simulado_runtime_progress_application(
        application,
        user_id=fixture.context.user_id,
    )
    return fixture


def _set_preapply_metadata(
    application: SimuladoRuntimeProgressApplication,
    *,
    runtime_policy_present: bool | None = None,
    explicit_apply_approval_present: bool | None = None,
    audit_confirmation_present: bool | None = None,
    rollback_plan_present: bool | None = None,
) -> None:
    if runtime_policy_present is not None:
        application.metadata["controlled_apply_runtime_policy_present"] = runtime_policy_present
    if explicit_apply_approval_present is not None:
        application.metadata["controlled_apply_explicit_apply_approval_present"] = (
            explicit_apply_approval_present
        )
    if audit_confirmation_present is not None:
        application.metadata["controlled_apply_audit_confirmation_present"] = audit_confirmation_present
    if rollback_plan_present is not None:
        application.metadata["controlled_apply_rollback_plan_present"] = rollback_plan_present


def build_controlled_apply_shell(
    fixture: SimuladoControlledApplyShellFixture,
) -> SimuladoControlledRuntimeApplyShell | None:
    source_id = fixture.missing_application_id
    if fixture.runtime_progress_application is not None:
        source_id = fixture.runtime_progress_application.application_id
    assert source_id is not None
    return fixture.context.service.build_apply_shell(
        source_application_id=source_id,
        user_id=fixture.context.user_id,
    )


def missing_runtime_progress_application_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    application_fixture = _missing_runtime_progress_application_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
    return SimuladoControlledApplyShellFixture(
        context=SimuladoControlledApplyShellFixtureContext(
            repository=application_fixture.context.repository,
            service=SimuladoControlledRuntimeApplyShellService(application_fixture.context.repository),
            user_id=user_id,
        ),
        runtime_progress_application_fixture=None,
        runtime_progress_application=None,
        missing_application_id="simulado-progress-application:missing",
    )


def source_application_planned_only_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_planned_mutation_intents_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=True,
        audit_confirmation_present=True,
        rollback_plan_present=False,
    )
    return _persist_application(fixture)


def planned_only_source_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    return source_application_planned_only_fixture(tmp_path, user_id=user_id, repository=repository)


def application_not_planned_only_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_no_runtime_application_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    application.application_mode = "live_apply_requested"
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=True,
        audit_confirmation_present=True,
    )
    return _persist_application(fixture)


def application_already_applied_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_no_runtime_application_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    application.runtime_application_applied = True
    application.application_status = "application_applied"
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=True,
        audit_confirmation_present=True,
    )
    return _persist_application(fixture)


def missing_runtime_policy_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_missing_runtime_policy_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    _set_preapply_metadata(
        application,
        runtime_policy_present=False,
        explicit_apply_approval_present=False,
        audit_confirmation_present=False,
    )
    return _persist_application(fixture)


def runtime_application_disabled_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_runtime_application_disabled_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    application.metadata["force_runtime_application_disabled"] = True
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=True,
        audit_confirmation_present=True,
    )
    return _persist_application(fixture)


def explicit_apply_approval_missing_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_explicit_apply_blocked_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=False,
        audit_confirmation_present=True,
    )
    return _persist_application(fixture)


def audit_confirmation_missing_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_audit_confirmation_missing_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=True,
        audit_confirmation_present=False,
    )
    return _persist_application(fixture)


def intents_not_apply_allowed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_planned_mutation_intents_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=True,
        audit_confirmation_present=True,
        rollback_plan_present=True,
    )
    return _persist_application(fixture)


def surfaces_not_apply_allowed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_proposed_surface_diffs_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    for intent in application.planned_mutation_intents:
        intent.apply_allowed = True
        intent.blockers = []
        intent.requires_review = False
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=True,
        audit_confirmation_present=True,
        rollback_plan_present=True,
    )
    return _persist_application(fixture)


def no_public_key_gabarito_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(
        _no_public_key_gabarito_safety_fixture(tmp_path, user_id=user_id, repository=repository)
    )
    application = fixture.runtime_progress_application
    assert application is not None
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=True,
        audit_confirmation_present=True,
    )
    return _persist_application(fixture)


def no_runtime_application_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    return source_application_planned_only_fixture(tmp_path, user_id=user_id, repository=repository)


def rollback_plan_missing_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    return source_application_planned_only_fixture(tmp_path, user_id=user_id, repository=repository)


def no_runtime_mutation_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_no_runtime_mutation_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=True,
        audit_confirmation_present=True,
    )
    return _persist_application(fixture)


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    return no_runtime_application_fixture(tmp_path, user_id=user_id, repository=repository)


def public_answer_key_exposure_forbidden_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_no_public_key_gabarito_safety_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    application.answer_key_publicly_exposed = True
    application.gabarito_publicly_exposed = True
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=True,
        audit_confirmation_present=True,
    )
    return _persist_application(fixture)


def intent_decision_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    return intents_not_apply_allowed_fixture(tmp_path, user_id=user_id, repository=repository)


def surface_decision_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    return surfaces_not_apply_allowed_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_requirements_shape_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    return source_application_planned_only_fixture(tmp_path, user_id=user_id, repository=repository)


def audit_trail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    return missing_runtime_policy_fixture(tmp_path, user_id=user_id, repository=repository)


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoControlledApplyShellFixture, SimuladoControlledApplyShellFixture]:
    owner_fixture = _api_readonly_fixture(tmp_path / "owner", user_id="user-a", repository=repository)
    other_fixture = _api_readonly_fixture(tmp_path / "other", user_id="user-b", repository=repository)
    return _wrap_fixture(owner_fixture), _wrap_fixture(other_fixture)


def api_readonly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    return no_runtime_application_fixture(tmp_path, user_id=user_id, repository=repository)


def mixed_controlled_apply_shell_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_mixed_application_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    _set_preapply_metadata(
        application,
        runtime_policy_present=False,
        explicit_apply_approval_present=False,
        audit_confirmation_present=False,
    )
    return _persist_application(fixture)


def mixed_shell_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    return mixed_controlled_apply_shell_fixture(tmp_path, user_id=user_id, repository=repository)


def incomplete_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoControlledApplyShellFixture:
    fixture = _wrap_fixture(_incomplete_guardrail_fixture(tmp_path, user_id=user_id, repository=repository))
    application = fixture.runtime_progress_application
    assert application is not None
    _set_preapply_metadata(
        application,
        runtime_policy_present=True,
        explicit_apply_approval_present=True,
        audit_confirmation_present=True,
    )
    return _persist_application(fixture)
