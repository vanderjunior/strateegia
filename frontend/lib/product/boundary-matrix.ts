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
    userFacingDescription: "PDFs com texto selecionavel podem ser processados.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Disponivel", "Validado", "Em validacao"],
    avoidTerms: ["extraction engine"],
    recommendedUiStatus: "Validado",
    actionMode: "read_only"
  },
  {
    internalKey: "ocr_adapter",
    groupKey: "documents",
    userFacingLabel: "OCR para PDF digitalizado",
    userFacingDescription: "A leitura de PDFs escaneados esta em validacao e pode exigir revisao.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Experimental", "Requer validacao", "OCR necessario"],
    avoidTerms: ["OCR provider", "binary OCR"],
    recommendedUiStatus: "Experimental",
    actionMode: "read_only"
  },
  {
    internalKey: "edital_ingestion",
    groupKey: "edital",
    userFacingLabel: "Leitura de edital",
    userFacingDescription: "O edital e analisado para identificar topicos, bibliografia, pesos e lacunas.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Em revisao", "Analise candidata", "Precisa de conferencia"],
    avoidTerms: ["ingestion"],
    recommendedUiStatus: "Analise candidata",
    actionMode: "review_only"
  },
  {
    internalKey: "bibliography_alignment",
    groupKey: "edital",
    userFacingLabel: "Alinhamento bibliografico",
    userFacingDescription: "O sistema compara materiais, bibliografia e topicos para apontar cobertura e gaps.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Gaps encontrados", "Cobertura parcial", "Candidato a revisao"],
    avoidTerms: ["alignment engine"],
    recommendedUiStatus: "Cobertura parcial",
    actionMode: "review_only"
  },
  {
    internalKey: "question_generation_blueprint",
    groupKey: "questions",
    userFacingLabel: "Planejamento de questoes",
    userFacingDescription: "Estrutura candidatos de questoes com base em fonte, tema e perfil da prova.",
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Em preparacao", "Requer fonte", "Pronto para revisao"],
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
    safeStatusLabels: ["Candidato", "Revisao necessaria", "Ainda nao finalizado"],
    avoidTerms: ["draft generation"],
    recommendedUiStatus: "Revisao necessaria",
    actionMode: "review_only"
  },
  {
    internalKey: "simulado_assembly",
    groupKey: "simulado",
    userFacingLabel: "Montagem de simulado",
    userFacingDescription: "O simulado pode ser organizado a partir de questoes candidatas e criterios de prova.",
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Em preparacao", "Ainda nao executavel", "Revisao necessaria"],
    avoidTerms: ["assembly"],
    recommendedUiStatus: "Ainda nao executavel",
    actionMode: "review_only"
  },
  {
    internalKey: "attempt_session",
    groupKey: "simulado",
    userFacingLabel: "Tentativa de simulado",
    userFacingDescription: "Uma prova pode ser aberta quando o simulado estiver pronto.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Disponivel", "Nao iniciado", "Em andamento", "Concluido"],
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
    safeStatusLabels: ["Corrigido", "Aguardando correcao", "Revisao necessaria"],
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
    safeStatusLabels: ["Calculado", "Aguardando respostas", "Indisponivel"],
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
    safeStatusLabels: ["Protegido", "Revisao controlada"],
    avoidTerms: ["boundary"],
    recommendedUiStatus: "Protegido",
    actionMode: "hidden"
  },
  {
    internalKey: "runtime_apply_policy",
    groupKey: "runtime",
    userFacingLabel: "Politica de aplicacao segura",
    userFacingDescription: "Define se uma atualizacao pode ser aplicada com seguranca.",
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Em revisao", "Controlado"],
    avoidTerms: ["apply policy"],
    recommendedUiStatus: "Controlado",
    actionMode: "controlled_action"
  },
  {
    internalKey: "minimal_progress_ledger_apply",
    groupKey: "runtime",
    userFacingLabel: "Registro minimo de progresso",
    userFacingDescription: "Registra progresso de forma limitada e auditavel.",
    audienceLabels: {
      student: "Progresso registrado com seguranca"
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
    userFacingLabel: "Registro de aplicacao",
    userFacingDescription: "Mantem o historico de atualizacoes confirmadas em modo seguro.",
    audienceLabels: {
      student: "Atualizacao registrada"
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
    userFacingLabel: "Protecao contra atualizacao indevida",
    userFacingDescription: "Evita que atualizacoes amplas ocorram sem a revisao certa.",
    audienceLabels: {
      student: "Atualizacoes amplas protegidas"
    },
    studentVisibility: "student_summary_only",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Protegido", "Em revisao"],
    avoidTerms: ["guardrail", "propagation"],
    recommendedUiStatus: "Protegido",
    actionMode: "controlled_action"
  },
  {
    internalKey: "controlled_propagation_apply",
    groupKey: "runtime",
    userFacingLabel: "Registro controlado de atualizacao",
    userFacingDescription: "Registra uma atualizacao controlada sem implicar mudanca ampla no sistema.",
    audienceLabels: {
      student: "Atualizacao controlada registrada"
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
    userFacingDescription: "Ajusta questoes ao estilo tecnico-operacional da banca da Marinha.",
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
    userFacingLabel: "Ciclo PSCPP sugerido",
    userFacingDescription: "Guia flexivel de estudo para PSCPP, editavel pelo usuario.",
    studentVisibility: "student_visible",
    mentorVisibility: "mentor_visible",
    adminVisibility: "admin_visible",
    developerVisibility: "developer_only",
    safeStatusLabels: ["Disponivel", "Editavel"],
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
