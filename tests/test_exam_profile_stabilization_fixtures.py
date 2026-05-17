import json
from io import BytesIO

from fastapi.testclient import TestClient

from app.main import create_app
from app.repositories.json_store import JsonStudyRepository
from app.services.exam_profiles import ExamProfileService
from tests.fixtures.exam_profile_edital_documents import (
    ALL_EXAM_PROFILE_FIXTURE_BUILDERS,
    aocp_multiple_choice_5_edital_text,
    build_edital_result_from_text,
    cebraspe_true_false_with_negative_marking_edital_text,
    cebraspe_with_multiple_choice_5_edital_text,
    cebraspe_without_explicit_ce_edital_text,
    conflicting_ce_and_ae_edital_text,
    fgv_discursive_mixed_edital_text,
    fgv_multiple_choice_5_edital_text,
    five_options_with_negative_marking_edital_text,
    ibfc_multiple_choice_4_edital_text,
    marinha_generic_military_without_pscpp_edital_text,
    marinha_pscpp_dpc_normam_edital_text,
    negative_marking_without_ce_edital_text,
    pscpp_textual_bibliography_driven_edital_text,
    pscpp_with_external_fgv_board_edital_text,
    quadrix_multiple_choice_5_edital_text,
    quadrix_true_false_edital_text,
    true_false_without_board_edital_text,
    true_false_without_negative_marking_edital_text,
    unknown_board_multiple_choice_5_edital_text,
    unknown_generic_edital_text,
)


def suggest_from_text(text: str, *, edital_id: str = "edital:test"):
    return ExamProfileService().suggest_exam_profile_from_edital(build_edital_result_from_text(edital_id, text))


def create_clients(tmp_path):
    repository = JsonStudyRepository(tmp_path / "study_data.json")
    app = create_app(repository=repository)
    return TestClient(app), TestClient(app), TestClient(app), repository


def register_and_login(client: TestClient, username: str) -> None:
    registered = client.post(
        "/api/auth/register",
        json={
            "username": username,
            "password": "senha-segura-123",
            "display_name": username.title(),
            "email": f"{username}@example.com",
        },
    )
    assert registered.status_code == 201
    logged_in = client.post("/api/auth/login", json={"username": username, "password": "senha-segura-123"})
    assert logged_in.status_code == 200


def upload_and_process_material(client: TestClient, filename: str, content: bytes) -> dict[str, object]:
    uploaded = client.post("/api/materials/upload", files={"file": (filename, BytesIO(content), "text/markdown")})
    assert uploaded.status_code == 201
    document_id = uploaded.json()["metadata"]["document_id"]
    processed = client.post(f"/api/materials/{document_id}/process")
    assert processed.status_code == 200
    return uploaded.json()


def assert_json_safe(payload) -> None:
    dumped = json.dumps(payload.model_dump(mode="json") if hasattr(payload, "model_dump") else payload, ensure_ascii=True)
    assert "password_hash" not in dumped
    assert "/uploads/" not in dumped


def test_exam_profile_fixture_sanity_is_deterministic_and_json_safe():
    for builder in ALL_EXAM_PROFILE_FIXTURE_BUILDERS:
        first = builder()
        second = builder()
        assert first == second
        json.dumps({"text": first}, ensure_ascii=True)
        assert len(first) < 1200


def test_cebraspe_and_true_false_fixtures_remain_conservative():
    explicit = suggest_from_text(cebraspe_true_false_with_negative_marking_edital_text(), edital_id="edital:ce-tf")
    without_ce = suggest_from_text(cebraspe_without_explicit_ce_edital_text(), edital_id="edital:ce-unknown")
    no_board = suggest_from_text(true_false_without_board_edital_text(), edital_id="edital:tf")
    no_negative = suggest_from_text(true_false_without_negative_marking_edital_text(), edital_id="edital:tf-no-neg")

    assert explicit.profile_id == "exam-profile:cebraspe"
    assert explicit.board_id == "board:cebraspe"
    assert explicit.format_type == "true_false"
    assert explicit.scoring_confidence >= 0.8
    assert explicit.scoring_evidence
    assert explicit.metadata["negative_marking_confirmed"] is True

    assert without_ce.profile_id == "exam-profile:cebraspe"
    assert without_ce.format_type in {"unknown", None}
    assert without_ce.confidence <= 0.7
    assert {item.code for item in without_ce.warnings} >= {"format_requires_confirmation", "board_style_used_as_fallback"}

    assert no_board.profile_id is None
    assert no_board.board_id is None
    assert no_board.format_type == "true_false"
    assert no_board.format_confidence >= 0.8

    assert no_negative.format_type == "true_false"
    assert no_negative.scoring_confidence <= 0.5
    assert no_negative.metadata["negative_marking_confirmed"] is False


