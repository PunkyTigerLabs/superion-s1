// Mock tests: an MCP client talks to the server in memory; fetch is replaced by a stub.
import { test } from "node:test";
import assert from "node:assert/strict";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { InMemoryTransport } from "@modelcontextprotocol/sdk/inMemory.js";
import { createServer } from "../dist/server.js";

const KEY = "s1k_test_not_a_real_key";

function stub(status, body, headers = {}) {
  const calls = [];
  const fetch = async (url, init) => {
    calls.push({ url, init, body: JSON.parse(init.body) });
    const h = new Headers({ "content-type": "application/json", "x-request-id": "req_test", ...headers });
    const payload = typeof body === "function" ? body(calls.at(-1).body) : body;
    return new Response(JSON.stringify(payload), { status, headers: h });
  };
  return { fetch, calls };
}

async function connect(opts) {
  const server = createServer({ apiKey: KEY, maxRetries: 0, ...opts });
  const [a, b] = InMemoryTransport.createLinkedPair();
  const client = new Client({ name: "test", version: "0.0.0" });
  await Promise.all([server.connect(a), client.connect(b)]);
  return client;
}

const meta = { request_id: "req_test", mode: "live", latency_ms: 120 };
const usage = { input_tokens: 42, output_tokens: 0 };

test("lists the five tools with input schemas and read-only annotations", async () => {
  const client = await connect(stub(200, {}));
  const { tools } = await client.listTools();
  assert.deepEqual(tools.map((t) => t.name).sort(), ["check_action", "classify", "decide", "decide_yes_no", "score"]);
  for (const t of tools) {
    assert.equal(t.inputSchema.type, "object");
    assert.ok(t.inputSchema.required.includes(t.name === "check_action" ? "action" : "text"));
    assert.equal(t.annotations.readOnlyHint, true);
    assert.ok(t.description.length > 40);
  }
});

test("decide_yes_no sends a noul question and returns probability_yes", async () => {
  const s = stub(200, { model: "superion-s1-v6", answers: { q: { type: "noul", noul: 0.99977 } }, usage, meta });
  const client = await connect(s);
  const r = await client.callTool({ name: "decide_yes_no", arguments: { text: "I want my money back.", question: "Refund request?" } });
  assert.ok(!r.isError);
  assert.equal(r.structuredContent.probability_yes, 0.99977);
  assert.equal(r.structuredContent.answer, "yes");
  assert.equal(r.structuredContent.request_id, "req_test");
  const { url, init, body } = s.calls[0];
  assert.equal(url, "https://api.punkytigerlabs.com/v1/systemone");
  assert.equal(init.headers.Authorization, `Bearer ${KEY}`);
  assert.deepEqual(body.questions.q, { type: "noul", instructions: "Refund request?", criteria: { true: "yes", false: "no" } });
  assert.equal(body.model, undefined); // server default (latest) unless SUPERION_MODEL is set
  assert.ok(!JSON.stringify(r).includes(KEY));
});

test("classify maps labels (and descriptions) to choice criteria and ranks the answer", async () => {
  const s = stub(200, (req) => ({
    model: "m", usage, meta,
    answers: { q: { type: "choice", choice: "billing", confidence: 0.7, probabilities: { tech: 0.1, billing: 0.85, sales: 0.05 } } },
  }));
  const client = await connect(s);
  const r = await client.callTool({
    name: "classify",
    arguments: { text: "I was charged twice", question: "Which team?", labels: ["tech", "billing", "sales"], descriptions: { billing: "payments and invoices" } },
  });
  assert.ok(!r.isError);
  assert.deepEqual(s.calls[0].body.questions.q.criteria, { tech: "tech", billing: "payments and invoices", sales: "sales" });
  assert.equal(r.structuredContent.label, "billing");
  assert.equal(r.structuredContent.probability, 0.85);
  assert.deepEqual(Object.keys(r.structuredContent.probabilities), ["billing", "tech", "sales"]);
});

test("classify rejects duplicate labels without calling the API", async () => {
  const s = stub(200, {});
  const client = await connect(s);
  const r = await client.callTool({ name: "classify", arguments: { text: "x", question: "q", labels: ["a", "a"] } });
  assert.equal(r.isError, true);
  assert.equal(s.calls.length, 0);
});

