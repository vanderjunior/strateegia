from __future__ import annotations

from app.domain.models import RuntimeSignalNormalizationProfile


def normalize_runtime_signal_families(block: dict[str, object] | None) -> RuntimeSignalNormalizationProfile:
    block = dict(block or {})
    retrieval_family = _retrieval_family(block)
    support_family = _support_family(block)
    continuity_family = _continuity_family(block)
    stabilization_family = _stabilization_family(block)
    overlap_family = _overlap_family(block)
    return RuntimeSignalNormalizationProfile(
        retrieval_family=retrieval_family,
        support_family=support_family,
        continuity_family=continuity_family,
        stabilization_family=stabilization_family,
        overlap_family=overlap_family,
        semantic_normalization_reasoning=[
            f"Retrieval agrupado em {retrieval_family}.",
            f"Suporte agrupado em {support_family}.",
            f"Continuidade/estabilidade agrupadas em {continuity_family} / {stabilization_family}.",
        ],
        runtime_semantic_summary=(
            f"retrieval={retrieval_family}; support={support_family}; "
            f"continuity={continuity_family}; stabilization={stabilization_family}; overlap={overlap_family}"
        ),
    )


def _retrieval_family(block: dict[str, object]) -> str:
    if (
        str(block.get("adaptive_signal_state") or "") == "retrieval_saturation"
        or str(block.get("pedagogical_observability_state") or "") == "retrieval_dense"
        or str(block.get("runtime_trace_state") or "") == "retrieval_clustered"
        or str(block.get("cognitive_momentum") or "") == "retrieval_heavy"
        or str(block.get("session_coherence_state") or "") == "retrieval_transition"
        or str(block.get("pedagogical_expression_mode") or "") == "retrieval_softener"
        or str(block.get("cognitive_compression_mode") or "") == "retrieval_focused"
        or str(block.get("retrieval_intensity") or "") == "high"
        or _clamp(block.get("retrieval_pressure_accumulation", 0.0)) >= 0.42
    ):
        return "retrieval_dense"
    if str(block.get("retrieval_intensity") or "") == "low":
        return "retrieval_light"
    return "retrieval_balanced"


def _support_family(block: dict[str, object]) -> str:
    if (
        str(block.get("trajectory_state") or "") == "reconstruction_fragile"
        or str(block.get("adaptive_signal_state") or "") in {"reconstruction_pressure", "support_convergent"}
        or str(block.get("pedagogical_observability_state") or "") in {"scaffold_saturated", "support_heavy"}
        or str(block.get("runtime_trace_state") or "") in {"support_accumulated", "reconstruction_supported"}
        or str(block.get("cognitive_compression_mode") or "") in {"reconstruction_scaffolded", "transfer_expanded", "prerequisite_supported"}
        or _clamp(block.get("scaffold_density", 0.0)) >= 0.48
    ):
        return "support_heavy"
    return "support_light"


def _continuity_family(block: dict[str, object]) -> str:
    if str(block.get("session_coherence_state") or "") in {"continuity_stable", "contextual_shift_softened", "stable_progression"}:
        return "continuity_stable"
    if (
        str(block.get("session_coherence_state") or "") == "pacing_fragile"
        or str(block.get("cognitive_momentum") or "") == "continuity_fragile"
    ):
        return "continuity_fragile"
    return "continuity_neutral"


def _stabilization_family(block: dict[str, object]) -> str:
    if (
        str(block.get("stabilization_stage") or "") in {"consolidated", "resilient"}
        or str(block.get("adaptive_signal_state") or "") == "compressed_stability"
        or str(block.get("pedagogical_validation_state") or "") in {"stabilization_sustainable", "longitudinally_stable"}
        or str(block.get("runtime_trace_state") or "") == "stabilization_progressive"
        or _clamp(block.get("longitudinal_retention", 0.0)) >= 0.72
    ):
        return "stabilized"
    if str(block.get("stabilization_stage") or "") == "stabilizing":
        return "stabilizing"
    return "unstable"


def _overlap_family(block: dict[str, object]) -> str:
    overlap = max(
        _clamp(block.get("modulation_overlap", 0.0)),
        _clamp(block.get("signal_overlap_density", 0.0)),
    )
    if (
        str(block.get("adaptive_signal_state") or "") in {"support_convergent", "reinforcement_overlap"}
        or str(block.get("pedagogical_observability_state") or "") == "signal_redundant"
        or overlap >= 0.5
    ):
        return "overlap_high"
    if overlap >= 0.28:
        return "overlap_moderate"
    return "overlap_low"


def _clamp(value: float | int | None, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if value is None:
        return minimum
    return max(minimum, min(float(value), maximum))
