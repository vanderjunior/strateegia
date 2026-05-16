from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from app.domain.models import (
    OfflineSnapshotComparisonInput,
    OfflineSnapshotComparisonResult,
    OfflineSnapshotComparisonSummary,
    OfflineSnapshotDeltaSummary,
    OfflineSnapshotMetricDelta,
    OfflineSnapshotRegressionSignal,
)
from app.services.scientific_tooling_contracts import ensure_reasoning_list, json_safe_profile, readonly_copy
from app.services.snapshot_offline_io import (
    EXPORT_KIND,
    REQUIRED_INSPECTION_PAYLOAD_KEYS,
    SCHEMA_VERSION,
    export_inspection_snapshot,
    import_inspection_snapshot,
)


@dataclass(frozen=True)
class _PreparedSnapshot:
    payload: dict[str, object]
    snapshot_id: str
    schema_version: str
    payload_keys: list[str]
    import_state: str
    warnings: list[str]
    errors: list[str]
    source_kind: str
    inspection_available: bool


NUMERIC_PATHS = [
    "benchmark_summary.benchmark_alignment_score",
    "benchmark_summary.benchmark_total_cases",
    "comparative_session_analytics.retrieval_delta",
    "comparative_session_analytics.scaffold_delta",
    "comparative_session_analytics.compression_delta",
    "comparative_session_analytics.continuity_delta",
    "comparative_session_analytics.reconstruction_delta",
    "comparative_session_analytics.pacing_delta",
    "comparative_session_analytics.validation_delta",
    "comparative_session_analytics.sustainability_delta",
    "comparative_session_analytics.behavioral_drift_signal",
    "stability_metrics.retrieval_density_metric",
    "stability_metrics.scaffold_load_metric",
    "stability_metrics.continuity_smoothness_metric",
    "stability_metrics.reconstruction_pressure_metric",
    "stability_metrics.compression_safety_metric",
    "stability_metrics.pacing_stability_metric",
    "stability_metrics.cognitive_balance_metric",
    "validation_dataset_awareness.comparative_validation_alignment",
    "controlled_tuning_registry.total_experiments",
    "longitudinal_retention.false_fluency_retention_risk",
    "longitudinal_retention.retention_confidence_indicator",
    "aggregate_retention.durable_microtopics_count",
    "aggregate_retention.fragile_microtopics_count",
    "aggregate_retention.superficial_microtopics_count",
    "aggregate_retention.insufficient_evidence_count",
    "aggregate_retention.false_fluency_count",
    "aggregate_retention.durable_ratio",
    "aggregate_retention.fragile_ratio",
    "aggregate_retention.superficial_ratio",
    "aggregate_retention.evidence_coverage_ratio",
]

STATE_PATHS = [
    "benchmark_summary.pedagogical_benchmark_state",
    "benchmark_summary.benchmark_readiness",
    "benchmark_summary.benchmark_regression_severity",
    "scientific_runtime_validation.scientific_validation_state",
    "scientific_runtime_validation.runtime_benchmark_state",
    "scientific_runtime_validation.regression_detection_state",
    "scientific_runtime_validation.sustainability_validation_state",
    "scientific_runtime_validation.cognitive_load_profile",
    "scientific_runtime_validation.retrieval_reliability_profile",
    "scientific_runtime_validation.scaffold_dependency_profile",
    "scientific_runtime_validation.compression_safety_profile",
    "scientific_runtime_validation.stabilization_reliability_profile",
    "scientific_runtime_validation.continuity_reliability_profile",
    "comparative_session_analytics.comparative_session_state",
    "comparative_session_analytics.pedagogical_regression_signal",
    "stability_metrics.session_stability_state",
    "validation_dataset_awareness.validation_dataset_state",
    "validation_dataset_awareness.pedagogical_scenario_family",
    "validation_dataset_awareness.runtime_validation_context",
    "controlled_tuning_registry.tuning_experiment_registry_state",
    "tuning_profile_benchmark_comparison.tuning_profile_comparison_state",
    "manual_experiment_inspection.manual_experiment_inspection_state",
    "longitudinal_retention.longitudinal_retention_state",
    "longitudinal_retention.retention_durability_state",
    "longitudinal_retention.resurfacing_effectiveness_state",
    "longitudinal_retention.recovery_state",
    "longitudinal_retention.reconstruction_retention_state",
    "longitudinal_retention.transfer_retention_state",
    "longitudinal_retention.retention_evidence_level",
    "aggregate_retention.aggregate_retention_state",
    "aggregate_retention.aggregate_resurfacing_state",
    "aggregate_retention.aggregate_recovery_state",
    "aggregate_retention.aggregate_reconstruction_state",
    "aggregate_retention.aggregate_transfer_state",
]

