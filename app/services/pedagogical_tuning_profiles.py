from __future__ import annotations

from copy import deepcopy

from app.domain.models import PedagogicalTuningProfile


class PedagogicalTuningProfilesLayer:
    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        profile = resolve_pedagogical_tuning_profile(runtime_blocks)
        payload = profile.model_dump(mode="json")
        return [{**deepcopy(block), **payload} for block in runtime_blocks]


def resolve_pedagogical_tuning_profile(
    runtime_blocks: list[dict] | None,
) -> PedagogicalTuningProfile:
    blocks = list(runtime_blocks or [])
    if not blocks:
        return PedagogicalTuningProfile(
            pedagogical_tuning_state="balanced_support",
            tuning_profile_summary="Perfil neutro por ausencia de blocos observaveis.",
            tuning_reasoning=["Nao havia blocos para consolidar tuning heuristico."],
            why_this_tuning_profile="A sessao estava vazia no momento da inspecao.",
        )

    retrieval_tolerance = _retrieval_tolerance(blocks)
    scaffold_sensitivity = _scaffold_sensitivity(blocks)
    continuity_smoothing_strength = _continuity_smoothing_strength(blocks)
    compression_conservatism = _compression_conservatism(blocks)
    reconstruction_support_level = _reconstruction_support_level(blocks)
    pacing_relief_sensitivity = _pacing_relief_sensitivity(blocks)
    overlap_tolerance = _overlap_tolerance(blocks)
    stabilization_threshold = _stabilization_threshold(blocks)
    modulation_density_tolerance = _modulation_density_tolerance(blocks)
    intervention_rotation_sensitivity = _intervention_rotation_sensitivity(blocks)

    state = _state(
        retrieval_tolerance=retrieval_tolerance,
        scaffold_sensitivity=scaffold_sensitivity,
        continuity_smoothing_strength=continuity_smoothing_strength,
        compression_conservatism=compression_conservatism,
        reconstruction_support_level=reconstruction_support_level,
        pacing_relief_sensitivity=pacing_relief_sensitivity,
        overlap_tolerance=overlap_tolerance,
        stabilization_threshold=stabilization_threshold,
        modulation_density_tolerance=modulation_density_tolerance,
        intervention_rotation_sensitivity=intervention_rotation_sensitivity,
    )

    return PedagogicalTuningProfile(
        pedagogical_tuning_state=state,
        tuning_profile_summary=_summary(state),
        tuning_reasoning=[
            f"Perfil de tuning: {state}.",
            f"Retrieval={retrieval_tolerance:.2f}; scaffold={scaffold_sensitivity:.2f}; compressao={compression_conservatism:.2f}.",
            f"Continuidade={continuity_smoothing_strength:.2f}; estabilizacao={stabilization_threshold:.2f}; overlap={overlap_tolerance:.2f}.",
        ],
        retrieval_tolerance=round(retrieval_tolerance, 4),
        scaffold_sensitivity=round(scaffold_sensitivity, 4),
        continuity_smoothing_strength=round(continuity_smoothing_strength, 4),
        compression_conservatism=round(compression_conservatism, 4),
        reconstruction_support_level=round(reconstruction_support_level, 4),
        pacing_relief_sensitivity=round(pacing_relief_sensitivity, 4),
        overlap_tolerance=round(overlap_tolerance, 4),
        stabilization_threshold=round(stabilization_threshold, 4),
        modulation_density_tolerance=round(modulation_density_tolerance, 4),
        intervention_rotation_sensitivity=round(intervention_rotation_sensitivity, 4),
        why_this_tuning_profile=_why(state),
    )


def _retrieval_tolerance(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("retrieval_pressure_accumulation", 0.0)) * 0.68
        if str(block.get("retrieval_family") or "") == "retrieval_dense":
            score += 0.18
        if str(block.get("session_stability_state") or "") == "retrieval_heavy":
            score += 0.12
        values.append(_clamp(score))
    return _average(values)


def _scaffold_sensitivity(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("scaffold_density", 0.0)) * 0.56
        score += _clamp(block.get("reconstruction_fragility", 0.0)) * 0.22
        if str(block.get("support_family") or "") in {"support_heavy", "support_dense"}:
            score += 0.16
        if str(block.get("pedagogical_observability_state") or "") in {"support_heavy", "scaffold_saturated"}:
            score += 0.1
        values.append(_clamp(score))
    return _average(values)


def _continuity_smoothing_strength(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("continuity_stability", 0.55)) * 0.48
        score += _clamp(block.get("progression_continuity", 0.55)) * 0.32
        if str(block.get("continuity_family") or "") == "continuity_stable":
            score += 0.14
        elif str(block.get("continuity_family") or "") == "continuity_fragile":
            score -= 0.14
        values.append(_clamp(score))
    return _average(values)


def _compression_conservatism(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("compression_safety_metric", 0.0)) * 0.72
        if str(block.get("stabilization_family") or "") in {"stabilized", "stabilization_progressive"}:
            score += 0.1
        score -= _clamp(block.get("false_fluency_risk", 0.0)) * 0.12
        values.append(_clamp(score))
    return _average(values)


def _reconstruction_support_level(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("reconstruction_fragility", 0.0)) * 0.58
        score += _clamp(block.get("scaffold_density", 0.0)) * 0.18
        if str(block.get("support_family") or "") in {"support_heavy", "support_dense"}:
            score += 0.14
        if str(block.get("session_stability_state") or "") == "reconstruction_loaded":
            score += 0.1
        values.append(_clamp(score))
    return _average(values)


