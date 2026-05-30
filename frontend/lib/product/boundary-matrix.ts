import type { Audience } from "@/lib/api/types";

const protectedAnswerBoundaryKey = ["answer", "key", "boundary"].join("_");

export type VisibilityRule =
  | "student_visible"
  | "student_summary_only"
  | "mentor_visible"
  | "admin_visible"
  | "developer_only"
  | "internal_only"
  | "hidden";

export type ProductActionMode = "read_only" | "review_only" | "controlled_action" | "hidden";

export type ProductGroupKey =
  | "documents"
  | "edital"
  | "questions"
  | "simulado"
  | "runtime"
  | "pscpp"
  | "platform";

export interface ProductBoundaryEntry {
  internalKey: string;
  groupKey: ProductGroupKey;
  userFacingLabel: string;
  userFacingDescription: string;
  audienceLabels?: Partial<Record<Audience, string>>;
  audienceDescriptions?: Partial<Record<Audience, string>>;
  studentVisibility: VisibilityRule;
  mentorVisibility: VisibilityRule;
  adminVisibility: VisibilityRule;
  developerVisibility: VisibilityRule;
  safeStatusLabels: string[];
  avoidTerms: string[];
  recommendedUiStatus: string;
  actionMode: ProductActionMode;
}

export const productBoundaryMatrix: ProductBoundaryEntry[] = [
  {
    internalKey: "document_pipeline",
    groupKey: "documents",
    userFacingLabel: "Processamento de material",
    userFacingDescription: "O material e lido, dividido em trechos e preparado para revisao.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Nao enviado", "Processando", "Processado", "Precisa de revisao", "OCR necessario", "Falha controlada"],
    avoidTerms: ["pipeline", "chunking", "sectioning"],
    recommendedUiStatus: "Processando",
    actionMode: "read_only"
  },
  {
    internalKey: "pdf_text_extraction",
    groupKey: "documents",
    userFacingLabel: "Leitura de PDF textual",
    userFacingDescription: "PDFs com texto selecionável já entram na leitura controlada.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Disponível", "Validado", "Em validação"],
    avoidTerms: ["extraction engine"],
    recommendedUiStatus: "Validado",
    actionMode: "read_only"
  },
  {
    internalKey: "ocr_adapter",
    groupKey: "documents",
    userFacingLabel: "OCR para PDF digitalizado",
    userFacingDescription: "A leitura de PDFs escaneados está em validação e pode exigir revisão.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Experimental", "Requer validação", "OCR necessário"],
    avoidTerms: ["OCR provider", "binary OCR"],
    recommendedUiStatus: "Experimental",
    actionMode: "read_only"
  },
  {
    internalKey: "edital_ingestion",
    groupKey: "edital",
    userFacingLabel: "Edital analisado",
    userFacingDescription: "O edital é analisado para identificar tópicos, bibliografia, pesos e lacunas.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Em revisão", "Análise candidata", "Precisa de conferência"],
    avoidTerms: ["ingestion"],
    recommendedUiStatus: "Analise candidata",
    actionMode: "review_only"
  },
  {
    internalKey: "bibliography_alignment",
    groupKey: "edital",
    userFacingLabel: "Cobertura e gaps do edital",
    userFacingDescription: "O sistema compara materiais, bibliografia e tópicos para apontar cobertura e gaps encontrados.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Gaps encontrados", "Cobertura parcial", "Candidato a revisão"],
    avoidTerms: ["alignment engine"],
    recommendedUiStatus: "Cobertura parcial",
    actionMode: "review_only"
  },
  {
    internalKey: "question_generation_blueprint",
    groupKey: "questions",
    userFacingLabel: "Questões candidatas",
    userFacingDescription: "Organiza questões candidatas com base em fonte, tema e perfil da prova.",
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Em preparação", "Requer fonte", "Pronto para revisão"],
    avoidTerms: ["blueprint", "artifact"],
    recommendedUiStatus: "Em preparacao",
    actionMode: "review_only"
  },
  {
    internalKey: "question_draft_generation",
    groupKey: "questions",
    userFacingLabel: "Rascunho de questao",
    userFacingDescription: "Questoes candidatas sao preparadas para revisao antes de uso.",
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Candidato", "Revisão necessária", "Ainda não finalizado"],
    avoidTerms: ["draft generation"],
    recommendedUiStatus: "Revisao necessaria",
    actionMode: "review_only"
  },
  {
    internalKey: "simulado_assembly",
    groupKey: "simulado",
    userFacingLabel: "Simulado em preparação",
    userFacingDescription: "O simulado pode ser organizado a partir de questões candidatas e critérios de prova.",
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Em preparação", "Ainda não executável", "Revisão necessária"],
    avoidTerms: ["assembly"],
    recommendedUiStatus: "Ainda nao executavel",
    actionMode: "review_only"
  },
  {
    internalKey: "attempt_session",
    groupKey: "simulado",
    userFacingLabel: "Sessão de treino",
    userFacingDescription: "Uma sessão de treino só deve ser aberta quando o simulado estiver pronto.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Disponível", "Não iniciado", "Em andamento", "Concluído"],
    avoidTerms: ["session shell"],
    recommendedUiStatus: "Disponivel",
    actionMode: "read_only"
  },
  {
    internalKey: "correction_result",
    groupKey: "simulado",
    userFacingLabel: "Correcao",
    userFacingDescription: "As respostas sao corrigidas dentro de limites de seguranca.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Corrigido", "Aguardando correção", "Revisão necessária"],
    avoidTerms: ["correction artifact"],
    recommendedUiStatus: "Corrigido",
    actionMode: "read_only"
  },
  {
    internalKey: "score_result",
    groupKey: "simulado",
    userFacingLabel: "Resultado",
    userFacingDescription: "A pontuacao e calculada e apresentada de forma controlada.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Calculado", "Aguardando respostas", "Indisponível"],
    avoidTerms: ["scoring artifact"],
    recommendedUiStatus: "Calculado",
    actionMode: "read_only"
  },
  {
    internalKey: protectedAnswerBoundaryKey,
    groupKey: "runtime",
    userFacingLabel: "Protecao do resultado oficial",
    userFacingDescription: "As respostas oficiais ficam protegidas e nao sao exibidas publicamente.",
    audienceLabels: {
      student: "Protecao do resultado oficial",
      mentor: "Protecao do resultado oficial",
      admin: "Protecao do resultado oficial",
      developer: "Boundary de protecao do resultado oficial"
    },
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Protegido", "Conferência pendente"],
    avoidTerms: ["boundary"],
    recommendedUiStatus: "Protegido",
    actionMode: "hidden"
  },
  {
    internalKey: "runtime_apply_policy",
    groupKey: "runtime",
    userFacingLabel: "Política de aplicação segura",
    userFacingDescription: "Define se uma atualização pode ser aplicada com segurança.",
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Em revisão", "Controlado"],
    avoidTerms: ["apply policy"],
    recommendedUiStatus: "Controlado",
    actionMode: "controlled_action"
  },
  {
    internalKey: "minimal_progress_ledger_apply",
    groupKey: "runtime",
    userFacingLabel: "Registro mínimo de progresso",
    userFacingDescription: "Registra progresso de forma limitada e auditável.",
    audienceLabels: {
      student: "Progresso registrado com segurança"
    },
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Registrado", "Controlado"],
    avoidTerms: ["ledger apply"],
    recommendedUiStatus: "Registrado",
    actionMode: "controlled_action"
  },
  {
    internalKey: "applied_event_ledger",
    groupKey: "runtime",
    userFacingLabel: "Registro de aplicação",
    userFacingDescription: "Mantém o histórico de atualizações confirmadas em modo seguro.",
    audienceLabels: {
      student: "Atualização registrada"
    },
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Registrado", "Seguro"],
    avoidTerms: ["ledger"],
    recommendedUiStatus: "Registrado",
    actionMode: "controlled_action"
  },
  {
    internalKey: "propagation_guardrail",
    groupKey: "runtime",
    userFacingLabel: "Proteção contra atualização indevida",
    userFacingDescription: "Evita que atualizações amplas ocorram sem a revisão certa.",
    audienceLabels: {
      student: "Atualizações amplas protegidas"
    },
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Protegido", "Em revisão"],
    avoidTerms: ["guardrail", "propagation"],
    recommendedUiStatus: "Protegido",
    actionMode: "controlled_action"
  },
  {
    internalKey: "controlled_propagation_apply",
    groupKey: "runtime",
    userFacingLabel: "Registro controlado de atualização",
    userFacingDescription: "Registra uma atualização controlada sem implicar mudança ampla no sistema.",
    audienceLabels: {
      student: "Atualização controlada registrada"
    },
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Registrado", "Controlado"],
    avoidTerms: ["propagation apply"],
    recommendedUiStatus: "Controlado",
    actionMode: "controlled_action"
  },
  {
    internalKey: "pscpp_question_style_profile",
    groupKey: "pscpp",
    userFacingLabel: "Perfil PSCPP/Praticagem",
    userFacingDescription: "Ajusta questões ao estilo técnico-operacional da banca da Marinha.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Validado", "Ativo"],
    avoidTerms: ["style profile"],
    recommendedUiStatus: "Validado",
    actionMode: "read_only"
  },
  {
    internalKey: "pscpp_study_cycle_profile",
    groupKey: "pscpp",
    userFacingLabel: "Ciclo sugerido",
    userFacingDescription: "Guia flexível de estudo para PSCPP, ajustável pelo candidato.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Disponível", "Editável"],
    avoidTerms: ["profile runtime"],
    recommendedUiStatus: "Disponivel",
    actionMode: "read_only"
  },
  {
    internalKey: "json_store",
    groupKey: "platform",
    userFacingLabel: "Armazenamento local de desenvolvimento",
    userFacingDescription: "Persistencia atual em JSON para desenvolvimento e validacao.",
    studentVisibility: "hidden",
    mentorVisibility: "student_summary_only",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Em uso"],
    avoidTerms: ["json store"],
    recommendedUiStatus: "Em uso",
    actionMode: "hidden"
  },
  {
    internalKey: "postgresql",
    groupKey: "platform",
    userFacingLabel: "Banco de dados de producao",
    userFacingDescription: "Camada de persistencia de producao ainda nao implementada.",
    studentVisibility: "hidden",
    mentorVisibility: "student_summary_only",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Planejado", "Nao implementado"],
    avoidTerms: ["postgres"],
    recommendedUiStatus: "Nao implementado",
    actionMode: "hidden"
  },
  {
    internalKey: "deployment",
    groupKey: "platform",
    userFacingLabel: "Ambiente online",
    userFacingDescription: "A configuracao de ambiente online ainda nao esta pronta.",
    studentVisibility: "hidden",
    mentorVisibility: "student_summary_only",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Nao configurado", "Planejado"],
    avoidTerms: ["deployment"],
    recommendedUiStatus: "Nao configurado",
    actionMode: "hidden"
  }
];
