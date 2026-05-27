"use client";

import { useEffect, useState } from "react";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { BackendConnectionInfo, MaterialDetail } from "@/lib/api/types";
import { buildMockMaterialDetail, loadMaterialDetail } from "@/lib/adapters/materials";
import { sourceLabel } from "@/lib/adapters/capabilities";
import {
  productStatusClass,
  sourceBadgeClass,
  WorkspaceBackLink,
  WorkspaceLink,
  WorkspaceSourcePanel
} from "@/components/workspace/WorkspaceShared";

function buildFallback(materialId: string): { connection: BackendConnectionInfo; detail: MaterialDetail } {
  return {
    connection: {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "Consulta local exibida até existir leitura segura do backend para este material."
    },
    detail: buildMockMaterialDetail(materialId)
  };
}

export function MaterialDetailReadOnlyClient({ materialId }: { materialId: string }) {
  const [viewModel, setViewModel] = useState<{ connection: BackendConnectionInfo; detail: MaterialDetail }>(
    buildFallback(materialId)
  );

  useEffect(() => {
    let active = true;
    void loadMaterialDetail(materialId).then((next) => {
      if (active) {
        setViewModel(next);
      }
    });
    return () => {
      active = false;
    };
  }, [materialId]);

  const { connection, detail } = viewModel;

  return (
    <div className="space-y-8">
      <WorkspaceBackLink href="/materials">Voltar para materiais</WorkspaceBackLink>

      <WorkspaceSourcePanel
        eyebrow="material"
        title={detail.title}
        subtitle="Consulte status do material, estrutura segura e avisos de revisão sem expor conteúdo bruto."
        connection={connection}
      />

      <section className="grid gap-4 xl:grid-cols-[1.15fr_0.85fr]">
        <Card className="min-w-0">
          <div className="flex flex-wrap gap-2">
            <Badge className={sourceBadgeClass(detail.source)}>{sourceLabel(detail.source)}</Badge>
            <Badge className={productStatusClass(detail.processingStatus)}>{detail.processingStatus}</Badge>
            <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
              {detail.typeLabel}
            </Badge>
            <Badge className={productStatusClass(detail.reviewState)}>{detail.reviewState}</Badge>
          </div>
          <div className="mt-6 grid gap-4 md:grid-cols-3">
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                extração
              </div>
              <p className="mt-2 text-sm text-ink">{detail.extractionStatus}</p>
            </div>
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                seções
              </div>
              <p className="mt-2 text-sm text-ink">{detail.sectionsCount ?? 0}</p>
            </div>
            <div>
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">
                trechos
              </div>
              <p className="mt-2 text-sm text-ink">{detail.chunksCount ?? 0}</p>
            </div>
          </div>
          <p className="mt-6 text-sm leading-7 text-silver">{detail.sourceNote}</p>
        </Card>

        <Card className="min-w-0">
          <div className="section-kicker">avisos</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">Revisão necessária</CardTitle>
          {detail.warnings.length ? (
            <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
              {detail.warnings.map((warning) => (
                <li key={warning} className="break-words">
                  • {warning}
                </li>
              ))}
            </ul>
          ) : (
            <p className="mt-5 text-sm leading-7 text-silver">Nenhum aviso adicional por enquanto.</p>
          )}
          <div className="mt-6">
            <WorkspaceLink href={`/pipeline/${materialId}`}>Ver pipeline</WorkspaceLink>
          </div>
        </Card>
      </section>

      <section className="grid gap-4 lg:grid-cols-2">
        <Card className="min-w-0">
          <div className="section-kicker">prévia segura</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">Seções identificadas</CardTitle>
          {detail.sectionPreviews.length ? (
            <div className="mt-5 space-y-3">
              {detail.sectionPreviews.map((section) => (
                <div
                  key={section.id}
                  className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
                >
                  <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
                    <p className="break-words text-sm text-ink">{section.title}</p>
                    <span className="font-mono text-[10px] uppercase tracking-[0.16em] text-silver">
                      {section.chunkRangeLabel}
                    </span>
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <p className="mt-5 text-sm leading-7 text-silver">Nenhuma seção para exibir ainda.</p>
          )}
        </Card>

        <Card className="min-w-0">
          <div className="section-kicker">limites</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">O que esta tela mostra</CardTitle>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            <li>• Títulos de seções e contagens seguras.</li>
            <li>• Status de leitura, OCR e revisão.</li>
            <li>• Nenhum texto bruto do documento é exibido.</li>
            <li>• Nenhum conteúdo completo de OCR ou imagem bruta é exibido.</li>
          </ul>
        </Card>
      </section>
    </div>
  );
}
