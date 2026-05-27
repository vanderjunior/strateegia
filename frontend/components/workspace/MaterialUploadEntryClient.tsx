"use client";

import { useState } from "react";
import Link from "next/link";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardTitle } from "@/components/ui/card";
import {
  ACCEPT_STRING,
  acceptedUploadTypes,
  extensionForFileName,
  formatUploadFileSize,
  isScannedPdfFile,
  validateUploadFile
} from "@/components/workspace/upload-validation";
import { uploadMaterialFile } from "@/lib/api/documents";
import { getApiConfig } from "@/lib/api/config";
import { sourceLabel } from "@/lib/adapters/capabilities";
import type {
  BackendConnectionInfo,
  UploadEntryState,
  UploadMaterialResult,
  UploadValidationState
} from "@/lib/api/types";
import {
  productStatusClass,
  sourceBadgeClass,
  WorkspaceBackLink,
  WorkspaceSourcePanel
} from "@/components/workspace/WorkspaceShared";
import { UploadDropzone } from "@/components/workspace/UploadDropzone";
import { UploadValidationSummary } from "@/components/workspace/UploadValidationSummary";

function buildConnection(): BackendConnectionInfo {
  const config = getApiConfig();
  if (config.forceMock) {
    return {
      state: "mock",
      source: "mock",
      title: "Dados de demonstração",
      detail: "NEXT_PUBLIC_USE_MOCK_API=true mantém este fluxo em demonstração. Nenhum arquivo será enviado."
    };
  }
  if (!config.baseUrl) {
    return {
      state: "unsupported",
      source: "unsupported",
      title: "Painel em validação",
      detail: "URL do backend não configurada para envio real."
    };
  }
  return {
    state: "connected",
    source: "backend",
    title: "Backend disponível",
    detail: "O envio usa o endpoint existente de materiais, com validação local e confirmação obrigatória."
  };
}

function buildMockResult(file: File): UploadMaterialResult {
  const scanned = isScannedPdfFile(file);
  return {
    documentId: `demo-${file.name.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`,
    filename: file.name,
    originalFilename: file.name,
    contentType: file.type || "",
    sizeBytes: file.size,
    processingStatus: "Material recebido para validação",
    extractionStatus: scanned ? "OCR necessário" : "Texto extraído",
    reviewState: scanned ? "OCR em validação" : "Pronto para revisão",
    source: "mock",
    demoOnly: true
  };
}

