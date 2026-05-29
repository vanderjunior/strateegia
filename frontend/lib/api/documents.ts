import { getApiConfig } from "@/lib/api/config";
import { getJson } from "@/lib/api/client";
import { makeApiFailure } from "@/lib/api/errors";
import type {
  ApiResult,
  BackendDocumentSummary,
  BackendMaterialSummary,
  BackendProtectedMaterialsList,
  MaterialType,
  UploadMaterialResult
} from "@/lib/api/types";

export const MATERIAL_TYPE_LABELS: Record<MaterialType, string> = {
  edital: "Edital",
  study_material: "Material de estudo",
  previous_exam: "Prova anterior",
  bibliography: "Bibliografia / referência",
  note: "Anotação / resumo",
  other: "Outro",
  unknown: "Não classificado"
};

export const MATERIAL_TYPE_OPTIONS: { id: MaterialType; label: string }[] = [
  { id: "edital", label: MATERIAL_TYPE_LABELS.edital },
  { id: "study_material", label: MATERIAL_TYPE_LABELS.study_material },
  { id: "previous_exam", label: MATERIAL_TYPE_LABELS.previous_exam },
  { id: "bibliography", label: MATERIAL_TYPE_LABELS.bibliography },
  { id: "note", label: MATERIAL_TYPE_LABELS.note },
  { id: "other", label: MATERIAL_TYPE_LABELS.other }
];

const MATERIAL_TYPE_VALUES = new Set<MaterialType>([
  "edital",
  "study_material",
  "previous_exam",
  "bibliography",
  "note",
  "other",
  "unknown"
]);

export function normalizeMaterialType(value: unknown): MaterialType {
  return typeof value === "string" && MATERIAL_TYPE_VALUES.has(value as MaterialType)
    ? (value as MaterialType)
    : "unknown";
}

export function materialTypeLabel(value: unknown): string {
  return MATERIAL_TYPE_LABELS[normalizeMaterialType(value)];
}

export function fetchDocuments(): Promise<ApiResult<BackendDocumentSummary[]>> {
  return getJson<BackendDocumentSummary[]>("/api/documents");
}

export function fetchDocumentById(documentId: string): Promise<ApiResult<BackendDocumentSummary>> {
  return getJson<BackendDocumentSummary>(`/api/documents/${documentId}`);
}

export async function fetchUserMaterialsList(): Promise<ApiResult<BackendProtectedMaterialsList>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: a listagem real não foi consultada.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "A listagem real de materiais não está configurada neste ambiente."
    );
  }

  try {
    const response = await fetch("/api/materials", {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível conectar ao backend.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "A listagem real de materiais não está configurada neste ambiente.",
        503
      );
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "unauthorized", "Sessão necessária.", response.status);
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
      const data = (await response.json()) as BackendProtectedMaterialsList;
      return {
        ok: true,
        data,
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure("backend", "invalid_json", "Backend returned invalid JSON.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "network_error", "Não foi possível consultar a listagem real de materiais.");
  }
}

export async function fetchMaterialSummary(materialId: string): Promise<ApiResult<BackendMaterialSummary>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: o resumo real do material não foi consultado.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "O resumo real do material não está configurado neste ambiente."
    );
  }

  try {
    const response = await fetch(`/api/materials/${encodeURIComponent(materialId)}/summary`, {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível conectar ao backend.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "O resumo real do material não está configurado neste ambiente.",
        503
      );
    }
    if (response.status === 404) {
      return makeApiFailure(
        "backend",
        "not_found",
        "Este conteúdo não está disponível nesta sessão.",
        404
      );
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "unauthorized", "Sessão necessária.", response.status);
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
      const data = (await response.json()) as BackendMaterialSummary;
      return {
        ok: true,
        data,
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure("backend", "invalid_json", "Backend returned invalid JSON.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "network_error", "Não foi possível consultar o resumo real do material.");
  }
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
    material_type?: MaterialType;
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
    materialType: normalizeMaterialType(response.metadata.material_type),
    materialTypeLabel: materialTypeLabel(response.metadata.material_type),
    sizeBytes: response.metadata.size_bytes,
    processingStatus,
    extractionStatus,
    reviewState,
    source: "backend",
    demoOnly: false
  };
}

export async function uploadMaterialFile(
  file: File,
  materialType: MaterialType = "unknown"
): Promise<ApiResult<UploadMaterialResult>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: nenhum arquivo foi enviado.");
  }

  if (!baseUrl) {
    return makeApiFailure("unsupported", "api_base_missing", "URL do backend não configurada para envio real.");
  }

  const formData = new FormData();
  formData.append("file", file, file.name);
  formData.append("material_type", materialType);

  try {
    const response = await fetch("/api/materials/upload", {
      method: "POST",
      credentials: "include",
      body: formData
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível conectar ao backend.", 502);
    }
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
