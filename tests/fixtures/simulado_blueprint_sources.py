from __future__ import annotations

from app.domain.models import EditalExtractionResult, EditalWeightHint
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_blueprint_builder import SimuladoBlueprintBuilderService
from app.services.study_cycle_orchestrator import StudyCycleOrchestratorService
from tests.fixtures.study_cycle_graphs import (
    ambiguous_topic_cycle_fixture as ambiguous_graph_fixture,
    balanced_cycle_fixture as balanced_graph_fixture,
    build_evidence,
    covered_topic_cycle_fixture as covered_graph_fixture,
    gap_heavy_cycle_fixture as gap_heavy_graph_fixture,
    maritime_praticagem_cycle_fixture as maritime_graph_fixture,
    material_blocked_cycle_fixture as material_blocked_graph_fixture,
    mixed_complex_cycle_fixture as mixed_complex_graph_fixture,
    multi_subject_rotation_fixture as multi_subject_graph_fixture,
    ocr_required_cycle_fixture as ocr_graph_fixture,
    weak_topic_cycle_fixture as weak_graph_fixture,
)


def build_edital_result_with_weight_hints(
    *,
    edital_id: str,
    preview: str,
    weight_hints: list[EditalWeightHint] | None = None,
    user_id: str | None = "user-a",
) -> EditalExtractionResult:
    return EditalExtractionResult(
        edital_id=edital_id,
        document_id=edital_id.replace("edital:", "doc:"),
        user_id=user_id,
        source_text_length=len(preview),
        weight_hints=weight_hints or [],
        metadata={"source_text_preview": preview},
    )


def build_question_count_hint(*, weight_id: str, value: float, target_title: str = "Estrutura da Prova") -> EditalWeightHint:
    return EditalWeightHint(
        weight_id=weight_id,
        target_type="section",
        target_title=target_title,
        weight_type="question_count",
        value=value,
        raw_text=f"{int(value)} questoes",
        confidence=0.9,
        reasoning="fixture weight hint",
    )


def persist_simulado_blueprint_fixture(
    repository: JsonStudyRepository,
    fixture: dict[str, object],
    *,
    user_id: str = "user-a",
) -> dict[str, object]:
    graph = fixture["graph"].model_copy(update={"user_id": user_id})
    repository.save_curriculum_graph(graph, user_id=user_id)
    edital_result = fixture.get("edital_result")
    if edital_result is not None:
        repository.save_edital_extraction_result(edital_result.model_copy(update={"user_id": user_id}), user_id=user_id)
    cycle_service = StudyCycleOrchestratorService(repository)
    cycle_state = cycle_service.build_cycle(graph.graph_id, user_id=user_id)
    builder = SimuladoBlueprintBuilderService(repository)
    blueprint_state = builder.build_blueprint(
        cycle_state.cycle_id,
        user_id=user_id,
        profile_id=fixture.get("profile_id"),
    )
    blueprint = repository.get_simulado_blueprint(cycle_state.cycle_id, user_id=user_id)
    return {
        "repository": repository,
        "graph": graph,
        "cycle_state": cycle_state,
        "blueprint_state": blueprint_state,
        "blueprint": blueprint,
    }


def run_simulado_blueprint_fixture(tmp_path, fixture: dict[str, object], *, user_id: str = "user-a") -> dict[str, object]:
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    return persist_simulado_blueprint_fixture(repository, fixture, user_id=user_id)


def cebraspe_true_false_confirmed_scoring_blueprint_fixture() -> dict[str, object]:
    graph = covered_graph_fixture()["graph"]
    return {
        "graph": graph,
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview=(
                "Banca CEBRASPE. Julgue os itens seguintes em CERTO ou ERRADO. "
                "Marque o campo C ou o campo E. Cada discordancia com o gabarito implica 1,00 ponto negativo. "
                "Item em branco vale 0."
            ),
        ),
    }


