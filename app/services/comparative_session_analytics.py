from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.domain.models import (
    ComparativeRuntimeSummary,
    ComparativeSessionAnalyticsProfile,
    PedagogicalRegressionSignal,
    SessionComparisonProfile,
    SessionExportSnapshot,
)
from app.services.runtime_profile_utils import average_values, clamp_value, state_message, state_reasoning
from app.services.session_export_debug import build_session_export_snapshot


class ComparativeSessionAnalyticsLayer:
    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        annotated: list[dict] = []
        previous_blocks: list[dict] | None = None
        for index in range(len(runtime_blocks)):
            current_blocks = runtime_blocks[: index + 1]
            profile = compare_session_analytics(previous_blocks, current_blocks)
            payload = profile.model_dump(mode="json")
            annotated.append({**deepcopy(runtime_blocks[index]), **payload})
            previous_blocks = current_blocks
        return annotated


def build_session_signature(source: list[dict] | SessionExportSnapshot | dict[str, Any] | None) -> ComparativeRuntimeSummary:
    snapshot = _coerce_export_snapshot(source)
    if snapshot is None:
        return ComparativeRuntimeSummary()

    stability = snapshot.stability_snapshot or {}
    compression = snapshot.compression_snapshot or {}
    continuity = snapshot.continuity_snapshot or {}
    support = snapshot.support_snapshot or {}
    retrieval = snapshot.retrieval_snapshot or {}
    reconstruction = snapshot.reconstruction_snapshot or {}
    validation = snapshot.validation_snapshot or {}

    return ComparativeRuntimeSummary(
        retrieval_level=clamp_value(retrieval.get("density", 0.0)),
        scaffold_level=clamp_value(support.get("scaffold_load", 0.0)),
        compression_level=clamp_value(compression.get("compression_safety_metric", 0.0)),
        continuity_level=clamp_value(continuity.get("continuity_smoothness", 0.0)),
        pacing_level=clamp_value(stability.get("pacing_stability", 0.0)),
        reconstruction_level=clamp_value(reconstruction.get("pressure", 0.0)),
        validation_level=clamp_value(validation.get("validation_confidence", 0.0)),
        sustainability_level=clamp_value(stability.get("stabilization_sustainability", 0.0)),
        balance_level=clamp_value(stability.get("cognitive_balance", 0.0)),
    )


def compare_session_analytics(
    baseline: list[dict] | SessionExportSnapshot | dict[str, Any] | None,
    candidate: list[dict] | SessionExportSnapshot | dict[str, Any] | None,
) -> ComparativeSessionAnalyticsProfile:
    candidate_snapshot = _coerce_export_snapshot(candidate)
    if candidate_snapshot is None:
        return ComparativeSessionAnalyticsProfile(
            comparative_session_state="comparison_inconclusive",
            comparative_session_reasoning=["Nao havia sessao candidata suficiente para comparacao."],
            comparative_runtime_summary="Sem sessao candidata comparavel.",
            why_this_comparison_state="A comparacao nao recebeu uma sessao candidata utilizavel.",
        )

    baseline_snapshot = _coerce_export_snapshot(baseline)
    candidate_signature = build_session_signature(candidate_snapshot)
    if baseline_snapshot is None:
        return ComparativeSessionAnalyticsProfile(
            comparative_session_state="comparison_inconclusive",
            comparative_session_reasoning=["Nao havia baseline observavel; comparacao inicial ficou inconclusiva."],
            comparative_runtime_summary="Comparacao inicial sem baseline comparavel.",
            session_comparison_profile=SessionComparisonProfile(
                baseline_session_signature=ComparativeRuntimeSummary(),
                candidate_session_signature=candidate_signature,
                comparison_context=_comparison_context(None, candidate_snapshot),
            ),
            baseline_session_signature=ComparativeRuntimeSummary().model_dump(mode="json"),
            candidate_session_signature=candidate_signature.model_dump(mode="json"),
            comparative_validation_alignment=_comparative_validation_alignment(None, candidate_snapshot),
            why_this_comparison_state="O baseline nao estava disponivel, entao a comparacao permaneceu descritiva.",
        )

    baseline_signature = build_session_signature(baseline_snapshot)
    deltas = _deltas(baseline_signature, candidate_signature)
    regression = _regression_signal(baseline_snapshot, candidate_snapshot, deltas)
    comparative_validation_alignment = _comparative_validation_alignment(baseline_snapshot, candidate_snapshot)
    state = _state(deltas, regression, comparative_validation_alignment)

    return ComparativeSessionAnalyticsProfile(
        comparative_session_state=state,
        comparative_session_reasoning=state_reasoning(
            "Comparacao de sessao",
            state,
            [
                f"retrieval={deltas['retrieval_delta']:.2f}; scaffold={deltas['scaffold_delta']:.2f}; compressao={deltas['compression_delta']:.2f}.",
                f"continuidade={deltas['continuity_delta']:.2f}; pacing={deltas['pacing_delta']:.2f}; validacao={deltas['validation_delta']:.2f}.",
            ],
        ),
        comparative_runtime_summary=_summary(state, deltas),
        session_comparison_profile=SessionComparisonProfile(
            baseline_session_signature=baseline_signature,
            candidate_session_signature=candidate_signature,
            comparison_context=_comparison_context(baseline_snapshot, candidate_snapshot),
        ),
        baseline_session_signature=baseline_signature.model_dump(mode="json"),
        candidate_session_signature=candidate_signature.model_dump(mode="json"),
        retrieval_delta=round(deltas["retrieval_delta"], 4),
        scaffold_delta=round(deltas["scaffold_delta"], 4),
        compression_delta=round(deltas["compression_delta"], 4),
        continuity_delta=round(deltas["continuity_delta"], 4),
        reconstruction_delta=round(deltas["reconstruction_delta"], 4),
        pacing_delta=round(deltas["pacing_delta"], 4),
        validation_delta=round(deltas["validation_delta"], 4),
        sustainability_delta=round(deltas["sustainability_delta"], 4),
        behavioral_drift_signal=round(regression.behavioral_drift_signal, 4),
        pedagogical_regression_signal=regression.pedagogical_regression_signal,
        comparative_validation_alignment=round(comparative_validation_alignment, 4),
        why_this_comparison_state=_why(state),
    )


