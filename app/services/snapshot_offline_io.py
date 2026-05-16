from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from typing import Any

from app.domain.models import (
    OfflineSnapshotEnvelope,
    OfflineSnapshotExportResult,
    OfflineSnapshotImportResult,
    OfflineSnapshotMetadata,
    OfflineSnapshotValidationResult,
)
from app.services.scientific_tooling_contracts import (
    ensure_reasoning_list,
    json_safe_profile,
    readonly_copy,
    scientific_payload_defaults,
)


SCHEMA_VERSION = "inspection-snapshot-v1"
EXPORT_KIND = "inspection_runtime_snapshot"
DEFAULT_SOURCE = "internal_inspection_console"
REQUIRED_INSPECTION_PAYLOAD_KEYS = {
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
}


def export_inspection_snapshot(
    payload: dict[str, object],
    *,
    source: str = DEFAULT_SOURCE,
) -> OfflineSnapshotExportResult:
    normalized_input = _normalize_payload_input(payload)
    payload_keys = sorted(normalized_input.keys())
    snapshot_payload = _build_snapshot_payload(normalized_input)
    snapshot_id = _snapshot_id_for_payload(snapshot_payload)
    exported_at = datetime.now(timezone.utc).isoformat()

    envelope = OfflineSnapshotEnvelope(
        schema_version=SCHEMA_VERSION,
        export_kind=EXPORT_KIND,
        exported_at=exported_at,
        source=source,
        inspection_available=bool(snapshot_payload.get("inspection_available")),
        snapshot_id=snapshot_id,
        snapshot_payload=snapshot_payload,
        payload_keys=payload_keys,
        validation_state="snapshot_invalid",
        export_reasoning=[],
    )
    validation = validate_offline_snapshot(envelope.model_dump(mode="json"))
    reasoning = _build_export_reasoning(validation, source=source, snapshot_id=snapshot_id)
    envelope.validation_state = validation.validation_state
    envelope.export_reasoning = reasoning
    metadata = OfflineSnapshotMetadata(
        schema_version=envelope.schema_version,
        export_kind=envelope.export_kind,
        exported_at=envelope.exported_at,
        source=envelope.source,
        inspection_available=envelope.inspection_available,
        snapshot_id=envelope.snapshot_id,
        payload_keys=envelope.payload_keys,
    )
    return OfflineSnapshotExportResult(
        export_state=_export_state_from_validation(validation),
        snapshot_envelope=envelope,
        snapshot_metadata=metadata,
        validation=validation,
        warnings=validation.warnings,
        errors=validation.errors,
        export_reasoning=reasoning,
    )


def import_inspection_snapshot(snapshot_data: dict[str, object]) -> OfflineSnapshotImportResult:
    raw_snapshot = readonly_copy(snapshot_data)
    validation = validate_offline_snapshot(raw_snapshot)
    normalized_snapshot = json_safe_profile(raw_snapshot, default={})
    metadata = _snapshot_metadata_from_data(normalized_snapshot if isinstance(normalized_snapshot, dict) else {})
    if validation.validation_state == "snapshot_unsupported_schema":
        return OfflineSnapshotImportResult(
            import_state="import_unsupported_schema",
            imported_payload={},
            snapshot_metadata=metadata,
            validation=validation,
            warnings=validation.warnings,
            errors=validation.errors,
            import_reasoning=_build_import_reasoning("import_unsupported_schema", validation),
        )
    if validation.validation_state == "snapshot_missing_payload":
        return OfflineSnapshotImportResult(
            import_state="import_missing_payload",
            imported_payload={},
            snapshot_metadata=metadata,
            validation=validation,
            warnings=validation.warnings,
            errors=validation.errors,
            import_reasoning=_build_import_reasoning("import_missing_payload", validation),
        )
    if validation.validation_state == "snapshot_invalid":
        return OfflineSnapshotImportResult(
            import_state="import_invalid",
            imported_payload={},
            snapshot_metadata=metadata,
            validation=validation,
            warnings=validation.warnings,
            errors=validation.errors,
            import_reasoning=_build_import_reasoning("import_invalid", validation),
        )

    snapshot_payload = normalized_snapshot.get("snapshot_payload", {})
    imported_payload = _build_snapshot_payload(snapshot_payload)
    state = "import_valid_with_warnings" if validation.warnings else "import_valid"
    return OfflineSnapshotImportResult(
        import_state=state,
        imported_payload=imported_payload,
        snapshot_metadata=metadata,
        validation=validation,
        warnings=validation.warnings,
        errors=validation.errors,
        import_reasoning=_build_import_reasoning(state, validation),
    )


