from __future__ import annotations


def basic_numbered_program_edital_text() -> str:
    return """# CONTEUDO PROGRAMATICO

1. Arte Naval
2. RIPEAM
3. Meteorologia: ventos; pressao atmosferica; frentes frias
4. Legislacao Maritima: autoridade maritima; infracoes; normas administrativas
"""


def colon_subtopics_program_edital_text() -> str:
    return """# Conteudo Programatico

Meteorologia: ventos; pressao atmosferica; frentes frias; cartas sinoticas
Legislacao Maritima: autoridade maritima, infracoes, normas administrativas
"""


def semicolon_inline_program_edital_text() -> str:
    return """# Conteudo Programatico

Conhecimentos Especificos: Arte Naval; RIPEAM; Meteorologia; Legislacao Maritima
"""


def bibliography_block_edital_text() -> str:
    return """# Bibliografia

SILVA, Joao. Navegacao Costeira. 2. ed. Rio de Janeiro: Editora Naval, 2020.
BRASIL. Normas da Autoridade Maritima. Brasilia, 2021.
"""


def exclusions_block_edital_text() -> str:
    return """# Exclusoes

Nao sera cobrado: sistemas militares sigilosos.
Exclui-se o estudo aprofundado de armamento belico.
Nao integra o programa a regulamentacao revogada.
"""


def exam_structure_with_weights_edital_text() -> str:
    return """# Estrutura da Prova

A prova objetiva tera 120 questoes.
Conhecimentos Especificos: 70 questoes.
Conhecimentos Gerais: 50 questoes.
Valor total de 100 pontos.
Peso relativo de 50%.
"""


def mixed_sections_edital_text() -> str:
    return """# Regras Gerais

O candidato deve observar as instrucoes do edital.

# Estrutura da Prova

Prova objetiva: 80 questoes, 100 pontos, 60%.

# Conteudo Programatico

1. Arte Naval
2. Meteorologia: ventos; frentes
3. Comunicacoes

# Bibliografia

SILVA, Joao. Navegacao Costeira. 2. ed. Rio de Janeiro: Editora Naval, 2020.

# Exclusoes

Nao sera cobrado: material revogado.
"""


def marinha_pscpp_style_edital_text() -> str:
    return """# Conteudo Programatico

1. Arte Naval
2. RIPEAM
3. Manobra
4. Meteorologia: ventos; pressao; frentes
5. Legislacao Maritima: autoridade maritima; infracoes
6. Navegacao
7. Comunicacoes

# Estrutura da Prova

Prova objetiva: 60 questoes, 100 pontos.
"""


def cebraspe_style_edital_text() -> str:
    return """# Estrutura da Prova

Itens do tipo CERTO ou ERRADO.
A prova objetiva tera 120 questoes.

# Conteudo Programatico

1. Direito Administrativo
2. Legislacao Maritima
3. Navegacao
"""


def fgv_style_edital_text() -> str:
    return """# Estrutura da Prova

Prova objetiva com alternativas A, B, C, D e E.
Valor total de 80 pontos.

# Conteudo Programatico

1. Arte Naval
2. Meteorologia
3. Comunicacoes
"""


def low_text_edital_text() -> str:
    return "OK"


def noisy_mixed_format_edital_text() -> str:
    return """# AVISOS ADMINISTRATIVOS

Comparecer com documento oficial. Horario de abertura dos portoes.

# CONTEUDO PROGRAMATICO

- Arte Naval
- Meteorologia: ventos; cartas sinoticas
- Legislacao Maritima

Texto administrativo avulso sem valor curricular imediato.

# Estrutura da Prova

Prova objetiva: 40 questoes.
"""

