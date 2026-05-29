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
    const backendResponse = await fetch(`${baseUrl}/api/auth/logout`, {
      method: "POST",
      headers: request.headers.get("cookie")
        ? {
            cookie: request.headers.get("cookie") as string,
            accept: "application/json"
          }
        : {
            accept: "application/json"
          },
      cache: "no-store"
    });

    const responseText = await backendResponse.text();
    return new Response(responseText, {
      status: backendResponse.status,
      headers: responseHeadersFromBackend(backendResponse)
    });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível conectar ao backend." },
      { status: 502 }
    );
  }
}