export function MaterialUploadEntryClient() {
  const connection = buildConnection();
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [confirmationChecked, setConfirmationChecked] = useState(false);
  const [validationState, setValidationState] = useState<UploadValidationState>("idle");
  const [entryState, setEntryState] = useState<UploadEntryState>(
    connection.source === "backend" ? "idle" : connection.source === "mock" ? "mock_only" : "endpoint_unavailable"
  );
  const [validationMessage, setValidationMessage] = useState("Aguardando validação");
  const [result, setResult] = useState<UploadMaterialResult | null>(null);

  function handleFileChange(file: File | null) {
    setSelectedFile(file);
    setResult(null);
    setConfirmationChecked(false);

    if (!file) {
      setValidationState("idle");
      setEntryState(connection.source === "backend" ? "idle" : connection.source === "mock" ? "mock_only" : "endpoint_unavailable");
      setValidationMessage("Aguardando validação");
      return;
    }

    setValidationState("validating");
    const outcome = validateUploadFile(file);
    if (!outcome.valid) {
      setValidationState(outcome.message.includes("limite") ? "invalid_size" : "invalid_type");
      setEntryState("failed");
      setValidationMessage(outcome.message);
      return;
    }

    setValidationState("valid");
    setEntryState(connection.source === "backend" ? "ready_to_send" : connection.source === "mock" ? "mock_only" : "endpoint_unavailable");
    setValidationMessage(outcome.message);
  }

  async function handleUpload() {
    if (!selectedFile) {
      return;
    }
    if (!confirmationChecked) {
      setValidationState("missing_confirmation");
      setValidationMessage("Confirmação necessária.");
      return;
    }

    if (connection.source !== "backend") {
      setEntryState(connection.source === "mock" ? "mock_only" : "endpoint_unavailable");
      setResult(buildMockResult(selectedFile));
      setValidationMessage(
        connection.source === "mock"
          ? "Modo de demonstração: nenhum arquivo foi enviado."
          : "URL do backend não configurada para envio real."
      );
      return;
    }

    setEntryState("sending");
    setValidationMessage("Enviando arquivo para validação.");
    const uploadResult = await uploadMaterialFile(selectedFile);

    if (!uploadResult.ok) {
      if (uploadResult.error.code === "endpoint_unavailable") {
        setEntryState("endpoint_unavailable");
        setValidationMessage("Endpoint de envio indisponível neste ambiente.");
        return;
      }
      if (uploadResult.error.code === "auth_required") {
        setEntryState("failed");
        setValidationMessage("Sessão necessária para enviar material.");
        return;
      }
      if (uploadResult.error.code === "api_base_missing") {
        setEntryState("endpoint_unavailable");
        setValidationMessage("URL do backend não configurada para envio real.");
        return;
      }
      if (uploadResult.error.code === "mock_mode") {
        setEntryState("mock_only");
        setValidationMessage("Modo de demonstração: nenhum arquivo foi enviado.");
        setResult(buildMockResult(selectedFile));
        return;
      }
      setEntryState("failed");
      setValidationMessage(uploadResult.error.message);
      return;
    }

    setEntryState("received");
    setResult(uploadResult.data);
    setValidationMessage("Material recebido para validação.");
  }

  const modeLabel =
    connection.source === "backend"
      ? "Upload controlado"
      : connection.source === "mock"
        ? "Dados de demonstração"
        : "Painel em validação";
  const submitLabel =
    connection.source === "backend"
      ? "Enviar para validação"
      : connection.source === "mock"
        ? "Simular envio em demonstração"
        : "Configuração necessária";

  const buttonDisabled =
    !selectedFile ||
    validationState === "invalid_size" ||
    validationState === "invalid_type" ||
    entryState === "sending" ||
    connection.source === "unsupported" ||
    !confirmationChecked;
  const showAuthGuidance = validationMessage === "Sessão necessária para enviar material.";
  const showOfflineGuidance = validationMessage === "Não foi possível conectar ao backend.";
  const showMissingBaseGuidance = validationMessage === "URL do backend não configurada para envio real.";
  const showLocalSetup = showOfflineGuidance || showMissingBaseGuidance;
  const returnedExtension = result ? extensionForFileName(result.filename) || "sem extensão" : "";

  return (
    <div className="space-y-8">
      <WorkspaceBackLink href="/materials">Voltar para materiais</WorkspaceBackLink>

      <WorkspaceSourcePanel
        eyebrow="enviar material"
        title="Enviar material"
        subtitle="Adicione um PDF, TXT ou Markdown (.md) para validação inicial. Esta etapa segue controlada e sujeita a revisão."
        connection={connection}
      />

      <UploadValidationSummary
        acceptedTypes={acceptedUploadTypes}
        validationState={validationState}
        entryState={entryState}
        validationMessage={validationMessage}
        confirmationChecked={confirmationChecked}
        modeLabel={modeLabel}
      />

      <section className="grid gap-4 xl:grid-cols-[1.1fr_0.9fr]">
        <UploadDropzone
          selectedFile={selectedFile}
          accept={ACCEPT_STRING}
          disabled={entryState === "sending"}
          onChange={handleFileChange}
        />

        <Card className="min-w-0">
          <div className="section-kicker">confirmação</div>
          <CardTitle className="mt-5 break-words text-[1.8rem]">Revisão antes do envio</CardTitle>
          <div className="mt-5 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
            <label className="flex items-start gap-3 text-sm leading-7 text-silver">
              <input
                type="checkbox"
                className="mt-1 h-4 w-4 rounded border-[rgba(168,184,196,0.26)] bg-transparent"
                checked={confirmationChecked}
                onChange={(event) => {
                  setConfirmationChecked(event.target.checked);
                  if (!event.target.checked && selectedFile) {
                    setValidationState("missing_confirmation");
                    setValidationMessage("Confirmação necessária.");
                  } else if (selectedFile) {
                    setValidationState("valid");
                    setValidationMessage("Arquivo pronto para validação.");
                  }
                }}
              />
              <span>Confirmo que este material pode ser enviado para validação.</span>
            </label>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge className={sourceBadgeClass(connection.source)}>{modeLabel}</Badge>
            <Badge className={productStatusClass(validationMessage)}>{validationMessage}</Badge>
          </div>
          <p className="mt-5 text-sm leading-7 text-silver">
            Esta etapa não gera questões, não gera simulados e não altera seu progresso.
          </p>
          {showAuthGuidance ? (
            <p className="mt-3 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
              Entre na aplicação para enviar materiais reais. O modo demonstração continua disponível sem envio.
            </p>
          ) : null}
          {showOfflineGuidance ? (
            <p className="mt-3 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
              Verifique se o backend está rodando em NEXT_PUBLIC_API_BASE_URL.
            </p>
          ) : null}
          {showLocalSetup ? (
            <div className="mt-4 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">ambiente local</div>
              <ul className="mt-3 space-y-2 text-sm leading-7 text-silver">
                <li>• Backend: http://127.0.0.1:8000</li>
                <li>• NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8000</li>
                <li>• NEXT_PUBLIC_USE_MOCK_API=false</li>
              </ul>
            </div>
          ) : null}
          <div className="mt-6 flex flex-wrap gap-3">
            <Button
              variant="secondary"
              disabled={buttonDisabled}
              aria-disabled={buttonDisabled}
              onClick={() => {
                void handleUpload();
              }}
            >
              {submitLabel}
            </Button>
            <Link
              href="/materials"
              className="inline-flex items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-transparent px-5 py-3 text-sm text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
            >
              Voltar para materiais
            </Link>
          </div>
        </Card>
      </section>

      {result ? (
        <Card className="border-[rgba(201,169,110,0.14)] bg-[rgba(255,255,255,0.02)]">
          <div className="flex flex-wrap items-start justify-between gap-3">
            <div className="min-w-0">
              <div className="section-kicker">resultado</div>
              <CardTitle className="mt-5 break-words text-[1.8rem]">
                {result.demoOnly ? "Modo de demonstração: nenhum arquivo foi enviado." : "Material recebido para validação"}
              </CardTitle>
            </div>
            <Badge className={sourceBadgeClass(result.source)}>{sourceLabel(result.source)}</Badge>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge className={productStatusClass(result.processingStatus)}>{result.processingStatus}</Badge>
            <Badge className={productStatusClass(result.extractionStatus)}>{result.extractionStatus}</Badge>
            <Badge className={productStatusClass(result.reviewState)}>{result.reviewState}</Badge>
          </div>
          <div className="mt-5 grid gap-3 md:grid-cols-2 xl:grid-cols-4">
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">arquivo</div>
              <p className="mt-3 break-words text-sm text-ink">{result.filename}</p>
            </div>
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">tipo</div>
              <p className="mt-3 text-sm text-ink">{returnedExtension || result.contentType || "Arquivo enviado"}</p>
            </div>
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">tamanho</div>
              <p className="mt-3 text-sm text-ink">{formatUploadFileSize(result.sizeBytes)}</p>
            </div>
            <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">identificador</div>
              <p className="mt-3 break-words text-sm text-ink">{result.documentId}</p>
            </div>
          </div>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            <li>• Próximo estado esperado: Texto extraído ou aguardando validação.</li>
            <li>• Se for PDF digitalizado, o arquivo pode seguir como OCR necessário.</li>
            <li>• Após validação, o material pode ficar pronto para revisão.</li>
            {result.demoOnly ? (
              <li>• Modo de demonstração: nenhum arquivo foi persistido.</li>
            ) : (
              <li>• Este material foi recebido nesta sessão. A listagem real depende da sessão autenticada.</li>
            )}
          </ul>
          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              href="/materials"
              className="inline-flex items-center justify-center rounded-xl border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.10)] px-5 py-3 text-sm text-ink transition hover:-translate-y-0.5 hover:bg-[rgba(201,169,110,0.16)]"
            >
              Voltar para materiais
            </Link>
            {!result.demoOnly ? (
              <>
                <Link
                  href={`/materials/${result.documentId}`}
                  className="inline-flex items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-transparent px-5 py-3 text-sm text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
                >
                  Ver material
                </Link>
                <Link
                  href={`/pipeline/${result.documentId}`}
                  className="inline-flex items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-transparent px-5 py-3 text-sm text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
                >
                  Ver pipeline
                </Link>
              </>
            ) : null}
          </div>
        </Card>
      ) : null}
    </div>
  );
}
