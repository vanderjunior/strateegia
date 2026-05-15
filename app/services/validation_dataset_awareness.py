from __future__ import annotations

from copy import deepcopy

from app.domain.models import ValidationDatasetAwarenessProfile
from app.services.runtime_profile_utils import average_values, clamp_value, state_message, state_reasoning


class ValidationDatasetAwarenessLayer:
    def annotate(self, runtime_blocks: list[dict]) -> list[dict]:
        if not runtime_blocks:
            return []

        profile = resolve_validation_dataset_awareness(runtime_blocks)
        payload = profile.model_dump(mode="json")
        return [{**deepcopy(block), **payload} for block in runtime_blocks]


def resolve_validation_dataset_awareness(
    runtime_blocks: list[dict] | None,
) -> ValidationDatasetAwarenessProfile:
    blocks = list(runtime_blocks or [])
    if not blocks:
        return ValidationDatasetAwarenessProfile(
            validation_dataset_state="validation_ready",
            validation_dataset_reasoning=["Nao havia blocos suficientes; contexto neutro de validacao aplicado."],
            pedagogical_scenario_family="balanced_validation",
            retrieval_condition_profile="retrieval_balanced",
            scaffold_condition_profile="scaffold_balanced",
            continuity_condition_profile="continuity_smooth",
            reconstruction_condition_profile="reconstruction_balanced",
            compression_condition_profile="compression_stable",
            transfer_condition_profile="transfer_supported",
            stabilization_condition_profile="stabilization_progressive",
            overlap_condition_profile="modulation_stable",
            pacing_condition_profile="pacing_stable",
            reinforcement_condition_profile="reinforcement_balanced",
            runtime_validation_context="Sessao vazia ou neutra para comparacao observacional.",
            comparative_validation_alignment=0.5,
            dataset_awareness_summary="Sem blocos suficientes para caracterizar um cenario de validacao.",
            why_this_validation_context="A camada recebeu uma sessao vazia e preservou um contexto neutro.",
        )

    retrieval_score = _retrieval_score(blocks)
    scaffold_score = _scaffold_score(blocks)
    continuity_quality = _continuity_quality(blocks)
    reconstruction_score = _reconstruction_score(blocks)
    compression_quality = _compression_quality(blocks)
    transfer_score = _transfer_score(blocks)
    stabilization_quality = _stabilization_quality(blocks)
    overlap_score = _overlap_score(blocks)
    pacing_score = _pacing_score(blocks)
    reinforcement_score = _reinforcement_score(blocks)
    resurfacing_quality = _resurfacing_quality(blocks)
    validation_confidence = _validation_confidence(blocks)

    retrieval_condition_profile = "retrieval_intensive" if retrieval_score >= 0.66 else "retrieval_balanced"
    scaffold_condition_profile = "scaffold_sensitive" if scaffold_score >= 0.64 else "scaffold_balanced"
    continuity_condition_profile = "continuity_fragile" if continuity_quality <= 0.44 else "continuity_smooth"
    reconstruction_condition_profile = (
        "reconstruction_heavy" if reconstruction_score >= 0.62 else "reconstruction_balanced"
    )
    compression_condition_profile = "compression_sensitive" if compression_quality <= 0.48 else "compression_stable"
    transfer_condition_profile = "transfer_fragile" if transfer_score >= 0.58 else "transfer_supported"
    stabilization_condition_profile = (
        "stabilization_progressive" if stabilization_quality >= 0.66 else "stabilization_moderate"
    )
    overlap_condition_profile = "overlap_accumulated" if overlap_score >= 0.58 else "modulation_stable"
    pacing_condition_profile = "pacing_sensitive" if pacing_score >= 0.54 else "pacing_stable"
    reinforcement_condition_profile = (
        "reinforcement_dense" if reinforcement_score >= 0.62 else "reinforcement_balanced"
    )
    resurfacing_condition = "resurfacing_dependent" if resurfacing_quality <= 0.44 else "resurfacing_supported"

    comparative_validation_alignment = _comparative_validation_alignment(
        retrieval_score=retrieval_score,
        scaffold_score=scaffold_score,
        continuity_quality=continuity_quality,
        reconstruction_score=reconstruction_score,
        compression_quality=compression_quality,
        transfer_score=transfer_score,
        stabilization_quality=stabilization_quality,
        overlap_score=overlap_score,
        pacing_score=pacing_score,
        reinforcement_score=reinforcement_score,
        resurfacing_quality=resurfacing_quality,
        validation_confidence=validation_confidence,
    )

    state = _state(
        retrieval_score=retrieval_score,
        scaffold_score=scaffold_score,
        continuity_quality=continuity_quality,
        reconstruction_score=reconstruction_score,
        compression_quality=compression_quality,
        transfer_score=transfer_score,
        stabilization_quality=stabilization_quality,
        overlap_score=overlap_score,
        pacing_score=pacing_score,
        reinforcement_score=reinforcement_score,
        resurfacing_quality=resurfacing_quality,
        comparative_validation_alignment=comparative_validation_alignment,
    )
    family = _scenario_family(state)

    return ValidationDatasetAwarenessProfile(
        validation_dataset_state=state,
        validation_dataset_reasoning=state_reasoning(
            "Contexto de validacao",
            state,
            [
                f"Retrieval={retrieval_score:.2f}; scaffold={scaffold_score:.2f}; reconstrucao={reconstruction_score:.2f}.",
                f"Continuidade={continuity_quality:.2f}; compressao={compression_quality:.2f}; alinhamento={comparative_validation_alignment:.2f}.",
            ],
        ),
        pedagogical_scenario_family=family,
        retrieval_condition_profile=retrieval_condition_profile,
        scaffold_condition_profile=scaffold_condition_profile,
        continuity_condition_profile=continuity_condition_profile,
        reconstruction_condition_profile=reconstruction_condition_profile,
        compression_condition_profile=compression_condition_profile,
        transfer_condition_profile=transfer_condition_profile,
        stabilization_condition_profile=stabilization_condition_profile,
        overlap_condition_profile=overlap_condition_profile,
        pacing_condition_profile=pacing_condition_profile,
        reinforcement_condition_profile=reinforcement_condition_profile,
        runtime_validation_context=_runtime_validation_context(
            retrieval_condition_profile,
            scaffold_condition_profile,
            continuity_condition_profile,
            reconstruction_condition_profile,
            compression_condition_profile,
            transfer_condition_profile,
            stabilization_condition_profile,
            overlap_condition_profile,
            pacing_condition_profile,
            reinforcement_condition_profile,
            resurfacing_condition,
        ),
        comparative_validation_alignment=round(comparative_validation_alignment, 4),
        dataset_awareness_summary=_summary(state),
        why_this_validation_context=_why(state),
    )


