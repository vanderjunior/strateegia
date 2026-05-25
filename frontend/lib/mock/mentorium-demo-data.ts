import type {
  CapabilityCard,
  CapabilityStatus,
  CoverageItem,
  EditalDetail,
  EditalListItem,
  GapItem,
  MaterialDetail,
  MaterialListItem,
  PipelineDetailViewModel,
  StudyOverviewCard
} from "@/lib/api/types";

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

export const materialsWorkspaceItems: MaterialListItem[] = [
  {
    id: "material-arte-naval",
    title: "PSCPP bibliografia - Arte Naval.pdf",
    typeLabel: "PDF textual",
    processingStatus: "Processado",
    extractionStatus: "Texto extraído",
    sectionsCount: 18,
    chunksCount: 124,
    reviewState: "Pronto para revisão",
    source: "mock",
    relatedGaps: 1
  },
  {
    id: "material-shiphandling-manobra",
    title: "Shiphandling for the Mariner - capítulo manobra.pdf",
    typeLabel: "PDF textual",
    processingStatus: "Processado",
    extractionStatus: "Texto extraído",
    sectionsCount: 9,
    chunksCount: 76,
    reviewState: "Pronto para revisão",
    source: "mock",
    relatedGaps: 2
  },
  {
    id: "material-roteiro-porto",
    title: "Roteiro escaneado - trecho porto.pdf",
    typeLabel: "PDF digitalizado",
    processingStatus: "OCR necessário",
    extractionStatus: "OCR em validação",
    sectionsCount: null,
    chunksCount: null,
    reviewState: "OCR em validação",
    source: "mock",
    relatedGaps: 1
  }
] as const;

export const materialDetailsById: Record<string, MaterialDetail> = {
  "material-arte-naval": {
    ...materialsWorkspaceItems[0],
    warnings: ["Texto extraído sujeito a revisão."],
    sectionPreviews: [
      { id: "arte-1", title: "Nomenclatura e geometria naval", level: 1, chunkRangeLabel: "Trechos 1 a 8" },
      { id: "arte-2", title: "Estabilidade inicial", level: 1, chunkRangeLabel: "Trechos 9 a 18" },
      { id: "arte-3", title: "Cabos, fundeio e governo", level: 1, chunkRangeLabel: "Trechos 19 a 31" }
    ],
    sourceNote: "Material processado em modo de demonstração, pronto para revisão assistida."
  },
  "material-shiphandling-manobra": {
    ...materialsWorkspaceItems[1],
    warnings: ["Texto extraído sujeito a revisão."],
    sectionPreviews: [
      { id: "ship-1", title: "Turning circle e stopping distance", level: 1, chunkRangeLabel: "Trechos 1 a 10" },
      { id: "ship-2", title: "Berthing com vento de través", level: 1, chunkRangeLabel: "Trechos 11 a 22" },
      { id: "ship-3", title: "Interação em canal restrito", level: 1, chunkRangeLabel: "Trechos 23 a 36" }
    ],
    sourceNote: "Capítulo tratado como base técnica para revisão de manobra e cenários."
  },
  "material-roteiro-porto": {
    ...materialsWorkspaceItems[2],
    warnings: [
      "Este arquivo pode precisar de OCR antes da revisão.",
      "OCR em validação."
    ],
    sectionPreviews: [],
    sourceNote: "Arquivo digitalizado mantido em etapa de revisão até existir leitura confiável."
  }
};

export const editalCoverageItems: CoverageItem[] = [
  {
    id: "coverage-arte-naval",
    title: "Arte Naval",
    coverageLabel: "Cobertura boa",
    detail: "Referências compatíveis já aparecem nos materiais processados.",
    source: "mock"
  },
  {
    id: "coverage-shiphandling",
    title: "Shiphandling",
    coverageLabel: "Cobertura parcial",
    detail: "Há material útil, mas ainda sujeito a revisão por cenário.",
    source: "mock"
  },
  {
    id: "coverage-colreg",
    title: "COLREG",
    coverageLabel: "Cobertura parcial",
    detail: "Boa base normativa, mas ainda com lacunas em aplicação operacional.",
    source: "mock"
  },
  {
    id: "coverage-normam",
    title: "NORMAM",
    coverageLabel: "Gap encontrado",
    detail: "Faltam materiais consolidados para revisão segura.",
    source: "mock"
  },
  {
    id: "coverage-nav-restrita",
    title: "Navegação restrita",
    coverageLabel: "Precisa de material",
    detail: "Cobertura ainda insuficiente para revisão com confiança.",
    source: "mock"
  }
] as const;

