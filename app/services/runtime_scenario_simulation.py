from __future__ import annotations

from copy import deepcopy
from typing import Any

from app.domain.models import (
    RuntimeScenarioProfile,
    ScenarioExpectation,
    ScenarioReplaySnapshot,
    ScenarioSimulationResult,
)
from app.services.comparative_session_analytics import (
    build_session_signature,
    compare_session_analytics,
)
from app.services.runtime_profile_utils import average_values, clamp_value, state_message, state_reasoning
from app.services.session_export_debug import build_session_export_snapshot


class RuntimeScenarioSimulationLayer:
    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        annotated: list[dict] = []
        for index in range(len(runtime_blocks)):
            current_blocks = runtime_blocks[: index + 1]
            profile = simulate_runtime_scenario(current_blocks)
            payload = profile.model_dump(mode="json")
            annotated.append({**deepcopy(runtime_blocks[index]), **payload})
        return annotated


def build_runtime_scenario_profile(
    category: str | list[dict] | dict[str, Any] | None,
) -> RuntimeScenarioProfile:
    if not isinstance(category, str):
        context = _coerce_source(category)
        inferred_category = "pedagogically_stable"
        if context is not None:
            replay_snapshot = _build_replay_snapshot(context)
            observed_states = _observed_states(context, replay_snapshot)
            inferred_category = _infer_category(replay_snapshot, observed_states)
        category = inferred_category
    expectation = _expectations_for(category)
    return RuntimeScenarioProfile(
        scenario_category=category,
        scenario_expected_states=expectation,
        scenario_notes=_scenario_note(category),
    )


def simulate_runtime_scenario(
    source: list[dict] | dict[str, Any] | None,
    scenario_profile: RuntimeScenarioProfile | None = None,
) -> ScenarioSimulationResult:
    context = _coerce_source(source)
    if context is None:
        return ScenarioSimulationResult(
            runtime_scenario_state="scenario_inconclusive",
            scenario_simulation_reasoning=["Nao havia dados suficientes para replay observacional de cenario."],
            scenario_validation_outcome="scenario_inconclusive",
            scenario_mismatch_reason="Sem blocos ou snapshot valido para simular o cenario.",
            scenario_replay_summary="Replay observacional inconclusivo por falta de dados.",
            why_this_scenario_outcome="A simulacao nao recebeu um contexto observacional utilizavel.",
        )

    replay_snapshot = _build_replay_snapshot(context)
    observed_states = _observed_states(context, replay_snapshot)
    category = scenario_profile.scenario_category if scenario_profile else _infer_category(replay_snapshot, observed_states)
    profile = scenario_profile or build_runtime_scenario_profile(category)
    expected = profile.scenario_expected_states

    alignment, mismatches = _expectation_alignment(expected, observed_states, category)
    regression_signal = str(observed_states.get("pedagogical_regression_signal") or "regression_stable")
    outcome = _outcome(category, alignment, mismatches, regression_signal)

    return ScenarioSimulationResult(
        runtime_scenario_state=outcome,
        scenario_simulation_reasoning=state_reasoning(
            "Simulacao de cenario",
            outcome,
            [
                f"Categoria={category}; alinhamento={alignment:.2f}; regressao={regression_signal}.",
                f"Retrieval={replay_snapshot.retrieval_level:.2f}; scaffold={replay_snapshot.scaffold_level:.2f}; compressao={replay_snapshot.compression_safety:.2f}.",
            ],
        ),
        scenario_category=category,
        scenario_replay_snapshot=replay_snapshot.model_dump(mode="json"),
        scenario_expected_states=expected.model_dump(mode="json"),
        scenario_observed_states=observed_states,
        scenario_expectation_alignment=round(alignment, 4),
        scenario_validation_outcome=outcome,
        scenario_regression_signal=regression_signal,
        scenario_mismatch_reason="; ".join(mismatches) if mismatches else "",
        scenario_replay_summary=_summary(category, outcome, observed_states),
        why_this_scenario_outcome=_why(outcome),
    )


def _coerce_source(source: list[dict] | dict[str, Any] | None) -> dict[str, Any] | None:
    if source is None:
        return None
    if isinstance(source, list):
        if not source:
            return None
        return {"blocks": list(source), "latest": dict(source[-1])}
    if isinstance(source, dict):
        if source.get("session_export_state"):
            return {"snapshot": dict(source), "latest": dict(source)}
        if source:
            return {"blocks": [dict(source)], "latest": dict(source)}
    return None


