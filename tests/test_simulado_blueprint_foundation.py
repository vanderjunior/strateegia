import json

from app.domain.models import EditalExtractionResult
from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_blueprint_builder import SimuladoBlueprintBuilderService
from app.services.study_cycle_orchestrator import StudyCycleOrchestratorService
from tests.fixtures.study_cycle_graphs import (
    balanced_cycle_fixture,
    covered_topic_cycle_fixture,
    maritime_praticagem_cycle_fixture,
    material_blocked_cycle_fixture,
    mixed_complex_cycle_fixture,
)


def persist_graph_fixture(
    repository: JsonStudyRepository,
    fixture: dict[str, object],
    *,
    user_id: str = "user-a",
):
    graph = fixture["graph"].model_copy(update={"user_id": user_id})
    repository.save_curriculum_graph(graph, user_id=user_id)
    return graph


def persist_edital_preview(
    repository: JsonStudyRepository,
    *,
    edital_id: str,
    user_id: str,
    preview: str,
) -> EditalExtractionResult:
    result = EditalExtractionResult(
        edital_id=edital_id,
        document_id=edital_id.replace("edital:", "doc:"),
        user_id=user_id,
        source_text_length=len(preview),
        metadata={"source_text_preview": preview},
    )
    repository.save_edital_extraction_result(result, user_id=user_id)
    return result


def build_cycle_and_blueprint(
    repository: JsonStudyRepository,
    fixture: dict[str, object],
    *,
    profile_id: str | None = None,
    edital_preview: str | None = None,
    user_id: str = "user-a",
):
    graph = persist_graph_fixture(repository, fixture, user_id=user_id)
    if edital_preview:
        persist_edital_preview(repository, edital_id=graph.edital_id, user_id=user_id, preview=edital_preview)
    cycle_service = StudyCycleOrchestratorService(repository)
    cycle_state = cycle_service.build_cycle(graph.graph_id, user_id=user_id)
    builder = SimuladoBlueprintBuilderService(repository)
    blueprint_state = builder.build_blueprint(cycle_state.cycle_id, user_id=user_id, profile_id=profile_id)
    blueprint = repository.get_simulado_blueprint(cycle_state.cycle_id, user_id=user_id)
    return graph, cycle_state, blueprint_state, blueprint


