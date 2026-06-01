import { getApiConfig } from "@/lib/api/config";
import { getJson } from "@/lib/api/client";
import { makeApiFailure } from "@/lib/api/errors";
import type {
  ApiResult,
  BackendDocumentSummary,
  BackendMaterialSummary,
  BackendProtectedMaterialsList,
  BackendStudyMaterialPreparationResponse,
  BackendStudyMaterialSummary,
  MaterialType,
  StudyMaterialPreparationStatus,
  StudyMaterialSummaryItemStatus,
  StudyMaterialSummaryStatus,
  UploadMaterialResult
} from "@/lib/api/types";

export const MATERIAL_TYPE_LABELS: Record<MaterialType, string> = {
  edital: "Edital",
  study_material: "Material de estudo",
  previous_exam: "Prova anterior",
  bibliography: "Bibliografia / referência",
  note: "Anotação / resumo",
  other: "Outro",
  unknown: "Tipo não informado"
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
      return makeApiFailure("offline", "backend_offline", "Não foi possível carregar os dados agora.", 502);
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
      return makeApiFailure("offline", "backend_offline", "Não foi possível carregar os dados agora.", 502);
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

const STUDY_PREPARATION_STATUSES = new Set<StudyMaterialPreparationStatus>([
  "ready_for_study",
  "needs_review",
  "not_ready",
  "failed"
]);

function isValidStudyPreparationPayload(data: BackendStudyMaterialPreparationResponse): boolean {
  return (
    typeof data.document_id === "string" &&
    STUDY_PREPARATION_STATUSES.has(data.preparation_status) &&
    data.material_type === "study_material" &&
    typeof data.section_count === "number" &&
    typeof data.chunk_count === "number" &&
    typeof data.warnings_count === "number" &&
    typeof data.ready_for_study === "boolean" &&
    data.source === "user_scope"
  );
}

function normalizeStudyPreparationPayload(
  data: BackendStudyMaterialPreparationResponse
): BackendStudyMaterialPreparationResponse {
  return {
    document_id: data.document_id,
    preparation_status: data.preparation_status,
    material_type: "study_material",
    section_count: data.section_count,
    chunk_count: data.chunk_count,
    warnings_count: data.warnings_count,
    ready_for_study: data.ready_for_study,
    source: "user_scope"
  };
}

export async function prepareStudyMaterial(
  materialId: string
): Promise<ApiResult<BackendStudyMaterialPreparationResponse>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: o material real não foi preparado.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "A preparação do material não está configurada neste ambiente."
    );
  }

  try {
    const response = await fetch(`/api/materials/${encodeURIComponent(materialId)}/study/prepare`, {
      method: "POST",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível preparar o material agora.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "A preparação do material não está configurada neste ambiente.",
        503
      );
    }
    if (response.status === 404) {
      return makeApiFailure("backend", "not_found", "Material não encontrado nesta sessão.", 404);
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "auth_required", "Entre para preparar este material.", response.status);
    }
    if (response.status === 422) {
      return makeApiFailure(
        "backend",
        "invalid_material_type",
        "Este arquivo não está classificado como material de estudo.",
        422
      );
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
      const data = (await response.json()) as BackendStudyMaterialPreparationResponse;
      if (!isValidStudyPreparationPayload(data)) {
        return makeApiFailure("backend", "invalid_response", "Não foi possível preparar o material agora.", response.status);
      }
      return {
        ok: true,
        data: normalizeStudyPreparationPayload(data),
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure("backend", "invalid_response", "Não foi possível preparar o material agora.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "backend_offline", "Não foi possível preparar o material agora.");
  }
}

const STUDY_SUMMARY_STATUSES = new Set<StudyMaterialSummaryStatus>([
  "ready",
  "needs_review",
  "not_ready",
  "failed"
]);

const STUDY_SUMMARY_ITEM_STATUSES = new Set<StudyMaterialSummaryItemStatus>([
  "ready",
  "needs_review"
]);

function isValidStudySummaryPayload(data: BackendStudyMaterialSummary): boolean {
  return (
    typeof data.document_id === "string" &&
    STUDY_SUMMARY_STATUSES.has(data.summary_status) &&
    data.material_type === "study_material" &&
    typeof data.title === "string" &&
    typeof data.sections_count === "number" &&
    Array.isArray(data.items) &&
    data.items.every(
      (item) =>
        typeof item.section_id === "string" &&
        typeof item.title === "string" &&
        typeof item.summary === "string" &&
        Array.isArray(item.key_points) &&
        item.key_points.every((point) => typeof point === "string") &&
        typeof item.estimated_minutes === "number" &&
        STUDY_SUMMARY_ITEM_STATUSES.has(item.status)
    ) &&
    typeof data.warnings_count === "number" &&
    data.source === "user_scope"
  );
}

function normalizeStudySummaryPayload(data: BackendStudyMaterialSummary): BackendStudyMaterialSummary {
  return {
    document_id: data.document_id,
    summary_status: data.summary_status,
    material_type: "study_material",
    title: data.title,
    sections_count: data.sections_count,
    items: data.items.map((item) => ({
      section_id: item.section_id,
      title: item.title,
      summary: item.summary,
      key_points: item.key_points,
      estimated_minutes: item.estimated_minutes,
      status: item.status
    })),
    warnings_count: data.warnings_count,
    source: "user_scope"
  };
}

export async function fetchStudyMaterialSummary(
  materialId: string
): Promise<ApiResult<BackendStudyMaterialSummary>> {
  const { baseUrl, forceMock } = getApiConfig();

  if (forceMock) {
    return makeApiFailure("mock", "mock_mode", "Modo de demonstração: o resumo do material não foi consultado.");
  }

  if (!baseUrl) {
    return makeApiFailure(
      "unsupported",
      "missing_base_url",
      "O resumo do material não está configurado neste ambiente."
    );
  }

  try {
    const response = await fetch(`/api/materials/${encodeURIComponent(materialId)}/study/summary`, {
      method: "GET",
      headers: {
        Accept: "application/json"
      },
      credentials: "include",
      cache: "no-store"
    });

    if (response.status === 502) {
      return makeApiFailure("offline", "backend_offline", "Não foi possível consultar o resumo agora.", 502);
    }
    if (response.status === 503) {
      return makeApiFailure(
        "unsupported",
        "missing_base_url",
        "O resumo do material não está configurado neste ambiente.",
        503
      );
    }
    if (response.status === 404) {
      return makeApiFailure("backend", "not_found", "Material não encontrado.", 404);
    }
    if (response.status === 401 || response.status === 403) {
      return makeApiFailure("backend", "auth_required", "Entre para ver o resumo do material.", response.status);
    }
    if (response.status === 422) {
      return makeApiFailure(
        "backend",
        "invalid_material_type",
        "Este arquivo não está classificado como material de estudo.",
        422
      );
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
      const data = (await response.json()) as BackendStudyMaterialSummary;
      if (!isValidStudySummaryPayload(data)) {
        return makeApiFailure("backend", "invalid_response", "Não foi possível consultar o resumo agora.", response.status);
      }
      if (data.summary_status === "not_ready") {
        return makeApiFailure("backend", "not_ready", "O resumo ainda não está pronto para este material.", response.status);
      }
      return {
        ok: true,
        data: normalizeStudySummaryPayload(data),
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure("backend", "invalid_response", "Não foi possível consultar o resumo agora.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "backend_offline", "Não foi possível consultar o resumo agora.");
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

function normalizeUploadResult(
  response: BackendUploadedMaterialResponse,
  requestedMaterialType: MaterialType
): UploadMaterialResult {
  const extractionStatus =
    response.metadata.extraction_status === "extracted"
      ? "Texto extraído"
      : response.metadata.extraction_status.includes("pending")
      ? "Aguardando envio"
        : response.metadata.extraction_status.includes("ocr")
          ? "OCR em validação"
          : "Aguardando envio";

  const processingStatus =
    response.metadata.status === "extracted"
      ? "Material processado"
      : response.metadata.status.includes("pending")
        ? "Recebido para validação"
        : "Aguardando envio";

  const reviewState =
    response.metadata.extraction_status === "extracted"
      ? "Pronto para revisão"
      : response.metadata.extraction_status.includes("ocr")
        ? "OCR em validação"
        : "Aguardando envio";

  return {
    documentId: response.metadata.document_id,
    filename: response.metadata.filename,
    originalFilename: response.metadata.original_filename,
    contentType: response.metadata.content_type,
    materialType: normalizeMaterialType(response.metadata.material_type ?? requestedMaterialType),
    materialTypeLabel: materialTypeLabel(response.metadata.material_type ?? requestedMaterialType),
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
    return makeApiFailure("unsupported", "api_base_missing", "Envio real não configurado.");
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
      return makeApiFailure("offline", "backend_offline", "Não foi possível carregar os dados agora.", 502);
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
        data: normalizeUploadResult(data, materialType),
        status: response.status,
        source: "backend"
      };
    } catch {
      return makeApiFailure("backend", "invalid_json", "Backend returned invalid JSON.", response.status);
    }
  } catch {
    return makeApiFailure("offline", "backend_offline", "Não foi possível carregar os dados agora.");
  }
}
