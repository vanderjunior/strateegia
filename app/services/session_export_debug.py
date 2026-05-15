from __future__ import annotations

from copy import deepcopy

from app.domain.models import (
    BehavioralDiffExport,
    RuntimeDebugEntry,
    SessionExportSnapshot,
    SessionInspectionSummary,
)
from app.services.runtime_profile_utils import average_values, clamp_value, state_reasoning
from app.services.session_snapshot_diff import build_session_snapshot, compare_session_snapshots


class SessionExportDebugLayer:
    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        snapshot = build_session_export_snapshot(runtime_blocks)
        payload = snapshot.model_dump(mode="json")
        return [{**deepcopy(block), **payload} for block in runtime_blocks]


def build_session_export_snapshot(runtime_blocks: list[dict] | None) -> SessionExportSnapshot:
    blocks = list(runtime_blocks or [])
    if not blocks:
        return SessionExportSnapshot(
            session_export_state="export_ready",
            runtime_export_summary="Sessao vazia ou neutra para exportacao observacional.",
            export_reasoning=["Nao havia blocos para estruturar exportacao de debug."],
            export_trace_summary="Sem trilha observacional exportavel.",
        )

    latest = blocks[-1]
    session_snapshot = build_session_snapshot(blocks)
    diff_export = build_behavioral_diff_export(blocks)
    inspection_summary = _build_inspection_summary(blocks)
    _ = [_build_debug_entry(block) for block in blocks]

    export_alignment = average_values(
        [
            session_snapshot.validation_confidence,
            clamp_value(latest.get("validation_confidence", 0.0)),
            clamp_value(latest.get("evidence_alignment", 0.0)),
        ]
    )

    return SessionExportSnapshot(
        session_export_state="export_ready",
        runtime_export_summary=_runtime_export_summary(session_snapshot, diff_export),
        pedagogical_runtime_snapshot={
            "pedagogical_mode": str(latest.get("pedagogical_mode") or ""),
            "micro_intervention": str(latest.get("micro_intervention") or ""),
            "trajectory_state": str(latest.get("trajectory_state") or ""),
            "expression_mode": str(latest.get("pedagogical_expression_mode") or ""),
            "compression_mode": str(latest.get("cognitive_compression_mode") or ""),
        },
        validation_snapshot={
            "pedagogical_validation_state": str(latest.get("pedagogical_validation_state") or ""),
            "validation_harness_state": str(latest.get("validation_harness_state") or ""),
            "validation_confidence": clamp_value(latest.get("validation_confidence", 0.0)),
            "runtime_validation_summary": str(latest.get("runtime_validation_summary") or ""),
        },
        behavioral_diff_snapshot={
            "state": diff_export.behavioral_diff_state,
            "delta": diff_export.runtime_behavior_delta,
            "convergence_summary": diff_export.convergence_summary,
            "divergence_summary": diff_export.divergence_summary,
        },
        runtime_trace_snapshot={
            "runtime_trace_state": str(latest.get("runtime_trace_state") or ""),
            "trace_summary": str(latest.get("runtime_pressure_summary") or ""),
            "signal_contributors": list(latest.get("signal_contributors") or []),
        },
        stability_snapshot={
            "session_stability_state": session_snapshot.session_snapshot_state,
            "stabilization_sustainability": session_snapshot.stabilization_sustainability,
            "pacing_stability": session_snapshot.pacing_stability,
            "cognitive_balance": session_snapshot.cognitive_balance,
        },
        tuning_snapshot={
            "pedagogical_tuning_state": str(latest.get("pedagogical_tuning_state") or ""),
            "retrieval_tolerance": clamp_value(latest.get("retrieval_tolerance", 0.0)),
            "compression_conservatism": clamp_value(latest.get("compression_conservatism", 0.0)),
        },
        compression_snapshot={
            "compression_mode": str(latest.get("cognitive_compression_mode") or ""),
            "compression_safety_metric": clamp_value(latest.get("compression_safety_metric", 0.0)),
            "compression_safety_signal": clamp_value(latest.get("compression_safety_signal", 0.0)),
        },
        continuity_snapshot={
            "continuity_state": str(latest.get("session_coherence_state") or ""),
            "continuity_family": str(latest.get("continuity_family") or ""),
            "continuity_smoothness": session_snapshot.continuity_smoothness,
        },
        support_snapshot={
            "support_family": str(latest.get("support_family") or ""),
            "support_density": session_snapshot.support_density,
            "scaffold_load": session_snapshot.scaffold_load,
        },
        retrieval_snapshot={
            "family": str(latest.get("retrieval_family") or ""),
            "density": session_snapshot.retrieval_density,
            "sustainability": clamp_value(latest.get("retrieval_sustainability_signal", 0.0)),
        },
        reconstruction_snapshot={
            "trajectory_state": str(latest.get("trajectory_state") or ""),
            "pressure": session_snapshot.reconstruction_pressure,
            "sustainability": clamp_value(latest.get("reconstruction_sustainability_signal", 0.0)),
        },
        export_reasoning=state_reasoning(
            "Estado de exportacao",
            "export_ready",
            [
                f"Snapshot de sessao: {session_snapshot.session_snapshot_state}.",
                f"Diff comportamental: {diff_export.behavioral_diff_state}.",
                f"Blocos observados: {len(blocks)}.",
            ],
        ),
        export_alignment=export_alignment,
        export_trace_summary=inspection_summary.inspection_summary,
    )


