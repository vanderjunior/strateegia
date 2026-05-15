from __future__ import annotations

from copy import deepcopy

from app.domain.models import SessionStabilityMetricsProfile
from app.services.runtime_profile_utils import clamp_value, state_message, state_reasoning


class SessionStabilityMetricsLayer:
    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        profile = resolve_session_stability_metrics(runtime_blocks)
        payload = profile.model_dump(mode="json")
        return [{**deepcopy(block), **payload} for block in runtime_blocks]


def resolve_session_stability_metrics(
    runtime_blocks: list[dict] | None,
) -> SessionStabilityMetricsProfile:
    blocks = list(runtime_blocks or [])
    if not blocks:
        return SessionStabilityMetricsProfile(
            session_stability_state="balanced",
            session_stability_reasoning=["Nao havia blocos para agregar; estado neutro aplicado."],
            session_pressure_summary="Sem pressao acumulada observavel.",
            session_stability_summary="Sessao vazia ou neutra para fins de diagnostico.",
            why_this_session_state="A agregacao recebeu uma sessao sem blocos executaveis.",
        )

    retrieval_density_metric = _retrieval_density_metric(blocks)
    scaffold_load_metric = _scaffold_load_metric(blocks)
    continuity_smoothness_metric = _continuity_smoothness_metric(blocks)
    reconstruction_pressure_metric = _reconstruction_pressure_metric(blocks)
    compression_safety_metric = _compression_safety_metric(blocks)
    modulation_convergence_metric = _modulation_convergence_metric(blocks)
    stabilization_sustainability_metric = _stabilization_sustainability_metric(blocks)
    support_density = _support_density_metric(
        scaffold_load_metric=scaffold_load_metric,
        compression_safety_metric=compression_safety_metric,
        modulation_convergence_metric=modulation_convergence_metric,
        blocks=blocks,
    )
    pacing_stability_metric = _pacing_stability_metric(blocks, continuity_smoothness_metric)
    cognitive_balance_metric = _cognitive_balance_metric(
        retrieval_density_metric=retrieval_density_metric,
        scaffold_load_metric=scaffold_load_metric,
        continuity_smoothness_metric=continuity_smoothness_metric,
        reconstruction_pressure_metric=reconstruction_pressure_metric,
        compression_safety_metric=compression_safety_metric,
        stabilization_sustainability_metric=stabilization_sustainability_metric,
        pacing_stability_metric=pacing_stability_metric,
    )

    state = _state(
        retrieval_density_metric=retrieval_density_metric,
        scaffold_load_metric=scaffold_load_metric,
        continuity_smoothness_metric=continuity_smoothness_metric,
        reconstruction_pressure_metric=reconstruction_pressure_metric,
        compression_safety_metric=compression_safety_metric,
        modulation_convergence_metric=modulation_convergence_metric,
        stabilization_sustainability_metric=stabilization_sustainability_metric,
        support_density=support_density,
        pacing_stability_metric=pacing_stability_metric,
        cognitive_balance_metric=cognitive_balance_metric,
    )

    return SessionStabilityMetricsProfile(
        session_stability_state=state,
        session_stability_reasoning=state_reasoning(
            "Estado agregado da sessao",
            state,
            [
                f"Densidade de retrieval: {retrieval_density_metric:.2f}; carga de scaffold: {scaffold_load_metric:.2f}.",
                f"Continuidade: {continuity_smoothness_metric:.2f}; convergencia modular: {modulation_convergence_metric:.2f}.",
            ],
        ),
        retrieval_density_metric=round(retrieval_density_metric, 4),
        scaffold_load_metric=round(scaffold_load_metric, 4),
        continuity_smoothness_metric=round(continuity_smoothness_metric, 4),
        reconstruction_pressure_metric=round(reconstruction_pressure_metric, 4),
        compression_safety_metric=round(compression_safety_metric, 4),
        modulation_convergence_metric=round(modulation_convergence_metric, 4),
        stabilization_sustainability_metric=round(stabilization_sustainability_metric, 4),
        support_density=round(support_density, 4),
        pacing_stability_metric=round(pacing_stability_metric, 4),
        cognitive_balance_metric=round(cognitive_balance_metric, 4),
        session_pressure_summary=_session_pressure_summary(
            retrieval_density_metric=retrieval_density_metric,
            scaffold_load_metric=scaffold_load_metric,
            reconstruction_pressure_metric=reconstruction_pressure_metric,
        ),
        session_stability_summary=_session_stability_summary(state),
        why_this_session_state=_why_this_session_state(state),
    )


