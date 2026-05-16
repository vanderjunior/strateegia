from __future__ import annotations

from copy import deepcopy


def _base_payload() -> dict[str, object]:
    return {
        "inspection_available": True,
        "inspection_label": "Internal Runtime Inspection Console — Read Only",
        "session": {"session_id": "session-retention"},
        "benchmark_summary": {
            "pedagogical_benchmark_state": "benchmark_stable",
            "benchmark_readiness": "benchmark_ready",
            "benchmark_alignment_score": 0.82,
            "benchmark_regression_severity": "none",
            "benchmark_total_cases": 8,
            "benchmark_passed_cases": ["baseline_case"],
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
            "aggregate_retention_state": "aggregate_retention_sustainable",
            "aggregate_retention_summary": "Aggregate retention appears sustainable.",
            "aggregate_retention_reasoning": ["Observed retention patterns remain durable."],
            "retention_population_summary": {},
            "topic_retention_risk_summary": [
                {
                    "topic_id": "topic-stable",
                    "observed_microtopics": 4,
                    "durable_count": 3,
                    "fragile_count": 0,
                    "superficial_count": 0,
                    "insufficient_evidence_count": 1,
                    "false_fluency_count": 0,
                    "risk_flags": [],
                    "topic_retention_state": "topic_retention_stable",
                    "topic_retention_reasoning": [],
                }
            ],
            "aggregate_retention_risk_profile": {},
            "aggregate_retention_evidence_summary": {
                "aggregate_retention_evidence_state": "evidence_sufficient",
                "aggregate_retention_evidence_reasoning": ["Coverage is sufficient for aggregate interpretation."],
                "evidence_coverage_ratio": 0.92,
            },
            "aggregate_resurfacing_state": "aggregate_resurfacing_effective",
            "aggregate_recovery_state": "aggregate_recovery_improving",
            "aggregate_reconstruction_state": "aggregate_reconstruction_durable",
            "aggregate_transfer_state": "aggregate_transfer_durable",
            "aggregate_retention_metrics": [],
            "aggregate_retention_risk_flags": [],
            "durable_microtopics_count": 6,
            "fragile_microtopics_count": 1,
            "superficial_microtopics_count": 0,
            "insufficient_evidence_count": 1,
            "false_fluency_count": 0,
            "evidence_coverage_ratio": 0.92,
            "durable_ratio": 0.75,
            "fragile_ratio": 0.12,
            "superficial_ratio": 0.0,
            "why_this_aggregate_retention_state": "Most observed microtopics remain durable with strong evidence coverage.",
        },
        "raw_runtime_block": {},
    }


def stable_retention_payload() -> dict[str, object]:
    return deepcopy(_base_payload())


def fragile_retention_payload() -> dict[str, object]:
    payload = stable_retention_payload()
    aggregate = payload["aggregate_retention"]
    aggregate["aggregate_retention_state"] = "aggregate_retention_fragile"
    aggregate["aggregate_retention_summary"] = "Aggregate retention appears fragile."
    aggregate["aggregate_retention_risk_flags"] = [
        "aggregate_resurfacing_failure_risk",
        "aggregate_topic_risk_concentration",
    ]
    aggregate["durable_microtopics_count"] = 2
    aggregate["fragile_microtopics_count"] = 4
    aggregate["superficial_microtopics_count"] = 1
    aggregate["false_fluency_count"] = 1
    aggregate["durable_ratio"] = 0.25
    aggregate["fragile_ratio"] = 0.5
    aggregate["superficial_ratio"] = 0.12
    aggregate["evidence_coverage_ratio"] = 0.78
    aggregate["topic_retention_risk_summary"] = [
        {
            "topic_id": "topic-fragile",
            "observed_microtopics": 4,
            "durable_count": 1,
            "fragile_count": 3,
            "superficial_count": 0,
            "insufficient_evidence_count": 0,
            "false_fluency_count": 0,
            "risk_flags": ["topic_fragility_present"],
            "topic_retention_state": "topic_retention_fragile",
            "topic_retention_reasoning": [],
        }
    ]
    return payload


def false_fluency_retention_payload() -> dict[str, object]:
    payload = stable_retention_payload()
    aggregate = payload["aggregate_retention"]
    aggregate["aggregate_retention_state"] = "aggregate_retention_superficial"
    aggregate["aggregate_retention_summary"] = "Aggregate retention appears superficially stable with false fluency risk."
    aggregate["aggregate_retention_risk_flags"] = [
        "aggregate_false_fluency_risk",
        "aggregate_superficial_stabilization_risk",
    ]
    aggregate["false_fluency_count"] = 3
    aggregate["superficial_microtopics_count"] = 3
    aggregate["superficial_ratio"] = 0.38
    aggregate["durable_ratio"] = 0.42
    aggregate["fragile_ratio"] = 0.12
    aggregate["evidence_coverage_ratio"] = 0.81
    return payload


