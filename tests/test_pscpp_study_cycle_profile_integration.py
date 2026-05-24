from __future__ import annotations

from app.services.study_cycle_profiles import (
    build_study_cycle_guidance_metadata,
    enrich_study_cycle_blueprint_with_profile,
)
from tests.fixtures.study_cycle_profiles import (
    pscpp_study_cycle_blueprint_metadata_fixture,
    pscpp_study_cycle_guidance_fixture,
)


def test_pscpp_study_cycle_guidance_metadata_integration_is_complete():
    metadata = pscpp_study_cycle_blueprint_metadata_fixture()

    assert metadata["study_cycle_profile_id"] == "marinha_dpc_pscpp_praticagem_study_cycle"
    assert metadata["exam_profile_id"] == "marinha_dpc_pscpp_praticagem"
    assert metadata["profile_type"] == "flexible_study_cycle_guidance"
    assert metadata["not_fixed_schedule"] is True
    assert metadata["user_override_allowed"] is True
    assert metadata["automatic_scheduler_mutation_allowed"] is False
    assert metadata["integration_metadata"]["question_style_profile_id"] == "marinha_dpc_pscpp_praticagem"
    assert metadata["integration_metadata"]["use_pscpp_question_style_profile"] is True
    assert metadata["question_generation_guidance"]["question_generation_profile_id"] == "marinha_dpc_pscpp_praticagem"


def test_pscpp_study_cycle_weekly_scaling_preserves_proportions():
    scaled = pscpp_study_cycle_guidance_fixture(weekly_hours=12)
    weekly = scaled["scaled_weekly_distribution"]

    assert weekly["total_hours"] == 12.0
    assert weekly["scaling_ratio"] == 0.5
    assert weekly["manoeuvrability_shiphandling_tugs"] == 3.0
    assert weekly["colreg_lights_marks_cis"] == 2.0
    assert weekly["restricted_navigation_radar_ecdis_tides"] == 2.0
    assert weekly["arte_naval"] == 1.5
    assert weekly["legislation_normam_tribunal_praticagem"] == 1.5
    assert weekly["meteorology_oceanography"] == 1.0
    assert weekly["communications_smcp_gmdss"] == 0.5
    assert weekly["cumulative_review_error_notebook"] == 0.5


def test_non_pscpp_study_cycle_behavior_remains_unchanged():
    base = {"existing": True}
    assert build_study_cycle_guidance_metadata("generic-study-cycle", base_metadata=base) == {"existing": True}
    assert enrich_study_cycle_blueprint_with_profile(
        profile_id="generic-study-cycle",
        blueprint_metadata=base,
    ) == {"existing": True}