def _coerce_export_snapshot(
    source: list[dict] | SessionExportSnapshot | dict[str, Any] | None,
) -> SessionExportSnapshot | None:
    if source is None:
        return None
    if isinstance(source, SessionExportSnapshot):
        return source
    if isinstance(source, list):
        if not source:
            return None
        return build_session_export_snapshot(source)
    if isinstance(source, dict) and "session_export_state" in source:
        return SessionExportSnapshot.model_validate(source)
    return None


def _deltas(
    baseline: ComparativeRuntimeSummary,
    candidate: ComparativeRuntimeSummary,
) -> dict[str, float]:
    return {
        "retrieval_delta": candidate.retrieval_level - baseline.retrieval_level,
        "scaffold_delta": candidate.scaffold_level - baseline.scaffold_level,
        "compression_delta": candidate.compression_level - baseline.compression_level,
        "continuity_delta": candidate.continuity_level - baseline.continuity_level,
        "reconstruction_delta": candidate.reconstruction_level - baseline.reconstruction_level,
        "pacing_delta": candidate.pacing_level - baseline.pacing_level,
        "validation_delta": candidate.validation_level - baseline.validation_level,
        "sustainability_delta": candidate.sustainability_level - baseline.sustainability_level,
        "balance_delta": candidate.balance_level - baseline.balance_level,
    }


def _regression_signal(
    baseline: SessionExportSnapshot,
    candidate: SessionExportSnapshot,
    deltas: dict[str, float],
) -> PedagogicalRegressionSignal:
    baseline_validation = baseline.validation_snapshot or {}
    candidate_validation = candidate.validation_snapshot or {}
    baseline_support = baseline.support_snapshot or {}
    candidate_support = candidate.support_snapshot or {}
    candidate_stability = candidate.stability_snapshot or {}
    baseline_stability = baseline.stability_snapshot or {}

    retrieval_inflation_risk = clamp_value(max(0.0, deltas["retrieval_delta"]) + clamp_value(candidate.retrieval_snapshot.get("density", 0.0)) * 0.2)
    scaffold_dependency_delta = deltas["scaffold_delta"] + clamp_value(candidate_support.get("support_density", 0.0)) * 0.12
    compression_safety_delta = deltas["compression_delta"]
    continuity_degradation_delta = max(0.0, -deltas["continuity_delta"])
    reconstruction_pressure_delta = max(0.0, deltas["reconstruction_delta"])
    pacing_instability_delta = max(0.0, -deltas["pacing_delta"])
    validation_confidence_delta = deltas["validation_delta"]
    sustainability_delta = deltas["sustainability_delta"]
    behavioral_drift_signal = average_values(
        [
            abs(deltas["retrieval_delta"]),
            abs(deltas["scaffold_delta"]),
            abs(deltas["compression_delta"]),
            abs(deltas["continuity_delta"]),
            abs(deltas["reconstruction_delta"]),
            abs(deltas["pacing_delta"]),
            abs(deltas["validation_delta"]),
            abs(deltas["sustainability_delta"]),
            clamp_value(candidate.behavioral_diff_snapshot.get("delta", candidate.runtime_trace_snapshot.get("trace_alignment", 0.0))),
        ]
    )

    regression_state = "regression_stable"
    if retrieval_inflation_risk >= 0.16 or str(candidate_validation.get("pedagogical_validation_state") or "") == "retrieval_saturated":
        regression_state = "retrieval_inflation"
    elif scaffold_dependency_delta >= 0.12 and reconstruction_pressure_delta >= 0.08:
        regression_state = "support_overextended"
    elif compression_safety_delta <= -0.08:
        regression_state = "compression_drift"
    elif continuity_degradation_delta >= 0.08:
        regression_state = "continuity_degrading"
    elif behavioral_drift_signal >= 0.12 or candidate_stability.get("cognitive_balance", 0.5) < baseline_stability.get("cognitive_balance", 0.5) - 0.1:
        regression_state = "behavioral_drift"

    return PedagogicalRegressionSignal(
        retrieval_inflation_risk=round(clamp_value(retrieval_inflation_risk), 4),
        scaffold_dependency_delta=round(scaffold_dependency_delta, 4),
        compression_safety_delta=round(compression_safety_delta, 4),
        continuity_degradation_delta=round(continuity_degradation_delta, 4),
        reconstruction_pressure_delta=round(reconstruction_pressure_delta, 4),
        pacing_instability_delta=round(pacing_instability_delta, 4),
        validation_confidence_delta=round(validation_confidence_delta, 4),
        sustainability_delta=round(sustainability_delta, 4),
        behavioral_drift_signal=round(behavioral_drift_signal, 4),
        pedagogical_regression_signal=regression_state,
    )


