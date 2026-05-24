from __future__ import annotations

from app.services.study_cycle_profiles import (
    PSCPP_STUDY_CYCLE_PROFILE_ID,
    build_study_cycle_guidance_metadata,
    enrich_study_cycle_blueprint_with_profile,
    get_pscpp_study_cycle_profile,
)


def pscpp_study_cycle_profile_fixture() -> dict[str, object]:
    return get_pscpp_study_cycle_profile()


def pscpp_study_cycle_guidance_fixture(*, weekly_hours: float = 24) -> dict[str, object]:
    return build_study_cycle_guidance_metadata(
        PSCPP_STUDY_CYCLE_PROFILE_ID,
        weekly_hours=weekly_hours,
    )


def pscpp_study_cycle_blueprint_metadata_fixture(*, weekly_hours: float = 24) -> dict[str, object]:
    return enrich_study_cycle_blueprint_with_profile(
        profile_id=PSCPP_STUDY_CYCLE_PROFILE_ID,
        blueprint_metadata={"cycle_context": "guidance"},
        weekly_hours=weekly_hours,
    )
