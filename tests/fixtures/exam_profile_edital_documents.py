from __future__ import annotations

from app.domain.models import EditalExtractionResult


def cebraspe_true_false_with_negative_marking_edital_text() -> str:
    return (
        "Banca CEBRASPE. Julgue os itens seguintes em CERTO ou ERRADO. "
        "Marque o campo C ou o campo E. Cada discordancia com o gabarito implica 1,00 ponto negativo. "
        "Item em branco vale 0 ponto."
    )


def cebraspe_without_explicit_ce_edital_text() -> str:
    return "Banca CEBRASPE. Prova objetiva. Conteudo programatico, bibliografia e criterios de avaliacao."


def cebraspe_with_multiple_choice_5_edital_text() -> str:
    return "Banca CEBRASPE. Prova objetiva com cinco alternativas: A, B, C, D e E. Somente uma correta."


def true_false_without_board_edital_text() -> str:
    return "Julgue os itens seguintes em Certo ou Errado, assinalando campo C ou campo E."


def true_false_without_negative_marking_edital_text() -> str:
    return "Julgue os itens seguintes em CERTO ou ERRADO, com marcacao no campo C ou campo E."


def fgv_multiple_choice_5_edital_text() -> str:
    return "FGV. Prova objetiva com cinco alternativas A, B, C, D e E. Apenas uma correta."


def fgv_discursive_mixed_edital_text() -> str:
    return "FGV. Prova objetiva com alternativas A, B, C, D e E e questoes discursivas com folha de textos definitivos."


def marinha_pscpp_dpc_normam_edital_text() -> str:
    return (
        "PSCPP para Praticante de Pratico. Servico de Praticagem. DPC - Diretoria de Portos e Costas. "
        "NORMAM-311. Autoridade Maritima. Conteudo Programatico. Bibliografia Sugerida."
    )


def pscpp_with_external_fgv_board_edital_text() -> str:
    return (
        "FGV organizadora. Processo seletivo PSCPP para Praticante de Pratico. "
        "DPC, NORMAM-311 e Praticagem. Prova objetiva com alternativas A, B, C, D e E."
    )


def marinha_generic_military_without_pscpp_edital_text() -> str:
    return "Marinha do Brasil. Processo seletivo militar com prova objetiva e conteudo geral, sem referencia a PSCPP ou Praticagem."


def quadrix_true_false_edital_text() -> str:
    return "Quadrix. Julgue os itens seguintes em Certo ou Errado."


def quadrix_multiple_choice_5_edital_text() -> str:
    return "Quadrix. Prova objetiva com cinco alternativas: A, B, C, D e E."


def ibfc_multiple_choice_4_edital_text() -> str:
    return "IBFC. Prova objetiva com quatro alternativas: A, B, C e D."


def aocp_multiple_choice_5_edital_text() -> str:
    return "Instituto AOCP. Prova objetiva com cinco alternativas A, B, C, D e E."


def unknown_board_multiple_choice_5_edital_text() -> str:
    return "Prova objetiva com cinco alternativas: A, B, C, D e E. Apenas uma correta."


def unknown_generic_edital_text() -> str:
    return "Processo seletivo com prova objetiva, conteudo programatico e avaliacao."


def conflicting_ce_and_ae_edital_text() -> str:
    return "Julgue os itens em Certo ou Errado. A prova tambem menciona alternativas A, B, C, D e E para marcacao."


def negative_marking_without_ce_edital_text() -> str:
    return "Cada erro implica ponto negativo e a discordancia com o gabarito reduz a nota, mas o formato nao foi explicitado."


def five_options_with_negative_marking_edital_text() -> str:
    return "Prova objetiva com alternativas A, B, C, D e E. Cada erro implica ponto negativo."


def pscpp_textual_bibliography_driven_edital_text() -> str:
    return (
        "PSCPP e Praticagem. Bibliografia Sugerida: Manobrabilidade do Navio, Ship Manoeuvrability, "
        "Naval Shiphandling, Principles of Naval Architecture. Conteudo tecnico-operacional maritimo."
    )


def build_edital_result_from_text(edital_id: str, text: str, *, user_id: str | None = None) -> EditalExtractionResult:
    return EditalExtractionResult(
        edital_id=edital_id,
        document_id=f"doc:{edital_id}",
        user_id=user_id,
        source_text_length=len(text),
        metadata={"source_text_preview": text},
    )


ALL_EXAM_PROFILE_FIXTURE_BUILDERS = [
    cebraspe_true_false_with_negative_marking_edital_text,
    cebraspe_without_explicit_ce_edital_text,
    cebraspe_with_multiple_choice_5_edital_text,
    true_false_without_board_edital_text,
    true_false_without_negative_marking_edital_text,
    fgv_multiple_choice_5_edital_text,
    fgv_discursive_mixed_edital_text,
    marinha_pscpp_dpc_normam_edital_text,
    pscpp_with_external_fgv_board_edital_text,
    marinha_generic_military_without_pscpp_edital_text,
    quadrix_true_false_edital_text,
    quadrix_multiple_choice_5_edital_text,
    ibfc_multiple_choice_4_edital_text,
    aocp_multiple_choice_5_edital_text,
    unknown_board_multiple_choice_5_edital_text,
    unknown_generic_edital_text,
    conflicting_ce_and_ae_edital_text,
    negative_marking_without_ce_edital_text,
    five_options_with_negative_marking_edital_text,
    pscpp_textual_bibliography_driven_edital_text,
]