LIST_PATHS = [
    "benchmark_summary.benchmark_passed_cases",
    "benchmark_summary.benchmark_failed_cases",
    "benchmark_summary.benchmark_inconclusive_cases",
    "benchmark_summary.benchmark_regression_cases",
    "manual_experiment_inspection.caution_flags",
    "manual_experiment_inspection.promising_candidate_profiles",
    "manual_experiment_inspection.redundant_profiles",
    "manual_experiment_inspection.tradeoff_sensitive_profiles",
    "manual_experiment_inspection.low_coverage_profiles",
    "manual_experiment_inspection.not_ready_profiles",
    "aggregate_retention.aggregate_retention_risk_flags",
]


def compare_offline_snapshots(
    baseline_snapshot: dict[str, object] | object,
    candidate_snapshot: dict[str, object] | object,
) -> OfflineSnapshotComparisonResult:
    if baseline_snapshot is None or candidate_snapshot is None:
        return _result_for_missing_snapshot(baseline_snapshot, candidate_snapshot)

    baseline = _prepare_snapshot(baseline_snapshot)
    candidate = _prepare_snapshot(candidate_snapshot)

    if baseline is None or candidate is None:
        return _result_for_missing_snapshot(baseline_snapshot, candidate_snapshot)

    if baseline.import_state == "import_unsupported_schema" or candidate.import_state == "import_unsupported_schema":
        return _schema_mismatch_result(baseline, candidate)

    if baseline.import_state in {"import_invalid", "import_missing_payload"} or candidate.import_state in {
        "import_invalid",
        "import_missing_payload",
    }:
        return _inconclusive_result(baseline, candidate, "Snapshot import did not produce a comparable payload.")

    metric_deltas = [_numeric_delta(path, baseline.payload, candidate.payload) for path in NUMERIC_PATHS]
    state_deltas = [_state_delta(path, baseline.payload, candidate.payload) for path in STATE_PATHS]
    list_deltas = [_list_delta(path, baseline.payload, candidate.payload) for path in LIST_PATHS]
    payload_key_delta = _list_delta_from_lists(
        "envelope.payload_keys",
        baseline.payload_keys,
        candidate.payload_keys,
    )
    list_deltas.append(payload_key_delta)

    added_payload_keys = payload_key_delta.added_items
    removed_payload_keys = payload_key_delta.removed_items
    shared_payload_keys = payload_key_delta.shared_items

    regression_signals = _regression_signals(baseline, candidate)
    limitations = _comparison_limitations(baseline, candidate)
    changed_metrics = sum(1 for item in metric_deltas if item.delta_direction not in {"unchanged", "unavailable"})
    changed_states = sum(1 for item in state_deltas if item.delta_state == "changed")
    changed_lists = sum(1 for item in list_deltas if item.delta_state == "list_changed")
    detected_regressions = sum(1 for item in regression_signals if item.signal_state == "detected")
    confidence = _comparison_confidence(baseline, candidate, limitations)
    state = _comparison_state(
        baseline,
        candidate,
        limitations=limitations,
        changed_metrics=changed_metrics,
        changed_states=changed_states,
        changed_lists=changed_lists,
        detected_regressions=detected_regressions,
    )
    reasoning = _comparison_reasoning(
        state=state,
        changed_metrics=changed_metrics,
        changed_states=changed_states,
        changed_lists=changed_lists,
        detected_regressions=detected_regressions,
        limitations=limitations,
    )
    summary = _comparison_summary_text(state, detected_regressions, limitations)

    input_profile = OfflineSnapshotComparisonInput(
        baseline_snapshot_id=baseline.snapshot_id,
        candidate_snapshot_id=candidate.snapshot_id,
        baseline_schema_version=baseline.schema_version,
        candidate_schema_version=candidate.schema_version,
        baseline_import_state=baseline.import_state,
        candidate_import_state=candidate.import_state,
    )
    summary_profile = OfflineSnapshotComparisonSummary(
        total_metric_deltas=len(metric_deltas),
        total_state_changes=changed_states,
        total_list_changes=changed_lists,
        total_regression_signals=detected_regressions,
        comparison_confidence=confidence,
        comparison_limitations=limitations,
    )
    return OfflineSnapshotComparisonResult(
        offline_comparison_state=state,
        offline_comparison_summary=summary,
        offline_comparison_reasoning=reasoning,
        comparison_input=input_profile,
        comparison_summary=summary_profile,
        baseline_snapshot_id=baseline.snapshot_id,
        candidate_snapshot_id=candidate.snapshot_id,
        baseline_schema_version=baseline.schema_version,
        candidate_schema_version=candidate.schema_version,
        metric_deltas=metric_deltas,
        state_deltas=state_deltas,
        list_deltas=list_deltas,
        regression_signals=regression_signals,
        added_payload_keys=added_payload_keys,
        removed_payload_keys=removed_payload_keys,
        shared_payload_keys=shared_payload_keys,
        comparison_confidence=confidence,
        comparison_limitations=limitations,
        why_this_offline_comparison_state=reasoning[0] if reasoning else "",
    )


