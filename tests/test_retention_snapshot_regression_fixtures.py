import json
from copy import deepcopy

from app.services.offline_snapshot_comparison import compare_offline_snapshots
from app.services.snapshot_offline_io import export_inspection_snapshot, import_inspection_snapshot
from tests.fixtures.retention_snapshots import (
    false_fluency_retention_payload,
    fragile_retention_payload,
    legacy_without_aggregate_retention_payload,
    low_evidence_retention_payload,
    no_session_retention_payload,
    reconstruction_decay_payload,
    recovery_degraded_payload,
    resurfacing_degraded_payload,
    stable_retention_payload,
    transfer_decay_payload,
)


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


def test_all_retention_fixtures_are_deterministic_and_json_safe():
    payload_factories = [
        stable_retention_payload,
        fragile_retention_payload,
        false_fluency_retention_payload,
        low_evidence_retention_payload,
        reconstruction_decay_payload,
        transfer_decay_payload,
        resurfacing_degraded_payload,
        recovery_degraded_payload,
        no_session_retention_payload,
        legacy_without_aggregate_retention_payload,
    ]

    for factory in payload_factories:
        first = factory()
        second = factory()
        exported = export_inspection_snapshot(first)
        envelope = exported.snapshot_envelope.model_dump(mode="json")
        imported = import_inspection_snapshot(envelope)

        assert first == second
        json.dumps(first, ensure_ascii=True)
        json.dumps(envelope, ensure_ascii=True)
        json.dumps(imported.model_dump(mode="json"), ensure_ascii=True)
        if factory is legacy_without_aggregate_retention_payload:
            assert "aggregate_retention" not in first
            assert imported.imported_payload["aggregate_retention"]["aggregate_retention_state"]
        else:
            assert imported.imported_payload["aggregate_retention"]["aggregate_retention_state"]


def test_stable_fixture_round_trip_and_self_comparison_remain_stable():
    payload = stable_retention_payload()
    payload_before = deepcopy(payload)
    baseline = build_exported_snapshot(payload)
    candidate = build_exported_snapshot(stable_retention_payload())
    baseline_before = deepcopy(baseline)
    candidate_before = deepcopy(candidate)

    result = compare_offline_snapshots(baseline, candidate)

    assert payload == payload_before
    assert baseline == baseline_before
    assert candidate == candidate_before
    assert result.offline_comparison_state == "offline_comparison_stable"
    assert all(item.signal_state in {"not_detected", "unavailable"} for item in result.regression_signals)


def test_stable_to_fragile_detects_fragility_regression():
    result = compare_offline_snapshots(
        build_exported_snapshot(stable_retention_payload()),
        build_exported_snapshot(fragile_retention_payload()),
    )

    assert result.offline_comparison_state == "offline_regression_risk_detected"
    assert signal(result, "aggregate_retention_fragility_increased").signal_state == "detected"
    assert metric_delta(result, "aggregate_retention.fragile_ratio").delta_direction == "increased"
    assert metric_delta(result, "aggregate_retention.fragile_microtopics_count").delta_direction == "increased"
    assert state_delta(result, "aggregate_retention.aggregate_retention_state").delta_state == "changed"


def test_stable_to_false_fluency_detects_superficial_regression():
    result = compare_offline_snapshots(
        build_exported_snapshot(stable_retention_payload()),
        build_exported_snapshot(false_fluency_retention_payload()),
    )

    assert signal(result, "aggregate_false_fluency_increased").signal_state == "detected"
    assert signal(result, "aggregate_superficial_stability_increased").signal_state == "detected"
    assert metric_delta(result, "aggregate_retention.false_fluency_count").delta_direction == "increased"
    assert "aggregate_false_fluency_risk" in list_delta(
        result,
        "aggregate_retention.aggregate_retention_risk_flags",
    ).added_items


def test_stable_to_low_evidence_detects_coverage_degradation_with_bounded_severity():
    result = compare_offline_snapshots(
        build_exported_snapshot(stable_retention_payload()),
        build_exported_snapshot(low_evidence_retention_payload()),
    )

    assert signal(result, "aggregate_evidence_coverage_decreased").signal_state == "detected"
    assert metric_delta(result, "aggregate_retention.evidence_coverage_ratio").delta_direction == "decreased"
    assert state_delta(result, "aggregate_retention.aggregate_retention_state").delta_state == "changed"
    assert all(item.severity in {"none", "low", "medium", "high"} for item in result.regression_signals)


