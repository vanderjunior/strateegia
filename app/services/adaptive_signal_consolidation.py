from __future__ import annotations

from collections import Counter

from app.domain.models import AdaptiveSignalConsolidationProfile


def resolve_adaptive_signal_consolidation(
    *,
    pedagogical_mode: str | None,
    micro_intervention: str | None,
    cognitive_trajectory: str | None,
    cognitive_momentum: str | None,
    session_coherence: str | None,
    compression_mode: str | None,
    expression_mode: str | None,
    stabilization_state: str | None,
    retrieval_intensity: str | None,
    cognitive_load_score: float | int | None,
    informational_density: float | int | None,
    explanation_density: float | int | None,
    reconstruction_fragility: float | int | None,
    transfer_fragility: float | int | None,
    longitudinal_retention: float | int | None,
    progression_continuity: float | int | None,
) -> AdaptiveSignalConsolidationProfile:
    pedagogical_mode = str(pedagogical_mode or "")
    micro_intervention = str(micro_intervention or "")
    cognitive_trajectory = str(cognitive_trajectory or "")
    cognitive_momentum = str(cognitive_momentum or "")
    session_coherence = str(session_coherence or "")
    compression_mode = str(compression_mode or "")
    expression_mode = str(expression_mode or "")
    stabilization_state = str(stabilization_state or "")
    retrieval_intensity = str(retrieval_intensity or "")
    cognitive_load_score = _clamp(cognitive_load_score)
    informational_density = _clamp(informational_density)
    explanation_density = _clamp(explanation_density)
    reconstruction_fragility = _clamp(reconstruction_fragility)
    transfer_fragility = _clamp(transfer_fragility)
    longitudinal_retention = _clamp(longitudinal_retention)
    progression_continuity = _clamp(progression_continuity)

    themes = [
        _theme_for_trajectory(cognitive_trajectory),
        _theme_for_momentum(cognitive_momentum),
        _theme_for_coherence(session_coherence),
        _theme_for_compression(compression_mode),
        _theme_for_expression(expression_mode),
        _theme_for_intervention(micro_intervention),
    ]
    themed = [theme for theme in themes if theme != "neutral"]
    theme_counts = Counter(themed)
    dominant_count = max(theme_counts.values(), default=1)
    cognitive_signal_alignment = _clamp(dominant_count / max(len(themed), 1))
    modulation_overlap = _clamp(
        max(0.0, (dominant_count - 1) * 0.24)
        + max(0.0, cognitive_load_score - 0.6) * 0.15
        + max(0.0, informational_density - 0.55) * 0.08
    )

    reconstruction_support_balance = _clamp(
        (0.36 if cognitive_trajectory == "reconstruction_fragile" else 0.0)
        + reconstruction_fragility * 0.34
        + (0.16 if micro_intervention == "guided_reconstruction" else 0.0)
        + (0.14 if compression_mode == "reconstruction_scaffolded" else 0.0)
        + (
            0.12
            if expression_mode in {"focused_reconstruction", "conceptual_clarifier"}
            else 0.0
        )
        + (
            0.08
            if pedagogical_mode in {"guided_explanation", "conceptual_reinforcement"}
            else 0.0
        )
    )

    retrieval_pressure_balance = _clamp(
        {"high": 0.34, "medium": 0.2, "low": 0.04}.get(retrieval_intensity, 0.04)
        + {"retrieval_heavy": 0.24, "pressured": 0.12}.get(cognitive_momentum, 0.0)
        + {"retrieval_transition": 0.12, "pacing_fragile": 0.06}.get(session_coherence, 0.0)
        + {"retrieval_focused": 0.14, "cumulative_lightweight": 0.08}.get(compression_mode, 0.0)
        + (0.12 if expression_mode == "retrieval_softener" else 0.0)
    )

    stabilization_consolidation = _clamp(
        longitudinal_retention * 0.36
        + {
            "resilient": 0.32,
            "consolidated": 0.28,
            "stabilizing": 0.14,
        }.get(stabilization_state, 0.0)
        + {"stable_compressed": 0.16, "cumulative_lightweight": 0.12}.get(compression_mode, 0.0)
        + {
            "stabilization_reassurance": 0.12,
            "concise_reinforcement": 0.08,
            "cumulative_reactivation": 0.08,
        }.get(expression_mode, 0.0)
    )

    reinforcement_convergence = _clamp(
        longitudinal_retention * 0.28
        + {
            "reinforcement_check": 0.1,
            "rapid_review": 0.08,
            "conceptual_reinforcement": 0.06,
        }.get(pedagogical_mode, 0.0)
        + {
            "confidence_check": 0.12,
            "lightweight_retrieval": 0.1,
            "verification_step": 0.06,
        }.get(micro_intervention, 0.0)
        + {
            "stable_compressed": 0.14,
            "reinforcement_condensed": 0.14,
            "cumulative_lightweight": 0.1,
        }.get(compression_mode, 0.0)
        + {
            "stabilization_reassurance": 0.1,
            "concise_reinforcement": 0.08,
            "cumulative_reactivation": 0.08,
        }.get(expression_mode, 0.0)
        - max(reconstruction_fragility, transfer_fragility) * 0.08
    )

    pacing_consolidation = _clamp(
        progression_continuity * 0.32
        + {"balanced": 0.22, "stable": 0.14}.get(cognitive_momentum, 0.0)
        + {
            "stable_progression": 0.18,
            "continuity_stable": 0.16,
            "cumulative_relief": 0.18,
            "contextual_shift_softened": 0.16,
        }.get(session_coherence, 0.0)
        + {
            "transition_smoother": 0.14,
            "pacing_relief": 0.14,
            "retrieval_softener": 0.1,
        }.get(expression_mode, 0.0)
        + {
            "guided_compact": 0.08,
            "stable_compressed": 0.12,
            "retrieval_focused": 0.08,
        }.get(compression_mode, 0.0)
        - max(0.0, cognitive_load_score - 0.7) * 0.12
    )

    state = _resolve_state(
        modulation_overlap=modulation_overlap,
        reinforcement_convergence=reinforcement_convergence,
        retrieval_pressure_balance=retrieval_pressure_balance,
        reconstruction_support_balance=reconstruction_support_balance,
        pacing_consolidation=pacing_consolidation,
        stabilization_consolidation=stabilization_consolidation,
        cognitive_signal_alignment=cognitive_signal_alignment,
        compression_mode=compression_mode,
        progression_continuity=progression_continuity,
    )

    return AdaptiveSignalConsolidationProfile(
        adaptive_signal_state=state,
        consolidation_reasoning=[
            f"Estado consolidado: {state}.",
            f"Sobreposicao modular: {modulation_overlap:.2f}.",
            f"Alinhamento cognitivo local: {cognitive_signal_alignment:.2f}.",
        ],
        modulation_overlap=round(modulation_overlap, 4),
        reinforcement_convergence=round(reinforcement_convergence, 4),
        retrieval_pressure_balance=round(retrieval_pressure_balance, 4),
        reconstruction_support_balance=round(reconstruction_support_balance, 4),
        pacing_consolidation=round(pacing_consolidation, 4),
        stabilization_consolidation=round(stabilization_consolidation, 4),
        cognitive_signal_alignment=round(cognitive_signal_alignment, 4),
        why_this_consolidation_now=_why_now(state),
    )


