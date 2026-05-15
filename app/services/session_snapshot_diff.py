from __future__ import annotations

from copy import deepcopy

from app.domain.models import BehavioralDiffProfile, SessionSnapshotProfile
from app.services.runtime_profile_utils import clamp_value, state_message, state_reasoning


class SessionSnapshotDiffLayer:
    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        session_snapshot = build_session_snapshot(runtime_blocks)
        annotated: list[dict] = []
        previous_snapshot: SessionSnapshotProfile | None = None
        for index in range(len(runtime_blocks)):
            current_snapshot = build_session_snapshot(runtime_blocks[: index + 1])
            diff = compare_session_snapshots(previous_snapshot, current_snapshot)
            annotated.append(
                {
                    **deepcopy(runtime_blocks[index]),
                    **session_snapshot.model_dump(mode="json"),
                    **diff.model_dump(mode="json"),
                }
            )
            previous_snapshot = current_snapshot
        return annotated


def build_session_snapshot(runtime_blocks: list[dict] | None) -> SessionSnapshotProfile:
    blocks = list(runtime_blocks or [])
    if not blocks:
        return SessionSnapshotProfile(
            session_snapshot_state="pedagogically_consistent",
            session_snapshot_summary="Sessao vazia ou neutra para fins de snapshot.",
        )

    retrieval_density = _avg(blocks, "retrieval_density_metric", fallback_key="retrieval_pressure_accumulation")
    scaffold_load = _avg(blocks, "scaffold_load_metric", fallback_key="scaffold_density")
    continuity_smoothness = _avg(blocks, "continuity_smoothness_metric")
    reconstruction_pressure = _avg(blocks, "reconstruction_pressure_metric", fallback_key="reconstruction_fragility")
    compression_safety = _avg(blocks, "compression_safety_metric")
    modulation_overlap = _avg(blocks, "modulation_convergence_metric", fallback_key="modulation_overlap")
    stabilization_sustainability = _avg(blocks, "stabilization_sustainability_metric", fallback_key="stabilization_quality_signal")
    pacing_stability = _avg(blocks, "pacing_stability_metric")
    cognitive_balance = _avg(blocks, "cognitive_balance_metric")
    support_density = _avg(blocks, "support_density")
    adaptive_overlap = _avg(blocks, "adaptive_overlap_signal", fallback_key="signal_overlap_density")
    validation_confidence = _avg(blocks, "validation_confidence", fallback_key="evidence_alignment")

    state = _snapshot_state(
        retrieval_density=retrieval_density,
        scaffold_load=scaffold_load,
        continuity_smoothness=continuity_smoothness,
        compression_safety=compression_safety,
        stabilization_sustainability=stabilization_sustainability,
        cognitive_balance=cognitive_balance,
        adaptive_overlap=adaptive_overlap,
    )

    return SessionSnapshotProfile(
        session_snapshot_state=state,
        session_snapshot_summary=_snapshot_summary(state),
        retrieval_density=round(retrieval_density, 4),
        scaffold_load=round(scaffold_load, 4),
        continuity_smoothness=round(continuity_smoothness, 4),
        reconstruction_pressure=round(reconstruction_pressure, 4),
        compression_safety=round(compression_safety, 4),
        modulation_overlap=round(modulation_overlap, 4),
        stabilization_sustainability=round(stabilization_sustainability, 4),
        pacing_stability=round(pacing_stability, 4),
        cognitive_balance=round(cognitive_balance, 4),
        support_density=round(support_density, 4),
        adaptive_overlap=round(adaptive_overlap, 4),
        validation_confidence=round(validation_confidence, 4),
    )


