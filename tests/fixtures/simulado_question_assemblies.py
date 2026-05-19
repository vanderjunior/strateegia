from __future__ import annotations

from dataclasses import dataclass, field

from app.domain.models import (
    AnswerExplanationGuardrail,
    AnswerExplanationWarning,
    QuestionDraft,
    QuestionDraftSet,
    QuestionGenerationBlueprint,
    SimuladoBlueprint,
    SimuladoBlueprintRationale,
    SimuladoQuestionSlot,
    ValidationFinding,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.answer_explanation_guardrails import AnswerExplanationGuardrailService
from app.services.simulado_question_assembly import SimuladoQuestionAssemblyService
from tests.fixtures.question_drafts import (
    build_fixture,
    long_snippet_bounds_fixture,
    ready_cebraspe_assertion_blueprint_fixture,
    ready_fgv_case_mcq_blueprint_fixture,
    source_review_needed_fixture,
)


@dataclass
class SimuladoAssemblyFixtureContext:
    repository: JsonStudyRepository
    assembly_service: SimuladoQuestionAssemblyService
    guardrail_service: AnswerExplanationGuardrailService
    user_id: str


@dataclass
class SimuladoAssemblyFixture:
    context: SimuladoAssemblyFixtureContext
    simulado_blueprint: SimuladoBlueprint
    blueprint_set: object
    draft_set: QuestionDraftSet | None = None
    guardrails: list[AnswerExplanationGuardrail] = field(default_factory=list)


def assembly_json_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(assembly_json_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(assembly_json_keys(item))
        return keys
    return set()


def _context(repository: JsonStudyRepository, user_id: str) -> SimuladoAssemblyFixtureContext:
    return SimuladoAssemblyFixtureContext(
        repository=repository,
        assembly_service=SimuladoQuestionAssemblyService(repository),
        guardrail_service=AnswerExplanationGuardrailService(repository),
        user_id=user_id,
    )


def _persist_simulado_from_blueprint_set(base_fixture) -> SimuladoBlueprint:
    slot_blueprints = base_fixture.blueprint_set.slot_blueprints
    blueprint_id = base_fixture.blueprint_set.source_simulado_blueprint_id
    first_slot = slot_blueprints[0] if slot_blueprints else None
    simulado = SimuladoBlueprint(
        blueprint_id=blueprint_id,
        graph_id=f"graph:{blueprint_id}",
        cycle_id=f"cycle:{blueprint_id}",
        exam_profile_id=f"exam-profile:{first_slot.board_id if first_slot else 'unknown'}",
        user_id=base_fixture.context.user_id,
        exam_board=first_slot.board_id if first_slot else None,
        exam_family=first_slot.exam_family if first_slot else None,
        format_type=first_slot.format_type if first_slot else "unknown",
        question_slots=[
            SimuladoQuestionSlot(
                slot_id=slot_blueprint.source_question_slot_id,
                section_id="section:primary",
                order_index=index,
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
            for index, slot_blueprint in enumerate(slot_blueprints)
        ],
        rationale=SimuladoBlueprintRationale(
            summary="fixture simulado blueprint for assembly stabilization",
            source_graph_id=f"graph:{blueprint_id}",
            source_cycle_id=f"cycle:{blueprint_id}",
            source_exam_profile_id=f"exam-profile:{first_slot.board_id if first_slot else 'unknown'}",
            confidence=0.8,
        ),
        metadata={"fixture": True},
    )
    base_fixture.context.repository.save_simulado_blueprint(simulado, user_id=base_fixture.context.user_id)
    return simulado


def _build_draft_set(base_fixture) -> QuestionDraftSet:
    return base_fixture.context.service.build_draft_set(
        base_fixture.blueprint_set.blueprint_set_id,
        user_id=base_fixture.context.user_id,
    )


def _build_fixture_from_base(
    base_fixture,
    *,
    draft_set: QuestionDraftSet | None = None,
    guardrails: list[AnswerExplanationGuardrail] | None = None,
) -> SimuladoAssemblyFixture:
    return SimuladoAssemblyFixture(
        context=_context(base_fixture.context.repository, base_fixture.context.user_id),
        simulado_blueprint=_persist_simulado_from_blueprint_set(base_fixture),
        blueprint_set=base_fixture.blueprint_set,
        draft_set=draft_set,
        guardrails=guardrails or [],
    )


def _save_draft_variant(base_fixture, draft: QuestionDraft, *, all_drafts: list[QuestionDraft] | None = None) -> QuestionDraftSet:
    current = _build_draft_set(base_fixture)
    new_set = current.model_copy(update={"drafts": all_drafts or [draft]})
    base_fixture.context.repository.save_question_draft_set(new_set, user_id=base_fixture.context.user_id)
    return new_set


def ready_for_review_candidate_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    base = ready_cebraspe_assertion_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    draft_set = _build_draft_set(base)
    guardrail = AnswerExplanationGuardrailService(base.context.repository).build_guardrail(
        draft_set.drafts[0].draft_id,
        user_id=user_id,
    )
    return _build_fixture_from_base(base, draft_set=draft_set, guardrails=[guardrail])


def missing_draft_candidate_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    base = ready_cebraspe_assertion_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    return _build_fixture_from_base(base, draft_set=None, guardrails=[])


def missing_guardrail_candidate_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    base = ready_cebraspe_assertion_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    draft_set = _build_draft_set(base)
    return _build_fixture_from_base(base, draft_set=draft_set, guardrails=[])


def blocked_guardrail_candidate_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    base = ready_fgv_case_mcq_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    draft_set = _build_draft_set(base)
    guardrail = AnswerExplanationGuardrailService(base.context.repository).build_guardrail(
        draft_set.drafts[0].draft_id,
        user_id=user_id,
    )
    return _build_fixture_from_base(base, draft_set=draft_set, guardrails=[guardrail])


def non_reviewed_draft_candidate_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    base = ready_cebraspe_assertion_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    current = _build_draft_set(base)
    draft = current.drafts[0].model_copy(
        update={
            "draft_id": f"{current.drafts[0].draft_id}:non-reviewed",
            "draft_status": "blocked",
            "draft_readiness": "blocked_by_blueprint",
        }
    )
    draft_set = _save_draft_variant(base, draft)
    guardrail = AnswerExplanationGuardrailService(base.context.repository).build_guardrail(
        draft.draft_id,
        user_id=user_id,
    )
    return _build_fixture_from_base(base, draft_set=draft_set, guardrails=[guardrail])


def unsupported_format_candidate_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    base = ready_cebraspe_assertion_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    current = _build_draft_set(base)
    draft = current.drafts[0].model_copy(
        update={
            "draft_id": f"{current.drafts[0].draft_id}:unsupported",
            "question_kind": "essay_future_format",
            "format_type": "unsupported_format",
            "draft_statement": None,
            "draft_option_placeholders": [],
        }
    )
    draft_set = _save_draft_variant(base, draft)
    guardrail = AnswerExplanationGuardrailService(base.context.repository).build_guardrail(
        draft.draft_id,
        user_id=user_id,
    )
    return _build_fixture_from_base(base, draft_set=draft_set, guardrails=[guardrail])


def ocr_blocked_candidate_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    fixture = ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    guardrail = fixture.guardrails[0].model_copy(
        update={
            "source_support_assessment": fixture.guardrails[0].source_support_assessment.model_copy(
                update={"ocr_blocked": True, "source_coverage_state": "ocr_required"}
            )
        }
    )
    fixture.context.repository.save_answer_explanation_guardrail(guardrail, user_id=user_id)
    return SimuladoAssemblyFixture(
        context=fixture.context,
        simulado_blueprint=fixture.simulado_blueprint,
        blueprint_set=fixture.blueprint_set,
        draft_set=fixture.draft_set,
        guardrails=[guardrail],
    )


def material_gap_candidate_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    fixture = ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)
    guardrail = fixture.guardrails[0].model_copy(
        update={
            "warnings": fixture.guardrails[0].warnings
            + [
                AnswerExplanationWarning(
                    code="material_gap",
                    message="Source support still indicates a material gap.",
                    severity="blocked",
                    related_artifact_type="answer_explanation_guardrail",
                    related_artifact_id=fixture.guardrails[0].guardrail_id,
                    metadata={"fixture": True},
                )
            ]
        }
    )
    fixture.context.repository.save_answer_explanation_guardrail(guardrail, user_id=user_id)
    return SimuladoAssemblyFixture(
        context=fixture.context,
        simulado_blueprint=fixture.simulado_blueprint,
        blueprint_set=fixture.blueprint_set,
        draft_set=fixture.draft_set,
        guardrails=[guardrail],
    )


def ambiguous_source_candidate_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    base = source_review_needed_fixture(tmp_path, user_id=user_id, repository=repository)
    draft_set = _build_draft_set(base)
    guardrail = AnswerExplanationGuardrailService(base.context.repository).build_guardrail(
        draft_set.drafts[0].draft_id,
        user_id=user_id,
    )
    return _build_fixture_from_base(base, draft_set=draft_set, guardrails=[guardrail])


def missing_source_candidate_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    base = ready_cebraspe_assertion_blueprint_fixture(tmp_path, user_id=user_id, repository=repository)
    current = _build_draft_set(base)
    draft = current.drafts[0].model_copy(
        update={
            "draft_id": f"{current.drafts[0].draft_id}:missing-source",
            "source_references": [],
            "validation_summary": current.drafts[0].validation_summary.model_copy(
                update={"source_grounded": False, "has_required_source_evidence": False}
            ),
        }
    )
    draft_set = _save_draft_variant(base, draft)
    guardrail = AnswerExplanationGuardrailService(base.context.repository).build_guardrail(
        draft.draft_id,
        user_id=user_id,
    )
    return _build_fixture_from_base(base, draft_set=draft_set, guardrails=[guardrail])


def no_candidates_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    base = build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:assembly-no-candidates",
        slot_blueprints=[],
        user_id=user_id,
        repository=repository,
    )
    return _build_fixture_from_base(base, draft_set=None, guardrails=[])


def bounded_summary_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    base = long_snippet_bounds_fixture(tmp_path, user_id=user_id, repository=repository)
    draft_set = _build_draft_set(base)
    guardrail = AnswerExplanationGuardrailService(base.context.repository).build_guardrail(
        draft_set.drafts[0].draft_id,
        user_id=user_id,
    )
    return _build_fixture_from_base(base, draft_set=draft_set, guardrails=[guardrail])


def no_final_content_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    return ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)