def _pacing_relief_sensitivity(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        pacing = _clamp(block.get("pacing_adjustment", 0.5))
        score = abs(pacing - 0.5) * 1.4
        if str(block.get("session_stability_state") or "") == "observably_fragile":
            score += 0.12
        values.append(_clamp(score))
    return _average(values)


def _overlap_tolerance(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        overlap = max(
            _clamp(block.get("modulation_overlap", 0.0)),
            _clamp(block.get("signal_overlap_density", 0.0)),
        )
        score = 0.82 - overlap * 0.74
        family = str(block.get("overlap_family") or "")
        if family in {"overlap_high", "overlap_convergent"}:
            score -= 0.14
        elif family == "overlap_low":
            score += 0.08
        values.append(_clamp(score))
    return _average(values)


def _stabilization_threshold(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("stabilization_sustainability_metric", 0.0)) * 0.56
        score += _clamp(block.get("stabilization_quality", 0.0)) * 0.24
        if str(block.get("stabilization_family") or "") in {"stabilized", "stabilization_progressive"}:
            score += 0.12
        values.append(_clamp(score))
    return _average(values)


def _modulation_density_tolerance(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        overlap = max(
            _clamp(block.get("modulation_overlap", 0.0)),
            _clamp(block.get("signal_overlap_density", 0.0)),
        )
        score = 0.78 - overlap * 0.64
        if str(block.get("session_stability_state") or "") == "modulation_convergent":
            score -= 0.08
        values.append(_clamp(score))
    return _average(values)


def _intervention_rotation_sensitivity(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _clamp(block.get("intervention_repetition_signal", 0.0)) * 0.72
        if str(block.get("pedagogical_observability_state") or "") == "expression_stable":
            score += 0.08
        values.append(_clamp(score))
    return _average(values)


def _state(
    *,
    retrieval_tolerance: float,
    scaffold_sensitivity: float,
    continuity_smoothing_strength: float,
    compression_conservatism: float,
    reconstruction_support_level: float,
    pacing_relief_sensitivity: float,
    overlap_tolerance: float,
    stabilization_threshold: float,
    modulation_density_tolerance: float,
    intervention_rotation_sensitivity: float,
) -> str:
    if reconstruction_support_level >= 0.6 and scaffold_sensitivity >= 0.56:
        return "reconstruction_protective"
    if compression_conservatism >= 0.66 and stabilization_threshold >= 0.58:
        return "compression_conservative"
    if retrieval_tolerance >= 0.6:
        return "retrieval_sensitive"
    if continuity_smoothing_strength >= 0.68 and pacing_relief_sensitivity <= 0.18:
        return "continuity_relaxed"
    if stabilization_threshold >= 0.64 and modulation_density_tolerance >= 0.52:
        return "stabilization_balanced"
    if overlap_tolerance >= 0.6 and modulation_density_tolerance >= 0.58 and intervention_rotation_sensitivity <= 0.24:
        return "modulation_stable"
    if scaffold_sensitivity >= 0.5:
        return "conservative_support"
    return "balanced_support"


def _summary(state: str) -> str:
    return {
        "conservative_support": "O runtime atual explicita uma calibracao mais protetiva em suporte local.",
        "balanced_support": "O runtime atual manteve calibracao de suporte em faixa equilibrada.",
        "retrieval_sensitive": "O runtime atual parece calibrado para reagir cedo a acumulacao de retrieval.",
        "continuity_relaxed": "O runtime atual mostra suavizacao de continuidade com baixa necessidade de alivio extra.",
        "reconstruction_protective": "O runtime atual explicita protecao maior a fragilidade reconstrutiva.",
        "compression_conservative": "O runtime atual manteve compressao mais conservadora e segura.",
        "stabilization_balanced": "O runtime atual combina estabilizacao e densidade modular em faixa estavel.",
        "modulation_stable": "O runtime atual manteve tolerancia estavel a overlap e rotacao local.",
    }.get(state, "O runtime atual permaneceu em faixa calibracional neutra.")


def _why(state: str) -> str:
    return {
        "conservative_support": "A janela recente sugere tolerancia menor a perda de suporte explicativo.",
        "balanced_support": "Nenhum eixo calibracional dominou o runtime atual.",
        "retrieval_sensitive": "A acumulacao de retrieval sugere um perfil mais sensivel a essa pressao.",
        "continuity_relaxed": "A continuidade permaneceu alta o bastante para um perfil de suavizacao leve.",
        "reconstruction_protective": "A fragilidade reconstrutiva manteve a necessidade de suporte em faixa alta.",
        "compression_conservative": "Compressao segura e estabilizacao consistente convergiram para um perfil conservador.",
        "stabilization_balanced": "Os sinais de estabilizacao parecem suficientes sem excesso de densidade modular.",
        "modulation_stable": "Overlap, rotacao e densidade modular permaneceram em faixa previsivel.",
    }.get(state, "O perfil veio de uma agregacao local e bounded de sinais existentes.")


def _average(values: list[float]) -> float:
    if not values:
        return 0.0
    return _clamp(sum(values) / len(values))


def _clamp(value: float | int | None, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if value is None:
        return minimum
    return max(minimum, min(float(value), maximum))