def test_cebraspe_fgv_and_unknown_multiple_choice_fixtures_respect_explicit_format():
    cebraspe_ae = suggest_from_text(cebraspe_with_multiple_choice_5_edital_text(), edital_id="edital:ce-ae")
    fgv_ae = suggest_from_text(fgv_multiple_choice_5_edital_text(), edital_id="edital:fgv-ae")
    unknown_ae = suggest_from_text(unknown_board_multiple_choice_5_edital_text(), edital_id="edital:unknown-ae")

    assert cebraspe_ae.profile_id == "exam-profile:cebraspe"
    assert cebraspe_ae.board_id == "board:cebraspe"
    assert cebraspe_ae.format_type == "multiple_choice_5"
    assert cebraspe_ae.format_confidence >= cebraspe_ae.board_confidence

    assert fgv_ae.profile_id == "exam-profile:fgv"
    assert fgv_ae.board_id == "board:fgv"
    assert fgv_ae.format_type == "multiple_choice_5"
    assert fgv_ae.selection_reasoning

    assert unknown_ae.profile_id is None
    assert unknown_ae.board_id is None
    assert unknown_ae.format_type == "multiple_choice_5"
    assert unknown_ae.format_confidence >= 0.8


def test_fgv_discursive_and_negative_marking_cases_keep_format_and_scoring_separate():
    fgv_mixed = suggest_from_text(fgv_discursive_mixed_edital_text(), edital_id="edital:fgv-mixed")
    scoring_only = suggest_from_text(negative_marking_without_ce_edital_text(), edital_id="edital:score-only")
    ae_negative = suggest_from_text(five_options_with_negative_marking_edital_text(), edital_id="edital:ae-negative")

    assert fgv_mixed.profile_id == "exam-profile:fgv"
    assert fgv_mixed.format_type in {"mixed", "discursive"}
    assert "discursive_module_detected" in {item.code for item in fgv_mixed.warnings}

    assert scoring_only.format_type in {"unknown", None}
    assert scoring_only.profile_id is None
    assert scoring_only.scoring_confidence >= 0.5
    assert scoring_only.board_id is None

    assert ae_negative.format_type == "multiple_choice_5"
    assert ae_negative.scoring_confidence >= 0.5
    assert ae_negative.metadata["negative_marking_confirmed"] is True


def test_pscpp_family_priority_and_bibliography_driven_cases_are_preserved():
    pscpp = suggest_from_text(marinha_pscpp_dpc_normam_edital_text(), edital_id="edital:pscpp")
    pscpp_fgv = suggest_from_text(pscpp_with_external_fgv_board_edital_text(), edital_id="edital:pscpp-fgv")
    pscpp_biblio = suggest_from_text(pscpp_textual_bibliography_driven_edital_text(), edital_id="edital:pscpp-biblio")
    marinha_generic = suggest_from_text(marinha_generic_military_without_pscpp_edital_text(), edital_id="edital:marinha-generic")

    assert pscpp.profile_id == "exam-profile:marinha-pscpp"
    assert pscpp.exam_family == "PSCPP"
    assert pscpp.family_confidence >= 0.8
    assert pscpp.family_evidence

    assert pscpp_fgv.profile_id == "exam-profile:marinha-pscpp"
    assert pscpp_fgv.board_id == "board:fgv"
    assert pscpp_fgv.exam_family == "PSCPP"
    assert "exam_family_over_board" in {item.code for item in pscpp_fgv.warnings}
    assert pscpp_fgv.format_type == "multiple_choice_5"

    profile = ExamProfileService().get_exam_profile("exam-profile:marinha-pscpp")
    assert profile.generation_profile.allow_english_terms is True
    assert profile.content_behavior_profile.bibliography_weight == "high"
    assert pscpp_biblio.profile_id == "exam-profile:marinha-pscpp"
    assert pscpp_biblio.family_evidence

    assert marinha_generic.profile_id is None
    assert marinha_generic.exam_family is None
    assert marinha_generic.confidence <= 0.5


