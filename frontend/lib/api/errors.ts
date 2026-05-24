import type { ApiFailure } from "@/lib/api/types";

export function makeApiFailure(
  source: ApiFailure["source"],
  code: ApiFailure["error"]["code"],
  message: string,
  status: number | null = null
): ApiFailure {
  return {
    ok: false,
    status,
    source,
    error: {
      code,
      message
    }
  };
}
