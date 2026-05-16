import json
from copy import deepcopy

from app.services.offline_snapshot_comparison import compare_offline_snapshots
from app.services.snapshot_offline_io import export_inspection_snapshot, import_inspection_snapshot


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
            "benchmark_passed_cases": ["baseline", "retrieval"],
            "benchmark_failed_cases": [],
            "benchmark_inconclusive_cases": [],
            "benchmark_regression_cases": [],
        },
        "benchmark_case_reports": [],
        "scientific_runtime_validation": {
            "scientific_validation_state": "validation_stable",
            "runtime_benchmark_state": "benchmark_stable",
            "regression_detection_state": "regression_stable",
            "sustainability_validation_state": "sustainability_improved",
            "cognitive_load_profile": "balanced",
            "retrieval_reliability_profile": "reliable",
            "scaffold_dependency_profile": "low",
            "compression_safety_profile": "safe",
            "stabilization_reliability_profile": "stable",
            "continuity_reliability_profile": "stable",
        },
        "comparative_session_analytics": {
            "comparative_session_state": "behavior_consistent",
            "retrieval_delta": 0.02,
            "scaffold_delta": 0.01,
            "compression_delta": 0.0,
            "continuity_delta": 0.01,
            "reconstruction_delta": 0.0,
            "pacing_delta": 0.01,
            "validation_delta": 0.01,
            "sustainability_delta": 0.02,
            "behavioral_drift_signal": 0.02,
            "pedagogical_regression_signal": "regression_stable",
        },
        "session_export_debug": {},
        "stability_metrics": {
            "session_stability_state": "stable",
            "retrieval_density_metric": 0.42,
            "scaffold_load_metric": 0.21,
            "continuity_smoothness_metric": 0.74,
            "reconstruction_pressure_metric": 0.18,
            "compression_safety_metric": 0.88,
            "pacing_stability_metric": 0.79,
            "cognitive_balance_metric": 0.72,
        },
        "validation_dataset_awareness": {
            "validation_dataset_state": "dataset_aligned",
            "pedagogical_scenario_family": "stable_baseline",
            "runtime_validation_context": "controlled",
            "comparative_validation_alignment": 0.76,
        },
        "controlled_tuning_registry": {
            "tuning_experiment_registry_state": "registry_ready",
            "total_experiments": 8,
        },
        "tuning_profile_benchmark_comparison": {
            "tuning_profile_comparison_state": "comparison_ready",
        },
        "manual_experiment_inspection": {
            "manual_experiment_inspection_state": "inspection_ready",
            "caution_flags": ["manual_review_required"],
            "promising_candidate_profiles": ["compression_conservative_profile"],
            "redundant_profiles": [],
            "tradeoff_sensitive_profiles": ["support_lightweight_profile"],
            "low_coverage_profiles": [],
            "not_ready_profiles": [],
        },
        "longitudinal_retention": {
            "longitudinal_retention_state": "retention_sustainable",
            "retention_durability_state": "durable",
            "resurfacing_effectiveness_state": "effective",
            "recovery_state": "recovery_improving",
            "reconstruction_retention_state": "reconstruction_durable",
            "transfer_retention_state": "transfer_durable",
            "false_fluency_retention_risk": 0.18,
            "retention_evidence_level": "moderate",
            "retention_confidence_indicator": 0.71,
        },
        "aggregate_retention": {
            "aggregate_retention_state": "aggregate_retention_mixed",
            "aggregate_retention_summary": "Aggregate retention is mixed across the observed population.",
            "durable_microtopics_count": 1,
            "fragile_microtopics_count": 1,
            "superficial_microtopics_count": 1,
            "insufficient_evidence_count": 0,
            "false_fluency_count": 1,
            "evidence_coverage_ratio": 0.75,
            "durable_ratio": 0.33,
            "fragile_ratio": 0.33,
            "superficial_ratio": 0.33,
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


def test_identical_exported_snapshots_are_stable_and_deterministic():
    baseline = build_exported_snapshot(build_payload())
    candidate = deepcopy(baseline)
    before_baseline = deepcopy(baseline)
    before_candidate = deepcopy(candidate)

    first = compare_offline_snapshots(baseline, candidate)
    second = compare_offline_snapshots(baseline, candidate)

    assert baseline == before_baseline
    assert candidate == before_candidate
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert first.offline_comparison_state == "offline_comparison_stable"
    assert first.comparison_confidence == 1.0


def test_changed_snapshots_produce_numeric_state_and_list_deltas():
    baseline_payload = build_payload()
    candidate_payload = build_payload()
    candidate_payload["benchmark_summary"]["pedagogical_benchmark_state"] = "benchmark_regression_detected"
    candidate_payload["scientific_runtime_validation"]["scientific_validation_state"] = "validation_watch"
    candidate_payload["longitudinal_retention"]["longitudinal_retention_state"] = "retention_fragile"
    candidate_payload["stability_metrics"]["retrieval_density_metric"] = 0.57
    candidate_payload["stability_metrics"]["scaffold_load_metric"] = 0.38
    candidate_payload["stability_metrics"]["compression_safety_metric"] = 0.54
    candidate_payload["stability_metrics"]["pacing_stability_metric"] = 0.52
    candidate_payload["validation_dataset_awareness"]["comparative_validation_alignment"] = 0.51
    candidate_payload["manual_experiment_inspection"]["caution_flags"] = [
        "manual_review_required",
        "compression_safety_risk",
    ]
    candidate_payload["benchmark_summary"]["benchmark_regression_cases"] = ["false_fluency_case"]

    result = compare_offline_snapshots(
        build_exported_snapshot(baseline_payload),
        build_exported_snapshot(candidate_payload),
    )

    assert result.offline_comparison_state == "offline_regression_risk_detected"
    assert metric_delta(result, "stability_metrics.retrieval_density_metric").delta_direction == "increased"
    assert metric_delta(result, "stability_metrics.scaffold_load_metric").delta_direction == "increased"
    assert metric_delta(result, "stability_metrics.compression_safety_metric").delta_direction == "decreased"
    assert metric_delta(result, "stability_metrics.pacing_stability_metric").delta_direction == "decreased"
    assert metric_delta(
        result,
        "validation_dataset_awareness.comparative_validation_alignment",
    ).delta_direction == "decreased"
    assert state_delta(result, "benchmark_summary.pedagogical_benchmark_state").delta_state == "changed"
    assert state_delta(
        result,
        "scientific_runtime_validation.scientific_validation_state",
    ).delta_state == "changed"
    assert state_delta(result, "longitudinal_retention.longitudinal_retention_state").delta_state == "changed"
    assert list_delta(result, "manual_experiment_inspection.caution_flags").added_items == [
        "compression_safety_risk"
    ]
    assert list_delta(result, "benchmark_summary.benchmark_regression_cases").added_items == [
        "false_fluency_case"
    ]


def test_regression_signals_are_detected_for_worsening_offline_snapshot():
    baseline_payload = build_payload()
    candidate_payload = build_payload()
    candidate_payload["benchmark_summary"]["benchmark_regression_severity"] = "high"
    candidate_payload["benchmark_summary"]["benchmark_regression_cases"] = [
        "false_fluency_case",
        "unsafe_compression_case",
    ]
    candidate_payload["stability_metrics"]["scaffold_load_metric"] = 0.41
    candidate_payload["stability_metrics"]["compression_safety_metric"] = 0.49
    candidate_payload["longitudinal_retention"]["false_fluency_retention_risk"] = 0.67
    candidate_payload["longitudinal_retention"]["longitudinal_retention_state"] = "retention_fragile"
    candidate_payload["inspection_available"] = False

    result = compare_offline_snapshots(
        build_exported_snapshot(baseline_payload),
        build_exported_snapshot(candidate_payload),
    )

    assert signal(result, "benchmark_regression_worsened").signal_state == "detected"
    assert signal(result, "scaffold_load_increased").signal_state == "detected"
    assert signal(result, "compression_safety_decreased").signal_state == "detected"
    assert signal(result, "false_fluency_risk_increased").signal_state == "detected"
    assert signal(result, "retention_fragility_increased").signal_state == "detected"
    assert signal(result, "inspection_availability_lost").signal_state == "detected"


def test_list_deltas_include_payload_key_changes():
    baseline = build_exported_snapshot(build_payload())
    candidate = deepcopy(baseline)
    candidate["payload_keys"] = sorted(set(candidate["payload_keys"]) | {"future_section"})

    result = compare_offline_snapshots(baseline, candidate)

    payload_delta = list_delta(result, "envelope.payload_keys")
    assert payload_delta.added_items == ["future_section"]
    assert "future_section" in result.added_payload_keys


def test_unsupported_schema_and_missing_snapshots_fall_back_safely():
    baseline = build_exported_snapshot(build_payload())
    unsupported = deepcopy(baseline)
    unsupported["schema_version"] = "inspection-snapshot-v2"

    missing_baseline = compare_offline_snapshots(None, baseline)
    missing_candidate = compare_offline_snapshots(baseline, None)
    schema_mismatch = compare_offline_snapshots(baseline, unsupported)

    assert missing_baseline.offline_comparison_state == "offline_missing_snapshot"
    assert missing_candidate.offline_comparison_state == "offline_missing_snapshot"
    assert schema_mismatch.offline_comparison_state == "offline_schema_mismatch"


def test_partial_and_no_session_snapshots_compare_without_crashing():
    baseline = build_exported_snapshot(
        {
            "inspection_available": False,
            "inspection_label": "Legacy snapshot",
            "session": {},
            "raw_runtime_block": {},
        }
    )
    candidate = build_exported_snapshot(build_payload())
    no_session = build_exported_snapshot(
        {
            "inspection_available": False,
            "inspection_label": "Internal Runtime Inspection Console — Read Only",
            "session": {"session_id": None},
            "raw_runtime_block": {},
        }
    )

    partial = compare_offline_snapshots(baseline, candidate)
    safe_no_session = compare_offline_snapshots(no_session, no_session)

    assert partial.offline_comparison_state == "offline_partial_comparison"
    assert partial.comparison_limitations
    assert safe_no_session.offline_comparison_state in {
        "offline_comparison_stable",
        "offline_partial_comparison",
    }


def test_round_trip_export_import_and_payload_comparison_are_json_safe():
    payload = build_payload()
    exported_baseline = export_inspection_snapshot(payload).snapshot_envelope.model_dump(mode="json")
    exported_candidate = export_inspection_snapshot(payload).snapshot_envelope.model_dump(mode="json")
    imported_baseline = import_inspection_snapshot(exported_baseline)
    imported_candidate = import_inspection_snapshot(exported_candidate)

    by_envelope = compare_offline_snapshots(exported_baseline, exported_candidate)
    by_payload = compare_offline_snapshots(
        imported_baseline.imported_payload,
        imported_candidate.imported_payload,
    )

    assert by_envelope.offline_comparison_state == "offline_comparison_stable"
    assert by_payload.offline_comparison_state == "offline_comparison_stable"
    json.dumps(by_envelope.model_dump(mode="json"), ensure_ascii=True)
    json.dumps(by_payload.model_dump(mode="json"), ensure_ascii=True)
