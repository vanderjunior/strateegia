import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.domain.models import BoardStyle, Document, GeneratedQuestion, Topic
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.offline_snapshot_comparison import compare_offline_snapshots
from app.services.snapshot_offline_io import (
    REQUIRED_INSPECTION_PAYLOAD_KEYS,
    SCHEMA_VERSION,
    export_inspection_snapshot,
    import_inspection_snapshot,
    validate_offline_snapshot,
)


def build_document(*, title: str, topic_id: str, question_id: str, created_at: datetime) -> Document:
    topic = Topic(
        id=topic_id,
        title=title,
        content=f"{title} exige leitura normativa, excecoes e comparacoes tecnicas.",
        key_points=[f"Ponto central de {title}"],
        trap_points=[f"Pegadinha comum de {title}"],
        relevance_score=0.85,
        source_pages=[1],
    )
    document = Document.create(
        title=title,
        source_filename=f"{title}.pdf",
        board=BoardStyle.CEBRASPE,
        exam_context="Marinha",
        source_excerpt=f"Trecho de {title}",
        topics=[topic],
        summaries=[],
        questions=[
            GeneratedQuestion(
                id=question_id,
                document_id="placeholder",
                topic_id=topic_id,
                style="certo_errado",
                stem=f"Julgue item sobre {title}.",
                options=["Certo", "Errado"],
                correct_answer="Certo",
                explanation=f"Explicacao de {title}",
                difficulty_level=1,
            )
        ],
    )
    document.created_at = created_at
    document.questions[0].document_id = document.id
    return document


def create_client(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), repository


def start_basic_session(client: TestClient):
    response = client.post("/api/session/start", json={"title": "Sessao", "max_questions": 2})
    assert response.status_code == 200
    return response.json()


def signal(result, name: str):
    return next(item for item in result.regression_signals if item.signal_name == name)


def test_end_to_end_offline_pipeline_is_json_safe_and_read_only(tmp_path, monkeypatch):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 16, 21, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Praticagem",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )
    started = start_basic_session(client)
    calls = {"record_feedback": 0, "review_plan": 0}

    def forbidden_record_feedback(*args, **kwargs):
        calls["record_feedback"] += 1
        raise AssertionError("Offline tooling must not submit answers.")

    def forbidden_build_review_plan(*args, **kwargs):
        calls["review_plan"] += 1
        raise AssertionError("Offline tooling must not create review plans.")

    monkeypatch.setattr("app.api.routes._record_feedback_answer", forbidden_record_feedback)
    monkeypatch.setattr(
        "app.api.routes.LearningDecisionEngine.build_review_plan",
        forbidden_build_review_plan,
    )

    progress_before = repository.load_progress().model_dump(mode="json")
    current_before = client.get(f"/api/session/{started['session_id']}/current").json()

    inspection_response = client.get("/api/inspection/runtime")
    payload = inspection_response.json()
    payload_before = deepcopy(payload)
    exported = export_inspection_snapshot(payload)
    envelope = exported.snapshot_envelope.model_dump(mode="json")
    envelope_before = deepcopy(envelope)
    imported = import_inspection_snapshot(envelope)
    imported_payload_before = deepcopy(imported.imported_payload)
    comparison = compare_offline_snapshots(envelope, imported.imported_payload)

    progress_after = repository.load_progress().model_dump(mode="json")
    current_after = client.get(f"/api/session/{started['session_id']}/current").json()

    assert inspection_response.status_code == 200
    assert payload == payload_before
    assert envelope == envelope_before
    assert imported.imported_payload == imported_payload_before
    assert exported.snapshot_envelope.schema_version == SCHEMA_VERSION
    assert set(imported.imported_payload) == REQUIRED_INSPECTION_PAYLOAD_KEYS
    assert comparison.offline_comparison_state == "offline_comparison_stable"
    assert calls == {"record_feedback": 0, "review_plan": 0}
    assert progress_before == progress_after
    assert current_before == current_after
    json.dumps(payload, ensure_ascii=True)
    json.dumps(envelope, ensure_ascii=True)
    json.dumps(imported.imported_payload, ensure_ascii=True)
    json.dumps(comparison.model_dump(mode="json"), ensure_ascii=True)


