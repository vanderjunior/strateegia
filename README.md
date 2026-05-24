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

## Cadeia atual da pipeline

Hoje a superficie principal do produto segue esta cadeia, ainda com etapas candidatas e review-friendly:

`upload/material`
-> `document pipeline`
-> `OCR optional fallback`
-> `edital ingestion`
-> `bibliography alignment`
-> `curriculum graph`
-> `study cycle`
-> `exam profile`
-> `simulado blueprint`
-> `question generation blueprint`
-> `question draft`
-> `answer/explanation guardrails`
-> `simulado question assembly`
-> `simulado attempt shell`
-> `simulado finalization/approval guardrails`
-> `simulado final approval artifact`
-> `simulado execution shell`
-> `simulado attempt session`
-> `answer submission`
-> `correction shell`
-> `answer key boundary`
-> `correction result`
-> `dashboard`

Regras importantes desta cadeia:

- continua textual-PDF-first
- OCR e opcional, bounded e desabilitado por padrao
- etapas edital-aware continuam candidate-based e nao sao autoridade final de runtime
- dashboard e apenas superficie de overview, nao um executor de acoes

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
- fundacao de question generation blueprint source-grounded, candidate-based e planning-only
- fundacao de question draft generation provisoria, bounded e review-required
- fundacao de answer key / explanation guardrails source-grounded, candidate-only e finalization-blocked
- fundacao de simulado question assembly source-grounded, guardrail-aware, non-executable e non-scoreable
- fundacao de simulado execution readiness / attempt shell assembly-aware, non-executable e sem submissions
- fundacao de finalization / approval guardrails assembly-aware, attempt-shell-aware, non-executable e sem aprovacao real
- fundacao de final approval artifact audit-friendly, user-scoped e ainda nao executavel
- fundacao de simulado execution shell final-approval-aware, non-active, non-executable e sem scoring
- fundacao de simulado attempt session execution-shell-aware, prepared-only e non-submittable
- fundacao de answer submission attempt-session-aware, bounded-input-only, non-correcting e non-scoring
- fundacao de correction readiness / correction shell answer-submission-aware, readiness-only, non-correcting e non-scoring
- fundacao de final answer key exposure boundary / correction input contract correction-shell-aware, internal-only, non-correcting e non-scoring
- fundacao de correction result answer-key-boundary-aware, non-scoreable e sem final simulado result
- fundacao de scoring result correction-result-aware, sem mutacao de progresso/ranking/retention/scheduler e sem exposicao publica de answer key/gabarito
- fundacao de progress mutation guardrails score-result-aware, sem aplicar score ao runtime e sem expor answer key/gabarito publicamente
- dashboard minimo de estudo, read-only e user-scoped, com materiais, pipeline documental, edital, coverage/alignment, curriculum graph, study cycle, exam profile, simulado blueprint e pending actions

## Fundacao de answer submission

Attempt sessions preparados agora podem receber um artifact separado de `answer submission`, sempre user-scoped e deterministico.

Capacidades atuais desta etapa:

- registra respostas fornecidas pelo usuario para um `SimuladoAttemptSession`
- suporta payloads pequenos e bounded para `selected_option`, `true_false_value`, `short_text` e `blank`
- valida apenas estrutura, duplicidade, item desconhecido, answer kind nao suportado e campos em branco
- persiste um artifact proprio de submissao, sem mutar o attempt session de origem
- mantem correction, scoring e progress mutation desabilitados

Endpoints atuais do answer submission:

- `POST /api/simulado-attempt-session/{attempt_session_id}/answer-submission/build`
- `GET /api/simulado-attempt-session/{attempt_session_id}/answer-submission`
- `GET /api/simulado-answer-submission/{answer_submission_id}`

Regras importantes:

- esta etapa grava apenas respostas brutas fornecidas pelo usuario
- esta etapa nao corrige respostas
- esta etapa nao calcula score, grade ou simulado result
- esta etapa nao expõe correct answer, answer key ou gabarito
- esta etapa nao muta progresso, ranking, retention ou scheduler
- texto curto e sanitizado e bounded

Trabalho futuro desta trilha:

- Answer Submission Stabilization Fixtures
- Correction Shell Stabilization Fixtures
- real Simulado Execution/Correction Foundation

## Fundacao de correction readiness / correction shell

Answer submissions agora podem gerar um artifact separado de `correction shell`, sempre user-scoped, deterministico e readiness-only.

Capacidades atuais desta etapa:

- avalia readiness estrutural para correcao futura a partir de um `SimuladoAnswerSubmission`
- cria registros por resposta submetida com blockers e estados de readiness
- registra indisponibilidade de final answer keys, correction rules e score rules
- persiste um artifact proprio de correction readiness, sem mutar answer submission ou attempt session de origem
- mantem correction, scoring e progress mutation desabilitados

Endpoints atuais de correction shell:

- `POST /api/simulado-answer-submission/{answer_submission_id}/correction-shell/build`
- `GET /api/simulado-answer-submission/{answer_submission_id}/correction-shell`
- `GET /api/simulado-correction-shell/{correction_shell_id}`

Regras importantes:

- esta etapa nao corrige respostas
- esta etapa nao calcula score, grade ou simulado result
- esta etapa nao expõe answer key, correct answer ou gabarito
- esta etapa nao marca respostas como corretas/incorretas
- esta etapa nao muta progresso, ranking, retention ou scheduler

Trabalho futuro desta trilha:

- Correction Shell Stabilization Fixtures
- real Simulado Execution/Correction Foundation

## Fundacao de final answer key exposure boundary / correction input contract

Correction shells agora podem gerar um artifact separado de `answer key boundary`, sempre user-scoped, deterministico e internal-only.

Capacidades atuais desta etapa:

- cria um correction input contract interno a partir de um `SimuladoCorrectionShell`
- registra readiness por resposta para correcao futura sem expor answer key ou gabarito
- persiste metadados redacted/hash-only de referencia interna quando necessario, sem retornar valor bruto de answer key
- registra indisponibilidade de internal answer key references, correction rules e score rules
- mantem correction, scoring e progress mutation desabilitados

Endpoints atuais de answer key boundary:

- `POST /api/simulado-correction-shell/{correction_shell_id}/answer-key-boundary/build`
- `GET /api/simulado-correction-shell/{correction_shell_id}/answer-key-boundary`
- `GET /api/simulado-answer-key-boundary/{answer_key_boundary_id}`

Regras importantes:

- esta etapa cria apenas contracts internos de correcao futura
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente
- esta etapa nao corrige respostas
- esta etapa nao calcula score, grade ou simulado result
- esta etapa nao muta progresso, ranking, retention ou scheduler

Trabalho futuro desta trilha:

- Correction Result Foundation
- Scoring Foundation
- Progress Mutation Guardrails
- Integrated Execution/Correction Foundation

## Fundacao de correction result

Answer key boundaries agora podem gerar um artifact separado de `correction result`, sempre user-scoped, deterministico e non-scoreable.

Capacidades atuais desta etapa:

