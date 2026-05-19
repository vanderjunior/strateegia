import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_attempt_shell import SimuladoAttemptShellService
from tests.fixtures.simulado_question_assemblies import (
    assembly_json_keys,
    build_assembly,
    bounded_summary_fixture,
    ready_for_review_candidate_fixture,
)


def test_simulado_attempt_shell_does_not_leak_sensitive_or_final_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = bounded_summary_fixture(tmp_path, repository=repository)
    assembly = build_assembly(fixture)
    assert assembly is not None
    result = SimuladoAttemptShellService(repository).build_attempt_shell(
        assembly.assembly_id,
        user_id=fixture.context.user_id,
    )
    assert result is not None
    dumped_payload = result.model_dump(mode="json")
    dumped = json.dumps(dumped_payload, ensure_ascii=True)
    dumped_keys = assembly_json_keys(dumped_payload)

    assert "password_hash" not in dumped
    assert "studyflow_session" not in dumped
    assert "/Users/" not in dumped
    assert "/private/" not in dumped
    assert "data:image" not in dumped
    assert "raw_runtime_block" not in dumped
    assert "final_question" not in dumped_keys
    assert "final_answer_key" not in dumped_keys
    assert "final_explanation" not in dumped_keys
    assert "student_attempt" not in dumped_keys
    assert "answer_submission" not in dumped_keys
    assert "correction_result" not in dumped_keys
    assert "scoring_result" not in dumped_keys


def test_simulado_attempt_shell_build_and_get_do_not_mutate_source_assembly(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = ready_for_review_candidate_fixture(tmp_path, repository=repository)
    assembly = build_assembly(fixture)
    assert assembly is not None
    service = SimuladoAttemptShellService(repository)

    before = repository.get_simulado_question_assembly(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )
    built = service.build_attempt_shell(assembly.assembly_id, user_id=fixture.context.user_id)
    assert built is not None
    loaded = service.get_attempt_shell(
        assembly.assembly_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_attempt_shell_by_id(
        built.attempt_shell_id,
        user_id=fixture.context.user_id,
    )
    after = repository.get_simulado_question_assembly(
        fixture.blueprint_set.source_simulado_blueprint_id,
        user_id=fixture.context.user_id,
    )

    assert before is not None
    assert loaded is not None
    assert by_id is not None
    assert after is not None
    assert built.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before.model_dump(mode="json") == after.model_dump(mode="json")