def test_no_session_pipeline_is_safe_and_not_a_false_strong_regression(tmp_path):
    client, _ = create_client(tmp_path)

    payload = client.get("/api/inspection/runtime").json()
    exported = export_inspection_snapshot(payload)
    imported = import_inspection_snapshot(exported.snapshot_envelope.model_dump(mode="json"))
    comparison = compare_offline_snapshots(
        exported.snapshot_envelope.model_dump(mode="json"),
        exported.snapshot_envelope.model_dump(mode="json"),
    )

    assert payload["inspection_available"] is False
    assert exported.export_state == "export_ready"
    assert imported.import_state == "import_valid"
    assert comparison.offline_comparison_state == "offline_comparison_stable"
    assert all(item.signal_state != "detected" for item in comparison.regression_signals)
    json.dumps(comparison.model_dump(mode="json"), ensure_ascii=True)


def test_partial_and_legacy_snapshots_warn_and_compare_as_partial():
    legacy_payload = {
        "inspection_available": False,
        "inspection_label": "Legacy snapshot",
        "session": {},
        "raw_runtime_block": {},
    }
    stable_payload = {
        "inspection_available": False,
        "inspection_label": "Internal Runtime Inspection Console — Read Only",
        "session": {"session_id": None},
        "benchmark_summary": {"pedagogical_benchmark_state": "not_available"},
        "benchmark_case_reports": [],
        "scientific_runtime_validation": {},
        "comparative_session_analytics": {},
        "session_export_debug": {},
        "stability_metrics": {},
        "validation_dataset_awareness": {},
        "controlled_tuning_registry": {},
        "tuning_profile_benchmark_comparison": {},
        "manual_experiment_inspection": {},
        "longitudinal_retention": {},
        "raw_runtime_block": {},
    }

    exported_legacy = export_inspection_snapshot(legacy_payload)
    imported_legacy = import_inspection_snapshot(exported_legacy.snapshot_envelope.model_dump(mode="json"))
    exported_stable = export_inspection_snapshot(stable_payload)
    comparison = compare_offline_snapshots(
        exported_legacy.snapshot_envelope.model_dump(mode="json"),
        exported_stable.snapshot_envelope.model_dump(mode="json"),
    )

    assert exported_legacy.export_state == "export_ready_with_warnings"
    assert imported_legacy.import_state == "import_valid_with_warnings"
    assert imported_legacy.validation.missing_required_keys
    assert comparison.offline_comparison_state == "offline_partial_comparison"
    assert comparison.comparison_limitations
    assert signal(comparison, "inspection_availability_lost").signal_state != "detected"
    assert all(item.severity in {"none", "low", "medium", "high"} for item in comparison.regression_signals)


def test_schema_contract_and_payload_key_contract_remain_stable():
    payload = {
        "inspection_available": False,
        "inspection_label": "Internal Runtime Inspection Console — Read Only",
        "session": {"session_id": None},
        "benchmark_summary": {"pedagogical_benchmark_state": "not_available"},
        "benchmark_case_reports": [],
        "scientific_runtime_validation": {},
        "comparative_session_analytics": {},
        "session_export_debug": {},
        "stability_metrics": {},
        "validation_dataset_awareness": {},
        "controlled_tuning_registry": {},
        "tuning_profile_benchmark_comparison": {},
        "manual_experiment_inspection": {},
        "longitudinal_retention": {},
        "raw_runtime_block": {},
    }
    exported = export_inspection_snapshot(payload)
    envelope = exported.snapshot_envelope.model_dump(mode="json")
    unsupported = deepcopy(envelope)
    unsupported["schema_version"] = "inspection-snapshot-v2"
    candidate = deepcopy(envelope)
    candidate["payload_keys"] = sorted(set(candidate["payload_keys"]) | {"future_section"})

    validation = validate_offline_snapshot(envelope)
    imported_unsupported = import_inspection_snapshot(unsupported)
    mismatch = compare_offline_snapshots(envelope, unsupported)
    key_delta = compare_offline_snapshots(envelope, candidate)

    assert validation.validation_state == "snapshot_valid"
    assert envelope["schema_version"] == SCHEMA_VERSION
    assert set(envelope["snapshot_payload"]) == REQUIRED_INSPECTION_PAYLOAD_KEYS
    assert imported_unsupported.import_state == "import_unsupported_schema"
    assert mismatch.offline_comparison_state == "offline_schema_mismatch"
    assert mismatch.baseline_schema_version == SCHEMA_VERSION
    assert mismatch.candidate_schema_version == "inspection-snapshot-v2"
    assert "future_section" in key_delta.added_payload_keys
    assert "inspection_available" in key_delta.shared_payload_keys