def _resolve_state(
    *,
    modulation_overlap: float,
    reinforcement_convergence: float,
    retrieval_pressure_balance: float,
    reconstruction_support_balance: float,
    pacing_consolidation: float,
    stabilization_consolidation: float,
    cognitive_signal_alignment: float,
    compression_mode: str,
    progression_continuity: float,
) -> str:
    if reconstruction_support_balance >= 0.64 and modulation_overlap >= 0.42:
        return "reconstruction_pressure"
    if retrieval_pressure_balance >= 0.64:
        return "retrieval_saturation"
    if stabilization_consolidation >= 0.64 and compression_mode in {
        "stable_compressed",
        "cumulative_lightweight",
    }:
        return "compressed_stability"
    if pacing_consolidation >= 0.64 and progression_continuity >= 0.58:
        return "continuity_supported"
    if reinforcement_convergence >= 0.58 and modulation_overlap >= 0.44:
        return "reinforcement_overlap"
    if stabilization_consolidation >= 0.56 and reinforcement_convergence >= 0.48:
        return "stabilization_balanced"
    if cognitive_signal_alignment >= 0.68 and modulation_overlap <= 0.36:
        return "modulation_stable"
    if cognitive_signal_alignment >= 0.52:
        return "support_convergent"
    return "balanced_support"


