import { NextResponse } from "next/server";

import { getServerBackendBaseUrl } from "@/lib/api/config";
import type {
  StudyProgressReviewBasis,
  StudyProgressStatus,
  StudyProgressSummary
} from "@/lib/api/types";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

const PROGRESS_STATUSES = new Set<StudyProgressStatus>(["ready", "not_ready"]);

const REVIEW_BASES = new Set<StudyProgressReviewBasis>([
  "prepared_materials",
  "studied_materials",
  "none"
]);

function toSafeNumber(value: unknown): number {
  return typeof value === "number" && Number.isFinite(value) ? value : 0;
}

function toSafeBoolean(value: unknown): boolean {
  return typeof value === "boolean" ? value : false;
}

function toSafeProgressStatus(value: unknown): StudyProgressStatus {
  return typeof value === "string" && PROGRESS_STATUSES.has(value as StudyProgressStatus)
    ? (value as StudyProgressStatus)
    : "not_ready";
}

function toSafeReviewBasis(value: unknown): StudyProgressReviewBasis {
  return typeof value === "string" && REVIEW_BASES.has(value as StudyProgressReviewBasis)
    ? (value as StudyProgressReviewBasis)
    : "none";
}

function sanitizeProgressSummary(payload: unknown): StudyProgressSummary {
  const raw = payload && typeof payload === "object" ? (payload as Record<string, unknown>) : {};
  return {
    progress_status: toSafeProgressStatus(raw.progress_status),
    opened_blocks_count: toSafeNumber(raw.opened_blocks_count),
    studied_blocks_count: toSafeNumber(raw.studied_blocks_count),
    prepared_materials_count: toSafeNumber(raw.prepared_materials_count),
    studied_materials_count: toSafeNumber(raw.studied_materials_count),
    review_due: toSafeBoolean(raw.review_due),
    review_basis: toSafeReviewBasis(raw.review_basis),
    reviewed_questions_count: toSafeNumber(raw.reviewed_questions_count),
    weak_topics_count: toSafeNumber(raw.weak_topics_count),
    source: "user_scope"
  };
}

export async function GET(request: Request) {
  const baseUrl = getServerBackendBaseUrl();

  if (!baseUrl) {
    return NextResponse.json(
      { detail: "O resumo de progresso não está configurado neste ambiente." },
      { status: 503 }
    );
  }

  try {
    const backendResponse = await fetch(`${baseUrl}/api/study/progress/summary`, {
      method: "GET",
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
    return NextResponse.json(sanitizeProgressSummary(payload), { status: 200 });
  } catch {
    return NextResponse.json(
      { detail: "Não foi possível carregar seu resumo de progresso agora." },
      { status: 502 }
    );
  }
}
