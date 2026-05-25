"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { PipelineDetailViewModel } from "@/lib/api/types";
import { buildMockPipelineDetail, loadPipelineDetail } from "@/lib/adapters/pipeline";
import { sourceLabel } from "@/lib/adapters/capabilities";
import { productStatusClass, sourceBadgeClass, WorkspaceSourcePanel } from "@/components/workspace/WorkspaceShared";

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

export function PipelineDetailReadOnlyClient({ documentId }: { documentId: string }) {
  const [viewModel, setViewModel] = useState<PipelineDetailViewModel>(buildMockPipelineDetail(documentId));

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

  return (
    <div className="space-y-8">
      <WorkspaceSourcePanel
        eyebrow="pipeline documental"
        title={viewModel.title}
        subtitle="Linha do tempo somente leitura para acompanhar extração, segmentação e etapa de revisão."
        connection={viewModel.connection}
      />

      <Card>
        <div className="flex flex-wrap gap-2">
          <Badge className={sourceBadgeClass(viewModel.source)}>{sourceLabel(viewModel.source)}</Badge>
          <Badge className={productStatusClass(viewModel.extractionStatus)}>{viewModel.extractionStatus}</Badge>
          <Badge className={productStatusClass(viewModel.reviewState)}>{viewModel.reviewState}</Badge>
        </div>
        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">seções</div>
            <p className="mt-2 text-sm text-ink">{viewModel.sectionsCount ?? 0}</p>
          </div>
          <div>
            <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">trechos</div>
            <p className="mt-2 text-sm text-ink">{viewModel.chunksCount ?? 0}</p>
          </div>
        </div>
      </Card>

      <section className="space-y-4">
        {viewModel.steps.map((step) => (
          <Card key={step.id} className={`border ${toneClass(step.tone)}`}>
            <div className="flex flex-wrap items-center justify-between gap-3">
              <div>
                <div className="section-kicker">{step.label}</div>
                <CardTitle className="mt-4 text-[1.8rem]">{step.statusLabel}</CardTitle>
              </div>
              <Badge className={productStatusClass(step.statusLabel)}>{step.statusLabel}</Badge>
            </div>
            <p className="mt-4 text-sm leading-7 text-silver">{step.detail}</p>
          </Card>
        ))}
      </section>

      <Card>
        <div className="section-kicker">notas</div>
        <CardTitle className="mt-5 text-[1.8rem]">Limites de exibição</CardTitle>
        <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
          {viewModel.notes.map((note) => (
            <li key={note}>• {note}</li>
          ))}
          <li>• Nenhum texto bruto do documento é exibido nesta linha do tempo.</li>
        </ul>
      </Card>
    </div>
  );
}