def _prepare_snapshot(snapshot: object) -> _PreparedSnapshot | None:
    if snapshot is None:
        return None
    if hasattr(snapshot, "model_dump"):
        snapshot = snapshot.model_dump(mode="json")
    normalized = json_safe_profile(readonly_copy(snapshot), default={})
    if not isinstance(normalized, dict):
        return _PreparedSnapshot(
            payload={},
            snapshot_id="",
            schema_version="",
            payload_keys=[],
            import_state="import_invalid",
            warnings=[],
            errors=["Snapshot input must be a JSON object."],
            source_kind="invalid",
            inspection_available=False,
        )

    if "imported_payload" in normalized and "import_state" in normalized:
        payload = normalized.get("imported_payload", {})
        metadata = normalized.get("snapshot_metadata", {})
        return _PreparedSnapshot(
            payload=json_safe_profile(payload, default={}),
            snapshot_id=str(metadata.get("snapshot_id", "") or ""),
            schema_version=str(metadata.get("schema_version", SCHEMA_VERSION) or SCHEMA_VERSION),
            payload_keys=sorted(json_safe_profile(payload, default={}).keys()),
            import_state=str(normalized.get("import_state", "") or "import_invalid"),
            warnings=[str(item) for item in normalized.get("warnings", [])],
            errors=[str(item) for item in normalized.get("errors", [])],
            source_kind="import_result",
            inspection_available=bool(payload.get("inspection_available")),
        )

    if "schema_version" in normalized or "snapshot_payload" in normalized or "export_kind" in normalized:
        imported = import_inspection_snapshot(normalized)
        payload = imported.imported_payload
        return _PreparedSnapshot(
            payload=json_safe_profile(payload, default={}),
            snapshot_id=imported.snapshot_metadata.snapshot_id,
            schema_version=imported.snapshot_metadata.schema_version,
            payload_keys=imported.snapshot_metadata.payload_keys,
            import_state=imported.import_state,
            warnings=imported.warnings,
            errors=imported.errors,
            source_kind="snapshot_envelope",
            inspection_available=bool(payload.get("inspection_available")),
        )

    exported = export_inspection_snapshot(normalized)
    imported = import_inspection_snapshot(exported.snapshot_envelope.model_dump(mode="json"))
    return _PreparedSnapshot(
        payload=json_safe_profile(imported.imported_payload, default={}),
        snapshot_id=exported.snapshot_metadata.snapshot_id,
        schema_version=exported.snapshot_metadata.schema_version,
        payload_keys=exported.snapshot_metadata.payload_keys,
        import_state=imported.import_state,
        warnings=imported.warnings,
        errors=imported.errors,
        source_kind="inspection_payload",
        inspection_available=bool(imported.imported_payload.get("inspection_available")),
    )


