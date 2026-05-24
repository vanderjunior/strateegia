from __future__ import annotations

from app.services.study_cycle_profiles import (
    PSCPP_STUDY_CYCLE_PROFILE_ID,
    build_study_cycle_guidance_metadata,
    enrich_study_cycle_blueprint_with_profile,
    get_pscpp_study_cycle_profile,
)


def pscpp_study_cycle_profile_fixture() -> dict[str, object]:
    return get_pscpp_study_cycle_profile()


def pscpp_study_cycle_profile_payload_fixture() -> dict[str, object]:
    return pscpp_study_cycle_profile_fixture()


def pscpp_historical_evidence_fixture() -> dict[str, object]:
    return pscpp_study_cycle_profile_fixture()["historical_exam_evidence"]


def pscpp_priority_blocks_fixture() -> list[dict[str, object]]:
    return pscpp_study_cycle_profile_fixture()["priority_blocks"]


def pscpp_phase_plan_fixture() -> list[dict[str, object]]:
    return pscpp_study_cycle_profile_fixture()["phase_plan"]


def pscpp_weekly_distribution_fixture() -> dict[str, object]:
    return pscpp_study_cycle_profile_fixture()["weekly_distribution_hint_24h"]


def pscpp_study_cycle_guidance_fixture(*, weekly_hours: float = 24) -> dict[str, object]:
    return build_study_cycle_guidance_metadata(
        PSCPP_STUDY_CYCLE_PROFILE_ID,
        weekly_hours=weekly_hours,
    )


def pscpp_scaled_weekly_distribution_fixture(*, weekly_hours: float) -> dict[str, object]:
    return pscpp_study_cycle_guidance_fixture(weekly_hours=weekly_hours)["scaled_weekly_distribution"]


def pscpp_rotating_12_session_cycle_fixture() -> list[dict[str, object]]:
    return pscpp_study_cycle_profile_fixture()["rotating_12_session_cycle"]


def pscpp_session_structure_fixture() -> dict[str, object]:
    return pscpp_study_cycle_profile_fixture()["session_structure"]


def pscpp_question_training_progression_fixture() -> dict[str, object]:
    return pscpp_study_cycle_profile_fixture()["question_training_progression"]


def pscpp_notebook_system_fixture() -> list[dict[str, object]]:
    return pscpp_study_cycle_profile_fixture()["notebook_system"]


def pscpp_question_style_bridge_fixture() -> dict[str, object]:
    return pscpp_study_cycle_profile_fixture()["question_generation_guidance"]


def pscpp_integration_metadata_fixture(*, weekly_hours: float = 24) -> dict[str, object]:
    return pscpp_study_cycle_blueprint_metadata_fixture(weekly_hours=weekly_hours)["integration_metadata"]


def pscpp_user_override_fixture(*, weekly_hours: float = 24) -> dict[str, object]:
    return {
        "not_fixed_schedule": pscpp_study_cycle_guidance_fixture(weekly_hours=weekly_hours)["not_fixed_schedule"],
        "user_override_allowed": pscpp_study_cycle_guidance_fixture(weekly_hours=weekly_hours)["user_override_allowed"],
        "profile_is_guidance_not_mandate": pscpp_study_cycle_guidance_fixture(weekly_hours=weekly_hours)[
            "profile_is_guidance_not_mandate"
        ],
    }


def pscpp_no_scheduler_mutation_fixture(*, weekly_hours: float = 24) -> dict[str, object]:
    guidance = pscpp_study_cycle_guidance_fixture(weekly_hours=weekly_hours)
    profile = pscpp_study_cycle_profile_fixture()
    return {
        "automatic_scheduler_mutation_allowed": guidance["automatic_scheduler_mutation_allowed"],
        "scheduler_mutation_disabled": guidance["integration_metadata"]["scheduler_mutation_disabled"],
        "study_cycle_runtime_mutation_disabled": guidance["integration_metadata"][
            "study_cycle_runtime_mutation_disabled"
        ],
        "runtime_mutation_performed": profile["metadata"]["runtime_mutation_performed"],
        "scheduler_mutation_performed": profile["metadata"]["scheduler_mutation_performed"],
        "calendar_mutation_performed": profile["metadata"]["calendar_mutation_performed"],
    }


def pscpp_study_cycle_blueprint_metadata_fixture(*, weekly_hours: float = 24) -> dict[str, object]:
    return enrich_study_cycle_blueprint_with_profile(
        profile_id=PSCPP_STUDY_CYCLE_PROFILE_ID,
        blueprint_metadata={"cycle_context": "guidance"},
        weekly_hours=weekly_hours,
    )


def non_pscpp_behavior_fixture() -> dict[str, object]:
    base = {"existing": True}
    return {
        "guidance": build_study_cycle_guidance_metadata("generic-study-cycle", base_metadata=base),
        "blueprint": enrich_study_cycle_blueprint_with_profile(
            profile_id="generic-study-cycle",
            blueprint_metadata=base,
        ),
    }


def pscpp_no_leakage_fixture(*, weekly_hours: float = 24) -> dict[str, object]:
    return {
        "profile": pscpp_study_cycle_profile_fixture(),
        "guidance": pscpp_study_cycle_guidance_fixture(weekly_hours=weekly_hours),
        "blueprint": pscpp_study_cycle_blueprint_metadata_fixture(weekly_hours=weekly_hours),
    }


def pscpp_no_runtime_mutation_fixture(*, weekly_hours: float = 24) -> dict[str, object]:
    guidance = pscpp_study_cycle_guidance_fixture(weekly_hours=weekly_hours)
    profile = pscpp_study_cycle_profile_fixture()
    return {
        "automatic_scheduler_mutation_allowed": guidance["automatic_scheduler_mutation_allowed"],
        "integration_metadata": guidance["integration_metadata"],
        "metadata": profile["metadata"],
    }


def stabilization_fixture_builders() -> dict[str, object]:
    return {
        "pscpp_study_cycle_profile": pscpp_study_cycle_profile_fixture,
        "pscpp_study_cycle_profile_payload": pscpp_study_cycle_profile_payload_fixture,
        "pscpp_historical_evidence": pscpp_historical_evidence_fixture,
        "pscpp_priority_blocks": pscpp_priority_blocks_fixture,
        "pscpp_phase_plan": pscpp_phase_plan_fixture,
        "pscpp_weekly_distribution": pscpp_weekly_distribution_fixture,
        "pscpp_scaled_weekly_distribution": pscpp_scaled_weekly_distribution_fixture,
        "pscpp_rotating_12_session_cycle": pscpp_rotating_12_session_cycle_fixture,
        "pscpp_session_structure": pscpp_session_structure_fixture,
        "pscpp_question_training_progression": pscpp_question_training_progression_fixture,
        "pscpp_notebook_system": pscpp_notebook_system_fixture,
        "pscpp_question_style_bridge": pscpp_question_style_bridge_fixture,
        "pscpp_integration_metadata": pscpp_integration_metadata_fixture,
        "pscpp_user_override": pscpp_user_override_fixture,
        "pscpp_no_scheduler_mutation": pscpp_no_scheduler_mutation_fixture,
        "non_pscpp_behavior": non_pscpp_behavior_fixture,
        "pscpp_no_leakage": pscpp_no_leakage_fixture,
        "pscpp_no_runtime_mutation": pscpp_no_runtime_mutation_fixture,
    }