def _comparative_validation_alignment(
    baseline: SessionExportSnapshot | None,
    candidate: SessionExportSnapshot,
) -> float:
    candidate_context = str(candidate.validation_snapshot.get("validation_harness_state", ""))
    candidate_state = str(candidate.behavioral_diff_snapshot.get("state", ""))
    candidate_confidence = clamp_value(candidate.validation_snapshot.get("validation_confidence", 0.0))
    if baseline is None:
        return average_values([candidate_confidence, 0.5])
    baseline_context = str(baseline.validation_snapshot.get("validation_harness_state", ""))
    baseline_state = str(baseline.behavioral_diff_snapshot.get("state", ""))
    context_match = 1.0 if candidate_context == baseline_context else 0.5
    state_match = 1.0 if candidate_state == baseline_state else 0.55
    return average_values(
        [
            context_match,
            state_match,
            1.0 - abs(clamp_value(candidate.validation_snapshot.get("validation_confidence", 0.0)) - clamp_value(baseline.validation_snapshot.get("validation_confidence", 0.0))),
            clamp_value(candidate.validation_snapshot.get("validation_confidence", 0.0)),
        ]
    )


def _state(
    deltas: dict[str, float],
    regression: PedagogicalRegressionSignal,
    comparative_validation_alignment: float,
) -> str:
    if regression.pedagogical_regression_signal in {"support_overextended", "behavioral_drift"}:
        return "pedagogical_regression_risk"
    if (
        regression.pedagogical_regression_signal == "retrieval_inflation"
        and (
            deltas["scaffold_delta"] >= 0.08
            or deltas["reconstruction_delta"] >= 0.08
            or regression.behavioral_drift_signal >= 0.14
        )
    ):
        return "pedagogical_regression_risk"
    if (
        regression.pedagogical_regression_signal in {"compression_drift", "continuity_degrading"}
        and regression.behavioral_drift_signal >= 0.14
    ):
        return "pedagogical_regression_risk"
    if deltas["retrieval_delta"] >= 0.08:
        return "retrieval_increased"
    if deltas["retrieval_delta"] <= -0.08:
        return "retrieval_reduced"
    if deltas["scaffold_delta"] >= 0.08:
        return "scaffold_increased"
    if deltas["scaffold_delta"] <= -0.08:
        return "scaffold_reduced"
    if deltas["compression_delta"] >= 0.08:
        return "compression_safer"
    if deltas["compression_delta"] <= -0.08:
        return "compression_riskier"
    if deltas["continuity_delta"] >= 0.08:
        return "continuity_improved"
    if deltas["continuity_delta"] <= -0.08:
        return "continuity_degraded"
    if deltas["reconstruction_delta"] >= 0.08:
        return "reconstruction_pressure_increased"
    if deltas["pacing_delta"] >= 0.08:
        return "pacing_stabilized"
    if deltas["pacing_delta"] <= -0.08:
        return "pacing_degraded"
    if deltas["validation_delta"] >= 0.08:
        return "validation_improved"
    if deltas["validation_delta"] <= -0.08:
        return "validation_weakened"
    if deltas["sustainability_delta"] >= 0.08:
        return "sustainability_improved"
    if deltas["sustainability_delta"] <= -0.08:
        return "sustainability_degraded"
    if regression.behavioral_drift_signal >= 0.12:
        return "behaviorally_divergent"
    if comparative_validation_alignment <= 0.46:
        return "comparison_inconclusive"
    return "behavior_consistent"


