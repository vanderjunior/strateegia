from __future__ import annotations

from app.domain.models import (
    EmpiricalValidationCase,
    EmpiricalValidationCaseResult,
    EmpiricalValidationDataset,
    EmpiricalValidationDatasetSummary,
    EmpiricalValidationExpectation,
)
from app.services.runtime_profile_utils import average_values, clamp_value, state_message, state_reasoning
from app.services.runtime_scenario_simulation import simulate_runtime_scenario


def build_empirical_validation_dataset() -> EmpiricalValidationDataset:
    return EmpiricalValidationDataset(
        dataset_id="controlled_empirical_validation_v1",
        dataset_name="Controlled Empirical Validation Dataset",
        cases=[
            EmpiricalValidationCase(
                case_id="sustainable_retrieval_case",
                case_name="Sustainable Retrieval",
                case_category="retrieval_sustainability",
                expected_states=EmpiricalValidationExpectation(
                    expected_scenario_category="retrieval_heavy_stable",
                    expected_dataset_awareness_state="retrieval_intensive",
                    expected_scientific_validation_state="validation_stable",
                    expected_regression_signal="regression_stable",
                    expected_risk_flags=["retrieval_high"],
                    expected_case_state="case_passed",
                ),
                case_notes="Retrieval ativo com estabilidade validacional preservada.",
            ),
            EmpiricalValidationCase(
                case_id="false_fluency_case",
                case_name="False Fluency",
                case_category="false_fluency",
                expected_states=EmpiricalValidationExpectation(
                    expected_scenario_category="false_fluency_risk",
                    expected_scientific_validation_state="sustainability_watch",
                    expected_risk_flags=["false_fluency_risk"],
                    expected_case_state="case_regression_detected",
                ),
                case_notes="Reconhecimento ou retrieval parecem bons, mas a sustentabilidade e fraca.",
            ),
            EmpiricalValidationCase(
                case_id="scaffold_dependency_case",
                case_name="Scaffold Dependency",
                case_category="support_dependency",
                expected_states=EmpiricalValidationExpectation(
                    expected_scenario_category="scaffold_dependent",
                    expected_dataset_awareness_state="scaffold_sensitive",
                    expected_scientific_validation_state="sustainability_watch",
                    expected_regression_signal="support_dependency_risk",
                    expected_risk_flags=["scaffold_dependency_risk"],
                    expected_case_state="case_regression_detected",
                ),
                case_notes="Suporte alto com dependencia de scaffold e possivel fragilidade reconstrutiva.",
            ),
            EmpiricalValidationCase(
                case_id="unsafe_compression_case",
                case_name="Unsafe Compression",
                case_category="compression_risk",
                expected_states=EmpiricalValidationExpectation(
                    expected_scenario_category="compression_risky",
                    expected_scientific_validation_state="regression_watch",
                    expected_risk_flags=["compression_risk"],
                    expected_case_state="case_regression_detected",
                ),
                case_notes="Compressao agressiva demais para o suporte presente.",
            ),
            EmpiricalValidationCase(
                case_id="transfer_fragility_case",
                case_name="Transfer Fragility",
                case_category="transfer_fragility",
                expected_states=EmpiricalValidationExpectation(
                    expected_scenario_category="transfer_fragile",
                    expected_dataset_awareness_state="transfer_fragile",
                    expected_risk_flags=["transfer_fragile"],
                    expected_case_state="case_passed",
                ),
                case_notes="Transferencia contextual instavel.",
            ),
            EmpiricalValidationCase(
                case_id="reconstruction_improving_case",
                case_name="Reconstruction Improving",
                case_category="reconstruction_improvement",
                expected_states=EmpiricalValidationExpectation(
                    expected_scientific_validation_state="validation_stable",
                    expected_regression_signal="regression_stable",
                    expected_case_state="case_partially_matched",
                ),
                case_notes="Reconstrucao melhora com suporte ainda controlado.",
            ),
            EmpiricalValidationCase(
                case_id="resurfacing_effective_case",
                case_name="Resurfacing Effective",
                case_category="resurfacing_effectiveness",
                expected_states=EmpiricalValidationExpectation(
                    expected_dataset_awareness_state="stabilization_progressive",
                    expected_scientific_validation_state="validation_stable",
                    expected_risk_flags=["resurfacing_effective"],
                    expected_case_state="case_passed",
                ),
                case_notes="Resurfacing positivo com estabilizacao crescente.",
            ),
            EmpiricalValidationCase(
                case_id="continuity_degraded_case",
                case_name="Continuity Degraded",
                case_category="continuity_fragility",
                expected_states=EmpiricalValidationExpectation(
                    expected_scenario_category="continuity_degraded",
                    expected_dataset_awareness_state="continuity_fragile",
                    expected_scientific_validation_state="regression_watch",
                    expected_risk_flags=["continuity_fragile"],
                    expected_case_state="case_passed",
                ),
                case_notes="Continuity degradada com possivel impacto de pacing ou contexto.",
            ),
            EmpiricalValidationCase(
                case_id="retrieval_inflation_case",
                case_name="Retrieval Inflation",
                case_category="retrieval_inflation",
                expected_states=EmpiricalValidationExpectation(
                    expected_scenario_category="retrieval_inflated_risky",
                    expected_dataset_awareness_state="retrieval_intensive",
                    expected_regression_signal="retrieval_inflation",
                    expected_risk_flags=["retrieval_high", "regression_risk"],
                    expected_case_state="case_regression_detected",
                ),
                case_notes="Retrieval cresce sem ganho proporcional de validacao.",
            ),
            EmpiricalValidationCase(
                case_id="pedagogically_stable_baseline_case",
                case_name="Pedagogically Stable Baseline",
                case_category="stable_baseline",
                expected_states=EmpiricalValidationExpectation(
                    expected_scenario_category="pedagogically_stable",
                    expected_dataset_awareness_state="validation_ready",
                    expected_scientific_validation_state="validation_stable",
                    expected_comparative_state="behavior_consistent",
                    expected_regression_signal="regression_stable",
                    expected_case_state="case_passed",
                ),
                case_notes="Baseline equilibrada com baixa pressao regressiva.",
            ),
        ],
    )