export const editalGapItems: GapItem[] = [
  {
    id: "gap-normam",
    title: "NORMAM",
    detail: "Gap encontrado em referências normativas atualizadas.",
    severityLabel: "Revisão necessária",
    source: "mock"
  },
  {
    id: "gap-nav-restrita",
    title: "Navegação restrita",
    detail: "Precisa de material complementar para cobertura mais segura.",
    severityLabel: "Precisa de material",
    source: "mock"
  }
] as const;

export const editaisWorkspaceItems: EditalListItem[] = [
  {
    id: "edital-pscpp-referencia",
    title: "PSCPP/Praticagem - edital de referência",
    statusLabel: "Análise candidata",
    topicsCount: 24,
    bibliographyItemsCount: 11,
    gapsCount: 4,
    reviewState: "Precisa de conferência",
    source: "mock"
  }
] as const;

export const editalDetailsById: Record<string, EditalDetail> = {
  "edital-pscpp-referencia": {
    ...editaisWorkspaceItems[0],
    topicCandidates: [
      "Manobrabilidade e rebocadores",
      "COLREG e sinais sonoros",
      "Navegação restrita",
      "Arte Naval",
      "NORMAM e legislação marítima",
      "Meteorologia e oceanografia"
    ],
    bibliographyCandidates: [
      "Arte Naval",
      "Shiphandling for the Mariner",
      "COLREG",
      "NORMAM aplicáveis",
      "Radar and ARPA Manual"
    ],
    coverageItems: editalCoverageItems,
    gapItems: editalGapItems,
    warnings: [
      "Os tópicos exibidos são candidatos e ainda precisam de conferência.",
      "A bibliografia identificada é preliminar e sujeita a revisão."
    ],
    notes: [
      "Alinhamento preliminar baseado em leitura heurística do edital.",
      "Não trate esta análise como verdade final sem revisão humana."
    ]
  }
};

export const pipelineDetailsById: Record<string, PipelineDetailViewModel> = {
  "material-arte-naval": {
    connection: {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "Linha do tempo local usada até existir leitura segura do backend para este material."
    },
    documentId: "material-arte-naval",
    title: "PSCPP bibliografia - Arte Naval.pdf",
    source: "mock",
    extractionStatus: "Texto extraído",
    reviewState: "Pronto para revisão",
    sectionsCount: 18,
    chunksCount: 124,
    notes: ["Texto extraído sujeito a revisão antes de uso em fluxos posteriores."],
    steps: [
      { id: "uploaded", label: "Enviado", statusLabel: "Concluído", tone: "complete", detail: "Material já está registrado." },
      { id: "extracted", label: "Texto extraído", statusLabel: "Concluído", tone: "complete", detail: "Leitura textual disponível." },
      { id: "chunked", label: "Segmentado", statusLabel: "Concluído", tone: "complete", detail: "Trechos preparados para revisão." },
      { id: "review", label: "Pronto para revisão", statusLabel: "Concluído", tone: "current", detail: "Material pronto para etapa de revisão." }
    ]
  },
  "material-roteiro-porto": {
    connection: {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "Linha do tempo local usada até existir leitura segura do backend para este material."
    },
    documentId: "material-roteiro-porto",
    title: "Roteiro escaneado - trecho porto.pdf",
    source: "mock",
    extractionStatus: "OCR em validação",
    reviewState: "OCR necessário",
    sectionsCount: null,
    chunksCount: null,
    notes: ["Este arquivo pode precisar de OCR antes da revisão."],
    steps: [
      { id: "uploaded", label: "Enviado", statusLabel: "Concluído", tone: "complete", detail: "Material já está registrado." },
      { id: "extracted", label: "Texto extraído", statusLabel: "OCR necessário", tone: "warning", detail: "A leitura textual ainda não está pronta." },
      { id: "chunked", label: "Segmentado", statusLabel: "Pendente", tone: "pending", detail: "A segmentação depende de validação do OCR." },
      { id: "review", label: "Pronto para revisão", statusLabel: "Em validação", tone: "warning", detail: "Arquivo mantido em revisão controlada." }
    ]
  }
};

export const betaSignals = [
  "beta fechado",
  "acesso antecipado",
  "uso experimental",
  "convite",
  "ambiente em validacao"
] as const;
