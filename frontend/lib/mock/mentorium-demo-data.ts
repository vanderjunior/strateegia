import type { CapabilityCard, CapabilityStatus, StudyOverviewCard } from "@/lib/api/types";

export const landingPipeline = [
  "Upload de materiais",
  "Leitura e segmentacao documental",
  "Ingestao de edital",
  "Alinhamento bibliografico e gaps",
  "Ciclo de estudo flexivel",
  "Questoes e simulados por perfil",
  "Tentativa, correcao e score auditaveis"
] as const;

export const landingFeatures = [
  {
    title: "PDFs textuais e materiais",
    description:
      "Leitura de PDFs textuais, TXT e Markdown com pipeline user-scoped e registros deterministas.",
    badge: "suportado"
  },
  {
    title: "Editais e bibliografia",
    description:
      "Extracao candidata, alinhamento bibliografico e mapeamento de gaps com revisao humana.",
    badge: "em validacao"
  },
  {
    title: "Perfil PSCPP/Praticagem",
    description:
      "Questoes e simulados orientados por estilo tecnico-operacional maritimo, com ancora bibliografica.",
    badge: "implementado"
  },
  {
    title: "Ciclo de estudos flexivel",
    description:
      "Perfil PSCPP com distribuicao semanal proporcional, rotacao de 12 sessoes e override do usuario.",
    badge: "guia editavel"
  },
  {
    title: "Runtime auditavel de simulado",
    description:
      "Tentativa, correcao, resultado e registros seguros dentro de limites controlados.",
    badge: "testado"
  },
  {
    title: "OCR experimental",
    description:
      "Fallback opcional com Tesseract para PDFs escaneados, sujeito a validacao manual em documentos reais.",
    badge: "experimental"
  }
] as const;

export const howItWorksSteps = [
  {
    id: "01",
    title: "Estruture o terreno",
    body:
      "Suba materiais, processe PDFs textuais e consolide o edital como base candidata para revisao tecnica."
  },
  {
    id: "02",
    title: "Mapeie cobertura e prioridades",
    body:
      "Cruze bibliografia, cobertura, gaps, ciclo de estudo e perfil PSCPP para orientar o treinamento."
  },
  {
    id: "03",
    title: "Treine com trilha auditavel",
    body:
      "Use questoes, simulados e a cadeia de tentativa/correcao/score com estados claros e sem overclaim operacional."
  }
] as const;

export const dashboardSidebar = [
  "Dashboard",
  "Materiais",
  "Editais",
  "Ciclo",
  "Questoes",
  "Simulados",
  "PSCPP",
  "Runtime"
] as const;

export const studyOverviewCards: StudyOverviewCard[] = [
  {
    id: "study-overview-dominant-block",
    internalKey: "pscpp_study_cycle_profile",
    title: "Bloco dominante",
    value: "Manobrabilidade e rebocadores",
    note: "prioridade 1 no guia PSCPP",
    metric: 78
  },
  {
    id: "study-overview-current-rotation",
    internalKey: "pscpp_study_cycle_profile",
    title: "Rotacao atual",
    value: "Sessao 7 de 12",
    note: "atracacao, desatracacao e fundeio",
    metric: 58
  },
  {
    id: "study-overview-weekly-training",
    internalKey: "question_generation_blueprint",
    title: "Treino da semana",
    value: "40 questoes por topico",
    note: "fase de consolidacao por cenarios",
    metric: 66
  }
] as const;

export const documentStatusCards: CapabilityCard[] = [
  {
    internalKey: "pdf_text_extraction",
    title: "PDF textual",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Suportado hoje com extracao, chunking e sectioning deterministas.",
    detail: "TXT, Markdown e PDFs textuais entram no pipeline atual."
  },
  {
    internalKey: "ocr_adapter",
    title: "PDF escaneado / OCR",
    status: "implemented_but_needs_manual_validation" as CapabilityStatus,
    summary: "Fallback opcional com Tesseract, desabilitado por padrao.",
    detail: "Nao tratar como producao pronta sem validacao de campo."
  },
  {
    internalKey: "edital_ingestion",
    title: "Ingestao de edital",
    status: "partially_implemented" as CapabilityStatus,
    summary: "Extracao heuristica de secoes, topicos e bibliografia.",
    detail: "Artefato candidato e review-friendly."
  },
  {
    internalKey: "bibliography_alignment",
    title: "Alinhamento bibliografico",
    status: "partially_implemented" as CapabilityStatus,
    summary: "Coverage, gaps e redundancias com evidencias bounded.",
    detail: "Ainda nao e um mapeamento final verificado."
  }
] as const;

export const runtimeStatusCards: CapabilityCard[] = [
  {
    internalKey: "attempt_session",
    title: "Tentativa / correcao / score",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Cadeia auditavel e bem testada.",
    detail: "A etapa de entrega executavel ainda nao esta aberta."
  },
  {
    internalKey: "minimal_progress_ledger_apply",
    title: "Minimal progress ledger",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Aplica apenas ledger minimo com idempotencia e rollback metadata.",
    detail: "Sem mutar ranking, retention, scheduler ou study cycle."
  },
  {
    internalKey: "applied_event_ledger",
    title: "Applied event ledger",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Replay-safe e deduplicado para eventos aplicados.",
    detail: "Camada auditavel para downstream review."
  },
  {
    internalKey: "propagation_guardrail",
    title: "Propagation guardrail",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Readiness-only para superficies futuras.",
    detail: "Nao propaga ranking, retention, scheduler, ciclo ou graph."
  },
  {
    internalKey: "controlled_propagation_apply",
    title: "Controlled propagation ledger",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Registra entradas isoladas de propagacao controlada.",
    detail: "Ledger-only, sem apply direto em runtime."
  },
  {
    internalKey: "simulado_assembly",
    title: "Geracao automatica completa de simulado",
    status: "foundation_only" as CapabilityStatus,
    summary: "Blueprint, drafts e assembly existem, mas a prova final executavel nao esta verificada.",
    detail: "Evitar prometer simulado perfeito a partir de qualquer PDF."
  }
] as const;

export const pscppProfileCards: CapabilityCard[] = [
  {
    internalKey: "pscpp_question_style_profile",
    title: "Question style profile",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Perfil PSCPP/Praticagem com ancora bibliografica, formato A-E e arquetipos tecnicos.",
    detail: "Base testada para orientar blueprint e draft metadata com regras de seguranca."
  },
  {
    internalKey: "question_generation_blueprint",
    title: "Question generation integration",
    status: "metadata_only" as CapabilityStatus,
    summary: "Integracao de metadata e validacao para simulado, fixation, review e summary.",
    detail: "Source-grounding, arquetipos e human review seguem sem gerar respostas finais sensiveis."
  },
  {
    internalKey: "pscpp_study_cycle_profile",
    title: "Study cycle guide",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Rotacao de 12 sessoes, fases de estudo e guidance proporcional para PSCPP.",
    detail: "Guidance-only, sem agenda forcada e com override do usuario."
  }
] as const;

export const betaSignals = [
  "beta fechado",
  "acesso antecipado",
  "uso experimental",
  "convite",
  "ambiente em validacao"
] as const;