def _numeric_delta(path: str, baseline_payload: dict[str, object], candidate_payload: dict[str, object]) -> OfflineSnapshotMetricDelta:
    baseline_value = _coerce_float(_path_value(baseline_payload, path))
    candidate_value = _coerce_float(_path_value(candidate_payload, path))
    if baseline_value is None or candidate_value is None:
        return OfflineSnapshotMetricDelta(
            path=path,
            baseline_value=baseline_value,
            candidate_value=candidate_value,
            delta=None,
            delta_direction="unavailable",
            interpretation=f"{path} is unavailable for offline comparison.",
        )
    delta = round(candidate_value - baseline_value, 4)
    if abs(delta) < 0.0001:
        direction = "unchanged"
    elif delta > 0:
        direction = "increased"
    else:
        direction = "decreased"
    return OfflineSnapshotMetricDelta(
        path=path,
        baseline_value=baseline_value,
        candidate_value=candidate_value,
        delta=delta,
        delta_direction=direction,
        interpretation=f"{path} {direction}." if direction != "unchanged" else f"{path} remained unchanged.",
    )


def _state_delta(path: str, baseline_payload: dict[str, object], candidate_payload: dict[str, object]) -> OfflineSnapshotDeltaSummary:
    baseline_value = _path_value(baseline_payload, path)
    candidate_value = _path_value(candidate_payload, path)
    if baseline_value in (None, "") and candidate_value in (None, ""):
        state = "unavailable"
    elif baseline_value in (None, ""):
        state = "missing_baseline"
    elif candidate_value in (None, ""):
        state = "missing_candidate"
    elif baseline_value == candidate_value:
        state = "unchanged"
    else:
        state = "changed"
    return OfflineSnapshotDeltaSummary(
        path=path,
        baseline_value=baseline_value,
        candidate_value=candidate_value,
        delta_state=state,
        interpretation=f"{path} {state.replace('_', ' ')}.",
    )


def _list_delta(path: str, baseline_payload: dict[str, object], candidate_payload: dict[str, object]) -> OfflineSnapshotDeltaSummary:
    return _list_delta_from_lists(
        path,
        _coerce_list(_path_value(baseline_payload, path)),
        _coerce_list(_path_value(candidate_payload, path)),
    )


def _list_delta_from_lists(path: str, baseline_items: list[object], candidate_items: list[object]) -> OfflineSnapshotDeltaSummary:
    baseline_values = sorted({str(item) for item in baseline_items})
    candidate_values = sorted({str(item) for item in candidate_items})
    shared = sorted(set(baseline_values).intersection(candidate_values))
    added = sorted(set(candidate_values).difference(baseline_values))
    removed = sorted(set(baseline_values).difference(candidate_values))
    if not baseline_values and not candidate_values:
        state = "unavailable"
    elif added or removed:
        state = "list_changed"
    else:
        state = "unchanged"
    return OfflineSnapshotDeltaSummary(
        path=path,
        baseline_value=baseline_values,
        candidate_value=candidate_values,
        delta_state=state,
        added_items=added,
        removed_items=removed,
        shared_items=shared,
        interpretation=f"{path} {state.replace('_', ' ')}.",
    )