test("score returns level labels, expected level and normalized score", async () => {
  const s = stub(200, {
    model: "m", usage, meta,
    answers: { q: { type: "score", score: 1.94, confidence: 0.6, probabilities: { "0": 0, "1": 0.06, "2": 0.94 } } },
  });
  const client = await connect(s);
  const levels = ["not urgent", "somewhat urgent", "very urgent"];
  const r = await client.callTool({ name: "score", arguments: { text: "Server is down!", question: "Urgency?", levels } });
  assert.ok(!r.isError);
  assert.deepEqual(s.calls[0].body.questions.q, { type: "score", instructions: "Urgency?", criteria: levels });
  assert.equal(r.structuredContent.level, "very urgent");
  assert.equal(r.structuredContent.level_index, 2);
  assert.equal(r.structuredContent.normalized_score, 0.97);
  assert.equal(r.structuredContent.probabilities["somewhat urgent"], 0.06);
});

test("score derives confidence and expected level when the API omits them", async () => {
  const s = stub(200, { model: "m", usage, meta, answers: { q: { type: "score", probabilities: { "0": 0.5, "1": 0.5 } } } });
  const client = await connect(s);
  const r = await client.callTool({ name: "score", arguments: { text: "t", question: "q", levels: ["low", "high"] } });
  assert.equal(r.structuredContent.expected_level, 0.5);
  assert.equal(r.structuredContent.confidence, 0);
});

test("decide passes several typed questions through unchanged", async () => {
  const questions = {
    refund: { type: "noul", instructions: "Refund?", criteria: { true: "yes", false: "no" } },
    sentiment: { type: "choice", instructions: "Sentiment", criteria: { pos: "positive", neg: "negative" } },
    urgency: { type: "score", instructions: "Urgency", criteria: ["low", "high"] },
  };
  const answers = {
    refund: { type: "noul", noul: 0.9 },
    sentiment: { type: "choice", choice: "neg", confidence: 0.9, probabilities: { pos: 0.01, neg: 0.99 } },
    urgency: { type: "score", score: 0.8, confidence: 0.3, probabilities: { "0": 0.2, "1": 0.8 }, legend: { "0": "low", "1": "high" } },
  };
  const s = stub(200, { model: "m", usage, meta, answers });
  const client = await connect(s);
  const r = await client.callTool({ name: "decide", arguments: { text: "Broken laptop, money back now!", questions } });
  assert.ok(!r.isError);
  assert.deepEqual(s.calls[0].body.questions, questions);
  assert.deepEqual(r.structuredContent.answers, answers);
  assert.equal(r.structuredContent.input_tokens, 42);
});

test("decide rejects an invalid question type at the schema level", async () => {
  const s = stub(200, {});
  const client = await connect(s);
  const r = await client.callTool({ name: "decide", arguments: { text: "t", questions: { a: { type: "bogus", instructions: "x", criteria: {} } } } });
  assert.equal(r.isError, true);
  assert.equal(s.calls.length, 0);
});

