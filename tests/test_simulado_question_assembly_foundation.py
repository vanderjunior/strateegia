import json

from app.domain.models import SimuladoBlueprint, SimuladoBlueprintRationale, SimuladoQuestionSlot
from app.repositories.json_store import JsonStudyRepository
from app.services.answer_explanation_guardrails import AnswerExplanationGuardrailService
from app.services.simulado_question_assembly import SimuladoQuestionAssemblyService
from tests.fixtures.question_drafts import (
    ready_cebraspe_assertion_blueprint_fixture,
    ready_fgv_case_mcq_blueprint_fixture,
    ready_pscpp_maritime_blueprint_fixture,
)


FORBIDDEN_FINAL_KEYS = {
    "final_question",
    "executable_question",
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
    "student_attempt",
    "answer_submission",
    "simulado_result",
    "executable_simulado",
    "exam_session",
}


def collect_json_keys(value):
    keys = set()
    if isinstance(value, dict):
        keys.update(value.keys())
        for nested in value.values():
            keys.update(collect_json_keys(nested))
    elif isinstance(value, list):
        for nested in value:
            keys.update(collect_json_keys(nested))
    return keys


def persist_simulado_from_fixture(fixture):
    slot_blueprint = fixture.blueprint_set.slot_blueprints[0]
    simulado = SimuladoBlueprint(
        blueprint_id=fixture.blueprint_set.source_simulado_blueprint_id,
        graph_id=f"graph:{fixture.blueprint_set.source_simulado_blueprint_id}",
        cycle_id=f"cycle:{fixture.blueprint_set.source_simulado_blueprint_id}",
        exam_profile_id=f"exam-profile:{slot_blueprint.board_id or 'unknown'}",
        user_id=fixture.context.user_id,
        exam_board=slot_blueprint.board_id,
        exam_family=slot_blueprint.exam_family,
        format_type=slot_blueprint.format_type,
        question_slots=[
            SimuladoQuestionSlot(
                slot_id=slot_blueprint.source_question_slot_id,
                section_id="section:primary",
                order_index=0,
                target_subject_id=slot_blueprint.target_subject_id,
                target_topic_id=slot_blueprint.target_topic_id,
                target_subtopic_ids=list(slot_blueprint.target_subtopic_ids),
                format_type=slot_blueprint.format_type,
                cognitive_demand=slot_blueprint.cognitive_demand,
                difficulty_hint=slot_blueprint.difficulty_hint,
                generation_style=slot_blueprint.question_kind,
                source_evidence_ids=[item.evidence_id for item in slot_blueprint.source_evidence],
                required_coverage_state="covered",
                readiness_state="ready_for_review",
                confidence=0.8,
                reasoning="fixture simulado question slot",
            )
        ],
        rationale=SimuladoBlueprintRationale(
            summary="fixture simulado blueprint for question assembly",
            source_graph_id=f"graph:{fixture.blueprint_set.source_simulado_blueprint_id}",
            source_cycle_id=f"cycle:{fixture.blueprint_set.source_simulado_blueprint_id}",
            source_exam_profile_id=f"exam-profile:{slot_blueprint.board_id or 'unknown'}",
            confidence=0.8,
        ),
        metadata={"fixture": True},
    )
    fixture.context.repository.save_simulado_blueprint(simulado, user_id=fixture.context.user_id)
    return simulado


def test_simulado_question_assembly_handles_missing_sources_and_no_candidates_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    service = SimuladoQuestionAssemblyService(repository)

    assert service.build_assembly("simulado:missing", user_id="user-a") is None
    assert repository.list_user_simulado_question_assemblies(user_id="user-a") == []

    fixture = ready_cebraspe_assertion_blueprint_fixture(tmp_path / "cebraspe")
    qgb = fixture.context.repository.get_question_generation_blueprint(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )
    assert qgb is not None
    result = service.build_assembly(qgb.source_simulado_blueprint_id, user_id=fixture.context.user_id)

    assert result is None


def test_simulado_question_assembly_creates_ready_for_review_candidate_from_full_chain(tmp_path):
    fixture = ready_cebraspe_assertion_blueprint_fixture(tmp_path)
    persist_simulado_from_fixture(fixture)
    draft_set = fixture.context.service.build_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )
    guardrail_service = AnswerExplanationGuardrailService(fixture.context.repository)
    guardrail = guardrail_service.build_guardrail(draft_set.drafts[0].draft_id, user_id=fixture.context.user_id)
    service = SimuladoQuestionAssemblyService(fixture.context.repository)
    result = service.build_assembly(fixture.blueprint_set.source_simulado_blueprint_id, user_id=fixture.context.user_id)

    assert result is not None
    assert result.readiness_state in {"assembly_ready_for_review", "assembly_needs_review"}
    assert result.total_candidates == 1
    candidate = result.candidates[0]
    assert candidate.source_question_draft_id == draft_set.drafts[0].draft_id
    assert candidate.source_guardrail_id == guardrail.guardrail_id
    assert candidate.readiness_state == "candidate_ready_for_review"
    assert candidate.requires_human_review is True
    assert candidate.not_executable is True
    assert candidate.not_scoreable is True
    assert candidate.draft_summary.draft_stem_preview
    assert candidate.guardrail_summary.no_final_answer_key_generated is True
    assert candidate.guardrail_summary.no_final_explanation_generated is True
    assert candidate.guardrail_summary.no_simulado_execution_enabled is True
    assert candidate.source_evidence_summary.primary_source_available is True


