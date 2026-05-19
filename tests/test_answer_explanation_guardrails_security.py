import json

from app.repositories.json_store import JsonStudyRepository
from app.services.answer_explanation_guardrails import AnswerExplanationGuardrailService
from tests.fixtures.question_drafts import (
    long_snippet_bounds_fixture,
    ready_cebraspe_assertion_blueprint_fixture,
)


def build_draft_set(fixture):
    return fixture.context.service.build_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )


def test_answer_explanation_guardrails_snippets_are_bounded_and_sanitized(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = long_snippet_bounds_fixture(tmp_path, repository=repository)
    draft_set = build_draft_set(fixture)
    guardrail = AnswerExplanationGuardrailService(repository).build_guardrail(
        draft_set.drafts[0].draft_id,
        user_id=fixture.context.user_id,
    )
    dumped = json.dumps(guardrail.model_dump(mode="json"), ensure_ascii=True)

    assert guardrail.source_support_assessment.safe_snippets
    assert all(len(item) <= 240 for item in guardrail.source_support_assessment.safe_snippets)
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped


def test_answer_explanation_guardrails_do_not_leak_or_mutate_question_drafts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = ready_cebraspe_assertion_blueprint_fixture(tmp_path, repository=repository)
    draft_set = build_draft_set(fixture)
    before_draft_set = repository.get_question_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )

    guardrail_service = AnswerExplanationGuardrailService(repository)
    result = guardrail_service.build_guardrail(
        draft_set.drafts[0].draft_id,
        user_id=fixture.context.user_id,
    )
    dumped = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)
    after_draft_set = repository.get_question_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )

    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "raw_runtime_block" not in dumped
    assert "data:image" not in dumped
    assert before_draft_set.model_dump(mode="json") == after_draft_set.model_dump(mode="json")
