# Arquitetura do MVP

## Objetivo

Construir uma base escalavel para estudo ativo a partir de PDFs, mantendo o MVP enxuto e preparado para evolucao.

## Modulos

### 1. Ingestao de PDFs

- Recebe arquivo PDF
- Valida extensao e conteudo basico
- Extrai texto via adaptador

### 2. Parsing e estruturacao

- Detecta secoes por heuristicas de cabecalho
- Quando nao houver cabecalhos, divide por blocos coerentes
- Produz topicos com paginas de origem e pontuacao de relevancia

### 3. Processamento pedagogico

- Gera resumo estruturado
- Destaca pontos-chave, excecoes e pegadinhas
- Gera questoes com explicacao
- Prepara dados para revisao diaria e revisao por bloco

### 4. Aprendizado baseado em erro

- Registra respostas
- Classifica erro
- Atualiza `erros_frequentes` e `pontos_fracos`
- Reprioriza revisoes

### 5. Persistencia

- Repositorio JSON simples no MVP
- Contratos preparados para trocar por PostgreSQL depois

### 6. API backend

- Endpoints REST para upload, consulta, revisao e resposta de questoes
- Separacao entre rotas, servicos e repositorios

### 7. Interface web

- Layout em 3 colunas
- Esquerda: indice navegavel dos PDFs
- Centro: resumo, questoes e revisao
- Direita: fonte original

## Fluxo de processamento

1. Upload do PDF
2. Extracao de texto
3. Estruturacao em topicos
4. Geracao de resumo e questoes
5. Persistencia do documento processado
6. Atualizacao das revisoes diarias e por bloco
7. Registro de respostas e erros

## Modelagem de dados do MVP

### Document

- `id`
- `title`
- `exam_context`
- `board`
- `source_filename`
- `source_excerpt`
- `topics`
- `summary`
- `questions`
- `created_at`

### Topic

- `id`
- `title`
- `content`
- `key_points`
- `trap_points`
- `relevance_score`
- `source_pages`

### Question

- `id`
- `document_id`
- `topic_id`
- `style`
- `stem`
- `options`
- `correct_answer`
- `explanation`

### ErrorLog

- `question_id`
- `document_id`
- `topic_id`
- `error_type`
- `selected_answer`
- `created_at`

### ProgressState

- `documents_completed`
- `errors`
- `weak_topics`
- `topic_performance`

## Regras do MVP implementadas

- Resumo por topico
- Questoes com explicacao
- Revisao diaria curta com 3 a 5 questoes
- Revisao por bloco a cada 3 PDFs
- Revisao cumulativa com prioridade maior para itens recentes
- Persistencia simples de progresso e erros

## Fora do MVP, mas previsto

- Integracao com APIs de bancos de questoes
- Login e multiusuario
- Filtros por banca, cargo e area
- Adaptacao avancada por banca com calibracao estatistica
- Agendamento inteligente mais sofisticado
