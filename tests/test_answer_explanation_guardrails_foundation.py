import json

from app.repositories.json_store import JsonStudyRepository
from app.services.answer_explanation_guardrails import (
    MAX_EXPLANATION_OUTLINE_LENGTH,
    MAX_SAFE_SNIPPET_LENGTH,
    AnswerExplanationGuardrailService,
)
from tests.fixtures.question_drafts import (
    ready_cebraspe_assertion_blueprint_fixture,
    ready_direct_multiple_choice_blueprint_fixture,
    ready_fgv_case_mcq_blueprint_fixture,
    ready_pscpp_maritime_blueprint_fixture,
    source_review_needed_fixture,
    unsupported_question_kind_fixture,
)
from tests.fixtures.question_generation_blueprints import collect_keys


FORBIDDEN_FINAL_KEYS = {
    "final_answer_key",
    "correct_option",
    "correct_answer",
    "gabarito",
    "gabarito_final",
    "final_explanation",
    "correction_rule",
    "auto_correction",
    "score_rule",
    "scoring_result",
    "executable_question",
    "simulado_ready_question",
    "approved_answer",
    "validated_answer",
}


def build_draft_set(fixture):
    return fixture.context.service.build_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )


def build_guardrail_from_fixture(fixture):
    draft_set = build_draft_set(fixture)
    draft = draft_set.drafts[0]
    service = AnswerExplanationGuardrailService(fixture.context.repository)
    return draft_set, draft, service.build_guardrail(draft.draft_id, user_id=fixture.context.user_id)


def test_answer_explanation_guardrails_blocks_non_ready_and_missing_source_drafts(tmp_path):
    fixture = ready_cebraspe_assertion_blueprint_fixture(tmp_path / "ready")
    draft_set = build_draft_set(fixture)
    repository = fixture.context.repository
    service = AnswerExplanationGuardrailService(repository)

    non_ready_draft = draft_set.drafts[0].model_copy(
        update={
            "draft_status": "blocked",
            "draft_readiness": "blocked_by_blueprint",
        }
    )
    non_ready_set = draft_set.model_copy(update={"drafts": [non_ready_draft]})
    repository.save_question_draft_set(non_ready_set, user_id=fixture.context.user_id)
    non_ready_guardrail = service.build_guardrail(non_ready_draft.draft_id, user_id=fixture.context.user_id)

    assert non_ready_guardrail.status == "blocked"
    assert non_ready_guardrail.answer_key_state == "answer_key_blocked_by_non_ready_draft"
    assert non_ready_guardrail.explanation_state == "explanation_blocked_by_non_ready_draft"
    assert non_ready_guardrail.candidate_answer_key.candidate_value is None
    assert non_ready_guardrail.candidate_explanation.explanation_outline is None
    assert non_ready_guardrail.review_required is True
    assert non_ready_guardrail.finalization_blocked is True

    missing_source_draft = draft_set.drafts[0].model_copy(
        update={
            "draft_id": "question-draft:missing-source",
            "source_references": [],
            "validation_summary": draft_set.drafts[0].validation_summary.model_copy(
                update={"source_grounded": False, "has_required_source_evidence": False}
            ),
        }
    )
    missing_source_set = draft_set.model_copy(update={"drafts": [missing_source_draft]})
    repository.save_question_draft_set(missing_source_set, user_id=fixture.context.user_id)
    missing_source_guardrail = service.build_guardrail(
        missing_source_draft.draft_id,
        user_id=fixture.context.user_id,
    )

    assert missing_source_guardrail.status == "blocked"
    assert missing_source_guardrail.answer_key_state == "answer_key_blocked_by_missing_source"
    assert missing_source_guardrail.explanation_state == "explanation_blocked_by_missing_source"
    assert missing_source_guardrail.source_support_assessment.missing_source is True
    assert missing_source_guardrail.candidate_answer_key.candidate_value is None
    assert missing_source_guardrail.candidate_explanation.explanation_outline is None


def test_answer_explanation_guardrails_handle_weak_source_conservatively(tmp_path):
    fixture = source_review_needed_fixture(tmp_path)
    _, _, guardrail = build_guardrail_from_fixture(fixture)

    assert guardrail.status == "needs_review"
    assert guardrail.answer_key_state in {
        "answer_key_needs_human_review",
        "answer_key_blocked_by_insufficient_evidence",
    }
    assert guardrail.explanation_state in {
        "explanation_needs_human_review",
        "explanation_blocked_by_insufficient_evidence",
    }
    assert guardrail.source_support_assessment.ambiguous_support is True
    assert guardrail.review_required is True
    assert guardrail.finalization_blocked is True


def test_answer_explanation_guardrails_assess_cebraspe_assertion_judgement_without_final_gabarito(tmp_path):
    _, _, guardrail = build_guardrail_from_fixture(ready_cebraspe_assertion_blueprint_fixture(tmp_path))

    assert guardrail.status == "ready_for_review"
    assert guardrail.answer_key_state == "answer_key_candidate_ready_for_review"
    assert guardrail.explanation_state == "explanation_candidate_ready_for_review"
    assert guardrail.candidate_answer_key.allowed_values == ["C", "E"]
    assert guardrail.candidate_answer_key.candidate_value is None
    assert guardrail.candidate_answer_key.requires_review is True
    assert guardrail.candidate_answer_key.finalization_blocked is True
    assert guardrail.candidate_explanation.explanation_outline is not None
    assert len(guardrail.candidate_explanation.explanation_outline) <= MAX_EXPLANATION_OUTLINE_LENGTH
    assert guardrail.review_required is True
    assert guardrail.finalization_blocked is True