def test_quadrix_ibfc_and_aocp_cases_use_explicit_format_without_board_overclaim():
    quadrix_tf = suggest_from_text(quadrix_true_false_edital_text(), edital_id="edital:quadrix-tf")
    quadrix_ae = suggest_from_text(quadrix_multiple_choice_5_edital_text(), edital_id="edital:quadrix-ae")
    ibfc_ad = suggest_from_text(ibfc_multiple_choice_4_edital_text(), edital_id="edital:ibfc-ad")
    aocp_ae = suggest_from_text(aocp_multiple_choice_5_edital_text(), edital_id="edital:aocp-ae")

    assert quadrix_tf.board_id == "board:quadrix"
    assert quadrix_tf.format_type == "true_false"
    assert quadrix_tf.profile_id is None

    assert quadrix_ae.board_id == "board:quadrix"
    assert quadrix_ae.format_type == "multiple_choice_5"
    assert quadrix_ae.profile_id is None

    assert ibfc_ad.board_id == "board:ibfc"
    assert ibfc_ad.format_type == "multiple_choice_4"

    assert aocp_ae.board_id == "board:aocp"
    assert aocp_ae.format_type == "multiple_choice_5"


def test_unknown_and_conflicting_cases_remain_low_confidence_and_json_safe():
    unknown = suggest_from_text(unknown_generic_edital_text(), edital_id="edital:unknown")
    conflicting = suggest_from_text(conflicting_ce_and_ae_edital_text(), edital_id="edital:conflict")

    assert unknown is not None
    assert unknown.profile_id is None
    assert unknown.confidence <= 0.5

    assert conflicting.profile_id is None
    assert conflicting.confidence <= 0.5
    assert "ambiguous_exam_profile_signals" in {item.code for item in conflicting.warnings}

    assert_json_safe(unknown)
    assert_json_safe(conflicting)


def test_exam_profile_fixture_suggestions_are_deterministic():
    first = suggest_from_text(pscpp_with_external_fgv_board_edital_text(), edital_id="edital:stable")
    second = suggest_from_text(pscpp_with_external_fgv_board_edital_text(), edital_id="edital:stable")

    assert first.model_dump(mode="json") == second.model_dump(mode="json")
    assert_json_safe(first)


def test_exam_profile_suggestion_api_returns_hardened_shape_and_enforces_ownership(tmp_path):
    owner, other, anonymous, repository = create_clients(tmp_path)
    register_and_login(owner, "owner")
    register_and_login(other, "other")

    uploaded = upload_and_process_material(
        owner,
        "edital.md",
        cebraspe_true_false_with_negative_marking_edital_text().encode("utf-8"),
    )
    document_id = uploaded["metadata"]["document_id"]
    ingest = owner.post(f"/api/materials/{document_id}/edital/ingest")
    assert ingest.status_code == 200
    edital_id = ingest.json()["edital_id"]

    suggested = owner.post(f"/api/edital/{edital_id}/exam-profile/suggest")
    loaded = owner.get(f"/api/edital/{edital_id}/exam-profile/suggestion")

    assert suggested.status_code == 200
    assert loaded.status_code == 200
    assert loaded.json()["board_id"] == "board:cebraspe"
    assert loaded.json()["format_type"] == "true_false"
    assert loaded.json()["scoring_confidence"] >= 0.8
    assert loaded.json()["format_evidence"]
    assert loaded.json()["scoring_evidence"]
    assert "selection_reasoning" in loaded.json()
    assert "password_hash" not in json.dumps(loaded.json(), ensure_ascii=True)

    assert anonymous.post(f"/api/edital/{edital_id}/exam-profile/suggest").status_code == 401
    assert other.post(f"/api/edital/{edital_id}/exam-profile/suggest").status_code == 404
    assert other.get(f"/api/edital/{edital_id}/exam-profile/suggestion").status_code == 404