- cria um correction result a partir de um `SimuladoAnswerKeyBoundary`
- registra estados por resposta submetida com blockers, review flags e disponibilidade estrutural de correcao
- persiste um artifact proprio de correction result, sem mutar boundary, correction shell ou answer submission de origem
- mantem scoring, final simulado result e progress mutation desabilitados
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de correction result:

- `POST /api/simulado-answer-key-boundary/{answer_key_boundary_id}/correction-result/build`
- `GET /api/simulado-answer-key-boundary/{answer_key_boundary_id}/correction-result`
- `GET /api/simulado-correction-result/{correction_result_id}`

Regras importantes:

- esta etapa cria apenas correction result artifacts non-scoreable
- esta etapa nao cria score, grade ou final simulado result
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente
- esta etapa nao muta progresso, ranking, retention ou scheduler

Trabalho futuro desta trilha:

- Correction Result Stabilization Fixtures
- Progress Mutation Guardrails
- Integrated Execution/Correction Foundation

## Fundacao de scoring

Correction results agora podem gerar um artifact separado de `score result`, sempre user-scoped, deterministico e isolado do runtime pedagogico.

Capacidades atuais desta etapa:

- cria um score result a partir de um `SimuladoCorrectionResult`
- registra item-level score records, score summary e score policy metadata conservadora
- preserva blockers, needs-review counts e itens nao scoreable sem inventar corretude ou gabarito
- persiste um artifact proprio de scoring, sem mutar correction result, answer key boundary, correction shell ou answer submission de origem
- mantem progress, ranking, retention, scheduler, study cycle e curriculum graph sem mutacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de scoring:

- `POST /api/simulado-correction-result/{correction_result_id}/score/build`
- `GET /api/simulado-correction-result/{correction_result_id}/score`
- `GET /api/simulado-score-result/{score_result_id}`

Regras importantes:

- esta etapa cria apenas score result artifacts
- esta etapa nao aplica score ao runtime pedagogico
- esta etapa nao muta progresso, ranking, retention, scheduler, study cycle ou curriculum graph
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente
- score so e computado quando correction records e policy persistida forem explicitamente seguros; caso contrario o artifact permanece blocked/no_scoreable_items

Trabalho futuro desta trilha:

- Scoring Stabilization Fixtures
- Progress Mutation Guardrails
- Integrated Execution/Correction Foundation

## Fundacao de progress mutation guardrails

Score results agora podem gerar um artifact separado de `progress guardrail`, sempre user-scoped, deterministico e isolado do runtime pedagogico.

Capacidades atuais desta etapa:

- cria um progress mutation guardrail a partir de um `SimuladoScoreResult`
- registra elegibilidade futura para progresso, ranking, retention, scheduler, study cycle e curriculum graph sem aplicar nenhuma mutacao
- persiste candidate progress targets e score completeness assessment apenas para revisao futura
- registra blockers de score incompleto, falta de mapping, falta de policy confirmation e runtime mutation disabled
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de progress guardrails:

- `POST /api/simulado-score-result/{score_result_id}/progress-guardrail/build`
- `GET /api/simulado-score-result/{score_result_id}/progress-guardrail`
- `GET /api/simulado-progress-guardrail/{progress_guardrail_id}`

Regras importantes:

- esta etapa cria apenas guardrail artifacts
- esta etapa nao muta progresso
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Progress Mutation Guardrails Stabilization Fixtures
- Integrated Execution/Correction Foundation

## Fundacao de integrated execution/correction

Attempt sessions agora podem gerar um artifact separado de `integrated execution/correction`, sempre user-scoped, deterministico e read-only.

Capacidades atuais desta etapa:

- cria um integrated result a partir de um `SimuladoAttemptSession`
- resolve e resume a cadeia `answer submission -> correction shell -> answer key boundary -> correction result -> score result -> progress guardrail`
- registra disponibilidade de artifacts, estados de correction/score/guardrail e blockers finais de runtime mutation disabled
- persiste um artifact proprio de integracao, sem mutar attempt session, submission, correction, score ou guardrail de origem
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem mutacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de integrated execution/correction:

- `POST /api/simulado-attempt-session/{attempt_session_id}/integrated-result/build`
- `GET /api/simulado-attempt-session/{attempt_session_id}/integrated-result`
- `GET /api/simulado-integrated-result/{integrated_result_id}`

Regras importantes:

- esta etapa cria apenas artifacts integrados read-only
- esta etapa nao aplica score ao runtime pedagogico
- esta etapa nao muta progresso, ranking, retention, scheduler, study cycle ou curriculum graph
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Integrated Execution/Correction Stabilization Fixtures
- Safe Runtime Progress Application Foundation

## Fundacao de safe runtime progress application guardrails

Integrated results agora podem gerar um artifact separado de `runtime application guardrail`, sempre user-scoped, deterministico e isolado de qualquer aplicacao real no runtime pedagogico.

Capacidades atuais desta etapa:

- cria um runtime application guardrail a partir de um `SimuladoIntegratedExecutionCorrection`
- avalia completude da cadeia integrada, presenca/seguranca do score e favorabilidade do progress guardrail sem aplicar nenhuma mutacao
- persiste candidate mutation intents e affected runtime surfaces apenas como metadados de revisao futura
- registra blockers de integrated chain incompleta, score ausente/incompleto, progress guardrail ausente/nao elegivel, runtime policy missing e runtime mutation disabled
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de runtime application guardrails:

- `POST /api/simulado-integrated-result/{integrated_result_id}/runtime-guardrail/build`
- `GET /api/simulado-integrated-result/{integrated_result_id}/runtime-guardrail`
- `GET /api/simulado-runtime-guardrail/{runtime_guardrail_id}`

Regras importantes:

- esta etapa cria apenas runtime application guardrail artifacts
- esta etapa nao aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Safe Runtime Progress Application Guardrail Stabilization Fixtures
- Runtime Progress Application Foundation

## Fundacao de runtime progress application

Runtime application guardrails agora podem gerar um artifact separado de `runtime progress application`, sempre user-scoped, deterministico e dry-run/planned-only.

Capacidades atuais desta etapa:

- cria um runtime progress application a partir de um `SimuladoRuntimeApplicationGuardrail`
- registra um application plan, planned mutation intents, proposed runtime surface diffs e audit trail placeholders sem aplicar nenhuma mutacao real
- persiste um artifact proprio de dry-run/planned application, sem mutar runtime guardrail, integrated result, score result ou progress guardrail de origem
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de runtime progress application:

- `POST /api/simulado-runtime-guardrail/{runtime_guardrail_id}/progress-application/build`
- `GET /api/simulado-runtime-guardrail/{runtime_guardrail_id}/progress-application`
- `GET /api/simulado-progress-application/{application_id}`

Regras importantes:

- esta etapa cria apenas dry-run/planned application artifacts
- esta etapa nao aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Runtime Progress Application Stabilization Fixtures
- Controlled Runtime Progress Apply Foundation

## Fundacao de controlled runtime progress apply shell

