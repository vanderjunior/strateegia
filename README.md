# StudyFlow AI

Aplicacao web de estudos com runtime pedagogico deterministico, sessoes adaptativas, observabilidade cientifica e fundacao inicial para uso multiusuario.

## O que a aplicacao faz hoje

- gera sessoes de estudo adaptativas a partir de materiais ja processados
- acompanha microtopicos, erros, cumulatividade e revisao
- mantem observabilidade longitudinal e agregada de retencao
- expõe console interno de inspecao e ferramental cientifico offline
- permite upload e processamento inicial de materiais por usuario
- mantem fundacoes deterministicas para fluxo edital-aware: ingestao candidata de edital, alinhamento bibliografico, curriculum graph, study cycle, exam profiles e simulado blueprint
- oferece um dashboard minimo de estudo, read-only e user-scoped, para o usuario acompanhar o estado da pipeline

## Capacidades atuais

- sessoes adaptativas com revisao cumulativa
- rastreamento de microtopicos e memoria pedagogica
- benchmark, validacao cientifica e inspection console
- export/import de snapshots e comparacao offline
- fundacao de usuarios, login local e progresso isolado por usuario
- fundacao de upload seguro para `PDF`, `TXT` e `Markdown`
- fundacao de pipeline documental user-scoped com extracao `TXT`/`MD`, PDF textual basico e fallback `ocr_required`
- fundacao de ingestao de edital candidata, deterministica e review-friendly
- fundacao de alinhamento bibliografico e coverage candidata
- fundacao de curriculum graph candidato
- fundacao de study cycle candidato
- fundacao de exam profiles declarativos e candidate-based
- fundacao de simulado blueprint candidate-based e read-only
- dashboard minimo de estudo, read-only e user-scoped, com materiais, pipeline documental, edital, coverage/alignment, curriculum graph, study cycle, exam profile, simulado blueprint e pending actions

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

