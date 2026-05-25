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
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: nenhum arquivo foi enviado.");
  }

  if (!baseUrl) {
    return makeApiFailure("unsupported", "api_base_missing", "URL do backend não configurada para envio real.");
  }

  const formData = new FormData();
  formData.append("file", file, file.name);

  try {
    const response = await fetch(`${baseUrl}/api/materials/upload`, {
      method: "POST",
      credentials: "include",
      body: formData
    });

    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "auth_required", "Sessão necessária para enviar material.", response.status);
    }
    if (response.status === 404) {
      return makeApiFailure("unsupported", "endpoint_unavailable", "Endpoint de envio indisponível neste ambiente.", 404);
    }
    if (response.status === 405) {
      return makeApiFailure("backend", "method_not_allowed", "Endpoint encontrado, mas o método de envio não foi aceito.", 405);
    }
    if (response.status === 413) {
      return makeApiFailure("backend", "file_too_large", "O arquivo excede o limite atual de 5 MB.", 413);
    }
    if (response.status === 415) {
      return makeApiFailure("backend", "unsupported_file_type", "Tipo de arquivo não aceito.", 415);
    }
    if (response.status === 400 || response.status === 422) {
      return makeApiFailure("backend", "validation_failed", "Arquivo não pôde ser validado.", response.status);
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
    return makeApiFailure("offline", "backend_offline", "Não foi possível conectar ao backend.");
  }
}