Runtime progress applications agora podem gerar um artifact separado de `controlled apply shell`, sempre user-scoped, deterministico e limitado a validacao pre-apply.

Capacidades atuais desta etapa:

- cria um controlled apply shell a partir de um `SimuladoRuntimeProgressApplication`
- valida precondicoes de future apply, incluindo runtime policy, explicit apply approval, audit confirmation e rollback plan sem aplicar nenhuma mutacao real
- registra intent decisions, surface decisions, audit requirements, blockers e audit trail de pre-apply sem mutar runtime progress application, runtime guardrail, integrated result, score result ou progress guardrail de origem
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de controlled apply shell:

- `POST /api/simulado-progress-application/{application_id}/controlled-apply-shell/build`
- `GET /api/simulado-progress-application/{application_id}/controlled-apply-shell`
- `GET /api/simulado-controlled-apply-shell/{apply_shell_id}`

Regras importantes:

- esta etapa cria apenas controlled apply shell artifacts
- esta etapa valida requisitos de pre-apply, mas nao aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Controlled Runtime Progress Apply Stabilization Fixtures
- Explicit Runtime Progress Apply Foundation

## Fundacao de explicit runtime progress apply

Controlled apply shells agora podem gerar um artifact separado de `explicit runtime progress apply`, sempre user-scoped, deterministico e limitado ao registro de decisao explicita.

Capacidades atuais desta etapa:

- cria um explicit runtime progress apply a partir de um `SimuladoControlledRuntimeApplyShell`
- registra decisoes `approve`, `deny`, `request_revision`, `block_apply` e `mark_not_reviewed`, com confirmacoes conservadoras e bounded
- interpreta `approve` apenas como aprovacao para future runtime mutation review, nunca como aplicacao real
- persiste intent approvals, surface approvals e audit trail de decisao explicita sem mutar controlled apply shell, runtime progress application, runtime guardrail, integrated result, score result ou progress guardrail de origem
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de explicit runtime progress apply:

- `POST /api/simulado-controlled-apply-shell/{apply_shell_id}/explicit-apply/build`
- `GET /api/simulado-controlled-apply-shell/{apply_shell_id}/explicit-apply`
- `GET /api/simulado-explicit-apply/{explicit_apply_id}`

Regras importantes:

- esta etapa cria apenas explicit apply decision artifacts
- aprovacao significa apenas future runtime mutation review, nao aplicacao real
- esta etapa nao aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Explicit Runtime Progress Apply Stabilization Fixtures
- Runtime Progress Mutation Foundation

## Fundacao de runtime progress mutation

Explicit runtime applies agora podem gerar um artifact separado de `runtime progress mutation transaction`, sempre user-scoped, deterministico e limitado a proposta de mutacao dry-run.

Capacidades atuais desta etapa:

- cria um runtime progress mutation transaction a partir de um `SimuladoExplicitRuntimeProgressApply`
- registra proposed progress deltas e proposed runtime surface updates apenas como resumos bounded
- inclui rollback plan metadata e audit trail de proposta sem executar commit
- persiste a transaction proposal sem mutar explicit apply, controlled apply shell, runtime progress application, runtime guardrail, integrated result, score result ou progress guardrail de origem
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de runtime progress mutation:

- `POST /api/simulado-explicit-apply/{explicit_apply_id}/progress-mutation/build`
- `GET /api/simulado-explicit-apply/{explicit_apply_id}/progress-mutation`
- `GET /api/simulado-progress-mutation/{mutation_transaction_id}`

Regras importantes:

- esta etapa cria apenas mutation transaction / proposal artifacts
- proposed deltas e surface updates continuam dry-run only, nunca commit real
- esta etapa nao faz mutation commit nem aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Runtime Progress Mutation Stabilization Fixtures
- Controlled Runtime Mutation Commit Foundation

## Fundacao de controlled runtime mutation commit shell

Runtime progress mutation transactions agora podem gerar um artifact separado de `controlled runtime mutation commit shell`, sempre user-scoped, deterministico e limitado a validacao pre-commit.

Capacidades atuais desta etapa:

- cria um controlled mutation commit shell a partir de um `SimuladoRuntimeProgressMutationTransaction`
- registra precondition summary, rollback readiness, delta commit decisions, surface commit decisions e audit requirements apenas como resumos bounded
- persiste a commit shell sem executar mutation commit
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de controlled runtime mutation commit shell:

- `POST /api/simulado-progress-mutation/{mutation_transaction_id}/commit-shell/build`
- `GET /api/simulado-progress-mutation/{mutation_transaction_id}/commit-shell`
- `GET /api/simulado-mutation-commit-shell/{commit_shell_id}`

Regras importantes:

- esta etapa cria apenas controlled commit shell artifacts
- esta etapa valida requisitos pre-commit, mas nao executa mutation commit
- esta etapa nao aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria mutation commit events, runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Controlled Runtime Mutation Commit Stabilization Fixtures
- Explicit Runtime Mutation Commit Stabilization Fixtures

## Fundacao de explicit runtime mutation commit

Controlled runtime mutation commit shells agora podem gerar um artifact separado de `explicit runtime mutation commit`, sempre user-scoped, deterministico e limitado a decisao explicita humana para revisao futura.

Capacidades atuais desta etapa:

- cria um explicit runtime mutation commit a partir de um `SimuladoControlledRuntimeMutationCommitShell`
- registra decisoes `approve`, `deny`, `request_revision`, `block` e `mark_not_reviewed` apenas como artifact de decisao bounded
- registra confirmation summary, delta approvals, surface approvals e audit trail apenas como metadados de revisao futura
- persiste a explicit commit artifact sem executar mutation commit
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de explicit runtime mutation commit:

- `POST /api/simulado-mutation-commit-shell/{commit_shell_id}/explicit-commit/build`
- `GET /api/simulado-mutation-commit-shell/{commit_shell_id}/explicit-commit`
- `GET /api/simulado-explicit-commit/{explicit_commit_id}`

Regras importantes:

- esta etapa cria apenas explicit commit decision artifacts
- `approve` significa somente future mutation commit review, nunca actual commit
- esta etapa nao faz mutation commit nem aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria mutation commit events, runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Explicit Runtime Mutation Commit Stabilization Fixtures
- Runtime Mutation Commit Transaction Foundation
- Controlled Runtime Commit Execution Guardrail Foundation

## Fundacao de runtime mutation commit transaction

Explicit runtime mutation commits agora podem gerar um artifact separado de `runtime mutation commit transaction`, sempre user-scoped, deterministico e limitado a commit planning / dry-run transaction metadata.

Capacidades atuais desta etapa:

- cria um runtime mutation commit transaction a partir de um `SimuladoExplicitRuntimeMutationCommit`
- registra planned progress commits e planned runtime surface commits apenas como resumos bounded de futura execucao
- registra rollback execution plan metadata sem executar rollback nem commit
- persiste o commit transaction artifact sem executar mutation commit
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de runtime mutation commit transaction:

