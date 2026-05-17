import json

from app.repositories.json_store import JsonStudyRepository
from app.services.curriculum_graph_builder import CurriculumGraphBuilderService
from tests.fixtures.curriculum_graph_documents import (
    ALL_CURRICULUM_GRAPH_FIXTURES,
    ambiguous_reference_graph_fixture,
    basic_covered_graph_fixture,
    low_edital_graph_fixture,
    maritime_praticagem_curriculum_graph_fixture,
    missing_document_text_graph_fixture,
    mixed_review_needed_graph_fixture,
    no_alignment_graph_fixture,
    ocr_required_graph_fixture,
    partial_coverage_graph_fixture,
    redundancy_graph_fixture,
    subject_fallback_graph_fixture,
    subtopic_hierarchy_graph_fixture,
    uncovered_topic_graph_fixture,
    weak_coverage_graph_fixture,
)


def run_curriculum_graph_fixture(tmp_path, fixture: dict[str, object], *, user_id: str = "user-a") -> dict[str, object]:
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    builder = CurriculumGraphBuilderService(repository)
    edital = fixture["edital"].model_copy(update={"user_id": user_id})
    repository.save_edital_extraction_result(edital, user_id=user_id)
    if fixture.get("alignment") is not None:
        alignment = fixture["alignment"].model_copy(update={"user_id": user_id})
        repository.save_bibliography_alignment_result(alignment, user_id=user_id)
    state = builder.build_graph(edital.edital_id, user_id=user_id)
    graph = repository.get_curriculum_graph(edital.edital_id, user_id=user_id)
    return {
        "repository": repository,
        "builder": builder,
        "state": state,
        "graph": graph,
        "edital": edital,
    }


