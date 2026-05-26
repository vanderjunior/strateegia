import type {
  CapabilityCard,
  CapabilityStatus,
  CoverageItem,
  EditalDetail,
  EditalListItem,
  GapItem,
  MaterialDetail,
  MaterialListItem,
  OnboardingStepItem,
  OnboardingViewModel,
  PipelineDetailViewModel,
  PscppCrosswalkBlockItem,
  PscppCrosswalkGapItem,
  PscppCrosswalkRelationshipItem,
  PscppCrosswalkSessionRef,
  PscppCrosswalkViewModel,
  PscppCycleViewModel,
  PscppNotebookItem,
  PscppPhaseItem,
  PscppPriorityBlock,
  PscppQuestionGuidanceItem,
  PscppQuestionsViewModel,
  PscppRotationSession,
  PscppWorkspaceViewModel,
  StudyOverviewCard,
  StudySessionDetail,
  StudySessionRelatedGap,
  StudySessionWorkspaceViewModel
} from "@/lib/api/types";

export const landingPipeline = [
  "Envio de material",
  "Leitura e segmentação documental",
  "Revisão de edital",
  "Mapa de preparação e gaps",
  "Ciclo de estudo flexível",
  "Questões candidatas em revisão",
  "Simulado em preparação"
] as const;

export const landingFeatures = [
  {
    title: "PDFs textuais e materiais",
    description:
      "Leitura de PDFs textuais, TXT e Markdown para validação inicial e revisão controlada.",
    badge: "upload controlado"
  },
  {
    title: "Editais e bibliografia",
    description:
      "Análise candidata, bibliografia identificada e gaps encontrados com revisão humana.",
    badge: "análise candidata"
  },
  {
    title: "Perfil PSCPP/Praticagem",
    description:
      "Mapa de preparação, prioridades e estudo guiado orientados pelo caminho técnico-operacional marítimo.",
    badge: "mapa de preparação"
  },
  {
    title: "Estudo de hoje",
    description:
      "Sessão sugerida, materiais relacionados e checklist de estudo sem agenda automática.",
    badge: "guia flexível"
  },
  {
    title: "Simulado em preparação",
    description:
      "Questões candidatas e montagem ainda exigem revisão antes de qualquer uso final.",
    badge: "revisão necessária"
  },
  {
    title: "OCR em validação",
    description:
      "PDFs escaneados podem exigir OCR e conferência manual antes de uma revisão segura.",
    badge: "uso experimental"
  }
] as const;

export const howItWorksSteps = [
  {
    id: "01",
    title: "Comece sua preparação",
    body:
      "Envie material, revise o edital e confirme o que já pode ser lido com segurança."
  },
  {
    id: "02",
    title: "Entenda o mapa PSCPP",
    body:
      "Cruze bibliografia, cobertura, gaps e blocos prioritários antes de decidir o foco."
  },
  {
    id: "03",
    title: "Siga o estudo de hoje",
    body:
      "Use a sessão sugerida como guia flexível, com checklist, materiais relacionados e revisão necessária."
  }
] as const;

