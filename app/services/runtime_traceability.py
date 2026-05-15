from __future__ import annotations

from copy import deepcopy

from app.domain.models import RuntimeTraceProfile


class RuntimeTraceabilityLayer:
    WINDOW_SIZE = 4

    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        annotated: list[dict] = []
        recent: list[dict] = []
        for block in [deepcopy(item) for item in runtime_blocks]:
            profile = resolve_runtime_traceability(current_block=block, recent_blocks=recent)
            annotated_block = {**block, **profile.model_dump(mode="json")}
            annotated.append(annotated_block)
            recent.append(annotated_block)
            recent = recent[-self.WINDOW_SIZE :]
        return annotated


def resolve_runtime_traceability(
    *,
    current_block: dict,
    recent_blocks: list[dict] | None = None,
) -> RuntimeTraceProfile:
    recent_blocks = list(recent_blocks or [])
    window = (recent_blocks[-3:] if recent_blocks else []) + [current_block]

    contributors = _signal_contributors(current_block)
    adaptation_stack = _adaptation_stack(current_block)
    trace_alignment = _trace_alignment(current_block, window)
    state = _state(current_block, window, trace_alignment)

    return RuntimeTraceProfile(
        runtime_trace_state=state,
        behavioral_trace=_behavioral_trace(current_block, window),
        trace_reasoning=[
            f"Estado de trace: {state}.",
            f"Contribuidores ativos: {', '.join(contributors) if contributors else 'nenhum explicito'}.",
            f"Alinhamento do trace: {trace_alignment:.2f}.",
        ],
        signal_contributors=contributors,
        adaptation_stack=adaptation_stack,
        runtime_pressure_summary=_runtime_pressure_summary(current_block, window),
        retrieval_density_trace=_retrieval_density_trace(window),
        support_overlap_trace=_support_overlap_trace(window),
        continuity_transition_trace=_continuity_transition_trace(window),
        stabilization_trace=_stabilization_trace(window),
        modulation_trace=_modulation_trace(current_block, window),
        trace_alignment=round(trace_alignment, 4),
        why_this_trace_now=_why_now(state),
    )


def _signal_contributors(block: dict) -> list[str]:
    contributors: list[str] = []
    if block.get("pedagogical_mode"):
        contributors.append("pedagogical_mode")
    if block.get("micro_intervention"):
        contributors.append("micro_intervention")
    if block.get("trajectory_state"):
        contributors.append("trajectory")
    if block.get("cognitive_momentum"):
        contributors.append("momentum")
    if block.get("session_coherence_state"):
        contributors.append("coherence")
    if block.get("pedagogical_expression_mode"):
        contributors.append("expression")
    if block.get("cognitive_compression_mode"):
        contributors.append("compression")
    if block.get("adaptive_signal_state"):
        contributors.append("signal_consolidation")
    if block.get("pedagogical_observability_state"):
        contributors.append("observability")
    return contributors


def _adaptation_stack(block: dict) -> list[str]:
    stack = [
        str(block.get("pedagogical_mode") or ""),
        str(block.get("micro_intervention") or ""),
        str(block.get("pedagogical_expression_mode") or ""),
        str(block.get("cognitive_compression_mode") or ""),
        str(block.get("adaptive_signal_state") or ""),
        str(block.get("pedagogical_observability_state") or ""),
    ]
    return [item for item in stack if item]


def _trace_alignment(block: dict, window: list[dict]) -> float:
    values = [
        _clamp(block.get("signal_overlap_density", 0.0)),
        _clamp(block.get("modulation_overlap", 0.0)),
        _clamp(block.get("progression_continuity", 0.5)),
        _clamp(block.get("longitudinal_consistency", 0.5)),
    ]
    retrieval = sum(
        {"high": 0.22, "medium": 0.1, "low": 0.03}.get(str(item.get("retrieval_intensity") or ""), 0.03)
        for item in window
    ) / max(len(window), 1)
    values.append(_clamp(retrieval))
    return _clamp(sum(values) / len(values))


def _state(current_block: dict, window: list[dict], trace_alignment: float) -> str:
    if _support_overlap_value(window) >= 0.6:
        return "support_accumulated"
    if _retrieval_cluster_value(window) >= 0.48:
        return "retrieval_clustered"
    if str(current_block.get("session_coherence_state") or "") in {"continuity_stable", "contextual_shift_softened"}:
        return "continuity_softened"
    if str(current_block.get("trajectory_state") or "") == "reconstruction_fragile":
        return "reconstruction_supported"
    if str(current_block.get("stabilization_stage") or "") in {"stabilizing", "consolidated", "resilient"}:
        return "stabilization_progressive"
    if str(current_block.get("adaptive_signal_state") or "") in {"support_convergent", "modulation_stable", "compressed_stability"}:
        return "adaptation_convergent"
    if trace_alignment >= 0.48:
        return "runtime_balanced"
    return "trace_stable"