def test_answer_explanation_guardrails_block_answer_key_for_placeholder_multiple_choice_formats(tmp_path):
    _, _, fgv_guardrail = build_guardrail_from_fixture(ready_fgv_case_mcq_blueprint_fixture(tmp_path / "fgv"))
    _, _, direct_guardrail = build_guardrail_from_fixture(
        ready_direct_multiple_choice_blueprint_fixture(tmp_path / "direct")
    )

    assert fgv_guardrail.status == "needs_review"
    assert fgv_guardrail.answer_key_state == "answer_key_blocked_by_ambiguous_draft"
    assert fgv_guardrail.explanation_state == "explanation_candidate_ready_for_review"
    assert fgv_guardrail.candidate_answer_key.allowed_values == ["A", "B", "C", "D", "E"]
    assert fgv_guardrail.candidate_answer_key.candidate_value is None
    assert fgv_guardrail.candidate_explanation.explanation_outline is not None

    assert direct_guardrail.status == "needs_review"
    assert direct_guardrail.answer_key_state == "answer_key_blocked_by_ambiguous_draft"
    assert direct_guardrail.candidate_answer_key.allowed_values == ["A", "B", "C", "D"]
    assert direct_guardrail.candidate_answer_key.candidate_value is None
    assert direct_guardrail.candidate_explanation.explanation_outline is not None


def test_answer_explanation_guardrails_require_human_review_for_technical_maritime_drafts(tmp_path):
    _, _, guardrail = build_guardrail_from_fixture(ready_pscpp_maritime_blueprint_fixture(tmp_path))

    codes = {item.code for item in guardrail.validation_findings}
    warning_codes = {item.code for item in guardrail.warnings}

    assert guardrail.status == "needs_review"
    assert guardrail.answer_key_state == "answer_key_needs_human_review"
    assert guardrail.explanation_state == "explanation_candidate_ready_for_review"
    assert guardrail.candidate_answer_key.candidate_value is None
    assert "technical_term_review_required" in codes or "technical_term_review_required" in warning_codes
    assert "source_topic_mapping_required" in codes or "source_topic_mapping_required" in warning_codes
    assert "human_review_required" in codes or "human_review_required" in warning_codes
    assert guardrail.review_required is True
    assert guardrail.finalization_blocked is True


def test_answer_explanation_guardrails_mark_unsupported_formats_without_final_candidates(tmp_path):
    fixture = ready_cebraspe_assertion_blueprint_fixture(tmp_path)
    draft_set = build_draft_set(fixture)
    repository = fixture.context.repository
    service = AnswerExplanationGuardrailService(repository)
    unsupported_draft = draft_set.drafts[0].model_copy(
        update={
            "draft_id": "question-draft:unsupported",
            "question_kind": "essay_future_format",
            "format_type": "unsupported_format",
        }
    )
    unsupported_set = draft_set.model_copy(update={"drafts": [unsupported_draft]})
    repository.save_question_draft_set(unsupported_set, user_id=fixture.context.user_id)

    guardrail = service.build_guardrail(unsupported_draft.draft_id, user_id=fixture.context.user_id)

    assert guardrail.status == "unsupported"
    assert guardrail.answer_key_state == "answer_key_blocked_by_unsupported_format"
    assert guardrail.explanation_state == "explanation_blocked_by_unsupported_format"
    assert guardrail.candidate_answer_key.candidate_value is None
    assert guardrail.candidate_explanation.explanation_outline is None


def test_answer_explanation_guardrails_preserve_no_final_content_and_persistence(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = unsupported_question_kind_fixture(tmp_path / "unused", repository=repository)
    del fixture
    foundation_fixture = ready_fgv_case_mcq_blueprint_fixture(tmp_path / "foundation", repository=repository)
    _, draft, first = build_guardrail_from_fixture(foundation_fixture)
    service = AnswerExplanationGuardrailService(repository)
    second = service.build_guardrail(draft.draft_id, user_id=foundation_fixture.context.user_id)
    by_source = repository.get_answer_explanation_guardrail(
        draft.draft_id,
        user_id=foundation_fixture.context.user_id,
    )
    by_id = repository.get_answer_explanation_guardrail_by_id(
        first.guardrail_id,
        user_id=foundation_fixture.context.user_id,
    )
    dumped = first.model_dump(mode="json")
    serialized = json.dumps(dumped, ensure_ascii=True)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert first.no_final_answer_key_generated is True
    assert first.no_final_explanation_generated is True
    assert first.no_simulado_execution_enabled is True
    assert len(first.source_support_assessment.safe_snippets) <= len(first.candidate_explanation.source_anchor_ids) + 1
    assert all(len(item) <= MAX_SAFE_SNIPPET_LENGTH for item in first.source_support_assessment.safe_snippets)
    for key in FORBIDDEN_FINAL_KEYS:
        assert key not in collect_keys(dumped)
    assert "password_hash" not in serialized
    assert "/Users/" not in serialized
    assert "/private/" not in serialized
    assert "data:image" not in serialized