def _retrieval_score(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _avg_block(
            block,
            "retrieval_pressure_accumulation",
            "retrieval_density_metric",
        )
        if str(block.get("retrieval_family") or "") == "retrieval_dense":
            score += 0.12
        values.append(_clamp(score))
    return _average(values)


def _scaffold_score(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _avg_block(block, "scaffold_density", "scaffold_load_metric", "support_density")
        if str(block.get("support_family") or "") in {"support_heavy", "support_dense"}:
            score += 0.1
        values.append(_clamp(score))
    return _average(values)


def _continuity_quality(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _avg_block(block, "continuity_smoothness_metric", "continuity_sustainability_signal")
        if str(block.get("continuity_family") or "") == "continuity_fragile":
            score -= 0.12
        elif str(block.get("continuity_family") or "") == "continuity_stable":
            score += 0.08
        values.append(_clamp(score))
    return _average(values)


def _reconstruction_score(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _avg_block(
            block,
            "reconstruction_fragility",
            "reconstruction_pressure_metric",
            inverse_keys=("reconstruction_sustainability_signal",),
        )
        values.append(_clamp(score))
    return _average(values)


def _compression_quality(blocks: list[dict]) -> float:
    return _average(
        [
            _avg_block(block, "compression_safety_metric", "compression_safety_signal")
            for block in blocks
        ]
    )


def _transfer_score(blocks: list[dict]) -> float:
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


def _stabilization_quality(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _avg_block(
            block,
            "stabilization_sustainability_metric",
            "stabilization_reliability_signal",
        )
        if str(block.get("stabilization_family") or "") in {"stabilized", "stabilization_progressive"}:
            score += 0.08
        values.append(_clamp(score))
    return _average(values)


def _overlap_score(blocks: list[dict]) -> float:
    values = []
    for block in blocks:
        score = _avg_block(block, "modulation_overlap", "adaptive_overlap_signal")
        if str(block.get("overlap_family") or "") in {"overlap_high", "overlap_convergent"}:
            score += 0.1
        values.append(_clamp(score))
    return _average(values)


def _pacing_score(blocks: list[dict]) -> float:
    return _average(
        [
            _avg_block(
                block,
                inverse_keys=("pacing_stability_metric", "pacing_sustainability_signal"),
            )
            for block in blocks
        ]
    )


def _reinforcement_score(blocks: list[dict]) -> float:
    return _average([_avg_block(block, "support_density", "reinforcement_density_signal") for block in blocks])


def _resurfacing_quality(blocks: list[dict]) -> float:
    return _average([_clamp(block.get("resurfacing_effectiveness_signal", 0.5)) for block in blocks])


def _validation_confidence(blocks: list[dict]) -> float:
    return _average([_clamp(block.get("validation_confidence", 0.5)) for block in blocks])


def _comparative_validation_alignment(
    *,
    retrieval_score: float,
    scaffold_score: float,
    continuity_quality: float,
    reconstruction_score: float,
    compression_quality: float,
    transfer_score: float,
    stabilization_quality: float,
    overlap_score: float,
    pacing_score: float,
    reinforcement_score: float,
    resurfacing_quality: float,
    validation_confidence: float,
) -> float:
    return average_values(
        [
            1.0 - max(0.0, retrieval_score - 0.48),
            1.0 - scaffold_score,
            continuity_quality,
            1.0 - reconstruction_score,
            compression_quality,
            1.0 - transfer_score,
            stabilization_quality,
            1.0 - overlap_score,
            1.0 - pacing_score,
            1.0 - (reinforcement_score * 0.72),
            resurfacing_quality,
            validation_confidence,
        ]
    )


def _state(
    *,
    retrieval_score: float,
    scaffold_score: float,
    continuity_quality: float,
    reconstruction_score: float,
    compression_quality: float,
    transfer_score: float,
    stabilization_quality: float,
    overlap_score: float,
    pacing_score: float,
    reinforcement_score: float,
    resurfacing_quality: float,
    comparative_validation_alignment: float,
) -> str:
    if retrieval_score >= 0.66:
        return "retrieval_intensive"
    if scaffold_score >= 0.64:
        return "scaffold_sensitive"
    if continuity_quality <= 0.44:
        return "continuity_fragile"
    if reconstruction_score >= 0.62:
        return "reconstruction_heavy"
    if compression_quality <= 0.48:
        return "compression_sensitive"
    if transfer_score >= 0.58:
        return "transfer_fragile"
    if overlap_score >= 0.58:
        return "overlap_accumulated"
    if pacing_score >= 0.54:
        return "pacing_sensitive"
    if reinforcement_score >= 0.62:
        return "reinforcement_dense"
    if resurfacing_quality <= 0.44:
        return "resurfacing_dependent"
    if stabilization_quality >= 0.7 and comparative_validation_alignment >= 0.7:
        return "validation_ready"
    if stabilization_quality >= 0.66:
        return "stabilization_progressive"
    if comparative_validation_alignment >= 0.74:
        return "cognitively_balanced"
    if overlap_score <= 0.3 and continuity_quality >= 0.68:
        return "modulation_stable"
    return "pedagogically_divergent"


def _scenario_family(state: str) -> str:
    if state == "retrieval_intensive":
        return "retrieval"
    if state in {"scaffold_sensitive", "reinforcement_dense", "resurfacing_dependent"}:
        return "support_scaffold"
    if state in {"continuity_fragile", "pacing_sensitive"}:
        return "continuity_pacing"
    if state in {"reconstruction_heavy", "compression_sensitive", "transfer_fragile"}:
        return "fragile_application"
    if state in {"overlap_accumulated", "pedagogically_divergent"}:
        return "overlap_divergence"
    return "balanced_validation"


def _runtime_validation_context(*labels: str) -> str:
    unique_labels = []
    for label in labels:
        if label.endswith("_balanced") or label.endswith("_stable") or label.endswith("_smooth"):
            continue
        if label in {"transfer_supported", "resurfacing_supported", "stabilization_moderate"}:
            continue
        if label and label not in unique_labels:
            unique_labels.append(label)
    if not unique_labels:
        return "Contexto balanceado, sem pressao pedagogica dominante."
    return "Contexto observacional: " + ", ".join(unique_labels[:4]) + "."


def _summary(state: str) -> str:
    return state_message(
        state,
        {
            "retrieval_intensive": "O runtime atual se parece com um cenario intensivo de retrieval.",
            "scaffold_sensitive": "O runtime atual sugere dependencia maior de scaffold e suporte.",
            "continuity_fragile": "O runtime atual sugere fragilidade de continuidade comparativa.",
            "reconstruction_heavy": "O runtime atual concentra mais pressao reconstrutiva.",
            "compression_sensitive": "O runtime atual pede leitura cuidadosa da seguranca de compressao.",
            "transfer_fragile": "O runtime atual sugere fragilidade de transferencia contextual.",
            "stabilization_progressive": "O runtime atual sugere estabilizacao progressiva.",
            "overlap_accumulated": "O runtime atual acumulou overlap e convergencia de sinais.",
            "cognitively_balanced": "O runtime atual parece cognitivamente equilibrado para validacao.",
            "validation_ready": "O runtime atual parece bem comparavel para validacao e benchmarking.",
            "resurfacing_dependent": "O runtime atual depende mais de resurfacing para manter consistencia.",
            "reinforcement_dense": "O runtime atual concentra reforco e suporte de forma densa.",
            "pacing_sensitive": "O runtime atual e sensivel a variacoes de pacing.",
            "modulation_stable": "O runtime atual manteve modulação estavel e legivel.",
            "pedagogically_divergent": "O runtime atual mostra divergencias suficientes para inspeção comparativa.",
        },
        "O runtime atual permaneceu em uma faixa observacional neutra.",
    )


def _why(state: str) -> str:
    return state_message(
        state,
        {
            "retrieval_intensive": "Retrieval e pressao comparativa ficaram acima da faixa neutra.",
            "scaffold_sensitive": "Scaffold, suporte e reforco apareceram acima do padrao balanceado.",
            "continuity_fragile": "Os sinais de continuidade ficaram abaixo da faixa confortavel.",
            "reconstruction_heavy": "A reconstrucao mostrou mais fragilidade ou carga acumulada.",
            "compression_sensitive": "A seguranca de compressao nao ficou alta o bastante para contexto neutro.",
            "transfer_fragile": "A transferencia contextual ainda parece instavel para comparacao segura.",
            "stabilization_progressive": "A estabilizacao agregada cresceu o suficiente para caracterizar progressao.",
            "overlap_accumulated": "Houve acumulacao local de overlap e convergencia adaptativa.",
            "cognitively_balanced": "Os sinais agregados ficaram proximos de um equilibrio observacional.",
            "validation_ready": "Os sinais agregados ficaram estaveis e comparaveis sem pressao dominante.",
            "resurfacing_dependent": "A efetividade de resurfacing ficou baixa o bastante para virar contexto relevante.",
            "reinforcement_dense": "O reforco agregado passou da faixa neutra de suporte.",
            "pacing_sensitive": "Os sinais de pacing ficaram mais sensiveis do que o padrao estavel.",
            "modulation_stable": "Overlap baixo e continuidade alta sustentaram estabilidade de modulação.",
            "pedagogically_divergent": "Os sinais nao convergiram para um contexto comparativo mais limpo.",
        },
        "O contexto permaneceu observacionalmente neutro.",
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