Dashboard de estudo:
- [http://127.0.0.1:8000/dashboard](http://127.0.0.1:8000/dashboard)

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
- a extracao de PDF ainda e basica e textual, sem OCR e sem layout parsing robusto
- PDFs escaneados ou sem texto utilizavel continuam aguardando OCR futuro
- a ingestao edital-aware existe como fundacao candidata e deterministica, mas ainda nao e uma extracao final/validada
- upload, processamento documental e ingestao de edital continuam sendo etapas separadas

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

## Fundacao de ingestao de edital

Documentos ja processados pelo pipeline agora podem ser ingeridos como edital de forma deterministica e auditavel.

Capacidades atuais desta etapa:

- deteccao de secoes candidatas como conteudo programatico, bibliografia, exclusoes e estrutura da prova
- extracao heuristica e local de topicos candidatos
- extracao heuristica de subtopicos candidatos
- extracao de candidatos de bibliografia
- extracao de candidatos de exclusoes
- extracao de weight hints como questoes, pontos e porcentagens
- persistencia user-scoped de estado, resultado e eventos de ingestao

Endpoints atuais da ingestao de edital:

- `POST /api/materials/{document_id}/edital/ingest`
- `GET /api/materials/{document_id}/edital`
- `GET /api/edital/{edital_id}`

Regras importantes:

- a ingestao usa apenas heuristicas deterministicas locais
- o resultado e sempre tratado como `candidate` e `ready_for_review`
- esta etapa nao gera grafo curricular final
- esta etapa nao faz alinhamento bibliografico
- esta etapa nao cria ciclo de estudos
- esta etapa nao altera ranking, progresso ou sessao
- documentos com pouco texto ou PDFs com `ocr_required` retornam estado seguro de texto insuficiente

## Fundacao de alinhamento bibliografico e cobertura

Extracoes candidatas de edital agora podem ser alinhadas contra os materiais processados do proprio usuario.

Capacidades atuais desta etapa:

- matching candidato entre bibliografia do edital e materiais enviados
- estimativa candidata de cobertura de topicos e subtopicos
- deteccao de gaps como bibliografia ausente, topico sem cobertura e material com `ocr_required`
- deteccao conservadora de redundancias como multiplos materiais cobrindo o mesmo topico
- evidencias, matched terms e reasoning para revisao manual

Endpoints atuais do alinhamento:

- `POST /api/edital/{edital_id}/align-bibliography`
- `GET /api/edital/{edital_id}/alignment`
- `GET /api/alignment/{alignment_id}`

Regras importantes:

- o alinhamento e heuristic-based e deterministic
- o resultado continua candidate-based e review-friendly
- esta etapa nao gera grafo curricular final
- esta etapa nao cria ciclo de estudos
- esta etapa nao altera ranking, sessao ou progresso
- materiais sem texto ou com `ocr_required` viram warning/gap, nao falso positivo forte

## Fundacao do curriculum graph

Artefatos de edital e alignment agora podem gerar um curriculum graph candidato, ainda separado do runtime ativo.

Capacidades atuais desta etapa:

- criacao de subject, topic e subtopic nodes a partir do edital ingerido
- preservacao de coverage links vindos do alignment
- anexacao de gaps e redundancias como referencias auditaveis
- evidence, reasoning e review states para revisao manual
- persistencia user-scoped de estado e resultado do graph

Endpoints atuais do curriculum graph:

- `POST /api/edital/{edital_id}/curriculum-graph/build`
- `GET /api/edital/{edital_id}/curriculum-graph`
- `GET /api/curriculum-graph/{graph_id}`

Regras importantes:

- o graph continua candidate-based e `ready_for_review`
- ele nao substitui o curriculo ativo do runtime
- ele nao cria ciclo de estudos, scheduler de revisao ou simulados
- ele nao aplica exam profiles
- gaps como `ocr_required` e `missing_document_text` continuam preservados

## Fundacao do study cycle

O curriculum graph candidato agora pode gerar uma proposta inicial de ciclo de estudos, ainda separada do runtime ativo.

Capacidades atuais desta etapa:

- subject rotation candidata e deterministica
- topic slots candidatos baseados em coverage/review state
- review slots candidatos para topicos fracos, parciais, ambiguos ou bloqueados
- gap slots para material ausente, OCR futuro e bloqueios de texto
- fatigue/balance hints e rationale para revisao manual
- persistencia user-scoped de estado e resultado do plano

Endpoints atuais do study cycle:

- `POST /api/curriculum-graph/{graph_id}/study-cycle/build`
- `GET /api/curriculum-graph/{graph_id}/study-cycle`
- `GET /api/study-cycle/{cycle_id}`

Regras importantes:

- o plano continua candidate-based e `ready_for_review`
- ele nao ativa scheduling no runtime nem substitui automaticamente o plano pedagogico vivo
- ele nao cria calendario, scheduler de revisao ou simulados
- ele nao substitui `CurriculumScheduler` nem `LearningDecisionEngine`
- topicos ambiguos ou bloqueados continuam sinalizados para revisao manual

## Fundacao dos exam profiles

O app agora inclui perfis declarativos de banca para uso futuro em revisao manual, estabilizacao e simulados, sem qualquer ativacao no runtime atual.

Perfis iniciais suportados:

- `CEBRASPE`
- `FGV`
- `Marinha / PSCPP`

Capacidades atuais desta etapa:

- perfis declarativos e inspecionaveis que separam banca, formato, familia especial e generation hints
- timing hints, scoring hints e difficulty hints conservadores
- cognitive demand e board behavior hints
- sugestao heuristica opcional a partir do edital ingerido
- respostas JSON-safe e side-effect free

Endpoints atuais de exam profiles:

- `GET /api/exam-profiles`
- `GET /api/exam-profiles/{profile_id}`
- `POST /api/edital/{edital_id}/exam-profile/suggest`
- `GET /api/edital/{edital_id}/exam-profile/suggestion`

Regras importantes:

- os perfis sao declarativos e candidate-based
- nome da banca nao decide sozinho o formato da prova
- formato explicito do edital tem prioridade sobre estilo historico da banca
- PSCPP/Praticagem e tratado como familia especial e pode prevalecer sobre banca externa mencionada
- negative marking so deve ser tratado como confirmado quando o edital trouxer sinal explicito
- eles nao geram simulados nem questoes
- eles nao alteram study cycle, ranking, sessao ou scheduler do runtime
- contagem de questoes, tempo e scoring continuam dependentes do edital real
- a sugestao por edital pode exigir revisao manual em casos ambiguos

## Fundacao dos simulados

O app agora consegue gerar um simulado candidato em formato de blueprint, usando study cycle, curriculum graph e exam profile como entradas declarativas, sem gerar questoes finais e sem ativar qualquer comportamento de runtime.

Capacidades atuais desta etapa:

- resolucao conservadora de formato, timing e scoring do simulado
- sections candidatas como `true_false_block`, `multiple_choice_block`, `technical_maritime_block` e `discursive_hint`
- question slots candidatos com topic/subtopic target, readiness state e generation hints
- distribution plan, coverage plan, readiness profile e generation constraints
- warnings e rationale auditaveis para revisao manual
- persistencia user-scoped de estado e resultado do blueprint

Endpoints atuais de simulado blueprint:

- `POST /api/study-cycle/{cycle_id}/simulado-blueprint/build`
- `GET /api/study-cycle/{cycle_id}/simulado-blueprint`
- `GET /api/simulado-blueprint/{blueprint_id}`

Regras importantes:

- o blueprint continua candidate-based e `ready_for_review`
- esta etapa nao gera pergunta final, alternativa, resposta, distrator, explicacao ou gabarito
- ela nao ativa agenda de prova nem altera study cycle, ranking, sessao ou scheduler
- negative marking so entra como confirmado quando o edital/profile suggestion trouxer evidencia explicita
- topicos com `ocr_required`, `missing_document_text` ou ambiguidade continuam bloqueados ou marcados para revisao
- PSCPP/Praticagem preserva technical maritime hints e source-topic mapping como constraints, nao como geracao ativa

## Dashboard minimo do usuario

O app agora inclui um dashboard de estudo read-only e product-facing, separado do console interno de inspection.

Rotas atuais do dashboard:

- `GET /dashboard`
- `GET /api/dashboard/overview`

O que o dashboard mostra hoje:

- identidade do usuario autenticado
- resumo futuro-compativel de projeto ativo, quando disponivel
- materiais enviados e pipeline de documentos
- status de edital, alignment, curriculum graph, study cycle e exam profile
- readiness do simulado blueprint
- pending actions e `primary_next_step`
- resumo descritivo de progresso e continuacao, quando houver dados seguros
- JSON compacto do mesmo overview seguro

Regras importantes:

- `/dashboard` e a superficie product-facing autenticada e user-scoped
- `/api/dashboard/overview` e a API read-only de overview do dashboard
- o dashboard e read-only e nao aciona processamento, ingestao, alignment ou builders
- ele usa pending actions e `primary_next_step` apenas como orientacao visual, sem disparar qualquer acao
- ele nao chama, encapsula ou reaproveita `/api/inspection/runtime`
- ele nao expõe payload bruto de runtime/debug nem dados cientificos internos
- ele nao mostra caminhos absolutos, `password_hash`, texto bruto extraido, chunks ou paginas
- ele nao executa OCR, nao gera questoes e nao executa simulados
- ele nao altera study cycle, ranking, sessao, scheduler ou runtime pedagogico
- o resumo do dashboard e deterministico e template-based, sem chamada a LLM
- o console `/inspection` continua separado para tooling interno

## Usuarios e persistencia

A fundacao atual inclui:

- cadastro local simples
- login local com cookie HTTP-only
- progresso isolado por usuario autenticado
- compatibilidade com o modo legado sem autenticacao
- compatibilidade com persistencia JSON existente

Quando nao ha usuario autenticado, o app continua operando no modo legado single-user para preservar compatibilidade do prototipo e do runtime atual.

Observacao:

- o modo legado single-user existe para preservar compatibilidade do prototipo e do runtime atual
- o dashboard de estudo e as APIs user-scoped novas exigem autenticacao e retornam apenas dados do usuario autenticado

## Inspection e seguranca

Rotas internas que expõem dados sensiveis de runtime e debug. Elas devem ser tratadas como tooling `internal`/debug:

- `/inspection`
- `/api/inspection/runtime`
- `/api/inspection/runtime/export`

Separacao de superficies:

- `/inspection` e tooling interno, cientifico e de debug
- `/dashboard` e a superficie de produto para o usuario autenticado
- `/dashboard` nao reutiliza payload bruto de inspection
- `/api/inspection/runtime` permanece interno e deve ser protegido em producao

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
- sem extracao robusta de PDF com layout parsing forte
- sem extracao final/validada de edital
- sem alinhamento bibliografico final/validado do edital
- sem grafo curricular final/aprovado a partir do edital; o graph atual continua candidate-based e review-friendly
- sem ativacao automatica do ciclo de estudos derivado do edital no runtime pedagogico
- sem vetores, embeddings ou RAG
- sem geracao final de questoes
- sem alternativas, distratores, respostas, explicacoes ou gabarito
- sem execucao/correcao de simulados
- sem ativacao automatica de graph, cycle ou simulado blueprint no runtime vivo
- sem dashboard mutavel ou com acoes de build
- sem scheduler avancado de revisao
- sem banco SQL
- sem hardening completo de producao para auth e rotas internas

## Direcao de produto

A aplicacao caminha para um fluxo de estudos edital-aware em que o usuario:

1. cria ou seleciona um objetivo de estudo, como PSCPP, Perito PF ou Receita Federal
2. envia materiais, apostilas, livros e editais
3. processa documentos e identifica lacunas de OCR/material
4. ingere edital e alinha bibliografia contra os materiais
5. gera curriculum graph e study cycle candidatos para revisao
6. estuda por ciclos, com resumos, questoes e revisoes
7. gera simulados conforme perfil de banca/prova
8. revisa pontos fracos e, futuramente, gera um resumao pre-prova

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

- pipeline robusto de PDF com OCR, layout parsing, chunking e secoes mais fortes
- OCR futuro para livros e materiais escaneados, inclusive casos de praticagem
- estabilizacao e validacao mais forte da extracao de edital
- refinamento e validacao do alinhamento bibliografico e da analise de coverage
- evolucao do curriculum graph candidato para fluxo de revisao/aprovacao
- evolucao do study cycle candidato sem ativacao automatica no runtime
- runtime edital-aware com topicos, pesos, exclusoes e fonte de coverage revisada
- geracao futura de questoes a partir de materiais, edital, perfil de banca e blueprint
- geracao futura de alternativas, distratores, respostas, explicacoes e gabarito
- execucao e correcao futura de simulados
- refinamento do dashboard de progresso, continuacao e retencao
- resumao pre-prova baseado no material ja estudado
- scheduler avancado de revisao