def mixed_assembly_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    repo = repository or JsonStudyRepository(tmp_path / "study_data.json")
    ready_slot = ready_cebraspe_assertion_blueprint_fixture(
        tmp_path / "ready",
        user_id=user_id,
        repository=repo,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={
            "source_simulado_blueprint_id": "simulado:assembly-mixed",
            "source_question_slot_id": "slot:mixed-ready",
            "blueprint_id": "qgb-slot:slot:mixed-ready",
        }
    )
    missing_draft_slot = ready_cebraspe_assertion_blueprint_fixture(
        tmp_path / "missing-draft",
        user_id=user_id,
        repository=repo,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={
            "source_simulado_blueprint_id": "simulado:assembly-mixed",
            "source_question_slot_id": "slot:mixed-missing-draft",
            "blueprint_id": "qgb-slot:slot:mixed-missing-draft",
        }
    )
    missing_guardrail_slot = ready_cebraspe_assertion_blueprint_fixture(
        tmp_path / "missing-guardrail",
        user_id=user_id,
        repository=repo,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={
            "source_simulado_blueprint_id": "simulado:assembly-mixed",
            "source_question_slot_id": "slot:mixed-missing-guardrail",
            "blueprint_id": "qgb-slot:slot:mixed-missing-guardrail",
        }
    )
    blocked_guardrail_slot = ready_fgv_case_mcq_blueprint_fixture(
        tmp_path / "blocked-guardrail",
        user_id=user_id,
        repository=repo,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={
            "source_simulado_blueprint_id": "simulado:assembly-mixed",
            "source_question_slot_id": "slot:mixed-blocked-guardrail",
            "blueprint_id": "qgb-slot:slot:mixed-blocked-guardrail",
        }
    )
    unsupported_slot = ready_cebraspe_assertion_blueprint_fixture(
        tmp_path / "unsupported",
        user_id=user_id,
        repository=repo,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={
            "source_simulado_blueprint_id": "simulado:assembly-mixed",
            "source_question_slot_id": "slot:mixed-unsupported",
            "blueprint_id": "qgb-slot:slot:mixed-unsupported",
        }
    )
    ambiguous_slot = source_review_needed_fixture(
        tmp_path / "ambiguous",
        user_id=user_id,
        repository=repo,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={
            "source_simulado_blueprint_id": "simulado:assembly-mixed",
            "source_question_slot_id": "slot:mixed-ambiguous",
            "blueprint_id": "qgb-slot:slot:mixed-ambiguous",
        }
    )
    base = build_fixture(
        tmp_path / "base",
        source_simulado_blueprint_id="simulado:assembly-mixed",
        slot_blueprints=[
            ready_slot,
            missing_draft_slot,
            missing_guardrail_slot,
            blocked_guardrail_slot,
            unsupported_slot,
            ambiguous_slot,
        ],
        user_id=user_id,
        repository=repo,
    )
    current = _build_draft_set(base)
    updated_drafts: list[QuestionDraft] = []
    for draft in current.drafts:
        if draft.source_question_generation_blueprint_id == "qgb-slot:slot:mixed-missing-draft":
            continue
        if draft.source_question_generation_blueprint_id == "qgb-slot:slot:mixed-unsupported":
            updated_drafts.append(
                draft.model_copy(
                    update={
                        "draft_id": f"{draft.draft_id}:unsupported",
                        "question_kind": "essay_future_format",
                        "format_type": "unsupported_format",
                        "draft_statement": None,
                        "draft_option_placeholders": [],
                    }
                )
            )
            continue
        updated_drafts.append(draft)
    draft_set = current.model_copy(update={"drafts": updated_drafts})
    base.context.repository.save_question_draft_set(draft_set, user_id=user_id)

    guardrail_service = AnswerExplanationGuardrailService(repo)
    guardrails: list[AnswerExplanationGuardrail] = []
    for draft in updated_drafts:
        if draft.source_question_generation_blueprint_id == "qgb-slot:slot:mixed-missing-guardrail":
            continue
        guardrails.append(guardrail_service.build_guardrail(draft.draft_id, user_id=user_id))

    return _build_fixture_from_base(base, draft_set=draft_set, guardrails=guardrails)


def user_scope_fixture(
    tmp_path,
    *,
    repository: JsonStudyRepository | None = None,
) -> tuple[SimuladoAssemblyFixture, SimuladoAssemblyFixture]:
    repo = repository or JsonStudyRepository(tmp_path / "study_data.json")
    owner = ready_for_review_candidate_fixture(tmp_path / "owner", user_id="user-a", repository=repo)
    other = ready_for_review_candidate_fixture(tmp_path / "other", user_id="user-b", repository=repo)
    return owner, other


def idempotency_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> SimuladoAssemblyFixture:
    return ready_for_review_candidate_fixture(tmp_path, user_id=user_id, repository=repository)


def build_assembly(fixture: SimuladoAssemblyFixture):
    return fixture.context.assembly_service.build_assembly(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )
