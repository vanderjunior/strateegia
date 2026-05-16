import json
from copy import deepcopy
from datetime import datetime, timedelta, timezone

from fastapi.testclient import TestClient

from app.domain.models import BoardStyle, Document, GeneratedQuestion, Topic
from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.offline_snapshot_comparison import compare_offline_snapshots
from app.services.snapshot_offline_io import export_inspection_snapshot, import_inspection_snapshot


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


def build_payload() -> dict[str, object]:
    return {
        "inspection_available": True,
        "inspection_label": "Internal Runtime Inspection Console — Read Only",
        "session": {"session_id": "session-1"},
        "benchmark_summary": {
            "pedagogical_benchmark_state": "benchmark_stable",
            "benchmark_readiness": "benchmark_ready",
            "benchmark_alignment_score": 0.82,
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
        "stability_metrics": {},
        "validation_dataset_awareness": {},
        "controlled_tuning_registry": {},
        "tuning_profile_benchmark_comparison": {},
        "manual_experiment_inspection": {},
        "longitudinal_retention": {},
        "aggregate_retention": {
            "aggregate_retention_state": "aggregate_retention_mixed",
            "aggregate_resurfacing_state": "aggregate_resurfacing_mixed",
            "aggregate_recovery_state": "aggregate_recovery_mixed",
            "aggregate_reconstruction_state": "aggregate_reconstruction_mixed",
            "aggregate_transfer_state": "aggregate_transfer_mixed",
            "durable_microtopics_count": 3,
            "fragile_microtopics_count": 1,
            "superficial_microtopics_count": 1,
            "insufficient_evidence_count": 0,
            "false_fluency_count": 1,
            "evidence_coverage_ratio": 0.8,
            "durable_ratio": 0.6,
            "fragile_ratio": 0.2,
            "superficial_ratio": 0.2,
            "aggregate_retention_risk_flags": [
                "aggregate_false_fluency_risk",
                "aggregate_topic_risk_concentration",
            ],
            "topic_retention_risk_summary": [
                {
                    "topic_id": "topic-a",
                    "observed_microtopics": 3,
                    "durable_count": 2,
                    "fragile_count": 1,
                    "superficial_count": 0,
                    "insufficient_evidence_count": 0,
                    "false_fluency_count": 0,
                    "risk_flags": ["topic_fragility_present"],
                    "topic_retention_state": "topic_retention_mixed",
                    "topic_retention_reasoning": [],
                }
            ],
        },
        "raw_runtime_block": {},
    }


def build_exported_snapshot(payload: dict[str, object]) -> dict[str, object]:
    return export_inspection_snapshot(payload).snapshot_envelope.model_dump(mode="json")


def metric_delta(result, path: str):
    return next(item for item in result.metric_deltas if item.path == path)


def state_delta(result, path: str):
    return next(item for item in result.state_deltas if item.path == path)


def list_delta(result, path: str):
    return next(item for item in result.list_deltas if item.path == path)


def signal(result, name: str):
    return next(item for item in result.regression_signals if item.signal_name == name)


def test_inspection_payload_includes_aggregate_retention_and_remains_json_safe(tmp_path):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 16, 18, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Cartas Nauticas",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )

    no_session = client.get("/api/inspection/runtime").json()
    start_basic_session(client)
    session_payload = client.get("/api/inspection/runtime").json()

    assert "aggregate_retention" in no_session
    assert no_session["aggregate_retention"]["aggregate_retention_state"]
    assert "aggregate_retention" in session_payload
    assert session_payload["aggregate_retention"]["aggregate_retention_state"]
    json.dumps(no_session, ensure_ascii=True)
    json.dumps(session_payload, ensure_ascii=True)


def test_export_import_preserve_aggregate_retention_and_legacy_snapshot_is_safe():
    payload = build_payload()
    payload_before = deepcopy(payload)
    exported = export_inspection_snapshot(payload)
    envelope = exported.snapshot_envelope.model_dump(mode="json")
    envelope_before = deepcopy(envelope)
    imported = import_inspection_snapshot(envelope)

    legacy_envelope = export_inspection_snapshot(
        {
            "inspection_available": False,
            "inspection_label": "Legacy snapshot",
            "session": {},
            "raw_runtime_block": {},
        }
    ).snapshot_envelope.model_dump(mode="json")
    imported_legacy = import_inspection_snapshot(legacy_envelope)

    assert payload == payload_before
    assert envelope == envelope_before
    assert imported.imported_payload["aggregate_retention"]["aggregate_retention_state"] == "aggregate_retention_mixed"
    assert imported_legacy.import_state == "import_valid_with_warnings"
    assert imported_legacy.imported_payload["aggregate_retention"]["aggregate_retention_state"]
    json.dumps(envelope, ensure_ascii=True)
    json.dumps(imported.imported_payload, ensure_ascii=True)


def test_offline_comparison_detects_aggregate_retention_metric_state_and_list_deltas():
    baseline = build_payload()
    candidate = build_payload()
    candidate["aggregate_retention"]["aggregate_retention_state"] = "aggregate_retention_fragile"
    candidate["aggregate_retention"]["aggregate_resurfacing_state"] = "aggregate_resurfacing_fragile"
    candidate["aggregate_retention"]["aggregate_recovery_state"] = "aggregate_recovery_unstable"
    candidate["aggregate_retention"]["aggregate_reconstruction_state"] = "aggregate_reconstruction_fragile"
    candidate["aggregate_retention"]["aggregate_transfer_state"] = "aggregate_transfer_fragile"
    candidate["aggregate_retention"]["durable_ratio"] = 0.3
    candidate["aggregate_retention"]["fragile_ratio"] = 0.5
    candidate["aggregate_retention"]["superficial_ratio"] = 0.3
    candidate["aggregate_retention"]["evidence_coverage_ratio"] = 0.45
    candidate["aggregate_retention"]["false_fluency_count"] = 3
    candidate["aggregate_retention"]["fragile_microtopics_count"] = 3
    candidate["aggregate_retention"]["durable_microtopics_count"] = 1
    candidate["aggregate_retention"]["aggregate_retention_risk_flags"] = [
        "aggregate_false_fluency_risk",
        "aggregate_topic_risk_concentration",
        "aggregate_reconstruction_decay_risk",
    ]
    candidate["aggregate_retention"]["topic_retention_risk_summary"] = [
        {
            "topic_id": "topic-a",
            "observed_microtopics": 3,
            "durable_count": 1,
            "fragile_count": 2,
            "superficial_count": 0,
            "insufficient_evidence_count": 0,
            "false_fluency_count": 1,
            "risk_flags": ["topic_fragility_present", "topic_false_fluency_present"],
            "topic_retention_state": "topic_retention_fragile",
            "topic_retention_reasoning": [],
        }
    ]

    result = compare_offline_snapshots(build_exported_snapshot(baseline), build_exported_snapshot(candidate))

    assert metric_delta(result, "aggregate_retention.durable_ratio").delta_direction == "decreased"
    assert metric_delta(result, "aggregate_retention.fragile_ratio").delta_direction == "increased"
    assert metric_delta(result, "aggregate_retention.superficial_ratio").delta_direction == "increased"
    assert metric_delta(result, "aggregate_retention.evidence_coverage_ratio").delta_direction == "decreased"
    assert metric_delta(result, "aggregate_retention.false_fluency_count").delta_direction == "increased"
    assert metric_delta(result, "aggregate_retention.fragile_microtopics_count").delta_direction == "increased"
    assert state_delta(result, "aggregate_retention.aggregate_retention_state").delta_state == "changed"
    assert state_delta(result, "aggregate_retention.aggregate_resurfacing_state").delta_state == "changed"
    assert state_delta(result, "aggregate_retention.aggregate_recovery_state").delta_state == "changed"
    assert state_delta(result, "aggregate_retention.aggregate_reconstruction_state").delta_state == "changed"
    assert state_delta(result, "aggregate_retention.aggregate_transfer_state").delta_state == "changed"
    assert list_delta(result, "aggregate_retention.aggregate_retention_risk_flags").added_items == [
        "aggregate_reconstruction_decay_risk"
    ]


def test_offline_comparison_detects_aggregate_retention_regression_signals():
    baseline = build_payload()
    candidate = build_payload()
    baseline["aggregate_retention"]["aggregate_retention_risk_flags"] = [
        "aggregate_false_fluency_risk",
    ]
    candidate["aggregate_retention"]["aggregate_retention_state"] = "aggregate_retention_fragile"
    candidate["aggregate_retention"]["durable_ratio"] = 0.2
    candidate["aggregate_retention"]["fragile_ratio"] = 0.6
    candidate["aggregate_retention"]["superficial_ratio"] = 0.4
    candidate["aggregate_retention"]["evidence_coverage_ratio"] = 0.35
    candidate["aggregate_retention"]["false_fluency_count"] = 4
    candidate["aggregate_retention"]["fragile_microtopics_count"] = 4
    candidate["aggregate_retention"]["aggregate_reconstruction_state"] = "aggregate_reconstruction_fragile"
    candidate["aggregate_retention"]["aggregate_transfer_state"] = "aggregate_transfer_fragile"
    candidate["aggregate_retention"]["aggregate_resurfacing_state"] = "aggregate_resurfacing_fragile"
    candidate["aggregate_retention"]["aggregate_recovery_state"] = "aggregate_recovery_unstable"
    candidate["aggregate_retention"]["aggregate_retention_risk_flags"] = [
        "aggregate_false_fluency_risk",
        "aggregate_topic_risk_concentration",
        "aggregate_resurfacing_failure_risk",
        "aggregate_transfer_decay_risk",
    ]

    result = compare_offline_snapshots(build_exported_snapshot(baseline), build_exported_snapshot(candidate))

    assert signal(result, "aggregate_retention_fragility_increased").signal_state == "detected"
    assert signal(result, "aggregate_false_fluency_increased").signal_state == "detected"
    assert signal(result, "aggregate_evidence_coverage_decreased").signal_state == "detected"
    assert signal(result, "aggregate_reconstruction_fragility_increased").signal_state == "detected"
    assert signal(result, "aggregate_transfer_fragility_increased").signal_state == "detected"
    assert signal(result, "aggregate_resurfacing_degraded").signal_state == "detected"
    assert signal(result, "aggregate_recovery_degraded").signal_state == "detected"
    assert signal(result, "aggregate_topic_risk_concentration_increased").signal_state == "detected"


def test_missing_aggregate_retention_alone_does_not_create_severe_regression_and_comparison_is_json_safe():
    baseline = build_exported_snapshot(build_payload())
    candidate = build_exported_snapshot(
        {
            "inspection_available": True,
            "inspection_label": "Internal Runtime Inspection Console — Read Only",
            "session": {"session_id": "session-1"},
            "benchmark_summary": {"pedagogical_benchmark_state": "benchmark_stable"},
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
    )

    baseline_before = deepcopy(baseline)
    candidate_before = deepcopy(candidate)
    result = compare_offline_snapshots(baseline, candidate)

    assert baseline == baseline_before
    assert candidate == candidate_before
    assert result.offline_comparison_state == "offline_partial_comparison"
    assert all(item.severity != "high" for item in result.regression_signals if item.signal_name.startswith("aggregate_"))
    json.dumps(result.model_dump(mode="json"), ensure_ascii=True)


def test_http_paths_remain_read_only_when_aggregate_retention_is_present(tmp_path, monkeypatch):
    client, repository = create_client(tmp_path)
    now = datetime(2026, 5, 16, 19, 0, tzinfo=timezone.utc)
    repository.save_document(
        build_document(
            title="Sinais Sonoros",
            topic_id="topic-1",
            question_id="q-1",
            created_at=now - timedelta(days=1),
        )
    )
    started = start_basic_session(client)
    calls = {"record_feedback": 0, "review_plan": 0}

    def forbidden_record_feedback(*args, **kwargs):
        calls["record_feedback"] += 1
        raise AssertionError("Inspection/export must not submit answers.")

    def forbidden_build_review_plan(*args, **kwargs):
        calls["review_plan"] += 1
        raise AssertionError("Inspection/export must not create review plans.")

    monkeypatch.setattr("app.api.routes._record_feedback_answer", forbidden_record_feedback)
    monkeypatch.setattr(
        "app.api.routes.LearningDecisionEngine.build_review_plan",
        forbidden_build_review_plan,
    )

    progress_before = repository.load_progress().model_dump(mode="json")
    current_before = client.get(f"/api/session/{started['session_id']}/current").json()
    inspection = client.get("/api/inspection/runtime")
    exported = client.get("/api/inspection/runtime/export")
    progress_after = repository.load_progress().model_dump(mode="json")
    current_after = client.get(f"/api/session/{started['session_id']}/current").json()

    assert inspection.status_code == 200
    assert exported.status_code == 200
    assert "aggregate_retention" in inspection.json()
    assert "aggregate_retention" in exported.json()["snapshot_payload"]
    assert calls == {"record_feedback": 0, "review_plan": 0}
    assert progress_before == progress_after
    assert current_before == current_after
