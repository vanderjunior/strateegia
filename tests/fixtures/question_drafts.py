from __future__ import annotations

from dataclasses import dataclass

from app.domain.models import (
    QuestionGenerationBlueprint,
    QuestionGenerationBlueprintSet,
    QuestionGenerationConstraint,
    QuestionGenerationWarning,
    QuestionSourceEvidence,
)
from app.repositories.json_store import JsonStudyRepository
from app.services.question_draft_generation import QuestionDraftGenerationService


@dataclass
class QuestionDraftFixtureContext:
    repository: JsonStudyRepository
    service: QuestionDraftGenerationService
    user_id: str = "user-a"


@dataclass
class QuestionDraftFixture:
    context: QuestionDraftFixtureContext
    blueprint_set: QuestionGenerationBlueprintSet


def create_context(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixtureContext:
    repo = repository or JsonStudyRepository(tmp_path / "study_data.json")
    return QuestionDraftFixtureContext(
        repository=repo,
        service=QuestionDraftGenerationService(repo),
        user_id=user_id,
    )


def build_fixture(
    tmp_path,
    *,
    source_simulado_blueprint_id: str,
    slot_blueprints: list[QuestionGenerationBlueprint],
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    context = create_context(tmp_path, user_id=user_id, repository=repository)
    ready_slots = sum(item.readiness_state == "ready_for_draft" for item in slot_blueprints)
    blocked_slots = sum(item.readiness_state.startswith("blocked_by_") for item in slot_blueprints)
    needs_review_slots = sum(item.readiness_state == "needs_review" for item in slot_blueprints)
    if not slot_blueprints:
        readiness_state = "no_slots"
    elif ready_slots and not blocked_slots and not needs_review_slots:
        readiness_state = "ready_for_draft"
    elif ready_slots:
        readiness_state = "partially_ready"
    elif needs_review_slots and not blocked_slots:
        readiness_state = "needs_review"
    else:
        readiness_state = "blocked"
    blueprint_set = QuestionGenerationBlueprintSet(
        blueprint_set_id=f"question-generation:{source_simulado_blueprint_id}",
        user_id=user_id,
        source_simulado_blueprint_id=source_simulado_blueprint_id,
        status=readiness_state,
        readiness_state=readiness_state,
        total_slots=len(slot_blueprints),
        ready_slots=ready_slots,
        blocked_slots=blocked_slots,
        needs_review_slots=needs_review_slots,
        slot_blueprints=slot_blueprints,
        constraints=[
            _constraint(
                "constraint:set:no-final-question-text",
                "no_final_question_text_in_this_pass",
                "No final question text may be generated in this pass.",
            )
        ],
        warnings=[
            _warning(
                "no_question_text_generated",
                "Question generation blueprint remains planning-only in this pass.",
                related_artifact_id=f"question-generation:{source_simulado_blueprint_id}",
            )
        ],
        metadata={"fixture": True, "llm_used": False, "external_calls_used": False},
    )
    context.repository.save_question_generation_blueprint(blueprint_set, user_id=user_id)
    return QuestionDraftFixture(context=context, blueprint_set=blueprint_set)


def _constraint(
    constraint_id: str,
    constraint_type: str,
    description: str,
    *,
    severity: str = "warning",
) -> QuestionGenerationConstraint:
    return QuestionGenerationConstraint(
        constraint_id=constraint_id,
        constraint_type=constraint_type,
        severity=severity,
        description=description,
        source="fixture",
        metadata={"fixture": True},
    )


def _warning(
    code: str,
    message: str,
    *,
    severity: str = "warning",
    related_artifact_id: str | None = None,
) -> QuestionGenerationWarning:
    return QuestionGenerationWarning(
        code=code,
        message=message,
        severity=severity,
        related_artifact_type="question_generation_blueprint",
        related_artifact_id=related_artifact_id,
        metadata={"fixture": True},
    )


def _evidence(
    evidence_id: str,
    *,
    snippet: str | None,
    topic_id: str,
    source_title: str = "Material tecnico",
) -> QuestionSourceEvidence:
    return QuestionSourceEvidence(
        evidence_id=evidence_id,
        document_id=f"document:{topic_id}",
        material_id=f"material:{topic_id}",
        section_id=f"section:{topic_id}",
        chunk_id=f"chunk:{topic_id}",
        topic_id=topic_id,
        evidence_role="primary_support",
        evidence_strength="strong",
        coverage_state="covered",
        source_title=source_title,
        source_type="document_chunk",
        safe_snippet=snippet,
        metadata={"fixture": True},
    )


def _blueprint(
    *,
    user_id: str,
    source_simulado_blueprint_id: str,
    source_question_slot_id: str,
    readiness_state: str,
    question_kind: str,
    format_type: str,
    board_id: str | None,
    exam_family: str | None,
    target_topic_id: str,
    style_hints: list[str],
    source_evidence: list[QuestionSourceEvidence],
    warnings: list[QuestionGenerationWarning] | None = None,
    constraints: list[QuestionGenerationConstraint] | None = None,
    blockers: list[str] | None = None,
) -> QuestionGenerationBlueprint:
    return QuestionGenerationBlueprint(
        blueprint_id=f"qgb-slot:{source_question_slot_id}",
        user_id=user_id,
        source_simulado_blueprint_id=source_simulado_blueprint_id,
        source_question_slot_id=source_question_slot_id,
        readiness_state=readiness_state,
        format_type=format_type,
        board_id=board_id,
        exam_family=exam_family,
        target_subject_id="subject:navegacao",
        target_topic_id=target_topic_id,
        target_subtopic_ids=[f"{target_topic_id}:subtopic:1"],
        difficulty_hint="medium",
        cognitive_demand="high",
        question_kind=question_kind,
        style_hints=style_hints,
        source_evidence=source_evidence,
        constraints=constraints
        or [
            _constraint(
                f"constraint:{source_question_slot_id}:must-use-source",
                "must_use_source_evidence",
                "Future drafting must remain grounded in the cited source evidence.",
            )
        ],
        blockers=blockers or [],
        warnings=warnings or [],
        metadata={"fixture": True},
    )


def ready_cebraspe_assertion_blueprint_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    topic_id = "topic:ripeam-governo"
    snippet = (
        "O RIPEAM exige avaliacao tecnica das regras de governo e rumo, com interpretacao precisa "
        "das condicoes operacionais e da prioridade de passagem."
    )
    blueprint = _blueprint(
        user_id=user_id,
        source_simulado_blueprint_id="simulado:qdf-cebraspe",
        source_question_slot_id="slot:cebraspe",
        readiness_state="ready_for_draft",
        question_kind="assertion_judgement",
        format_type="true_false",
        board_id="CEBRASPE",
        exam_family="concurso_publico",
        target_topic_id=topic_id,
        style_hints=[
            "single_assertion",
            "technical_precision",
            "source_grounded_assertion_required",
        ],
        source_evidence=[_evidence("evidence:cebraspe", snippet=snippet, topic_id=topic_id)],
        warnings=[_warning("no_question_text_generated", "Blueprint remains planning-only.")],
    )
    return build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:qdf-cebraspe",
        slot_blueprints=[blueprint],
        user_id=user_id,
        repository=repository,
    )


def ready_fgv_case_mcq_blueprint_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    topic_id = "topic:meteorologia-sinotica"
    snippet = (
        "Cartas sinoticas e leitura de vento exigem correlacao entre fenomenos atmosfericos, sinais "
        "observaveis e impacto na navegacao segura."
    )
    blueprint = _blueprint(
        user_id=user_id,
        source_simulado_blueprint_id="simulado:qdf-fgv",
        source_question_slot_id="slot:fgv",
        readiness_state="ready_for_draft",
        question_kind="case_based_multiple_choice",
        format_type="multiple_choice_5",
        board_id="FGV",
        exam_family="prova_objetiva",
        target_topic_id=topic_id,
        style_hints=[
            "contextualized_command",
            "plausible_distractors_future",
            "single_best_answer",
        ],
        source_evidence=[_evidence("evidence:fgv", snippet=snippet, topic_id=topic_id)],
        warnings=[_warning("no_question_text_generated", "Blueprint remains planning-only.")],
    )
    return build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:qdf-fgv",
        slot_blueprints=[blueprint],
        user_id=user_id,
        repository=repository,
    )