def validate_offline_snapshot(snapshot_data: dict[str, object]) -> OfflineSnapshotValidationResult:
    raw_snapshot = readonly_copy(snapshot_data)
    if not isinstance(raw_snapshot, dict):
        return OfflineSnapshotValidationResult(
            validation_state="snapshot_invalid",
            schema_version="",
            warnings=[],
            errors=["Snapshot envelope must be a JSON object."],
            is_valid=False,
            validation_reasoning=["Snapshot envelope is malformed."],
        )

    normalized_snapshot = json_safe_profile(raw_snapshot, default={})
    if not isinstance(normalized_snapshot, dict):
        return OfflineSnapshotValidationResult(
            validation_state="snapshot_invalid",
            schema_version="",
            warnings=[],
            errors=["Snapshot envelope could not be normalized."],
            is_valid=False,
            validation_reasoning=["Snapshot envelope normalization failed."],
        )

    schema_version = str(normalized_snapshot.get("schema_version", "") or "")
    export_kind = str(normalized_snapshot.get("export_kind", "") or "")
    snapshot_payload = normalized_snapshot.get("snapshot_payload")
    payload_keys = normalized_snapshot.get("payload_keys")

    if schema_version and schema_version != SCHEMA_VERSION:
        return OfflineSnapshotValidationResult(
            validation_state="snapshot_unsupported_schema",
            schema_version=schema_version,
            warnings=[],
            errors=[f"Unsupported schema_version: {schema_version}."],
            is_valid=False,
            validation_reasoning=["Snapshot schema is not supported by this importer."],
        )
    if export_kind and export_kind != EXPORT_KIND:
        return OfflineSnapshotValidationResult(
            validation_state="snapshot_invalid",
            schema_version=schema_version,
            warnings=[],
            errors=[f"Unexpected export_kind: {export_kind}."],
            is_valid=False,
            validation_reasoning=["Snapshot export kind does not match the inspection snapshot contract."],
        )
    if "snapshot_payload" not in normalized_snapshot:
        return OfflineSnapshotValidationResult(
            validation_state="snapshot_missing_payload",
            schema_version=schema_version or SCHEMA_VERSION,
            warnings=[],
            errors=["snapshot_payload is required."],
            is_valid=False,
            validation_reasoning=["Snapshot payload is missing from the envelope."],
        )
    if not isinstance(snapshot_payload, dict):
        return OfflineSnapshotValidationResult(
            validation_state="snapshot_invalid",
            schema_version=schema_version or SCHEMA_VERSION,
            warnings=[],
            errors=["snapshot_payload must be a JSON object."],
            is_valid=False,
            validation_reasoning=["Snapshot payload is malformed."],
        )

    present_keys = _present_keys(payload_keys, snapshot_payload)
    missing_required_keys = sorted(REQUIRED_INSPECTION_PAYLOAD_KEYS.difference(present_keys))
    warnings: list[str] = []
    reasoning = ["Snapshot payload is JSON-safe and schema-compatible."]
    if missing_required_keys:
        warnings.append(
            "Snapshot payload is missing required inspection sections: "
            + ", ".join(missing_required_keys)
            + "."
        )
        reasoning.append("Missing required keys were tolerated with safe defaults.")

    state = "snapshot_valid_with_warnings" if warnings else "snapshot_valid"
    return OfflineSnapshotValidationResult(
        validation_state=state,
        schema_version=schema_version or SCHEMA_VERSION,
        missing_required_keys=missing_required_keys,
        present_keys=present_keys,
        warnings=warnings,
        errors=[],
        is_valid=True,
        validation_reasoning=reasoning,
    )