def _summary(state: str, deltas: dict[str, float]) -> str:
    mapping = {
        "behavior_consistent": "O comportamento permaneceu estavel entre as sessoes comparadas.",
        "retrieval_increased": "A densidade de retrieval aumentou na sessao candidata.",
        "retrieval_reduced": "A densidade de retrieval diminuiu na sessao candidata.",
        "scaffold_increased": "A carga de scaffold aumentou na sessao candidata.",
        "scaffold_reduced": "A carga de scaffold diminuiu na sessao candidata.",
        "compression_safer": "A compressao ficou mais conservadora e segura na sessao candidata.",
        "compression_riskier": "A compressao ficou mais agressiva ou menos segura na sessao candidata.",
        "continuity_improved": "A continuidade melhorou na sessao candidata.",
        "continuity_degraded": "A continuidade ficou mais fragil na sessao candidata.",
        "reconstruction_pressure_increased": "A pressao reconstrutiva aumentou na sessao candidata.",
        "pacing_stabilized": "O pacing ficou mais estavel na sessao candidata.",
        "pacing_degraded": "O pacing ficou menos estavel na sessao candidata.",
        "validation_improved": "A confianca de validacao melhorou na sessao candidata.",
        "validation_weakened": "A confianca de validacao enfraqueceu na sessao candidata.",
        "sustainability_improved": "A sustentabilidade observacional melhorou na sessao candidata.",
        "sustainability_degraded": "A sustentabilidade observacional piorou na sessao candidata.",
        "pedagogical_regression_risk": "A comparacao sugere risco de regressao pedagogica observavel.",
        "behaviorally_divergent": "As sessoes comparadas exibem drift comportamental relevante.",
        "comparison_inconclusive": "A comparacao nao ficou suficientemente alinhada para conclusao forte.",
    }
    if state in mapping:
        return mapping[state]
    return (
        f"Comparacao observacional: retrieval={deltas['retrieval_delta']:.2f}, "
        f"scaffold={deltas['scaffold_delta']:.2f}, continuidade={deltas['continuity_delta']:.2f}."
    )


def _comparison_context(
    baseline: SessionExportSnapshot | None,
    candidate: SessionExportSnapshot,
) -> str:
    candidate_context = str(candidate.validation_snapshot.get("validation_harness_state", ""))
    candidate_state = str(candidate.behavioral_diff_snapshot.get("state", ""))
    if baseline is None:
        return f"baseline=inexistente; candidate={candidate_context or 'neutro'}; diff={candidate_state or 'neutro'}"
    baseline_context = str(baseline.validation_snapshot.get("validation_harness_state", ""))
    return f"baseline={baseline_context or 'neutro'}; candidate={candidate_context or 'neutro'}; diff={candidate_state or 'neutro'}"


def _why(state: str) -> str:
    return state_message(
        state,
        {
            "behavior_consistent": "As assinaturas de sessao permaneceram proximas e alinhadas.",
            "retrieval_increased": "A assinatura candidata concentrou mais retrieval do que a baseline.",
            "retrieval_reduced": "A assinatura candidata reduziu a presenca relativa de retrieval.",
            "scaffold_increased": "A assinatura candidata mostrou mais scaffold e suporte agregado.",
            "scaffold_reduced": "A assinatura candidata mostrou menos scaffold e suporte agregado.",
            "compression_safer": "A assinatura candidata preservou mais seguranca de compressao.",
            "compression_riskier": "A assinatura candidata reduziu a seguranca de compressao.",
            "continuity_improved": "A assinatura candidata melhorou a continuidade agregada.",
            "continuity_degraded": "A assinatura candidata perdeu continuidade agregada.",
            "reconstruction_pressure_increased": "A assinatura candidata elevou a pressao de reconstrucao.",
            "pacing_stabilized": "A assinatura candidata estabilizou melhor o pacing.",
            "pacing_degraded": "A assinatura candidata degradou a estabilidade de pacing.",
            "validation_improved": "A assinatura candidata aumentou a confianca de validacao.",
            "validation_weakened": "A assinatura candidata reduziu a confianca de validacao.",
            "sustainability_improved": "A assinatura candidata reforcou a sustentabilidade observacional.",
            "sustainability_degraded": "A assinatura candidata perdeu sustentabilidade observacional.",
            "pedagogical_regression_risk": "A comparacao encontrou drift ou inflacao suficiente para risco regressivo.",
            "behaviorally_divergent": "A comparacao encontrou drift agregado acima da faixa estavel.",
            "comparison_inconclusive": "O alinhamento comparativo ficou insuficiente para conclusao mais forte.",
        },
        "A comparacao permaneceu em faixa observacional neutra.",
    )