def low_evidence_retention_payload() -> dict[str, object]:
    payload = stable_retention_payload()
    aggregate = payload["aggregate_retention"]
    aggregate["aggregate_retention_state"] = "aggregate_retention_insufficient_evidence"
    aggregate["aggregate_retention_summary"] = "Aggregate retention has insufficient longitudinal evidence."
    aggregate["aggregate_retention_risk_flags"] = ["aggregate_insufficient_longitudinal_evidence"]
    aggregate["insufficient_evidence_count"] = 5
    aggregate["durable_microtopics_count"] = 1
    aggregate["fragile_microtopics_count"] = 0
    aggregate["superficial_microtopics_count"] = 0
    aggregate["false_fluency_count"] = 0
    aggregate["durable_ratio"] = 0.12
    aggregate["fragile_ratio"] = 0.0
    aggregate["superficial_ratio"] = 0.0
    aggregate["evidence_coverage_ratio"] = 0.22
    return payload


def reconstruction_decay_payload() -> dict[str, object]:
    payload = fragile_retention_payload()
    aggregate = payload["aggregate_retention"]
    aggregate["aggregate_reconstruction_state"] = "aggregate_reconstruction_fragile"
    aggregate["aggregate_retention_risk_flags"] = sorted(
        set(aggregate["aggregate_retention_risk_flags"]) | {"aggregate_reconstruction_decay_risk"}
    )
    return payload


def transfer_decay_payload() -> dict[str, object]:
    payload = fragile_retention_payload()
    aggregate = payload["aggregate_retention"]
    aggregate["aggregate_transfer_state"] = "aggregate_transfer_fragile"
    aggregate["aggregate_retention_risk_flags"] = sorted(
        set(aggregate["aggregate_retention_risk_flags"]) | {"aggregate_transfer_decay_risk"}
    )
    return payload


def resurfacing_degraded_payload() -> dict[str, object]:
    payload = fragile_retention_payload()
    aggregate = payload["aggregate_retention"]
    aggregate["aggregate_resurfacing_state"] = "aggregate_resurfacing_fragile"
    aggregate["aggregate_retention_risk_flags"] = sorted(
        set(aggregate["aggregate_retention_risk_flags"]) | {"aggregate_resurfacing_failure_risk"}
    )
    return payload


def recovery_degraded_payload() -> dict[str, object]:
    payload = fragile_retention_payload()
    aggregate = payload["aggregate_retention"]
    aggregate["aggregate_recovery_state"] = "aggregate_recovery_unstable"
    aggregate["aggregate_retention_risk_flags"] = sorted(
        set(aggregate["aggregate_retention_risk_flags"]) | {"aggregate_unstable_recovery_risk"}
    )
    return payload


def no_session_retention_payload() -> dict[str, object]:
    payload = stable_retention_payload()
    payload["inspection_available"] = False
    payload["session"] = {"session_id": None}
    payload["aggregate_retention"] = {
        "aggregate_retention_state": "aggregate_retention_insufficient_evidence",
        "aggregate_retention_summary": "No session data is available for aggregate retention.",
        "aggregate_retention_reasoning": [],
        "retention_population_summary": {},
        "topic_retention_risk_summary": [],
        "aggregate_retention_risk_profile": {},
        "aggregate_retention_evidence_summary": {
            "aggregate_retention_evidence_state": "evidence_insufficient",
            "aggregate_retention_evidence_reasoning": [],
            "evidence_coverage_ratio": 0.0,
        },
        "aggregate_resurfacing_state": "aggregate_resurfacing_insufficient_evidence",
        "aggregate_recovery_state": "aggregate_recovery_insufficient_evidence",
        "aggregate_reconstruction_state": "aggregate_reconstruction_insufficient_evidence",
        "aggregate_transfer_state": "aggregate_transfer_insufficient_evidence",
        "aggregate_retention_metrics": [],
        "aggregate_retention_risk_flags": ["aggregate_insufficient_longitudinal_evidence"],
        "durable_microtopics_count": 0,
        "fragile_microtopics_count": 0,
        "superficial_microtopics_count": 0,
        "insufficient_evidence_count": 0,
        "false_fluency_count": 0,
        "evidence_coverage_ratio": 0.0,
        "durable_ratio": 0.0,
        "fragile_ratio": 0.0,
        "superficial_ratio": 0.0,
        "why_this_aggregate_retention_state": "No aggregate retention evidence is available without an active session.",
    }
    return payload


def legacy_without_aggregate_retention_payload() -> dict[str, object]:
    payload = stable_retention_payload()
    payload.pop("aggregate_retention", None)
    payload["inspection_label"] = "Legacy inspection snapshot"
    return payload