def _build_replay_snapshot(context: dict[str, Any]) -> ScenarioReplaySnapshot:
    if "blocks" in context:
        blocks = context["blocks"]
        signature = build_session_signature(blocks)
        latest = context["latest"]
        expected_classification = str(latest.get("validation_dataset_state") or "")
        return ScenarioReplaySnapshot(
            retrieval_level=signature.retrieval_level,
            scaffold_level=signature.scaffold_level,
            compression_safety=signature.compression_level,
            reconstruction_pressure=signature.reconstruction_level,
            transfer_stability=clamp_value(latest.get("transfer_stability_signal", 0.5)),
            continuity_level=signature.continuity_level,
            pacing_stability=signature.pacing_level,
            validation_confidence=signature.validation_level,
            sustainability_level=signature.sustainability_level,
            overlap_level=clamp_value(latest.get("adaptive_overlap_signal", 0.0)),
            expected_classification=expected_classification,
        )

    snapshot = build_session_export_snapshot([context["latest"]])
    signature = build_session_signature(snapshot)
    latest = context["latest"]
    return ScenarioReplaySnapshot(
        retrieval_level=signature.retrieval_level,
        scaffold_level=signature.scaffold_level,
        compression_safety=signature.compression_level,
        reconstruction_pressure=signature.reconstruction_level,
        transfer_stability=clamp_value(latest.get("transfer_stability_signal", 0.5)),
        continuity_level=signature.continuity_level,
        pacing_stability=signature.pacing_level,
        validation_confidence=signature.validation_level,
        sustainability_level=signature.sustainability_level,
        overlap_level=clamp_value(latest.get("adaptive_overlap_signal", 0.0)),
        expected_classification=str(latest.get("validation_dataset_state") or ""),
    )


def _observed_states(context: dict[str, Any], replay_snapshot: ScenarioReplaySnapshot) -> dict[str, object]:
    latest = context["latest"]
    comparison = compare_session_analytics(context.get("blocks"), context.get("blocks"))
    derived_regression_signal = _regression_signal_from_snapshot(replay_snapshot, latest)
    explicit_regression_signal = str(latest.get("pedagogical_regression_signal") or "")
    regression_signal = (
        derived_regression_signal
        if explicit_regression_signal in {"", "regression_stable"}
        else explicit_regression_signal
    )
    return {
        "pedagogical_validation_state": str(latest.get("pedagogical_validation_state") or ""),
        "validation_dataset_state": str(latest.get("validation_dataset_state") or _dataset_state_from_snapshot(replay_snapshot)),
        "scientific_validation_state": str(latest.get("scientific_validation_state") or _scientific_state_from_snapshot(replay_snapshot)),
        "comparative_session_state": str(latest.get("comparative_session_state") or comparison.comparative_session_state),
        "pedagogical_regression_signal": regression_signal,
        "risk_flags": _risk_flags(replay_snapshot, latest),
    }


def _infer_category(replay_snapshot: ScenarioReplaySnapshot, observed_states: dict[str, object]) -> str:
    risk_flags = set(observed_states.get("risk_flags") or [])
    if "false_fluency_risk" in risk_flags:
        return "false_fluency_risk"
    if replay_snapshot.continuity_level <= 0.44:
        return "continuity_degraded"
    if replay_snapshot.compression_safety <= 0.46:
        return "compression_risky"
    if replay_snapshot.scaffold_level >= 0.62 and ("scaffold_dependency_risk" in risk_flags or replay_snapshot.scaffold_level >= 0.72):
        return "scaffold_dependent"
    if replay_snapshot.retrieval_level >= 0.7 and observed_states.get("pedagogical_regression_signal") == "retrieval_inflation":
        return "retrieval_inflated_risky"
    if replay_snapshot.retrieval_level >= 0.7:
        return "retrieval_heavy_stable"
    if replay_snapshot.reconstruction_pressure >= 0.62:
        return "reconstruction_fragile"
    if replay_snapshot.transfer_stability <= 0.44:
        return "transfer_fragile"
    if replay_snapshot.pacing_stability <= 0.44:
        return "pacing_unstable"
    if "resurfacing_inconclusive" in risk_flags:
        return "resurfacing_inconclusive"
    if (
        observed_states.get("validation_dataset_state") == "validation_ready"
        and observed_states.get("scientific_validation_state") == "validation_stable"
        and observed_states.get("comparative_session_state") == "behavior_consistent"
    ):
        return "pedagogically_stable"
    if replay_snapshot.continuity_level >= 0.68:
        return "continuity_stable"
    if replay_snapshot.pacing_stability >= 0.68:
        return "pacing_stable"
    if replay_snapshot.scaffold_level <= 0.42:
        return "scaffold_safe"
    if replay_snapshot.compression_safety >= 0.72:
        return "compression_safe"
    if observed_states.get("comparative_session_state") == "behaviorally_divergent":
        return "behaviorally_divergent"
    if "resurfacing_effective" in risk_flags:
        return "resurfacing_effective"
    return "pedagogically_stable"


