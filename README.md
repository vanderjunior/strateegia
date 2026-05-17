# StudyFlow AI

Aplicacao web de estudos com runtime pedagogico deterministico, sessoes adaptativas, observabilidade cientifica e fundacao inicial para uso multiusuario.

## O que a aplicacao faz hoje

- gera sessoes de estudo adaptativas a partir de materiais ja processados
- acompanha microtopicos, erros, cumulatividade e revisao
- mantem observabilidade longitudinal e agregada de retencao
- expõe console interno de inspecao e ferramental cientifico offline
- permite upload inicial de materiais por usuario
- prepara a base para futura ingestao robusta de PDF e fluxo edital-aware

## Capacidades atuais

- sessoes adaptativas com revisao cumulativa
- rastreamento de microtopicos e memoria pedagogica
- benchmark, validacao cientifica e inspection console
- export/import de snapshots e comparacao offline
- fundacao de usuarios, login local e progresso isolado por usuario
- fundacao de upload seguro para `PDF`, `TXT` e `Markdown`

## Como instalar

1. Crie e ative um ambiente Python 3.12+.
2. Instale as dependencias:

```bash
python -m pip install -r requirements.txt
```

## Como executar

```bash
PYTHONPATH=./.python_packages /Users/vjr/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m uvicorn app.main:app --reload
```

