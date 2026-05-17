import json

from app.domain.models import EditalExtractionResult
from app.services.exam_profiles import ExamProfileService


def test_exam_profiles_are_available_stable_and_json_safe():
    service = ExamProfileService()

    first = service.list_exam_profiles()
    second = service.list_exam_profiles()

    assert [item.profile_id for item in first] == ["exam-profile:cebraspe", "exam-profile:fgv", "exam-profile:marinha-pscpp"]
    assert [item.profile_id for item in first] == [item.profile_id for item in second]
    assert service.get_exam_profile("exam-profile:unknown") is None

    for profile in first:
        dumped = json.dumps(profile.model_dump(mode="json"), ensure_ascii=True)
        assert "password_hash" not in dumped
        assert "/uploads/" not in dumped


def test_cebraspe_profile_is_conservative_and_declarative():
    profile = ExamProfileService().get_exam_profile("exam-profile:cebraspe")

    assert profile is not None
    assert profile.exam_board == "CEBRASPE"
    assert profile.question_format.format_type in {"true_false", "objective"}
    assert profile.question_format.supports_true_false is True
    assert profile.question_format.supports_multiple_choice is False
    assert profile.scoring_profile.scoring_type in {"right_wrong", "unknown"}
    assert profile.scoring_profile.penalty_hint is True
    assert profile.cognitive_demand_profile.reading_precision_demand == "high"
    assert profile.cognitive_demand_profile.trap_sensitivity == "high"
    assert profile.question_format.expected_question_count >= 0
    assert profile.question_format.question_count_range[0] <= profile.question_format.question_count_range[1]
    assert profile.summary.format_summary
    assert profile.summary.limitation_summary


def test_fgv_profile_is_conservative_and_declarative():
    profile = ExamProfileService().get_exam_profile("exam-profile:fgv")

    assert profile is not None
    assert profile.exam_board == "FGV"
    assert profile.question_format.format_type in {"multiple_choice", "objective"}
    assert profile.question_format.supports_multiple_choice is True
    assert profile.question_format.answer_options == ["A", "B", "C", "D", "E"]
    assert profile.question_format.supports_true_false is False
    assert profile.cognitive_demand_profile.interpretation_demand in {"medium", "high"}
    assert profile.cognitive_demand_profile.application_demand in {"medium", "high"}
    assert profile.cognitive_demand_profile.time_pressure_sensitivity in {"medium", "high"}
    assert profile.summary.timing_summary
    assert profile.description


def test_marinha_pscpp_profile_is_conservative_and_declarative():
    profile = ExamProfileService().get_exam_profile("exam-profile:marinha-pscpp")

    assert profile is not None
    assert profile.exam_board == "MARINHA_PSCPP"
    assert profile.question_format.format_type in {"objective", "mixed"}
    assert profile.question_format.supports_multiple_choice is True
    assert profile.question_format.question_count_range[0] == 50
    assert profile.question_format.question_count_range[1] == 100
    assert profile.cognitive_demand_profile.application_demand in {"medium", "high"}
    assert profile.cognitive_demand_profile.reading_precision_demand in {"medium", "high"}
    behavior_types = {item.behavior_type for item in profile.board_behavior_hints}
    assert "jurisprudence_or_normative_detail" in behavior_types or "formula_or_data_recall" in behavior_types
    assert profile.summary.cognitive_demand_summary


def test_exam_profile_lookup_by_board_is_stable():
    service = ExamProfileService()

    assert service.get_exam_profile_for_board("CEBRASPE").profile_id == "exam-profile:cebraspe"
    assert service.get_exam_profile_for_board("fgv").profile_id == "exam-profile:fgv"
    assert service.get_exam_profile_for_board("Marinha / PSCPP").profile_id == "exam-profile:marinha-pscpp"
    assert service.get_exam_profile_for_board("unknown") is None


def test_exam_profile_suggestion_is_safe_and_side_effect_free():
    service = ExamProfileService()

    cebraspe = EditalExtractionResult(
        edital_id="edital:cebraspe",
        document_id="doc:1",
        source_text_length=120,
        metadata={"source_text_preview": "Banca CEBRASPE. Julgue os itens seguintes em CERTO ou ERRADO."},
    )
    fgv = EditalExtractionResult(
        edital_id="edital:fgv",
        document_id="doc:2",
        source_text_length=120,
        metadata={"source_text_preview": "Fundacao Getulio Vargas - FGV. Prova objetiva com alternativas A, B, C, D e E."},
    )
    marinha = EditalExtractionResult(
        edital_id="edital:marinha",
        document_id="doc:3",
        source_text_length=120,
        metadata={"source_text_preview": "Marinha do Brasil. PSCPP. Praticagem e Autoridade Maritima."},
    )
    ambiguous = EditalExtractionResult(
        edital_id="edital:amb",
        document_id="doc:4",
        source_text_length=120,
        metadata={"source_text_preview": "FGV e CEBRASPE aparecem em anexos comparativos sem banca definida."},
    )
    unknown = EditalExtractionResult(
        edital_id="edital:unknown",
        document_id="doc:5",
        source_text_length=120,
        metadata={"source_text_preview": "Processo seletivo com prova objetiva sem identificacao clara da banca."},
    )

    cebraspe_selection = service.suggest_exam_profile_from_edital(cebraspe)
    fgv_selection = service.suggest_exam_profile_from_edital(fgv)
    marinha_selection = service.suggest_exam_profile_from_edital(marinha)
    ambiguous_selection = service.suggest_exam_profile_from_edital(ambiguous)
    unknown_selection = service.suggest_exam_profile_from_edital(unknown)

    assert cebraspe_selection is not None
    assert cebraspe_selection.profile_id == "exam-profile:cebraspe"
    assert cebraspe_selection.confidence >= 0.7
    assert cebraspe_selection.reasoning

    assert fgv_selection is not None
    assert fgv_selection.profile_id == "exam-profile:fgv"
    assert fgv_selection.confidence >= 0.7

    assert marinha_selection is not None
    assert marinha_selection.profile_id == "exam-profile:marinha-pscpp"
    assert marinha_selection.confidence >= 0.7

    assert ambiguous_selection is not None
    assert ambiguous_selection.profile_id is None
    assert ambiguous_selection.confidence <= 0.5
    assert ambiguous_selection.warnings

    assert unknown_selection is None or unknown_selection.profile_id is None