def _expectations_for(category: str) -> ScenarioExpectation:
    mapping = {
        "retrieval_heavy_stable": ScenarioExpectation(
            expected_dataset_awareness_state="retrieval_intensive",
            expected_scientific_validation_state="validation_stable",
            expected_comparative_state="behavior_consistent",
            expected_regression_signal="regression_stable",
            expected_risk_flags=["retrieval_high"],
        ),
        "retrieval_inflated_risky": ScenarioExpectation(
            expected_dataset_awareness_state="retrieval_intensive",
            expected_scientific_validation_state="regression_watch",
            expected_regression_signal="retrieval_inflation",
            expected_risk_flags=["retrieval_high", "regression_risk"],
        ),
        "scaffold_dependent": ScenarioExpectation(
            expected_dataset_awareness_state="scaffold_sensitive",
            expected_scientific_validation_state="sustainability_watch",
            expected_regression_signal="support_dependency_risk",
            expected_risk_flags=["scaffold_dependency_risk"],
        ),
        "scaffold_safe": ScenarioExpectation(
            expected_scientific_validation_state="validation_stable",
            expected_regression_signal="regression_stable",
        ),
        "compression_safe": ScenarioExpectation(
            expected_scientific_validation_state="validation_stable",
            expected_regression_signal="regression_stable",
        ),
        "compression_risky": ScenarioExpectation(
            expected_scientific_validation_state="regression_watch",
            expected_risk_flags=["compression_risk"],
        ),
        "reconstruction_fragile": ScenarioExpectation(
            expected_dataset_awareness_state="reconstruction_heavy",
            expected_scientific_validation_state="sustainability_watch",
            expected_risk_flags=["reconstruction_fragile"],
        ),
        "reconstruction_recovering": ScenarioExpectation(
            expected_scientific_validation_state="validation_stable",
        ),
        "transfer_fragile": ScenarioExpectation(
            expected_dataset_awareness_state="transfer_fragile",
            expected_risk_flags=["transfer_fragile"],
        ),
        "continuity_degraded": ScenarioExpectation(
            expected_dataset_awareness_state="continuity_fragile",
            expected_scientific_validation_state="regression_watch",
            expected_risk_flags=["continuity_fragile"],
        ),
        "continuity_stable": ScenarioExpectation(
            expected_scientific_validation_state="validation_stable",
        ),
        "pacing_unstable": ScenarioExpectation(
            expected_dataset_awareness_state="pacing_sensitive",
            expected_risk_flags=["pacing_unstable"],
        ),
        "pacing_stable": ScenarioExpectation(),
        "resurfacing_effective": ScenarioExpectation(
            expected_risk_flags=["resurfacing_effective"],
        ),
        "resurfacing_inconclusive": ScenarioExpectation(
            expected_risk_flags=["resurfacing_inconclusive"],
        ),
        "false_fluency_risk": ScenarioExpectation(
            expected_scientific_validation_state="sustainability_watch",
            expected_risk_flags=["false_fluency_risk"],
        ),
        "behaviorally_divergent": ScenarioExpectation(
            expected_comparative_state="behaviorally_divergent",
        ),
        "pedagogically_stable": ScenarioExpectation(
            expected_dataset_awareness_state="validation_ready",
            expected_scientific_validation_state="validation_stable",
            expected_comparative_state="behavior_consistent",
            expected_regression_signal="regression_stable",
        ),
    }
    return mapping.get(category, ScenarioExpectation())


def _scenario_note(category: str) -> str:
    return state_message(
        category,
        {
            "retrieval_heavy_stable": "Cenario com retrieval alto, mas ainda observacionalmente estavel.",
            "retrieval_inflated_risky": "Cenario com retrieval elevado e risco regressivo associado.",
            "scaffold_dependent": "Cenario com dependencia aparente de scaffold e suporte.",
            "compression_risky": "Cenario com compressao possivelmente agressiva demais.",
            "reconstruction_fragile": "Cenario com pressao reconstrutiva fragilizada.",
            "false_fluency_risk": "Cenario com risco de fluencia superficial.",
            "continuity_degraded": "Cenario com degradacao clara de continuidade.",
            "pedagogically_stable": "Cenario baseline pedagogicamente estavel.",
        },
        "Cenario observacional controlado para validacao.",
    )


