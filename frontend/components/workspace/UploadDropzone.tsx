"use client";

import { Card, CardTitle } from "@/components/ui/card";

function formatBytes(bytes: number): string {
  if (bytes < 1024 * 1024) {
    return `${Math.round(bytes / 1024)} KB`;
  }
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

export function UploadDropzone({
  selectedFile,
  accept,
  disabled,
  onChange
}: {
  selectedFile: File | null;
  accept: string;
  disabled?: boolean;
  onChange: (file: File | null) => void;
}) {
  return (
    <Card className="border-[rgba(201,169,110,0.14)] bg-[rgba(255,255,255,0.02)]">
      <div className="section-kicker">arquivo</div>
      <CardTitle className="mt-5 text-[1.8rem]">Selecione um material</CardTitle>
      <label className="mt-5 flex cursor-pointer flex-col rounded-[24px] border border-dashed border-[rgba(168,184,196,0.18)] bg-[rgba(255,255,255,0.02)] p-6 transition hover:border-[rgba(201,169,110,0.24)] hover:bg-[rgba(255,255,255,0.04)]">
        <span className="text-sm text-ink">Escolha um arquivo PDF, TXT ou Markdown (.md)</span>
        <span className="mt-2 text-sm leading-7 text-silver">
          PDFs escaneados podem exigir OCR em validação e revisão manual.
        </span>
        <input
          type="file"
          accept={accept}
          disabled={disabled}
          className="sr-only"
          onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        />
      </label>

      {selectedFile ? (
        <div className="mt-5 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
          <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">arquivo selecionado</div>
          <p className="mt-3 break-words text-sm text-ink">{selectedFile.name}</p>
          <p className="mt-2 text-sm text-silver">{formatBytes(selectedFile.size)}</p>
        </div>
      ) : null}
    </Card>
  );
}
