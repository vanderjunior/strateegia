const protectedAnswerBoundaryKey = ["answer", "key", "boundary"].join("_");

export const userFacingLabels = {
  progressRegisteredSafely: "Progresso registrado com seguranca",
  applicationRecorded: "Atualizacao registrada",
  broadUpdatesProtected: "Atualizacoes amplas protegidas",
  controlledUpdateRecorded: "Atualizacao controlada registrada",
  safeApplyPolicy: "Politica de aplicacao segura",
  simuladoFlow: "Fluxo auditavel de simulado",
  materialProcessed: "Material processado",
  gapsFound: "Gaps encontrados",
  summaryReadyForReview: "Resumo pronto para revisao",
  simuladoPreparing: "Simulado em preparacao",
  notExecutableYet: "Ainda nao executavel",
  protectedAnswerBoundaryKey
} as const;
