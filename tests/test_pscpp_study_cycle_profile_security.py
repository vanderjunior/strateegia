from __future__ import annotations

import json

from tests.fixtures.study_cycle_profiles import (
    pscpp_study_cycle_blueprint_metadata_fixture,
    pscpp_study_cycle_guidance_fixture,
    pscpp_study_cycle_profile_fixture,
)


def _collect_keys(value):
    if isinstance(value, dict):
        keys = set(value)
        for item in value.values():
            keys.update(_collect_keys(item))
        return keys
    if isinstance(value, list):
        keys = set()
        for item in value:
            keys.update(_collect_keys(item))
        return keys
    return set()


def test_pscpp_study_cycle_payloads_are_secure_and_deterministic():
    profile = pscpp_study_cycle_profile_fixture()
    guidance = pscpp_study_cycle_guidance_fixture()
    blueprint = pscpp_study_cycle_blueprint_metadata_fixture()
    repeated = pscpp_study_cycle_guidance_fixture()

    assert guidance == repeated
    dumped = {"profile": profile, "guidance": guidance, "blueprint": blueprint}
    serialized = json.dumps(dumped, ensure_ascii=True)
    dumped_keys = _collect_keys(dumped)

    for forbidden in (
        "correct_answer",
        "correct_option",
        "answer_key",
        "answer_key_value",
        "final_answer_key",
        "final_answer_key_content",
        "gabarito",
        "correctness",
        "is_correct",
        "password_hash",
        "session_token",
    ):
        assert forbidden not in dumped_keys
    for forbidden in ("/Users/", "/private/", "raw document body", "OCR/base64", "storage_root"):
        assert forbidden not in serialized


def test_pscpp_study_cycle_guidance_never_mutates_runtime_or_scheduler():
    guidance = pscpp_study_cycle_guidance_fixture()

    assert guidance["automatic_scheduler_mutation_allowed"] is False
    assert guidance["integration_metadata"]["scheduler_mutation_disabled"] is True
    assert guidance["integration_metadata"]["study_cycle_runtime_mutation_disabled"] is True
    assert guidance["profile_is_guidance_not_mandate"] is True
    assert guidance["user_override_allowed"] is True