Aplicacao principal:
- [http://127.0.0.1:8000/](http://127.0.0.1:8000/)

Console interno de inspection:
- [http://127.0.0.1:8000/inspection](http://127.0.0.1:8000/inspection)

## Como rodar os testes

```bash
PYTHONPATH=./.python_packages /Users/vjr/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3 -m pytest -q
```

## Upload de material

O endpoint inicial de fundacao para materiais e:

- `POST /api/materials/upload`

Regras atuais:

- exige usuario autenticado
- aceita apenas `PDF`, `TXT` e `Markdown`
- normaliza nome de arquivo
- bloqueia extensoes nao suportadas
- aplica limite de tamanho
- salva o arquivo em pasta por usuario
- para `TXT` e `MD`, faz extracao simples de texto
- para `PDF` textual simples, tenta extracao basica de texto
- para `PDF` escaneado ou sem texto utilizavel, registra `pending_extraction` com indicacao de OCR futuro

Limitacoes importantes:

- nao existe OCR ainda
- nao existe pipeline robusto de extracao de PDF ainda
- nao existe extracao edital-aware ainda

O endpoint legado `POST /api/documents/upload` foi preservado para o prototipo atual e para os testes existentes do pipeline PDF processado.

## Fundacao do pipeline de documentos

Materiais enviados agora podem entrar em um pipeline estruturado, user-scoped e observavel.

Capacidades atuais desta etapa:

- `TXT`: extracao simples de texto
- `MD`: extracao simples de texto com deteccao basica de headings `#`, `##` e `###`
- `PDF` textual: extracao basica de texto com adapter leve e reaproveitamento do chunking/sectioning atual
- chunking deterministico por texto/paragrafos para `TXT` e `MD`
- sectioning simples para `TXT`, `MD` e `PDF` textual com fallback `Document`
- `PDF` escaneado/sem texto: registro em estado `pending_extraction` com `ocr_required`
- persistencia JSON de estado, extracao, chunks, secoes e eventos de pipeline

Estagios atuais do pipeline:

- `uploaded`
- `type_detected`
- `extraction_pending`
- `extraction_started`
- `extracted`
- `chunked`
- `sectioned`
- `metadata_ready`
- `failed`
- `unsupported`

Endpoints atuais do pipeline:

- `POST /api/materials/{document_id}/process`
- `GET /api/materials/{document_id}/pipeline`
- `GET /api/materials/{document_id}/chunks`
- `GET /api/materials/{document_id}/sections`

Regras importantes:

- esses endpoints exigem autenticacao
- cada usuario so pode processar e ler os proprios documentos
- o pipeline atual nao executa OCR
- o pipeline atual nao faz parsing de edital
- o pipeline atual nao cria embeddings, vetores ou busca semantica
- `storage_path` em respostas continua relativo e seguro

Comportamento atual para PDFs:

- PDF textual simples: extrai texto, cria chunks deterministas, cria secao fallback e conclui em `metadata_ready`
- PDF sem texto utilizavel ou escaneado: permanece em `extraction_pending` com warnings como `pdf_text_empty` e `ocr_required`
- PDF invalido ou malformado: falha de forma segura e observavel, sem vazar caminhos absolutos

## Usuarios e persistencia

A fundacao atual inclui:

- cadastro local simples
- login local com cookie HTTP-only
- progresso isolado por usuario autenticado
- compatibilidade com o modo legado sem autenticacao
- compatibilidade com persistencia JSON existente

Quando nao ha usuario autenticado, o app continua operando no modo legado single-user para preservar compatibilidade do prototipo e do runtime atual.

## Inspection e seguranca

Rotas internas que expõem dados sensiveis de runtime e debug. Elas devem ser tratadas como tooling `internal`/debug:

- `/inspection`
- `/api/inspection/runtime`
- `/api/inspection/runtime/export`

Essas rotas sao internas e read-only, mas **devem ser protegidas antes de qualquer deploy em producao**. Hoje elas continuam acessiveis em dev/test para preservar o ferramental cientifico existente.

Configuracao de server mode para inspection:

- `APP_ENV`
  - `development`
  - `test`
  - `production`
- `ENABLE_INSPECTION`
  - aceita `true/false`, `1/0`, `yes/no`, `on/off`
- `REQUIRE_AUTH_FOR_INSPECTION`
  - aceita `true/false`, `1/0`, `yes/no`, `on/off`
- `INSPECTION_ALLOWED_IN_PRODUCTION`
  - aceita `true/false`, `1/0`, `yes/no`, `on/off`

Defaults atuais:

- em `development` e `test`, inspection fica habilitada por padrao
- em `development` e `test`, auth para inspection fica desabilitada por padrao
- em `production`, inspection fica bloqueada por padrao
- em `production`, inspection so pode ser exposta com opt-in explicito
- em `production`, se inspection for habilitada, auth e exigida por padrao

Exemplo de configuracao para producao com inspection explicitamente habilitada:

```bash
export APP_ENV=production
export ENABLE_INSPECTION=true
export INSPECTION_ALLOWED_IN_PRODUCTION=true
export REQUIRE_AUTH_FOR_INSPECTION=true
```

Outras notas de seguranca:

- senhas locais nao sao armazenadas em texto puro
- uploads nao sao executados
- nomes de arquivo sao saneados
- uploads sao isolados por usuario
- o pipeline de documentos nao segue caminhos fora do storage root previsto
- erros de processamento sao persistidos de forma segura e sem expor caminhos absolutos
- esta etapa ainda nao substitui um sistema de auth de producao

## Limitações atuais

- sem OCR
- sem extracao robusta de PDF
- sem extracao de edital
- sem alinhamento bibliografico
- sem vetores, embeddings ou RAG
- sem simulados
- sem dashboard de produto
- sem scheduler avancado de revisao
- sem banco SQL
- sem hardening completo de producao para auth e rotas internas

## Estrutura

```text
app/
  api/
  domain/
  repositories/
  services/
  static/
tests/
data/
docs/
```

## Roadmap futuro

Itens planejados, mas nao implementados nesta etapa:

- pipeline robusto de PDF com OCR, chunking e secoes mais fortes
- OCR futuro para livros e materiais escaneados, inclusive casos de praticagem
- runtime edital-aware com topicos, pesos e exclusoes
- alinhamento bibliografico e analise de cobertura
- grafo curricular e orquestrador de ciclos de estudo
- perfis de banca e simulados
- dashboard de progresso e retencao
- scheduler avancado de revisao