def _expectation_alignment(
    expected: ScenarioExpectation,
    observed: dict[str, object],
    category: str,
) -> tuple[float, list[str]]:
    checks: list[bool] = []
    mismatches: list[str] = []

    observed_category = _infer_category_from_observed(observed)
    checks.append(observed_category == category)
    if observed_category != category:
        mismatches.append(f"categoria observada={observed_category}")

    expected_pairs = {
        "expected_validation_state": "pedagogical_validation_state",
        "expected_dataset_awareness_state": "validation_dataset_state",
        "expected_scientific_validation_state": "scientific_validation_state",
        "expected_comparative_state": "comparative_session_state",
        "expected_regression_signal": "pedagogical_regression_signal",
    }
    for expected_key, observed_key in expected_pairs.items():
        expected_value = getattr(expected, expected_key)
        if not expected_value:
            continue
        checks.append(str(observed.get(observed_key) or "") == expected_value)
        if str(observed.get(observed_key) or "") != expected_value:
            mismatches.append(f"{observed_key}={observed.get(observed_key) or ''}")

    expected_flags = set(expected.expected_risk_flags)
    if expected_flags:
        observed_flags = set(observed.get("risk_flags") or [])
        flag_match = expected_flags.issubset(observed_flags)
        checks.append(flag_match)
        if not flag_match:
            mismatches.append(f"risk_flags={sorted(observed_flags)}")

    if not checks:
        return 0.0, ["sem expectativas comparaveis"]
    return average_values([1.0 if matched else 0.0 for matched in checks]), mismatches


def _outcome(
    category: str,
    alignment: float,
    mismatches: list[str],
    regression_signal: str,
) -> str:
    if alignment == 0.0 and mismatches == ["sem expectativas comparaveis"]:
        return "scenario_inconclusive"
    if regression_signal != "regression_stable" and category in {"retrieval_inflated_risky", "scaffold_dependent", "compression_risky"}:
        return "regression_detected"
    if alignment >= 0.999:
        return "scenario_passed"
    if alignment >= 0.6:
        return "expectation_partially_matched"
    if mismatches:
        return "classification_mismatch"
    return "scenario_failed"


def _summary(category: str, outcome: str, observed_states: dict[str, object]) -> str:
    if outcome == "scenario_passed":
        return state_message(
            category,
            {
                "retrieval_heavy_stable": "Scenario matched retrieval-heavy behavior without regression risk.",
                "scaffold_dependent": "Scenario matched scaffold dependency with expected support pressure.",
                "compression_risky": "Compression-risk scenario produced the expected risky profile.",
                "reconstruction_fragile": "Reconstruction-fragile scenario produced the expected fragile pressure.",
                "false_fluency_risk": "False-fluency scenario produced the expected warning profile.",
                "continuity_degraded": "Continuity-degraded scenario produced the expected fragile continuity profile.",
                "pedagogically_stable": "Stable baseline scenario matched the expected balanced behavior.",
            },
            "Scenario matched the expected observational profile.",
        )
    if outcome == "regression_detected":
        return f"Scenario exposed regression-sensitive behavior: {observed_states.get('pedagogical_regression_signal') or 'regressao observada'}."
    if outcome == "classification_mismatch":
        return "Scenario did not match the expected classification profile."
    if outcome == "scenario_inconclusive":
        return "Scenario remained inconclusive because the observational context was incomplete."
    return "Scenario matched only part of the expected observational profile."


def _why(outcome: str) -> str:
    return state_message(
        outcome,
        {
            "scenario_passed": "Os estados observados convergiram com as expectativas do cenario.",
            "regression_detected": "O cenario foi desenhado para risco e os sinais regressivos apareceram.",
            "expectation_partially_matched": "Parte das expectativas foi observada, mas houve desalinhamentos locais.",
            "classification_mismatch": "A classificacao observada nao convergiu com o cenario esperado.",
            "scenario_inconclusive": "Os dados observacionais nao bastaram para validar o cenario.",
            "scenario_failed": "As expectativas centrais do cenario nao foram reproduzidas.",
        },
        "O resultado permaneceu observacionalmente neutro.",
    )