def ready_pscpp_maritime_blueprint_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    topic_id = "topic:manobra-fundeio"
    snippet = (
        "Em contexto tecnico-maritimo, a avaliacao de fundeio considera vento, corrente, profundidade "
        "e comunicacao operacional com uso de terminologia tecnica e, quando necessario, termos em ingles."
    )
    blueprint = _blueprint(
        user_id=user_id,
        source_simulado_blueprint_id="simulado:qdf-pscpp",
        source_question_slot_id="slot:pscpp",
        readiness_state="ready_for_draft",
        question_kind="technical_maritime_scenario",
        format_type="multiple_choice_4",
        board_id="DPC",
        exam_family="pscpp",
        target_topic_id=topic_id,
        style_hints=[
            "technical_operational_context",
            "source_topic_mapping_required",
            "allow_english_maritime_terms",
            "prioritize_bibliography_evidence",
        ],
        source_evidence=[_evidence("evidence:pscpp", snippet=snippet, topic_id=topic_id)],
        warnings=[_warning("no_question_text_generated", "Blueprint remains planning-only.")],
        constraints=[
            _constraint(
                "constraint:pscpp:must-preserve-maritime-context",
                "must_preserve_technical_maritime_context",
                "The future draft must preserve the maritime technical context.",
            )
        ],
    )
    return build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:qdf-pscpp",
        slot_blueprints=[blueprint],
        user_id=user_id,
        repository=repository,
    )


