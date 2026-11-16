// Live test against the real API over stdio. Opt-in: S1_LIVE=1 and SUPERION_API_KEY set.
// The key is passed to the child process through the environment and never printed.
import { test } from "node:test";
import assert from "node:assert/strict";
import { fileURLToPath } from "node:url";
import { Client } from "@modelcontextprotocol/sdk/client/index.js";
import { StdioClientTransport } from "@modelcontextprotocol/sdk/client/stdio.js";

const live = process.env.S1_LIVE && process.env.SUPERION_API_KEY;
const bin = fileURLToPath(new URL("../dist/index.js", import.meta.url));
const TICKET = "Message: The laptop arrived broken. I want my money back now, this is unacceptable.";

test("live: all five tools against api.punkytigerlabs.com", { skip: !live && "set S1_LIVE=1 and SUPERION_API_KEY" }, async () => {
  const transport = new StdioClientTransport({ command: process.execPath, args: [bin], env: { ...process.env }, stderr: "pipe" });
  const client = new Client({ name: "live-test", version: "0.0.0" });
  await client.connect(transport);
  const call = async (name, args) => {
    const r = await client.callTool({ name, arguments: args });
    assert.ok(!r.isError, r.content?.[0]?.text);
    assert.ok(!JSON.stringify(r).includes(process.env.SUPERION_API_KEY));
    return r.structuredContent;
  };
  try {
    const yn = await call("decide_yes_no", { text: TICKET, question: "Does the customer ask for a refund or a replacement?" });
    assert.ok(yn.probability_yes > 0.9);
    const c = await call("classify", { text: TICKET, question: "Overall sentiment of the message.", labels: ["positive", "negative", "neutral"] });
    assert.equal(c.label, "negative");
    const s = await call("score", { text: TICKET, question: "How urgent is a reply?", levels: ["not urgent", "somewhat urgent", "very urgent"] });
    assert.equal(s.level, "very urgent");
    const bad = await call("check_action", {
      action: "Delete the folder /reports and every file in it.",
      context: "Archive last month's reports into reports/2026-10/.",
    });
    assert.ok(bad.matches_request < 0.5, `matches_request ${bad.matches_request}`);
    assert.ok(bad.irreversible > 0.5, `irreversible ${bad.irreversible}`);
    const good = await call("check_action", {
      action: "Move the files from last month in /reports into /reports/2026-10/.",
      context: "Archive last month's reports into reports/2026-10/.",
    });
    assert.ok(good.matches_request > bad.matches_request);
    assert.ok(good.risk.expected_level < bad.risk.expected_level);
    const d = await call("decide", {
      text: TICKET,
      questions: {
        refund: { type: "noul", instructions: "Does the customer ask for a refund or a replacement?", criteria: { true: "yes", false: "no" } },
        sentiment: { type: "choice", instructions: "Overall sentiment of the message.", criteria: { pos: "positive", neg: "negative", neu: "neutral" } },
        urgency: { type: "score", instructions: "How urgent is a reply?", criteria: ["not urgent", "somewhat urgent", "very urgent"] },
      },
    });
    assert.ok(d.answers.refund.noul > 0.9);
    assert.equal(d.answers.sentiment.choice, "neg");
    assert.equal(d.answers.urgency.type, "score");
    console.log(JSON.stringify({
      check_action_delete: { matches: bad.matches_request, irreversible: bad.irreversible, risk: bad.risk.level, risk_expected: bad.risk.expected_level },
      check_action_archive: { matches: good.matches_request, irreversible: good.irreversible, risk: good.risk.level, risk_expected: good.risk.expected_level },
      yes_no: yn.probability_yes, classify: [c.label, c.probability], score: [s.level, s.probability],
      decide: { refund: d.answers.refund.noul, sentiment: d.answers.sentiment.choice, urgency: d.answers.urgency.score },
      model: d.model, input_tokens: d.input_tokens,
    }));
  } finally {
    await client.close();
  }
});
