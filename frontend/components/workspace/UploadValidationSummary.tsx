"use client";

import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import type { AcceptedUploadType, UploadEntryState, UploadValidationState } from "@/lib/api/types";
import { productStatusClass } from "@/components/workspace/WorkspaceShared";

function entryStateLabel(state: UploadEntryState): string {
  switch (state) {
    case "sending":
      return "Enviando";
    case "received":
      return "Material recebido para validação";
    case "failed":
      return "Falha controlada";
    case "mock_only":
      return "Modo de demonstração";
    case "endpoint_unavailable":
      return "Configuração necessária";
    case "ready_to_send":
      return "Pronto para envio";
    default:
      return "Aguardando validação";
  }
}

export function UploadValidationSummary({
  acceptedTypes,
  validationState,
  entryState,
  validationMessage,
  confirmationChecked,
  modeLabel
}: {
  acceptedTypes: AcceptedUploadType[];
  validationState: UploadValidationState;
  entryState: UploadEntryState;
  validationMessage: string;
  confirmationChecked: boolean;
  modeLabel: string;
}) {
  return (
    <div className="grid gap-4 xl:grid-cols-[1.05fr_0.95fr]">
      <Card>
        <div className="section-kicker">tipos aceitos</div>
        <CardTitle className="mt-5 text-[1.8rem]">Validação inicial</CardTitle>
        <div className="mt-5 space-y-3">
          {acceptedTypes.map((item) => (
            <div
              key={item.id}
              className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4"
            >
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="break-words text-sm text-ink">{item.label}</p>
                  <p className="mt-2 text-sm leading-7 text-silver">{item.extensions.join(", ")}</p>
                </div>
                {item.note ? (
                  <Badge className={productStatusClass(item.note)}>{item.note}</Badge>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <div className="section-kicker">estado</div>
        <CardTitle className="mt-5 text-[1.8rem]">Revisão antes do envio</CardTitle>
        <div className="mt-5 flex flex-wrap gap-2">
          <Badge className={productStatusClass(entryStateLabel(entryState))}>{entryStateLabel(entryState)}</Badge>
          <Badge className="border-[rgba(168,184,196,0.16)] bg-[rgba(168,184,196,0.08)] text-silver">
            {modeLabel}
          </Badge>
          <Badge className={productStatusClass(validationMessage)}>{validationMessage}</Badge>
        </div>
        <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
          <li>• PDFs escaneados podem exigir OCR e revisão manual.</li>
          <li>• OCR está em validação e pode não estar disponível para todos os arquivos.</li>
          <li>• Não prometa suporte completo a PDF escaneado.</li>
          <li>• Para envio real, use PDF, TXT ou Markdown (.md).</li>
          {validationState === "missing_confirmation" && !confirmationChecked ? (
            <li>• Confirme o envio antes de liberar a ação.</li>
          ) : null}
        </ul>
      </Card>
    </div>
  );
}