- `POST /api/simulado-explicit-commit/{explicit_commit_id}/commit-transaction/build`
- `GET /api/simulado-explicit-commit/{explicit_commit_id}/commit-transaction`
- `GET /api/simulado-commit-transaction/{commit_transaction_id}`

Regras importantes:

- esta etapa cria apenas commit transaction / commit execution plan artifacts
- o artifact e plan-only / dry-run only, nunca actual commit execution
- esta etapa nao faz mutation commit nem aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria mutation commit events, runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Runtime Mutation Commit Transaction Stabilization Fixtures
- Controlled Runtime Commit Execution Guardrail Foundation

## Fundacao de controlled runtime commit execution guardrail

Runtime mutation commit transactions agora podem gerar um artifact separado de `controlled runtime commit execution guardrail`, sempre user-scoped, deterministico e limitado a readiness/safety validation para futura execucao controlada.

Capacidades atuais desta etapa:

- cria um controlled runtime commit execution guardrail a partir de um `SimuladoRuntimeMutationCommitTransaction`
- valida commit transaction safety, rollback execution readiness, planned progress commit checks e planned surface commit checks apenas como metadados bounded
- registra audit requirements e audit trail apenas como requisitos de futura execucao
- persiste o execution guardrail artifact sem executar commit
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de controlled runtime commit execution guardrail:

- `POST /api/simulado-commit-transaction/{commit_transaction_id}/execution-guardrail/build`
- `GET /api/simulado-commit-transaction/{commit_transaction_id}/execution-guardrail`
- `GET /api/simulado-commit-execution-guardrail/{execution_guardrail_id}`

Regras importantes:

- esta etapa cria apenas execution guardrail/readiness artifacts
- esta etapa nao executa commit nem mutation commit
- esta etapa nao aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria commit execution events, mutation commit events, runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Controlled Runtime Commit Execution Guardrail Stabilization Fixtures
- Explicit Runtime Commit Execution Approval Foundation

## Fundacao de explicit runtime commit execution approval

Controlled runtime commit execution guardrails agora podem gerar um artifact separado de `explicit runtime commit execution approval`, sempre user-scoped, deterministico e limitado a decisao explicita humana para futura revisao de execucao controlada.

Capacidades atuais desta etapa:

- cria um explicit runtime commit execution approval a partir de um `SimuladoControlledRuntimeCommitExecutionGuardrail`
- registra decisoes `approve`, `deny`, `request_revision`, `block` e `mark_not_reviewed` apenas como artifact explicito bounded
- registra confirmation summary, progress execution approvals e surface execution approvals apenas para futura revisao
- persiste o explicit execution approval artifact sem executar commit
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de explicit runtime commit execution approval:

- `POST /api/simulado-commit-execution-guardrail/{execution_guardrail_id}/explicit-execution-approval/build`
- `GET /api/simulado-commit-execution-guardrail/{execution_guardrail_id}/explicit-execution-approval`
- `GET /api/simulado-explicit-execution-approval/{execution_approval_id}`

Regras importantes:

- esta etapa cria apenas explicit execution approval artifacts
- approval significa apenas future controlled execution review, nao execucao real
- esta etapa nao executa commit nem mutation commit
- esta etapa nao aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria commit execution events, mutation commit events, runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Explicit Runtime Commit Execution Approval Stabilization Fixtures
- Runtime Commit Execution Plan Foundation

## Fundacao de runtime commit execution plan

Explicit runtime commit execution approvals agora podem gerar um artifact separado de `runtime commit execution plan`, sempre user-scoped, deterministico e limitado a consolidacao final de metadata aprovada para futura revisao de execucao controlada.

Capacidades atuais desta etapa:

- cria um runtime commit execution plan a partir de um `SimuladoExplicitRuntimeCommitExecutionApproval`
- consolida approved future-review execution metadata em phases, planned progress steps e planned surface steps
- cria rollback checkpoints e audit checkpoints bounded
- registra blockers, validation findings e warnings apenas para futura revisao
- persiste o execution plan artifact sem executar commit
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de runtime commit execution plan:

- `POST /api/simulado-explicit-execution-approval/{execution_approval_id}/execution-plan/build`
- `GET /api/simulado-explicit-execution-approval/{execution_approval_id}/execution-plan`
- `GET /api/simulado-execution-plan/{execution_plan_id}`

Regras importantes:

- esta etapa cria apenas runtime commit execution plan artifacts
- o artifact permanece execution-plan-only e dry-run-only
- esta etapa nao executa commit nem mutation commit
- esta etapa nao aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria commit execution events, mutation commit events, runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Runtime Commit Execution Plan Stabilization Fixtures
- Controlled Runtime Commit Execution Foundation

## Fundacao de controlled runtime commit execution

Runtime commit execution plans agora podem gerar um artifact separado de `controlled runtime commit execution`, sempre user-scoped, deterministico e limitado a um dry-run/preview de execucao controlada.

Capacidades atuais desta etapa:

- cria um controlled runtime commit execution a partir de um `SimuladoRuntimeCommitExecutionPlan`
- avalia phases, progress steps, surface steps, rollback verifications e audit verifications sem executar commit
- registra blockers, validation findings, warnings e audit trail entries apenas para preview controlado
- persiste o controlled execution artifact sem mutation commit nem runtime application
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de controlled runtime commit execution:

- `POST /api/simulado-execution-plan/{execution_plan_id}/controlled-execution/build`
- `GET /api/simulado-execution-plan/{execution_plan_id}/controlled-execution`
- `GET /api/simulado-controlled-execution/{controlled_execution_id}`

Regras importantes:

- esta etapa cria apenas controlled execution dry-run artifacts
- o artifact permanece dry-run-only e execution-preview-only
- esta etapa nao executa commit nem mutation commit
- esta etapa nao aplica progresso ao runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao cria commit execution events, mutation commit events, runtime application events nem final pedagogical update events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Controlled Runtime Commit Execution Stabilization Fixtures
- Final Pedagogical Update Event Foundation

## Fundacao de final pedagogical update event

Controlled runtime commit executions agora podem gerar um artifact separado de `final pedagogical update event`, sempre user-scoped, deterministico e limitado a uma proposta final de atualizacao pedagogica sem aplicacao real.

Capacidades atuais desta etapa:

- cria um final pedagogical update event a partir de um `SimuladoControlledRuntimeCommitExecution`
- consolida proposed progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning updates de forma bounded
- registra blockers, validation findings, warnings e audit trail apenas para proposta final dry-run
- persiste o final event artifact sem aplicar o evento e sem runtime mutation
- mantem progress, ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning sem aplicacao
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de final pedagogical update event:

- `POST /api/simulado-controlled-execution/{controlled_execution_id}/final-pedagogical-event/build`
- `GET /api/simulado-controlled-execution/{controlled_execution_id}/final-pedagogical-event`
- `GET /api/simulado-final-pedagogical-event/{final_event_id}`

Regras importantes:

- esta etapa cria apenas final pedagogical update event proposal artifacts
- o artifact permanece event-proposal-only e dry-run-final-event-only
- esta etapa nao aplica o evento final
- esta etapa nao muta progresso nem runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao executa adaptive tuning
- esta etapa nao cria applied final pedagogical update events nem runtime application events
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Final Pedagogical Update Event Stabilization Fixtures
- Runtime Apply Policy / Feature Flag Foundation
- Minimal Progress Ledger Apply Foundation

## Fundacao de runtime apply policy / feature flag

Final pedagogical update events agora podem gerar um artifact separado de `runtime apply policy`, sempre user-scoped, deterministico e limitado a um policy gate para futuras aplicacoes sem aplicar nada no runtime atual.

Capacidades atuais desta etapa:

- cria um runtime apply policy a partir de um `SimuladoFinalPedagogicalUpdateEvent`
- avalia feature flag snapshot, apply scope policy, idempotency, rollback, audit, human review e environment safety
- persiste o policy artifact sem aplicar final event, sem progress ledger apply e sem runtime mutation
- mantem feature flag desabilitada por padrao e `runtime_apply_allowed_now = false`
- mantem minimal progress ledger apply desabilitado
- mantem ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning apply desabilitados
- mantem answer key e gabarito sem exposicao publica

Endpoints atuais de runtime apply policy:

- `POST /api/simulado-final-pedagogical-event/{final_event_id}/runtime-apply-policy/build`
- `GET /api/simulado-final-pedagogical-event/{final_event_id}/runtime-apply-policy`
- `GET /api/simulado-runtime-apply-policy/{runtime_apply_policy_id}`

Regras importantes:

- esta etapa cria apenas runtime apply policy artifacts
- o artifact permanece policy-gate-only e feature-flag-gate-only
- esta etapa nao aplica o final event
- esta etapa nao muta progresso nem runtime pedagogico
- esta etapa nao atualiza ranking, retention ou scheduler
- esta etapa nao altera study cycle ou curriculum graph
- esta etapa nao executa adaptive tuning
- esta etapa nao cria applied final pedagogical update events nem applied progress ledger entries
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Runtime Apply Policy / Feature Flag Stabilization Fixtures
- Minimal Progress Ledger Apply Foundation

## Fundacao de minimal progress ledger apply

Runtime apply policies agora podem gerar um artifact separado de `minimal progress ledger apply`, sempre user-scoped, deterministico, idempotente e limitado a um ledger isolado de simulado sem propagar efeitos para o runtime pedagogico maior.

Capacidades atuais desta etapa:

- cria um `SimuladoMinimalProgressLedgerApply` a partir de um `SimuladoRuntimeApplyPolicy`
- aplica apenas bounded ledger entries derivados de proposed progress updates do final event
- persiste o apply artifact com idempotency record, rollback record e audit trail
- aplica somente ao escopo `minimal_progress_ledger`
- nao muta existing progress aggregates nem global runtime progress
- nao atualiza ranking, retention, scheduler, study cycle, curriculum graph ou adaptive tuning
- preserva owner scope, JSON safety e no public answer key/gabarito exposure

Endpoints atuais de minimal progress ledger apply:

- `POST /api/simulado-runtime-apply-policy/{runtime_apply_policy_id}/minimal-progress-ledger-apply/build`
- `GET /api/simulado-runtime-apply-policy/{runtime_apply_policy_id}/minimal-progress-ledger-apply`
- `GET /api/simulado-minimal-progress-ledger-apply/{minimal_progress_ledger_apply_id}`

Regras importantes:

- esta etapa e o primeiro limited real apply step
- o apply e isolado ao minimal progress ledger artifact
- esta etapa requer policy gates de runtime apply satisfeitos
- esta etapa e idempotente por `source_runtime_apply_policy_id` e idempotency key
- esta etapa nao muta existing progress aggregates
- esta etapa nao atualiza ranking, retention, scheduler, study cycle, curriculum graph ou adaptive tuning
- esta etapa nao executa commit execution nem mutation commit
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Minimal Progress Ledger Apply Stabilization Fixtures
- Applied Event Ledger / Idempotency Foundation
- Propagation Guardrails

## Fundacao de applied event ledger / idempotency

Minimal progress ledger applies agora podem gerar um artifact separado de `applied event ledger`, sempre user-scoped, deterministico e limitado a registrar, auditar e deduplicar o isolated apply de 48A sem criar novos ledger entries nem propagar efeitos.

Capacidades atuais desta etapa:

- cria um `SimuladoAppliedEventLedger` a partir de um `SimuladoMinimalProgressLedgerApply`
- registra applied event records bounded e source-linked para os ledger entries ja aplicados em 48A
- persiste idempotency record, deduplication record, replay safety record, rollback reference e audit trail
- reforca replay safety e deduplicacao por `source_minimal_progress_ledger_apply_id` e idempotency key
- nao cria novos progress ledger entries
- nao muta existing progress aggregates nem global runtime progress
- nao atualiza ranking, retention, scheduler, study cycle, curriculum graph ou adaptive tuning

Endpoints atuais de applied event ledger:

- `POST /api/simulado-minimal-progress-ledger-apply/{minimal_progress_ledger_apply_id}/applied-event-ledger/build`
- `GET /api/simulado-minimal-progress-ledger-apply/{minimal_progress_ledger_apply_id}/applied-event-ledger`
- `GET /api/simulado-applied-event-ledger/{applied_event_ledger_id}`

Regras importantes:

- esta etapa e uma ledger/idempotency layer, nao uma propagation layer
- esta etapa nao cria novos applies de progresso
- esta etapa nao marca o final event como globally applied
- esta etapa nao muta existing progress aggregates
- esta etapa nao atualiza ranking, retention, scheduler, study cycle, curriculum graph ou adaptive tuning
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Applied Event Ledger / Idempotency Stabilization Fixtures
- Propagation Guardrails

## Fundacao de propagation guardrail

Applied event ledgers agora podem gerar um artifact separado de `propagation guardrail`, sempre user-scoped, deterministico e limitado a avaliar readiness para futuras propagacoes sem executar nenhuma propagacao real.

Capacidades atuais desta etapa:

- cria um `SimuladoPropagationGuardrail` a partir de um `SimuladoAppliedEventLedger`
- gera candidate propagation targets bounded para ranking, retention, scheduler, study cycle, curriculum graph e adaptive tuning
- persiste readiness summary, source ledger summary, surface risk summary, blockers, warnings e audit trail
- avalia replay safety, deduplication enforcement, no-propagation state e sinais de unsafe source state
- nao propaga
- nao cria review schedule entries
- nao cria novos progress applies
- nao muta existing progress aggregates nem global runtime progress
- nao atualiza ranking, retention, scheduler, study cycle, curriculum graph ou adaptive tuning

Endpoints atuais de propagation guardrail:

- `POST /api/simulado-applied-event-ledger/{applied_event_ledger_id}/propagation-guardrail/build`
- `GET /api/simulado-applied-event-ledger/{applied_event_ledger_id}/propagation-guardrail`
- `GET /api/simulado-propagation-guardrail/{propagation_guardrail_id}`

Regras importantes:

- esta etapa e propagation guardrail/readiness only, nao propagation
- todos os candidate targets permanecem `propagation_allowed = false` e `propagated = false`
- esta etapa nao muta existing progress aggregates
- esta etapa nao marca o final event como globally applied
- esta etapa nao cria ranking, retention, scheduler, study cycle, curriculum graph ou adaptive tuning updates
- esta etapa nao expõe answer key, answer key value, correct answer ou gabarito publicamente

Trabalho futuro desta trilha:

- Propagation Guardrail Stabilization Fixtures
- Controlled Propagation Apply Foundation

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
- para `PDF` escaneado ou sem texto utilizavel, registra `pending_extraction` com indicacao de OCR-required; quando OCR estiver explicitamente habilitado e as dependencias estiverem disponiveis, o pipeline pode tentar OCR de forma limitada e segura

Limitacoes importantes:

- OCR existe apenas como foundation opcional e limitada, desabilitada por padrao e dependente de engine externa
- a extracao de PDF ainda e basica e textual, com OCR apenas como fallback opcional e sem layout parsing robusto
- PDFs escaneados ou sem texto utilizavel continuam OCR-required quando OCR estiver desabilitado, indisponivel ou insuficiente
- a ingestao edital-aware existe como fundacao candidata e deterministica, mas ainda nao e uma extracao final/validada
- upload, processamento documental e ingestao de edital continuam sendo etapas separadas

O endpoint legado `POST /api/documents/upload` foi preservado para o prototipo atual e para os testes existentes do pipeline PDF processado.

## Fundacao do pipeline de documentos

Materiais enviados agora podem entrar em um pipeline estruturado, user-scoped e observavel.

Capacidades atuais desta etapa:

- `TXT`: extracao simples de texto
- `MD`: extracao simples de texto com deteccao basica de headings `#`, `##` e `###`
- `PDF` textual: extracao basica de texto com adapter leve e reaproveitamento do chunking/sectioning atual
- OCR Adapter Foundation opcional para PDFs sem texto embutido utilizavel
- chunking deterministico por texto/paragrafos para `TXT` e `MD`
- sectioning simples para `TXT`, `MD` e `PDF` textual com fallback `Document`
- `PDF` escaneado/sem texto: registro em estado `pending_extraction` com `ocr_required`; quando OCR estiver habilitado e disponivel, o pipeline pode tentar OCR antes de manter o fallback seguro
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
- OCR e desabilitado por padrao
- OCR depende de engine externa, como Tesseract, quando configurado
- a aplicacao continua funcionando sem Tesseract instalado
- OCR respeita limite de paginas e DPI
- OCR nao roda no upload, dashboard ou endpoints GET
- OCR nao roda em `/inspection` nem em `/api/inspection/runtime`
- OCR nao roda antes da extracao textual normal do PDF
- o pipeline atual nao faz parsing de edital
- o pipeline atual nao cria embeddings, vetores ou busca semantica
- `storage_path` em respostas continua relativo e seguro

Comportamento atual para PDFs:

- PDF textual simples: extrai texto, cria chunks deterministas, cria secao fallback e conclui em `metadata_ready`
- PDF sem texto utilizavel ou escaneado: primeiro permanece em `extraction_pending` com warnings como `pdf_text_empty` e `ocr_required`; quando OCR estiver habilitado e disponivel, o pipeline pode tentar OCR de forma limitada
- OCR util: reaproveita o chunking e o sectioning existentes sem criar uma pipeline paralela
- OCR vazio, insuficiente, indisponivel ou com falha: preserva o fallback seguro de `ocr_required` ou estado conservador equivalente
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

## Fundacao de question generation blueprint

Cada slot candidato do simulado agora pode ser mapeado para um artifact de planejamento source-grounded, user-scoped e review-friendly para uma futura etapa de draft.

Capacidades atuais desta etapa:

- mapeamento deterministico de slots do simulado para blueprints de geracao de questao
- readiness conservador por slot como `ready_for_draft`, `needs_review`, `blocked_by_ocr`, `blocked_by_material_gap` e `blocked_by_insufficient_coverage`
- source evidence bounded com referencias a `document_id`, `section_id` e `chunk_id` quando disponiveis
- style hints declarativos a partir de exam profile e simulado blueprint
- constraints explicitas para impedir geracao sem evidencia, com OCR pendente, com material faltante ou com formato/perfil ambiguos
- persistencia user-scoped do conjunto de blueprints e leitura owner-only

Endpoints atuais de question generation blueprint:

- `POST /api/simulado-blueprint/{blueprint_id}/question-generation-blueprint/build`
- `GET /api/simulado-blueprint/{blueprint_id}/question-generation-blueprint`
- `GET /api/question-generation-blueprint/{question_generation_blueprint_id}`

Regras importantes:

- esta etapa produz planning artifacts apenas, nao questoes finais
- nao gera `question_text`, `stem`, `statement`, alternativas, distratores, respostas, explicacoes ou gabarito
- nao chama LLM, RAG, vector DB, embeddings ou servicos externos
- usa apenas artifacts ja persistidos como simulado blueprint, curriculum graph, chunks, secoes, alignment e exam profile
- snippets continuam bounded e sanitizados, sem corpo bruto completo do documento nem caminhos absolutos
- build e deterministico e user-scoped; leituras por `GET` nao constroem nem mutam nada

## Fundacao de question draft generation

Question drafts agora podem ser criados apenas a partir de `QuestionGenerationBlueprints` com `readiness_state = ready_for_draft`.

Capacidades atuais desta etapa:

- criacao deterministica de drafts provisiorios e auditaveis a partir de blueprints prontos
- drafts source-grounded com referencias a evidencias ja persistidas
- templates bounded por `question_kind`, `format_type`, `board_id` e `exam_family`
- suporte inicial para drafts `assertion_judgement`, `case_based_multiple_choice`, `technical_maritime_scenario` e `direct_multiple_choice`
- placeholders de alternativas apenas quando o draft for de multipla escolha
- provenance, validation summary, constraints e warnings preservados no artifact
- persistencia user-scoped e owner-only do draft set

Endpoints atuais de question draft generation:

- `POST /api/question-generation-blueprint/{blueprint_set_id}/question-drafts/build`
- `GET /api/question-generation-blueprint/{blueprint_set_id}/question-drafts`
- `GET /api/question-draft-set/{draft_set_id}`

Regras importantes:

- drafts sao sempre provisiorios, `review_required = true` e `finalization_blocked = true`
- drafts so sao criados a partir de blueprints `ready_for_draft`
- drafts permanecem bounded e source-grounded
- drafts nao incluem `answer_key`, `gabarito`, alternativas finais, distractors ou explicacoes finais
- drafts nao executam simulados nem alteram study cycle, runtime, ranking, sessao ou scheduler
- a etapa nao chama LLM, RAG, vector DB, embeddings ou servicos externos

## Fundacao de answer key / explanation guardrails

Question drafts agora podem receber uma avaliacao deterministica e user-scoped de prontidao para futuros candidatos de answer key e explanation.