def _retrieval_density_metric(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("retrieval_pressure_accumulation", 0.0)) * 0.72
        family = str(block.get("retrieval_family") or "")
        if family == "retrieval_dense":
            score += 0.2
        elif family == "retrieval_balanced":
            score += 0.08
        state = str(block.get("pedagogical_validation_state") or "")
        if state == "retrieval_saturated":
            score += 0.12
        elif state == "retrieval_effective":
            score += 0.06
        values.append(_clamp(score))
    return _average(values)


def _scaffold_load_metric(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("scaffold_density", 0.0)) * 0.72
        if str(block.get("support_family") or "") in {"support_heavy", "support_dense"}:
            score += 0.18
        if str(block.get("pedagogical_observability_state") or "") in {"support_heavy", "scaffold_saturated"}:
            score += 0.1
        values.append(_clamp(score))
    return _average(values)


def _continuity_smoothness_metric(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = (
            _clamp(block.get("continuity_stability", 0.55)) * 0.52
            + _clamp(block.get("progression_continuity", 0.55)) * 0.34
        )
        family = str(block.get("continuity_family") or "")
        if family == "continuity_stable":
            score += 0.12
        elif family == "continuity_fragile":
            score -= 0.18
        values.append(_clamp(score))
    return _average(values)


def _reconstruction_pressure_metric(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("reconstruction_fragility", 0.0)) * 0.7
        if str(block.get("support_family") or "") == "support_heavy":
            score += 0.14
        if str(block.get("runtime_trace_state") or "") == "reconstruction_supported":
            score += 0.08
        values.append(_clamp(score))
    return _average(values)


def _compression_safety_metric(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = 0.28
        score += _clamp(block.get("compression_support_alignment", 0.0)) * 0.42
        score += _clamp(block.get("stabilization_quality_signal", 0.0)) * 0.1
        score += _clamp(block.get("continuity_stability", 0.0)) * 0.08
        score -= _clamp(block.get("false_fluency_risk", 0.0)) * 0.18
        if str(block.get("pedagogical_validation_state") or "") == "surface_fluency_detected":
            score -= 0.12
        values.append(_clamp(score))
    return _average(values)


def _modulation_convergence_metric(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = max(
            _clamp(block.get("modulation_overlap", 0.0)),
            _clamp(block.get("signal_overlap_density", 0.0)),
        ) * 0.7
        overlap_family = str(block.get("overlap_family") or "")
        if overlap_family in {"overlap_high", "overlap_convergent"}:
            score += 0.22
        elif overlap_family == "overlap_moderate":
            score += 0.12
        values.append(_clamp(score))
    return _average(values)


def _stabilization_sustainability_metric(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = (
            _clamp(block.get("stabilization_quality_signal", 0.0)) * 0.36
            + _clamp(block.get("longitudinal_validation_signal", 0.0)) * 0.34
            + _clamp(block.get("longitudinal_consistency", 0.0)) * 0.18
            + _clamp(block.get("stabilization_quality", 0.0)) * 0.08
        )
        family = str(block.get("stabilization_family") or "")
        if family in {"stabilized", "stabilization_progressive"}:
            score += 0.1
        values.append(_clamp(score))
    return _average(values)


def _support_density_metric(
    *,
    scaffold_load_metric: float,
    compression_safety_metric: float,
    modulation_convergence_metric: float,
    blocks: list[dict],
) -> float:
    support_heavy_ratio = sum(
        1.0
        for block in blocks
        if str(block.get("support_family") or "") in {"support_heavy", "support_dense"}
    ) / max(len(blocks), 1)
    return _clamp(
        scaffold_load_metric * 0.52
        + compression_safety_metric * 0.18
        + modulation_convergence_metric * 0.12
        + support_heavy_ratio * 0.18
    )


def _pacing_stability_metric(
    blocks: list[dict],
    continuity_smoothness_metric: float,
) -> float:
    values = []
    for block in blocks:
        pacing = _clamp(block.get("pacing_adjustment", 0.5))
        stability = 1.0 - min(abs(pacing - 0.5) * 1.6, 1.0)
        values.append(_clamp(stability))
    return _clamp(_average(values) * 0.62 + continuity_smoothness_metric * 0.38)


def _cognitive_balance_metric(
    *,
    retrieval_density_metric: float,
    scaffold_load_metric: float,
    continuity_smoothness_metric: float,
    reconstruction_pressure_metric: float,
    compression_safety_metric: float,
    stabilization_sustainability_metric: float,
    pacing_stability_metric: float,
) -> float:
    positive = (
        continuity_smoothness_metric
        + compression_safety_metric
        + stabilization_sustainability_metric
        + pacing_stability_metric
    ) / 4
    pressure = (
        max(0.0, retrieval_density_metric - 0.45)
        + max(0.0, scaffold_load_metric - 0.45)
        + max(0.0, reconstruction_pressure_metric - 0.45)
    ) / 3
    return _clamp(positive * 0.8 + (1.0 - pressure) * 0.2)


def _state(
    *,
    retrieval_density_metric: float,
    scaffold_load_metric: float,
    continuity_smoothness_metric: float,
    reconstruction_pressure_metric: float,
    compression_safety_metric: float,
    modulation_convergence_metric: float,
    stabilization_sustainability_metric: float,
    support_density: float,
    pacing_stability_metric: float,
    cognitive_balance_metric: float,
) -> str:
    if retrieval_density_metric >= 0.62 and retrieval_density_metric >= support_density - 0.04:
        return "retrieval_heavy"
    if support_density >= 0.62 or scaffold_load_metric >= 0.62:
        return "support_dense"
    if reconstruction_pressure_metric >= 0.64:
        return "reconstruction_loaded"
    if stabilization_sustainability_metric >= 0.72:
        return "stabilization_progressive"
    if modulation_convergence_metric >= 0.66:
        return "modulation_convergent"
    if continuity_smoothness_metric >= 0.72 and pacing_stability_metric >= 0.62:
        return "continuity_stable"
    if compression_safety_metric >= 0.72 and scaffold_load_metric <= 0.42:
        return "compression_safe"
    if cognitive_balance_metric <= 0.38 or continuity_smoothness_metric <= 0.34:
        return "observably_fragile"
    if cognitive_balance_metric >= 0.68 and pacing_stability_metric >= 0.58:
        return "cognitively_balanced"
    return "balanced"


def _session_pressure_summary(
    *,
    retrieval_density_metric: float,
    scaffold_load_metric: float,
    reconstruction_pressure_metric: float,
) -> str:
    if retrieval_density_metric >= scaffold_load_metric and retrieval_density_metric >= reconstruction_pressure_metric:
        return "A maior pressao da sessao veio da acumulacao de retrieval."
    if scaffold_load_metric >= reconstruction_pressure_metric:
        return "A maior pressao da sessao veio da acumulacao de suporte e scaffold."
    return "A maior pressao da sessao veio da carga reconstrutiva sustentada."


def _session_stability_summary(state: str) -> str:
    return state_message(
        state,
        {
            "balanced": "A sessao permaneceu observacionalmente equilibrada e sem pressao dominante.",
            "retrieval_heavy": "A sessao acumulou mais retrieval do que o restante das modulacoes.",
            "support_dense": "A sessao concentrou suporte e scaffold acima da faixa mais leve.",
            "reconstruction_loaded": "A sessao sustentou pressao reconstrutiva relevante na janela agregada.",
            "continuity_stable": "A sessao manteve continuidade legivel e ritmo relativamente suave.",
            "stabilization_progressive": "A sessao mostrou sinais consistentes de estabilizacao sustentavel.",
            "modulation_convergent": "As modulacoes da sessao convergiram com pouca dispersao semantica.",
            "compression_safe": "A compressao permaneceu segura para o contexto observado.",
            "cognitively_balanced": "A combinacao de ritmo, continuidade e suporte ficou cognitivamente equilibrada.",
            "observably_fragile": "Os sinais da sessao sugerem fragilidade observacional em mais de um eixo.",
        },
        "A sessao permaneceu em faixa observacional neutra.",
    )


def _why_this_session_state(state: str) -> str:
    return state_message(
        state,
        {
            "balanced": "Nenhum eixo agregado dominou a sessao de forma clara.",
            "retrieval_heavy": "Os sinais de retrieval apareceram com mais frequencia e intensidade na sessao.",
            "support_dense": "Os sinais de scaffold e suporte convergiram acima da faixa leve.",
            "reconstruction_loaded": "A fragilidade reconstrutiva permaneceu suficientemente presente na agregacao.",
            "continuity_stable": "A sessao manteve continuidade e ritmo sem quedas locais relevantes.",
            "stabilization_progressive": "Os sinais de estabilidade longitudinal e qualidade de consolidacao convergiram bem.",
            "modulation_convergent": "As camadas atuais apontaram para uma sessao semanticamente convergente.",
            "compression_safe": "A compressao observada permaneceu alinhada ao contexto sem aumento forte de risco.",
            "cognitively_balanced": "O equilibrio entre suporte, continuidade e pacing permaneceu saudavel.",
            "observably_fragile": "A agregacao mostrou baixa folga em continuidade, compressao ou balanceamento cognitivo.",
        },
        "O estado veio de uma agregacao local sem dominancia forte.",
    )


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return _clamp(sum(values) / len(values))


def _clamp(value: float | int | None, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return clamp_value(value, minimum, maximum)