def test_stable_to_reconstruction_decay_detects_reconstruction_regression():
    result = compare_offline_snapshots(
        build_exported_snapshot(stable_retention_payload()),
        build_exported_snapshot(reconstruction_decay_payload()),
    )

    assert signal(result, "aggregate_reconstruction_fragility_increased").signal_state == "detected"
    assert state_delta(result, "aggregate_retention.aggregate_reconstruction_state").delta_state == "changed"


def test_stable_to_transfer_decay_detects_transfer_regression():
    result = compare_offline_snapshots(
        build_exported_snapshot(stable_retention_payload()),
        build_exported_snapshot(transfer_decay_payload()),
    )

    assert signal(result, "aggregate_transfer_fragility_increased").signal_state == "detected"
    assert state_delta(result, "aggregate_retention.aggregate_transfer_state").delta_state == "changed"


def test_stable_to_resurfacing_degraded_detects_resurfacing_regression():
    result = compare_offline_snapshots(
        build_exported_snapshot(stable_retention_payload()),
        build_exported_snapshot(resurfacing_degraded_payload()),
    )

    assert signal(result, "aggregate_resurfacing_degraded").signal_state == "detected"
    assert state_delta(result, "aggregate_retention.aggregate_resurfacing_state").delta_state == "changed"


def test_stable_to_recovery_degraded_detects_recovery_regression():
    result = compare_offline_snapshots(
        build_exported_snapshot(stable_retention_payload()),
        build_exported_snapshot(recovery_degraded_payload()),
    )

    assert signal(result, "aggregate_recovery_degraded").signal_state == "detected"
    assert state_delta(result, "aggregate_retention.aggregate_recovery_state").delta_state == "changed"


def test_no_session_fixture_exports_imports_and_compares_safely():
    payload = no_session_retention_payload()
    exported = build_exported_snapshot(payload)
    imported = import_inspection_snapshot(exported)
    result = compare_offline_snapshots(exported, build_exported_snapshot(no_session_retention_payload()))

    assert imported.import_state in {"import_valid", "import_valid_with_warnings"}
    assert result.offline_comparison_state in {"offline_comparison_stable", "offline_partial_comparison"}
    assert all(
        item.severity != "high"
        for item in result.regression_signals
        if item.signal_name.startswith("aggregate_") and item.signal_state == "detected"
    )
    json.dumps(result.model_dump(mode="json"), ensure_ascii=True)


def test_legacy_missing_aggregate_retention_compares_safely_in_both_directions():
    legacy = build_exported_snapshot(legacy_without_aggregate_retention_payload())
    stable = build_exported_snapshot(stable_retention_payload())
    legacy_before = deepcopy(legacy)
    stable_before = deepcopy(stable)

    legacy_to_stable = compare_offline_snapshots(legacy, stable)
    stable_to_legacy = compare_offline_snapshots(stable, legacy)

    assert legacy == legacy_before
    assert stable == stable_before
    assert legacy_to_stable.offline_comparison_state in {
        "offline_partial_comparison",
        "offline_comparison_changed",
        "offline_comparison_inconclusive",
    }
    assert stable_to_legacy.offline_comparison_state in {
        "offline_partial_comparison",
        "offline_comparison_changed",
        "offline_comparison_inconclusive",
    }
    assert all(
        item.severity != "high"
        for item in legacy_to_stable.regression_signals
        if item.signal_name.startswith("aggregate_")
    )
    assert all(
        item.severity != "high"
        for item in stable_to_legacy.regression_signals
        if item.signal_name.startswith("aggregate_")
    )


def test_fixture_pipeline_is_read_only_and_deterministic():
    baseline_payload = stable_retention_payload()
    candidate_payload = fragile_retention_payload()
    baseline_payload_before = deepcopy(baseline_payload)
    candidate_payload_before = deepcopy(candidate_payload)
    baseline = build_exported_snapshot(baseline_payload)
    candidate = build_exported_snapshot(candidate_payload)
    baseline_before = deepcopy(baseline)
    candidate_before = deepcopy(candidate)

    first = compare_offline_snapshots(baseline, candidate)
    second = compare_offline_snapshots(baseline, candidate)

    assert baseline_payload == baseline_payload_before
    assert candidate_payload == candidate_payload_before
    assert baseline == baseline_before
    assert candidate == candidate_before
    assert baseline["snapshot_id"] == build_exported_snapshot(stable_retention_payload())["snapshot_id"]
    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    json.dumps(first.model_dump(mode="json"), ensure_ascii=True)