def test_real_regressions_still_signal_while_missing_metadata_alone_does_not():
    baseline_payload = {
        "inspection_available": True,
        "inspection_label": "Internal Runtime Inspection Console — Read Only",
        "session": {"session_id": "session-1"},
        "benchmark_summary": {
            "pedagogical_benchmark_state": "benchmark_stable",
            "benchmark_readiness": "benchmark_ready",
            "benchmark_alignment_score": 0.84,
            "benchmark_regression_severity": "none",
            "benchmark_total_cases": 10,
            "benchmark_passed_cases": ["baseline"],
            "benchmark_failed_cases": [],
            "benchmark_inconclusive_cases": [],
            "benchmark_regression_cases": [],
        },
        "benchmark_case_reports": [],
        "scientific_runtime_validation": {},
        "comparative_session_analytics": {},
        "session_export_debug": {},
        "stability_metrics": {
            "scaffold_load_metric": 0.18,
            "compression_safety_metric": 0.91,
        },
        "validation_dataset_awareness": {
            "comparative_validation_alignment": 0.78,
        },
        "controlled_tuning_registry": {},
        "tuning_profile_benchmark_comparison": {},
        "manual_experiment_inspection": {"caution_flags": []},
        "longitudinal_retention": {
            "false_fluency_retention_risk": 0.16,
            "longitudinal_retention_state": "retention_sustainable",
        },
        "raw_runtime_block": {},
    }
    candidate_payload = deepcopy(baseline_payload)
    candidate_payload["stability_metrics"]["scaffold_load_metric"] = 0.33
    candidate_payload["stability_metrics"]["compression_safety_metric"] = 0.51
    candidate_payload["inspection_available"] = False
    candidate_payload["longitudinal_retention"]["false_fluency_retention_risk"] = 0.61
    candidate_payload["longitudinal_retention"]["longitudinal_retention_state"] = "retention_fragile"
    candidate_payload["benchmark_summary"]["benchmark_regression_severity"] = "high"
    candidate_payload["benchmark_summary"]["benchmark_regression_cases"] = ["false_fluency_case"]

    regression = compare_offline_snapshots(
        export_inspection_snapshot(baseline_payload).snapshot_envelope.model_dump(mode="json"),
        export_inspection_snapshot(candidate_payload).snapshot_envelope.model_dump(mode="json"),
    )
    partial = compare_offline_snapshots(
        export_inspection_snapshot(
            {
                "inspection_available": False,
                "inspection_label": "Legacy snapshot",
                "session": {},
                "raw_runtime_block": {},
            }
        ).snapshot_envelope.model_dump(mode="json"),
        export_inspection_snapshot(
            {
                "inspection_available": False,
                "inspection_label": "Legacy snapshot 2",
                "session": {},
                "raw_runtime_block": {},
            }
        ).snapshot_envelope.model_dump(mode="json"),
    )

    assert regression.offline_comparison_state == "offline_regression_risk_detected"
    assert signal(regression, "scaffold_load_increased").signal_state == "detected"
    assert signal(regression, "compression_safety_decreased").signal_state == "detected"
    assert signal(regression, "inspection_availability_lost").signal_state == "detected"
    assert signal(regression, "false_fluency_risk_increased").signal_state == "detected"
    assert partial.offline_comparison_state == "offline_partial_comparison"
    assert all(item.signal_state != "detected" or item.severity != "high" for item in partial.regression_signals)


def test_determinism_of_snapshot_id_and_offline_comparison_output():
    payload = {
        "inspection_available": False,
        "inspection_label": "Internal Runtime Inspection Console — Read Only",
        "session": {"session_id": None},
        "benchmark_summary": {"pedagogical_benchmark_state": "not_available"},
        "benchmark_case_reports": [],
        "scientific_runtime_validation": {},
        "comparative_session_analytics": {},
        "session_export_debug": {},
        "stability_metrics": {},
        "validation_dataset_awareness": {},
        "controlled_tuning_registry": {},
        "tuning_profile_benchmark_comparison": {},
        "manual_experiment_inspection": {},
        "longitudinal_retention": {},
        "raw_runtime_block": {},
    }

    first_export = export_inspection_snapshot(payload)
    second_export = export_inspection_snapshot(payload)
    first_comparison = compare_offline_snapshots(
        first_export.snapshot_envelope.model_dump(mode="json"),
        second_export.snapshot_envelope.model_dump(mode="json"),
    )
    second_comparison = compare_offline_snapshots(
        first_export.snapshot_envelope.model_dump(mode="json"),
        second_export.snapshot_envelope.model_dump(mode="json"),
    )

    assert first_export.snapshot_envelope.snapshot_id == second_export.snapshot_envelope.snapshot_id
    assert first_comparison.model_dump(mode="json") == second_comparison.model_dump(mode="json")
    assert json.dumps(first_comparison.model_dump(mode="json"), ensure_ascii=True) == json.dumps(
        second_comparison.model_dump(mode="json"),
        ensure_ascii=True,
    )
