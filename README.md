# StudyFlow AI

Aplicacao web de estudos baseada em PDFs para concursos publicos.

## MVP entregue

- Upload de PDF
- Parsing com `PyMuPDF` ou `pdfplumber`
- Estruturacao por topicos
- Geracao de resumo estruturado
- Geracao de questoes com explicacao
- Revisao diaria curta
- Revisao por bloco a cada 3 PDFs
- Persistencia simples de progresso, erros e pontos fracos em JSON
- Interface web minimalista em HTML/CSS/JS

## Stack

- Backend: FastAPI
- Testes: pytest
- PDF: PyMuPDF com fallback para pdfplumber
- Frontend: HTML/CSS/JS

## Executar

```bash
PYTHONPATH=./.python_packages /Users/vjr/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m uvicorn app.main:app --reload
```

## Testar

```bash
PYTHONPATH=./.python_packages /Users/vjr/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest
```

## Estrutura

```text
app/
  api/
  domain/
  repositories/
  services/
  static/
  templates/
docs/
tests/
data/
```

## Observacoes

- O MVP foi mantido simples de proposito.
- Integracoes externas, login, filtros avancados e adaptacao sofisticada por banca ficaram planejados na arquitetura.
