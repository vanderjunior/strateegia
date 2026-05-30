"use client";

import { useEffect, useState } from "react";
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
import { MATERIAL_TYPE_OPTIONS, materialTypeLabel, uploadMaterialFile } from "@/lib/api/documents";
import { getApiConfig } from "@/lib/api/config";
import { sourceLabel } from "@/lib/adapters/capabilities";
import { buildDefaultSessionState, loadSessionState } from "@/lib/adapters/session";
import type {
  BackendConnectionInfo,
  UploadEntryState,
  MaterialType,
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
      detail: "Você pode conhecer o fluxo sem enviar arquivos reais."
    };
  }
  if (!config.baseUrl) {
    return {
      state: "unsupported",
      source: "unsupported",
      title: "Envio indisponível",
      detail: "O envio real não está disponível agora."
    };
  }
  return {
    state: "connected",
    source: "backend",
    title: "Envio disponível",
    detail: "Envie um PDF, TXT ou Markdown para guardar na sua biblioteca."
  };
}

function buildMockResult(file: File, materialType: MaterialType): UploadMaterialResult {
  const scanned = isScannedPdfFile(file);
  return {
    documentId: `demo-${file.name.replace(/[^a-z0-9]+/gi, "-").toLowerCase()}`,
    filename: file.name,
    originalFilename: file.name,
    contentType: file.type || "",
    materialType,
    materialTypeLabel: materialTypeLabel(materialType),
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
  const [sessionState, setSessionState] = useState(() => buildDefaultSessionState());
  const [sessionReady, setSessionReady] = useState(() => buildDefaultSessionState().status === "authenticated");
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [selectedIntentId, setSelectedIntentId] = useState<MaterialType | "">("");
  const [confirmationChecked, setConfirmationChecked] = useState(false);
  const [validationState, setValidationState] = useState<UploadValidationState>("idle");
  const [entryState, setEntryState] = useState<UploadEntryState>(
    connection.source === "backend" ? "idle" : connection.source === "mock" ? "mock_only" : "endpoint_unavailable"
  );
  const [validationMessage, setValidationMessage] = useState("Aguardando envio");
  const [result, setResult] = useState<UploadMaterialResult | null>(null);

  useEffect(() => {
    let active = true;
    void loadSessionState({ refresh: true }).then((nextState) => {
      if (active) {
        setSessionState(nextState);
        setSessionReady(true);
      }
    });
    return () => {
      active = false;
    };
  }, []);

  function handleFileChange(file: File | null) {
    setSelectedFile(file);
    setResult(null);
    setConfirmationChecked(false);

    if (!file) {
      setValidationState("idle");
      setEntryState(connection.source === "backend" ? "idle" : connection.source === "mock" ? "mock_only" : "endpoint_unavailable");
      setValidationMessage("Aguardando envio");
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
    if (!selectedIntentId) {
      setValidationState("missing_confirmation");
      setValidationMessage("Classificação necessária.");
      return;
    }

    if (connection.source !== "backend") {
      setEntryState(connection.source === "mock" ? "mock_only" : "endpoint_unavailable");
      setResult(buildMockResult(selectedFile, selectedIntentId));
      setValidationMessage(
        connection.source === "mock"
          ? "Modo de demonstração: nenhum arquivo foi enviado."
          : "Envio real indisponível neste ambiente."
      );
      return;
    }

    setEntryState("sending");
    setValidationMessage("Enviando arquivo.");
    const uploadResult = await uploadMaterialFile(selectedFile, selectedIntentId);

    if (!uploadResult.ok) {
      if (uploadResult.error.code === "endpoint_unavailable") {
        setEntryState("endpoint_unavailable");
        setValidationMessage("Envio real indisponível neste ambiente.");
        return;
      }
      if (uploadResult.error.code === "auth_required") {
        setEntryState("failed");
        setValidationMessage("Sessão necessária para enviar material.");
        return;
      }
      if (uploadResult.error.code === "api_base_missing") {
        setEntryState("endpoint_unavailable");
        setValidationMessage("Envio real indisponível neste ambiente.");
        return;
      }
      if (uploadResult.error.code === "mock_mode") {
        setEntryState("mock_only");
        setValidationMessage("Modo de demonstração: nenhum arquivo foi enviado.");
        setResult(buildMockResult(selectedFile, selectedIntentId));
        return;
      }
      setEntryState("failed");
      setValidationMessage(uploadResult.error.message);
      return;
    }

    setEntryState("received");
    setResult(uploadResult.data);
    setValidationMessage("Arquivo recebido.");
  }

  const uploadBlocked = connection.source === "backend" && (!sessionReady || sessionState.status !== "authenticated");
  const modeLabel =
    connection.source === "backend"
      ? "Envio seguro"
      : connection.source === "mock"
        ? "Dados de demonstração"
        : "Envio indisponível";
  const submitLabel =
    connection.source === "backend"
      ? "Enviar arquivo"
      : connection.source === "mock"
        ? "Simular envio em demonstração"
        : "Configuração necessária";

  const buttonDisabled =
    uploadBlocked ||
    !selectedFile ||
    validationState === "invalid_size" ||
    validationState === "invalid_type" ||
    entryState === "sending" ||
    connection.source === "unsupported" ||
    !confirmationChecked ||
    !selectedIntentId;
  const showAuthGuidance = validationMessage === "Sessão necessária para enviar material.";
  const showOfflineGuidance = validationMessage === "Não foi possível carregar os dados agora.";
  const showMissingBaseGuidance = validationMessage === "Envio real indisponível neste ambiente.";
  const showLocalSetup = showOfflineGuidance || showMissingBaseGuidance;
  const returnedExtension = result ? extensionForFileName(result.filename) || "sem extensão" : "";
  const selectedIntentLabel =
    selectedIntentId ? materialTypeLabel(selectedIntentId) : "";

  return (
    <div className="space-y-8">
      <WorkspaceBackLink href="/materials">Voltar para materiais</WorkspaceBackLink>

      {uploadBlocked ? (
        <Card className="border-[rgba(201,169,110,0.16)] bg-[rgba(255,255,255,0.02)]">
          <div className="section-kicker">entrar</div>
          <CardTitle className="mt-5 break-words text-[1.9rem] leading-[1.04]">
            {sessionReady ? "Entre para enviar materiais." : "Preparando envio."}
          </CardTitle>
          <p className="mt-4 max-w-2xl text-sm leading-7 text-silver">
            {sessionReady
              ? "O envio fica disponível depois que você entra na sua conta."
              : "Estamos verificando se você já entrou na aplicação."}
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            {sessionReady ? (
              <Link
                href="/login"
                className="inline-flex items-center justify-center rounded-xl border border-[rgba(201,169,110,0.24)] bg-[rgba(201,169,110,0.10)] px-5 py-3 text-sm text-ink transition hover:bg-[rgba(201,169,110,0.16)]"
              >
                Entrar
              </Link>
            ) : null}
            <Link
              href="/materials"
              className="inline-flex items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-transparent px-5 py-3 text-sm text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
            >
              Voltar para materiais
            </Link>
          </div>
        </Card>
      ) : (
        <>
      <WorkspaceSourcePanel
        eyebrow="enviar material"
        title="Enviar material"
        subtitle="Adicione um PDF, TXT ou Markdown (.md) para organizar seus materiais de estudo."
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
          <CardTitle className="mt-5 break-words text-[1.8rem]">Antes do envio</CardTitle>
          <div className="mt-5 rounded-2xl border border-[rgba(201,169,110,0.14)] bg-[rgba(201,169,110,0.06)] p-4">
            <fieldset>
              <legend className="break-words text-sm font-medium text-ink">O que você está enviando?</legend>
              <p className="mt-2 text-sm leading-7 text-silver">
                Isso ajuda a organizar o caminho de estudo. A classificação pode ser ajustada depois.
              </p>
              <div className="mt-4 grid gap-2 sm:grid-cols-2">
                {MATERIAL_TYPE_OPTIONS.map((option) => (
                  <label
                    key={option.id}
                    className="flex items-center gap-3 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] px-4 py-3 text-sm text-silver"
                  >
                    <input
                      type="radio"
                      name="upload-intent"
                      value={option.id}
                      checked={selectedIntentId === option.id}
                      onChange={() => {
                        setSelectedIntentId(option.id);
                        if (selectedFile && confirmationChecked) {
                          setValidationState("valid");
                          setValidationMessage("Arquivo pronto para validação.");
                        }
                      }}
                    />
                    <span>{option.label}</span>
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
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
                  } else if (selectedFile && selectedIntentId) {
                    setValidationState("valid");
                    setValidationMessage("Arquivo pronto para validação.");
                  } else if (selectedFile) {
                    setValidationState("missing_confirmation");
                    setValidationMessage("Classificação necessária.");
                  }
                }}
              />
              <span>Confirmo que este material pode ser enviado para validação.</span>
            </label>
          </div>
          <div className="mt-5 flex flex-wrap gap-2">
            <Badge className={productStatusClass(validationMessage)}>{validationMessage}</Badge>
            {selectedIntentLabel ? <Badge>{selectedIntentLabel}</Badge> : null}
          </div>
          <p className="mt-5 text-sm leading-7 text-silver">
            Esta etapa não gera questões, não gera simulados e não altera seu progresso.
          </p>
          {showAuthGuidance ? (
            <p className="mt-3 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
              Entre na aplicação para enviar materiais reais. Exemplos podem aparecer sem liberar envio.
            </p>
          ) : null}
          {showOfflineGuidance ? (
            <p className="mt-3 text-sm leading-7 text-[rgba(232,238,242,0.68)]">
              O envio real depende do serviço de materiais disponível.
            </p>
          ) : null}
          {showLocalSetup ? (
            <div className="mt-4 rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">envio indisponível</div>
              <ul className="mt-3 space-y-2 text-sm leading-7 text-silver">
                <li>• O envio real depende do serviço de materiais disponível.</li>
                <li>• A demonstração continua acessível sem persistir arquivos.</li>
                <li>• A confirmação continua obrigatória antes de qualquer envio.</li>
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
            <Badge>{result.materialTypeLabel}</Badge>
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
              <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">referência</div>
              <p className="mt-3 break-words text-sm text-ink">{result.documentId}</p>
            </div>
            {result.materialTypeLabel ? (
              <div className="rounded-2xl border border-[rgba(168,184,196,0.10)] bg-[rgba(255,255,255,0.03)] p-4">
                <div className="font-mono text-[10px] uppercase tracking-[0.18em] text-silver">classificação escolhida</div>
                <p className="mt-3 text-sm text-ink">{result.materialTypeLabel}</p>
              </div>
            ) : null}
          </div>
          <ul className="mt-5 space-y-3 text-sm leading-7 text-silver">
            <li>• Próximo estado esperado: Texto extraído ou aguardando validação.</li>
            <li>• Se for PDF digitalizado, o arquivo pode seguir como OCR necessário.</li>
            <li>• Após validação, o material pode ficar pronto para revisão.</li>
            <li>• A classificação foi enviada como metadado do material; ela não aciona processamento automático.</li>
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
                  Ver detalhes
                </Link>
                <Link
                  href={`/pipeline/${result.documentId}`}
                  className="inline-flex items-center justify-center rounded-xl border border-[rgba(168,184,196,0.12)] bg-transparent px-5 py-3 text-sm text-silver transition hover:border-[rgba(201,169,110,0.24)] hover:text-ink"
                >
                  Ver acompanhamento
                </Link>
              </>
            ) : null}
          </div>
        </Card>
      ) : null}
        </>
      )}
    </div>
  );
}
