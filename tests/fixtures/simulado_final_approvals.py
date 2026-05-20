from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import SimuladoFinalApprovalArtifact, SimuladoFinalizationGuardrail
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_final_approval import SimuladoFinalApprovalService
from tests.fixtures.simulado_finalization_guardrails import (
    SimuladoFinalizationGuardrailFixture,
    assembly_json_keys,
    bounded_summary_fixture as _bounded_summary_fixture,
    build_finalization_guardrail,
    idempotency_fixture as _idempotency_fixture,
    mixed_ready_blocked_review_fixture as _mixed_ready_blocked_review_fixture,
    non_final_assembly_fixture as _non_final_assembly_fixture,
    ready_candidates_not_finalizable_fixture as _ready_candidates_not_finalizable_fixture,
    user_scope_fixture as _user_scope_fixture,
)


@dataclass
class SimuladoFinalApprovalFixtureContext:
    repository: JsonStudyRepository
    service: SimuladoFinalApprovalService
    user_id: str


@dataclass
class SimuladoFinalApprovalFixture:
    context: SimuladoFinalApprovalFixtureContext
    finalization_guardrail: SimuladoFinalizationGuardrail


def _wrap_fixture(
    finalization_fixture: SimuladoFinalizationGuardrailFixture,
) -> SimuladoFinalApprovalFixture:
    finalization_guardrail = build_finalization_guardrail(finalization_fixture)
    assert finalization_guardrail is not None
    return SimuladoFinalApprovalFixture(
        context=SimuladoFinalApprovalFixtureContext(
            repository=finalization_fixture.context.repository,
            service=SimuladoFinalApprovalService(finalization_fixture.context.repository),
            user_id=finalization_fixture.context.user_id,
        ),
        finalization_guardrail=finalization_guardrail,
    )


def build_approval_artifact(
    fixture: SimuladoFinalApprovalFixture,
    *,
    decision_payload: dict[str, object] | None = None,
) -> SimuladoFinalApprovalArtifact | None:
    return fixture.context.service.build_approval_artifact(
        fixture.finalization_guardrail.finalization_guardrail_id,
        user_id=fixture.context.user_id,
        decision_payload=decision_payload,
    )


def first_candidate_id(fixture: SimuladoFinalApprovalFixture) -> str | None:
    if not fixture.finalization_guardrail.candidate_summaries:
        return None
    return fixture.finalization_guardrail.candidate_summaries[0].source_question_candidate_id


def candidate_ids(fixture: SimuladoFinalApprovalFixture) -> list[str]:
    return [
        item.source_question_candidate_id
        for item in fixture.finalization_guardrail.candidate_summaries
        if item.source_question_candidate_id
    ]


def single_decision_payload(
    fixture: SimuladoFinalApprovalFixture,
    *,
    decision_type: str,
    reason: str,
    source_candidate_id: str | None = None,
    reviewer_id: str | None = None,
) -> dict[str, object]:
    candidate_id = source_candidate_id or first_candidate_id(fixture)
    assert candidate_id is not None
    decision: dict[str, object] = {
        "source_candidate_id": candidate_id,
        "decision_type": decision_type,
        "reason": reason,
    }
    if reviewer_id is not None:
        decision["reviewer_id"] = reviewer_id
    return {"decisions": [decision]}


def mixed_decision_payload(fixture: SimuladoFinalApprovalFixture) -> dict[str, object]:
    decisions: list[dict[str, object]] = []
    decision_types = [
        "approve_for_future_execution_review",
        "reject",
        "request_revision",
        "block",
        "mark_not_reviewed",
    ]
    for index, candidate_id in enumerate(candidate_ids(fixture)):
        decisions.append(
            {
                "source_candidate_id": candidate_id,
                "decision_type": decision_types[index % len(decision_types)],
                "reason": f"Deterministic fixture decision {index}.",
            }
        )
    return {"decisions": decisions}


def no_decision_payload_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _ready_candidates_not_finalizable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def explicit_approve_for_future_execution_review_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _ready_candidates_not_finalizable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def reject_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _ready_candidates_not_finalizable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def request_revision_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _ready_candidates_not_finalizable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def block_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _ready_candidates_not_finalizable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def mark_not_reviewed_decision_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _ready_candidates_not_finalizable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def mixed_decision_payload_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _mixed_ready_blocked_review_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def blocked_guardrail_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _non_final_assembly_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def final_readiness_flags_false_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _ready_candidates_not_finalizable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def no_execution_submission_score_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _ready_candidates_not_finalizable_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def bounded_audit_reason_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _bounded_summary_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoFinalApprovalFixture, SimuladoFinalApprovalFixture]:
    owner_fixture, other_fixture = _user_scope_fixture(tmp_path, repository=repository)
    return _wrap_fixture(owner_fixture), _wrap_fixture(other_fixture)


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoFinalApprovalFixture:
    return _wrap_fixture(
        _idempotency_fixture(tmp_path, user_id=user_id, repository=repository)
    )
