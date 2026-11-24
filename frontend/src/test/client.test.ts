import { afterEach, describe, expect, it, vi } from "vitest";

import { ApiError, askQuestion } from "../api/client";

function mockFetch(status: number, body: unknown) {
  const fetchMock = vi.fn().mockResolvedValue(
    new Response(JSON.stringify(body), {
      status,
      headers: { "Content-Type": "application/json" },
    }),
  );
  vi.stubGlobal("fetch", fetchMock);
  return fetchMock;
}

afterEach(() => {
  vi.unstubAllGlobals();
});

describe("askQuestion", () => {
  it("posts the question and history and returns the answer", async () => {
    const fetchMock = mockFetch(200, { answer: "42", sources: [] });
    const result = await askQuestion("why?", [{ role: "user", content: "hi" }]);

    expect(result.answer).toBe("42");
    const [url, init] = fetchMock.mock.calls[0];
    expect(url).toBe("/api/v1/query");
    expect(JSON.parse(init.body)).toEqual({
      question: "why?",
      history: [{ role: "user", content: "hi" }],
    });
  });

  it("raises ApiError with the server detail message", async () => {
    mockFetch(503, { detail: "OPENAI_API_KEY is not configured on the server." });
    await expect(askQuestion("q", [])).rejects.toEqual(
      new ApiError("OPENAI_API_KEY is not configured on the server.", 503),
    );
  });
});