test("check_action asks matches_request, irreversible and risk in ONE call", async () => {
  const s = stub(200, {
    model: "m", usage, meta,
    answers: {
      matches_request: { type: "noul", noul: 0.0062 },
      irreversible: { type: "noul", noul: 0.97 },
      risk: { type: "score", score: 2.7, confidence: 0.5, probabilities: { "0": 0.01, "1": 0.04, "2": 0.19, "3": 0.76 } },
    },
  });
  const client = await connect(s);
  const r = await client.callTool({
    name: "check_action",
    arguments: { action: "Delete the folder /reports", context: "Archive last month's reports" },
  });
  assert.ok(!r.isError);
  assert.equal(s.calls.length, 1);
  const body = s.calls[0].body;
  assert.match(body.state, /User request:\nArchive last month's reports/);
  assert.match(body.state, /Planned action:\nDelete the folder \/reports/);
  assert.deepEqual(Object.keys(body.questions), ["matches_request", "irreversible", "risk"]);
  assert.equal(body.questions.matches_request.type, "noul");
  assert.equal(body.questions.irreversible.type, "noul");
  assert.deepEqual(body.questions.risk.criteria, ["no risk", "low risk", "moderate risk", "high risk"]);
  const out = r.structuredContent;
  assert.equal(out.matches_request, 0.0062);
  assert.equal(out.irreversible, 0.97);
  assert.equal(out.risk.level, "high risk");
  assert.equal(out.risk.probability, 0.76);
  assert.equal(out.risk.normalized_score, 0.9);
  assert.equal(out.risk.probabilities["low risk"], 0.04);
  assert.equal(out.verdict, undefined); // probabilities only: the agent picks its thresholds
});

test("check_action requires both action and context", async () => {
  const s = stub(200, {});
  const client = await connect(s);
  const r = await client.callTool({ name: "check_action", arguments: { action: "rm -rf /tmp/x" } });
  assert.equal(r.isError, true);
  assert.equal(s.calls.length, 0);
});

test("check_action surfaces API errors (402) clearly", async () => {
  const client = await connect(stub(402, { error: "insufficient credits", balance_usd: 0 }));
  const r = await client.callTool({ name: "check_action", arguments: { action: "a", context: "c" } });
  assert.equal(r.isError, true);
  assert.match(r.content[0].text, /insufficient prepaid credit \(402\)/);
});

const errorCases = [
  [401, { error: "invalid API key" }, {}, /rejected the API key \(401\).*SUPERION_API_KEY.*punkytigerlabs\.com\/s1/s],
  [402, { error: "insufficient credits", code: "insufficient_credits", balance_usd: 0.0012, contact_url: "https://punkytigerlabs.com/s1/account" },
    {}, /insufficient prepaid credit \(402\).*Balance: 0\.0012 USD.*s1\/account/s],
  [429, { error: "rate limited", code: "rate_limited" }, { "retry-after": "3600" }, /\(429\).*Retry after 3600 s/s],
  [400, { error: "unknown model" }, {}, /rejected the request \(400\).*unknown model.*req_test/s],
  [422, { error: "state too long" }, {}, /\(422\).*32,768 tokens/s],
  [503, { error: "busy" }, {}, /service error \(503\)/],
];
for (const [status, body, headers, re] of errorCases) {
  test(`HTTP ${status} becomes a clear tool error`, async () => {
    const client = await connect(stub(status, body, headers));
    const r = await client.callTool({ name: "decide_yes_no", arguments: { text: "t", question: "q" } });
    assert.equal(r.isError, true);
    assert.match(r.content[0].text, re);
    assert.ok(!r.content[0].text.includes(KEY));
  });
}

test("429 with a short Retry-After is retried once and then succeeds", async () => {
  let n = 0;
  const fetch = async () => {
    n++;
    if (n === 1) return new Response(JSON.stringify({ error: "rate limited" }), { status: 429, headers: { "retry-after": "0" } });
    return new Response(JSON.stringify({ model: "m", usage, meta, answers: { q: { type: "noul", noul: 0.2 } } }), { status: 200 });
  };
  const client = await connect({ fetch, maxRetries: 2 });
  const r = await client.callTool({ name: "decide_yes_no", arguments: { text: "t", question: "q" } });
  assert.equal(n, 2);
  assert.equal(r.structuredContent.answer, "no");
});

test("missing API key returns setup instructions instead of calling the API", async () => {
  const saved = process.env.SUPERION_API_KEY;
  delete process.env.SUPERION_API_KEY;
  try {
    const s = stub(200, {});
    const client = await connect({ ...s, apiKey: "" });
    const r = await client.callTool({ name: "score", arguments: { text: "t", question: "q", levels: ["a", "b"] } });
    assert.equal(r.isError, true);
    assert.match(r.content[0].text, /SUPERION_API_KEY is not set/);
    assert.equal(s.calls.length, 0);
  } finally {
    if (saved !== undefined) process.env.SUPERION_API_KEY = saved;
  }
});

test("SUPERION_MODEL and SUPERION_BASE_URL are honoured", async () => {
  const s = stub(200, { model: "pinned", usage, meta, answers: { q: { type: "noul", noul: 0.5 } } });
  const client = await connect({ ...s, model: "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc", baseURL: "https://example.test/" });
  await client.callTool({ name: "decide_yes_no", arguments: { text: "t", question: "q" } });
  assert.equal(s.calls[0].url, "https://example.test/v1/systemone");
  assert.equal(s.calls[0].body.model, "superion-s1-v6-int4e-vllm-kv1@sha256:e6dc49dc");
});
