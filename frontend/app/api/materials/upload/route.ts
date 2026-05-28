import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

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

    const responseText = await backendResponse.text();
    return new Response(responseText, {
      status: backendResponse.status,
      headers: {
        "content-type": backendResponse.headers.get("content-type") ?? "application/json"
      }
    });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar ao backend." },
      { status: 502 }
    );
  }
}