def _regression_signals(baseline: _PreparedSnapshot, candidate: _PreparedSnapshot) -> list[OfflineSnapshotRegressionSignal]:
    signals = [
        _signal_from_condition(
            "benchmark_regression_worsened",
            _severity_rank(_path_value(candidate.payload, "benchmark_summary.benchmark_regression_severity"))
            > _severity_rank(_path_value(baseline.payload, "benchmark_summary.benchmark_regression_severity"))
            or len(_coerce_list(_path_value(candidate.payload, "benchmark_summary.benchmark_regression_cases")))
            > len(_coerce_list(_path_value(baseline.payload, "benchmark_summary.benchmark_regression_cases"))),
            "high",
            "Benchmark regression severity or regression case count increased.",
        ),
        _signal_from_metric_path(
            baseline.payload,
            candidate.payload,
            "validation_dataset_awareness.comparative_validation_alignment",
            expected_direction="decreased",
            signal_name="validation_confidence_decreased",
            severity="medium",
            reason="Comparative validation alignment decreased.",
        ),
        _signal_from_metric_path(
            baseline.payload,
            candidate.payload,
            "stability_metrics.scaffold_load_metric",
            expected_direction="increased",
            signal_name="scaffold_load_increased",
            severity="medium",
            reason="Scaffold load metric increased.",
        ),
        _signal_from_metric_path(
            baseline.payload,
            candidate.payload,
            "stability_metrics.retrieval_density_metric",
            expected_direction="increased",
            signal_name="retrieval_inflation_increased",
            severity="low",
            reason="Retrieval density metric increased.",
        ),
        _signal_from_metric_path(
            baseline.payload,
            candidate.payload,
            "stability_metrics.compression_safety_metric",
            expected_direction="decreased",
            signal_name="compression_safety_decreased",
            severity="high",
            reason="Compression safety metric decreased.",
        ),
        _signal_from_metric_path(
            baseline.payload,
            candidate.payload,
            "stability_metrics.continuity_smoothness_metric",
            expected_direction="decreased",
            signal_name="continuity_degraded",
            severity="medium",
            reason="Continuity smoothness decreased.",
        ),
        _signal_from_metric_path(
            baseline.payload,
            candidate.payload,
            "stability_metrics.reconstruction_pressure_metric",
            expected_direction="increased",
            signal_name="reconstruction_pressure_increased",
            severity="medium",
            reason="Reconstruction pressure increased.",
        ),
        _signal_from_metric_path(
            baseline.payload,
            candidate.payload,
            "stability_metrics.pacing_stability_metric",
            expected_direction="decreased",
            signal_name="pacing_stability_decreased",
            severity="medium",
            reason="Pacing stability decreased.",
        ),
        _signal_from_condition(
            "retention_fragility_increased",
            _path_value(candidate.payload, "longitudinal_retention.longitudinal_retention_state")
            in {"retention_fragile", "retention_superficial"}
            and _path_value(baseline.payload, "longitudinal_retention.longitudinal_retention_state")
            not in {"retention_fragile", "retention_superficial"},
            "high",
            "Longitudinal retention shifted toward a more fragile state.",
        ),
        _signal_from_metric_path(
            baseline.payload,
            candidate.payload,
            "longitudinal_retention.false_fluency_retention_risk",
            expected_direction="increased",
            signal_name="false_fluency_risk_increased",
            severity="high",
            reason="False fluency retention risk increased.",
        ),
        _signal_from_condition(
            "manual_caution_flags_increased",
            len(_coerce_list(_path_value(candidate.payload, "manual_experiment_inspection.caution_flags")))
            > len(_coerce_list(_path_value(baseline.payload, "manual_experiment_inspection.caution_flags"))),
            "low",
            "Manual experiment caution flags increased.",
        ),
        _signal_from_condition(
            "benchmark_case_failures_increased",
            len(_coerce_list(_path_value(candidate.payload, "benchmark_summary.benchmark_failed_cases")))
            > len(_coerce_list(_path_value(baseline.payload, "benchmark_summary.benchmark_failed_cases"))),
            "medium",
            "Benchmark failed cases increased.",
        ),
        _signal_from_condition(
            "inspection_availability_lost",
            bool(_path_value(baseline.payload, "inspection_available"))
            and not bool(_path_value(candidate.payload, "inspection_available")),
            "high",
            "Inspection availability was lost in the candidate snapshot.",
        ),
        _signal_from_condition(
            "schema_mismatch",
            baseline.schema_version != candidate.schema_version
            or baseline.schema_version != SCHEMA_VERSION
            or candidate.schema_version != SCHEMA_VERSION,
            "high",
            "Snapshot schema versions do not match the supported contract.",
        ),
        _signal_from_condition(
            "aggregate_retention_fragility_increased",
            _path_value(candidate.payload, "aggregate_retention.aggregate_retention_state")
            in {"aggregate_retention_fragile", "aggregate_retention_superficial"}
            and _path_value(baseline.payload, "aggregate_retention.aggregate_retention_state")
            not in {"aggregate_retention_fragile", "aggregate_retention_superficial"},
            "high",
            "Aggregate retention shifted toward a more fragile or superficial state.",
        ),
        _signal_from_metric_path(
            baseline.payload,
            candidate.payload,
            "aggregate_retention.false_fluency_count",
            expected_direction="increased",
            signal_name="aggregate_false_fluency_increased",
            severity="high",
            reason="Aggregate false fluency count increased.",
        ),
        _signal_from_metric_path(
            baseline.payload,
            candidate.payload,
            "aggregate_retention.superficial_ratio",
            expected_direction="increased",
            signal_name="aggregate_superficial_stability_increased",
            severity="medium",
            reason="Aggregate superficial stability ratio increased.",
        ),
        _signal_from_metric_path(
            baseline.payload,
            candidate.payload,
            "aggregate_retention.evidence_coverage_ratio",
            expected_direction="decreased",
            signal_name="aggregate_evidence_coverage_decreased",
            severity="medium",
            reason="Aggregate evidence coverage ratio decreased.",
        ),
        _signal_from_condition(
            "aggregate_reconstruction_fragility_increased",
            _path_value(candidate.payload, "aggregate_retention.aggregate_reconstruction_state")
            == "aggregate_reconstruction_fragile"
            and _path_value(baseline.payload, "aggregate_retention.aggregate_reconstruction_state")
            != "aggregate_reconstruction_fragile",
            "high",
            "Aggregate reconstruction retention degraded into a fragile state.",
        ),
        _signal_from_condition(
            "aggregate_transfer_fragility_increased",
            _path_value(candidate.payload, "aggregate_retention.aggregate_transfer_state")
            == "aggregate_transfer_fragile"
            and _path_value(baseline.payload, "aggregate_retention.aggregate_transfer_state")
            != "aggregate_transfer_fragile",
            "high",
            "Aggregate transfer retention degraded into a fragile state.",
        ),
        _signal_from_condition(
            "aggregate_resurfacing_degraded",
            _path_value(candidate.payload, "aggregate_retention.aggregate_resurfacing_state")
            == "aggregate_resurfacing_fragile"
            and _path_value(baseline.payload, "aggregate_retention.aggregate_resurfacing_state")
            != "aggregate_resurfacing_fragile",
            "medium",
            "Aggregate resurfacing effectiveness degraded.",
        ),
        _signal_from_condition(
            "aggregate_recovery_degraded",
            _path_value(candidate.payload, "aggregate_retention.aggregate_recovery_state")
            == "aggregate_recovery_unstable"
            and _path_value(baseline.payload, "aggregate_retention.aggregate_recovery_state")
            != "aggregate_recovery_unstable",
            "medium",
            "Aggregate recovery after error degraded.",
        ),
        _signal_from_condition(
            "aggregate_topic_risk_concentration_increased",
            "aggregate_topic_risk_concentration"
            in _coerce_list(_path_value(candidate.payload, "aggregate_retention.aggregate_retention_risk_flags"))
            and "aggregate_topic_risk_concentration"
            not in _coerce_list(_path_value(baseline.payload, "aggregate_retention.aggregate_retention_risk_flags")),
            "medium",
            "Aggregate topic risk concentration increased.",
        ),
    ]
    return signals