Capacidades atuais desta etapa:

- criacao de guardrail assessments source-grounded e auditaveis a partir de `QuestionDrafts` existentes
- avaliacao separada de `answer_key_state`, `explanation_state` e `source_support_assessment`
- candidatos nao finais de answer key com `candidate_value` normalmente nulo e `allowed_values` apenas quando seguro
- explanation outlines curtos, bounded e ancorados em `safe_snippets`, quando houver suporte suficiente
- findings e warnings para draft ambiguo, evidencia ausente, formato nao suportado e necessidade de revisao humana
- persistencia user-scoped e owner-only do guardrail por draft

Endpoints atuais de answer key / explanation guardrails:

- `POST /api/question-drafts/{draft_id}/answer-explanation-guardrail/build`
- `GET /api/question-drafts/{draft_id}/answer-explanation-guardrail`
- `GET /api/answer-explanation-guardrail/{guardrail_id}`

Regras importantes:

- esta etapa produz assessment/candidate artifacts apenas, nao answer keys ou explanations finais
- `candidate_answer_key` nao e `final_answer_key`
- `candidate_explanation` nao e `final_explanation`
- tudo continua `review_required = true` e `finalization_blocked = true`
- a etapa nao finaliza questoes, nao monta simulados, nao corrige respostas e nao gera score/correction rules
- a etapa usa apenas `QuestionDrafts` e referencias de fonte ja persistidas
- a etapa nao chama LLM, RAG, vector DB, embeddings ou servicos externos

## Fundacao de simulado question assembly

Um `SimuladoBlueprint` agora pode produzir um assembly candidate-only, source-grounded e guardrail-aware que organiza drafts e guardrails existentes em um pacote de revisao humana.

Capacidades atuais desta etapa:

- montagem deterministica e user-scoped de candidates a partir de `SimuladoBlueprint`, `QuestionGenerationBlueprintSet`, `QuestionDraftSet` e `AnswerExplanationGuardrail`
- readiness conservador por candidate como `candidate_ready_for_review`, `candidate_needs_review` e blockers para draft ausente, guardrail ausente, fonte fraca, OCR, material gap ou formato nao suportado
- resumos bounded de draft, guardrail e source evidence, sem expor texto bruto completo nem conteudo executavel
- findings e warnings explicitos para explicar por que o assembly continua nao executavel e nao scoreable
- persistencia owner-only do assembly por simulado blueprint

Endpoints atuais de simulado question assembly:

- `POST /api/simulado-blueprint/{blueprint_id}/question-assembly/build`
- `GET /api/simulado-blueprint/{blueprint_id}/question-assembly`
- `GET /api/simulado-question-assembly/{assembly_id}`

Regras importantes:

- esta etapa produz candidate assemblies nao executaveis apenas
- nao cria questoes finais, answer keys finais, explanations finais, alternativas finais ou distratores
- nao cria correction rules, scoring rules, student attempts ou resultados de simulado
- todo assembly continua `requires_human_review = true`, `not_executable = true` e `not_scoreable = true`
- a etapa usa apenas artifacts ja persistidos e nao rebuilda simulado blueprint, question drafts ou guardrails
- a etapa nao chama LLM, RAG, vector DB, embeddings ou servicos externos

## Fundacao de simulado execution readiness / attempt shell

Assemblies de simulado agora podem gerar um artifact user-scoped de readiness chamado `SimuladoAttemptShell`, ainda estritamente nao executavel e sem qualquer tentativa real de aluno.

Capacidades atuais desta etapa:

- avaliacao deterministica de readiness futura a partir de `SimuladoQuestionAssembly`
- contagem de candidates `ready_for_review`, bloqueados e em revisao, sem transformar isso em questoes executaveis
- blockers explicitos para assembly nao final, questoes nao finalizadas, answer keys finais ausentes, explanations finais ausentes e necessidade de finalizacao humana
- flags declarativas para manter execution, correction, scoring, submissions e progress mutation desligados
- persistencia owner-only do shell por assembly de origem

Endpoints atuais de simulado execution readiness / attempt shell:

- `POST /api/simulado-question-assembly/{assembly_id}/attempt-shell/build`
- `GET /api/simulado-question-assembly/{assembly_id}/attempt-shell`
- `GET /api/simulado-attempt-shell/{attempt_shell_id}`

Regras importantes:

- esta etapa produz readiness/shell artifacts nao executaveis apenas
- `candidate_ready_for_review` nao significa simulado executavel
- `assembly_ready_for_review` nao significa tentativa liberada
- `execution_enabled`, `correction_enabled`, `scoring_enabled` e `student_submission_enabled` permanecem `false`
- nao cria student attempts reais, answer submissions, correction results, scores ou mutacao de progresso
- nao cria questoes finais, answer keys finais ou explanations finais
- a etapa usa apenas `SimuladoQuestionAssembly` ja persistido e nao chama LLM, RAG, vector DB, embeddings ou servicos externos

## Fundacao de finalization / approval guardrails

Attempt shells agora podem gerar um artifact user-scoped de readiness chamado `SimuladoFinalizationGuardrail`, ainda estritamente nao aprovador, nao finalizador e nao executavel.

Capacidades atuais desta etapa:

- avaliacao deterministica de readiness futura para finalization/approval review a partir de `SimuladoQuestionAssembly` e `SimuladoAttemptShell`
- contagem conservadora de candidates `ready_for_review`, bloqueados e em revisao, sem transformar isso em candidates finalizaveis
- blockers explicitos para assembly nao final, attempt shell nao executavel, questoes finais ausentes, answer keys finais ausentes, explanations finais ausentes e revisao humana obrigatoria
- candidate finalization summaries bounded com estados, blockers e flags booleanas sem expor conteudo final
- flags declarativas para manter approval, execution, correction, scoring, submissions e progress mutation desligados
- persistencia owner-only do guardrail por attempt shell de origem

Endpoints atuais de finalization / approval guardrails:

- `POST /api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail/build`
- `GET /api/simulado-attempt-shell/{attempt_shell_id}/finalization-guardrail`
- `GET /api/simulado-finalization-guardrail/{finalization_guardrail_id}`

Regras importantes:

- esta etapa produz artifacts de readiness para approval/finalization review apenas
- `candidate_ready_for_review` nao significa candidate finalizavel
- readiness do attempt shell nao significa simulado executavel
- `approval_required` e `human_review_required` permanecem `true`
- `execution_enabled`, `correction_enabled`, `scoring_enabled`, `student_submission_enabled` e `progress_mutation_enabled` permanecem `false`
- nao aprova nem finaliza simulados
- nao cria student attempts reais, answer submissions, correction results, scores ou mutacao de progresso
- nao cria questoes finais, answer keys finais ou explanations finais
- a etapa usa apenas `SimuladoQuestionAssembly` e `SimuladoAttemptShell` ja persistidos e nao chama LLM, RAG, vector DB, embeddings ou servicos externos

## Fundacao de final approval artifact

