from __future__ import annotations

from app.domain.models import (
    ControlledTuningDimension,
    ControlledTuningExperiment,
    ControlledTuningExperimentRegistry,
    ControlledTuningHypothesis,
)
from app.services.runtime_profile_utils import state_message


def build_controlled_tuning_experiment_registry(
    *,
    experiments: list[ControlledTuningExperiment] | None = None,
) -> ControlledTuningExperimentRegistry:
    registry_experiments = list(experiments) if experiments is not None else _default_experiments()
    total = len(registry_experiments)
    read_only = sum(1 for experiment in registry_experiments if experiment.read_only)
    executable = sum(1 for experiment in registry_experiments if experiment.executable)
    categories = sorted({experiment.experiment_category for experiment in registry_experiments})
    coverage = _benchmark_case_coverage(registry_experiments)
    risks = {
        "low": sum(1 for experiment in registry_experiments if experiment.risk_level == "low"),
        "medium": sum(1 for experiment in registry_experiments if experiment.risk_level == "medium"),
        "high": sum(1 for experiment in registry_experiments if experiment.risk_level == "high"),
    }
    state = _registry_state(registry_experiments)
    return ControlledTuningExperimentRegistry(
        tuning_experiment_registry_state=state,
        tuning_experiment_registry_summary=_registry_summary(state),
        tuning_experiments=registry_experiments,
        total_experiments=total,
        read_only_experiments=read_only,
        executable_experiments=executable,
        experiment_categories=categories,
        benchmark_case_coverage=coverage,
        experiment_risk_summary=risks,
        why_this_registry_state=_why_registry(state),
    )


def _default_experiments() -> list[ControlledTuningExperiment]:
    return [
        _experiment(
            experiment_id="baseline_current_behavior",
            experiment_name="Baseline Current Behavior",
            experiment_category="baseline",
            experiment_description="Representa o comportamento observacional atual sem qualquer mudanca hipotetica.",
            dimensions=[
                _dimension("baseline_reference", "current_runtime", "none", "Mantem o perfil atual como controle."),
            ],
            hypothesis_id="baseline_control",
            hypothesis="Nenhuma mudanca comportamental e esperada; serve apenas como controle declarativo.",
            effects=["no behavioral change"],
            cases=["pedagogically_stable_baseline_case"],
            risk="low",
        ),
        _experiment(
            experiment_id="compression_conservative_profile",
            experiment_name="Compression Conservative Profile",
            experiment_category="compression",
            experiment_description="Hipotese declarativa para tornar a compressao mais segura e menos agressiva.",
            dimensions=[
                _dimension("compression_conservatism", "current_tuning", "increase", "Aumentaria a cautela de compressao."),
                _dimension("scaffold_sensitivity", "current_tuning", "slight_increase", "Pode elevar um pouco suporte explicito."),
            ],
            hypothesis_id="compression_conservative_hypothesis",
            hypothesis="Reducao de compression risk com leve aumento potencial de scaffold/load.",
            effects=["reduce compression risk", "possibly increase scaffold load slightly"],
            cases=["unsafe_compression_case", "reconstruction_improving_case", "transfer_fragility_case"],
            risk="medium",
        ),
        _experiment(
            experiment_id="scaffold_sensitive_profile",
            experiment_name="Scaffold Sensitive Profile",
            experiment_category="support",
            experiment_description="Hipotese para detectar dependencia de scaffold mais cedo.",
            dimensions=[
                _dimension("scaffold_sensitivity", "current_tuning", "increase", "Elevaria sensibilidade a suporte excessivo."),
            ],
            hypothesis_id="scaffold_sensitive_hypothesis",
            hypothesis="Maior sensibilidade a dependencia de scaffold e menor risco de mascarar fragilidade.",
            effects=["increase scaffold dependency detection sensitivity", "reduce risk of masked fragility"],
            cases=["scaffold_dependency_case", "false_fluency_case"],
            risk="medium",
        ),
        _experiment(
            experiment_id="retrieval_inflation_guarded_profile",
            experiment_name="Retrieval Inflation Guarded Profile",
            experiment_category="retrieval",
            experiment_description="Hipotese para aumentar cautela contra inflacao artificial de retrieval.",
            dimensions=[
                _dimension("retrieval_tolerance", "current_tuning", "decrease", "Tornaria retrieval inflation mais facil de sinalizar."),
            ],
            hypothesis_id="retrieval_guarded_hypothesis",
            hypothesis="Melhora da deteccao de retrieval inflation sem perder leitura de retrieval sustentavel.",
            effects=["improve retrieval sustainability detection", "increase sensitivity to inflated retrieval pressure"],
            cases=["retrieval_inflation_case", "sustainable_retrieval_case"],
            risk="medium",
        ),
        _experiment(
            experiment_id="reconstruction_protective_profile",
            experiment_name="Reconstruction Protective Profile",
            experiment_category="reconstruction",
            experiment_description="Hipotese para preservar suporte em contextos reconstrutivamente frageis.",
            dimensions=[
                _dimension("reconstruction_support_level", "current_tuning", "increase", "Elevaria protecao reconstrutiva."),
            ],
            hypothesis_id="reconstruction_protective_hypothesis",
            hypothesis="Maior suporte de reconstrucao e menor risco de checks prematuros de confianca.",
            effects=["increase reconstruction support", "reduce premature confidence checks"],
            cases=["reconstruction_improving_case", "false_fluency_case"],
            risk="medium",
        ),
        _experiment(
            experiment_id="continuity_smoothing_cautious_profile",
            experiment_name="Continuity Smoothing Cautious Profile",
            experiment_category="continuity",
            experiment_description="Hipotese para evitar sobre-suavizacao de continuidade fragmentada.",
            dimensions=[
                _dimension("continuity_smoothing_strength", "current_tuning", "decrease", "Preservaria sinais de fragmentacao."),
            ],
            hypothesis_id="continuity_cautious_hypothesis",
            hypothesis="Menor risco de criar falsa sensacao de progressao suave quando ha fragilidade real.",
            effects=["preserve continuity warnings", "reduce false sense of smooth progression"],
            cases=["continuity_degraded_case", "transfer_fragility_case"],
            risk="medium",
        ),
        _experiment(
            experiment_id="support_lightweight_profile",
            experiment_name="Support Lightweight Profile",
            experiment_category="support",
            experiment_description="Hipotese para reduzir suporte em contextos genuinamente estaveis.",
            dimensions=[
                _dimension("scaffold_sensitivity", "current_tuning", "decrease", "Reduziria suporte em faixas consolidadas."),
                _dimension("modulation_density_tolerance", "current_tuning", "decrease", "Conteria densidade de apoio."),
            ],
            hypothesis_id="support_lightweight_hypothesis",
            hypothesis="Menor scaffold load mantendo estabilidade quando a consolidacao e real.",
            effects=["reduce scaffold load", "maintain stability if baseline is truly consolidated"],
            cases=["pedagogically_stable_baseline_case", "resurfacing_effective_case"],
            risk="high",
        ),
        _experiment(
            experiment_id="stabilization_conservative_profile",
            experiment_name="Stabilization Conservative Profile",
            experiment_category="stabilization",
            experiment_description="Hipotese para evitar declaracao precoce de estabilidade.",
            dimensions=[
                _dimension("stabilization_threshold", "current_tuning", "increase", "Exigiria mais evidencia antes de estabilidade."),
            ],
            hypothesis_id="stabilization_conservative_hypothesis",
            hypothesis="Reducao de false stabilization e maior sensibilidade a fragilidade longitudinal.",
            effects=["reduce false stabilization", "increase sensitivity to long-term fragility"],
            cases=["false_fluency_case", "transfer_fragility_case", "resurfacing_effective_case"],
            risk="medium",
        ),
    ]