def _normalize_payload_input(payload: object) -> dict[str, object]:
    if not isinstance(payload, dict):
        return {}
    normalized = json_safe_profile(readonly_copy(payload), default={})
    if isinstance(normalized, dict):
        return normalized
    return {}


def _build_snapshot_payload(payload: object) -> dict[str, object]:
    normalized = _normalize_payload_input(payload)
    base_payload = scientific_payload_defaults(
        controlled_tuning_registry={},
        tuning_profile_benchmark_comparison={},
        manual_experiment_inspection={},
        longitudinal_retention={},
        aggregate_retention=_default_aggregate_retention_payload(),
    )
    merged_payload = dict(base_payload)
    merged_payload.update(normalized)
    return json_safe_profile(merged_payload, default={})


def _default_aggregate_retention_payload() -> dict[str, object]:
    return {
        "aggregate_retention_state": "aggregate_retention_insufficient_evidence",
        "aggregate_retention_summary": "Aggregate retention has insufficient evidence for a reliable summary.",
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
        "total_microtopics_observed": 0,
        "durable_microtopics_count": 0,
        "fragile_microtopics_count": 0,
        "superficial_microtopics_count": 0,
        "insufficient_evidence_count": 0,
        "false_fluency_count": 0,
        "evidence_coverage_ratio": 0.0,
        "durable_ratio": 0.0,
        "fragile_ratio": 0.0,
        "superficial_ratio": 0.0,
        "why_this_aggregate_retention_state": "Aggregate retention evidence is insufficient to support a stronger conclusion.",
    }


def _snapshot_id_for_payload(payload: dict[str, object]) -> str:
    canonical_payload = json.dumps(
        json_safe_profile(payload, default={}),
        ensure_ascii=True,
        sort_keys=True,
        separators=(",", ":"),
    )
    return hashlib.sha256(canonical_payload.encode("utf-8")).hexdigest()


def _present_keys(payload_keys: object, snapshot_payload: dict[str, object]) -> list[str]:
    if isinstance(payload_keys, list):
        return sorted({str(item) for item in payload_keys})
    return sorted(snapshot_payload.keys())


def _snapshot_metadata_from_data(snapshot_data: dict[str, object]) -> OfflineSnapshotMetadata:
    return OfflineSnapshotMetadata(
        schema_version=str(snapshot_data.get("schema_version", "") or ""),
        export_kind=str(snapshot_data.get("export_kind", "") or ""),
        exported_at=str(snapshot_data.get("exported_at", "") or ""),
        source=str(snapshot_data.get("source", "") or ""),
        inspection_available=bool(snapshot_data.get("inspection_available")),
        snapshot_id=str(snapshot_data.get("snapshot_id", "") or ""),
        payload_keys=_present_keys(snapshot_data.get("payload_keys"), {}),
    )


def _export_state_from_validation(validation: OfflineSnapshotValidationResult) -> str:
    if validation.validation_state == "snapshot_valid_with_warnings":
        return "export_ready_with_warnings"
    if validation.validation_state == "snapshot_valid":
        return "export_ready"
    return "export_invalid"


def _build_export_reasoning(
    validation: OfflineSnapshotValidationResult,
    *,
    source: str,
    snapshot_id: str,
) -> list[str]:
    reasoning = [
        f"Snapshot exported from {source}.",
        f"Snapshot id: {snapshot_id}.",
    ]
    reasoning.extend(ensure_reasoning_list(validation.validation_reasoning))
    return reasoning


def _build_import_reasoning(
    import_state: str,
    validation: OfflineSnapshotValidationResult,
) -> list[str]:
    reasoning = [f"Snapshot import completed with state {import_state}."]
    reasoning.extend(ensure_reasoning_list(validation.validation_reasoning))
    return reasoning
