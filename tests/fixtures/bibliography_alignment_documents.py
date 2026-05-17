from __future__ import annotations


def exact_bibliography_match_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Bibliografia

SILVA, Joao. Navegacao Costeira. 2. ed. Rio de Janeiro: Editora Naval, 2020.
""",
        "materials": [
            {
                "alias": "nav_exact",
                "filename": "silva_navegacao_costeira_2020.md",
                "content_type": "text/markdown",
                "text": """# Navegacao Costeira

Joao Silva apresenta fundamentos de navegacao costeira e planejamento de derrota.
""",
                "process": True,
            }
        ],
    }


def partial_author_title_match_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Bibliografia

SILVA, Joao. Navegacao Costeira. 2. ed. Rio de Janeiro: Editora Naval, 2020.
""",
        "materials": [
            {
                "alias": "nav_partial",
                "filename": "manual_navegacao_costeira.md",
                "content_type": "text/markdown",
                "text": """# Manual de Navegacao

Resumo de navegacao costeira com derrotas, perigos e referencias costeiras.
""",
                "process": True,
            }
        ],
    }


def generic_year_overlap_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Bibliografia

ALMEIDA, Carla. Manobras Costeiras Avancadas. Santos: Editora Porto, 2020.
""",
        "materials": [
            {
                "alias": "generic_2020",
                "filename": "relatorio_geral_2020.md",
                "content_type": "text/markdown",
                "text": """# Relatorio Geral

Documento administrativo geral do ano de 2020 sem conteudo de manobra costeira.
""",
                "process": True,
            }
        ],
    }


def ambiguous_duplicate_material_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Bibliografia

BRASIL. RIPEAM Comentado. Brasilia, 2021.
""",
        "materials": [
            {
                "alias": "ripeam_a",
                "filename": "ripeam_comentado_2021.md",
                "content_type": "text/markdown",
                "text": """# RIPEAM Comentado

Compendio de regras de governo, luzes, marcas e rumos.
""",
                "process": True,
            },
            {
                "alias": "ripeam_b",
                "filename": "ripeam_comentado_resumo_2021.md",
                "content_type": "text/markdown",
                "text": """# RIPEAM Comentado

Resumo operacional de RIPEAM com regras de governo e navegacao.
""",
                "process": True,
            },
        ],
    }


def unmatched_bibliography_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Bibliografia

PEREIRA, Ana. Cartas Nauticas Modernas. Rio Grande: Mar Aberto, 2022.
""",
        "materials": [
            {
                "alias": "meteorologia",
                "filename": "meteorologia_basica.md",
                "content_type": "text/markdown",
                "text": """# Meteorologia Basica

Ventos, pressao atmosferica e previsao de tempo para navegacao.
""",
                "process": True,
            }
        ],
    }


def no_materials_alignment_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Conteudo Programatico

1. Meteorologia

# Bibliografia

SILVA, Joao. Navegacao Costeira. 2020.
""",
        "materials": [],
    }


def topic_covered_by_chunk_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Conteudo Programatico

1. Meteorologia: ventos; pressao atmosferica; frentes; cartas sinoticas
""",
        "materials": [
            {
                "alias": "meteo_chunk",
                "filename": "meteorologia_costeira.md",
                "content_type": "text/markdown",
                "text": """# Estudos

Ventos, pressao atmosferica, frentes frias e cartas sinoticas apoiam a navegacao costeira.
""",
                "process": True,
            }
        ],
    }


def topic_covered_by_section_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Conteudo Programatico

1. RIPEAM
""",
        "materials": [
            {
                "alias": "ripeam_section",
                "filename": "manual_ripeam.md",
                "content_type": "text/markdown",
                "text": """# RIPEAM - Regras de Governo e Navegacao

Resumo introdutorio.
""",
                "process": True,
            }
        ],
    }


def weak_generic_overlap_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Conteudo Programatico

1. Legislacao Maritima Especial
""",
        "materials": [
            {
                "alias": "generic_rules",
                "filename": "normas_gerais.md",
                "content_type": "text/markdown",
                "text": """# Conteudo Geral

Normas gerais, conteudo administrativo e procedimentos internos sem foco tecnico especifico.
""",
                "process": True,
            }
        ],
    }


def ocr_required_material_gap_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Conteudo Programatico

1. Autoridade Maritima Aplicada
""",
        "materials": [
            {
                "alias": "ocr_pdf",
                "filename": "autoridade_maritima_aplicada.pdf",
                "content_type": "application/pdf",
                "pdf_pages": [""],
                "process": True,
            }
        ],
    }