export const dashboardSidebar = [
  "Dashboard",
  "Começar",
  "Materiais",
  "Editais",
  "Ciclo",
  "Questoes",
  "Simulados",
  "PSCPP",
  "Execução"
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
    title: "Sessão de treino em revisão",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Estrutura auditável de tentativa e revisão já existe.",
    detail: "A etapa de entrega executável ainda não está aberta para uso final."
  },
  {
    internalKey: "minimal_progress_ledger_apply",
    title: "Registro mínimo de progresso",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Mantido apenas como base técnica interna, sem uso visível para o candidato.",
    detail: "Sem alterar ranking, retenção, agenda ou ciclo de estudo."
  },
  {
    internalKey: "applied_event_ledger",
    title: "Registro auditável de aplicação",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Camada interna mantida para revisão auditável.",
    detail: "Não representa uma ação aberta na interface do candidato."
  },
  {
    internalKey: "propagation_guardrail",
    title: "Proteção de atualização ampla",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Proteção interna para superfícies futuras.",
    detail: "Não libera ranking, retenção, agenda ou ciclo automaticamente."
  },
  {
    internalKey: "controlled_propagation_apply",
    title: "Registro controlado de atualização",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Registro interno de atualizações isoladas.",
    detail: "Mantido sem aplicação direta na experiência atual."
  },
  {
    internalKey: "simulado_assembly",
    title: "Geracao automatica completa de simulado",
    status: "foundation_only" as CapabilityStatus,
    summary: "A montagem existe como base, mas a prova final ainda não está verificada.",
    detail: "Evitar prometer simulado completo a partir de qualquer material."
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

export const pscppEvidence = ["PSCPP/2011", "PSCPP/2012 Prova Rosa"] as const;

export const pscppEvidenceNotes = [
  "Referência de estratégia e estilo.",
  "Não substitui o escopo do edital atual.",
  "Exige alinhamento com edital e bibliografia em uso."
] as const;

export const pscppPriorityBlocks: PscppPriorityBlock[] = [
  {
    id: "priority-manoeuvrability",
    title: "Manobrabilidade, águas rasas, canal, interação, squat, rebocadores e atracação",
    detail: "Bloco dominante para cenários operacionais, controle de navio e tomada de decisão."
  },
  {
    id: "priority-colreg",
    title: "COLREG, luzes, marcas, sinais sonoros e canais estreitos",
    detail: "Leitura normativa aplicada, comandos negativos e sequências de afirmativas."
  },
  {
    id: "priority-navigation",
    title: "Navegação em águas restritas, radar, ECDIS, marés, agulhas e passage planning",
    detail: "Base para navegação técnica, instrumentos e tomada de rumo sob restrição."
  },
  {
    id: "priority-arte-naval",
    title: "Arte Naval: nomenclatura, geometria, estabilidade, cabos, fundeio e aparelho de governo",
    detail: "Vocabulário técnico e fundamentos estruturais que a banca costuma tensionar."
  },
  {
    id: "priority-general",
    title: "Legislação, meteorologia/oceanografia, comunicações e conhecimentos gerais",
    detail: "Fechamento de lacunas normativas e apoio a cenários curtos de prova."
  }
];

export const pscppPhasePlan: PscppPhaseItem[] = [
  {
    id: "phase-base",
    title: "Base técnica e vocabulário",
    detail: "Consolidar terminologia marítima, regras fatais e conceitos que a banca troca."
  },
  {
    id: "phase-scenarios",
    title: "Consolidação por cenários",
    detail: "Cruzar fontes, cenários operacionais e afirmativas em sequência."
  },
  {
    id: "phase-advanced",
    title: "Aprofundamento e produção de questões inéditas",
    detail: "Usar bibliografia visível e revisão humana para lapidar questões candidatas."
  },
  {
    id: "phase-post-edital",
    title: "Pós-edital e ajuste fino",
    detail: "Repriorizar blocos com base no edital atual, gaps e erros recorrentes."
  }
];

export const pscppRotation: PscppRotationSession[] = [
  { id: "rotation-1", index: 1, title: "Manobrabilidade", detail: "Forças, resistência, propulsão" },
  { id: "rotation-2", index: 2, title: "COLREG", detail: "Regras de governo e navegação" },
  { id: "rotation-3", index: 3, title: "Arte Naval", detail: "Nomenclatura, geometria, estabilidade" },
  { id: "rotation-4", index: 4, title: "Navegação", detail: "Rumos, marcações, agulhas, LDP" },
  { id: "rotation-5", index: 5, title: "Manobrabilidade", detail: "Leme, curva de giro, zigue-zague, stopping" },
  { id: "rotation-6", index: 6, title: "Legislação", detail: "NORMAM, LESTA/RLESTA, praticagem" },
  { id: "rotation-7", index: 7, title: "Shiphandling", detail: "Atracação, desatracação, fundeio" },
  { id: "rotation-8", index: 8, title: "COLREG", detail: "Luzes, marcas, sinais sonoros" },
  { id: "rotation-9", index: 9, title: "Navegação restrita", detail: "Radar, ECDIS, AIS, passage planning" },
  { id: "rotation-10", index: 10, title: "Rebocadores", detail: "Interação, bollard pull, escort" },
  { id: "rotation-11", index: 11, title: "Meteorologia", detail: "Oceanografia, marés, METAREA" },
  { id: "rotation-12", index: 12, title: "Simulado curto + revisão", detail: "Erros recorrentes e ajuste fino" }
];

export const pscppSessionStructure = [
  "20 min revisão ativa",
  "60 a 90 min teoria dirigida",
  "40 min questões ou criação de questões",
  "20 min caderno de erros/flashcards"
] as const;

export const pscppNotebookSystem: PscppNotebookItem[] = [
  {
    id: "notebook-concepts",
    title: "Conceitos que a banca troca",
    detail: "Definições próximas, pegadinhas normativas e vocabulário técnico."
  },
  {
    id: "notebook-rules",
    title: "Números e regras fatais",
    detail: "Regras de governo, sinais, parâmetros e referências que exigem memória limpa."
  },
  {
    id: "notebook-scenarios",
    title: "Caderno de cenários",
    detail: "Situações operacionais curtas para treino de julgamento técnico."
  }
];

export const pscppQuestionArchetypes: PscppQuestionGuidanceItem[] = [
  { id: "arch-i-v", title: "Afirmativas I-V", detail: "Sequências de validação técnica com leitura atenta de cada proposição." },
  { id: "arch-vf", title: "V/F em sequência", detail: "Combina regras, exceções e contexto operacional." },
  { id: "arch-incorrect", title: "Assinale a incorreta", detail: "Exige comando negativo claro e distractores plausíveis." },
  { id: "arch-calc", title: "Cálculo aplicado", detail: "Cuidado com unidades, sinais e contexto náutico." },
  { id: "arch-scenario", title: "Cenário operacional", detail: "Traz praticagem, manobra e navegação restrita para a decisão." },
  { id: "arch-gap", title: "Lacuna técnica", detail: "Pede termo, referência ou regra exata a partir da fonte." }
];

export const pscppQuestionSourceRules: PscppQuestionGuidanceItem[] = [
  { id: "rule-source", title: "Fonte obrigatória", detail: "Cada questão candidata precisa nascer de uma fonte ou edital claramente identificado." },
  { id: "rule-bibliography", title: "Bibliografia visível", detail: "A âncora bibliográfica deve ficar explícita para revisão posterior." },
  { id: "rule-scenario", title: "Cenário operacional", detail: "Priorizar situações técnicas compatíveis com a banca e a praticagem." },
  { id: "rule-distractors", title: "Distratores tecnicamente plausíveis", detail: "Alternativas erradas devem parecer críveis sem distorcer a fonte." }
];

export const pscppQuestionReviewRules: PscppQuestionGuidanceItem[] = [
  { id: "review-human", title: "Revisão humana da resposta final", detail: "Não fechar resposta final sem revisão humana e confronto com a fonte." },
  { id: "review-negative", title: "Cuidado com comando negativo", detail: "Destacar instruções como incorreta, exceto ou falsa para evitar ruído." },
  { id: "review-weights", title: "Pesos variados como guia", detail: "Usar dificuldade e peso apenas como orientação, não como nota definitiva." },
  { id: "review-status", title: "Questões candidatas", detail: "Tratar a saída como revisão necessária e ainda não finalizada." }
];

export const pscppWorkspaceViewModelMock: PscppWorkspaceViewModel = {
  connection: {
    state: "mock",
    source: "mock",
    title: "Dados de demonstração",
    detail: "Perfil PSCPP, ciclo e orientação de questões exibidos por fallback auditado enquanto a leitura do perfil no backend não é confirmada."
  },
  summary: [
    {
      id: "pscpp-summary-profile",
      label: "Perfil PSCPP configurado",
      value: "Perfil configurado",
      detail: "Base técnico-operacional marítima com âncora bibliográfica."
    },
    {
      id: "pscpp-summary-cycle",
      label: "Ciclo sugerido",
      value: "12 sessões",
      detail: "Rotação flexível, ajustável pelo candidato."
    },
    {
      id: "pscpp-summary-questions",
      label: "Questões candidatas",
      value: "Fonte obrigatória",
      detail: "Orientação por fonte, bibliografia e revisão humana."
    },
    {
      id: "pscpp-summary-simulado",
      label: "Simulado",
      value: "Em preparação",
      detail: "Ainda não executável de ponta a ponta."
    }
  ],
  profileTitle: "PSCPP / Praticagem",
  profileDescription:
    "Prova técnico-operacional marítima com forte dependência de bibliografia, COLREG, NORMAM, navegação, meteorologia e manobra.",
  statusLabel: "Perfil configurado",
  modeLabel: "Guia flexível",
  examProfileId: "exam-profile:marinha-pscpp",
  questionStyleProfileId: "marinha_dpc_pscpp_praticagem",
  studyCycleProfileId: "marinha_dpc_pscpp_praticagem_study_cycle",
  evidence: [...pscppEvidence],
  evidenceNotes: [...pscppEvidenceNotes],
  priorityBlocks: pscppPriorityBlocks
};

export const pscppCycleViewModelMock: PscppCycleViewModel = {
  connection: {
    state: "mock",
    source: "mock",
    title: "Dados de demonstração",
    detail: "O ciclo PSCPP é guidance-only: não cria agenda automaticamente e não altera progresso."
  },
  summary: [
    {
      id: "pscpp-cycle-guidance",
      label: "Modo de uso",
      value: "Guia flexível",
      detail: "Ajustável pelo candidato e sem agenda fixa."
    },
    {
      id: "pscpp-cycle-baseline",
      label: "Base semanal",
      value: "24h",
      detail: "Distribuição de referência, nunca obrigatória."
    },
    {
      id: "pscpp-cycle-rotation",
      label: "Rotação",
      value: "12 sessões",
      detail: "Revezamento entre manobra, COLREG, navegação e revisão."
    },
    {
      id: "pscpp-cycle-override",
      label: "Override",
      value: "Permitido",
      detail: "Não altera seu progresso nem cria agenda automaticamente."
    }
  ],
  modeLabel: "Sugestão flexível",
  weeklyGuidance: "Distribuição semanal base de 24 horas, usada apenas como orientação.",
  overrideLabel: "Ajustável pelo candidato",
  baselineLabel: "Não cria agenda automaticamente",
  sessionStructure: [...pscppSessionStructure],
  phasePlan: pscppPhasePlan,
  notebookSystem: pscppNotebookSystem,
  rotation: pscppRotation
};

export const pscppQuestionsViewModelMock: PscppQuestionsViewModel = {
  connection: {
    state: "mock",
    source: "mock",
    title: "Dados de demonstração",
    detail: "Regras de estilo e revisão exibidas por fallback auditado; não há geração automática final nesta tela."
  },
  summary: [
    {
      id: "pscpp-questions-source",
      label: "Fonte obrigatória",
      value: "Bibliografia visível",
      detail: "Questões candidatas precisam de âncora clara em fonte ou edital."
    },
    {
      id: "pscpp-questions-review",
      label: "Revisão",
      value: "Necessária",
      detail: "Não tratar questão candidata como finalizada."
    },
    {
      id: "pscpp-questions-simulado",
      label: "Simulado",
      value: "Ainda em preparação",
      detail: "Integração existe como guia, mas a execução final ainda requer revisão."
    },
    {
      id: "pscpp-questions-weights",
      label: "Pesos",
      value: "Orientativos",
      detail: "Usar variação de peso e dificuldade apenas como guia."
    }
  ],
  archetypes: pscppQuestionArchetypes,
  sourceRules: pscppQuestionSourceRules,
  reviewRules: pscppQuestionReviewRules,
  relationToSimulado: [
    "Questões candidatas",
    "Revisão necessária",
    "Ainda não finalizadas"
  ]
};

const pscppCrosswalkSessionRefs: Record<string, PscppCrosswalkSessionRef> = {
  "1": { id: "rotation-1", index: 1, label: "Sessão 1", detail: "Manobrabilidade: forças, resistência, propulsão" },
  "2": { id: "rotation-2", index: 2, label: "Sessão 2", detail: "COLREG: regras de governo e navegação" },
  "3": { id: "rotation-3", index: 3, label: "Sessão 3", detail: "Arte Naval: nomenclatura, geometria, estabilidade" },
  "4": { id: "rotation-4", index: 4, label: "Sessão 4", detail: "Navegação: rumos, marcações, agulhas, LDP" },
  "5": { id: "rotation-5", index: 5, label: "Sessão 5", detail: "Manobrabilidade: leme, curva de giro, zigue-zague, stopping" },
  "6": { id: "rotation-6", index: 6, label: "Sessão 6", detail: "Legislação: NORMAM, LESTA/RLESTA, praticagem" },
  "7": { id: "rotation-7", index: 7, label: "Sessão 7", detail: "Shiphandling: atracação, desatracação, fundeio" },
  "8": { id: "rotation-8", index: 8, label: "Sessão 8", detail: "COLREG: luzes, marcas, sinais sonoros" },
  "9": { id: "rotation-9", index: 9, label: "Sessão 9", detail: "Navegação restrita: radar, ECDIS, AIS, passage planning" },
  "10": { id: "rotation-10", index: 10, label: "Sessão 10", detail: "Rebocadores, interação, bollard pull, escort" },
  "11": { id: "rotation-11", index: 11, label: "Sessão 11", detail: "Meteorologia, oceanografia, marés, METAREA" },
  "12": { id: "rotation-12", index: 12, label: "Sessão 12", detail: "Simulado curto + revisão de erros" }
};

export const pscppCrosswalkBlocks: PscppCrosswalkBlockItem[] = [
  {
    id: "crosswalk-block-1",
    priorityNumber: 1,
    title: "Manobrabilidade, águas rasas, canal, interação, squat, rebocadores e atracação",
    coverageLabel: "Cobertura parcial",
    reviewState: "Alinhamento preliminar",
    materialsCount: 2,
    gapsCount: 1,
    suggestedSessions: [
      { ...pscppCrosswalkSessionRefs["1"], emphasis: "gap_focus" },
      { ...pscppCrosswalkSessionRefs["5"], emphasis: "gap_focus" },
      { ...pscppCrosswalkSessionRefs["10"], emphasis: "gap_focus" }
    ],
    relatedMaterials: [
      {
        id: "material-shiphandling-manobra",
        title: "Shiphandling for the Mariner - capítulo manobra.pdf",
        typeLabel: "PDF textual",
        statusLabel: "Pronto para revisão",
        linkHref: "/materials/material-shiphandling-manobra"
      },
      {
        id: "material-arte-naval",
        title: "PSCPP bibliografia - Arte Naval.pdf",
        typeLabel: "PDF textual",
        statusLabel: "Pronto para revisão",
        linkHref: "/materials/material-arte-naval"
      }
    ],
    relatedEditais: [
      {
        id: "edital-pscpp-referencia",
        title: "PSCPP/Praticagem - edital de referência",
        statusLabel: "Análise candidata",
        linkHref: "/editais/edital-pscpp-referencia"
      }
    ],
    gaps: ["Squat e interação em canal estreito precisam de reforço."],
    notes: ["Sugestão de reforço baseada em materiais já processados e leitura preliminar do edital."]
  },
  {
    id: "crosswalk-block-2",
    priorityNumber: 2,
    title: "COLREG, luzes, marcas, sinais sonoros e canais estreitos",
    coverageLabel: "Cobertura parcial",
    reviewState: "Precisa de conferência",
    materialsCount: 1,
    gapsCount: 1,
    suggestedSessions: [
      { ...pscppCrosswalkSessionRefs["2"], emphasis: "gap_focus" },
      { ...pscppCrosswalkSessionRefs["8"], emphasis: "gap_focus" }
    ],
    relatedMaterials: [
      {
        id: "material-arte-naval",
        title: "PSCPP bibliografia - Arte Naval.pdf",
        typeLabel: "PDF textual",
        statusLabel: "Processado",
        linkHref: "/materials/material-arte-naval"
      }
    ],
    relatedEditais: [
      {
        id: "edital-pscpp-referencia",
        title: "PSCPP/Praticagem - edital de referência",
        statusLabel: "Análise candidata",
        linkHref: "/editais/edital-pscpp-referencia"
      }
    ],
    gaps: ["Luzes e sinais em visibilidade restrita precisam de revisão."],
    notes: ["Comando negativo e exceções normativas pedem revisão humana adicional."]
  },
  {
    id: "crosswalk-block-3",
    priorityNumber: 3,
    title: "Navegação em águas restritas, radar, ECDIS, marés, agulhas e passage planning",
    coverageLabel: "Precisa de material",
    reviewState: "Gap identificado",
    materialsCount: 1,
    gapsCount: 1,
    suggestedSessions: [
      { ...pscppCrosswalkSessionRefs["4"], emphasis: "gap_focus" },
      { ...pscppCrosswalkSessionRefs["9"], emphasis: "gap_focus" },
      { ...pscppCrosswalkSessionRefs["11"], emphasis: "gap_focus" }
    ],
    relatedMaterials: [
      {
        id: "material-roteiro-porto",
        title: "Roteiro escaneado - trecho porto.pdf",
        typeLabel: "PDF digitalizado",
        statusLabel: "OCR em validação",
        linkHref: "/materials/material-roteiro-porto"
      }
    ],
    relatedEditais: [
      {
        id: "edital-pscpp-referencia",
        title: "PSCPP/Praticagem - edital de referência",
        statusLabel: "Precisa de conferência",
        linkHref: "/editais/edital-pscpp-referencia"
      }
    ],
    gaps: ["Radar, ECDIS e AIS precisam de material mais completo."],
    notes: ["O principal material relacionado ainda depende de validação de OCR."]
  },
  {
    id: "crosswalk-block-4",
    priorityNumber: 4,
    title: "Arte Naval: nomenclatura, geometria, estabilidade, cabos, fundeio e aparelho de governo",
    coverageLabel: "Cobertura boa",
    reviewState: "Pronto para revisão",
    materialsCount: 1,
    gapsCount: 1,
    suggestedSessions: [
      { ...pscppCrosswalkSessionRefs["3"] },
      { ...pscppCrosswalkSessionRefs["7"] }
    ],
    relatedMaterials: [
      {
        id: "material-arte-naval",
        title: "PSCPP bibliografia - Arte Naval.pdf",
        typeLabel: "PDF textual",
        statusLabel: "Pronto para revisão",
        linkHref: "/materials/material-arte-naval"
      }
    ],
    relatedEditais: [
      {
        id: "edital-pscpp-referencia",
        title: "PSCPP/Praticagem - edital de referência",
        statusLabel: "Análise candidata",
        linkHref: "/editais/edital-pscpp-referencia"
      }
    ],
    gaps: ["Revisar números e nomenclaturas confundíveis."],
    notes: ["Boa base atual, com foco em consolidação de termos e parâmetros."]
  },
  {
    id: "crosswalk-block-5",
    priorityNumber: 5,
    title: "Legislação, meteorologia/oceanografia, comunicações e conhecimentos gerais",
    coverageLabel: "Gap encontrado",
    reviewState: "Precisa de conferência",
    materialsCount: 0,
    gapsCount: 1,
    suggestedSessions: [
      { ...pscppCrosswalkSessionRefs["6"], emphasis: "gap_focus" },
      { ...pscppCrosswalkSessionRefs["11"], emphasis: "gap_focus" },
      { ...pscppCrosswalkSessionRefs["12"], emphasis: "gap_focus" }
    ],
    relatedMaterials: [],
    relatedEditais: [
      {
        id: "edital-pscpp-referencia",
        title: "PSCPP/Praticagem - edital de referência",
        statusLabel: "Precisa de conferência",
        linkHref: "/editais/edital-pscpp-referencia"
      }
    ],
    gaps: ["NORMAM, Tribunal Marítimo e GMDSS precisam de reforço."],
    notes: ["Alinhamento preliminar indica reforço normativo antes de ampliar revisão por cenário."]
  }
];

export const pscppCrosswalkGaps: PscppCrosswalkGapItem[] = [
  {
    id: "crosswalk-gap-1",
    title: "Squat e interação em canal estreito",
    affectedBlockTitle: pscppCrosswalkBlocks[0].title,
    whyItMatters: "Afeta leitura de cenário operacional e decisão de manobra em águas restritas.",
    suggestedAction: "Reforçar capítulos de shiphandling e revisar cenários de canal com rebocadores.",
    reviewState: "Sugestão de reforço",
    relatedSessions: pscppCrosswalkBlocks[0].suggestedSessions
  },
  {
    id: "crosswalk-gap-2",
    title: "Luzes e sinais em visibilidade restrita",
    affectedBlockTitle: pscppCrosswalkBlocks[1].title,
    whyItMatters: "A banca costuma explorar exceções e comandos negativos em COLREG.",
    suggestedAction: "Revisar sequências de luzes, marcas e sinais sonoros com conferência humana.",
    reviewState: "Precisa de conferência",
    relatedSessions: pscppCrosswalkBlocks[1].suggestedSessions
  },
  {
    id: "crosswalk-gap-3",
    title: "Radar, ECDIS e AIS",
    affectedBlockTitle: pscppCrosswalkBlocks[2].title,
    whyItMatters: "Sem material sólido, a revisão de navegação restrita fica incompleta.",
    suggestedAction: "Buscar material complementar e validar o roteiro escaneado antes da revisão final.",
    reviewState: "Gap identificado",
    relatedSessions: pscppCrosswalkBlocks[2].suggestedSessions
  },
  {
    id: "crosswalk-gap-4",
    title: "NORMAM, Tribunal Marítimo e GMDSS",
    affectedBlockTitle: pscppCrosswalkBlocks[4].title,
    whyItMatters: "Esses temas fecham lacunas normativas e sustentam questões de legislação e comunicações.",
    suggestedAction: "Cruzar o edital de referência com materiais complementares e revisar os tópicos normativos prioritários.",
    reviewState: "Alinhamento preliminar",
    relatedSessions: pscppCrosswalkBlocks[4].suggestedSessions
  }
];

export const pscppCrosswalkRelationships: PscppCrosswalkRelationshipItem[] = [
  {
    id: "crosswalk-rel-arte",
    material: pscppCrosswalkBlocks[3].relatedMaterials[0],
    edital: pscppCrosswalkBlocks[3].relatedEditais[0],
    blockTitle: pscppCrosswalkBlocks[3].title,
    contributionLabel: "Cobertura boa"
  },
  {
    id: "crosswalk-rel-shiphandling",
    material: pscppCrosswalkBlocks[0].relatedMaterials[0],
    edital: pscppCrosswalkBlocks[0].relatedEditais[0],
    blockTitle: pscppCrosswalkBlocks[0].title,
    contributionLabel: "Cobertura parcial"
  },
  {
    id: "crosswalk-rel-porto",
    material: pscppCrosswalkBlocks[2].relatedMaterials[0],
    edital: pscppCrosswalkBlocks[2].relatedEditais[0],
    blockTitle: pscppCrosswalkBlocks[2].title,
    contributionLabel: "Precisa de material"
  }
];

export const pscppCrosswalkViewModelMock: PscppCrosswalkViewModel = {
  connection: {
    state: "mock",
    source: "mock",
    title: "Dados de demonstração",
    detail: "Mapa PSCPP montado por fallback auditado a partir de materiais, edital, gaps e ciclo sugerido."
  },
  summary: [
    {
      id: "pscpp-map-summary-blocks",
      label: "Blocos prioritários",
      value: "5",
      detail: "Leitura consolidada dos blocos que mais orientam a preparação."
    },
    {
      id: "pscpp-map-summary-good",
      label: "Cobertura boa",
      value: "1",
      detail: "Há bloco com base técnica já pronta para revisão."
    },
    {
      id: "pscpp-map-summary-partial",
      label: "Cobertura parcial",
      value: "2",
      detail: "Exige reforço e conferência antes de ampliar a revisão."
    },
    {
      id: "pscpp-map-summary-gaps",
      label: "Gaps encontrados",
      value: "4",
      detail: "Lacunas principais conectadas ao edital de referência."
    },
    {
      id: "pscpp-map-summary-sessions",
      label: "Sessões sugeridas",
      value: "8",
      detail: "Sessões do ciclo ligadas aos gaps mais urgentes."
    }
  ],
  blocks: pscppCrosswalkBlocks,
  mainGaps: pscppCrosswalkGaps,
  relationships: pscppCrosswalkRelationships,
  highlightedSessions: [
    { ...pscppCrosswalkSessionRefs["1"], emphasis: "gap_focus" },
    { ...pscppCrosswalkSessionRefs["2"], emphasis: "gap_focus" },
    { ...pscppCrosswalkSessionRefs["4"], emphasis: "gap_focus" },
    { ...pscppCrosswalkSessionRefs["5"], emphasis: "gap_focus" },
    { ...pscppCrosswalkSessionRefs["6"], emphasis: "gap_focus" },
    { ...pscppCrosswalkSessionRefs["8"], emphasis: "gap_focus" },
    { ...pscppCrosswalkSessionRefs["10"], emphasis: "gap_focus" },
    { ...pscppCrosswalkSessionRefs["11"], emphasis: "gap_focus" }
  ]
};

const studySessionRelatedGaps: Record<string, StudySessionRelatedGap> = {
  "gap-squat": {
    id: "gap-squat",
    title: "Squat e interação em canal estreito",
    detail: "Precisa de reforço para leitura de cenário e decisão de manobra."
  },
  "gap-colreg-signals": {
    id: "gap-colreg-signals",
    title: "Luzes e sinais em visibilidade restrita",
    detail: "Exige revisão de exceções e comando negativo em COLREG."
  },
  "gap-radar-ecdis": {
    id: "gap-radar-ecdis",
    title: "Radar, ECDIS e AIS",
    detail: "Precisa de material mais completo antes de uma revisão segura."
  },
  "gap-arte-naval": {
    id: "gap-arte-naval",
    title: "Números e nomenclaturas confundíveis",
    detail: "Pede consolidação de termos fatais e pares que a banca troca."
  },
  "gap-normam-gmdss": {
    id: "gap-normam-gmdss",
    title: "NORMAM, Tribunal Marítimo e GMDSS",
    detail: "Pede reforço normativo e alinhamento preliminar com o edital."
  }
};

export const studySessionDetailsById: Record<string, StudySessionDetail> = {
  "session-1-manobrabilidade-forcas": {
    id: "session-1-manobrabilidade-forcas",
    sessionNumber: 1,
    title: "Sessão 1 — Manobrabilidade: forças, resistência e propulsão",
    objective: "Entender como forças externas, resistência e propulsão afetam a decisão de manobra.",
    priorityBlockTitle: pscppCrosswalkBlocks[0].title,
    durationLabel: "20 + 60-90 + 40 + 20 min",
    relatedMaterialsCount: 2,
    relatedGapsCount: 1,
    statusLabel: "Pronto para estudo",
    note: "Base para o bloco dominante do caminho PSCPP.",
    structure: [...pscppSessionStructure],
    relatedMaterials: pscppCrosswalkBlocks[0].relatedMaterials,
    relatedEditais: pscppCrosswalkBlocks[0].relatedEditais,
    relatedGaps: [studySessionRelatedGaps["gap-squat"]],
    checklist: [
      { id: "s1-c1", label: "Revisar forças de vento e corrente sobre o casco." },
      { id: "s1-c2", label: "Mapear resistência, propulsão e efeito do leme." },
      { id: "s1-c3", label: "Criar mapa de causa e efeito da manobra." },
      { id: "s1-c4", label: "Registrar conceitos confundíveis." }
    ],
    outputs: [
      { id: "s1-o1", label: "Resumo operacional", statusLabel: "Pendente de revisão" },
      { id: "s1-o2", label: "Mapa de pegadinhas", statusLabel: "Pendente de revisão" },
      { id: "s1-o3", label: "Flashcards", statusLabel: "Pendente de revisão" },
      { id: "s1-o4", label: "Questões candidatas para revisão", statusLabel: "Ainda não geradas" }
    ],
    cautions: [
      "Esta tela não altera seu progresso.",
      "Questões candidatas ainda exigem revisão."
    ]
  },
  "session-2-colreg-regras": {
    id: "session-2-colreg-regras",
    sessionNumber: 2,
    title: "Sessão 2 — COLREG: regras de governo e navegação",
    objective: "Aplicar regras de governo em cenários operacionais, sem tratar a norma como decoreba isolada.",
    priorityBlockTitle: pscppCrosswalkBlocks[1].title,
    durationLabel: "20 + 60-90 + 40 + 20 min",
    relatedMaterialsCount: 1,
    relatedGapsCount: 1,
    statusLabel: "Requer revisão",
    note: "Priorize exceções, cenários e sinais em sequência.",
    structure: [...pscppSessionStructure],
    relatedMaterials: pscppCrosswalkBlocks[1].relatedMaterials,
    relatedEditais: pscppCrosswalkBlocks[1].relatedEditais,
    relatedGaps: [studySessionRelatedGaps["gap-colreg-signals"]],
    checklist: [
      { id: "s2-c1", label: "Classificar embarcação e condição operacional." },
      { id: "s2-c2", label: "Identificar a regra aplicável ao cenário." },
      { id: "s2-c3", label: "Separar regra geral e exceção." },
      { id: "s2-c4", label: "Criar um cenário com pegadinha provável." }
    ],
    outputs: [
      { id: "s2-o1", label: "Resumo operacional", statusLabel: "Pendente de revisão" },
      { id: "s2-o2", label: "Mapa de pegadinhas", statusLabel: "Pendente de revisão" },
      { id: "s2-o3", label: "Flashcards", statusLabel: "Pendente de revisão" },
      { id: "s2-o4", label: "Questões candidatas para revisão", statusLabel: "Ainda não geradas" }
    ],
    cautions: [
      "Esta tela não altera seu progresso.",
      "Questões candidatas ainda exigem revisão."
    ]
  },
  "session-3-arte-naval": {
    id: "session-3-arte-naval",
    sessionNumber: 3,
    title: "Sessão 3 — Arte Naval: nomenclatura, geometria e estabilidade",
    objective: "Consolidar vocabulário técnico e pares que a banca pode confundir.",
    priorityBlockTitle: pscppCrosswalkBlocks[3].title,
    durationLabel: "20 + 60-90 + 40 + 20 min",
    relatedMaterialsCount: 1,
    relatedGapsCount: 1,
    statusLabel: "Pronto para estudo",
    note: "Boa base técnica, com foco em termos fatais e nomenclaturas.",
    structure: [...pscppSessionStructure],
    relatedMaterials: pscppCrosswalkBlocks[3].relatedMaterials,
    relatedEditais: pscppCrosswalkBlocks[3].relatedEditais,
    relatedGaps: [studySessionRelatedGaps["gap-arte-naval"]],
    checklist: [
      { id: "s3-c1", label: "Revisar nomenclatura e geometria." },
      { id: "s3-c2", label: "Separar conceitos confundíveis." },
      { id: "s3-c3", label: "Registrar números e termos fatais." },
      { id: "s3-c4", label: "Fazer flashcards bilíngues quando útil." }
    ],
    outputs: [
      { id: "s3-o1", label: "Resumo operacional", statusLabel: "Pendente de revisão" },
      { id: "s3-o2", label: "Mapa de pegadinhas", statusLabel: "Pendente de revisão" },
      { id: "s3-o3", label: "Flashcards", statusLabel: "Pendente de revisão" },
      { id: "s3-o4", label: "Questões candidatas para revisão", statusLabel: "Ainda não geradas" }
    ],
    cautions: [
      "Esta tela não altera seu progresso.",
      "Questões candidatas ainda exigem revisão."
    ]
  },
  "session-9-navegacao-restrita": {
    id: "session-9-navegacao-restrita",
    sessionNumber: 9,
    title: "Sessão 9 — Navegação restrita: radar, ECDIS, AIS e passage planning",
    objective: "Conectar navegação restrita, instrumentos e planejamento de derrota a decisões de praticagem.",
    priorityBlockTitle: pscppCrosswalkBlocks[2].title,
    durationLabel: "20 + 60-90 + 40 + 20 min",
    relatedMaterialsCount: 1,
    relatedGapsCount: 1,
    statusLabel: "Requer revisão",
    note: "A sessão depende de material complementar e validação do roteiro escaneado.",
    structure: [...pscppSessionStructure],
    relatedMaterials: pscppCrosswalkBlocks[2].relatedMaterials,
    relatedEditais: pscppCrosswalkBlocks[2].relatedEditais,
    relatedGaps: [studySessionRelatedGaps["gap-radar-ecdis"]],
    checklist: [
      { id: "s9-c1", label: "Revisar uso prático de radar, ECDIS e AIS." },
      { id: "s9-c2", label: "Conectar instrumentos ao passage planning." },
      { id: "s9-c3", label: "Separar limitações operacionais e alertas de cenário." },
      { id: "s9-c4", label: "Registrar o que ainda precisa de material mais completo." }
    ],
    outputs: [
      { id: "s9-o1", label: "Resumo operacional", statusLabel: "Pendente de revisão" },
      { id: "s9-o2", label: "Mapa de pegadinhas", statusLabel: "Pendente de revisão" },
      { id: "s9-o3", label: "Flashcards", statusLabel: "Pendente de revisão" },
      { id: "s9-o4", label: "Questões candidatas para revisão", statusLabel: "Ainda não geradas" }
    ],
    cautions: [
      "Esta tela não altera seu progresso.",
      "Questões candidatas ainda exigem revisão."
    ]
  },
  "session-12-simulado-curto-revisao": {
    id: "session-12-simulado-curto-revisao",
    sessionNumber: 12,
    title: "Sessão 12 — Simulado curto + revisão de erros",
    objective: "Revisar lacunas e transformar erros em próximos passos.",
    priorityBlockTitle: pscppCrosswalkBlocks[4].title,
    durationLabel: "20 + 60-90 + 40 + 20 min",
    relatedMaterialsCount: 0,
    relatedGapsCount: 1,
    statusLabel: "Requer revisão",
    note: "Usa revisão curta e não representa geração executável de simulado.",
    structure: [...pscppSessionStructure],
    relatedMaterials: [],
    relatedEditais: pscppCrosswalkBlocks[4].relatedEditais,
    relatedGaps: [studySessionRelatedGaps["gap-normam-gmdss"]],
    checklist: [
      { id: "s12-c1", label: "Revisar os erros mais recorrentes do bloco normativo." },
      { id: "s12-c2", label: "Separar falhas de conceito, regra e leitura de enunciado." },
      { id: "s12-c3", label: "Transformar os erros em próximos passos de estudo." },
      { id: "s12-c4", label: "Atualizar o caderno de cenários e conceitos confundíveis." }
    ],
    outputs: [
      { id: "s12-o1", label: "Resumo operacional", statusLabel: "Pendente de revisão" },
      { id: "s12-o2", label: "Mapa de pegadinhas", statusLabel: "Pendente de revisão" },
      { id: "s12-o3", label: "Flashcards", statusLabel: "Pendente de revisão" },
      { id: "s12-o4", label: "Questões candidatas para revisão", statusLabel: "Ainda não geradas" }
    ],
    cautions: [
      "Esta tela não altera seu progresso.",
      "Questões candidatas ainda exigem revisão.",
      "Simulado curto ainda não executável.",
      "Esta tela não gera prova nem corrige respostas."
    ]
  }
};

export const studySessionWorkspaceViewModelMock: StudySessionWorkspaceViewModel = {
  connection: {
    state: "mock",
    source: "mock",
    title: "Dados de demonstração",
    detail: "Sessões sugeridas montadas por fallback auditado a partir do ciclo PSCPP, materiais e gaps conectados."
  },
  summary: [
    {
      id: "study-summary-sessions",
      label: "Sessões sugeridas",
      value: "5",
      detail: "Sessões priorizadas para orientar o próximo estudo."
    },
    {
      id: "study-summary-gaps",
      label: "Gaps conectados",
      value: "5",
      detail: "Lacunas ligadas diretamente às sessões do caminho PSCPP."
    },
    {
      id: "study-summary-materials",
      label: "Materiais relacionados",
      value: "3",
      detail: "Materiais já conectados ao estudo de hoje."
    },
    {
      id: "study-summary-questions",
      label: "Questões candidatas em revisão",
      value: "5",
      detail: "As saídas esperadas seguem como revisão necessária."
    }
  ],
  nextSuggestedSessionId: "session-1-manobrabilidade-forcas",
  sessions: Object.values(studySessionDetailsById).map((item) => ({
    id: item.id,
    sessionNumber: item.sessionNumber,
    title: item.title,
    objective: item.objective,
    priorityBlockTitle: item.priorityBlockTitle,
    durationLabel: item.durationLabel,
    relatedMaterialsCount: item.relatedMaterialsCount,
    relatedGapsCount: item.relatedGapsCount,
    statusLabel: item.statusLabel,
    note: item.note
  })),
  highlightedGaps: [
    studySessionRelatedGaps["gap-squat"],
    studySessionRelatedGaps["gap-colreg-signals"],
    studySessionRelatedGaps["gap-radar-ecdis"],
    studySessionRelatedGaps["gap-normam-gmdss"]
  ],
  starterMaterials: [
    pscppCrosswalkBlocks[0].relatedMaterials[0],
    pscppCrosswalkBlocks[0].relatedMaterials[1],
    pscppCrosswalkBlocks[2].relatedMaterials[0]
  ]
};

export const onboardingSteps: OnboardingStepItem[] = [
  {
    id: "onboarding-step-1",
    stepNumber: 1,
    title: "Envie material",
    description: "Adicione PDFs, TXT ou Markdown para validação inicial.",
    statusLabel: "Upload controlado",
    note: "Validação inicial disponível com leitura cautelosa do formato enviado.",
    cautionLabel: "PDFs escaneados podem exigir OCR em validação.",
    primaryLink: {
      label: "Enviar material",
      href: "/materials/upload"
    },
    secondaryLinks: [
      {
        label: "Ver materiais",
        href: "/materials"
      }
    ]
  },
  {
    id: "onboarding-step-2",
    stepNumber: 2,
    title: "Revise edital",
    description: "Confira tópicos, bibliografia identificada e lacunas antes de tratar a análise como final.",
    statusLabel: "Análise candidata",
    note: "Use a leitura do edital como base de conferência, não como verdade final automática.",
    cautionLabel: "O alinhamento é preliminar e precisa de conferência.",
    primaryLink: {
      label: "Ver editais",
      href: "/editais"
    },
    secondaryLinks: []
  },
  {
    id: "onboarding-step-3",
    stepNumber: 3,
    title: "Veja o mapa PSCPP",
    description: "Cruze materiais, edital, gaps e blocos prioritários da prova.",
    statusLabel: "Mapa de preparação",
    note: "O mapa mostra cobertura e gaps sem criar plano automático.",
    cautionLabel: "Gaps encontrados ainda pedem leitura guiada e revisão necessária.",
    primaryLink: {
      label: "Ver mapa PSCPP",
      href: "/pscpp/mapa"
    },
    secondaryLinks: [
      {
        label: "Ver ciclo PSCPP",
        href: "/pscpp/ciclo"
      }
    ]
  },
  {
    id: "onboarding-step-4",
    stepNumber: 4,
    title: "Siga o estudo de hoje",
    description: "Abra a sessão sugerida, consulte materiais relacionados e use o checklist de estudo.",
    statusLabel: "Guia flexível",
    note: "A sessão sugerida ajuda a decidir o que estudar agora, com foco em materiais e gaps conectados.",
    cautionLabel: "A tela não altera seu progresso e não cria agenda automaticamente.",
    primaryLink: {
      label: "Ver estudo de hoje",
      href: "/study"
    },
    secondaryLinks: []
  }
];

export const onboardingViewModelMock: OnboardingViewModel = {
  summary: [
    {
      id: "onboarding-summary-upload",
      label: "Upload controlado",
      value: "1",
      detail: "Entrada segura já conectada ao fluxo de materiais."
    },
    {
      id: "onboarding-summary-edital",
      label: "Análise candidata",
      value: "1",
      detail: "Edital de referência pronto para conferência cuidadosa."
    },
    {
      id: "onboarding-summary-map",
      label: "Mapa de preparação",
      value: "5",
      detail: "Blocos prioritários já conectados a gaps e materiais."
    },
    {
      id: "onboarding-summary-study",
      label: "Guia flexível",
      value: "5",
      detail: "Sessões sugeridas prontas para consulta guiada."
    }
  ],
  readyHighlights: [
    "Upload controlado já aponta para a entrada segura de materiais.",
    "Edital de referência, mapa PSCPP e estudo de hoje já podem orientar a leitura inicial.",
    "Os links principais levam apenas para páginas de consulta e revisão."
  ],
  reviewHighlights: [
    "OCR em validação ainda exige cautela para PDFs escaneados.",
    "A análise de edital continua preliminar e precisa de conferência.",
    "Questões candidatas e simulado curto seguem em revisão, sem execução automática."
  ],
  steps: onboardingSteps
};
