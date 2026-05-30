"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { BackendConnectionInfo, PipelineDetailViewModel } from "@/lib/api/types";
import { buildMockPipelineDetail, loadPipelineDetail } from "@/lib/adapters/pipeline";
import { sourceLabel } from "@/lib/adapters/capabilities";
import {
  productStatusClass,
  sourceBadgeClass,
  WorkspaceBackLink,
  WorkspaceSourcePanel
} from "@/components/workspace/WorkspaceShared";

function toneClass(tone: PipelineDetailViewModel["steps"][number]["tone"]): string {
  switch (tone) {
    case "complete":
      return "border-emerald-400/30 bg-emerald-400/10";
    case "current":
      return "border-[rgba(201,169,110,0.28)] bg-[rgba(201,169,110,0.10)]";
    case "warning":
      return "border-amber-400/30 bg-amber-400/10";
    default:
      return "border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]";
  }
}

function buildFallback(documentId: string): { connection: BackendConnectionInfo; detail: PipelineDetailViewModel | null } {
  return {
    connection: {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "Demonstração exibida até existir leitura segura para este material."
    },
    detail: buildMockPipelineDetail(documentId)
  };
}

export function PipelineDetailReadOnlyClient({ documentId }: { documentId: string }) {
  const [viewModel, setViewModel] = useState<{ connection: BackendConnectionInfo; detail: PipelineDetailViewModel | null }>(
    buildFallback(documentId)
  );

  useEffect(() => {
    let active = true;
    void loadPipelineDetail(documentId).then((next) => {
      if (active) {
        setViewModel(next);
      }
    });
    return () => {
      active = false;
    };
  }, [documentId]);

  const { connection, detail } = viewModel;

  if (!detail) {
    return (
      <div className="space-y-8">
        <WorkspaceBackLink href="/materials">Voltar para materiais</WorkspaceBackLink>

        <WorkspaceSourcePanel
          eyebrow="pipeline"
          title="Item não encontrado"
          subtitle="Este conteúdo não está disponível nesta sessão. Consulte os dados de demonstração ou volte para materiais."
          connection={connection}
        />

        <Card className="min-w-0 border-[rgba(168,184,196,0.12)] bg-[rgba(255,255,255,0.02)]">
          <CardTitle className="text-[1.8rem] leading-[1.04]">Consulte os materiais disponíveis</CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            Entre para consultar o acompanhamento real deste material. Enquanto isso, a demonstração continua disponível.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <WorkspaceBackLink href="/materials">Voltar para materiais</WorkspaceBackLink>
          </div>
        </Card>
      </div>
    );
  }

  return (
    <div className="space-y-8">
      <WorkspaceBackLink href={`/materials/${documentId}`}>Voltar para o material</WorkspaceBackLink>

      <WorkspaceSourcePanel
        eyebrow="pipeline"
        title={detail.title}
        subtitle="Acompanhe a linha do processamento com foco em extração, segmentação e revisão."
        connection={connection}
      />

      <Card className="min-w-0">
        <div className="section-kicker">processamento</div>
        <CardTitle className="mt-5 break-words text-[1.8rem]">Linha do processamento</CardTitle>
        <div className="flex flex-wrap gap-2">
          <Badge className={sourceBadgeClass(detail.source)}>{sourceLabel(detail.source)}</Badge>
          <Badge className={productStatusClass(detail.extractionStatus)}>{detail.extractionStatus}</Badge>
          <Badge className={productStatusClass(detail.reviewState)}>{detail.reviewState}</Badge>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">seções</div>
            <p className="mt-2 text-sm text-ink">{detail.sectionsCount ?? 0}</p>
          </div>
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">trechos</div>
            <p className="mt-2 text-sm text-ink">{detail.chunksCount ?? 0}</p>
          </div>
        </div>
      </Card>

      <section className="space-y-4">
        {detail.steps.map((step, index) => (
          <Card key={step.id} className={`min-w-0 border ${toneClass(step.tone)}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div className="min-w-0">
                <div className="section-kicker">etapa {index + 1}</div>
                <CardTitle className="mt-4 break-words text-[1.6rem] leading-[1.02] sm:text-[1.8rem]">
                  {step.label}
                </CardTitle>
              </div>
              <Badge className={productStatusClass(step.statusLabel)}>{step.statusLabel}</Badge>
            </div>
            <p className="mt-4 text-sm leading-7 text-silver">{step.detail}</p>
          </Card>
        ))}
      </section>

      <Card className="min-w-0">
        <div className="section-kicker">notas</div>
        <CardTitle className="mt-5 break-words text-[1.8rem]">Limites desta tela</CardTitle>
        <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
          {detail.notes.map((note) => (
            <li key={note}>• {note}</li>
          ))}
          <li>• Nenhum texto bruto do documento é exibido nesta tela.</li>
        </ul>
      </Card>
    </div>
  );
}