def compare_session_snapshots(
    previous: SessionSnapshotProfile | None,
    current: SessionSnapshotProfile,
) -> BehavioralDiffProfile:
    if previous is None:
        return BehavioralDiffProfile(
            behavioral_diff_state="behavior_stable",
            behavioral_diff_reasoning=["Primeiro snapshot observado; diff neutro aplicado."],
            convergence_summary="Nao havia snapshot anterior para comparar.",
            divergence_summary="Sem divergencia inicial.",
            runtime_behavior_delta=0.0,
            why_this_behavioral_diff="A comparacao comecou no primeiro ponto observavel da sessao.",
        )

    retrieval_shift = current.retrieval_density - previous.retrieval_density
    scaffold_shift = current.scaffold_load - previous.scaffold_load
    continuity_shift = current.continuity_smoothness - previous.continuity_smoothness
    pacing_shift = current.pacing_stability - previous.pacing_stability
    compression_shift = current.compression_safety - previous.compression_safety
    stabilization_shift = current.stabilization_sustainability - previous.stabilization_sustainability
    overlap_shift = current.adaptive_overlap - previous.adaptive_overlap
    modulation_shift = current.modulation_overlap - previous.modulation_overlap
    validation_shift = current.validation_confidence - previous.validation_confidence

    runtime_behavior_delta = _clamp(
        (
            abs(retrieval_shift)
            + abs(scaffold_shift)
            + abs(continuity_shift)
            + abs(pacing_shift)
            + abs(compression_shift)
            + abs(stabilization_shift)
            + abs(overlap_shift)
            + abs(modulation_shift)
            + abs(validation_shift)
        )
        / 9
    )

    state = _diff_state(
        retrieval_shift=retrieval_shift,
        scaffold_shift=scaffold_shift,
        continuity_shift=continuity_shift,
        compression_shift=compression_shift,
        stabilization_shift=stabilization_shift,
        overlap_shift=overlap_shift,
        runtime_behavior_delta=runtime_behavior_delta,
    )

    return BehavioralDiffProfile(
        behavioral_diff_state=state,
        behavioral_diff_reasoning=state_reasoning(
            "Diff comportamental",
            state,
            [
                f"retrieval={retrieval_shift:.2f}; scaffold={scaffold_shift:.2f}; continuity={continuity_shift:.2f}.",
                f"compression={compression_shift:.2f}; stabilization={stabilization_shift:.2f}; overlap={overlap_shift:.2f}.",
            ],
        ),
        retrieval_shift=round(_clamp(abs(retrieval_shift)), 4),
        scaffold_shift=round(scaffold_shift, 4),
        continuity_shift=round(continuity_shift, 4),
        pacing_shift=round(pacing_shift, 4),
        compression_shift=round(compression_shift, 4),
        stabilization_shift=round(stabilization_shift, 4),
        overlap_shift=round(overlap_shift, 4),
        modulation_shift=round(modulation_shift, 4),
        validation_shift=round(validation_shift, 4),
        convergence_summary=_convergence_summary(state),
        divergence_summary=_divergence_summary(state),
        runtime_behavior_delta=round(runtime_behavior_delta, 4),
        why_this_behavioral_diff=_why_diff(state),
    )


def _avg(blocks: list[dict], key: str, *, fallback_key: str | None = None) -> float:
    values = []
    for block in blocks:
        value = block.get(key)
        if value is None and fallback_key is not None:
            value = block.get(fallback_key, 0.0)
        values.append(_clamp(value))
    return _clamp(sum(values) / max(len(values), 1))


def _snapshot_state(
    *,
    retrieval_density: float,
    scaffold_load: float,
    continuity_smoothness: float,
    compression_safety: float,
    stabilization_sustainability: float,
    cognitive_balance: float,
    adaptive_overlap: float,
) -> str:
    if retrieval_density >= 0.66:
        return "retrieval_heavy"
    if scaffold_load >= 0.62:
        return "support_dense"
    if continuity_smoothness >= 0.72 and cognitive_balance >= 0.66:
        return "pedagogically_consistent"
    if compression_safety >= 0.76 and stabilization_sustainability >= 0.64:
        return "compression_safe"
    if adaptive_overlap >= 0.58:
        return "behaviorally_divergent"
    return "behavior_stable"


def _snapshot_summary(state: str) -> str:
    return state_message(
        state,
        {
            "behavior_stable": "O snapshot atual permaneceu observacionalmente estavel.",
            "retrieval_heavy": "O snapshot atual concentrou mais pressao de retrieval.",
            "support_dense": "O snapshot atual concentrou mais suporte e scaffold.",
            "compression_safe": "O snapshot atual manteve compressao segura e controlada.",
            "pedagogically_consistent": "O snapshot atual parece pedagogicamente consistente e equilibrado.",
            "behaviorally_divergent": "O snapshot atual sugere maior divergencia ou overlap local.",
        },
        "O snapshot atual permaneceu em faixa observacional neutra.",
    )


