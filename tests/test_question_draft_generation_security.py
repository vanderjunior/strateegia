import json

from app.repositories.json_store import JsonStudyRepository
from app.services.document_pipeline import DocumentPipelineService
from app.services.material_service import MaterialService
from app.services.question_draft_generation import QuestionDraftGenerationService
from app.services.question_generation_blueprint import QuestionGenerationBlueprintService
from tests.fixtures.question_generation_blueprints import (
    long_chunk_snippet_fixture,
    ready_source_grounded_slot_fixture,
)


def create_services(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    storage_root = tmp_path / "uploads"
    return (
        repository,
        MaterialService(repository, storage_root=storage_root),
        DocumentPipelineService(repository, storage_root=storage_root),
        QuestionGenerationBlueprintService(repository),
        QuestionDraftGenerationService(repository),
    )


def test_question_draft_generation_snippets_are_bounded_and_sanitized(tmp_path):
    _, _, _, _, service = create_services(tmp_path)
    fixture = long_chunk_snippet_fixture(tmp_path)
    blueprint_set = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    result = service.build_draft_set(blueprint_set.blueprint_set_id, user_id=fixture.context.user_id)
    dumped = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)
    source_ref = result.drafts[0].source_references[0]

    assert source_ref.safe_snippet is not None
    assert len(source_ref.safe_snippet) <= 240
    assert "/Users/" not in source_ref.safe_snippet
    assert fixture.chunk.text not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped


def test_question_draft_generation_does_not_leak_or_mutate_runtime_artifacts(tmp_path, monkeypatch):
    repository, _, _, qgb_service, draft_service = create_services(tmp_path)
    fixture = ready_source_grounded_slot_fixture(tmp_path)
    blueprint_set = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    before_graph = fixture.context.repository.get_curriculum_graph_by_id(
        fixture.graph.graph_id,
        user_id=fixture.context.user_id,
    )
    before_simulado = fixture.context.repository.get_simulado_blueprint_by_id(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    before_qgb = fixture.context.repository.get_question_generation_blueprint(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )

    def fail_build(*args, **kwargs):
        raise AssertionError("Question generation blueprint rebuild should not run during draft generation.")

    monkeypatch.setattr(qgb_service, "build_blueprint_set", fail_build)
    result = draft_service.build_draft_set(blueprint_set.blueprint_set_id, user_id=fixture.context.user_id)
    dumped = json.dumps(result.model_dump(mode="json"), ensure_ascii=True)
    after_graph = fixture.context.repository.get_curriculum_graph_by_id(
        fixture.graph.graph_id,
        user_id=fixture.context.user_id,
    )
    after_simulado = fixture.context.repository.get_simulado_blueprint_by_id(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )
    after_qgb = fixture.context.repository.get_question_generation_blueprint(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )

    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "data:image" not in dumped
    assert before_graph.model_dump(mode="json") == after_graph.model_dump(mode="json")
    assert before_simulado.model_dump(mode="json") == after_simulado.model_dump(mode="json")
    assert before_qgb.model_dump(mode="json") == after_qgb.model_dump(mode="json")
