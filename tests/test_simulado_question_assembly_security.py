import json

from app.domain.models import SimuladoBlueprint, SimuladoBlueprintRationale, SimuladoQuestionSlot
from app.repositories.json_store import JsonStudyRepository
from app.services.answer_explanation_guardrails import AnswerExplanationGuardrailService
from app.services.simulado_question_assembly import SimuladoQuestionAssemblyService
from tests.fixtures.question_drafts import (
    long_snippet_bounds_fixture,
    ready_cebraspe_assertion_blueprint_fixture,
)


def prepare_chain(fixture):
    slot_blueprint = fixture.blueprint_set.slot_blueprints[0]
    fixture.context.repository.save_simulado_blueprint(
        SimuladoBlueprint(
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
                summary="fixture simulado blueprint for question assembly security",
                source_graph_id=f"graph:{fixture.blueprint_set.source_simulado_blueprint_id}",
                source_cycle_id=f"cycle:{fixture.blueprint_set.source_simulado_blueprint_id}",
                source_exam_profile_id=f"exam-profile:{slot_blueprint.board_id or 'unknown'}",
                confidence=0.8,
            ),
            metadata={"fixture": True},
        ),
        user_id=fixture.context.user_id,
    )
    draft_set = fixture.context.service.build_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )
    AnswerExplanationGuardrailService(fixture.context.repository).build_guardrail(
        draft_set.drafts[0].draft_id,
        user_id=fixture.context.user_id,
    )
    return draft_set


def test_simulado_question_assembly_summaries_are_bounded_and_sanitized(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = long_snippet_bounds_fixture(tmp_path, repository=repository)
    prepare_chain(fixture)
    result = SimuladoQuestionAssemblyService(repository).build_assembly(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )
    dumped = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)
    candidate = result.candidates[0]

    assert candidate.draft_summary.draft_stem_preview is None or len(candidate.draft_summary.draft_stem_preview) <= 240
    assert candidate.draft_summary.draft_command_preview is None or len(candidate.draft_summary.draft_command_preview) <= 160
    assert all(len(item) <= 240 for item in candidate.source_evidence_summary.safe_snippets)
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped


def test_simulado_question_assembly_does_not_leak_or_mutate_runtime_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = ready_cebraspe_assertion_blueprint_fixture(tmp_path, repository=repository)
    draft_set = prepare_chain(fixture)
    before_draft_set = repository.get_question_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )
    before_guardrails = repository.list_user_answer_explanation_guardrails(user_id=fixture.context.user_id)

    result = SimuladoQuestionAssemblyService(repository).build_assembly(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )
    dumped = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)
    after_draft_set = repository.get_question_draft_set(
        fixture.blueprint_set.blueprint_set_id,
        user_id=fixture.context.user_id,
    )
    after_guardrails = repository.list_user_answer_explanation_guardrails(user_id=fixture.context.user_id)

    assert draft_set.drafts[0].draft_id in dumped
    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "raw_runtime_block" not in dumped
    assert "data:image" not in dumped
    assert before_draft_set.model_dump(mode="json") == after_draft_set.model_dump(mode="json")
    assert [item.model_dump(mode="json") for item in before_guardrails] == [
        item.model_dump(mode="json") for item in after_guardrails
    ]
