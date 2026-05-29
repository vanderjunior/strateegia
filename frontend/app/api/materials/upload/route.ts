import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function toSafeNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toSafeNullableString(value: unknown): string | null {
  return typeof value === "string" && value.trim() ? value : null;
}

function toSafeString(value: unknown): string {
  return typeof value === "string" ? value : "";
}

function sanitizeUploadResponse(payload: unknown) {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  const rawMetadata =
    raw.metadata && typeof raw.metadata === "object"
      ? (raw.metadata as Record<string, unknown>)
      : raw;

  return {
    metadata: {
      document_id: toSafeString(rawMetadata.document_id),
      filename: toSafeString(rawMetadata.filename),
      original_filename: toSafeString(rawMetadata.original_filename),
      content_type: toSafeString(rawMetadata.content_type),
      size_bytes: toSafeNumber(rawMetadata.size_bytes),
      status: toSafeString(rawMetadata.status) || "uploaded",
      extraction_status: toSafeString(rawMetadata.extraction_status) || "uploaded",
      created_at: toSafeNullableString(rawMetadata.created_at),
      updated_at: toSafeNullableString(rawMetadata.updated_at)
    },
    message: toSafeString(raw.message) || "Material recebido para validação.",
    source: "user_scope"
  };
}

export async function POST(request: Request) {
  const baseUrl = getServerBackendBaseUrl();
  if (!baseUrl) {
    return NextResponse.json(
      { detail: "URL do backend não configurada para envio real." },
      { status: 503 }
    );
  }

  const formData = await request.formData();
  const file = formData.get("file");

  if (!(file instanceof File)) {
    return NextResponse.json({ detail: "Arquivo não encontrado." }, { status: 422 });
  }

  const backendFormData = new FormData();
  backendFormData.append("file", file, file.name);

  try {
    const backendResponse = await fetch(`${baseUrl}/api/materials/upload`, {
      method: "POST",
      body: backendFormData,
      headers: request.headers.get("cookie")
        ? {
            cookie: request.headers.get("cookie") as string
          }
        : undefined,
      cache: "no-store"
    });

    if (!backendResponse.ok) {
      const responseText = await backendResponse.text();
      return new Response(responseText, {
        status: backendResponse.status,
        headers: {
          "content-type": backendResponse.headers.get("content-type") ?? "application/json"
        }
      });
    }

    const payload = await backendResponse.json();
    return NextResponse.json(sanitizeUploadResponse(payload), {
      status: backendResponse.status
    });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar ao backend." },
      { status: 502 }
    );
  }
}
