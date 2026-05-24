import type { ApiSource, CapabilityStatusItem } from "@/lib/api/types";

export function buildAuditedCapabilityItems(source: ApiSource): CapabilityStatusItem[] {
  return [
    {
      id: "text-pdf",
      label: "Leitura de PDF textual",
      status: "implemented_and_tested",
      source,
      detail: "Pipeline textual implementado e testado."
    },
    {
      id: "scanned-ocr",
      label: "OCR para PDF escaneado",
      status: "implemented_but_needs_manual_validation",
      source,
      detail: "Fallback opcional com Tesseract ainda sujeito a validacao real."
    },
    {
      id: "edital-ingestion",
      label: "Ingestao de edital",
      status: "partially_implemented",
      source,
      detail: "Extracao heuristica e review-friendly, sem parser final autoritativo."
    },
    {
      id: "bibliography-alignment",
      label: "Alinhamento bibliografico",
      status: "partially_implemented",
      source,
      detail: "Coverage e gaps candidatos, ainda sem verificacao final automatica."
    },
    {
      id: "pscpp-style",
      label: "Perfil PSCPP de questoes",
      status: "implemented_and_tested",
      source,
      detail: "Perfil de estilo e seguranca do PSCPP implementado e testado."
    },
    {
      id: "pscpp-generation",
      label: "Integracao PSCPP na geracao",
      status: "metadata_only",
      source,
      detail: "Metadata e validacao integradas sem expor respostas finais sensiveis."
    },
    {
      id: "pscpp-cycle",
      label: "Perfil PSCPP de ciclo",
      status: "implemented_and_tested",
      source,
      detail: "Guidance flexivel testado, sem agenda forcada."
    },
    {
      id: "simulado-generation",
      label: "Geracao completa de simulado",
      status: "foundation_only",
      source,
      detail: "Foundation existe, mas o fluxo completo fim a fim nao esta validado."
    },
    {
      id: "simulado-runtime",
      label: "Tentativa, correcao e score",
      status: "implemented_and_tested",
      source,
      detail: "Runtime auditavel e testado."
    },
    {
      id: "minimal-ledger",
      label: "Minimal progress ledger",
      status: "implemented_and_tested",
      source,
      detail: "Aplicacao minima e auditavel, sem mutacoes amplas."
    },
    {
      id: "applied-ledger",
      label: "Applied event ledger",
      status: "implemented_and_tested",
      source,
      detail: "Replay-safe e deduplicado."
    },
    {
      id: "propagation-guardrail",
      label: "Propagation guardrail",
      status: "implemented_and_tested",
      source,
      detail: "Readiness-only, sem propagacao real."
    },
    {
      id: "controlled-propagation",
      label: "Controlled propagation ledger",
      status: "implemented_and_tested",
      source,
      detail: "Ledger isolado, sem mutacao direta de runtime."
    },
    {
      id: "persistence",
      label: "Persistencia",
      status: "partially_implemented",
      source,
      detail: "JSON store em uso; PostgreSQL ainda nao implementado."
    },
    {
      id: "deploy",
      label: "Deploy",
      status: "not_implemented",
      source,
      detail: "Staging e deploy ainda nao configurados."
    }
  ];
}
