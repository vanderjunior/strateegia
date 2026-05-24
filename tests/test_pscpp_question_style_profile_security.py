from __future__ import annotations

import json

from tests.fixtures.question_style_profiles import (
    pscpp_draft_fixture,
    pscpp_profile_fixture,
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


def test_pscpp_profile_and_blueprint_payloads_do_not_leak_answer_keys_or_paths(tmp_path):
    profile = pscpp_profile_fixture()
    fixture = pscpp_ready_blueprint_fixture(tmp_path)
    blueprint_set = fixture.context.blueprint_service.build_blueprint_set(
        fixture.simulado_blueprint.blueprint_id,
        user_id=fixture.context.user_id,
    )

    dumped = json.dumps(
        {
            "profile": profile,
            "blueprint_set": blueprint_set.model_dump(mode="json"),
        },
        ensure_ascii=True,
    )
    dumped_keys = _collect_keys(
        {
            "profile": profile,
            "blueprint_set": blueprint_set.model_dump(mode="json"),
        }
    )
    for forbidden in (
        "correct_answer",
        "correct_option",
        "answer_key",
        "answer_key_value",
        "final_answer_key_content",
        "gabarito",
        "correctness",
        "is_correct",
        "password_hash",
        "session_token",
    ):
        assert forbidden not in dumped_keys
    for forbidden in ("OCR/base64", "file://", "/Users/", "/private/"):
        assert forbidden not in dumped


def test_pscpp_draft_payload_is_json_safe_bounded_and_review_only(tmp_path):
    draft_set = pscpp_draft_fixture(tmp_path)
    dumped = draft_set.model_dump(mode="json")
    serialized = json.dumps(dumped, ensure_ascii=True)
    dumped_keys = _collect_keys(dumped)

    assert draft_set.no_answer_key_generated is True
    assert draft_set.no_final_alternatives_generated is True
    assert draft_set.no_distractors_generated is True
    assert draft_set.drafts[0].review_required is True
    assert draft_set.drafts[0].finalization_blocked is True
    assert len(draft_set.drafts[0].metadata["visible_source_titles"]) <= 5
    for forbidden in (
        "correct_answer",
        "correct_option",
        "answer_key",
        "answer_key_value",
        "final_answer_key_content",
        "gabarito",
        "password_hash",
        "session_token",
    ):
        assert forbidden not in dumped_keys
    for forbidden in ("raw document body", "OCR/base64", "/Users/", "/private/"):
        assert forbidden not in serialized
