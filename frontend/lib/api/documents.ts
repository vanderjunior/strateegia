import { getApiConfig } from "@/lib/api/config";
import { getJson } from "@/lib/api/client";
import { makeApiFailure } from "@/lib/api/errors";
import type { ApiResult, BackendDocumentSummary, UploadMaterialResult } from "@/lib/api/types";

export function fetchDocuments(): Promise<ApiResult<BackendDocumentSummary[]>> {
  return getJson<BackendDocumentSummary[]>("/api/documents");
}

export function fetchDocumentById(documentId: string): Promise<ApiResult<BackendDocumentSummary>> {
  return getJson<BackendDocumentSummary>(`/api/documents/${documentId}`);
}

interface BackendUploadedMaterialResponse {
  metadata: {
    document_id: string;
    filename: string;
    original_filename: string;
    content_type: string;
    size_bytes: number;
    status: string;
    extraction_status: string;
  };
}

function normalizeUploadResult(response: BackendUploadedMaterialResponse): UploadMaterialResult {
  const extractionStatus =
    response.metadata.extraction_status === "extracted"
      ? "Texto extraído"
      : response.metadata.extraction_status.includes("pending")
        ? "Aguardando validação"
        : response.metadata.extraction_status.includes("ocr")
          ? "OCR em validação"
          : "Aguardando validação";

  const processingStatus =
    response.metadata.status === "extracted"
      ? "Material processado"
      : response.metadata.status.includes("pending")
        ? "Recebido para validação"
        : "Aguardando validação";

  const reviewState =
    response.metadata.extraction_status === "extracted"
      ? "Pronto para revisão"
      : response.metadata.extraction_status.includes("ocr")
        ? "OCR em validação"
        : "Aguardando validação";

  return {
    documentId: response.metadata.document_id,
    filename: response.metadata.filename,
    originalFilename: response.metadata.original_filename,
    contentType: response.metadata.content_type,
    sizeBytes: response.metadata.size_bytes,
    processingStatus,
    extractionStatus,
    reviewState,
    source: "backend",
    demoOnly: false
  };
}

export async function uploadMaterialFile(file: File): Promise<ApiResult<UploadMaterialResult>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Mock mode is forcing local fallback.");
  }

  if (!baseUrl) {
    return makeApiFailure("unsupported", "missing_base_url", "No API base URL is configured.");
  }

  const formData = new FormData();
  formData.append("file", file, file.name);

  try {
    const response = await fetch(`${baseUrl}/api/materials/upload`, {
      method: "POST",
      credentials: "include",
      body: formData
    });

    if (response.status === 401) {
      return makeApiFailure("backend", "unauthorized", "Authentication is required for this endpoint.", 401);
    }
    if (response.status === 404) {
      return makeApiFailure("unsupported", "not_found", "Endpoint not found.", 404);
    }
    if (response.status === 413) {
      return makeApiFailure("backend", "payload_too_large", "O arquivo excede o limite suportado.", 413);
    }
    if (response.status === 415) {
      return makeApiFailure("backend", "unsupported_media", "Tipo de arquivo não suportado.", 415);
    }
    if (response.status === 400) {
      return makeApiFailure("backend", "bad_request", "O arquivo não passou na validação do endpoint.", 400);
    }
    if (response.status === 422) {
      return makeApiFailure("backend", "validation_error", "O upload precisa de ajustes antes do envio.", 422);
    }
    if (!response.ok) {
      return makeApiFailure(
        "backend",
        "http_error",
        `Backend returned HTTP ${response.status}.`,
        response.status
      );
    }

    try {
      const data = (await response.json()) as BackendUploadedMaterialResponse;
      return {
        ok: true,
        data: normalizeUploadResult(data),
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure("backend", "invalid_json", "Backend returned invalid JSON.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "network_error", "Backend is offline or unreachable.");
  }
}