def _dimension(dimension_id: str, current_reference: str, hypothetical_direction: str, rationale: str) -> ControlledTuningDimension:
    return ControlledTuningDimension(
        dimension_id=dimension_id,
        current_reference=current_reference,
        hypothetical_direction=hypothetical_direction,
        rationale=rationale,
    )


def _experiment(
    *,
    experiment_id: str,
    experiment_name: str,
    experiment_category: str,
    experiment_description: str,
    dimensions: list[ControlledTuningDimension],
    hypothesis_id: str,
    hypothesis: str,
    effects: list[str],
    cases: list[str],
    risk: str,
) -> ControlledTuningExperiment:
    return ControlledTuningExperiment(
        experiment_id=experiment_id,
        experiment_name=experiment_name,
        experiment_category=experiment_category,
        experiment_description=experiment_description,
        tuning_dimensions=dimensions,
        hypothesis=ControlledTuningHypothesis(
            hypothesis_id=hypothesis_id,
            statement=hypothesis,
            expected_directional_effects=effects,
            relevant_benchmark_cases=cases,
        ),
        expected_directional_effects=effects,
        relevant_benchmark_cases=cases,
        risk_level=risk,
        read_only=True,
        executable=False,
        experiment_reasoning=[
            f"Categoria={experiment_category}; risco={risk}.",
            f"Cases={', '.join(cases)}.",
        ],
    )


def _benchmark_case_coverage(
    experiments: list[ControlledTuningExperiment],
) -> dict[str, list[str]]:
    coverage: dict[str, list[str]] = {}
    for experiment in experiments:
        for case_id in experiment.relevant_benchmark_cases:
            coverage.setdefault(case_id, []).append(experiment.experiment_id)
    return {case_id: sorted(experiment_ids) for case_id, experiment_ids in sorted(coverage.items())}


def _registry_state(experiments: list[ControlledTuningExperiment]) -> str:
    if not experiments:
        return "registry_empty"
    if any(experiment.executable for experiment in experiments):
        return "registry_partial"
    if not all(experiment.read_only for experiment in experiments):
        return "registry_partial"
    return "registry_ready"


def _registry_summary(state: str) -> str:
    return state_message(
        state,
        {
            "registry_ready": "Controlled tuning experiment registry is ready for read-only inspection.",
            "registry_empty": "Controlled tuning experiment registry is empty.",
            "registry_partial": "Controlled tuning experiment registry is only partially constrained.",
            "registry_not_executable": "Controlled tuning experiment registry is intentionally non-executable.",
            "registry_incomplete": "Controlled tuning experiment registry is incomplete.",
        },
        "Controlled tuning experiment registry remains observationally neutral.",
    )


def _why_registry(state: str) -> str:
    return state_message(
        state,
        {
            "registry_ready": "All declared experiments remain read-only, bounded and benchmark-oriented.",
            "registry_empty": "No declarative experiment definitions are available yet.",
            "registry_partial": "Some declarative constraints are missing or inconsistent.",
            "registry_not_executable": "The registry is intentionally declarative and not runnable.",
            "registry_incomplete": "The registry still lacks enough coverage for controlled comparison.",
        },
        "The registry remains in a neutral observational state.",
    )