Finalization guardrails agora podem gerar um artifact user-scoped e audit-friendly chamado `SimuladoFinalApprovalArtifact`, voltado apenas a registrar decisoes humanas explicitas de review/aprovacao futura.

Capacidades atuais desta etapa:

- registro explicito de decisoes humanas por candidate, como approve for future execution review, reject, request revision, block e mark not reviewed
- trilha de auditoria bounded com actor, event type e mensagem curta
- artifact owner-only persistido por finalization guardrail de origem
- contagens auditaveis de approved, blocked, needs review, rejected e not reviewed
- flags declarativas para manter execution, correction, scoring, submissions e progress mutation desligados mesmo apos decisoes humanas

Endpoints atuais de final approval artifact:

- `POST /api/simulado-finalization-guardrail/{finalization_guardrail_id}/final-approval/build`
- `GET /api/simulado-finalization-guardrail/{finalization_guardrail_id}/final-approval`
- `GET /api/simulado-final-approval/{approval_artifact_id}`

Regras importantes:

- esta etapa registra explicit human approval/review decisions apenas
- approval aqui significa somente future execution review, nunca execucao viva
- `execution_enabled`, `correction_enabled`, `scoring_enabled`, `student_submission_enabled` e `progress_mutation_enabled` permanecem `false`
- nao cria student attempts reais, answer submissions, correction results, scores ou execution sessions
- nao expoe final question content, final answer key content ou final explanation content
- a etapa usa apenas `SimuladoFinalizationGuardrail` ja persistido e nao chama LLM, RAG, vector DB, embeddings ou servicos externos

## Fundacao de simulado execution shell

Final approval artifacts agora podem gerar um artifact user-scoped e non-active chamado `SimuladoExecutionShell`, voltado apenas a resumir estrutura operacional futura sem iniciar execucao.

Capacidades atuais desta etapa:

- cria execution shell nao ativo, owner-only e persistido por final approval artifact de origem
- registra candidate records com ordering metadata deterministico, blockers e readiness states conservadores
- mantem summaries operacionais bounded sobre approved candidates, estimated question count e duration placeholders
- preserva flags declarativas para manter execution, submissions, correction, scoring e progress mutation desligados

Endpoints atuais de simulado execution shell:

- `POST /api/simulado-final-approval/{approval_artifact_id}/execution-shell/build`
- `GET /api/simulado-final-approval/{approval_artifact_id}/execution-shell`
- `GET /api/simulado-execution-shell/{execution_shell_id}`

Regras importantes:

- esta etapa cria apenas operational execution shell artifacts nao ativos
- execution nao e iniciada e attempts reais nao sao criados
- `execution_shell_active`, `execution_started` e `attempt_created` permanecem `false`
- `student_submission_enabled`, `correction_enabled`, `scoring_enabled` e `progress_mutation_enabled` permanecem `false`
- approved candidates nao se tornam executable candidates nesta etapa
- nao expoe final question content, final answer key content ou final explanation content
- a etapa usa apenas `SimuladoFinalApprovalArtifact` ja persistido e nao chama LLM, RAG, vector DB, embeddings ou servicos externos

## Fundacao de simulado attempt session

Execution shells agora podem gerar um artifact user-scoped e prepared-only chamado `SimuladoAttemptSession`, voltado apenas a representar um container de tentativa ainda nao submetivel.

Capacidades atuais desta etapa:

- cria prepared attempt session owner-only e persistido por execution shell de origem
- registra items estruturais com source ids, ordering metadata e timing placeholders
- mantem flags declarativas para answer submission, correction, scoring e progress mutation desabilitados
- preserva blockers e findings explicando por que a sessao ainda nao e submetivel, corrigivel ou scoreable

Endpoints atuais de simulado attempt session:

- `POST /api/simulado-execution-shell/{execution_shell_id}/attempt-session/build`
- `GET /api/simulado-execution-shell/{execution_shell_id}/attempt-session`
- `GET /api/simulado-attempt-session/{attempt_session_id}`

Regras importantes:

- esta etapa cria apenas prepared non-submittable attempt session artifacts
- answer submissions nao sao aceitas
- correction e scoring permanecem desabilitados
- progress mutation permanece desabilitada
- nao cria correction results nem scores
- nao expoe final question content, final answer key content ou final explanation content
- a etapa usa apenas `SimuladoExecutionShell` ja persistido e nao chama LLM, RAG, vector DB, embeddings ou servicos externos

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
- ele nao dispara OCR, nao gera questoes e nao executa simulados
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

- OCR existe apenas como foundation opcional e limitada; desabilitado por padrao e dependente de engine externa
- sem pipeline robusto de OCR para livros escaneados, layout parsing, tabelas ou correcao semantica
- sem extracao robusta de PDF com layout parsing forte
- sem extracao final/validada de edital
- sem alinhamento bibliografico final/validado do edital
- sem grafo curricular final/aprovado a partir do edital; o graph atual continua candidate-based e review-friendly
- sem ativacao automatica do ciclo de estudos derivado do edital no runtime pedagogico
- sem vetores, embeddings ou RAG
- question generation blueprint existe apenas como fundacao de planejamento
- question draft generation existe apenas como artifact provisiorio e review-required; sem geracao final de questoes
- answer key / explanation guardrails existem apenas como assessment/candidate layer, sem answer key final, explanation final, scoring ou correction
- simulado question assembly existe apenas como pacote de revisao nao executavel e nao scoreable
- simulado execution readiness / attempt shell existe apenas como artifact de readiness nao executavel, sem attempts, submissions, correction ou scoring
- finalization / approval guardrails existem apenas como assessment layer para readiness futura, sem aprovacao real, finalizacao real, execucao, correction ou scoring
- final approval artifact existe apenas como registro explicito de decisao humana, ainda sem execucao, correction, scoring, submissions ou mutacao de progresso
- simulado execution shell existe apenas como artifact operacional nao ativo, sem attempts, submissions, correction, scoring ou exposicao de conteudo final
- simulado attempt session existe apenas como container preparado e nao submetivel, sem answer submissions, correction, scoring ou mutacao de progresso
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
- fixtures de estabilizacao para question generation blueprint
- fixtures de estabilizacao para question draft generation
- fixtures de estabilizacao para answer key / explanation guardrails
- fixtures de estabilizacao para simulado question assembly
- fixtures de estabilizacao para simulado execution readiness / attempt shell
- fixtures de estabilizacao para finalization / approval guardrails
- fixtures de estabilizacao para final approval artifact
- fundacao de simulado execution shell
- fixtures de estabilizacao para simulado execution shell
- fundacao de simulado attempt session
- fixtures de estabilizacao para simulado attempt session
- fundacao de answer submission
- correction readiness / correction shell foundation
- execucao e correcao futura de simulados, somente apos camadas futuras de approval artifact e execution shell
- geracao futura de questoes a partir de materiais, edital, perfil de banca e blueprint
- geracao futura de alternativas, distratores, respostas, explicacoes e gabarito
- refinamento do dashboard de progresso, continuacao e retencao
- resumao pre-prova baseado no material ja estudado
- scheduler avancado de revisao