def build_behavioral_diff_export(runtime_blocks: list[dict] | None) -> BehavioralDiffExport:
    blocks = list(runtime_blocks or [])
    if not blocks:
        return BehavioralDiffExport(
            behavioral_diff_state="behavior_stable",
            convergence_summary="Sem blocos para comparar.",
            divergence_summary="Sem divergencia observacional.",
            why_this_behavioral_diff="Nao havia sessao para exportar diff.",
        )

    latest = blocks[-1]
    previous = build_session_snapshot(blocks[:-1]) if len(blocks) > 1 else None
    current = build_session_snapshot(blocks)
    diff = compare_session_snapshots(previous, current)
    state = str(latest.get("behavioral_diff_state") or diff.behavioral_diff_state)
    return BehavioralDiffExport(
        behavioral_diff_state=state,
        retrieval_shift=clamp_value(latest.get("retrieval_shift", diff.retrieval_shift)),
        scaffold_shift=latest.get("scaffold_shift", diff.scaffold_shift),
        continuity_shift=latest.get("continuity_shift", diff.continuity_shift),
        pacing_shift=latest.get("pacing_shift", diff.pacing_shift),
        compression_shift=latest.get("compression_shift", diff.compression_shift),
        stabilization_shift=latest.get("stabilization_shift", diff.stabilization_shift),
        overlap_shift=latest.get("overlap_shift", diff.overlap_shift),
        modulation_shift=latest.get("modulation_shift", diff.modulation_shift),
        validation_shift=latest.get("validation_shift", diff.validation_shift),
        convergence_summary=str(latest.get("convergence_summary") or diff.convergence_summary),
        divergence_summary=str(latest.get("divergence_summary") or diff.divergence_summary),
        runtime_behavior_delta=clamp_value(latest.get("runtime_behavior_delta", diff.runtime_behavior_delta)),
        why_this_behavioral_diff=str(latest.get("why_this_behavioral_diff") or diff.why_this_behavioral_diff),
    )


def _build_debug_entry(block: dict) -> RuntimeDebugEntry:
    return RuntimeDebugEntry(
        block_type=str(block.get("type") or ""),
        topic_id=str(block.get("topic_id") or ""),
        state_labels=[
            str(block.get("session_stability_state") or ""),
            str(block.get("pedagogical_tuning_state") or ""),
            str(block.get("validation_harness_state") or ""),
            str(block.get("behavioral_diff_state") or ""),
        ],
        signal_families={
            "retrieval": str(block.get("retrieval_family") or ""),
            "support": str(block.get("support_family") or ""),
            "continuity": str(block.get("continuity_family") or ""),
            "stabilization": str(block.get("stabilization_family") or ""),
            "overlap": str(block.get("overlap_family") or ""),
        },
        primary_summary=str(
            block.get("runtime_validation_summary")
            or block.get("session_stability_summary")
            or block.get("tuning_profile_summary")
            or ""
        ),
    )


def _build_inspection_summary(blocks: list[dict]) -> SessionInspectionSummary:
    latest = blocks[-1]
    pressures = []
    if clamp_value(latest.get("retrieval_density_metric", 0.0)) >= 0.6:
        pressures.append("retrieval")
    if clamp_value(latest.get("scaffold_load_metric", 0.0)) >= 0.6:
        pressures.append("scaffold")
    if clamp_value(latest.get("adaptive_overlap_signal", 0.0)) >= 0.5:
        pressures.append("overlap")

    states = [
        str(latest.get("session_stability_state") or ""),
        str(latest.get("validation_harness_state") or ""),
        str(latest.get("behavioral_diff_state") or ""),
    ]

    pressure_summary = ", ".join(pressures) if pressures else "sem pressao dominante"
    state_summary = ", ".join([state for state in states if state]) or "sem estado dominante"
    return SessionInspectionSummary(
        dominant_runtime_pressures=pressures,
        dominant_runtime_states=[state for state in states if state],
        validation_confidence=clamp_value(latest.get("validation_confidence", 0.0)),
        inspection_summary=f"Pressao dominante: {pressure_summary}. Estados dominantes: {state_summary}.",
    )


def _runtime_export_summary(snapshot, diff) -> str:
    return (
        f"snapshot={snapshot.session_snapshot_state}; diff={diff.behavioral_diff_state}; "
        f"retrieval={snapshot.retrieval_density:.2f}; support={snapshot.support_density:.2f}; "
        f"continuity={snapshot.continuity_smoothness:.2f}"
    )