def _behavioral_trace(current_block: dict, window: list[dict]) -> list[str]:
    parts = [
        f"modo={current_block.get('pedagogical_mode') or 'n/a'}",
        f"intervencao={current_block.get('micro_intervention') or 'n/a'}",
        f"trajetoria={current_block.get('trajectory_state') or 'n/a'}",
        f"compressao={current_block.get('cognitive_compression_mode') or 'n/a'}",
        f"observabilidade={current_block.get('pedagogical_observability_state') or 'n/a'}",
        f"janela={len(window)}",
    ]
    return parts


def _runtime_pressure_summary(current_block: dict, window: list[dict]) -> str:
    retrieval = _retrieval_cluster_value(window)
    support = _support_overlap_value(window)
    load = sum(_clamp(item.get("cognitive_load_score", 0.0)) for item in window) / max(len(window), 1)
    return (
        f"retrieval={retrieval:.2f}; support={support:.2f}; "
        f"load={load:.2f}; coherence={current_block.get('session_coherence_state') or 'n/a'}"
    )


def _retrieval_density_trace(window: list[dict]) -> str:
    value = _retrieval_cluster_value(window)
    if value >= 0.52:
        return "Retrieval recente apareceu de forma agrupada."
    if value <= 0.18:
        return "Retrieval recente permaneceu leve."
    return "Retrieval recente ficou moderado."


def _support_overlap_trace(window: list[dict]) -> str:
    value = _support_overlap_value(window)
    if value >= 0.6:
        return "Suporte cognitivo apareceu acumulado em janela curta."
    if value <= 0.22:
        return "Suporte cognitivo permaneceu enxuto."
    return "Suporte cognitivo ficou em faixa intermediaria."


def _continuity_transition_trace(window: list[dict]) -> str:
    last = window[-1]
    state = str(last.get("session_coherence_state") or "")
    if state in {"continuity_stable", "contextual_shift_softened"}:
        return "A transicao recente preservou continuidade perceptivel."
    if state == "pacing_fragile":
        return "A transicao recente mostrou fragilidade local."
    return "A transicao recente permaneceu neutra."


def _stabilization_trace(window: list[dict]) -> str:
    stages = [str(item.get("stabilization_stage") or "") for item in window if item.get("stabilization_stage")]
    if any(stage in {"consolidated", "resilient"} for stage in stages):
        return "A janela recente contem sinais claros de estabilizacao."
    if any(stage == "stabilizing" for stage in stages):
        return "A janela recente mostra estabilizacao em progresso."
    return "A estabilizacao recente permaneceu discreta."


def _modulation_trace(current_block: dict, window: list[dict]) -> str:
    pieces = [
        str(current_block.get("adaptive_signal_state") or "neutral"),
        str(current_block.get("pedagogical_observability_state") or "neutral"),
        str(current_block.get("cognitive_momentum") or "neutral"),
    ]
    unique = len({piece for piece in pieces if piece != "neutral"})
    if unique >= 3:
        return "A modulacao atual mostra varias camadas visiveis ao mesmo tempo."
    if unique == 2:
        return "A modulacao atual mostra convergencia moderada."
    return "A modulacao atual permanece enxuta."


def _retrieval_cluster_value(window: list[dict]) -> float:
    total = 0.0
    for item in window:
        total += {"high": 0.28, "medium": 0.14, "low": 0.03}.get(str(item.get("retrieval_intensity") or ""), 0.03)
        total += {"retrieval_heavy": 0.12, "pressured": 0.05}.get(str(item.get("cognitive_momentum") or ""), 0.0)
        total += {"retrieval_dense": 0.1}.get(str(item.get("pedagogical_observability_state") or ""), 0.0)
    return _clamp(total / max(len(window), 1))


def _support_overlap_value(window: list[dict]) -> float:
    total = 0.0
    for item in window:
        total += _clamp(item.get("signal_overlap_density", 0.0)) * 0.3
        total += _clamp(item.get("scaffold_density", 0.0)) * 0.3
        total += _clamp(item.get("modulation_overlap", 0.0)) * 0.25
        if str(item.get("trajectory_state") or "") == "reconstruction_fragile":
            total += 0.08
        if str(item.get("pedagogical_observability_state") or "") == "scaffold_saturated":
            total += 0.07
    return _clamp(total / max(len(window), 1))


def _why_now(state: str) -> str:
    return {
        "trace_stable": "O trace atual registra um bloco sem concentracao anormal de sinais.",
        "support_accumulated": "O trace atual destaca acumulacao local de suporte cognitivo.",
        "retrieval_clustered": "O trace atual destaca concentracao recente de sinais de retrieval.",
        "continuity_softened": "O trace atual registra uma transicao local suavizada.",
        "reconstruction_supported": "O trace atual registra reforco claro de reconstrucao.",
        "stabilization_progressive": "O trace atual registra sinais de estabilizacao em andamento.",
        "adaptation_convergent": "O trace atual registra convergencia entre camadas adaptativas observadas.",
        "runtime_balanced": "O trace atual resume um runtime localmente equilibrado.",
    }.get(state, "O trace atual permaneceu em faixa observacional neutra.")


def _clamp(value: float | int | None, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if value is None:
        return minimum
    return max(minimum, min(float(value), maximum))
