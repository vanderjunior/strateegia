"use client";

import { useEffect, useState } from "react";

import { Card, CardTitle } from "@/components/ui/card";
import type { MaterialsWorkspaceViewModel } from "@/lib/api/types";
import { buildMockMaterialsWorkspaceViewModel, loadMaterialsWorkspaceViewModel } from "@/lib/adapters/materials";
import { getUserFacingCapability } from "@/lib/product/product-language";
import {
  productStatusClass,
  sourceBadgeClass,
  WorkspaceLink,
  WorkspaceSourcePanel,
  WorkspaceSummaryGrid
} from "@/components/workspace/WorkspaceShared";
import { Badge } from "@/components/ui/badge";
import { sourceLabel } from "@/lib/adapters/capabilities";

export function MaterialsReadOnlyClient() {
  const [viewModel, setViewModel] = useState<MaterialsWorkspaceViewModel>(buildMockMaterialsWorkspaceViewModel());

  useEffect(() => {
    let active = true;
    void loadMaterialsWorkspaceViewModel().then((next) => {
      if (active) {
        setViewModel(next);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  const pipelineCopy = getUserFacingCapability("document_pipeline", "student");
  const ocrCopy = getUserFacingCapability("ocr_adapter", "student");

  return (
    <div className="space-y-8">
      <WorkspaceSourcePanel
        eyebrow="materiais"
        title="Materiais"
        subtitle="Acompanhe materiais enviados, leitura de texto e necessidade de revisão."
        connection={viewModel.connection}
      />

      <WorkspaceSummaryGrid items={viewModel.summary} />

      <section className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
        {viewModel.items.map((item) => (
          <Card key={item.id} className="flex h-full flex-col">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="max-w-[18rem]">
                <div className="section-kicker">material</div>
                <CardTitle className="mt-4 text-[1.8rem]">{item.title}</CardTitle>
              </div>
              <Badge className={sourceBadgeClass(item.source)}>{sourceLabel(item.source)}</Badge>
            </div>
            <div className="mt-5 flex flex-wrap gap-2">
              <Badge className={productStatusClass(item.processingStatus)}>{item.processingStatus}</Badge>
              <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
                {item.typeLabel}
              </Badge>
              <Badge className={productStatusClass(item.reviewState)}>{item.reviewState}</Badge>
            </div>
            <div className="mt-5 grid gap-3 sm:grid-cols-2">
              <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                  extração
                </div>
                <p className="mt-2 text-sm text-ink">{item.extractionStatus}</p>
              </div>
              <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                  estrutura
                </div>
                <p className="mt-2 text-sm text-ink">
                  {item.sectionsCount ?? 0} seções · {item.chunksCount ?? 0} trechos
                </p>
              </div>
            </div>
            <p className="mt-5 text-sm leading-7 text-silver">
              {pipelineCopy?.description ?? "O material é lido, dividido em trechos e preparado para revisão."}
            </p>
            <p className="mt-2 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
              {item.processingStatus === "OCR necessário"
                ? (ocrCopy?.description ?? "A leitura de PDFs escaneados está em validação e pode exigir revisão.")
                : `Gaps relacionados: ${item.relatedGaps}.`}
            </p>
            <div className="mt-6 flex items-center justify-between gap-4">
              <span className="text-xs uppercase tracking-[0.18em] text-[rgba(232,238,242,0.42)]">
                Envio de material será tratado em etapa controlada.
              </span>
              <WorkspaceLink href={`/materials/${item.id}`}>Ver material</WorkspaceLink>
            </div>
          </Card>
        ))}
      </section>
    </div>
  );
}