def evaluate_empirical_validation_dataset(
    source: list[dict] | dict | None,
    dataset: EmpiricalValidationDataset | None = None,
) -> EmpiricalValidationDatasetSummary:
    current_dataset = dataset or build_empirical_validation_dataset()
    case_results = [_evaluate_case(source, case) for case in current_dataset.cases]

    passed_cases = [result.case_id for result in case_results if result.case_result_state == "case_passed"]
    failed_cases = [result.case_id for result in case_results if result.case_result_state == "case_failed"]
    inconclusive_cases = [
        result.case_id
        for result in case_results
        if result.case_result_state in {"case_inconclusive", "case_partially_matched"}
    ]
    dataset_alignment_score = average_values([result.expectation_alignment for result in case_results])
    regression_flags = sorted(
        {
            flag
            for result in case_results
            for flag in result.regression_flags
            if flag and flag != "regression_stable"
        }
    )
    state = _dataset_state(case_results, regression_flags)

    return EmpiricalValidationDatasetSummary(
        empirical_dataset_state=state,
        empirical_dataset_summary=_dataset_summary(state),
        empirical_dataset_reasoning=state_reasoning(
            "Dataset empirico",
            state,
            [
                f"Casos={len(case_results)}; passed={len(passed_cases)}; failed={len(failed_cases)}; inconclusive={len(inconclusive_cases)}.",
                f"Alignment={dataset_alignment_score:.2f}; regressions={len(regression_flags)}.",
            ],
        ),
        validation_case_results=case_results,
        passed_cases=passed_cases,
        failed_cases=failed_cases,
        inconclusive_cases=inconclusive_cases,
        dataset_alignment_score=dataset_alignment_score,
        dataset_regression_flags=regression_flags,
        dataset_coverage_summary=f"passed={len(passed_cases)} failed={len(failed_cases)} inconclusive={len(inconclusive_cases)} total={len(case_results)}",
        empirical_validation_context=f"{current_dataset.dataset_name} ({current_dataset.dataset_id})",
        why_this_dataset_result=_why_dataset(state),
    )


def _evaluate_case(
    source: list[dict] | dict | None,
    case: EmpiricalValidationCase,
) -> EmpiricalValidationCaseResult:
    scenario_result = simulate_runtime_scenario(source)
    observed_states = dict(scenario_result.scenario_observed_states or {})
    expected_states = case.expected_states.model_dump(mode="json")
    alignment, mismatches = _alignment(case.expected_states, scenario_result)
    regression_flags = sorted(
        set(list(observed_states.get("risk_flags") or []) + [scenario_result.scenario_regression_signal])
    )
    case_result_state = _case_result_state(case.expected_states, scenario_result, alignment, mismatches)

    return EmpiricalValidationCaseResult(
        case_id=case.case_id,
        case_name=case.case_name,
        case_category=case.case_category,
        expected_states=expected_states,
        observed_states=observed_states,
        expectation_alignment=round(alignment, 4),
        case_result_state=case_result_state,
        case_reasoning=state_reasoning(
            "Caso empirico",
            case_result_state,
            [
                f"Esperado={case.expected_states.expected_scenario_category or 'n/a'}; observado={scenario_result.scenario_category or 'n/a'}.",
                f"Alinhamento={alignment:.2f}; regressao={scenario_result.scenario_regression_signal or 'regression_stable'}.",
            ],
        ),
        mismatch_reasons=mismatches,
        regression_flags=regression_flags,
        validation_confidence=round(clamp_value((scenario_result.scenario_replay_snapshot or {}).get("validation_confidence", 0.0)), 4),
        why_this_case_result=_why_case(case_result_state),
    )