def _signal_from_metric_path(
    baseline_payload: dict[str, object],
    candidate_payload: dict[str, object],
    path: str,
    *,
    expected_direction: str,
    signal_name: str,
    severity: str,
    reason: str,
) -> OfflineSnapshotRegressionSignal:
    baseline_value = _coerce_float(_path_value(baseline_payload, path))
    candidate_value = _coerce_float(_path_value(candidate_payload, path))
    if baseline_value is None or candidate_value is None:
        return OfflineSnapshotRegressionSignal(
            signal_name=signal_name,
            signal_state="unavailable",
            severity="none",
            reasoning=[f"{path} is unavailable for regression comparison."],
        )
    delta = round(candidate_value - baseline_value, 4)
    detected = delta > 0 if expected_direction == "increased" else delta < 0
    return _signal_from_condition(signal_name, detected, severity, reason)


def _signal_from_condition(signal_name: str, detected: bool, severity: str, reason: str) -> OfflineSnapshotRegressionSignal:
    return OfflineSnapshotRegressionSignal(
        signal_name=signal_name,
        signal_state="detected" if detected else "not_detected",
        severity=severity if detected else "none",
        reasoning=[reason] if detected else [f"{signal_name} was not detected."],
    )


def _comparison_limitations(baseline: _PreparedSnapshot, candidate: _PreparedSnapshot) -> list[str]:
    limitations: list[str] = []
    limitations.extend(ensure_reasoning_list(baseline.warnings))
    limitations.extend(ensure_reasoning_list(candidate.warnings))
    limitations.extend(ensure_reasoning_list(baseline.errors))
    limitations.extend(ensure_reasoning_list(candidate.errors))
    if baseline.import_state.endswith("with_warnings") or candidate.import_state.endswith("with_warnings"):
        limitations.append("One or both snapshots were imported with warnings.")
    if set(baseline.payload_keys) != REQUIRED_INSPECTION_PAYLOAD_KEYS or set(candidate.payload_keys) != REQUIRED_INSPECTION_PAYLOAD_KEYS:
        limitations.append("One or both snapshots have partial payload coverage.")
    return sorted(dict.fromkeys(limitations))


