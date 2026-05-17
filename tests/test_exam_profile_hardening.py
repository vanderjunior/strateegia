import json

from app.domain.models import EditalExtractionResult
from app.services.exam_profiles import ExamProfileService


def _edital(edital_id: str, preview: str) -> EditalExtractionResult:
    return EditalExtractionResult(
        edital_id=edital_id,
        document_id=f"doc:{edital_id}",
        source_text_length=len(preview),
        metadata={"source_text_preview": preview},
    )


def test_exam_profiles_expose_board_format_generation_and_scoring_separately():
    service = ExamProfileService()

    profile = service.get_exam_profile("exam-profile:cebraspe")

    assert profile is not None
    assert profile.board_profile.board_id == "board:cebraspe"
    assert profile.question_format.format_type in {"unknown", "objective", "true_false"}
    assert profile.generation_profile.generation_style == "assertion_based"
    assert profile.scoring_profile.explicit_scoring_confirmed is False
    assert profile.scoring_profile.scoring_source in {"board_default", "unknown"}
    assert json.dumps(profile.model_dump(mode="json"), ensure_ascii=True)


def test_pscpp_family_has_priority_over_board_name_when_detected():
    service = ExamProfileService()
    result = service.suggest_exam_profile_from_edital(
        _edital(
            "edital:pscpp-fgv",
            "FGV organizadora. Processo seletivo PSCPP da DPC com NORMAM-311, Praticagem e Autoridade Maritima.",
        )
    )

    assert result is not None
    assert result.profile_id == "exam-profile:marinha-pscpp"
    assert result.board_id == "board:fgv"
    assert result.exam_family == "PSCPP"
    assert result.family_confidence >= result.board_confidence
    assert result.family_evidence
    assert result.board_evidence
    warning_codes = {item.code for item in result.warnings}
    assert "exam_family_over_board" in warning_codes


def test_explicit_format_has_priority_over_board_default():
    service = ExamProfileService()
    result = service.suggest_exam_profile_from_edital(
        _edital(
            "edital:cebraspe-ae",
            "Banca CEBRASPE. Prova objetiva com alternativas A, B, C, D e E.",
        )
    )

    assert result is not None
    assert result.profile_id == "exam-profile:cebraspe"
    assert result.board_id == "board:cebraspe"
    assert result.format_type == "multiple_choice_5"
    assert result.format_confidence >= result.board_confidence
    assert "A, B, C, D, E" in " ".join(result.format_evidence) or result.format_evidence


def test_cebraspe_without_explicit_format_requires_confirmation():
    service = ExamProfileService()
    result = service.suggest_exam_profile_from_edital(
        _edital(
            "edital:cebraspe-unknown",
            "Banca CEBRASPE. Prova objetiva. Conteudo programatico e bibliografia.",
        )
    )

    assert result is not None
    assert result.profile_id == "exam-profile:cebraspe"
    assert result.format_type in {"unknown", None}
    assert result.format_confidence <= 0.5
    warning_codes = {item.code for item in result.warnings}
    assert "format_requires_confirmation" in warning_codes
    assert "board_style_used_as_fallback" in warning_codes


def test_explicit_true_false_and_multiple_choice_without_board_are_detected():
    service = ExamProfileService()
    true_false = service.suggest_exam_profile_from_edital(
        _edital("edital:tf", "Julgue os itens seguintes em CERTO ou ERRADO, marcando campo C ou campo E.")
    )
    multiple_choice = service.suggest_exam_profile_from_edital(
        _edital("edital:mc5", "Prova objetiva com cinco alternativas: A, B, C, D e E.")
    )

    assert true_false is not None
    assert true_false.profile_id is None
    assert true_false.format_type == "true_false"
    assert true_false.board_id is None

    assert multiple_choice is not None
    assert multiple_choice.profile_id is None
    assert multiple_choice.format_type == "multiple_choice_5"
    assert multiple_choice.board_id is None


def test_conflicting_explicit_formats_return_ambiguous_candidate():
    service = ExamProfileService()
    result = service.suggest_exam_profile_from_edital(
        _edital(
            "edital:conflict",
            "Julgue os itens em CERTO ou ERRADO. A prova tambem menciona alternativas A, B, C, D e E para marcacao.",
        )
    )

    assert result is not None
    assert result.profile_id is None
    assert result.confidence <= 0.5
    warning_codes = {item.code for item in result.warnings}
    assert "conflicting_board_and_format" in warning_codes or "ambiguous_exam_profile_signals" in warning_codes


def test_negative_marking_is_only_confirmed_with_explicit_scoring_signals():
    service = ExamProfileService()
    explicit = service.suggest_exam_profile_from_edital(
        _edital(
            "edital:negative",
            "Julgue os itens seguintes em CERTO ou ERRADO. Cada erro implica 1,00 ponto negativo. Em branco vale zero ponto.",
        )
    )
    implicit = service.suggest_exam_profile_from_edital(
        _edital(
            "edital:no-negative",
            "Banca CEBRASPE. Julgue os itens seguintes em CERTO ou ERRADO.",
        )
    )

    assert explicit is not None
    assert explicit.scoring_confidence >= 0.8
    assert explicit.scoring_evidence
    assert explicit.metadata["negative_marking_confirmed"] is True

    assert implicit is not None
    assert implicit.scoring_confidence <= 0.5
    assert implicit.metadata["negative_marking_confirmed"] is False


def test_fgv_can_hint_discursive_without_overriding_objective_profile():
    service = ExamProfileService()
    result = service.suggest_exam_profile_from_edital(
        _edital(
            "edital:fgv-discursive",
            "FGV. Prova objetiva com alternativas A, B, C, D e E e etapa discursiva com folha de textos definitivos.",
        )
    )

    assert result is not None
    assert result.profile_id == "exam-profile:fgv"
    assert result.format_type in {"mixed", "discursive"}
    assert result.format_evidence
    warning_codes = {item.code for item in result.warnings}
    assert "discursive_module_detected" in warning_codes
