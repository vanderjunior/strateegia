import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.domain.models import BoardStyle, Document, GeneratedQuestion, Topic
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.snapshot_offline_io import (
    EXPORT_KIND,
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


def build_minimal_payload() -> dict[str, object]:
    return {
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


def test_export_produces_stable_json_safe_envelope_without_mutating_input():
    payload = build_minimal_payload()
    before = deepcopy(payload)

    first = export_inspection_snapshot(payload)
    second = export_inspection_snapshot(payload)

    assert payload == before
    assert first.export_state == "export_ready"
    assert first.snapshot_envelope.schema_version == SCHEMA_VERSION
    assert first.snapshot_envelope.export_kind == EXPORT_KIND
    assert first.snapshot_envelope.source == "internal_inspection_console"
    assert first.snapshot_envelope.snapshot_payload["inspection_label"] == payload["inspection_label"]
    assert set(first.snapshot_envelope.payload_keys) == REQUIRED_INSPECTION_PAYLOAD_KEYS
    assert first.snapshot_envelope.snapshot_id == second.snapshot_envelope.snapshot_id
    json.dumps(first.snapshot_envelope.model_dump(mode="json"), ensure_ascii=True)


def test_valid_exported_snapshot_imports_successfully_without_mutating_input():
    payload = build_minimal_payload()
    exported = export_inspection_snapshot(payload)
    envelope = exported.snapshot_envelope.model_dump(mode="json")
    before = deepcopy(envelope)

    result = import_inspection_snapshot(envelope)

    assert envelope == before
    assert result.import_state == "import_valid"
    assert set(result.imported_payload) == REQUIRED_INSPECTION_PAYLOAD_KEYS
    assert result.imported_payload["inspection_label"] == payload["inspection_label"]
    json.dumps(result.imported_payload, ensure_ascii=True)


def test_validate_partial_snapshot_reports_missing_required_keys_with_warnings():
    exported = export_inspection_snapshot(
        {
            "inspection_available": False,
            "inspection_label": "Internal Runtime Inspection Console — Read Only",
            "session": {"session_id": None},
        }
    )

    validation = validate_offline_snapshot(exported.snapshot_envelope.model_dump(mode="json"))

    assert validation.validation_state == "snapshot_valid_with_warnings"
    assert validation.is_valid is True
    assert "benchmark_summary" in validation.missing_required_keys
    assert validation.warnings
    assert validation.validation_reasoning


def test_validation_rejects_unsupported_schema_and_malformed_snapshots():
    unsupported = validate_offline_snapshot(
        {
            "schema_version": "inspection-snapshot-v999",
            "export_kind": EXPORT_KIND,
            "snapshot_payload": build_minimal_payload(),
        }
    )
    malformed = validate_offline_snapshot(["not", "a", "snapshot"])

    assert unsupported.validation_state == "snapshot_unsupported_schema"
    assert unsupported.is_valid is False
    assert malformed.validation_state == "snapshot_invalid"
    assert malformed.errors


def test_import_handles_missing_payload_and_unsupported_schema_safely():
    missing_payload = import_inspection_snapshot(
        {
            "schema_version": SCHEMA_VERSION,
            "export_kind": EXPORT_KIND,
        }
    )
    unsupported = import_inspection_snapshot(
        {
            "schema_version": "inspection-snapshot-v2",
            "export_kind": EXPORT_KIND,
            "snapshot_payload": build_minimal_payload(),
        }
    )

    assert missing_payload.import_state == "import_missing_payload"
    assert missing_payload.imported_payload == {}
    assert unsupported.import_state == "import_unsupported_schema"
    assert unsupported.imported_payload == {}


def test_round_trip_preserves_semantic_structure_for_full_payload():
    payload = build_minimal_payload()
    payload["benchmark_summary"] = {
        "pedagogical_benchmark_state": "benchmark_stable",
        "benchmark_total_cases": 10,
    }
    payload["scientific_runtime_validation"] = {
        "scientific_validation_state": "validation_stable",
    }

    exported = export_inspection_snapshot(payload)
    imported = import_inspection_snapshot(exported.snapshot_envelope.model_dump(mode="json"))

    assert imported.import_state == "import_valid"
    assert imported.imported_payload == exported.snapshot_envelope.snapshot_payload
    json.dumps(exported.snapshot_envelope.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(imported.imported_payload, ensure_ascii=True)


def test_no_session_payload_exports_safely_and_partial_legacy_payload_warns(tmp_path):
    client, _ = create_client(tmp_path)
    response = client.get("/api/inspection/runtime")

    exported = export_inspection_snapshot(response.json())
    legacy = import_inspection_snapshot(
        export_inspection_snapshot(
            {
                "inspection_available": False,
                "inspection_label": "Legacy snapshot",
                "session": {},
                "raw_runtime_block": {},
            }
        ).snapshot_envelope.model_dump(mode="json")
    )

    assert response.status_code == 200
    assert exported.export_state == "export_ready"
    assert exported.snapshot_envelope.validation_state in {
        "snapshot_valid",
        "snapshot_valid_with_warnings",
    }
    assert legacy.import_state == "import_valid_with_warnings"
    assert "benchmark_summary" in legacy.validation.missing_required_keys


def test_export_endpoint_returns_json_envelope_without_runtime_mutation(tmp_path, monkeypatch):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 16, 18, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Sinalizacao Nautica",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )
    started = start_basic_session(client)
    calls = {"record_feedback": 0, "review_plan": 0}

    def forbidden_record_feedback(*args, **kwargs):
        calls["record_feedback"] += 1
        raise AssertionError("Snapshot export must not submit answers.")

    def forbidden_build_review_plan(*args, **kwargs):
        calls["review_plan"] += 1
        raise AssertionError("Snapshot export must not create review plans.")

    monkeypatch.setattr("app.api.routes._record_feedback_answer", forbidden_record_feedback)
    monkeypatch.setattr(
        "app.api.routes.LearningDecisionEngine.build_review_plan",
        forbidden_build_review_plan,
    )

    progress_before = repository.load_progress().model_dump(mode="json")
    current_before = client.get(f"/api/session/{started['session_id']}/current").json()

    response = client.get("/api/inspection/runtime/export")
    payload = response.json()

    progress_after = repository.load_progress().model_dump(mode="json")
    current_after = client.get(f"/api/session/{started['session_id']}/current").json()

    assert response.status_code == 200
    assert payload["schema_version"] == SCHEMA_VERSION
    assert payload["export_kind"] == EXPORT_KIND
    assert payload["snapshot_payload"]["inspection_available"] is True
    assert calls == {"record_feedback": 0, "review_plan": 0}
    assert progress_before == progress_after
    assert current_before == current_after
    json.dumps(payload, ensure_ascii=True)