def test_simulado_blueprint_handles_missing_sources_and_unknown_profile_safely(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    builder = SimuladoBlueprintBuilderService(repository)

    missing_cycle = builder.build_blueprint("cycle:missing", user_id="user-a")
    assert missing_cycle is not None
    assert missing_cycle.status == "insufficient_cycle"

    graph, cycle_state, blueprint_state, blueprint = build_cycle_and_blueprint(
        repository,
        {"graph": covered_topic_cycle_fixture()["graph"].model_copy(update={"subjects": [], "topics": []})},
        profile_id="exam-profile:unknown",
    )

    assert graph.graph_id == "graph:covered"
    assert cycle_state.status == "insufficient_graph"
    assert blueprint_state.status in {"insufficient_profile", "insufficient_sources"}
    assert blueprint is not None
    assert blueprint.question_slots == []
    assert any(item.code in {"insufficient_study_cycle", "insufficient_exam_profile"} for item in blueprint.warnings)


def test_simulado_blueprint_resolves_true_false_format_scoring_and_non_generation_rules(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    _, cycle_state, blueprint_state, blueprint = build_cycle_and_blueprint(
        repository,
        covered_topic_cycle_fixture(),
        edital_preview=(
            "Banca CEBRASPE. Julgue os itens em CERTO ou ERRADO. Marque o campo C ou o campo E. "
            "Discordancia com o gabarito gera 1,00 ponto negativo e em branco vale 0."
        ),
    )

    assert cycle_state.status == "ready_for_review"
    assert blueprint_state.status == "ready_for_review"
    assert blueprint is not None
    assert blueprint.format_type == "true_false"
    assert blueprint.scoring_plan.negative_marking is True
    assert blueprint.scoring_plan.scoring_source == "explicit_edital"
    assert blueprint.sections[0].section_type == "true_false_block"
    assert blueprint.question_slots
    assert all(slot.format_type == "true_false" for slot in blueprint.question_slots)
    assert all("question_text" not in slot.model_dump(mode="json") for slot in blueprint.question_slots)
    assert all("options" not in slot.model_dump(mode="json") for slot in blueprint.question_slots)
    assert all("gabarito" not in slot.model_dump(mode="json") for slot in blueprint.question_slots)
    assert any(item.constraint_type == "no_question_generation_in_this_pass" for item in blueprint.generation_constraints)


def test_simulado_blueprint_resolves_multiple_choice_distribution_and_json_safe_round_trip(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    _, _, first_state, first_blueprint = build_cycle_and_blueprint(
        repository,
        balanced_cycle_fixture(),
        edital_preview=(
            "FGV. Prova objetiva com cinco alternativas A, B, C, D e E, apenas uma correta. "
            "Questoes discursivas e folha de textos definitivos."
        ),
    )
    _, _, second_state, second_blueprint = build_cycle_and_blueprint(
        repository,
        balanced_cycle_fixture(),
        edital_preview=(
            "FGV. Prova objetiva com cinco alternativas A, B, C, D e E, apenas uma correta. "
            "Questoes discursivas e folha de textos definitivos."
        ),
    )
    listed = repository.list_user_simulado_blueprints(user_id="user-a")

    assert first_state.model_dump(mode="json") == second_state.model_dump(mode="json")
    assert first_blueprint.model_dump(mode="json") == second_blueprint.model_dump(mode="json")
    assert len(listed) == 1
    assert first_blueprint.format_type == "mixed"
    assert first_blueprint.sections[0].section_type == "multiple_choice_block"
    assert any(section.section_type == "discursive_hint" for section in first_blueprint.sections)
    assert first_blueprint.distribution_plan.question_count_source in {"exam_profile_hint", "default_candidate", "explicit_edital"}
    assert all(slot.format_type == "multiple_choice_5" for slot in first_blueprint.question_slots)
    assert all(slot.generation_style in {"interpretive", "case_based", "applied_problem_solving", "unknown"} for slot in first_blueprint.question_slots)
    json.dumps(first_state.model_dump(mode="json"), ensure_ascii=True)
    dumped = json.dumps(first_blueprint.model_dump(mode="json"), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped


def test_simulado_blueprint_preserves_pscpp_family_and_technical_maritime_constraints(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    _, _, blueprint_state, blueprint = build_cycle_and_blueprint(
        repository,
        maritime_praticagem_cycle_fixture(),
        edital_preview=(
            "PSCPP. Praticante de Pratico. Servico de Praticagem. DPC. NORMAM-311. "
            "Autoridade Maritima. Bibliografia Sugerida. Ship Manoeuvrability."
        ),
    )

    assert blueprint_state.status == "ready_for_review"
    assert blueprint is not None
    assert blueprint.exam_family == "PSCPP"
    assert blueprint.sections[0].section_type == "technical_maritime_block"
    assert any(slot.generation_style == "technical_maritime" for slot in blueprint.question_slots)
    assert any(item.constraint_type == "require_source_topic_mapping" for item in blueprint.generation_constraints)
    assert any(item.constraint_type == "exam_family_over_board" for item in blueprint.generation_constraints) is False
    assert blueprint.metadata["allow_english_terms"] is True
    assert blueprint.metadata["bibliography_driven"] is True


def test_simulado_blueprint_readiness_and_coverage_plan_stay_conservative_for_blocked_sources(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    _, _, blocked_state, blocked_blueprint = build_cycle_and_blueprint(
        repository,
        material_blocked_cycle_fixture(),
        profile_id="exam-profile:marinha-pscpp",
    )
    _, _, mixed_state, mixed_blueprint = build_cycle_and_blueprint(
        repository,
        mixed_complex_cycle_fixture(),
        profile_id="exam-profile:fgv",
    )

    assert blocked_state.status == "ready_for_review"
    assert blocked_blueprint.readiness_profile.readiness_state in {
        "blueprint_material_blocked",
        "blueprint_ocr_blocked",
        "blueprint_partially_ready",
    }
    assert blocked_blueprint.coverage_plan.ocr_blocked_slots >= 1
    assert blocked_blueprint.coverage_plan.uncovered_topic_slots >= 1
    assert blocked_blueprint.coverage_plan.excluded_gap_ids
    assert any(slot.readiness_state in {"blocked_by_material_gap", "blocked_by_ocr"} for slot in blocked_blueprint.question_slots)

    assert mixed_state.status == "ready_for_review"
    assert mixed_blueprint.readiness_profile.review_needed_slot_count >= 1
    assert mixed_blueprint.coverage_plan.ambiguous_slots >= 1
    assert any(slot.readiness_state == "blocked_by_ambiguity" for slot in mixed_blueprint.question_slots)
    assert any(item.constraint_type == "avoid_ocr_blocked_topic" for item in mixed_blueprint.generation_constraints)
    assert any(item.constraint_type == "require_manual_review" for item in mixed_blueprint.generation_constraints)
