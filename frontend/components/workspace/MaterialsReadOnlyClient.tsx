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
import Link from "next/link";

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

      <Card className="border-[rgba(201,169,110,0.14)] bg-[rgba(255,255,255,0.02)]">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div className="max-w-2xl">
            <div className="section-kicker">entrada controlada</div>
            <CardTitle className="mt-4 text-[1.8rem]">Enviar material</CardTitle>
            <p className="mt-3 text-sm leading-7 text-silver">
              Adicione um PDF, TXT ou Markdown para validação inicial. Envio e processamento ocorrem em etapas controladas.
            </p>
          </div>
          <div className="flex flex-wrap gap-3">
            <Link
              href="/materials/upload"
              className="inline-flex items-center justify-center rounded-xl border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.10)] px-5 py-3 text-sm text-ink transition hover:-translate-y-0.5 hover:bg-[rgba(201,169,110,0.16)]"
            >
              Enviar material
            </Link>
          </div>
        </div>
      </Card>

      <WorkspaceSummaryGrid items={viewModel.summary} />

      {viewModel.items.length ? (
        <section className="grid gap-4 lg:grid-cols-2 xl:grid-cols-3">
          {viewModel.items.map((item) => (
          <Card key={item.id} className="flex h-full flex-col">
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="min-w-0 max-w-[18rem]">
                <div className="section-kicker">material</div>
                <CardTitle className="mt-4 break-words text-[1.55rem] leading-[1.02] sm:text-[1.8rem]">
                  {item.title}
                </CardTitle>
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
              <div className="min-w-0 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                  extração
                </div>
                <p className="mt-2 text-sm text-ink">{item.extractionStatus}</p>
              </div>
              <div className="min-w-0 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                  estrutura
                </div>
                <p className="mt-2 break-words text-sm text-ink">
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
            <div className="mt-6 flex flex-col items-start justify-between gap-4 sm:flex-row sm:items-center">
              <span className="max-w-[18rem] text-xs uppercase tracking-[0.18em] text-[rgba(232,238,242,0.42)]">
                Envio e processamento serão tratados em uma etapa controlada.
              </span>
              <WorkspaceLink href={`/materials/${item.id}`}>Ver material</WorkspaceLink>
            </div>
          </Card>
          ))}
        </section>
      ) : (
        <Card>
          <div className="section-kicker">materiais</div>
          <CardTitle className="mt-5 text-[1.8rem]">Nenhum material para exibir ainda</CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            O painel continua disponível em modo somente leitura. Envio e processamento serão tratados em uma etapa controlada.
          </p>
        </Card>
      )}
    </div>
  );
}