def ready_direct_multiple_choice_blueprint_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    topic_id = "topic:sinalizacao-nautica"
    snippet = (
        "A identificacao de marcas laterais e cardinais depende da leitura correta de cor, luz, forma "
        "e posicionamento relativo no canal navegavel."
    )
    blueprint = _blueprint(
        user_id=user_id,
        source_simulado_blueprint_id="simulado:qdf-direct",
        source_question_slot_id="slot:direct",
        readiness_state="ready_for_draft",
        question_kind="direct_multiple_choice",
        format_type="multiple_choice_4",
        board_id="CESGRANRIO",
        exam_family="prova_objetiva",
        target_topic_id=topic_id,
        style_hints=["single_best_answer"],
        source_evidence=[_evidence("evidence:direct", snippet=snippet, topic_id=topic_id)],
        warnings=[_warning("no_question_text_generated", "Blueprint remains planning-only.")],
    )
    return build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:qdf-direct",
        slot_blueprints=[blueprint],
        user_id=user_id,
        repository=repository,
    )


def unsupported_question_kind_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    topic_id = "topic:regulamento-portuario"
    blueprint = _blueprint(
        user_id=user_id,
        source_simulado_blueprint_id="simulado:qdf-unsupported",
        source_question_slot_id="slot:unsupported",
        readiness_state="ready_for_draft",
        question_kind="essay_future_format",
        format_type="unsupported_format",
        board_id="UNKNOWN",
        exam_family="desconhecida",
        target_topic_id=topic_id,
        style_hints=["format_needs_confirmation"],
        source_evidence=[_evidence("evidence:unsupported", snippet="Trecho tecnico curto.", topic_id=topic_id)],
        warnings=[_warning("unsupported_question_format", "Question format is not supported in this pass.")],
    )
    return build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:qdf-unsupported",
        slot_blueprints=[blueprint],
        user_id=user_id,
        repository=repository,
    )


def non_ready_blueprint_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    topic_id = "topic:insuficiente"
    blueprint = _blueprint(
        user_id=user_id,
        source_simulado_blueprint_id="simulado:qdf-non-ready",
        source_question_slot_id="slot:non-ready",
        readiness_state="needs_review",
        question_kind="assertion_judgement",
        format_type="true_false",
        board_id="CEBRASPE",
        exam_family="concurso_publico",
        target_topic_id=topic_id,
        style_hints=["single_assertion"],
        source_evidence=[_evidence("evidence:non-ready", snippet="Cobertura ainda ambigua.", topic_id=topic_id)],
        warnings=[_warning("ambiguous_coverage", "Coverage remains ambiguous and still needs review.")],
    )
    return build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:qdf-non-ready",
        slot_blueprints=[blueprint],
        user_id=user_id,
        repository=repository,
    )


def missing_source_evidence_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    topic_id = "topic:sem-evidencia"
    blueprint = _blueprint(
        user_id=user_id,
        source_simulado_blueprint_id="simulado:qdf-missing-source",
        source_question_slot_id="slot:missing-source",
        readiness_state="ready_for_draft",
        question_kind="assertion_judgement",
        format_type="true_false",
        board_id="CEBRASPE",
        exam_family="concurso_publico",
        target_topic_id=topic_id,
        style_hints=["single_assertion"],
        source_evidence=[],
        warnings=[_warning("source_evidence_missing", "Source evidence is still missing for this slot.")],
        blockers=["blocked_by_missing_source"],
    )
    return build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:qdf-missing-source",
        slot_blueprints=[blueprint],
        user_id=user_id,
        repository=repository,
    )


