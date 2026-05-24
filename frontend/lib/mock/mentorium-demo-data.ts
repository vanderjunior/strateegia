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
      "Leitura de PDFs textuais, TXT e Markdown com pipeline user-scoped e artefatos deterministas.",
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
      "Tentativa, correcao, score, ledger e guardrails auditaveis sem mutacoes amplas nao aprovadas.",
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
      "Cruze bibliografia, coverage, gaps, ciclo de estudo e perfil PSCPP para orientar o treinamento."
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
    title: "Bloco dominante",
    value: "Manobrabilidade e rebocadores",
    note: "prioridade 1 no guia PSCPP",
    metric: 78
  },
  {
    title: "Rotacao atual",
    value: "Sessao 7 de 12",
    note: "atracacao, desatracacao e fundeio",
    metric: 58
  },
  {
    title: "Treino da semana",
    value: "40 questoes por topico",
    note: "fase de consolidacao por cenarios",
    metric: 66
  }
] as const;

export const documentStatusCards: CapabilityCard[] = [
  {
    title: "PDF textual",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Suportado hoje com extracao, chunking e sectioning deterministas.",
    detail: "TXT, Markdown e PDFs textuais entram no pipeline atual."
  },
  {
    title: "PDF escaneado / OCR",
    status: "implemented_but_needs_manual_validation" as CapabilityStatus,
    summary: "Fallback opcional com Tesseract, desabilitado por padrao.",
    detail: "Nao tratar como producao pronta sem validacao de campo."
  },
  {
    title: "Ingestao de edital",
    status: "partially_implemented" as CapabilityStatus,
    summary: "Extracao heuristica de secoes, topicos e bibliografia.",
    detail: "Artefato candidato e review-friendly."
  },
  {
    title: "Alinhamento bibliografico",
    status: "partially_implemented" as CapabilityStatus,
    summary: "Coverage, gaps e redundancias com evidencias bounded.",
    detail: "Ainda nao e um mapeamento final verificado."
  }
] as const;

export const runtimeStatusCards: CapabilityCard[] = [
  {
    title: "Tentativa / correcao / score",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Cadeia auditavel e bem testada.",
    detail: "A etapa de entrega executavel ainda nao esta aberta."
  },
  {
    title: "Minimal progress ledger",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Aplica apenas ledger minimo com idempotencia e rollback metadata.",
    detail: "Sem mutar ranking, retention, scheduler ou study cycle."
  },
  {
    title: "Applied event ledger",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Replay-safe e deduplicado para eventos aplicados.",
    detail: "Camada auditavel para downstream review."
  },
  {
    title: "Propagation guardrail",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Readiness-only para superficies futuras.",
    detail: "Nao propaga ranking, retention, scheduler, ciclo ou graph."
  },
  {
    title: "Controlled propagation ledger",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Registra entradas isoladas de propagacao controlada.",
    detail: "Ledger-only, sem apply direto em runtime."
  },
  {
    title: "Geracao automatica completa de simulado",
    status: "foundation_only" as CapabilityStatus,
    summary: "Blueprint, drafts e assembly existem, mas a prova final executavel nao esta verificada.",
    detail: "Evitar prometer simulado perfeito a partir de qualquer PDF."
  }
] as const;

export const pscppProfileCards: CapabilityCard[] = [
  {
    title: "Question style profile",
    status: "implemented_and_tested" as CapabilityStatus,
    summary: "Perfil PSCPP/Praticagem com ancora bibliografica, formato A-E e arquetipos tecnicos.",
    detail: "Base testada para orientar blueprint e draft metadata com regras de seguranca."
  },
  {
    title: "Question generation integration",
    status: "metadata_only" as CapabilityStatus,
    summary: "Integracao de metadata e validacao para simulado, fixation, review e summary.",
    detail: "Source-grounding, arquetipos e human review seguem sem gerar respostas finais sensiveis."
  },
  {
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