def _alignment(
    expected: EmpiricalValidationExpectation,
    scenario_result,
) -> tuple[float, list[str]]:
    observed_states = dict(scenario_result.scenario_observed_states or {})
    mismatches: list[str] = []
    checks: list[bool] = []

    mapping = {
        "expected_scenario_category": scenario_result.scenario_category,
        "expected_validation_state": observed_states.get("pedagogical_validation_state") or "",
        "expected_dataset_awareness_state": observed_states.get("validation_dataset_state") or "",
        "expected_scientific_validation_state": observed_states.get("scientific_validation_state") or "",
        "expected_comparative_state": observed_states.get("comparative_session_state") or "",
        "expected_regression_signal": observed_states.get("pedagogical_regression_signal") or "",
    }
    for field_name, observed_value in mapping.items():
        expected_value = getattr(expected, field_name)
        if not expected_value:
            continue
        matched = expected_value == observed_value
        checks.append(matched)
        if not matched:
            mismatches.append(f"{field_name}={observed_value}")

    if expected.expected_risk_flags:
        observed_flags = set(observed_states.get("risk_flags") or [])
        matched = set(expected.expected_risk_flags).issubset(observed_flags)
        checks.append(matched)
        if not matched:
            mismatches.append(f"risk_flags={sorted(observed_flags)}")

    if not checks:
        return 0.0, ["sem expectativas avaliaveis"]
    return average_values([1.0 if matched else 0.0 for matched in checks]), mismatches


def _case_result_state(
    expected: EmpiricalValidationExpectation,
    scenario_result,
    alignment: float,
    mismatches: list[str],
) -> str:
    if scenario_result.runtime_scenario_state == "scenario_inconclusive":
        return "case_inconclusive"
    if expected.expected_case_state == "case_regression_detected":
        observed_states = dict(scenario_result.scenario_observed_states or {})
        observed_flags = set(observed_states.get("risk_flags") or [])
        expected_flags = set(expected.expected_risk_flags or [])
        if scenario_result.scenario_validation_outcome == "regression_detected":
            return "case_regression_detected"
        if alignment >= 0.999 and expected_flags and expected_flags.issubset(observed_flags):
            return "case_regression_detected"
        if alignment >= 0.6:
            return "case_partially_matched"
        return "case_failed"
    if alignment >= 0.999:
        return "case_passed"
    if alignment >= 0.6:
        return "case_partially_matched"
    if mismatches:
        return "case_failed"
    return "case_inconclusive"


def _dataset_state(
    case_results: list[EmpiricalValidationCaseResult],
    regression_flags: list[str],
) -> str:
    if not case_results or all(result.case_result_state == "case_inconclusive" for result in case_results):
        return "dataset_inconclusive"
    if regression_flags:
        return "dataset_regression_detected"
    if all(result.case_result_state == "case_passed" for result in case_results):
        return "dataset_validated"
    return "dataset_mixed"


def _dataset_summary(state: str) -> str:
    return state_message(
        state,
        {
            "dataset_validated": "O dataset empirico controlado foi majoritariamente validado.",
            "dataset_mixed": "O dataset empirico mostrou mistura de correspondencias e desvios.",
            "dataset_regression_detected": "O dataset empirico detectou pelo menos um risco regressivo relevante.",
            "dataset_inconclusive": "O dataset empirico permaneceu inconclusivo para o contexto atual.",
        },
        "O dataset empirico permaneceu em faixa observacional neutra.",
    )


def _why_dataset(state: str) -> str:
    return state_message(
        state,
        {
            "dataset_validated": "Os casos controlados convergiram para os resultados esperados.",
            "dataset_mixed": "Parte dos casos convergiu, mas ainda houve desvios ou matches parciais.",
            "dataset_regression_detected": "Ao menos um caso controlado expôs risco regressivo ou dependencia excessiva.",
            "dataset_inconclusive": "Os sinais observados nao bastaram para avaliar o dataset de forma forte.",
        },
        "O dataset permaneceu observacionalmente neutro.",
    )


def _why_case(state: str) -> str:
    return state_message(
        state,
        {
            "case_passed": "O caso controlado convergiu com as expectativas definidas.",
            "case_failed": "O caso controlado nao reproduziu os sinais esperados.",
            "case_inconclusive": "O caso controlado nao teve evidencia suficiente.",
            "case_partially_matched": "O caso controlado reproduziu apenas parte da expectativa.",
            "case_regression_detected": "O caso controlado confirmou o risco regressivo esperado.",
        },
        "O caso permaneceu observacionalmente neutro.",
    )
