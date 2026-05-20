from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SimuladoExecutionShell, SimuladoFinalApprovalArtifact
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_execution_shell import SimuladoExecutionShellService
from tests.fixtures.simulado_final_approvals import (
    SimuladoFinalApprovalFixture,
    assembly_json_keys,
    block_decision_fixture as _block_decision_fixture,
    bounded_audit_reason_fixture as _bounded_audit_reason_fixture,
    build_approval_artifact,
    explicit_approve_for_future_execution_review_fixture as _explicit_approve_for_future_execution_review_fixture,
    idempotency_fixture as _idempotency_fixture,
    mark_not_reviewed_decision_fixture as _mark_not_reviewed_decision_fixture,
    mixed_decision_payload,
    mixed_decision_payload_fixture as _mixed_decision_payload_fixture,
    no_decision_payload_fixture as _no_decision_payload_fixture,
    no_execution_submission_score_safety_fixture as _no_execution_submission_score_safety_fixture,
    reject_decision_fixture as _reject_decision_fixture,
    request_revision_decision_fixture as _request_revision_decision_fixture,
    single_decision_payload,
    user_scope_fixture as _user_scope_fixture,
)


@dataclass
class SimuladoExecutionShellFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoExecutionShellService
    user_id: str


@dataclass
class SimuladoExecutionShellFixture:
    context: SimuladoExecutionShellFixtureContext
    final_approval_fixture: SimuladoFinalApprovalFixture | None
    final_approval_artifact: SimuladoFinalApprovalArtifact | None
    missing_approval_artifact_id: str | None = None


def _wrap_fixture(
    approval_fixture: SimuladoFinalApprovalFixture,
    *,
    decision_payload: dict[str, object] | None = None,
) -> SimuladoExecutionShellFixture:
    artifact = build_approval_artifact(approval_fixture, decision_payload=decision_payload)
    assert artifact is not None
    return SimuladoExecutionShellFixture(
        context=SimuladoExecutionShellFixtureContext(
            repository=approval_fixture.context.repository,
            service=SimuladoExecutionShellService(approval_fixture.context.repository),
            user_id=approval_fixture.context.user_id,
        ),
        final_approval_fixture=approval_fixture,
        final_approval_artifact=artifact,
    )


def build_execution_shell(
    fixture: SimuladoExecutionShellFixture,
) -> SimuladoExecutionShell | None:
    source_id = fixture.missing_approval_artifact_id
    if fixture.final_approval_artifact is not None:
        source_id = fixture.final_approval_artifact.approval_artifact_id
    assert source_id is not None
    return fixture.context.service.build_execution_shell(
        source_id,
        user_id=fixture.context.user_id,
    )


def missing_final_approval_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    repository = repository or JsonStudyRepository(tmp_path / "study_data.json")
    return SimuladoExecutionShellFixture(
        context=SimuladoExecutionShellFixtureContext(
            repository=repository,
            service=SimuladoExecutionShellService(repository),
            user_id=user_id,
        ),
        final_approval_fixture=None,
        final_approval_artifact=None,
        missing_approval_artifact_id="simulado-final-approval:missing",
    )


def no_approved_candidates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    return _wrap_fixture(
        _no_decision_payload_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def approved_candidates_not_executable_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    approval_fixture = _explicit_approve_for_future_execution_review_fixture(
        tmp_path, user_id=user_id, repository=repository
    )
    return _wrap_fixture(
        approval_fixture,
        decision_payload=single_decision_payload(
            approval_fixture,
            decision_type="approve_for_future_execution_review",
            reason="Approved for future execution review only.",
        ),
    )


def missing_final_questions_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    return approved_candidates_not_executable_fixture(
        tmp_path, user_id=user_id, repository=repository
    )


def missing_final_answer_keys_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    return approved_candidates_not_executable_fixture(
        tmp_path, user_id=user_id, repository=repository
    )


def missing_final_explanations_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    return approved_candidates_not_executable_fixture(
        tmp_path, user_id=user_id, repository=repository
    )


def mixed_approval_states_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    approval_fixture = _mixed_decision_payload_fixture(
        tmp_path, user_id=user_id, repository=repository
    )
    return _wrap_fixture(
        approval_fixture,
        decision_payload=mixed_decision_payload(approval_fixture),
    )


def ordering_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    return mixed_approval_states_fixture(
        tmp_path, user_id=user_id, repository=repository
    )


def disabled_flags_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    return approved_candidates_not_executable_fixture(
        tmp_path, user_id=user_id, repository=repository
    )


def no_attempt_submission_score_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    approval_fixture = _no_execution_submission_score_safety_fixture(
        tmp_path, user_id=user_id, repository=repository
    )
    return _wrap_fixture(
        approval_fixture,
        decision_payload=single_decision_payload(
            approval_fixture,
            decision_type="approve_for_future_execution_review",
            reason="Safety fixture approval only.",
        ),
    )


def bounded_summary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    approval_fixture = _bounded_audit_reason_fixture(
        tmp_path, user_id=user_id, repository=repository
    )
    return _wrap_fixture(
        approval_fixture,
        decision_payload=single_decision_payload(
            approval_fixture,
            decision_type="approve_for_future_execution_review",
            reason="Safe bounded execution shell fixture approval only.",
        ),
    )


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoExecutionShellFixture, SimuladoExecutionShellFixture]:
    owner_fixture, other_fixture = _user_scope_fixture(tmp_path, repository=repository)
    owner = _wrap_fixture(
        owner_fixture,
        decision_payload=single_decision_payload(
            owner_fixture,
            decision_type="approve_for_future_execution_review",
            reason="Owner execution shell fixture approval only.",
        ),
    )
    other = _wrap_fixture(
        other_fixture,
        decision_payload=single_decision_payload(
            other_fixture,
            decision_type="approve_for_future_execution_review",
            reason="Other execution shell fixture approval only.",
        ),
    )
    return owner, other


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoExecutionShellFixture:
    approval_fixture = _idempotency_fixture(tmp_path, user_id=user_id, repository=repository)
    return _wrap_fixture(
        approval_fixture,
        decision_payload=single_decision_payload(
            approval_fixture,
            decision_type="approve_for_future_execution_review",
            reason="Deterministic execution shell idempotency approval only.",
        ),
    )

