import type { ApiSource, CapabilityStatusItem } from "@/lib/api/types";

export function buildAuditedCapabilityItems(source: ApiSource): CapabilityStatusItem[] {
  return [
    {
      id: "text-pdf",
      internalKey: "pdf_text_extraction",
      label: "Leitura de PDF textual",
      status: "implemented_and_tested",
      source,
      detail: "Leitura textual validada para materiais com texto selecionável."
    },
    {
      id: "scanned-ocr",
      internalKey: "ocr_adapter",
      label: "PDF que exige conferência",
      status: "implemented_but_needs_manual_validation",
      source,
      detail: "Alguns PDFs podem precisar de uma versão textual antes de entrar no estudo."
    },
    {
      id: "edital-ingestion",
      internalKey: "edital_ingestion",
      label: "Edital analisado",
      status: "partially_implemented",
      source,
      detail: "Tópicos, bibliografia e lacunas seguem como análise candidata."
    },
    {
      id: "bibliography-alignment",
      internalKey: "bibliography_alignment",
      label: "Cobertura do edital",
      status: "partially_implemented",
      source,
      detail: "Pontos cobertos e pontos a revisar ainda exigem conferência."
    },
    {
      id: "pscpp-style",
      internalKey: "pscpp_question_style_profile",
      label: "Perfil PSCPP/Praticagem",
      status: "implemented_and_tested",
      source,
      detail: "Perfil técnico-operacional validado para orientar revisão e preparação."
    },
    {
      id: "pscpp-generation",
      internalKey: "question_generation_blueprint",
      label: "Questões de fixação",
      status: "metadata_only",
      source,
      detail: "Questões de apoio orientam revisão, sem respostas finais expostas."
    },
    {
      id: "pscpp-cycle",
      internalKey: "pscpp_study_cycle_profile",
      label: "Ciclo sugerido",
      status: "implemented_and_tested",
      source,
      detail: "Guia flexível disponível, sem agenda automática."
    },
    {
      id: "simulado-generation",
      internalKey: "simulado_assembly",
      label: "Avaliações futuras",
      status: "foundation_only",
      source,
      detail: "Avaliações completas ficam para uma etapa posterior."
    },
    {
      id: "simulado-runtime",
      internalKey: "attempt_session",
      label: "Sessão de treino",
      status: "implemented_and_tested",
      source,
      detail: "A sessão de treino só deve avançar quando as avaliações futuras estiverem realmente prontas."
    },
    {
      id: "minimal-ledger",
      internalKey: "minimal_progress_ledger_apply",
      label: "Progresso registrado com segurança",
      status: "implemented_and_tested",
      source,
      detail: "Registro limitado a ações explícitas, sem atualização ampla."
    },
    {
      id: "applied-ledger",
      internalKey: "applied_event_ledger",
      label: "Atualização registrada",
      status: "implemented_and_tested",
      source,
      detail: "Histórico seguro de atualização, sem ação aberta ao candidato."
    },
    {
      id: "propagation-guardrail",
      internalKey: "propagation_guardrail",
      label: "Proteção contra atualização indevida",
      status: "implemented_and_tested",
      source,
      detail: "Proteção mantida para evitar atualização ampla sem revisão."
    },
    {
      id: "controlled-propagation",
      internalKey: "controlled_propagation_apply",
      label: "Atualização controlada registrada",
      status: "implemented_and_tested",
      source,
      detail: "Registro controlado, sem mudança ampla na experiência atual."
    },
    {
      id: "persistence",
      internalKey: "json_store",
      label: "Persistencia",
      status: "partially_implemented",
      source,
      detail: "JSON store em uso; PostgreSQL ainda nao implementado."
    },
    {
      id: "deploy",
      internalKey: "deployment",
      label: "Deploy",
      status: "not_implemented",
      source,
      detail: "Staging e deploy ainda nao configurados."
    }
  ];
}