def _theme_for_trajectory(value: str) -> str:
    if value == "reconstruction_fragile":
        return "reconstruction"
    if value == "transfer_fragile":
        return "continuity"
    if value in {"consolidated", "stabilizing", "superficially_stable"}:
        return "stability"
    return "neutral"


def _theme_for_momentum(value: str) -> str:
    return {
        "retrieval_heavy": "retrieval",
        "pressured": "reconstruction",
        "continuity_fragile": "continuity",
        "conceptually_dense": "reconstruction",
        "balanced": "stability",
        "stable": "stability",
    }.get(value, "neutral")


def _theme_for_coherence(value: str) -> str:
    return {
        "retrieval_transition": "retrieval",
        "reconstruction_cluster": "reconstruction",
        "pacing_fragile": "continuity",
        "stable_progression": "stability",
        "continuity_stable": "continuity",
        "cumulative_relief": "stability",
    }.get(value, "neutral")


def _theme_for_compression(value: str) -> str:
    return {
        "retrieval_focused": "retrieval",
        "reconstruction_scaffolded": "reconstruction",
        "transfer_expanded": "continuity",
        "context_supported": "continuity",
        "stable_compressed": "stability",
        "cumulative_lightweight": "stability",
        "reinforcement_condensed": "stability",
        "prerequisite_supported": "reconstruction",
    }.get(value, "neutral")


def _theme_for_expression(value: str) -> str:
    return {
        "retrieval_softener": "retrieval",
        "focused_reconstruction": "reconstruction",
        "contextual_bridge": "continuity",
        "transition_smoother": "continuity",
        "stabilization_reassurance": "stability",
        "cumulative_reactivation": "stability",
        "concise_reinforcement": "stability",
        "conceptual_clarifier": "reconstruction",
    }.get(value, "neutral")


def _theme_for_intervention(value: str) -> str:
    return {
        "guided_reconstruction": "reconstruction",
        "prerequisite_recall": "reconstruction",
        "lightweight_retrieval": "retrieval",
        "semantic_reactivation": "retrieval",
        "cumulative_bridge": "continuity",
        "contrast_reconciliation": "continuity",
        "confidence_check": "stability",
        "verification_step": "stability",
    }.get(value, "neutral")


def _why_now(state: str) -> str:
    return {
        "balanced_support": "Os sinais ativos ficaram moderados e nao pediram consolidacao mais forte.",
        "reinforcement_overlap": "Camadas proximas ja reforcam o mesmo ponto e a leitura foi consolidada.",
        "reconstruction_pressure": "O suporte reconstrutivo ja convergiu bastante e precisa aparecer de forma harmonizada.",
        "retrieval_saturation": "A pressao de recuperacao ja se acumulou o bastante para pedir consolidacao local.",
        "compressed_stability": "A estabilidade atual permite consolidar compressao e reforco sem ampliar o bloco.",
        "continuity_supported": "A continuidade local ja esta bem sustentada e os sinais foram consolidados.",
        "modulation_stable": "Os sinais ativos convergiram de forma limpa e permaneceram em faixa estavel.",
        "support_convergent": "Ha convergencia suficiente entre camadas para expor um racional unico e mais limpo.",
        "stabilization_balanced": "A consolidacao atual equilibra estabilidade e reforco sem amplificacao desnecessaria.",
    }.get(state, "A consolidacao atual permaneceu em faixa neutra e auditavel.")


def _clamp(value: float | int | None, minimum: float = 0.0, maximum: float = 1.0) -> float:
    if value is None:
        return minimum
    return max(minimum, min(float(value), maximum))
