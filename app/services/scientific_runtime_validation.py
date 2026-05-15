from __future__ import annotations

from copy import deepcopy

from app.domain.models import ScientificRuntimeValidationProfile
from app.services.runtime_profile_utils import average_values, clamp_value, state_message, state_reasoning


class ScientificRuntimeValidationLayer:
    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        profile = resolve_scientific_runtime_validation(runtime_blocks)
        payload = profile.model_dump(mode="json")
        return [{**deepcopy(block), **payload} for block in runtime_blocks]


def resolve_scientific_runtime_validation(
    runtime_blocks: list[dict] | None,
) -> ScientificRuntimeValidationProfile:
    blocks = list(runtime_blocks or [])
    if not blocks:
        return ScientificRuntimeValidationProfile(
            scientific_validation_state="validation_stable",
            scientific_validation_reasoning=["Nao havia blocos suficientes para perfil cientifico comparativo."],
            runtime_benchmark_state="benchmark_watch",
            regression_detection_state="regression_stable",
            sustainability_validation_state="sustainability_supported",
            cognitive_load_profile="load_balanced",
            retrieval_reliability_profile="retrieval_reliable",
            scaffold_dependency_profile="scaffold_controlled",
            compression_safety_profile="compression_safe",
            overlap_inflation_profile="overlap_controlled",
            stabilization_reliability_profile="stabilization_reliable",
            continuity_reliability_profile="continuity_reliable",
            reinforcement_redundancy_profile="reinforcement_balanced",
            pedagogical_regression_summary="Sem dados suficientes para regressao observacional.",
            runtime_benchmark_summary="Sem blocos suficientes para readiness de benchmark.",
            empirical_validation_context="Sessao vazia ou neutra para validacao cientifica.",
            comparative_runtime_alignment=0.5,
            reproducibility_summary="Contexto neutro e reproduzivel por ausencia de blocos.",
            why_this_validation_profile="A camada recebeu uma sessao vazia e preservou um estado observacional neutro.",
        )

    retrieval_inflation = _retrieval_inflation(blocks)
    scaffold_dependency = _scaffold_dependency(blocks)
    compression_risk = _compression_risk(blocks)
    reconstruction_fragility = _reconstruction_fragility(blocks)
    continuity_risk = _continuity_risk(blocks)
    overlap_inflation = _overlap_inflation(blocks)
    pacing_instability = _pacing_instability(blocks)
    stabilization_reliability = _stabilization_reliability(blocks)
    reinforcement_redundancy = _reinforcement_redundancy(blocks)
    transfer_instability = _transfer_instability(blocks)
    resurfacing_sustainability = _resurfacing_sustainability(blocks)
    false_fluency_risk = _false_fluency_risk(blocks)
    comparative_runtime_alignment = _comparative_runtime_alignment(
        retrieval_inflation=retrieval_inflation,
        scaffold_dependency=scaffold_dependency,
        compression_risk=compression_risk,
        reconstruction_fragility=reconstruction_fragility,
        continuity_risk=continuity_risk,
        overlap_inflation=overlap_inflation,
        pacing_instability=pacing_instability,
        stabilization_reliability=stabilization_reliability,
        reinforcement_redundancy=reinforcement_redundancy,
        transfer_instability=transfer_instability,
        resurfacing_sustainability=resurfacing_sustainability,
        false_fluency_risk=false_fluency_risk,
        validation_confidence=_validation_confidence(blocks),
    )

    regression_detection_state = _regression_detection_state(
        retrieval_inflation=retrieval_inflation,
        scaffold_dependency=scaffold_dependency,
        compression_risk=compression_risk,
        continuity_risk=continuity_risk,
        overlap_inflation=overlap_inflation,
        reinforcement_redundancy=reinforcement_redundancy,
    )
    sustainability_validation_state = _sustainability_validation_state(
        scaffold_dependency=scaffold_dependency,
        reconstruction_fragility=reconstruction_fragility,
        pacing_instability=pacing_instability,
        stabilization_reliability=stabilization_reliability,
        continuity_risk=continuity_risk,
        false_fluency_risk=false_fluency_risk,
    )
    runtime_benchmark_state = _runtime_benchmark_state(
        comparative_runtime_alignment=comparative_runtime_alignment,
        regression_detection_state=regression_detection_state,
        sustainability_validation_state=sustainability_validation_state,
    )
    scientific_validation_state = _scientific_validation_state(
        runtime_benchmark_state=runtime_benchmark_state,
        regression_detection_state=regression_detection_state,
        sustainability_validation_state=sustainability_validation_state,
    )

    return ScientificRuntimeValidationProfile(
        scientific_validation_state=scientific_validation_state,
        scientific_validation_reasoning=state_reasoning(
            "Validacao cientifica",
            scientific_validation_state,
            [
                f"retrieval={retrieval_inflation:.2f}; scaffold={scaffold_dependency:.2f}; compressao={compression_risk:.2f}.",
                f"continuidade={continuity_risk:.2f}; overlap={overlap_inflation:.2f}; alinhamento={comparative_runtime_alignment:.2f}.",
            ],
        ),
        runtime_benchmark_state=runtime_benchmark_state,
        regression_detection_state=regression_detection_state,
        sustainability_validation_state=sustainability_validation_state,
        cognitive_load_profile="load_elevated" if _cognitive_load(blocks) >= 0.56 else "load_balanced",
        retrieval_reliability_profile="retrieval_fragile" if retrieval_inflation >= 0.62 else "retrieval_reliable",
        scaffold_dependency_profile="scaffold_dependent" if scaffold_dependency >= 0.62 else "scaffold_controlled",
        compression_safety_profile="compression_risky" if compression_risk >= 0.54 else "compression_safe",
        overlap_inflation_profile="overlap_inflated" if overlap_inflation >= 0.58 else "overlap_controlled",
        stabilization_reliability_profile=(
            "stabilization_fragile" if stabilization_reliability <= 0.52 else "stabilization_reliable"
        ),
        continuity_reliability_profile="continuity_fragile" if continuity_risk >= 0.5 else "continuity_reliable",
        reinforcement_redundancy_profile=(
            "reinforcement_redundant" if reinforcement_redundancy >= 0.6 else "reinforcement_balanced"
        ),
        pedagogical_regression_summary=_pedagogical_regression_summary(regression_detection_state),
        runtime_benchmark_summary=_runtime_benchmark_summary(runtime_benchmark_state),
        empirical_validation_context=_empirical_validation_context(
            blocks,
            regression_detection_state=regression_detection_state,
            sustainability_validation_state=sustainability_validation_state,
        ),
        comparative_runtime_alignment=round(comparative_runtime_alignment, 4),
        reproducibility_summary=_reproducibility_summary(
            comparative_runtime_alignment=comparative_runtime_alignment,
            resurfacing_sustainability=resurfacing_sustainability,
            validation_confidence=_validation_confidence(blocks),
        ),
        why_this_validation_profile=_why(scientific_validation_state),
    )


