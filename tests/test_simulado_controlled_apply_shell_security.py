import json

from app.repositories.json_store import JsonStudyRepository
from app.services.simulado_controlled_apply_shell import (
    SimuladoControlledRuntimeApplyShellService,
)
from tests.fixtures.simulado_controlled_apply_shells import (
    build_controlled_apply_shell,
    no_runtime_mutation_fixture,
)
from tests.fixtures.simulado_question_assemblies import assembly_json_keys


def test_controlled_apply_shell_does_not_leak_sensitive_or_answer_key_content(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = no_runtime_mutation_fixture(tmp_path, repository=repository)
    result = build_controlled_apply_shell(fixture)
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
    assert "correct_answer" not in dumped_keys
    assert "correct_option" not in dumped_keys
    assert "answer_key" not in dumped_keys
    assert "answer_key_value" not in dumped_keys
    assert "gabarito" not in dumped_keys
    assert "final_question_content" not in dumped_keys
    assert "final_answer_key_content" not in dumped_keys
    assert "final_explanation_content" not in dumped_keys
    assert "runtime_application_event" not in dumped_keys
    assert "final_pedagogical_update_event" not in dumped_keys


def test_controlled_apply_shell_build_and_get_do_not_mutate_source_artifacts(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    fixture = no_runtime_mutation_fixture(tmp_path, repository=repository)
    result = build_controlled_apply_shell(fixture)
    assert result is not None
    application = fixture.runtime_progress_application
    assert application is not None
    service = SimuladoControlledRuntimeApplyShellService(repository)

    before_application = repository.get_simulado_runtime_progress_application_by_id(
        application.application_id,
        user_id=fixture.context.user_id,
    )
    before_runtime_guardrail = repository.get_simulado_runtime_guardrail_by_id(
        application.source_runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    before_integrated = repository.get_simulado_integrated_result_by_id(
        application.source_integrated_result_id,
        user_id=fixture.context.user_id,
    )
    before_progress = repository.load_progress(user_id=fixture.context.user_id)

    loaded = service.get_apply_shell(
        application.application_id,
        user_id=fixture.context.user_id,
    )
    by_id = service.get_apply_shell_by_id(
        result.apply_shell_id,
        user_id=fixture.context.user_id,
    )

    after_application = repository.get_simulado_runtime_progress_application_by_id(
        application.application_id,
        user_id=fixture.context.user_id,
    )
    after_runtime_guardrail = repository.get_simulado_runtime_guardrail_by_id(
        application.source_runtime_guardrail_id,
        user_id=fixture.context.user_id,
    )
    after_integrated = repository.get_simulado_integrated_result_by_id(
        application.source_integrated_result_id,
        user_id=fixture.context.user_id,
    )
    after_progress = repository.load_progress(user_id=fixture.context.user_id)

    assert before_application is not None
    assert before_runtime_guardrail is not None
    assert before_integrated is not None
    assert loaded is not None
    assert by_id is not None
    assert after_application is not None
    assert after_runtime_guardrail is not None
    assert after_integrated is not None
    assert result.model_dump(mode="json") == loaded.model_dump(mode="json") == by_id.model_dump(mode="json")
    assert before_application.model_dump(mode="json") == after_application.model_dump(mode="json")
    assert before_runtime_guardrail.model_dump(mode="json") == after_runtime_guardrail.model_dump(mode="json")
    assert before_integrated.model_dump(mode="json") == after_integrated.model_dump(mode="json")
    assert before_progress.model_dump(mode="json") == after_progress.model_dump(mode="json")