def _dataset_state_from_snapshot(replay_snapshot: ScenarioReplaySnapshot) -> str:
    if replay_snapshot.retrieval_level >= 0.7:
        return "retrieval_intensive"
    if replay_snapshot.scaffold_level >= 0.62:
        return "scaffold_sensitive"
    if replay_snapshot.continuity_level <= 0.44:
        return "continuity_fragile"
    if replay_snapshot.reconstruction_pressure >= 0.62:
        return "reconstruction_heavy"
    if replay_snapshot.pacing_stability <= 0.44:
        return "pacing_sensitive"
    if replay_snapshot.transfer_stability <= 0.44:
        return "transfer_fragile"
    return "validation_ready"


def _scientific_state_from_snapshot(replay_snapshot: ScenarioReplaySnapshot) -> str:
    if replay_snapshot.compression_safety <= 0.46 or replay_snapshot.continuity_level <= 0.44:
        return "regression_watch"
    if replay_snapshot.scaffold_level >= 0.62 or replay_snapshot.reconstruction_pressure >= 0.62:
        return "sustainability_watch"
    return "validation_stable"


def _regression_signal_from_snapshot(replay_snapshot: ScenarioReplaySnapshot, latest: dict[str, Any]) -> str:
    if replay_snapshot.retrieval_level >= 0.78 and replay_snapshot.scaffold_level >= 0.68:
        return "retrieval_inflation"
    if replay_snapshot.scaffold_level >= 0.62 and clamp_value(latest.get("scaffold_dependency_signal", 0.0)) >= 0.58:
        return "support_dependency_risk"
    if replay_snapshot.compression_safety <= 0.46:
        return "compression_risk"
    if replay_snapshot.continuity_level <= 0.44:
        return "continuity_fragility"
    return "regression_stable"


def _risk_flags(replay_snapshot: ScenarioReplaySnapshot, latest: dict[str, Any]) -> list[str]:
    flags: list[str] = []
    if replay_snapshot.retrieval_level >= 0.7:
        flags.append("retrieval_high")
    if clamp_value(latest.get("scaffold_dependency_signal", 0.0)) >= 0.58 or replay_snapshot.scaffold_level >= 0.68:
        flags.append("scaffold_dependency_risk")
    if replay_snapshot.compression_safety <= 0.46:
        flags.append("compression_risk")
    if replay_snapshot.reconstruction_pressure >= 0.62:
        flags.append("reconstruction_fragile")
    if replay_snapshot.transfer_stability <= 0.44:
        flags.append("transfer_fragile")
    if replay_snapshot.continuity_level <= 0.44:
        flags.append("continuity_fragile")
    if replay_snapshot.pacing_stability <= 0.44:
        flags.append("pacing_unstable")
    resurfacing = clamp_value(latest.get("resurfacing_effectiveness_signal", 0.5))
    if resurfacing >= 0.62:
        flags.append("resurfacing_effective")
    elif resurfacing <= 0.44:
        flags.append("resurfacing_inconclusive")
    if clamp_value(latest.get("false_fluency_risk", 0.0)) >= 0.58:
        flags.append("false_fluency_risk")
    if str(latest.get("pedagogical_regression_signal") or "") not in {"", "regression_stable"}:
        flags.append("regression_risk")
    return flags


def _infer_category_from_observed(observed: dict[str, object]) -> str:
    dataset = str(observed.get("validation_dataset_state") or "")
    scientific = str(observed.get("scientific_validation_state") or "")
    regression = str(observed.get("pedagogical_regression_signal") or "")
    risk_flags = set(observed.get("risk_flags") or [])
    if "false_fluency_risk" in risk_flags:
        return "false_fluency_risk"
    if dataset == "continuity_fragile":
        return "continuity_degraded"
    if dataset == "reconstruction_heavy":
        return "reconstruction_fragile"
    if dataset == "transfer_fragile":
        return "transfer_fragile"
    if dataset == "pacing_sensitive":
        return "pacing_unstable"
    if dataset == "scaffold_sensitive":
        return "scaffold_dependent"
    if dataset == "retrieval_intensive" and regression == "regression_stable":
        return "retrieval_heavy_stable"
    if dataset == "retrieval_intensive":
        return "retrieval_inflated_risky"
    if "compression_risk" in risk_flags:
        return "compression_risky"
    if scientific == "validation_stable":
        return "pedagogically_stable"
    return "pedagogically_stable"
