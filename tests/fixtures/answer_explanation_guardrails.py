from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    QuestionDraft,
    QuestionDraftSet,
    QuestionDraftSourceReference,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.answer_explanation_guardrails import AnswerExplanationGuardrailService
from tests.fixtures.question_drafts import (
    long_snippet_bounds_fixture,
    ready_cebraspe_assertion_blueprint_fixture,
    ready_direct_multiple_choice_blueprint_fixture,
    ready_fgv_case_mcq_blueprint_fixture,
    ready_pscpp_maritime_blueprint_fixture,
    source_review_needed_fixture,
)


@dataclass
class GuardrailFixtureContext:
    repository: JsonStudyRepository
    service: AnswerExplanationGuardrailService
    user_id: str


@dataclass
class GuardrailDraftFixture:
    context: GuardrailFixtureContext
    draft_set: QuestionDraftSet
    draft: QuestionDraft


def _build_draft_fixture(base_fixture) -> GuardrailDraftFixture:
    draft_set = base_fixture.context.service.build_draft_set(
        base_fixture.blueprint_set.blueprint_set_id,
        user_id=base_fixture.context.user_id,
    )
    draft = draft_set.drafts[0]
    return GuardrailDraftFixture(
        context=GuardrailFixtureContext(
            repository=base_fixture.context.repository,
            service=AnswerExplanationGuardrailService(base_fixture.context.repository),
            user_id=base_fixture.context.user_id,
        ),
        draft_set=draft_set,
        draft=draft,
    )


def _persist_variant(
    fixture: GuardrailDraftFixture,
    *,
    draft: QuestionDraft,
    draft_set: QuestionDraftSet | None = None,
) -> GuardrailDraftFixture:
    new_set = draft_set or fixture.draft_set.model_copy(update={"drafts": [draft]})
    fixture.context.repository.save_question_draft_set(new_set, user_id=fixture.context.user_id)
    return GuardrailDraftFixture(
        context=fixture.context,
        draft_set=new_set,
        draft=draft,
    )


def cebraspe_assertion_draft_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    return _build_draft_fixture(
        ready_cebraspe_assertion_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def fgv_placeholder_mcq_draft_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    return _build_draft_fixture(
        ready_fgv_case_mcq_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def pscpp_technical_maritime_draft_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    return _build_draft_fixture(
        ready_pscpp_maritime_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def direct_multiple_choice_placeholder_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    return _build_draft_fixture(
        ready_direct_multiple_choice_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def non_ready_draft_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    fixture = cebraspe_assertion_draft_fixture(tmp_path, user_id=user_id, repository=repository)
    draft = fixture.draft.model_copy(
        update={
            "draft_id": f"{fixture.draft.draft_id}:non-ready",
            "draft_status": "blocked",
            "draft_readiness": "blocked_by_blueprint",
        }
    )
    return _persist_variant(fixture, draft=draft)


def missing_source_draft_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    fixture = cebraspe_assertion_draft_fixture(tmp_path, user_id=user_id, repository=repository)
    draft = fixture.draft.model_copy(
        update={
            "draft_id": f"{fixture.draft.draft_id}:missing-source",
            "source_references": [],
            "validation_summary": fixture.draft.validation_summary.model_copy(
                update={"source_grounded": False, "has_required_source_evidence": False}
            ),
        }
    )
    return _persist_variant(fixture, draft=draft)


def weak_source_draft_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    fixture = cebraspe_assertion_draft_fixture(tmp_path, user_id=user_id, repository=repository)
    weak_reference = fixture.draft.source_references[0].model_copy(
        update={
            "evidence_strength": "weak",
            "safe_snippet": "Trecho curto e ainda insuficiente para sustentar uma decisao segura.",
        }
    )
    draft = fixture.draft.model_copy(
        update={
            "draft_id": f"{fixture.draft.draft_id}:weak-source",
            "source_references": [weak_reference],
        }
    )
    return _persist_variant(fixture, draft=draft)


def ambiguous_source_draft_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    return _build_draft_fixture(
        source_review_needed_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def unsupported_format_draft_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    fixture = cebraspe_assertion_draft_fixture(tmp_path, user_id=user_id, repository=repository)
    draft = fixture.draft.model_copy(
        update={
            "draft_id": f"{fixture.draft.draft_id}:unsupported",
            "question_kind": "essay_future_format",
            "format_type": "unsupported_format",
            "draft_option_placeholders": [],
            "draft_statement": None,
        }
    )
    return _persist_variant(fixture, draft=draft)


def long_safe_snippet_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    return _build_draft_fixture(
        long_snippet_bounds_fixture(tmp_path, user_id=user_id, repository=repository)
    )


def explanation_outline_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    return cebraspe_assertion_draft_fixture(tmp_path, user_id=user_id, repository=repository)


def no_final_content_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    return fgv_placeholder_mcq_draft_fixture(tmp_path, user_id=user_id, repository=repository)


def mixed_guardrail_set_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> list[GuardrailDraftFixture]:
    repo = repository
    return [
        cebraspe_assertion_draft_fixture(tmp_path / "cebraspe", user_id=user_id, repository=repo),
        fgv_placeholder_mcq_draft_fixture(tmp_path / "fgv", user_id=user_id, repository=repo),
        pscpp_technical_maritime_draft_fixture(tmp_path / "pscpp", user_id=user_id, repository=repo),
        missing_source_draft_fixture(tmp_path / "missing", user_id=user_id, repository=repo),
        unsupported_format_draft_fixture(tmp_path / "unsupported", user_id=user_id, repository=repo),
    ]


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[GuardrailDraftFixture, GuardrailDraftFixture]:
    repo = repository or JsonStudyRepository(tmp_path / "study_data.json")
    owner = cebraspe_assertion_draft_fixture(tmp_path / "owner", user_id="user-a", repository=repo)
    other = cebraspe_assertion_draft_fixture(tmp_path / "other", user_id="user-b", repository=repo)
    return owner, other


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> GuardrailDraftFixture:
    return fgv_placeholder_mcq_draft_fixture(tmp_path, user_id=user_id, repository=repository)


def guardrail_json_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(guardrail_json_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(guardrail_json_keys(item))
        return keys
    return set()
