import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

function responseHeadersFromBackend(backendResponse: Response): Headers {
  const headers = new Headers({
    "content-type": backendResponse.headers.get("content-type") ?? "application/json"
  });
  const setCookie = backendResponse.headers.get("set-cookie");
  if (setCookie) {
    headers.set("set-cookie", setCookie);
  }
  return headers;
}

export async function POST(request: Request) {
  const baseUrl = getServerBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "Sessão não configurada neste ambiente." },
      { status: 503 }
    );
  }

  try {
    const body = await request.text();
    const backendResponse = await fetch(`${baseUrl}/api/auth/login`, {
      method: "POST",
      headers: {
        "content-type": request.headers.get("content-type") ?? "application/json",
        accept: "application/json"
      },
      body,
      cache: "no-store"
    });

    const responseText = await backendResponse.text();
    return new Response(responseText, {
      status: backendResponse.status,
      headers: responseHeadersFromBackend(backendResponse)
    });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível carregar o acesso agora." },
      { status: 502 }
    );
  }
}
