from __future__ import annotations

import json

from tests.fixtures.question_style_profiles import (
    pscpp_direct_metadata_fixture,
    pscpp_draft_fixture,
    pscpp_ready_blueprint_fixture,
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


def test_pscpp_generation_metadata_security_and_determinism(tmp_path):
    first = pscpp_direct_metadata_fixture(context="fixation")
    second = pscpp_direct_metadata_fixture(context="fixation")
    fixture = pscpp_ready_blueprint_fixture(tmp_path)
    blueprint_set = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )

    assert first == second
    dumped = {
        "helper": first,
        "blueprint": blueprint_set.model_dump(mode="json"),
    }
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
        "gabarito_final",
        "correctness",
        "is_correct",
        "password_hash",
        "session_token",
    ):
        assert forbidden not in dumped_keys
    for forbidden in ("/Users/", "/private/", "OCR/base64", "raw document body", "storage_root"):
        assert forbidden not in serialized


def test_pscpp_draft_security_preserves_review_only_without_answer_key_or_paths(tmp_path):
    draft_set = pscpp_draft_fixture(tmp_path)
    dumped = draft_set.model_dump(mode="json")
    serialized = json.dumps(dumped, ensure_ascii=True)
    dumped_keys = _collect_keys(dumped)

    assert draft_set.drafts[0].metadata["human_review_required_for_answer_key"] is True
    assert draft_set.drafts[0].metadata["selected_question_archetype"] == "technical_operational_scenario"
    for forbidden in (
        "correct_answer",
        "correct_option",
        "answer_key",
        "answer_key_value",
        "final_answer_key",
        "final_answer_key_content",
        "gabarito",
        "gabarito_final",
        "correctness",
        "is_correct",
    ):
        assert forbidden not in dumped_keys
    for forbidden in ("/Users/", "/private/", "raw document body", "OCR/base64", "storage_root"):
        assert forbidden not in serialized