def cebraspe_true_false_unconfirmed_scoring_blueprint_fixture() -> dict[str, object]:
    graph = covered_graph_fixture()["graph"]
    return {
        "graph": graph,
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview="CEBRASPE. Julgue os itens seguintes em CERTO ou ERRADO, com campo C e campo E.",
        ),
    }


def cebraspe_multiple_choice_5_blueprint_fixture() -> dict[str, object]:
    graph = balanced_graph_fixture()["graph"]
    return {
        "graph": graph,
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview="Banca CEBRASPE. Prova objetiva com cinco alternativas: A, B, C, D e E. Somente uma correta.",
        ),
    }


def fgv_multiple_choice_5_blueprint_fixture() -> dict[str, object]:
    graph = balanced_graph_fixture()["graph"]
    return {
        "graph": graph,
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview="FGV. Prova objetiva com cinco alternativas A, B, C, D e E. Apenas uma correta.",
        ),
    }


def fgv_mixed_discursive_hint_blueprint_fixture() -> dict[str, object]:
    graph = balanced_graph_fixture()["graph"]
    return {
        "graph": graph,
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview=(
                "FGV. Prova objetiva com cinco alternativas A, B, C, D e E. "
                "Questoes discursivas com folha de textos definitivos."
            ),
        ),
    }


def pscpp_technical_maritime_blueprint_fixture() -> dict[str, object]:
    graph = maritime_graph_fixture()["graph"]
    return {
        "graph": graph,
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview=(
                "PSCPP. Praticante de Pratico. Servico de Praticagem. DPC. NORMAM-311. "
                "Autoridade Maritima. Bibliografia Sugerida. Ship Manoeuvrability."
            ),
        ),
    }


def pscpp_with_ocr_and_material_gaps_blueprint_fixture() -> dict[str, object]:
    graph = maritime_graph_fixture()["graph"]
    return {
        "graph": graph,
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview=(
                "PSCPP. Praticagem. DPC. NORMAM-311. Prova objetiva tecnica com bibliografia sugerida "
                "e conteudo tecnico-operacional maritimo."
            ),
        ),
    }


def unknown_format_blueprint_fixture() -> dict[str, object]:
    graph = balanced_graph_fixture()["graph"]
    return {
        "graph": graph,
        "profile_id": "exam-profile:cebraspe",
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview="Processo seletivo com prova objetiva, conteudo programatico e avaliacao.",
        ),
    }


def conflicting_format_blueprint_fixture() -> dict[str, object]:
    graph = covered_graph_fixture()["graph"]
    return {
        "graph": graph,
        "profile_id": "exam-profile:cebraspe",
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview="Julgue os itens em Certo ou Errado. A prova tambem menciona alternativas A, B, C, D e E para marcacao.",
        ),
    }


def material_blocked_blueprint_fixture() -> dict[str, object]:
    graph = material_blocked_graph_fixture()["graph"]
    return {"graph": graph, "profile_id": "exam-profile:marinha-pscpp"}


def ocr_blocked_blueprint_fixture() -> dict[str, object]:
    graph = ocr_graph_fixture()["graph"]
    return {"graph": graph, "profile_id": "exam-profile:marinha-pscpp"}


def ambiguous_topic_blueprint_fixture() -> dict[str, object]:
    graph = ambiguous_graph_fixture()["graph"]
    return {"graph": graph, "profile_id": "exam-profile:fgv"}