def source_review_needed_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    topic_id = "topic:revisao-fonte"
    blueprint = _blueprint(
        user_id=user_id,
        source_simulado_blueprint_id="simulado:qdf-source-review",
        source_question_slot_id="slot:source-review",
        readiness_state="ready_for_draft",
        question_kind="assertion_judgement",
        format_type="true_false",
        board_id="CEBRASPE",
        exam_family="concurso_publico",
        target_topic_id=topic_id,
        style_hints=["single_assertion"],
        source_evidence=[_evidence("evidence:source-review", snippet=None, topic_id=topic_id)],
        warnings=[_warning("safe_snippet_omitted", "Safe snippet still needs confirmation.")],
    )
    return build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:qdf-source-review",
        slot_blueprints=[blueprint],
        user_id=user_id,
        repository=repository,
    )


def long_snippet_bounds_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    topic_id = "topic:long-snippet"
    snippet = (
        "Trecho tecnico muito extenso sobre navegacao costeira, repetido apenas para testar truncamento e "
        "sanitizacao segura de paths sensiveis. "
        "/Users/vjr/Documents/New project/uploads/private/ripeam.pdf "
        + "conteudo " * 80
    )
    blueprint = _blueprint(
        user_id=user_id,
        source_simulado_blueprint_id="simulado:qdf-long-snippet",
        source_question_slot_id="slot:long-snippet",
        readiness_state="ready_for_draft",
        question_kind="case_based_multiple_choice",
        format_type="multiple_choice_5",
        board_id="FGV",
        exam_family="prova_objetiva",
        target_topic_id=topic_id,
        style_hints=["contextualized_command"],
        source_evidence=[_evidence("evidence:long-snippet", snippet=snippet, topic_id=topic_id)],
    )
    return build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:qdf-long-snippet",
        slot_blueprints=[blueprint],
        user_id=user_id,
        repository=repository,
    )


def mixed_draft_set_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    ready_assertion = ready_cebraspe_assertion_blueprint_fixture(
        tmp_path / "assertion",
        user_id=user_id,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={"source_simulado_blueprint_id": "simulado:qdf-mixed", "source_question_slot_id": "slot:mixed-assertion"}
    )
    ready_fgv = ready_fgv_case_mcq_blueprint_fixture(
        tmp_path / "fgv",
        user_id=user_id,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={"source_simulado_blueprint_id": "simulado:qdf-mixed", "source_question_slot_id": "slot:mixed-fgv"}
    )
    review_source = source_review_needed_fixture(
        tmp_path / "source-review",
        user_id=user_id,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={"source_simulado_blueprint_id": "simulado:qdf-mixed", "source_question_slot_id": "slot:mixed-source-review"}
    )
    blocked_non_ready = non_ready_blueprint_fixture(
        tmp_path / "non-ready",
        user_id=user_id,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={"source_simulado_blueprint_id": "simulado:qdf-mixed", "source_question_slot_id": "slot:mixed-non-ready"}
    )
    unsupported = unsupported_question_kind_fixture(
        tmp_path / "unsupported",
        user_id=user_id,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={"source_simulado_blueprint_id": "simulado:qdf-mixed", "source_question_slot_id": "slot:mixed-unsupported"}
    )
    missing_source = missing_source_evidence_fixture(
        tmp_path / "missing-source",
        user_id=user_id,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={"source_simulado_blueprint_id": "simulado:qdf-mixed", "source_question_slot_id": "slot:mixed-missing-source"}
    )
    return build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:qdf-mixed",
        slot_blueprints=[
            ready_assertion,
            ready_fgv,
            review_source,
            blocked_non_ready,
            unsupported,
            missing_source,
        ],
        user_id=user_id,
        repository=repository,
    )


def no_ready_blueprints_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    needs_review = non_ready_blueprint_fixture(
        tmp_path / "needs-review",
        user_id=user_id,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={"source_simulado_blueprint_id": "simulado:qdf-no-ready", "source_question_slot_id": "slot:no-ready-review"}
    )
    blocked = missing_source_evidence_fixture(
        tmp_path / "blocked",
        user_id=user_id,
    ).blueprint_set.slot_blueprints[0].model_copy(
        update={
            "source_simulado_blueprint_id": "simulado:qdf-no-ready",
            "source_question_slot_id": "slot:no-ready-blocked",
            "readiness_state": "blocked_by_missing_source",
        }
    )
    return build_fixture(
        tmp_path,
        source_simulado_blueprint_id="simulado:qdf-no-ready",
        slot_blueprints=[needs_review, blocked],
        user_id=user_id,
        repository=repository,
    )


def no_final_content_safety_fixture(
    tmp_path,
    *,
    user_id: str = "user-a",
    repository: JsonStudyRepository | None = None,
) -> QuestionDraftFixture:
    return ready_fgv_case_mcq_blueprint_fixture(
        tmp_path,
        user_id=user_id,
        repository=repository,
    )