def _comparison_confidence(baseline: _PreparedSnapshot, candidate: _PreparedSnapshot, limitations: list[str]) -> float:
    if baseline.import_state == "import_valid" and candidate.import_state == "import_valid" and not limitations:
        return 1.0
    if baseline.import_state.startswith("import_valid") and candidate.import_state.startswith("import_valid"):
        return 0.7
    return 0.4


def _comparison_state(
    baseline: _PreparedSnapshot,
    candidate: _PreparedSnapshot,
    *,
    limitations: list[str],
    changed_metrics: int,
    changed_states: int,
    changed_lists: int,
    detected_regressions: int,
) -> str:
    if baseline.schema_version != candidate.schema_version:
        return "offline_schema_mismatch"
    if baseline.import_state in {"import_invalid", "import_missing_payload"} or candidate.import_state in {
        "import_invalid",
        "import_missing_payload",
    }:
        return "offline_comparison_inconclusive"
    if limitations:
        return "offline_partial_comparison"
    if detected_regressions:
        return "offline_regression_risk_detected"
    if changed_metrics or changed_states or changed_lists:
        return "offline_comparison_changed"
    return "offline_comparison_stable"


def _comparison_reasoning(
    *,
    state: str,
    changed_metrics: int,
    changed_states: int,
    changed_lists: int,
    detected_regressions: int,
    limitations: list[str],
) -> list[str]:
    reasoning = [
        f"Offline comparison finished with state {state}.",
        f"Metric deltas changed: {changed_metrics}.",
        f"State deltas changed: {changed_states}.",
        f"List deltas changed: {changed_lists}.",
        f"Regression signals detected: {detected_regressions}.",
    ]
    reasoning.extend(ensure_reasoning_list(limitations))
    return reasoning


def _comparison_summary_text(state: str, detected_regressions: int, limitations: list[str]) -> str:
    if state == "offline_regression_risk_detected":
        return f"Offline regression risk detected: {detected_regressions} regression signals were raised."
    if state == "offline_partial_comparison":
        return "Offline comparison completed with partial snapshot coverage."
    if state == "offline_comparison_changed":
        return "Offline comparison detected deterministic changes across exported snapshots."
    if state == "offline_comparison_stable":
        return "Offline comparison remained stable across exported snapshots."
    if state == "offline_schema_mismatch":
        return "Offline comparison could not proceed because snapshot schemas did not match."
    if state == "offline_missing_snapshot":
        return "Offline comparison could not proceed because one snapshot was missing."
    if limitations:
        return "Offline comparison is inconclusive because snapshot validity is limited."
    return "Offline comparison is inconclusive."