def _diff_state(
    *,
    retrieval_shift: float,
    scaffold_shift: float,
    continuity_shift: float,
    compression_shift: float,
    stabilization_shift: float,
    overlap_shift: float,
    runtime_behavior_delta: float,
) -> str:
    if retrieval_shift >= 0.08:
        return "retrieval_increased"
    if retrieval_shift <= -0.08:
        return "retrieval_reduced"
    if scaffold_shift >= 0.08:
        return "scaffold_accumulated"
    if scaffold_shift <= -0.08:
        return "scaffold_reduced"
    if continuity_shift >= 0.08:
        return "continuity_improved"
    if continuity_shift <= -0.08:
        return "continuity_fragile"
    if compression_shift >= 0.08:
        return "compression_more_conservative"
    if compression_shift <= -0.08:
        return "compression_more_aggressive"
    if overlap_shift >= 0.08:
        return "overlap_increased"
    if overlap_shift <= -0.08:
        return "overlap_reduced"
    if stabilization_shift >= 0.08:
        return "stabilization_strengthened"
    if stabilization_shift <= -0.08:
        return "stabilization_fragile"
    if runtime_behavior_delta <= 0.04:
        return "behavior_stable"
    if runtime_behavior_delta <= 0.08:
        return "pedagogically_consistent"
    return "behaviorally_divergent"


def _convergence_summary(state: str) -> str:
    return state_message(
        state,
        {
            "behavior_stable": "Os snapshots permaneceram muito proximos na janela observada.",
            "pedagogically_consistent": "Os snapshots seguem convergindo para um perfil parecido.",
            "continuity_improved": "A sessao ganhou continuidade entre os snapshots recentes.",
            "compression_more_conservative": "A sessao passou a privilegiar compressao mais segura.",
            "stabilization_strengthened": "A sustentacao de estabilizacao aumentou entre snapshots.",
        },
        "Nao houve uma convergencia dominante entre os snapshots.",
    )


def _divergence_summary(state: str) -> str:
    return state_message(
        state,
        {
            "retrieval_increased": "O principal desvio recente veio do aumento de retrieval.",
            "retrieval_reduced": "O principal desvio recente veio da reducao de retrieval.",
            "scaffold_accumulated": "O principal desvio recente veio do aculo de scaffold.",
            "scaffold_reduced": "O principal desvio recente veio da reducao de scaffold.",
            "continuity_fragile": "O principal desvio recente veio da perda de continuidade.",
            "compression_more_aggressive": "O principal desvio recente veio de compressao mais agressiva.",
            "overlap_increased": "O principal desvio recente veio do aumento de overlap adaptativo.",
            "overlap_reduced": "O principal desvio recente veio da reducao de overlap adaptativo.",
            "stabilization_fragile": "O principal desvio recente veio da queda de estabilizacao.",
            "behaviorally_divergent": "Os snapshots recentes mostraram mudanca distribuida em varios eixos.",
        },
        "Nao houve divergencia dominante a destacar.",
    )


def _why_diff(state: str) -> str:
    return state_message(
        state,
        {
            "behavior_stable": "As metricas agregadas quase nao se moveram entre os snapshots.",
            "retrieval_increased": "A densidade de retrieval subiu acima da faixa neutra de comparacao.",
            "retrieval_reduced": "A densidade de retrieval caiu de forma perceptivel na comparacao local.",
            "scaffold_accumulated": "A sessao passou a concentrar mais scaffold e suporte local.",
            "scaffold_reduced": "A sessao passou a exigir menos scaffold na comparacao local.",
            "continuity_improved": "A continuidade agregada melhorou entre os snapshots comparados.",
            "continuity_fragile": "A continuidade agregada piorou na comparacao local.",
            "compression_more_conservative": "A sessao ficou mais conservadora em compressao entre snapshots.",
            "compression_more_aggressive": "A sessao ficou mais agressiva em compressao entre snapshots.",
            "overlap_increased": "O overlap adaptativo cresceu acima da faixa neutra de comparacao.",
            "overlap_reduced": "O overlap adaptativo diminuiu na comparacao local.",
            "stabilization_strengthened": "A estabilidade agregada aumentou entre snapshots recentes.",
            "stabilization_fragile": "A estabilidade agregada caiu na comparacao local.",
            "pedagogically_consistent": "As mudancas foram pequenas e coerentes entre os snapshots.",
            "behaviorally_divergent": "Houve drift distribuido em varios eixos observacionais.",
        },
        "O diff veio de uma comparacao curta e puramente observacional.",
    )


def _clamp(value: float | int | None, minimum: float = 0.0, maximum: float = 1.0) -> float:
    return clamp_value(value, minimum, maximum)