def test_simulado_question_assembly_blocks_candidates_for_missing_draft_guardrail_and_source_issues(tmp_path):
    fixture = ready_fgv_case_mcq_blueprint_fixture(tmp_path / "fgv")
    persist_simulado_from_fixture(fixture)
    draft_set = fixture.context.service.build_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )
    guardrail_service = AnswerExplanationGuardrailService(fixture.context.repository)
    guardrail = guardrail_service.build_guardrail(draft_set.drafts[0].draft_id, user_id=fixture.context.user_id)
    service = SimuladoQuestionAssemblyService(fixture.context.repository)

    missing_draft_result = service.build_assembly(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id="missing-user",
    )
    assert missing_draft_result is None

    missing_guardrail_repo = JsonStudyRepository(tmp_path / "missing-guardrail.json")
    missing_guardrail_fixture = ready_cebraspe_assertion_blueprint_fixture(
        tmp_path / "missing-guardrail",
        repository=missing_guardrail_repo,
    )
    persist_simulado_from_fixture(missing_guardrail_fixture)
    missing_guardrail_fixture.context.service.build_draft_set(
        missing_guardrail_fixture.blueprint_set.blueprint_set_id,
        user_id=missing_guardrail_fixture.context.user_id,
    )
    missing_guardrail_service = SimuladoQuestionAssemblyService(missing_guardrail_repo)
    missing_guardrail_result = missing_guardrail_service.build_assembly(
        missing_guardrail_fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=missing_guardrail_fixture.context.user_id,
    )
    assert missing_guardrail_result is not None
    assert missing_guardrail_result.candidates[0].readiness_state == "candidate_blocked_by_missing_guardrail"

    blocked_repo = JsonStudyRepository(tmp_path / "blocked-guardrail.json")
    blocked_fixture = ready_fgv_case_mcq_blueprint_fixture(tmp_path / "blocked", repository=blocked_repo)
    persist_simulado_from_fixture(blocked_fixture)
    blocked_draft_set = blocked_fixture.context.service.build_draft_set(
        blocked_fixture.blueprint_set.blueprint_set_id,
        user_id=blocked_fixture.context.user_id,
    )
    guardrail_service = AnswerExplanationGuardrailService(blocked_repo)
    blocked_guardrail = guardrail_service.build_guardrail(
        blocked_draft_set.drafts[0].draft_id,
        user_id=blocked_fixture.context.user_id,
    )
    blocked_result = SimuladoQuestionAssemblyService(blocked_repo).build_assembly(
        blocked_fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=blocked_fixture.context.user_id,
    )

    assert blocked_guardrail.answer_key_state == "answer_key_blocked_by_ambiguous_draft"
    assert blocked_result is not None
    assert blocked_result.candidates[0].readiness_state == "candidate_blocked_by_unfinalized_answer"


