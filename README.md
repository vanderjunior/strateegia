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
- para `PDF`, registra `pending_extraction`

Limitacoes importantes:

- nao existe OCR ainda
- nao existe pipeline robusto de extracao de PDF ainda
- nao existe extracao edital-aware ainda

O endpoint legado `POST /api/documents/upload` foi preservado para o prototipo atual e para os testes existentes do pipeline PDF processado.

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
- esta etapa ainda nao substitui um sistema de auth de producao

## Limitações atuais

- sem OCR
- sem extracao de edital
- sem alinhamento bibliografico
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

- pipeline robusto de PDF com OCR, chunking e secoes
- runtime edital-aware com topicos, pesos e exclusoes
- alinhamento bibliografico e analise de cobertura
- grafo curricular e orquestrador de ciclos de estudo
- perfis de banca e simulados
- dashboard de progresso e retencao
- scheduler avancado de revisao