def mixed_ready_blocked_blueprint_fixture() -> dict[str, object]:
    graph = mixed_complex_graph_fixture()["graph"]
    updated_topics = []
    for topic in graph.topics:
        if topic.topic_id == "topic:ripeam":
            updated_topics.append(
                topic.model_copy(
                    update={
                        "evidence": [
                            build_evidence(
                                evidence_id="e:mixed-ripeam",
                                source_id="doc:ripeam",
                                excerpt="RIPEAM com regras de governo e rumo.",
                                matched_terms=["ripeam"],
                                confidence=0.9,
                            )
                        ]
                    }
                )
            )
        elif topic.topic_id == "topic:meteo":
            updated_topics.append(
                topic.model_copy(
                    update={
                        "evidence": [
                            build_evidence(
                                evidence_id="e:mixed-meteo",
                                source_id="doc:meteo",
                                excerpt="Ventos, cartas sinoticas e previsao meteorologica.",
                                matched_terms=["ventos", "meteorologia"],
                                confidence=0.58,
                            )
                        ]
                    }
                )
            )
        else:
            updated_topics.append(topic)
    graph = graph.model_copy(update={"topics": updated_topics})
    return {"graph": graph, "profile_id": "exam-profile:fgv"}


def weak_topic_allocation_blueprint_fixture() -> dict[str, object]:
    graph = weak_graph_fixture()["graph"]
    return {"graph": graph, "profile_id": "exam-profile:fgv"}


def edital_weight_hint_distribution_blueprint_fixture() -> dict[str, object]:
    graph = multi_subject_graph_fixture()["graph"]
    return {
        "graph": graph,
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview="FGV. Prova objetiva com cinco alternativas A, B, C, D e E. 80 questoes.",
            weight_hints=[build_question_count_hint(weight_id="weight:80", value=80.0)],
        ),
    }


def profile_hint_distribution_blueprint_fixture() -> dict[str, object]:
    graph = multi_subject_graph_fixture()["graph"]
    return {"graph": graph, "profile_id": "exam-profile:fgv"}


def insufficient_sources_blueprint_fixture() -> dict[str, object]:
    graph = covered_graph_fixture()["graph"].model_copy(update={"subjects": [], "topics": []})
    return {"graph": graph, "profile_id": "exam-profile:unknown"}


def no_ready_topics_blueprint_fixture() -> dict[str, object]:
    graph = gap_heavy_graph_fixture()["graph"]
    return {"graph": graph, "profile_id": "exam-profile:marinha-pscpp"}


def multi_subject_balanced_blueprint_fixture() -> dict[str, object]:
    graph = multi_subject_graph_fixture()["graph"]
    return {
        "graph": graph,
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview="FGV. Prova objetiva com cinco alternativas A, B, C, D e E. Duracao de 180 minutos.",
        ),
    }


def no_question_generation_safety_fixture() -> dict[str, object]:
    graph = balanced_graph_fixture()["graph"]
    return {
        "graph": graph,
        "edital_result": build_edital_result_with_weight_hints(
            edital_id=graph.edital_id,
            preview=(
                "FGV. Prova objetiva com cinco alternativas A, B, C, D e E. "
                "Apenas uma correta. Duracao de 180 minutos."
            ),
        ),
    }


ALL_SIMULADO_BLUEPRINT_FIXTURES = [
    cebraspe_true_false_confirmed_scoring_blueprint_fixture,
    cebraspe_true_false_unconfirmed_scoring_blueprint_fixture,
    cebraspe_multiple_choice_5_blueprint_fixture,
    fgv_multiple_choice_5_blueprint_fixture,
    fgv_mixed_discursive_hint_blueprint_fixture,
    pscpp_technical_maritime_blueprint_fixture,
    pscpp_with_ocr_and_material_gaps_blueprint_fixture,
    unknown_format_blueprint_fixture,
    conflicting_format_blueprint_fixture,
    material_blocked_blueprint_fixture,
    ocr_blocked_blueprint_fixture,
    ambiguous_topic_blueprint_fixture,
    mixed_ready_blocked_blueprint_fixture,
    weak_topic_allocation_blueprint_fixture,
    edital_weight_hint_distribution_blueprint_fixture,
    profile_hint_distribution_blueprint_fixture,
    insufficient_sources_blueprint_fixture,
    no_ready_topics_blueprint_fixture,
    multi_subject_balanced_blueprint_fixture,
    no_question_generation_safety_fixture,
]