def test_simulado_question_assembly_blocks_for_non_reviewed_draft_unsupported_format_and_source_flags(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = ready_cebraspe_assertion_blueprint_fixture(tmp_path / "base", repository=repository)
    persist_simulado_from_fixture(fixture)
    draft_set = fixture.context.service.build_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )
    base_draft = draft_set.drafts[0]
    guardrail_service = AnswerExplanationGuardrailService(repository)

    non_ready_draft = base_draft.model_copy(
        update={"draft_id": "question-draft:non-reviewed", "draft_status": "blocked", "draft_readiness": "blocked_by_blueprint"}
    )
    fixture.context.repository.save_question_draft_set(
        draft_set.model_copy(update={"drafts": [non_ready_draft]}),
        user_id=fixture.context.user_id,
    )
    guardrail_service.build_guardrail(non_ready_draft.draft_id, user_id=fixture.context.user_id)
    non_ready_result = SimuladoQuestionAssemblyService(repository).build_assembly(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )
    assert non_ready_result is not None
    assert non_ready_result.candidates[0].readiness_state == "candidate_blocked_by_non_reviewed_draft"

    unsupported_repo = JsonStudyRepository(tmp_path / "unsupported.json")
    unsupported_fixture = ready_cebraspe_assertion_blueprint_fixture(tmp_path / "unsupported", repository=unsupported_repo)
    persist_simulado_from_fixture(unsupported_fixture)
    unsupported_draft_set = unsupported_fixture.context.service.build_draft_set(
        unsupported_fixture.blueprint_set.blueprint_set_id,
        user_id=unsupported_fixture.context.user_id,
    )
    unsupported_draft = unsupported_draft_set.drafts[0].model_copy(
        update={"draft_id": "question-draft:unsupported", "question_kind": "essay_future_format", "format_type": "unsupported_format"}
    )
    unsupported_fixture.context.repository.save_question_draft_set(
        unsupported_draft_set.model_copy(update={"drafts": [unsupported_draft]}),
        user_id=unsupported_fixture.context.user_id,
    )
    guardrail_service = AnswerExplanationGuardrailService(unsupported_repo)
    guardrail_service.build_guardrail(unsupported_draft.draft_id, user_id=unsupported_fixture.context.user_id)
    unsupported_result = SimuladoQuestionAssemblyService(unsupported_repo).build_assembly(
        unsupported_fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=unsupported_fixture.context.user_id,
    )
    assert unsupported_result is not None
    assert unsupported_result.candidates[0].readiness_state == "candidate_blocked_by_unsupported_format"

    source_issue_repo = JsonStudyRepository(tmp_path / "source-issue.json")
    source_issue_fixture = ready_cebraspe_assertion_blueprint_fixture(tmp_path / "source-issue", repository=source_issue_repo)
    persist_simulado_from_fixture(source_issue_fixture)
    source_issue_draft_set = source_issue_fixture.context.service.build_draft_set(
        source_issue_fixture.blueprint_set.blueprint_set_id,
        user_id=source_issue_fixture.context.user_id,
    )
    weak_draft = source_issue_draft_set.drafts[0].model_copy(
        update={
            "draft_id": "question-draft:weak-source",
            "source_references": [
                source_issue_draft_set.drafts[0].source_references[0].model_copy(
                    update={"evidence_strength": "weak"}
                )
            ],
        }
    )
    source_issue_fixture.context.repository.save_question_draft_set(
        source_issue_draft_set.model_copy(update={"drafts": [weak_draft]}),
        user_id=source_issue_fixture.context.user_id,
    )
    guardrail_service = AnswerExplanationGuardrailService(source_issue_repo)
    weak_guardrail = guardrail_service.build_guardrail(weak_draft.draft_id, user_id=source_issue_fixture.context.user_id)
    source_issue_result = SimuladoQuestionAssemblyService(source_issue_repo).build_assembly(
        source_issue_fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=source_issue_fixture.context.user_id,
    )

    assert weak_guardrail is not None
    assert source_issue_result is not None
    assert source_issue_result.candidates[0].readiness_state in {
        "candidate_needs_review",
        "candidate_blocked_by_source_issue",
    }


def test_simulado_question_assembly_preserves_no_execution_no_scoring_and_idempotency(tmp_path):
    fixture = ready_pscpp_maritime_blueprint_fixture(tmp_path)
    persist_simulado_from_fixture(fixture)
    draft_set = fixture.context.service.build_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )
    guardrail_service = AnswerExplanationGuardrailService(fixture.context.repository)
    guardrail_service.build_guardrail(draft_set.drafts[0].draft_id, user_id=fixture.context.user_id)
    service = SimuladoQuestionAssemblyService(fixture.context.repository)

    first = service.build_assembly(fixture.blueprint_set.source_simulado_blueprint_id, user_id=fixture.context.user_id)
    second = service.build_assembly(fixture.blueprint_set.source_simulado_blueprint_id, user_id=fixture.context.user_id)
    by_source = fixture.context.repository.get_simulado_question_assembly(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )
    by_id = fixture.context.repository.get_simulado_question_assembly_by_id(
        first.assembly_id,
        user_id=fixture.context.user_id,
    )
    dumped = first.model_dump(mode="json")
    dumped_keys = collect_json_keys(dumped)
    dumped_text = json.dumps(dumped, ensure_ascii=True)

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert by_source is not None
    assert by_id is not None
    assert first.requires_human_review is True
    assert first.not_executable is True
    assert first.not_scoreable is True
    assert first.no_student_attempts_enabled is True
    assert first.no_progress_mutation is True
    assert first.no_final_questions_created is True
    assert first.no_final_answer_keys_created is True
    assert first.no_final_explanations_created is True
    for key in FORBIDDEN_FINAL_KEYS:
        assert key not in dumped_keys
    assert "password_hash" not in dumped_text
    assert "/Users/" not in dumped_text
    assert "/private/" not in dumped_text
