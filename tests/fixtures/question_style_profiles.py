from __future__ import annotations

from app.services.question_draft_generation import QuestionDraftGenerationService
from app.services.question_style_profiles import (
    PSCPP_EXAM_PROFILE_ID,
    enrich_question_generation_blueprint_with_style_profile,
    get_pscpp_question_style_profile,
)
from tests.fixtures.question_generation_blueprints import (
    QuestionGenerationFixture,
    build_slot,
    missing_source_slot_fixture,
    persist_simulado,
    pscpp_maritime_fixture,
)


def pscpp_profile_fixture() -> dict[str, object]:
    return get_pscpp_question_style_profile()


def pscpp_ready_blueprint_fixture(tmp_path) -> QuestionGenerationFixture:
    return pscpp_maritime_fixture(tmp_path)


def pscpp_missing_source_blueprint_fixture(tmp_path) -> QuestionGenerationFixture:
    base = missing_source_slot_fixture(tmp_path)
    simulado = persist_simulado(
        base.context,
        graph_id=base.graph.graph_id,
        profile_id=PSCPP_EXAM_PROFILE_ID,
        format_type="multiple_choice_5",
        question_slots=[
            build_slot(
                topic_id="topic:missing-source",
                format_type="multiple_choice_5",
                readiness_state="ready_for_generation",
            )
        ],
        exam_family="PSCPP",
        artifact_key="pscpp-missing-source",
    )
    return QuestionGenerationFixture(
        context=base.context,
        simulado_blueprint=simulado,
        graph=base.graph,
        expected_slot_state="blocked_by_missing_source",
        expected_set_state="blocked",
    )


def pscpp_fixation_metadata_fixture() -> dict[str, object]:
    return enrich_question_generation_blueprint_with_style_profile(
        exam_profile_id=PSCPP_EXAM_PROFILE_ID,
        blueprint_metadata={"question_context": "fixation"},
        source_titles=["Bridge Team Management"],
        source_present=True,
        requested_archetype="technical_operational_scenario",
        delivery_context="fixation",
    )


def pscpp_review_metadata_fixture() -> dict[str, object]:
    return enrich_question_generation_blueprint_with_style_profile(
        exam_profile_id=PSCPP_EXAM_PROFILE_ID,
        blueprint_metadata={"question_context": "review"},
        source_titles=["NORMAM-12/DPC"],
        source_present=True,
        requested_archetype="statement_combination",
        per_statement_source_support=True,
        delivery_context="review",
    )


def pscpp_summary_reading_metadata_fixture() -> dict[str, object]:
    return enrich_question_generation_blueprint_with_style_profile(
        exam_profile_id=PSCPP_EXAM_PROFILE_ID,
        blueprint_metadata={"question_context": "summary_reading"},
        source_titles=["Arte Naval - Maurilio M. Fonseca"],
        source_present=True,
        requested_archetype="incorrect_alternative",
        negative_command=True,
        delivery_context="summary_reading",
    )


def pscpp_draft_fixture(tmp_path):
    fixture = pscpp_ready_blueprint_fixture(tmp_path)
    blueprint_set = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    draft_service = QuestionDraftGenerationService(fixture.context.repository)
    return draft_service.build_draft_set(blueprint_set.blueprint_set_id, user_id=fixture.context.user_id)


def pscpp_direct_metadata_fixture(
    *,
    context: str,
    requested_archetype: str | None = None,
    source_present: bool = True,
    bibliography_anchor_present: bool | None = None,
    source_title_visible: bool | None = None,
    current_edital_alignment_present: bool | None = None,
    formula_supported: bool = False,
    per_statement_source_support: bool = False,
    negative_command: bool = False,
    exact_source_value_present: bool = False,
    scenario_present: bool = False,
    normative_source_present: bool = False,
    units_present: bool = False,
) -> dict[str, object]:
    return enrich_question_generation_blueprint_with_style_profile(
        exam_profile_id=PSCPP_EXAM_PROFILE_ID,
        blueprint_metadata={"question_context": context},
        source_titles=["NORMAM-12/DPC"] if source_present else [],
        source_present=source_present,
        requested_archetype=requested_archetype,
        bibliography_anchor_present=bibliography_anchor_present,
        source_title_visible=source_title_visible,
        current_edital_alignment_present=current_edital_alignment_present,
        formula_supported=formula_supported,
        per_statement_source_support=per_statement_source_support,
        negative_command=negative_command,
        exact_source_value_present=exact_source_value_present,
        scenario_present=scenario_present,
        normative_source_present=normative_source_present,
        units_present=units_present,
        delivery_context=context,
    )


def pscpp_archetype_slot_fixture(
    tmp_path,
    *,
    requested_archetype: str,
    slot_metadata: dict[str, object] | None = None,
):
    fixture = pscpp_ready_blueprint_fixture(tmp_path)
    context = fixture.context
    slot = build_slot(
        topic_id="topic:ripeam-pscpp",
        format_type="multiple_choice_5",
        readiness_state="ready_for_generation",
        source_evidence_ids=["e:ripeam:pscpp"],
    ).model_copy(
        update={
            "metadata": {
                "requested_archetype": requested_archetype,
                **(slot_metadata or {}),
            }
        }
    )
    simulado = persist_simulado(
        context,
        graph_id=fixture.graph.graph_id,
        profile_id=PSCPP_EXAM_PROFILE_ID,
        format_type="multiple_choice_5",
        question_slots=[slot],
        exam_family="PSCPP",
        artifact_key=f"pscpp-archetype-{requested_archetype}",
    )
    return QuestionGenerationFixture(
        context=context,
        simulado_blueprint=simulado,
        graph=fixture.graph,
        expected_slot_state="ready_for_draft",
        expected_set_state="ready_for_review",
        uploaded_material=fixture.uploaded_material,
        chunk=fixture.chunk,
    )