def multiple_documents_same_topic_redundancy_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Conteudo Programatico

1. Meteorologia: ventos; frentes; cartas sinoticas
""",
        "materials": [
            {
                "alias": "meteo_a",
                "filename": "meteorologia_vento.md",
                "content_type": "text/markdown",
                "text": """# Meteorologia

Ventos, frentes e cartas sinoticas no apoio a navegacao.
""",
                "process": True,
            },
            {
                "alias": "meteo_b",
                "filename": "meteorologia_cartas.md",
                "content_type": "text/markdown",
                "text": """# Meteorologia Aplicada

Cartas sinoticas, ventos e frentes para planejamento de derrota.
""",
                "process": True,
            },
        ],
    }


def unprocessed_material_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Conteudo Programatico

1. Navegacao Costeira
""",
        "materials": [
            {
                "alias": "unprocessed",
                "filename": "navegacao_costeira_manual.md",
                "content_type": "text/markdown",
                "text": """# Navegacao Costeira

Material ainda nao processado.
""",
                "process": False,
            }
        ],
    }


def maritime_praticagem_alignment_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Conteudo Programatico

1. Arte Naval
2. RIPEAM
3. Manobra
4. Meteorologia: ventos; pressao; frentes
5. Legislacao Maritima: autoridade maritima; infracoes
""",
        "materials": [
            {
                "alias": "ripeam_doc",
                "filename": "ripeam_comentado.md",
                "content_type": "text/markdown",
                "text": """# RIPEAM

Regras de governo, rumo e manobras preventivas.
""",
                "process": True,
            },
            {
                "alias": "meteo_doc",
                "filename": "meteorologia_pratica.md",
                "content_type": "text/markdown",
                "text": """# Meteorologia

Ventos, pressao atmosferica e frentes para seguranca da navegacao.
""",
                "process": True,
            },
        ],
    }


def mixed_alignment_fixture() -> dict[str, object]:
    return {
        "edital_text": """# Conteudo Programatico

1. RIPEAM
2. Meteorologia: ventos; cartas sinoticas
3. Arte Naval

# Bibliografia

BRASIL. RIPEAM Comentado. Brasilia, 2021.
SILVA, Joao. Navegacao Costeira. Rio de Janeiro, 2020.
PEREIRA, Ana. Manobra em Aguas Restritas. Santos, 2022.
""",
        "materials": [
            {
                "alias": "ripeam_a",
                "filename": "ripeam_comentado_2021.md",
                "content_type": "text/markdown",
                "text": """# RIPEAM

RIPEAM comentado com regras de governo e navegacao.
""",
                "process": True,
            },
            {
                "alias": "ripeam_b",
                "filename": "ripeam_comentado_resumo_2021.md",
                "content_type": "text/markdown",
                "text": """# RIPEAM

Resumo de RIPEAM e regras de navegacao para praticagem.
""",
                "process": True,
            },
            {
                "alias": "meteo_doc",
                "filename": "meteorologia_cartas_sinoticas.md",
                "content_type": "text/markdown",
                "text": """# Meteorologia

Ventos e cartas sinoticas aplicadas a navegacao.
""",
                "process": True,
            },
            {
                "alias": "generic_nav",
                "filename": "navegacao_costeira_2020.md",
                "content_type": "text/markdown",
                "text": """# Navegacao Costeira

Introducao geral a navegacao costeira e derrota.
""",
                "process": True,
            },
        ],
    }


ALL_BIBLIOGRAPHY_ALIGNMENT_FIXTURES = [
    exact_bibliography_match_fixture,
    partial_author_title_match_fixture,
    generic_year_overlap_fixture,
    ambiguous_duplicate_material_fixture,
    unmatched_bibliography_fixture,
    no_materials_alignment_fixture,
    topic_covered_by_chunk_fixture,
    topic_covered_by_section_fixture,
    weak_generic_overlap_fixture,
    ocr_required_material_gap_fixture,
    multiple_documents_same_topic_redundancy_fixture,
    unprocessed_material_fixture,
    maritime_praticagem_alignment_fixture,
    mixed_alignment_fixture,
]
