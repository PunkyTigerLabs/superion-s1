import { describe, expect, it, vi } from "vitest";
import {
  AuthenticationError, DEFAULT_MODEL, InsufficientBalanceError, RateLimitError, Superion, UnprocessableError,
  choice, noul, score,
} from "../src/index";

const REAL = {
  model: DEFAULT_MODEL,
  usage: { input_tokens: 135, output_tokens: 0 },
  answers: {
    refund: { type: "noul", noul: 0.9997470683161428 },
    sentiment: { type: "choice", probabilities: { pos: 0.0002855798545093104, neg: 0.9942880386883389, neu: 0.005426381457151809 } },
    urgency: { type: "score", probabilities: { "0": 1.2e-12, "1": 0.19215297234497805, "2": 0.8078470276538201 } },
  },
};
const Q = {
  refund: noul("Does the customer ask for a refund or a replacement?"),
  sentiment: choice("Overall sentiment of the message.", { pos: "positive", neg: "negative", neu: "neutral" }),
  urgency: score("How urgent is a reply?", ["not urgent", "somewhat urgent", "very urgent"]),
};

const reply = (status: number, body: unknown, headers: Record<string, string> = {}) =>
  new Response(JSON.stringify(body), { status, headers: { "content-type": "application/json", ...headers } });

function client(...responses: Array<Response | Error>) {
  const fetch = vi.fn(async () => { const r = responses.shift()!; if (r instanceof Error) throw r; return r; });
  return { s1: new Superion({ apiKey: "s1k_test", fetch: fetch as unknown as typeof globalThis.fetch, maxRetryWait: 5 }), fetch };
}

describe("Superion", () => {
  it("requires a key", () => {
    const old = process.env.SUPERION_API_KEY; delete process.env.SUPERION_API_KEY;
    expect(() => new Superion()).toThrow(/SUPERION_API_KEY/);
    if (old) process.env.SUPERION_API_KEY = old;
  });

  it("never serialises the key", () => {
    expect(JSON.stringify(new Superion({ apiKey: "s1k_secret" }))).not.toContain("s1k_secret");
  });

  it("sends the exact wire format and parses typed answers", async () => {
    const { s1, fetch } = client(reply(200, REAL, { "X-RateLimit-Limit": "60", "X-S1-Balance-USD": "4.99" }));
    const d = await s1.decide("Message: broken laptop", Q);
    const [url, init] = fetch.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("https://api.punkytigerlabs.com/v1/systemone");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer s1k_test");
    expect(JSON.parse(init.body as string)).toEqual({ model: DEFAULT_MODEL, state: "Message: broken laptop", questions: Q });
    expect(d.answers.refund.p).toBeCloseTo(0.99975, 4);
    expect(d.answers.refund.yes()).toBe(true);
    expect(d.answers.sentiment.best).toBe("neg");
    expect(d.answers.urgency.best).toBe(2);
    expect(d.answers.urgency.bestLabel).toBe("very urgent");
    expect(d.answers.urgency.expected).toBeCloseTo(1.808, 3);
    expect(d.usage).toEqual({ inputTokens: 135, outputTokens: 0 });
    expect(d.rateLimit).toEqual({ "x-ratelimit-limit": "60" });
    expect(d.balanceUsd).toBe(4.99);
  });

  it("single-question helpers", async () => {
    const { s1 } = client(
      reply(200, { model: "m", usage: { input_tokens: 1, output_tokens: 0 }, answers: { q: { type: "noul", noul: 0.2 } } }),
      reply(200, { model: "m", usage: { input_tokens: 1, output_tokens: 0 }, answers: { q: { type: "choice", probabilities: { a: 0.3, b: 0.7 } } } }),
      reply(200, { model: "m", usage: { input_tokens: 1, output_tokens: 0 }, answers: { q: { type: "score", probabilities: { "0": 0.5, "1": 0.5 } } } }),
    );
    expect(await s1.noul("s", "q?")).toBe(0.2);
    expect((await s1.choice("s", "q", ["a", "b"])).best).toBe("b");
    expect((await s1.score("s", "q", ["lo", "hi"])).normalized).toBe(0.5);
  });

  it("retries 429/503 honouring Retry-After", async () => {
    const { s1, fetch } = client(
      reply(429, { error: "server busy: queue full, retry shortly" }, { "Retry-After": "0" }),
      reply(503, { error: "service temporarily unavailable" }, { "Retry-After": "0" }),
      reply(200, REAL));
    expect((await s1.decide("s", Q)).answers.sentiment.best).toBe("neg");
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it("does not sleep through a daily quota", async () => {
    const { s1, fetch } = client(reply(429, { error: "daily token limit reached" }, { "Retry-After": "43200" }));
    const e = await s1.decide("s", Q).catch((x) => x);
    expect(e).toBeInstanceOf(RateLimitError);
    expect(e.retryAfter).toBe(43200);
    expect(fetch).toHaveBeenCalledTimes(1);
  });

  it.each([
    [401, { error: "invalid API key" }, AuthenticationError],
    [402, { error: "insufficient balance", balance_usd: -0.000004 }, InsufficientBalanceError],
    [422, { error: "question s: score supports 2..16 levels" }, UnprocessableError],
  ])("maps %i to a typed error without retrying", async (status, body, Cls) => {
    const { s1, fetch } = client(reply(status, body));
    const e = await s1.decide("s", Q).catch((x) => x);
    expect(e).toBeInstanceOf(Cls);
    expect(e.status).toBe(status);
    expect(e.error).toBe(body.error);
    expect(fetch).toHaveBeenCalledTimes(1);
    if (status === 402) expect(e.balanceUsd).toBe(-0.000004);
  });

  it("retries network errors then raises", async () => {
    const { s1, fetch } = client(new TypeError("fetch failed"), new TypeError("fetch failed"), new TypeError("fetch failed"));
    await expect(s1.decide("s", Q)).rejects.toThrow(/fetch failed/);
    expect(fetch).toHaveBeenCalledTimes(3);
  });

  it("validates questions client-side", async () => {
    const { s1, fetch } = client();
    await expect(s1.decide("s", { q: { type: "noul", instructions: "?", criteria: { true: "y" } } as never })).rejects.toThrow(/true\/false/);
    expect(() => score("q", Array.from({ length: 17 }, String))).toThrow(/2..16/);
    expect(fetch).not.toHaveBeenCalled();
  });

  it("public endpoints do not send the key", async () => {
    const { s1, fetch } = client(reply(200, { data: [{ id: DEFAULT_MODEL }] }), reply(200, { status: "ok" }));
    expect((await s1.models())[0].id).toBe(DEFAULT_MODEL);
    expect(await s1.health()).toBe(true);
    for (const [, init] of fetch.mock.calls as unknown as [string, RequestInit][]) {
      expect((init.headers as Record<string, string>).Authorization).toBeUndefined();
    }
  });
});
