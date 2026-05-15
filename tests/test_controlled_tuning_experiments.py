from app.services.controlled_tuning_experiments import (
    build_controlled_tuning_experiment_registry,
)


def experiment_index():
    registry = build_controlled_tuning_experiment_registry()
    return {experiment.experiment_id: experiment for experiment in registry.tuning_experiments}


def test_controlled_tuning_registry_is_deterministic():
    first = build_controlled_tuning_experiment_registry()
    second = build_controlled_tuning_experiment_registry()

    assert first == second


def test_baseline_experiment_exists():
    experiment = experiment_index()["baseline_current_behavior"]

    assert experiment.experiment_name
    assert "pedagogically_stable_baseline_case" in experiment.relevant_benchmark_cases


def test_compression_conservative_profile_exists():
    experiment = experiment_index()["compression_conservative_profile"]

    assert "unsafe_compression_case" in experiment.relevant_benchmark_cases


def test_scaffold_sensitive_profile_exists():
    experiment = experiment_index()["scaffold_sensitive_profile"]

    assert "scaffold_dependency_case" in experiment.relevant_benchmark_cases


def test_retrieval_inflation_guarded_profile_exists():
    experiment = experiment_index()["retrieval_inflation_guarded_profile"]

    assert "retrieval_inflation_case" in experiment.relevant_benchmark_cases


def test_reconstruction_protective_profile_exists():
    experiment = experiment_index()["reconstruction_protective_profile"]

    assert "reconstruction_improving_case" in experiment.relevant_benchmark_cases


def test_continuity_smoothing_cautious_profile_exists():
    experiment = experiment_index()["continuity_smoothing_cautious_profile"]

    assert "continuity_degraded_case" in experiment.relevant_benchmark_cases


def test_support_lightweight_profile_exists():
    experiment = experiment_index()["support_lightweight_profile"]

    assert "resurfacing_effective_case" in experiment.relevant_benchmark_cases


def test_stabilization_conservative_profile_exists():
    experiment = experiment_index()["stabilization_conservative_profile"]

    assert "false_fluency_case" in experiment.relevant_benchmark_cases


def test_all_experiments_are_read_only():
    registry = build_controlled_tuning_experiment_registry()

    assert all(experiment.read_only for experiment in registry.tuning_experiments)


def test_all_experiments_are_non_executable():
    registry = build_controlled_tuning_experiment_registry()

    assert all(not experiment.executable for experiment in registry.tuning_experiments)


def test_registry_benchmark_case_coverage_is_summarized():
    registry = build_controlled_tuning_experiment_registry()

    assert "false_fluency_case" in registry.benchmark_case_coverage
    assert "pedagogically_stable_baseline_case" in registry.benchmark_case_coverage


def test_registry_risk_summary_is_exposed():
    registry = build_controlled_tuning_experiment_registry()

    assert registry.experiment_risk_summary["low"] >= 1
    assert registry.experiment_risk_summary["medium"] >= 1


def test_registry_ready_state():
    registry = build_controlled_tuning_experiment_registry()

    assert registry.tuning_experiment_registry_state == "registry_ready"


def test_registry_empty_state_if_no_experiments():
    registry = build_controlled_tuning_experiment_registry(experiments=[])

    assert registry.tuning_experiment_registry_state == "registry_empty"
    assert registry.total_experiments == 0


def test_registry_handles_missing_optional_metadata():
    registry = build_controlled_tuning_experiment_registry()
    baseline = next(
        experiment
        for experiment in registry.tuning_experiments
        if experiment.experiment_id == "baseline_current_behavior"
    )

    assert baseline.experiment_reasoning
    assert baseline.tuning_dimensions