def _result_for_missing_snapshot(baseline_snapshot: object, candidate_snapshot: object) -> OfflineSnapshotComparisonResult:
    limitations = []
    if baseline_snapshot is None:
        limitations.append("Baseline snapshot is missing.")
    if candidate_snapshot is None:
        limitations.append("Candidate snapshot is missing.")
    summary_profile = OfflineSnapshotComparisonSummary(
        comparison_confidence=0.0,
        comparison_limitations=limitations,
    )
    return OfflineSnapshotComparisonResult(
        offline_comparison_state="offline_missing_snapshot",
        offline_comparison_summary="Offline comparison could not proceed because one snapshot was missing.",
        offline_comparison_reasoning=limitations,
        comparison_summary=summary_profile,
        comparison_confidence=0.0,
        comparison_limitations=limitations,
        why_this_offline_comparison_state=limitations[0] if limitations else "",
    )


def _schema_mismatch_result(baseline: _PreparedSnapshot, candidate: _PreparedSnapshot) -> OfflineSnapshotComparisonResult:
    limitations = ["At least one snapshot uses an unsupported schema version."]
    summary_profile = OfflineSnapshotComparisonSummary(
        comparison_confidence=0.0,
        comparison_limitations=limitations,
    )
    return OfflineSnapshotComparisonResult(
        offline_comparison_state="offline_schema_mismatch",
        offline_comparison_summary="Offline comparison could not proceed because snapshot schemas did not match.",
        offline_comparison_reasoning=limitations,
        comparison_input=OfflineSnapshotComparisonInput(
            baseline_snapshot_id=baseline.snapshot_id,
            candidate_snapshot_id=candidate.snapshot_id,
            baseline_schema_version=baseline.schema_version,
            candidate_schema_version=candidate.schema_version,
            baseline_import_state=baseline.import_state,
            candidate_import_state=candidate.import_state,
        ),
        comparison_summary=summary_profile,
        baseline_snapshot_id=baseline.snapshot_id,
        candidate_snapshot_id=candidate.snapshot_id,
        baseline_schema_version=baseline.schema_version,
        candidate_schema_version=candidate.schema_version,
        comparison_confidence=0.0,
        comparison_limitations=limitations,
        why_this_offline_comparison_state=limitations[0],
    )


def _inconclusive_result(baseline: _PreparedSnapshot, candidate: _PreparedSnapshot, reason: str) -> OfflineSnapshotComparisonResult:
    limitations = [reason]
    summary_profile = OfflineSnapshotComparisonSummary(
        comparison_confidence=0.0,
        comparison_limitations=limitations,
    )
    return OfflineSnapshotComparisonResult(
        offline_comparison_state="offline_comparison_inconclusive",
        offline_comparison_summary="Offline comparison is inconclusive.",
        offline_comparison_reasoning=limitations,
        comparison_input=OfflineSnapshotComparisonInput(
            baseline_snapshot_id=baseline.snapshot_id,
            candidate_snapshot_id=candidate.snapshot_id,
            baseline_schema_version=baseline.schema_version,
            candidate_schema_version=candidate.schema_version,
            baseline_import_state=baseline.import_state,
            candidate_import_state=candidate.import_state,
        ),
        comparison_summary=summary_profile,
        baseline_snapshot_id=baseline.snapshot_id,
        candidate_snapshot_id=candidate.snapshot_id,
        baseline_schema_version=baseline.schema_version,
        candidate_schema_version=candidate.schema_version,
        comparison_confidence=0.0,
        comparison_limitations=limitations,
        why_this_offline_comparison_state=reason,
    )


def _path_value(payload: dict[str, object], path: str) -> object:
    current: object = payload
    for segment in path.split("."):
        if not isinstance(current, dict) or segment not in current:
            return None
        current = current.get(segment)
    return current


def _coerce_float(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return round(float(value), 4)
    except (TypeError, ValueError):
        return None


def _coerce_list(value: object) -> list[object]:
    if isinstance(value, list):
        return list(value)
    if isinstance(value, tuple):
        return list(value)
    return []


def _severity_rank(value: object) -> int:
    ranks = {"none": 0, "low": 1, "medium": 2, "high": 3}
    return ranks.get(str(value or "none"), 0)