def _retrieval_inflation(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _avg_block(block, "retrieval_pressure_accumulation", "retrieval_density_metric")
        score += min(abs(float(block.get("retrieval_shift", 0.0))), 1.0) * 0.2
        if str(block.get("retrieval_family") or "") == "retrieval_dense":
            score += 0.12
        if str(block.get("validation_dataset_state") or "") == "retrieval_intensive":
            score += 0.08
        values.append(_clamp(score))
    return _average(values)


def _scaffold_dependency(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _avg_block(block, "scaffold_density", "scaffold_load_metric", "support_density")
        if str(block.get("support_family") or "") in {"support_heavy", "support_dense"}:
            score += 0.12
        values.append(_clamp(score))
    return _average(values)


def _compression_risk(blocks: list[dict]) -> float:
    return _average(
        [
            _avg_block(
                block,
                inverse_keys=("compression_safety_metric", "compression_safety_signal"),
            )
            + _clamp(block.get("false_fluency_risk", 0.0)) * 0.18
            for block in blocks
        ]
    )


def _reconstruction_fragility(blocks: list[dict]) -> float:
    return _average(
        [
            _avg_block(
                block,
                "reconstruction_fragility",
                "reconstruction_pressure_metric",
                inverse_keys=("reconstruction_sustainability_signal",),
            )
            for block in blocks
        ]
    )


def _continuity_risk(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _avg_block(
            block,
            inverse_keys=("continuity_smoothness_metric", "continuity_sustainability_signal"),
        )
        if str(block.get("continuity_family") or "") == "continuity_fragile":
            score += 0.12
        score += min(abs(float(block.get("continuity_shift", 0.0))), 1.0) * 0.08
        values.append(_clamp(score))
    return _average(values)


def _overlap_inflation(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _avg_block(block, "modulation_overlap", "adaptive_overlap_signal", "signal_overlap_density")
        score += min(abs(float(block.get("overlap_shift", 0.0))), 1.0) * 0.08
        if str(block.get("overlap_family") or "") in {"overlap_high", "overlap_convergent"}:
            score += 0.12
        values.append(_clamp(score))
    return _average(values)


def _pacing_instability(blocks: list[dict]) -> float:
    return _average(
        [
            _avg_block(
                block,
                inverse_keys=("pacing_stability_metric", "pacing_sustainability_signal"),
            )
            for block in blocks
        ]
    )


def _stabilization_reliability(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _avg_block(
            block,
            "stabilization_sustainability_metric",
            "stabilization_reliability_signal",
            "longitudinal_validation_signal",
        )
        if str(block.get("stabilization_family") or "") in {"stabilized", "stabilization_progressive"}:
            score += 0.08
        values.append(_clamp(score))
    return _average(values)


def _reinforcement_redundancy(blocks: list[dict]) -> float:
    return _average(
        [
            _avg_block(block, "support_density", "reinforcement_density_signal", "adaptive_overlap_signal")
            for block in blocks
        ]
    )


def _transfer_instability(blocks: list[dict]) -> float:
    return _average(
        [
            _avg_block(
                block,
                "transfer_fragility",
                inverse_keys=("transfer_stability_signal",),
            )
            for block in blocks
        ]
    )


def _resurfacing_sustainability(blocks: list[dict]) -> float:
    candidates = [
        _clamp(block.get("resurfacing_effectiveness_signal", block.get("longitudinal_validation_signal", 0.5)))
        for block in blocks
    ]
    return _average(candidates)


def _false_fluency_risk(blocks: list[dict]) -> float:
    return _average([_clamp(block.get("false_fluency_risk", 0.0)) for block in blocks])


def _validation_confidence(blocks: list[dict]) -> float:
    return _average([_clamp(block.get("validation_confidence", 0.5)) for block in blocks])


def _cognitive_load(blocks: list[dict]) -> float:
    return _average(
        [
            _avg_block(
                block,
                "retrieval_pressure_accumulation",
                "scaffold_density",
                "reconstruction_pressure_metric",
                "adaptive_overlap_signal",
            )
            for block in blocks
        ]
    )


def _comparative_runtime_alignment(
    *,
    retrieval_inflation: float,
    scaffold_dependency: float,
    compression_risk: float,
    reconstruction_fragility: float,
    continuity_risk: float,
    overlap_inflation: float,
    pacing_instability: float,
    stabilization_reliability: float,
    reinforcement_redundancy: float,
    transfer_instability: float,
    resurfacing_sustainability: float,
    false_fluency_risk: float,
    validation_confidence: float,
) -> float:
    return average_values(
        [
            1.0 - retrieval_inflation,
            1.0 - scaffold_dependency,
            1.0 - compression_risk,
            1.0 - reconstruction_fragility,
            1.0 - continuity_risk,
            1.0 - overlap_inflation,
            1.0 - pacing_instability,
            stabilization_reliability,
            1.0 - reinforcement_redundancy,
            1.0 - transfer_instability,
            resurfacing_sustainability,
            1.0 - false_fluency_risk,
            validation_confidence,
        ]
    )


def _regression_detection_state(
    *,
    retrieval_inflation: float,
    scaffold_dependency: float,
    compression_risk: float,
    continuity_risk: float,
    overlap_inflation: float,
    reinforcement_redundancy: float,
) -> str:
    if retrieval_inflation >= 0.62:
        return "retrieval_inflation"
    if scaffold_dependency >= 0.66 and reinforcement_redundancy >= 0.58:
        return "support_overextended"
    if compression_risk >= 0.56:
        return "compression_drift"
    if overlap_inflation >= 0.58:
        return "overlap_inflated"
    if continuity_risk >= 0.54:
        return "continuity_degrading"
    return "regression_stable"


def _sustainability_validation_state(
    *,
    scaffold_dependency: float,
    reconstruction_fragility: float,
    pacing_instability: float,
    stabilization_reliability: float,
    continuity_risk: float,
    false_fluency_risk: float,
) -> str:
    if (
        scaffold_dependency >= 0.62
        or reconstruction_fragility >= 0.58
        or pacing_instability >= 0.56
        or continuity_risk >= 0.5
        or false_fluency_risk >= 0.44
    ):
        return "sustainability_fragile"
    if stabilization_reliability >= 0.7:
        return "sustainability_supported"
    return "sustainability_watch"


def _runtime_benchmark_state(
    *,
    comparative_runtime_alignment: float,
    regression_detection_state: str,
    sustainability_validation_state: str,
) -> str:
    if (
        comparative_runtime_alignment >= 0.74
        and regression_detection_state == "regression_stable"
        and sustainability_validation_state == "sustainability_supported"
    ):
        return "benchmark_ready"
    if comparative_runtime_alignment >= 0.62:
        return "benchmark_watch"
    return "benchmark_fragile"


def _scientific_validation_state(
    *,
    runtime_benchmark_state: str,
    regression_detection_state: str,
    sustainability_validation_state: str,
) -> str:
    if runtime_benchmark_state == "benchmark_ready":
        return "benchmark_ready"
    if regression_detection_state != "regression_stable":
        return "regression_watch"
    if sustainability_validation_state == "sustainability_fragile":
        return "sustainability_watch"
    return "validation_stable"


def _pedagogical_regression_summary(state: str) -> str:
    return state_message(
        state,
        {
            "retrieval_inflation": "Houve inflacao observavel de retrieval na janela comparada.",
            "support_overextended": "Suporte e scaffold parecem mais extensos do que o padrao balanceado.",
            "compression_drift": "A seguranca de compressao parece ter degradado na janela observada.",
            "overlap_inflated": "O overlap adaptativo aumentou o suficiente para merecer inspeção.",
            "continuity_degrading": "A continuidade perdeu confiabilidade observacional na janela recente.",
            "regression_stable": "Nao houve sinal forte de regressao observacional dominante.",
        },
        "Nao houve uma regressao observacional dominante.",
    )


def _runtime_benchmark_summary(state: str) -> str:
    return state_message(
        state,
        {
            "benchmark_ready": "O runtime atual parece suficientemente estavel e comparavel para benchmarking.",
            "benchmark_watch": "O runtime atual ja permite comparacao, mas ainda merece leitura cuidadosa.",
            "benchmark_fragile": "O runtime atual ainda mostra fragilidade para benchmark comparativo limpo.",
        },
        "O runtime atual ficou em uma faixa neutra para benchmarking.",
    )


def _empirical_validation_context(
    blocks: list[dict],
    *,
    regression_detection_state: str,
    sustainability_validation_state: str,
) -> str:
    latest = blocks[-1]
    family = str(latest.get("pedagogical_scenario_family") or "balanced_validation")
    dataset_state = str(latest.get("validation_dataset_state") or "validation_ready")
    return (
        f"contexto={family}; dataset={dataset_state}; "
        f"regressao={regression_detection_state}; sustentabilidade={sustainability_validation_state}"
    )


def _reproducibility_summary(
    *,
    comparative_runtime_alignment: float,
    resurfacing_sustainability: float,
    validation_confidence: float,
) -> str:
    return (
        f"alinhamento={comparative_runtime_alignment:.2f}; "
        f"resurfacing={resurfacing_sustainability:.2f}; "
        f"confianca={validation_confidence:.2f}"
    )


def _why(state: str) -> str:
    return state_message(
        state,
        {
            "benchmark_ready": "Os sinais ficaram estaveis o bastante para comparacao cientifica mais confiavel.",
            "regression_watch": "A camada encontrou inflacao ou drift suficiente para inspeção regressiva.",
            "sustainability_watch": "Os sinais sugerem fragilidade de sustentacao pedagógica na janela atual.",
            "validation_stable": "Os sinais permaneceram observacionalmente controlados e reprodutiveis.",
        },
        "O perfil cientifico permaneceu em faixa observacional neutra.",
    )


def _avg_block(
    block: dict,
    *keys: str,
    inverse_keys: tuple[str, ...] = (),
) -> float:
    values = [clamp_value(block.get(key, 0.0)) for key in keys]
    values.extend(1.0 - clamp_value(block.get(key, 0.0)) for key in inverse_keys)
    if not values:
        return 0.0
    return average_values(values)


def _average(values: list[float]) -> float:
    return average_values(values)


def _clamp(value: float | int | None) -> float:
    return clamp_value(value)
