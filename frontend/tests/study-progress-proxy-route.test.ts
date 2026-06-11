import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { POST } from "@/app/api/study/progress/events/route";
import { GET } from "@/app/api/study/progress/summary/route";

describe("study progress same-origin proxy routes", () => {
  const originalBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL;
  const originalInternalUrl = process.env.BACKEND_INTERNAL_URL;

  beforeEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = "http://127.0.0.1:8000";
    process.env.BACKEND_INTERNAL_URL = "http://backend:8000";
    vi.unstubAllGlobals();
  });

  afterEach(() => {
    process.env.NEXT_PUBLIC_API_BASE_URL = originalBaseUrl;
    process.env.BACKEND_INTERNAL_URL = originalInternalUrl;
    vi.unstubAllGlobals();
  });

  it("POST targets backend progress event endpoint, forwards cookies, and strips unsafe request fields", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          event_id: "study-progress-event:1",
          event_type: "block_marked_studied",
          target_type: "block",
          target_id: "study-block:material:doc-1:0",
          created_at: "2026-06-09T12:00:00+00:00",
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new Request("http://localhost/api/study/progress/events", {
        method: "POST",
        headers: {
          cookie: "studyflow_session=server-only",
          "content-type": "application/json"
        },
        body: JSON.stringify({
          event_type: "block_marked_studied",
          target_type: "block",
          target_id: "study-block:material:doc-1:0",
          idempotency_key: "mark-doc-1",
          answer: "A",
          selected_answer: "A",
          answer_key: "A",
          gabarito: "A",
          correct_answer: "A",
          correct_alternative: "A",
          score: 10,
          correction: "official",
          progress_payload: { done: true },
          raw_text: "RAW-SHOULD-NOT-FORWARD",
          extracted_text: "EXTRACTED-SHOULD-NOT-FORWARD",
          chunk: "CHUNK-SHOULD-NOT-FORWARD",
          storage_path: "/Users/private/file.md",
          token: "TOKEN-SHOULD-NOT-FORWARD",
          cookie: "COOKIE-SHOULD-NOT-FORWARD",
          password_hash: "HASH-SHOULD-NOT-FORWARD"
        })
      })
    );
    const forwardedCall = fetchSpy.mock.calls[0] as unknown as [string, RequestInit];
    const forwardedBody = JSON.parse(String(forwardedCall[1].body));

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/study/progress/events",
      expect.objectContaining({
        method: "POST",
        headers: {
          cookie: "studyflow_session=server-only",
          "Content-Type": "application/json"
        },
        cache: "no-store"
      })
    );
    expect(forwardedBody).toEqual({
      event_type: "block_marked_studied",
      target_type: "block",
      target_id: "study-block:material:doc-1:0",
      idempotency_key: "mark-doc-1"
    });
  });

  it.each([
    [
      "unknown event_type",
      {
        event_type: "invalid_event",
        target_type: "block",
        target_id: "study-block:material:doc-1:0"
      }
    ],
    [
      "unknown target_type",
      {
        event_type: "block_marked_studied",
        target_type: "invalid_target",
        target_id: "study-block:material:doc-1:0"
      }
    ],
    [
      "missing event_type",
      {
        target_type: "block",
        target_id: "study-block:material:doc-1:0"
      }
    ],
    [
      "missing target_type",
      {
        event_type: "block_marked_studied",
        target_id: "study-block:material:doc-1:0"
      }
    ],
    [
      "missing target_id",
      {
        event_type: "block_marked_studied",
        target_type: "block"
      }
    ],
    [
      "unsafe fields with invalid event_type",
      {
        event_type: "invalid_event",
        target_type: "block",
        target_id: "study-block:material:doc-1:0",
        answer: "A",
        answer_key: "A",
        gabarito: "A",
        correct_answer: "A",
        score: 10,
        correction: "official",
        raw_text: "RAW-SHOULD-NOT-LEAK",
        storage_path: "/Users/private/file.md",
        token: "TOKEN-SHOULD-NOT-LEAK",
        internal_trace: "TRACE-SHOULD-NOT-LEAK"
      }
    ]
  ])("returns 422 locally for %s and does not call backend", async (_caseName, body) => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(
      new Request("http://localhost/api/study/progress/events", {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify(body)
      })
    );
    const dumped = await response.text();

    expect(response.status).toBe(422);
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(dumped).not.toContain("block_opened");
    expect(dumped).not.toContain("answer_key");
    expect(dumped).not.toContain("gabarito");
    expect(dumped).not.toContain("correct_answer");
    expect(dumped).not.toContain("score");
    expect(dumped).not.toContain("correction");
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("storage_path");
    expect(dumped).not.toContain("TOKEN-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("TRACE-SHOULD-NOT-LEAK");
  });

  it("GET targets backend progress summary endpoint and forwards cookies", async () => {
    const fetchSpy = vi.fn(async () =>
      new Response(
        JSON.stringify({
          progress_status: "ready",
          opened_blocks_count: 1,
          studied_blocks_count: 1,
          prepared_materials_count: 3,
          studied_materials_count: 0,
          review_due: true,
          review_basis: "prepared_materials",
          reviewed_questions_count: 1,
          weak_topics_count: 0,
          source: "user_scope"
        }),
        { status: 200, headers: { "content-type": "application/json" } }
      )
    );
    vi.stubGlobal("fetch", fetchSpy);

    const response = await GET(
      new Request("http://localhost/api/study/progress/summary", {
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" }
      })
    );

    expect(response.status).toBe(200);
    expect(fetchSpy).toHaveBeenCalledWith(
      "http://backend:8000/api/study/progress/summary",
      expect.objectContaining({
        method: "GET",
        headers: { cookie: "studyflow_session=server-only" },
        cache: "no-store"
      })
    );
  });

  it("sanitizes malicious event response fields by whitelist", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            event_id: "study-progress-event:1",
            event_type: "block_marked_studied",
            target_type: "block",
            target_id: "study-block:material:doc-1:0",
            created_at: "2026-06-09T12:00:00+00:00",
            source: "user_scope",
            answer: "A",
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            correct_answer: "CORRECT-SHOULD-NOT-LEAK",
            score: 10,
            correction: "CORRECTION-SHOULD-NOT-LEAK",
            storage_path: "/Users/private/file.md",
            raw_text: "RAW-SHOULD-NOT-LEAK",
            chunk: "CHUNK-SHOULD-NOT-LEAK",
            token: "TOKEN-SHOULD-NOT-LEAK",
            internal_trace: "TRACE-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await POST(
      new Request("http://localhost/api/study/progress/events", {
        method: "POST",
        body: JSON.stringify({
          event_type: "block_marked_studied",
          target_type: "block",
          target_id: "study-block:material:doc-1:0"
        })
      })
    );
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(payload).toEqual({
      event_id: "study-progress-event:1",
      event_type: "block_marked_studied",
      target_type: "block",
      target_id: "study-block:material:doc-1:0",
      created_at: "2026-06-09T12:00:00+00:00",
      source: "user_scope"
    });
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CORRECT-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CORRECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CHUNK-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("TOKEN-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("TRACE-SHOULD-NOT-LEAK");
  });

  it("sanitizes malicious summary response fields by whitelist", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(
          JSON.stringify({
            progress_status: "ready",
            opened_blocks_count: 1,
            studied_blocks_count: 1,
            prepared_materials_count: 3,
            studied_materials_count: 0,
            review_due: true,
            review_basis: "prepared_materials",
            reviewed_questions_count: 1,
            weak_topics_count: 0,
            source: "user_scope",
            answer_key: "ANSWER-SHOULD-NOT-LEAK",
            gabarito: "GABARITO-SHOULD-NOT-LEAK",
            correct_answer: "CORRECT-SHOULD-NOT-LEAK",
            score: 10,
            correction: "CORRECTION-SHOULD-NOT-LEAK",
            progress_payload: { done: true },
            attempt_payload: { answer: "A" },
            storage_path: "/Users/private/file.md",
            raw_text: "RAW-SHOULD-NOT-LEAK",
            internal_trace: "TRACE-SHOULD-NOT-LEAK"
          }),
          { status: 200, headers: { "content-type": "application/json" } }
        )
      )
    );

    const response = await GET(new Request("http://localhost/api/study/progress/summary", { method: "GET" }));
    const payload = await response.json();
    const dumped = JSON.stringify(payload);

    expect(payload).toEqual({
      progress_status: "ready",
      opened_blocks_count: 1,
      studied_blocks_count: 1,
      prepared_materials_count: 3,
      studied_materials_count: 0,
      review_due: true,
      review_basis: "prepared_materials",
      reviewed_questions_count: 1,
      weak_topics_count: 0,
      source: "user_scope"
    });
    expect(dumped).not.toContain("ANSWER-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("GABARITO-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CORRECT-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("CORRECTION-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("RAW-SHOULD-NOT-LEAK");
    expect(dumped).not.toContain("TRACE-SHOULD-NOT-LEAK");
  });

  it.each([401, 403])("passes through backend auth status %i", async (status) => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () =>
        new Response(JSON.stringify({ detail: "Auth response." }), {
          status,
          headers: { "content-type": "application/json" }
        })
      )
    );

    expect(
      (
        await POST(
          new Request("http://localhost/api/study/progress/events", {
            method: "POST",
            body: JSON.stringify({
              event_type: "block_marked_studied",
              target_type: "block",
              target_id: "study-block:material:doc-1:0"
            })
          })
        )
      ).status
    ).toBe(status);
    expect((await GET(new Request("http://localhost/api/study/progress/summary", { method: "GET" }))).status).toBe(status);
  });

  it("returns 422 for an empty event post without creating defaults", async () => {
    const fetchSpy = vi.fn();
    vi.stubGlobal("fetch", fetchSpy);

    const response = await POST(new Request("http://localhost/api/study/progress/events", { method: "POST" }));
    const dumped = await response.text();

    expect(response.status).toBe(422);
    expect(fetchSpy).not.toHaveBeenCalled();
    expect(dumped).not.toContain("block_opened");
  });

  it("returns 503 when backend base URL is missing", async () => {
    delete process.env.NEXT_PUBLIC_API_BASE_URL;
    delete process.env.BACKEND_INTERNAL_URL;

    expect((await POST(new Request("http://localhost/api/study/progress/events", { method: "POST" }))).status).toBe(503);
    expect((await GET(new Request("http://localhost/api/study/progress/summary", { method: "GET" }))).status).toBe(503);
  });

  it("returns 502 when backend cannot be reached", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn(async () => {
        throw new Error("network down");
      })
    );

    expect(
      (
        await POST(
          new Request("http://localhost/api/study/progress/events", {
            method: "POST",
            body: JSON.stringify({
              event_type: "block_marked_studied",
              target_type: "block",
              target_id: "study-block:material:doc-1:0"
            })
          })
        )
      ).status
    ).toBe(502);
    expect((await GET(new Request("http://localhost/api/study/progress/summary", { method: "GET" }))).status).toBe(502);
  });
});
