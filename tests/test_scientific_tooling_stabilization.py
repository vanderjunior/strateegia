import json
from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.comparative_session_analytics import compare_session_analytics
from app.services.controlled_tuning_experiments import (
    build_controlled_tuning_experiment_registry,
)
from app.services.empirical_validation_dataset import (
    evaluate_empirical_validation_dataset,
)
from app.services.aggregate_retention_observability import observe_aggregate_retention
from app.services.longitudinal_retention_observability import (
    observe_longitudinal_retention,
)
from app.services.manual_experiment_inspection import (
    build_manual_experiment_inspection,
)
from app.services.pedagogical_benchmark_runner import run_pedagogical_benchmark
from app.services.runtime_scenario_simulation import simulate_runtime_scenario
from app.services.scientific_runtime_validation import (
    resolve_scientific_runtime_validation,
)
from app.services.scientific_tooling_contracts import (
    json_safe_profile,
    scientific_payload_defaults,
)
from app.services.session_export_debug import build_session_export_snapshot
from app.services.tuning_profile_benchmark_comparison import (
    compare_tuning_profiles_against_benchmark,
)


def create_client(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), repository


def test_scientific_profiles_serialize_to_json_safe_payloads():
    registry = build_controlled_tuning_experiment_registry()
    comparison = compare_tuning_profiles_against_benchmark(registry=registry, benchmark_result=None)
    profiles = [
        build_session_export_snapshot([]),
        resolve_scientific_runtime_validation([]),
        compare_session_analytics(None, None),
        simulate_runtime_scenario(None),
        evaluate_empirical_validation_dataset(None),
        run_pedagogical_benchmark(runtime_source=None),
        registry,
        comparison,
        build_manual_experiment_inspection(registry=registry, comparison=comparison),
        observe_longitudinal_retention(progress=None, runtime_block={}),
        observe_aggregate_retention(progress=None, runtime_block={}),
    ]

    serialized = [json_safe_profile(profile) for profile in profiles]

    assert all(isinstance(payload, dict) for payload in serialized)
    json.dumps(serialized, ensure_ascii=True)


def test_json_safe_profile_handles_datetime_and_nested_models():
    payload = json_safe_profile(
        {
            "generated_at": datetime(2026, 5, 16, 12, 0, tzinfo=timezone.utc),
            "registry": build_controlled_tuning_experiment_registry(),
        }
    )

    assert payload["generated_at"].startswith("2026-05-16T12:00:00")
    assert payload["registry"]["tuning_experiment_registry_state"] == "registry_ready"


def test_scientific_payload_defaults_expose_stable_top_level_keys():
    payload = scientific_payload_defaults(
        controlled_tuning_registry=json_safe_profile(build_controlled_tuning_experiment_registry()),
        tuning_profile_benchmark_comparison=json_safe_profile(
            compare_tuning_profiles_against_benchmark(
                registry=build_controlled_tuning_experiment_registry(),
                benchmark_result=None,
            )
        ),
        manual_experiment_inspection=json_safe_profile(
            build_manual_experiment_inspection(
                registry=build_controlled_tuning_experiment_registry(),
                comparison=compare_tuning_profiles_against_benchmark(
                    registry=build_controlled_tuning_experiment_registry(),
                    benchmark_result=None,
                ),
            )
        ),
        longitudinal_retention=json_safe_profile(
            observe_longitudinal_retention(progress=None, runtime_block={})
        ),
        aggregate_retention=json_safe_profile(
            observe_aggregate_retention(progress=None, runtime_block={})
        ),
    )

    assert sorted(payload) == sorted(
        [
            "inspection_available",
            "inspection_label",
            "session",
            "benchmark_summary",
            "benchmark_case_reports",
            "scientific_runtime_validation",
            "comparative_session_analytics",
            "session_export_debug",
            "stability_metrics",
            "validation_dataset_awareness",
            "controlled_tuning_registry",
            "tuning_profile_benchmark_comparison",
            "manual_experiment_inspection",
            "longitudinal_retention",
            "aggregate_retention",
            "raw_runtime_block",
        ]
    )


def test_scientific_services_tolerate_missing_metadata():
    registry = build_controlled_tuning_experiment_registry(experiments=[])
    comparison = compare_tuning_profiles_against_benchmark(
        registry=registry,
        benchmark_result=None,
    )
    manual = build_manual_experiment_inspection(registry=registry, comparison=None)
    retention = observe_longitudinal_retention(progress=None, runtime_block={})
    scenario = simulate_runtime_scenario({})
    comparative = compare_session_analytics(None, None)
    export_snapshot = build_session_export_snapshot([])
    scientific = resolve_scientific_runtime_validation([])

    assert comparison.comparison_readiness == "comparison_registry_empty"
    assert manual.inspection_readiness == "inspection_no_profiles"
    assert retention.longitudinal_retention_state == "retention_insufficient_evidence"
    assert scenario.runtime_scenario_state == "scenario_inconclusive"
    assert comparative.comparative_session_state == "comparison_inconclusive"
    assert export_snapshot.session_export_state == "export_ready"
    assert scientific.scientific_validation_state == "validation_stable"


def test_inspection_endpoint_contract_is_stable_and_read_only(tmp_path, monkeypatch):
    client, repository = create_client(tmp_path)
    called = {"decision_engine": False}

    def forbidden_build_review_plan(*args, **kwargs):
        called["decision_engine"] = True
        raise AssertionError("Decision engine must not be called by inspection tooling.")

    monkeypatch.setattr(
        "app.api.routes.LearningDecisionEngine.build_review_plan",
        forbidden_build_review_plan,
    )

    before = repository.load_progress().model_dump(mode="json")
    response = client.get("/api/inspection/runtime")
    after = repository.load_progress().model_dump(mode="json")

    payload = response.json()

    assert response.status_code == 200
    assert called["decision_engine"] is False
    assert before == after
    assert payload["inspection_label"] == "Internal Runtime Inspection Console — Read Only"
    assert "manual_experiment_inspection" in payload
    assert "longitudinal_retention" in payload
    assert "controlled_tuning_registry" in payload
    assert "tuning_profile_benchmark_comparison" in payload


def test_inspection_page_remains_read_only_and_separate(tmp_path):
    client, _ = create_client(tmp_path)

    inspection = client.get("/inspection")
    study = client.get("/")

    assert inspection.status_code == 200
    assert study.status_code == 200
    assert "Internal Runtime Inspection Console" in inspection.text
    assert "apply button" not in inspection.text.lower()
    assert "run tuning" not in inspection.text.lower()
    assert "save profile" not in inspection.text.lower()
    assert "Internal Runtime Inspection Console" not in study.text