def assert_json_safe(model) -> None:
    dumped = json.dumps(model.model_dump(mode="json"), ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped


def topic_by_title(graph, title: str):
    return next(item for item in graph.topics if item.title == title)


def test_curriculum_graph_fixture_sanity_is_deterministic_and_json_safe():
    for builder in ALL_CURRICULUM_GRAPH_FIXTURES:
        first = builder()
        second = builder()
        assert first["edital"].model_dump(mode="json") == second["edital"].model_dump(mode="json")
        if first.get("alignment") is not None:
            assert first["alignment"].model_dump(mode="json") == second["alignment"].model_dump(mode="json")
        json.dumps(first["edital"].model_dump(mode="json"), ensure_ascii=True)
        if first.get("alignment") is not None:
            json.dumps(first["alignment"].model_dump(mode="json"), ensure_ascii=True)


def test_basic_covered_and_partial_graphs_preserve_coverage_links_and_hierarchy(tmp_path):
    covered = run_curriculum_graph_fixture(tmp_path / "covered", basic_covered_graph_fixture())
    partial = run_curriculum_graph_fixture(tmp_path / "partial", partial_coverage_graph_fixture())
    covered_graph = covered["graph"]
    partial_graph = partial["graph"]

    ripeam = topic_by_title(covered_graph, "RIPEAM")
    meteorologia = topic_by_title(partial_graph, "Meteorologia")

    assert covered_graph.subjects
    assert ripeam.coverage_state == "covered"
    assert ripeam.review_state in {"ready_for_review", "candidate"}
    assert any(link.target_type == "topic" and link.target_id == ripeam.topic_id for link in covered_graph.coverage_links)
    assert any(evidence.document_id == "doc:ripeam" for evidence in ripeam.evidence)
    assert meteorologia.coverage_state == "partially_covered"
    assert meteorologia.review_state in {"candidate", "needs_review", "ready_for_review"}
    assert len(partial_graph.subtopics) == 2
    assert [item.title for item in partial_graph.subtopics] == ["Ventos", "Frentes"]


def test_weak_and_uncovered_graphs_remain_conservative(tmp_path):
    weak = run_curriculum_graph_fixture(tmp_path / "weak", weak_coverage_graph_fixture())
    uncovered = run_curriculum_graph_fixture(tmp_path / "uncovered", uncovered_topic_graph_fixture())

    weak_topic = topic_by_title(weak["graph"], "Legislacao Maritima Especial")
    uncovered_topic = topic_by_title(uncovered["graph"], "Arte Naval")

    assert weak_topic.coverage_state in {"weakly_covered", "uncovered"}
    assert weak_topic.review_state in {"candidate", "needs_review"}
    assert weak_topic.confidence <= 0.35
    assert uncovered_topic.coverage_state == "uncovered"
    assert uncovered_topic.review_state in {"needs_review", "source_missing"}
    assert any(gap.gap_type == "uncovered_topic" for gap in uncovered["graph"].gaps)
    assert uncovered["graph"].summary.uncovered_topics_count >= 1


def test_ocr_required_and_missing_document_text_are_preserved_without_fake_coverage(tmp_path):
    ocr = run_curriculum_graph_fixture(tmp_path / "ocr", ocr_required_graph_fixture())
    missing_text = run_curriculum_graph_fixture(tmp_path / "missing-text", missing_document_text_graph_fixture())

    ocr_topic = topic_by_title(ocr["graph"], "Autoridade Maritima Aplicada")
    missing_text_topic = topic_by_title(missing_text["graph"], "Navegacao Costeira")

    assert ocr_topic.coverage_state in {"uncovered", "insufficient_evidence"}
    assert ocr_topic.review_state == "ocr_required"
    assert any(gap.gap_type == "ocr_required" for gap in ocr["graph"].gaps)
    assert ocr["graph"].summary.ocr_required_count >= 1
    assert missing_text_topic.coverage_state in {"uncovered", "insufficient_evidence"}
    assert missing_text_topic.review_state in {"source_missing", "needs_review"}
    assert any(gap.gap_type == "missing_document_text" for gap in missing_text["graph"].gaps)


def test_ambiguous_and_redundant_graph_states_are_preserved_without_auto_resolution(tmp_path):
    ambiguous = run_curriculum_graph_fixture(tmp_path / "ambiguous", ambiguous_reference_graph_fixture())
    redundant = run_curriculum_graph_fixture(tmp_path / "redundant", redundancy_graph_fixture())

    ambiguous_topic = topic_by_title(ambiguous["graph"], "RIPEAM")
    assert ambiguous_topic.coverage_state == "partially_covered"
    assert ambiguous_topic.review_state == "ambiguous"
    assert any(gap.gap_type == "ambiguous_reference" for gap in ambiguous["graph"].gaps)

    redundancy_types = {item.redundancy_type for item in redundant["graph"].redundancies}
    assert "duplicate_bibliography_match" in redundancy_types
    assert "overlapping_topic_coverage" in redundancy_types
    assert any(item.overlapping_document_ids for item in redundant["graph"].redundancies)
    assert redundant["graph"].summary.redundancy_count >= 2


def test_subject_fallback_and_subtopic_hierarchy_are_stable(tmp_path):
    fallback = run_curriculum_graph_fixture(tmp_path / "fallback", subject_fallback_graph_fixture())
    hierarchy = run_curriculum_graph_fixture(tmp_path / "hierarchy", subtopic_hierarchy_graph_fixture())

    fallback_graph = fallback["graph"]
    hierarchy_graph = hierarchy["graph"]

    assert fallback_graph.subjects[0].subject_id == "subject:conteudo-programatico"
    assert fallback_graph.subjects[0].title == "Conteudo Programatico"
    assert topic_by_title(fallback_graph, "Comunicacoes").subject_id == fallback_graph.subjects[0].subject_id

    meteorologia = topic_by_title(hierarchy_graph, "Meteorologia")
    assert meteorologia.subtopic_ids == ["subtopic:ventos", "subtopic:frentes", "subtopic:cartas"]
    assert [item.parent_topic_id for item in hierarchy_graph.subtopics] == [meteorologia.topic_id] * 3
    assert [item.title for item in hierarchy_graph.subtopics] == ["Ventos", "Frentes Frias", "Cartas Sinoticas"]
    assert all(item.coverage_state == meteorologia.coverage_state for item in hierarchy_graph.subtopics)


def test_maritime_and_mixed_review_needed_graphs_cover_expected_states(tmp_path):
    maritime = run_curriculum_graph_fixture(tmp_path / "maritime", maritime_praticagem_curriculum_graph_fixture())
    mixed = run_curriculum_graph_fixture(tmp_path / "mixed", mixed_review_needed_graph_fixture())

    maritime_titles = [item.title for item in maritime["graph"].topics]
    assert maritime_titles == ["Arte Naval", "RIPEAM", "Manobra", "Meteorologia", "Legislacao Maritima"]
    assert topic_by_title(maritime["graph"], "RIPEAM").coverage_state in {"covered", "partially_covered"}
    assert topic_by_title(maritime["graph"], "Meteorologia").coverage_state in {"covered", "partially_covered"}
    assert topic_by_title(maritime["graph"], "Arte Naval").coverage_state == "uncovered"
    assert any(gap.gap_type == "ocr_required" for gap in maritime["graph"].gaps)

    mixed_states = {item.coverage_state for item in mixed["graph"].topics}
    mixed_reviews = {item.review_state for item in mixed["graph"].topics}
    assert "covered" in mixed_states
    assert "partially_covered" in mixed_states
    assert "weakly_covered" in mixed_states or "uncovered" in mixed_states
    assert "needs_review" in mixed_reviews or "source_missing" in mixed_reviews
    assert "ocr_required" in mixed_reviews
    assert "ambiguous" in mixed_reviews
    assert mixed["graph"].summary.needs_review_count > 0
    assert mixed["graph"].gaps
    assert mixed["graph"].redundancies


def test_missing_alignment_and_low_edital_are_safe_and_do_not_fake_topics(tmp_path):
    no_alignment = run_curriculum_graph_fixture(tmp_path / "no-alignment", no_alignment_graph_fixture())
    low_edital = run_curriculum_graph_fixture(tmp_path / "low-edital", low_edital_graph_fixture())

    assert no_alignment["state"].status == "insufficient_alignment"
    assert no_alignment["graph"].topics
    assert no_alignment["graph"].coverage_links == []
    assert any(item.code == "missing_bibliography_alignment" for item in no_alignment["graph"].warnings)

    assert low_edital["state"].status in {"insufficient_alignment", "insufficient_edital"}
    assert low_edital["graph"].topics == []
    assert low_edital["graph"].coverage_links == []
    assert_json_safe(low_edital["state"])
    assert_json_safe(low_edital["graph"])


def test_graph_nodes_links_and_outputs_are_json_safe_and_bounded(tmp_path):
    context = run_curriculum_graph_fixture(tmp_path, mixed_review_needed_graph_fixture())
    state = context["state"]
    graph = context["graph"]

    assert_json_safe(state)
    assert_json_safe(graph)
    assert all(0.0 <= item.confidence <= 1.0 for item in graph.topics)
    assert all(item.reasoning for item in graph.topics)
    assert all(0.0 <= link.confidence <= 1.0 for link in graph.coverage_links)
    assert all(link.reasoning for link in graph.coverage_links)
    assert all(len(item.excerpt) <= 160 for link in graph.coverage_links for item in link.evidence)


def test_curriculum_graph_build_is_deterministic_and_idempotent(tmp_path):
    fixture = mixed_review_needed_graph_fixture()
    first = run_curriculum_graph_fixture(tmp_path / "first", fixture)
    second = run_curriculum_graph_fixture(tmp_path / "second", fixture)
    rerun_state = first["builder"].build_graph(first["edital"].edital_id, user_id="user-a")
    rerun_graph = first["repository"].get_curriculum_graph(first["edital"].edital_id, user_id="user-a")

    assert first["state"].graph_id == second["state"].graph_id
    assert [item.title for item in first["graph"].topics] == [item.title for item in second["graph"].topics]
    assert [item.coverage_state for item in first["graph"].topics] == [item.coverage_state for item in second["graph"].topics]
    assert first["state"].model_dump(mode="json") == rerun_state.model_dump(mode="json")
    assert first["graph"].model_dump(mode="json") == rerun_graph.model_dump(mode="json")


def test_curriculum_graph_fixture_flow_respects_user_scope(tmp_path):
    owner = run_curriculum_graph_fixture(tmp_path / "owner", basic_covered_graph_fixture(), user_id="owner")
    other = run_curriculum_graph_fixture(tmp_path / "other", no_alignment_graph_fixture(), user_id="other")

    assert owner["graph"].topics
    assert other["state"].status == "insufficient_alignment"
    assert owner["repository"].get_curriculum_graph(owner["edital"].edital_id, user_id="other") is None
    assert owner["repository"].get_curriculum_graph_by_id(owner["state"].graph_id, user_id="other") is None
